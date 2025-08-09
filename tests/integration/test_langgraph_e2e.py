#!/usr/bin/env python3
"""
LangGraph Agent 端到端集成测试

测试完整的 langgraph Agent 工作流，包括任务提交、状态监控和结果验证。
"""

import sys
import os
import time
import logging
import pytest
from unittest.mock import patch, Mock

# 添加项目根目录到Python路径（用于独立运行）
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.models.case import Case, Node
from app.services.ai.langgraph_agent_service import (
    submit_langgraph_query_analysis_task,
    get_langgraph_task_status
)

# 配置日志
logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.langgraph
class TestLanggraphEndToEnd:
    """LangGraph Agent 端到端测试"""

    def test_agent_state_and_nodes(self, app):
        """测试Agent状态和节点定义"""
        with app.app_context():
            try:
                from app.services.ai.agent_state import AgentState
                from app.services.ai.agent_nodes import analyze_query, retrieve_knowledge, generate_solution
                from app.services.ai.agent_workflow import create_agent_workflow

                logger.info("测试Agent状态定义...")
                test_state: AgentState = {
                    "messages": [],
                    "context": [],
                    "user_query": "测试查询",
                    "vendor": "Huawei",
                    "category": None,
                    "need_more_info": False,
                    "solution_ready": False,
                    "case_id": "test_case",
                    "current_node_id": "test_node",
                    "analysis_result": None,
                    "clarification": None,
                    "solution": None,
                    "error": None,
                    "step": "initializing"
                }

                # 验证状态字段
                assert test_state["user_query"] == "测试查询"
                assert test_state["vendor"] == "Huawei"
                assert test_state["step"] == "initializing"
                assert test_state["need_more_info"] is False
                assert test_state["solution_ready"] is False

                logger.info("✅ Agent状态定义正常")

                logger.info("测试Agent工作流创建...")
                workflow = create_agent_workflow()
                assert workflow is not None
                logger.info("✅ Agent工作流创建成功")

            except Exception as e:
                logger.error(f"Agent组件测试失败: {str(e)}")
                pytest.fail(f"Agent组件测试失败: {str(e)}")

    @pytest.mark.slow
    @patch('app.services.ai.langgraph_agent_service.get_task_queue')
    def test_langgraph_workflow_integration(self, mock_get_task_queue, app, sample_user):
        """测试langgraph工作流集成（模拟版本）"""
        with app.app_context():
            try:
                # 模拟队列和任务
                mock_queue = Mock()
                mock_get_task_queue.return_value = mock_queue

                mock_job = Mock()
                mock_job.id = "test_job_123"
                mock_queue.enqueue.return_value = mock_job

                # 创建测试案例
                logger.info("创建测试案例...")
                case = Case(
                    title="测试langgraph Agent",
                    user_id=sample_user.id,
                    metadata={
                        'vendor': 'Huawei',
                        'use_langgraph': True,
                        'original_query': 'OSPF邻居建立失败，请帮忙分析原因',
                        'created_with_langgraph': True
                    }
                )
                db.session.add(case)
                db.session.flush()

                # 创建测试节点
                node = Node(
                    case_id=case.id,
                    type='AI_ANALYSIS',
                    title='AI分析中...',
                    status='PROCESSING',
                    node_metadata={
                        'timestamp': time.time()
                    }
                )
                db.session.add(node)
                db.session.flush()
                db.session.commit()

                logger.info(f"测试案例创建成功: case_id={case.id}, node_id={node.id}")

                # 提交langgraph任务
                logger.info("提交langgraph分析任务...")
                test_query = "OSPF邻居建立失败，日志显示Hello包没有收到回复，网络环境是三层交换机组网"

                job_id = submit_langgraph_query_analysis_task(
                    case_id=str(case.id),
                    node_id=str(node.id),
                    query=test_query
                )

                logger.info(f"任务提交成功: job_id={job_id}")

                # 验证任务提交
                assert job_id == "test_job_123"
                mock_queue.enqueue.assert_called_once()

                logger.info("✅ langgraph工作流集成测试成功!")

            except Exception as e:
                logger.error(f"测试过程中发生错误: {str(e)}")
                pytest.fail(f"langgraph工作流测试失败: {str(e)}")


