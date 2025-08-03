"""
大语言模型服务

本模块实现了与LLM的交互，包括问题分析、解决方案生成等功能。
集成了缓存机制和性能监控。
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
from app.services.storage.cache_service import cached_llm_call
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

    @monitor_performance("llm_analyze_query", slow_threshold=5.0)
    @cached_llm_call("llm_analysis", expire_time=3600)
    def analyze_query(self, query: str, vendor: str = "Huawei",
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析用户查询

        Args:
            query: 用户查询
            vendor: 厂商类型
            context: 上下文信息

        Returns:
            分析结果
        """
        if not query or not query.strip():
            return {
                'analysis': '查询为空，请提供具体的问题描述',
                'category': 'invalid_query',
                'vendor': vendor,
                'confidence': 0.0
            }

        try:
            # 构建系统提示
            system_prompt = SYSTEM_ROLE_PROMPT + "\n\n" + get_vendor_prompt(vendor)

            # 构建分析提示
            analysis_prompt = ANALYSIS_PROMPT.format(
                vendor=vendor,
                query=query,
                context=context or {}
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=analysis_prompt)
            ]

            start_time = time.time()
            response = self.llm.invoke(messages)
            duration = time.time() - start_time

            result = {
                'analysis': response.content,
                'category': self._extract_category(response.content),
                'vendor': vendor,
                'confidence': self._extract_confidence(response.content),
                'processing_time': duration
            }

            logger.info(f"查询分析完成，耗时: {duration:.2f}s")
            return result

        except Exception as e:
            logger.error(f"查询分析失败: {str(e)}")
            return {
                'analysis': f'分析过程中出现错误: {str(e)}',
                'category': 'error',
                'vendor': vendor,
                'confidence': 0.0,
                'error': str(e)
            }

    def _extract_category(self, content: str) -> str:
        """从回复中提取问题类别"""
        content_lower = content.lower()

        # 定义类别关键词
        categories = {
            'routing': ['路由', 'ospf', 'bgp', 'isis', 'rip'],
            'switching': ['交换', 'vlan', 'stp', 'trunk', 'access'],
            'network': ['网络', '连接', '丢包', '延迟', 'ping'],
            'configuration': ['配置', 'config', '设置', '参数'],
            'troubleshooting': ['故障', '问题', '错误', '异常', '告警'],
            'security': ['安全', '防火墙', 'acl', '认证', '授权'],
            'performance': ['性能', '优化', '带宽', '吞吐量', '利用率']
        }

        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return category

        return 'general'

    def _extract_confidence(self, content: str) -> float:
        """从回复中提取置信度"""
        # 简化的置信度计算
        content_length = len(content)

        if content_length > 500:
            return 0.9
        elif content_length > 200:
            return 0.7
        elif content_length > 100:
            return 0.5
        else:
            return 0.3

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'model_name': 'qwen-plus',
            'provider': 'Alibaba Cloud',
            'max_tokens': 2000,
            'temperature': 0.1
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            test_message = [HumanMessage(content="Hello")]
            response = self.llm.invoke(test_message)

            return {
                'status': 'healthy',
                'response_time': 'normal',
                'model_available': True
            }
        except Exception as e:
            logger.error(f"LLM健康检查失败: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'model_available': False
            }
