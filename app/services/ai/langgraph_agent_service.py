"""
LangGraph Agent服务

使用langgraph实现的智能对话Agent服务，替代原有的简单状态处理逻辑。
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from rq import get_current_job
from app import create_app, db
from app.models.case import Case, Node, Edge
from app.services import get_task_queue
from app.services.infrastructure.task_monitor import with_monitoring_and_retry
from app.services.ai.agent_workflow import create_agent_workflow, create_response_processing_workflow
from app.services.ai.agent_state import AgentState
from app.services.ai.agent_service import RetrievalService
from app.utils.monitoring import monitor_performance

logger = logging.getLogger(__name__)


@with_monitoring_and_retry(max_retries=3, retry_intervals=[10, 30, 60])
def analyze_user_query_with_langgraph(case_id: str, node_id: str, query: str):
    """
    使用langgraph分析用户查询的异步任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        query: 用户查询内容
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"开始使用langgraph分析用户查询: case_id={case_id}, node_id={node_id}")

            # 获取当前任务
            job = get_current_job()
            if job:
                job.meta['status'] = 'processing'
                job.meta['progress'] = 0
                job.meta['step'] = 'initializing'
                job.save_meta()

            # 获取节点
            node = db.session.get(Node, node_id)
            if not node:
                raise Exception(f"节点 {node_id} 不存在")

            # 获取案例
            case = db.session.get(Case, case_id)
            if not case:
                raise Exception(f"案例 {case_id} 不存在")

            # 更新任务进度
            if job:
                job.meta['progress'] = 10
                job.meta['step'] = 'creating_workflow'
                job.save_meta()

            # 创建Agent工作流
            try:
                agent_workflow = create_agent_workflow()
                logger.info("Agent工作流创建成功")
            except Exception as e:
                logger.error(f"创建Agent工作流失败: {str(e)}")
                raise Exception(f"无法创建Agent工作流: {str(e)}")

            # 更新任务进度
            if job:
                job.meta['progress'] = 20
                job.meta['step'] = 'initializing_state'
                job.save_meta()

            # 获取案例相关信息（设备厂商等）
            vendor = case.metadata.get('vendor') if case.metadata else None

            # 初始化Agent状态
            initial_state: AgentState = {
                "messages": [],
                "context": [],
                "user_query": query,
                "vendor": vendor,
                "category": None,
                "need_more_info": False,
                "solution_ready": False,
                "case_id": case_id,
                "current_node_id": node_id,
                "analysis_result": None,
                "clarification": None,
                "solution": None,
                "error": None,
                "step": "initializing"
            }

            # 更新任务进度
            if job:
                job.meta['progress'] = 30
                job.meta['step'] = 'executing_workflow'
                job.save_meta()

            # 执行Agent工作流
            logger.info("开始执行Agent工作流")
            final_state = agent_workflow.invoke(initial_state)

            # 更新任务进度
            if job:
                job.meta['progress'] = 90
                job.meta['step'] = 'finalizing'
                job.save_meta()

            # 记录工作流执行结果
            logger.info(f"Agent工作流执行完成，最终步骤: {final_state.get('step')}")

            # 检查是否有错误
            if final_state.get("error"):
                logger.error(f"Agent工作流执行出错: {final_state['error']}")
                raise Exception(final_state["error"])

            # 更新案例时间
            case.updated_at = datetime.utcnow()

            # 更新案例元数据
            if case.metadata is None:
                case.metadata = {}
            case.metadata.update({
                'last_workflow_step': final_state.get('step'),
                'workflow_executed_at': datetime.utcnow().isoformat(),
                'need_more_info': final_state.get('need_more_info', False),
                'solution_ready': final_state.get('solution_ready', False)
            })

            # 提交数据库更改
            db.session.commit()

            # 更新任务进度
            if job:
                job.meta['status'] = 'completed'
                job.meta['progress'] = 100
                job.meta['step'] = 'completed'
                job.meta['final_state'] = {
                    'step': final_state.get('step'),
                    'need_more_info': final_state.get('need_more_info'),
                    'solution_ready': final_state.get('solution_ready'),
                    'category': final_state.get('category')
                }
                job.save_meta()

            logger.info(f"langgraph用户查询分析完成: case_id={case_id}, node_id={node_id}")

        except Exception as e:
            # 错误处理
            logger.error(f"langgraph分析用户查询失败: {str(e)}")

            # 更新节点状态为错误
            try:
                node = db.session.get(Node, node_id)
                if node:
                    node.status = 'COMPLETED'
                    node.content = {
                        'error': 'Agent处理过程中发生错误，请重试',
                        'error_details': str(e),
                        'workflow_type': 'langgraph'
                    }
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"更新数据库失败: {str(db_error)}")

            # 更新任务状态
            job = get_current_job()
            if job:
                job.meta['status'] = 'failed'
                job.meta['error'] = str(e)
                job.meta['step'] = 'error'
                job.save_meta()

            raise