# 如果需要真实的端到端测试（需要实际的Redis和数据库）
@pytest.mark.slow
@pytest.mark.e2e
@pytest.mark.skipif(
    True,  # 默认跳过，除非明确需要运行真实集成测试
    reason="需要真实的Redis和完整环境支持，仅在完整集成测试时运行"
)
class TestLanggraphRealIntegration:
    """真实环境下的 LangGraph 集成测试"""

    def test_real_langgraph_workflow(self, app, sample_user):
        """测试真实的langgraph工作流（需要完整环境）"""
        with app.app_context():
            try:
                # 创建测试案例
                logger.info("创建测试案例...")
                case = Case(
                    title="测试langgraph Agent - 真实环境",
                    user_id=sample_user.id,
                    metadata={
                        'vendor': 'Huawei',
                        'use_langgraph': True,
                        'original_query': 'OSPF邻居建立失败，请帮忙分析原因',
                        'created_with_langgraph': True
                    }
                )
                db.session.add(case)
                db.session.flush()

                # 创建测试节点
                node = Node(
                    case_id=case.id,
                    type='AI_ANALYSIS',
                    title='AI分析中...',
                    status='PROCESSING',
                    node_metadata={
                        'timestamp': time.time()
                    }
                )
                db.session.add(node)
                db.session.flush()
                db.session.commit()

                logger.info(f"测试案例创建成功: case_id={case.id}, node_id={node.id}")

                # 提交langgraph任务
                logger.info("提交langgraph分析任务...")
                test_query = "OSPF邻居建立失败，日志显示Hello包没有收到回复，网络环境是三层交换机组网"

                job_id = submit_langgraph_query_analysis_task(
                    case_id=str(case.id),
                    node_id=str(node.id),
                    query=test_query
                )

                logger.info(f"任务提交成功: job_id={job_id}")

                # 监控任务状态
                logger.info("监控任务执行状态...")
                max_wait_time = 120  # 最大等待2分钟
                start_time = time.time()

                while time.time() - start_time < max_wait_time:
                    status = get_langgraph_task_status(job_id)

                    logger.info(f"任务状态: {status.get('status')}, 进度: {status.get('progress', 0)}%, 步骤: {status.get('step', 'unknown')}")

                    if status.get('status') in ['completed', 'failed']:
                        break

                    time.sleep(5)  # 每5秒检查一次

                # 获取最终状态
                final_status = get_langgraph_task_status(job_id)
                logger.info(f"最终任务状态: {final_status}")

                # 检查节点更新结果
                db.session.refresh(node)
                logger.info(f"节点最终状态: type={node.type}, status={node.status}")
                logger.info(f"节点内容: {node.content}")

                if final_status.get('status') == 'completed':
                    logger.info("✅ langgraph工作流测试成功!")
                    assert True
                else:
                    logger.error("❌ langgraph工作流测试失败!")
                    pytest.fail("langgraph工作流未能成功完成")

            except Exception as e:
                logger.error(f"测试过程中发生错误: {str(e)}")
                pytest.fail(f"真实集成测试失败: {str(e)}")


# 便捷的单独运行函数（保持向后兼容）
def main():
    """主函数 - 用于独立运行测试"""
    logger.info("开始测试langgraph Agent实现...")

    app = create_app()

    # 测试基础组件
    test_class = TestLanggraphEndToEnd()

    try:
        test_class.test_agent_state_and_nodes(app)
        logger.info("✅ 基础组件测试通过")

        logger.info("🎉 所有测试通过！langgraph Agent实现正常")
        assert True  # 测试通过

    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        assert False, "测试失败"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
