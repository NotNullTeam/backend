"""
langgraph Agent 基础组件测试

测试 langgraph Agent 的核心组件，包括状态定义、节点函数和工作流创建。
"""

import pytest
from typing import Dict, Any

from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import (
    analyze_query, generate_clarification,
    retrieve_knowledge, generate_solution, handle_error
)
from app.services.ai.agent_workflow import (
    create_agent_workflow, create_response_processing_workflow
)


class TestLanggraphDependencies:
    """测试 langgraph 相关依赖"""

    def test_langgraph_import(self):
        """测试 langgraph 模块导入"""
        import langgraph
        from langgraph.graph import StateGraph, END
        assert StateGraph is not None
        assert END is not None

    def test_langchain_openai_import(self):
        """测试 langchain_openai 导入"""
        from langchain_openai import ChatOpenAI
        assert ChatOpenAI is not None


class TestAgentState:
    """测试 Agent 状态定义"""

    def test_agent_state_creation(self):
        """测试 AgentState 创建"""
        test_state: AgentState = {
            "messages": [],
            "context": [],
            "user_query": "测试OSPF问题",
            "vendor": "Huawei",
            "category": None,
            "need_more_info": False,
            "solution_ready": False,
            "case_id": "test_case_123",
            "current_node_id": "test_node_456",
            "analysis_result": None,
            "clarification": None,
            "solution": None,
            "error": None,
            "step": "initializing"
        }

        assert test_state["user_query"] == "测试OSPF问题"
        assert test_state["vendor"] == "Huawei"
        assert test_state["step"] == "initializing"
        assert test_state["need_more_info"] is False
        assert test_state["solution_ready"] is False


class TestAgentNodes:
    """测试 Agent 节点函数"""

    def test_node_function_signatures(self):
        """测试节点函数签名"""
        import inspect

        functions = [
            ("analyze_query", analyze_query),
            ("generate_clarification", generate_clarification),
            ("retrieve_knowledge", retrieve_knowledge),
            ("generate_solution", generate_solution),
            ("handle_error", handle_error)
        ]

        for name, func in functions:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())

            # 所有节点函数都应该接受 AgentState 参数
            assert len(params) == 1, f"{name}应该只有一个参数"
            assert params[0] == "state", f"{name}的参数应该叫state"

            # 检查返回类型注解
            return_annotation = sig.return_annotation
            if return_annotation != inspect.Signature.empty:
                assert return_annotation == AgentState


class TestAgentWorkflow:
    """测试 Agent 工作流"""

    def test_create_agent_workflow(self):
        """测试创建 Agent 工作流"""
        workflow = create_agent_workflow()
        assert workflow is not None
        assert str(type(workflow)) == "<class 'langgraph.graph.state.CompiledStateGraph'>"

    def test_create_response_processing_workflow(self):
        """测试创建响应处理工作流"""
        response_workflow = create_response_processing_workflow()
        assert response_workflow is not None
        assert str(type(response_workflow)) == "<class 'langgraph.graph.state.CompiledStateGraph'>"


class TestWorkflowLogic:
    """测试工作流逻辑"""

    def test_workflow_scenarios(self):
        """测试工作流场景"""
        from app.services.ai.agent_workflow import create_agent_workflow

        # 创建工作流
        workflow = create_agent_workflow()

        # 测试场景1：模糊查询
        initial_state_1: AgentState = {
            "messages": [],
            "context": [],
            "user_query": "网络有问题",  # 模糊查询
            "vendor": "Huawei",
            "category": None,
            "need_more_info": False,
            "solution_ready": False,
            "case_id": "test_case_1",
            "current_node_id": "test_node_1",
            "analysis_result": None,
            "clarification": None,
            "solution": None,
            "error": None,
            "step": "initializing"
        }

        assert initial_state_1["user_query"] == "网络有问题"
        assert initial_state_1["step"] == "initializing"

        # 测试场景2：详细查询
        initial_state_2: AgentState = {
            "messages": [],
            "context": [],
            "user_query": "OSPF邻居建立失败，日志显示Hello包超时，网络环境是三层交换机组网，使用华为S5700设备",
            "vendor": "Huawei",
            "category": None,
            "need_more_info": False,
            "solution_ready": False,
            "case_id": "test_case_2",
            "current_node_id": "test_node_2",
            "analysis_result": None,
            "clarification": None,
            "solution": None,
            "error": None,
            "step": "initializing"
        }

        assert "OSPF邻居建立失败" in initial_state_2["user_query"]
        assert initial_state_2["vendor"] == "Huawei"