@with_monitoring_and_retry(max_retries=3, retry_intervals=[10, 30, 60])
def process_user_response_with_langgraph(case_id: str, node_id: str, response_data: Dict[str, Any],
                                       retrieval_weight: float = 0.7, filter_tags: Optional[List[str]] = None):
    """
    使用langgraph处理用户响应的异步任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        response_data: 用户响应数据
        retrieval_weight: 检索权重
        filter_tags: 过滤标签
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"开始使用langgraph处理用户响应: case_id={case_id}, node_id={node_id}")

            # 获取当前任务
            job = get_current_job()
            if job:
                job.meta['status'] = 'processing'
                job.meta['progress'] = 0
                job.meta['step'] = 'initializing'
                job.save_meta()

            # 获取节点
            node = db.session.get(Node, node_id)
            if not node:
                raise Exception(f"节点 {node_id} 不存在")

            # 获取案例
            case = db.session.get(Case, case_id)
            if not case:
                raise Exception(f"案例 {case_id} 不存在")

            # 更新任务进度
            if job:
                job.meta['progress'] = 10
                job.meta['step'] = 'creating_response_workflow'
                job.save_meta()

            # 创建响应处理工作流
            try:
                response_workflow = create_response_processing_workflow()
                logger.info("响应处理工作流创建成功")
            except Exception as e:
                logger.error(f"创建响应处理工作流失败: {str(e)}")
                raise Exception(f"无法创建响应处理工作流: {str(e)}")

            # 更新任务进度
            if job:
                job.meta['progress'] = 20
                job.meta['step'] = 'preparing_enhanced_query'
                job.save_meta()

            # 构建增强的查询（结合原始问题和用户补充信息）
            original_query = case.original_query if hasattr(case, 'original_query') else ""
            user_response = response_data.get('response', '')
            enhanced_query = f"原始问题: {original_query}\n\n补充信息: {user_response}"

            # 获取案例相关信息
            vendor = case.metadata.get('vendor') if case.metadata else None

            # 初始化Agent状态（跳过分析步骤，直接进入检索和解决方案生成）
            initial_state: AgentState = {
                "messages": [],
                "context": [],
                "user_query": enhanced_query,
                "vendor": vendor,
                "category": case.metadata.get('category') if case.metadata else None,
                "need_more_info": False,  # 已经获得用户响应，不再需要更多信息
                "solution_ready": False,
                "case_id": case_id,
                "current_node_id": node_id,
                "analysis_result": None,
                "clarification": None,
                "solution": None,
                "error": None,
                "step": "user_response_received"
            }

            # 更新任务进度
            if job:
                job.meta['progress'] = 30
                job.meta['step'] = 'executing_response_workflow'
                job.save_meta()

            # 执行响应处理工作流
            logger.info("开始执行响应处理工作流")
            final_state = response_workflow.invoke(initial_state)

            # 更新任务进度
            if job:
                job.meta['progress'] = 90
                job.meta['step'] = 'finalizing'
                job.save_meta()

            # 记录工作流执行结果
            logger.info(f"响应处理工作流执行完成，最终步骤: {final_state.get('step')}")

            # 检查是否有错误
            if final_state.get("error"):
                logger.error(f"响应处理工作流执行出错: {final_state['error']}")
                raise Exception(final_state["error"])

            # 更新案例时间
            case.updated_at = datetime.utcnow()

            # 更新案例元数据
            if case.metadata is None:
                case.metadata = {}
            case.metadata.update({
                'last_response_processed_at': datetime.utcnow().isoformat(),
                'response_workflow_step': final_state.get('step'),
                'solution_ready': final_state.get('solution_ready', False),
                'retrieval_weight': retrieval_weight,
                'filter_tags': filter_tags or []
            })

            # 提交数据库更改
            db.session.commit()

            # 更新任务进度
            if job:
                job.meta['status'] = 'completed'
                job.meta['progress'] = 100
                job.meta['step'] = 'completed'
                job.meta['final_state'] = {
                    'step': final_state.get('step'),
                    'solution_ready': final_state.get('solution_ready'),
                    'category': final_state.get('category')
                }
                job.save_meta()

            logger.info(f"langgraph用户响应处理完成: case_id={case_id}, node_id={node_id}")

        except Exception as e:
            # 错误处理
            logger.error(f"langgraph处理用户响应失败: {str(e)}")

            # 更新节点状态为错误
            try:
                node = db.session.get(Node, node_id)
                if node:
                    node.status = 'COMPLETED'
                    node.content = {
                        'error': '响应处理过程中发生错误，请重试',
                        'error_details': str(e),
                        'workflow_type': 'langgraph_response'
                    }
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"更新数据库失败: {str(db_error)}")

            # 更新任务状态
            job = get_current_job()
            if job:
                job.meta['status'] = 'failed'
                job.meta['error'] = str(e)
                job.meta['step'] = 'error'
                job.save_meta()

            raise


def submit_langgraph_query_analysis_task(case_id: str, node_id: str, query: str) -> str:
    """
    提交langgraph查询分析任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        query: 用户查询

    Returns:
        任务ID
    """
    queue = get_task_queue()
    job = queue.enqueue(
        analyze_user_query_with_langgraph,
        case_id, node_id, query,
        timeout='5m',
        job_timeout='10m'
    )
    logger.info(f"已提交langgraph查询分析任务: {job.id}")
    return job.id


def submit_langgraph_response_processing_task(case_id: str, node_id: str, response_data: Dict[str, Any],
                                            retrieval_weight: float = 0.7,
                                            filter_tags: Optional[List[str]] = None) -> str:
    """
    提交langgraph响应处理任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        response_data: 响应数据
        retrieval_weight: 检索权重
        filter_tags: 过滤标签

    Returns:
        任务ID
    """
    queue = get_task_queue()
    job = queue.enqueue(
        process_user_response_with_langgraph,
        case_id, node_id, response_data, retrieval_weight, filter_tags,
        timeout='5m',
        job_timeout='10m'
    )
    logger.info(f"已提交langgraph响应处理任务: {job.id}")
    return job.id


def get_langgraph_task_status(job_id: str) -> Dict[str, Any]:
    """
    获取langgraph任务状态

    Args:
        job_id: 任务ID

    Returns:
        任务状态字典
    """
    try:
        queue = get_task_queue()
        job = queue.fetch_job(job_id)

        if not job:
            return {
                'status': 'not_found',
                'message': '任务不存在'
            }

        status_info = {
            'job_id': job_id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        }

        # 添加任务元数据
        if hasattr(job, 'meta') and job.meta:
            status_info.update({
                'progress': job.meta.get('progress', 0),
                'step': job.meta.get('step', 'unknown'),
                'workflow_type': 'langgraph'
            })

            # 如果任务完成，添加最终状态
            if job.meta.get('status') == 'completed':
                status_info['final_state'] = job.meta.get('final_state', {})

            # 如果任务失败，添加错误信息
            if job.meta.get('status') == 'failed':
                status_info['error'] = job.meta.get('error', '未知错误')

        # 添加结果信息
        if job.result:
            status_info['result'] = job.result

        return status_info

    except Exception as e:
        logger.error(f"获取langgraph任务状态失败: {str(e)}")
        return {
            'status': 'error',
            'message': f'获取任务状态失败: {str(e)}'
        }
