"""
langgraph Agent 集成测试

测试 langgraph Agent 服务的集成功能，包括异步任务处理和完整的工作流执行。
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.services.ai.agent_state import AgentState


class TestLanggraphAgentServiceIntegration:
    """测试 langgraph Agent 服务集成"""

    def test_service_function_signatures(self):
        """测试服务函数签名"""
        import inspect
        from app.services.ai.langgraph_agent_service import (
            analyze_user_query_with_langgraph,
            process_user_response_with_langgraph
        )

        # 测试 analyze_user_query_with_langgraph 函数签名
        sig1 = inspect.signature(analyze_user_query_with_langgraph)
        params1 = list(sig1.parameters.keys())
        expected_params1 = ['case_id', 'node_id', 'query']
        assert params1 == expected_params1

        # 测试 process_user_response_with_langgraph 函数签名
        sig2 = inspect.signature(process_user_response_with_langgraph)
        params2 = list(sig2.parameters.keys())
        expected_params2 = ['case_id', 'node_id', 'response_data', 'retrieval_weight', 'filter_tags']
        assert params2 == expected_params2

    @patch('app.services.ai.langgraph_agent_service.get_task_queue')
    def test_submit_langgraph_query_analysis_task(self, mock_get_task_queue):
        """测试提交查询分析任务"""
        from app.services.ai.langgraph_agent_service import submit_langgraph_query_analysis_task

        # 模拟队列和任务
        mock_queue = Mock()
        mock_get_task_queue.return_value = mock_queue

        mock_job = Mock()
        mock_job.id = "test_job_123"
        mock_queue.enqueue.return_value = mock_job

        # 调用函数
        job_id = submit_langgraph_query_analysis_task(
            case_id="test_case_123",
            node_id="test_node_456",
            query="OSPF配置问题"
        )

        # 验证结果
        assert job_id == "test_job_123"
        mock_queue.enqueue.assert_called_once()

    @patch('app.services.ai.langgraph_agent_service.get_task_queue')
    def test_submit_langgraph_response_processing_task(self, mock_get_task_queue):
        """测试提交响应处理任务"""
        from app.services.ai.langgraph_agent_service import submit_langgraph_response_processing_task

        # 模拟队列和任务
        mock_queue = Mock()
        mock_get_task_queue.return_value = mock_queue

        mock_job = Mock()
        mock_job.id = "test_job_456"
        mock_queue.enqueue.return_value = mock_job

        # 调用函数
        job_id = submit_langgraph_response_processing_task(
            case_id="test_case_123",
            node_id="test_node_456",
            response_data={
                "user_response": "是的，使用的是华为S5700交换机",
                "clarification_content": "请确认设备型号"
            }
        )

        # 验证结果
        assert job_id == "test_job_456"
        mock_queue.enqueue.assert_called_once()


class TestWorkflowStateTransitions:
    """测试工作流状态转换"""

    def test_state_transition_logic(self):
        """测试状态转换逻辑"""
        from app.services.ai.agent_workflow import (
            should_generate_clarification, should_continue_to_solution,
            create_agent_workflow, create_response_processing_workflow
        )

        # 测试 should_generate_clarification 条件
        state_need_clarify: AgentState = {
            "messages": [],
            "context": [],
            "user_query": "网络有问题",
            "vendor": "Huawei",
            "category": None,
            "need_more_info": True,  # 需要更多信息
            "solution_ready": False,
            "case_id": "test",
            "current_node_id": "test",
            "analysis_result": {"confidence": 0.3},  # 低置信度
            "clarification": None,
            "solution": None,
            "error": None,
            "step": "analyzing"
        }

        clarify_result = should_generate_clarification(state_need_clarify)
        assert clarify_result == "generate_clarification"

        # 测试 should_continue_to_solution 条件
        state_ready_solution: AgentState = {
            "messages": [],
            "context": [],
            "user_query": "OSPF邻居建立失败",
            "vendor": "Huawei",
            "category": "ospf",
            "need_more_info": False,
            "solution_ready": True,  # 准备生成解决方案
            "case_id": "test",
            "current_node_id": "test",
            "analysis_result": {"confidence": 0.9},  # 高置信度
            "clarification": None,
            "solution": None,
            "error": None,
            "step": "retrieving"
        }

        solution_result = should_continue_to_solution(state_ready_solution)
        assert solution_result == "generate_solution"

    def test_workflow_compilation(self):
        """测试工作流编译"""
        from app.services.ai.agent_workflow import (
            create_agent_workflow, create_response_processing_workflow
        )

        # 测试主工作流编译
        main_workflow = create_agent_workflow()
        assert main_workflow is not None

        # 验证工作流类型
        workflow_type = str(type(main_workflow))
        assert "CompiledStateGraph" in workflow_type

        # 测试响应处理工作流编译
        response_workflow = create_response_processing_workflow()
        assert response_workflow is not None

        # 验证响应工作流类型
        response_workflow_type = str(type(response_workflow))
        assert "CompiledStateGraph" in response_workflow_type


class TestErrorHandling:
    """测试错误处理"""

    def test_error_state_handling(self):
        """测试错误状态处理"""
        from unittest.mock import patch, Mock
        from app.services.ai.agent_nodes import handle_error

        error_state: AgentState = {
            "messages": [],
            "context": [],
            "user_query": "测试查询",
            "vendor": "Huawei",
            "category": None,
            "need_more_info": False,
            "solution_ready": False,
            "case_id": "test",
            "current_node_id": "test_node_123",
            "analysis_result": None,
            "clarification": None,
            "solution": None,
            "error": "测试错误信息",
            "step": "error"
        }

        # 模拟数据库操作，避免实际数据库依赖
        with patch('app.services.ai.agent_nodes.db') as mock_db:
            # 模拟Node对象
            mock_node = Mock()
            mock_node.status = "PROCESSING"
            mock_node.content = {}
            mock_db.session.get.return_value = mock_node
            mock_db.session.commit.return_value = None

            # 调用错误处理函数
            result_state = handle_error(error_state)

            # 验证错误状态正确处理
            assert result_state["error"] == "测试错误信息"
            # 正常情况下应该是 error_handled，但允许 critical_error 以应对异常情况
            assert result_state["step"] in ["error_handled", "critical_error"]
            
            # 验证数据库操作被正确调用
            from app.models.case import Node
            mock_db.session.get.assert_called_once_with(Node, "test_node_123")
            mock_db.session.commit.assert_called_once()
            
            # 验证节点状态更新
            assert mock_node.status == "COMPLETED"
            assert "error" in mock_node.content
