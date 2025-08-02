"""
大语言模型服务

本模块实现了与LLM的交互，包括问题分析、解决方案生成等功能。
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from app.prompts import (
    ANALYSIS_PROMPT,
    CLARIFICATION_PROMPT,
    SOLUTION_PROMPT,
    CONTINUE_CONVERSATION_PROMPT,
    FEEDBACK_PROCESSING_PROMPT
)
from app.prompts.base_prompt import SYSTEM_ROLE_PROMPT, ERROR_HANDLING_PROMPT
from app.prompts.vendor_prompts import get_vendor_prompt
from app.services.storage.cache_service import cached_llm_result
from app.utils.monitoring import monitor_performance

logger = logging.getLogger(__name__)


class LLMService:
    """大语言模型服务类"""

    def __init__(self):
        """初始化LLM服务"""
        try:
            self.llm = ChatOpenAI(
                model="qwen-plus",
                openai_api_key=os.environ.get('DASHSCOPE_API_KEY'),
                openai_api_base=os.environ.get('OPENAI_API_BASE',
                    'https://dashscope.aliyuncs.com/compatible-mode/v1'),
                temperature=0.1,
                max_tokens=2000,
                timeout=30
            )
            logger.info("LLM服务初始化成功")
        except Exception as e:
            logger.error(f"LLM服务初始化失败: {str(e)}")
            raise

    @monitor_performance("llm_analyze_query", include_args=True)
    @cached_llm_result(expire_time=1800, cache_prefix="llm_analysis")  # 30分钟缓存
    def analyze_query(self, query: str, context: str = "", vendor: str = None) -> Dict[str, Any]:
        """
        分析用户查询

        Args:
            query: 用户问题
            context: 上下文信息
            vendor: 设备厂商

        Returns:
            分析结果字典
        """
        try:
            start_time = time.time()

            # 构建提示词
            prompt = ANALYSIS_PROMPT.format(
                user_query=query,
                context=context or "无额外上下文信息"
            )

            # 如果指定了厂商，添加厂商相关的提示
            system_message = SYSTEM_ROLE_PROMPT
            if vendor:
                vendor_prompt = get_vendor_prompt(vendor, "")
                system_message += f"\n\n{vendor_prompt}"

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)

            # 解析响应
            analysis_text = response.content
            need_more_info = "[NEED_MORE_INFO]" in analysis_text
            need_detailed_diagnosis = "[NEED_DETAILED_DIAGNOSIS]" in analysis_text

            # 提取问题分类
            category = self._extract_category(analysis_text)
            severity = self._extract_severity(analysis_text)

            duration = time.time() - start_time
            logger.info(f"问题分析完成，耗时: {duration:.2f}秒")

            return {
                "analysis": analysis_text.replace("[NEED_MORE_INFO]", "").replace("[NEED_DETAILED_DIAGNOSIS]", "").strip(),
                "need_more_info": need_more_info,
                "need_detailed_diagnosis": need_detailed_diagnosis,
                "category": category,
                "severity": severity,
                "vendor": vendor
            }

        except Exception as e:
            logger.error(f"问题分析失败: {str(e)}")
            return {
                "analysis": "分析过程中发生错误，请稍后重试。",
                "need_more_info": True,
                "need_detailed_diagnosis": False,
                "category": "其他",
                "severity": "中",
                "vendor": vendor,
                "error": str(e)
            }

    @monitor_performance("llm_generate_clarification", include_args=True)
    @cached_llm_result(expire_time=3600, cache_prefix="llm_clarification")
    def generate_clarification(self, query: str, analysis: Dict[str, Any],
                             vendor: str = None) -> Dict[str, Any]:
        """
        生成澄清问题

        Args:
            query: 原始问题
            analysis: 分析结果
            vendor: 设备厂商

        Returns:
            澄清问题字典
        """
        try:
            start_time = time.time()

            # 生成针对性的问题列表
            questions = self._generate_specific_questions(analysis.get("category", "其他"), vendor)

            prompt = CLARIFICATION_PROMPT.format(
                current_analysis=analysis.get("analysis", ""),
                category=analysis.get("category", "未知"),
                severity=analysis.get("severity", "中"),
                questions=questions
            )

            # 构建系统消息
            system_message = SYSTEM_ROLE_PROMPT
            if vendor:
                vendor_prompt = get_vendor_prompt(vendor, "")
                system_message += f"\n\n{vendor_prompt}"

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)

            duration = time.time() - start_time
            logger.info(f"澄清问题生成完成，耗时: {duration:.2f}秒")

            return {
                "clarification": response.content,
                "questions": questions,
                "category": analysis.get("category"),
                "vendor": vendor
            }

        except Exception as e:
            logger.error(f"澄清问题生成失败: {str(e)}")
            return {
                "clarification": "为了更好地帮助您解决问题，请提供更多详细信息。",
                "questions": "请详细描述问题现象、网络环境和设备信息。",
                "category": analysis.get("category", "其他"),
                "vendor": vendor,
                "error": str(e)
            }

    @monitor_performance("llm_generate_solution", include_args=True)
    @cached_llm_result(expire_time=1800, cache_prefix="llm_solution")
    def generate_solution(self, query: str, context: List[Dict],
                         analysis: Dict[str, Any] = None,
                         user_context: str = "",
                         vendor: str = "通用") -> Dict[str, Any]:
        """
        生成解决方案

        Args:
            query: 用户问题
            context: 检索到的文档上下文
            analysis: 问题分析结果
            user_context: 用户补充的上下文信息
            vendor: 设备厂商

        Returns:
            解决方案字典
        """
        try:
            start_time = time.time()

            # 格式化检索到的文档
            retrieved_docs = self._format_context(context)

            # 构建解决方案提示词
            prompt = SOLUTION_PROMPT.format(
                vendor=vendor,
                problem=query,
                category=analysis.get("category", "未知") if analysis else "未知",
                environment=user_context or "未提供详细环境信息",
                retrieved_docs=retrieved_docs,
                user_context=user_context
            )

            # 构建系统消息
            system_message = SYSTEM_ROLE_PROMPT
            vendor_prompt = get_vendor_prompt(vendor, "")
            system_message += f"\n\n{vendor_prompt}"

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)

            # 解析解决方案
            solution_text = response.content
            sources = self._extract_sources(context)
            commands = self._extract_commands(solution_text)

            duration = time.time() - start_time
            logger.info(f"解决方案生成完成，耗时: {duration:.2f}秒")

            return {
                "answer": solution_text,
                "sources": sources,
                "commands": commands,
                "vendor": vendor,
                "category": analysis.get("category") if analysis else "其他"
            }

        except Exception as e:
            logger.error(f"解决方案生成失败: {str(e)}")
            return {
                "answer": "解决方案生成过程中发生错误，请稍后重试。",
                "sources": [],
                "commands": [],
                "vendor": vendor,
                "error": str(e)
            }

    def continue_conversation(self, conversation_history: List[Dict],
                            new_query: str, problem_status: str = "进行中") -> Dict[str, Any]:
        """
        处理多轮对话

        Args:
            conversation_history: 对话历史
            new_query: 新问题
            problem_status: 问题状态

        Returns:
            回复字典
        """
        try:
            # 格式化对话历史
            history_text = self._format_conversation_history(conversation_history)

            prompt = CONTINUE_CONVERSATION_PROMPT.format(
                conversation_history=history_text,
                new_query=new_query,
                problem_status=problem_status
            )

            messages = [
                SystemMessage(content=SYSTEM_ROLE_PROMPT),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)

            return {
                "response": response.content,
                "conversation_type": "continue",
                "status": problem_status
            }

        except Exception as e:
            logger.error(f"多轮对话处理失败: {str(e)}")
            return {
                "response": "对话处理过程中发生错误，请重新开始对话。",
                "conversation_type": "error",
                "status": "错误",
                "error": str(e)
            }

    def process_feedback(self, original_problem: str, provided_solution: str,
                        user_feedback: str) -> Dict[str, Any]:
        """
        处理用户反馈

        Args:
            original_problem: 原始问题
            provided_solution: 提供的解决方案
            user_feedback: 用户反馈

        Returns:
            处理结果字典
        """
        try:
            prompt = FEEDBACK_PROCESSING_PROMPT.format(
                original_problem=original_problem,
                provided_solution=provided_solution,
                user_feedback=user_feedback
            )

            messages = [
                SystemMessage(content=SYSTEM_ROLE_PROMPT),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)

            return {
                "feedback_response": response.content,
                "feedback_type": self._analyze_feedback_type(user_feedback)
            }

        except Exception as e:
            logger.error(f"反馈处理失败: {str(e)}")
            return {
                "feedback_response": "感谢您的反馈。如有其他问题，请随时咨询。",
                "feedback_type": "unknown",
                "error": str(e)
            }

    def _extract_category(self, text: str) -> str:
        """从分析结果中提取问题分类"""
        categories = ["OSPF", "BGP", "MPLS", "VPN", "交换", "路由", "安全", "硬件"]
        text_upper = text.upper()

        for category in categories:
            if category.upper() in text_upper:
                return category
        return "其他"

    def _extract_severity(self, text: str) -> str:
        """从分析结果中提取严重程度"""
        if "紧急" in text:
            return "紧急"
        elif "高" in text:
            return "高"
        elif "低" in text:
            return "低"
        else:
            return "中"

    def _format_context(self, context: List[Dict]) -> str:
        """格式化检索到的上下文"""
        if not context:
            return "未找到相关文档。"

        formatted = ""
        for i, doc in enumerate(context, 1):
            title = doc.get('title', doc.get('file_name', '文档'))
            content = doc.get('content', doc.get('text', ''))
            source = doc.get('source_document', doc.get('source', ''))

            formatted += f"[doc{i}] {title}\n"
            if source:
                formatted += f"来源: {source}\n"
            formatted += f"{content}\n\n"

        return formatted

    def _extract_sources(self, context: List[Dict]) -> List[Dict]:
        """提取引用来源"""
        sources = []
        for i, doc in enumerate(context, 1):
            sources.append({
                "id": f"doc{i}",
                "title": doc.get('title', doc.get('file_name', '文档')),
                "source": doc.get('source_document', doc.get('source', '')),
                "page": doc.get('page_number', doc.get('page', 0))
            })
        return sources

    def _extract_commands(self, text: str) -> List[str]:
        """从回答中提取命令"""
        import re
        # 匹配反引号中的命令
        commands = re.findall(r'`([^`]+)`', text)
        # 过滤掉太短的匹配（可能不是命令）
        commands = [cmd.strip() for cmd in commands if len(cmd.strip()) > 3]
        return commands

    def _generate_specific_questions(self, category: str, vendor: str = None) -> str:
        """根据问题分类生成具体的澄清问题"""
        base_questions = [
            "请详细描述问题的具体现象？",
            "问题是什么时候开始出现的？",
            "是否有相关的错误日志或告警信息？",
            "网络拓扑是怎样的？涉及哪些设备？"
        ]

        category_questions = {
            "OSPF": [
                "OSPF邻居状态是什么？",
                "OSPF区域配置是否正确？",
                "是否有路由振荡现象？"
            ],
            "BGP": [
                "BGP邻居状态如何？",
                "AS号配置是否正确？",
                "是否有路由泄露问题？"
            ],
            "VPN": [
                "VPN类型是什么（IPSec、MPLS VPN等）？",
                "隧道状态是否正常？",
                "认证配置是否正确？"
            ],
            "交换": [
                "VLAN配置是否正确？",
                "端口状态如何？",
                "是否有环路问题？"
            ]
        }

        questions = base_questions.copy()
        if category in category_questions:
            questions.extend(category_questions[category])

        if vendor:
            questions.append(f"设备型号和{vendor}系统版本是什么？")

        return "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """格式化对话历史"""
        formatted = ""
        for i, msg in enumerate(history[-5:], 1):  # 只保留最近5轮对话
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted += f"{i}. {role}: {content}\n"
        return formatted

    def _analyze_feedback_type(self, feedback: str) -> str:
        """分析反馈类型"""
        feedback_lower = feedback.lower()
        if any(word in feedback_lower for word in ["成功", "解决", "有效", "好的", "谢谢"]):
            return "success"
        elif any(word in feedback_lower for word in ["失败", "无效", "不行", "错误"]):
            return "failure"
        elif any(word in feedback_lower for word in ["部分", "还有", "继续"]):
            return "partial"
        else:
            return "clarification"
