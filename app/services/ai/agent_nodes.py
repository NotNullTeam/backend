"""
Agent节点实现

实现langgraph Agent的各个处理节点，包括问题分析、知识检索、解决方案生成等。
"""

import logging
from typing import Dict, Any
from app.services.ai.agent_state import AgentState
from app.services.ai.llm_service import LLMService
from app.services.ai.agent_service import RetrievalService
from app.models.case import Node
from app import db

logger = logging.getLogger(__name__)


def analyze_query(state: AgentState) -> AgentState:
    """
    分析用户问题节点

    Args:
        state: Agent状态

    Returns:
        更新后的Agent状态
    """
    try:
        logger.info(f"开始分析用户查询: {state['user_query']}")

        # 初始化LLM服务
        llm_service = LLMService()

        # 分析用户查询
        analysis_result = llm_service.analyze_query(
            query=state["user_query"],
            context="",
            vendor=state.get("vendor")
        )

        # 更新状态
        state["category"] = analysis_result.get("category")
        state["need_more_info"] = analysis_result.get("need_more_info", False)
        state["analysis_result"] = analysis_result
        state["step"] = "analysis_completed"

        # 更新数据库节点
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.content = {
                "analysis": analysis_result.get("analysis"),
                "category": analysis_result.get("category"),
                "severity": analysis_result.get("severity")
            }

            if state["need_more_info"]:
                node.type = "AI_ANALYSIS"
                node.status = "AWAITING_USER_INPUT"
                state["step"] = "need_clarification"
            else:
                node.type = "AI_ANALYSIS"
                node.status = "COMPLETED"
                state["step"] = "ready_for_retrieval"

            # 更新节点元数据
            if node.node_metadata is None:
                node.node_metadata = {}
            node.node_metadata.update({
                'analysis_step': 'completed',
                'category': analysis_result.get("category"),
                'need_more_info': state["need_more_info"]
            })

            db.session.commit()

        logger.info(f"问题分析完成，分类: {analysis_result.get('category')}, 需要更多信息: {state['need_more_info']}")

    except Exception as e:
        logger.error(f"分析用户查询失败: {str(e)}")
        state["error"] = f"分析过程中发生错误: {str(e)}"
        state["step"] = "analysis_error"

        # 更新数据库节点错误状态
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.status = "COMPLETED"
            node.content = {"error": "分析过程中发生错误，请重试"}
            db.session.commit()

    return state


def generate_clarification(state: AgentState) -> AgentState:
    """
    生成澄清问题节点

    Args:
        state: Agent状态

    Returns:
        更新后的Agent状态
    """
    try:
        logger.info("开始生成澄清问题")

        # 初始化LLM服务
        llm_service = LLMService()

        # 生成澄清问题
        clarification = llm_service.generate_clarification(
            query=state["user_query"],
            analysis=state.get("analysis_result", {}),
            vendor=state.get("vendor")
        )

        # 更新状态
        state["clarification"] = clarification
        state["step"] = "clarification_generated"

        # 更新数据库节点
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.type = "AI_CLARIFICATION"
            node.title = "需要更多信息"
            node.status = "AWAITING_USER_INPUT"
            node.content = {
                "analysis": state["analysis_result"].get("analysis", ""),
                "category": state["analysis_result"].get("category", ""),
                "severity": state["analysis_result"].get("severity", ""),
                "clarification": clarification.get("clarification", ""),
                "questions": clarification.get("questions", ""),
                "vendor": state.get("vendor")
            }

            # 更新节点元数据
            if node.node_metadata is None:
                node.node_metadata = {}
            node.node_metadata.update({
                'clarification_step': 'completed',
                'needs_user_response': True
            })

            db.session.commit()

        logger.info("澄清问题生成完成")

    except Exception as e:
        logger.error(f"生成澄清问题失败: {str(e)}")
        state["error"] = f"澄清问题生成失败: {str(e)}"
        state["step"] = "clarification_error"

        # 更新数据库节点错误状态
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.status = "COMPLETED"
            node.content = {"error": "澄清问题生成失败，请重试"}
            db.session.commit()

    return state


def retrieve_knowledge(state: AgentState) -> AgentState:
    """
    检索相关知识节点

    Args:
        state: Agent状态

    Returns:
        更新后的Agent状态
    """
    try:
        logger.info("开始检索相关知识")

        # 初始化检索服务
        retrieval_service = RetrievalService()

        # 构建检索过滤器
        search_filters = {}
        if state.get("vendor"):
            search_filters["vendor"] = state["vendor"]

        # 执行知识检索
        context = retrieval_service.search(
            query=state["user_query"],
            filters=search_filters
        )

        # 更新状态
        state["context"] = context
        state["step"] = "knowledge_retrieved"

        logger.info(f"知识检索完成，找到 {len(context)} 个相关文档")

    except Exception as e:
        logger.error(f"知识检索失败: {str(e)}")
        state["error"] = f"知识检索失败: {str(e)}"
        state["context"] = []
        state["step"] = "retrieval_error"

    return state


def generate_solution(state: AgentState) -> AgentState:
    """
    生成解决方案节点

    Args:
        state: Agent状态

    Returns:
        更新后的Agent状态
    """
    try:
        logger.info("开始生成解决方案")

        # 初始化LLM服务
        llm_service = LLMService()

        # 生成解决方案
        solution = llm_service.generate_solution(
            query=state["user_query"],
            context=state.get("context", []),
            analysis=state.get("analysis_result"),
            vendor=state.get("vendor", "通用")
        )

        # 更新状态
        state["solution"] = solution
        state["solution_ready"] = True
        state["step"] = "solution_generated"

        # 更新数据库节点
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.type = "SOLUTION"
            node.title = "解决方案"
            node.status = "COMPLETED"
            node.content = {
                "answer": solution.get("answer"),
                "sources": solution.get("sources", []),
                "commands": solution.get("commands", []),
                "category": state.get("category"),
                "vendor": state.get("vendor", "通用")
            }

            # 更新节点元数据
            if node.node_metadata is None:
                node.node_metadata = {}
            node.node_metadata.update({
                'solution_step': 'completed',
                'context_count': len(state.get("context", [])),
                'solution_ready': True
            })

            db.session.commit()

        logger.info("解决方案生成完成")

    except Exception as e:
        logger.error(f"解决方案生成失败: {str(e)}")
        state["error"] = f"解决方案生成失败: {str(e)}"
        state["step"] = "solution_error"

        # 更新数据库节点错误状态
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.status = "COMPLETED"
            node.content = {"error": "解决方案生成失败，请重试"}
            db.session.commit()

    return state


def handle_error(state: AgentState) -> AgentState:
    """
    错误处理节点

    Args:
        state: Agent状态

    Returns:
        更新后的Agent状态
    """
    try:
        logger.error(f"处理Agent错误: {state.get('error', '未知错误')}")

        # 更新数据库节点错误状态
        node = db.session.get(Node, state["current_node_id"])
        if node:
            node.status = "COMPLETED"
            node.content = {
                "error": state.get("error", "处理过程中发生未知错误"),
                "step": state.get("step", "unknown")
            }
            db.session.commit()

        state["step"] = "error_handled"

    except Exception as e:
        logger.error(f"错误处理失败: {str(e)}")
        state["step"] = "critical_error"

    return state
