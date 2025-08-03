"""
Agent工作流编排

使用langgraph构建智能对话Agent的状态机工作流。
"""

import logging
from typing import Callable
from langgraph.graph import StateGraph, END
from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import (
    analyze_query,
    generate_clarification,
    retrieve_knowledge,
    generate_solution,
    handle_error
)

logger = logging.getLogger(__name__)


def should_generate_clarification(state: AgentState) -> str:
    """
    判断是否需要生成澄清问题

    Args:
        state: Agent状态

    Returns:
        下一个节点的名称
    """
    if state.get("error"):
        return "handle_error"

    if state.get("need_more_info", False):
        return "generate_clarification"

    return "retrieve_knowledge"


def should_continue_to_solution(state: AgentState) -> str:
    """
    判断是否继续生成解决方案

    Args:
        state: Agent状态

    Returns:
        下一个节点的名称
    """
    if state.get("error"):
        return "handle_error"

    # 检查是否需要澄清（此时应该停止流程等待用户输入）
    if state.get("step") == "clarification_generated":
        return END

    return "generate_solution"


def should_end_workflow(state: AgentState) -> str:
    """
    判断是否结束工作流

    Args:
        state: Agent状态

    Returns:
        下一个节点的名称或END
    """
    if state.get("error"):
        return "handle_error"

    if state.get("solution_ready", False):
        return END

    return END


def create_agent_workflow() -> Callable:
    """
    创建Agent工作流

    Returns:
        编译后的工作流图
    """
    try:
        logger.info("开始创建Agent工作流")

        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("analyze_query", analyze_query)
        workflow.add_node("generate_clarification", generate_clarification)
        workflow.add_node("retrieve_knowledge", retrieve_knowledge)
        workflow.add_node("generate_solution", generate_solution)
        workflow.add_node("handle_error", handle_error)

        # 设置入口点
        workflow.set_entry_point("analyze_query")

        # 定义条件边
        workflow.add_conditional_edges(
            "analyze_query",
            should_generate_clarification,
            {
                "generate_clarification": "generate_clarification",
                "retrieve_knowledge": "retrieve_knowledge",
                "handle_error": "handle_error"
            }
        )

        workflow.add_conditional_edges(
            "generate_clarification",
            should_continue_to_solution,
            {
                "handle_error": "handle_error",
                END: END
            }
        )

        workflow.add_conditional_edges(
            "retrieve_knowledge",
            should_continue_to_solution,
            {
                "generate_solution": "generate_solution",
                "handle_error": "handle_error"
            }
        )

        workflow.add_conditional_edges(
            "generate_solution",
            should_end_workflow,
            {
                "handle_error": "handle_error",
                END: END
            }
        )

        # 错误处理节点总是结束
        workflow.add_edge("handle_error", END)

        # 编译工作流
        compiled_workflow = workflow.compile()

        logger.info("Agent工作流创建成功")
        return compiled_workflow

    except Exception as e:
        logger.error(f"创建Agent工作流失败: {str(e)}")
        raise


def create_response_processing_workflow() -> Callable:
    """
    创建用户响应处理工作流

    用于处理用户对澄清问题的回复，继续原有的诊断流程。

    Returns:
        编译后的工作流图
    """
    try:
        logger.info("开始创建响应处理工作流")

        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加节点（跳过分析，直接检索和生成解决方案）
        workflow.add_node("retrieve_knowledge", retrieve_knowledge)
        workflow.add_node("generate_solution", generate_solution)
        workflow.add_node("handle_error", handle_error)

        # 设置入口点
        workflow.set_entry_point("retrieve_knowledge")

        # 定义条件边
        workflow.add_conditional_edges(
            "retrieve_knowledge",
            should_continue_to_solution,
            {
                "generate_solution": "generate_solution",
                "handle_error": "handle_error"
            }
        )

        workflow.add_conditional_edges(
            "generate_solution",
            should_end_workflow,
            {
                "handle_error": "handle_error",
                END: END
            }
        )

        # 错误处理节点总是结束
        workflow.add_edge("handle_error", END)

        # 编译工作流
        compiled_workflow = workflow.compile()

        logger.info("响应处理工作流创建成功")
        return compiled_workflow

    except Exception as e:
        logger.error(f"创建响应处理工作流失败: {str(e)}")
        raise
