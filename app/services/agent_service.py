"""
IP智慧解答专家系统 - Agent服务

本模块实现AI Agent相关的异步任务处理。
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from rq import get_current_job
from app import create_app, db
from app.models.case import Case, Node, Edge
from app.services import get_task_queue
from app.services.task_monitor import with_monitoring_and_retry
from app.services.hybrid_retrieval import get_hybrid_retrieval, search_knowledge

logger = logging.getLogger(__name__)


# 临时的服务类定义（后续会在专门的模块中实现）
class LLMService:
    """大语言模型服务（占位符）"""
    def analyze_query(self, query: str) -> Dict[str, Any]:
        return _analyze_query_content(query)

    def generate_clarification(self, query: str, analysis: Dict, context: List) -> Dict[str, Any]:
        return _generate_clarification(query, analysis)

    def generate_solution(self, query: str, context: List, analysis: Dict) -> Dict[str, Any]:
        return _generate_solution(query, analysis)


class RetrievalService:
    """检索服务 - 使用混合检索算法"""
    def __init__(self):
        self.hybrid_retrieval = get_hybrid_retrieval()

    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """执行混合检索"""
        try:
            results = search_knowledge(query, filters=filters, top_k=10)
            logger.info(f"检索到 {len(results)} 个相关结果")
            return results
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []


@with_monitoring_and_retry(max_retries=3, retry_intervals=[10, 30, 60])
def analyze_user_query(case_id: str, node_id: str, query: str):
    """
    分析用户查询的异步任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        query: 用户查询内容
    """
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"开始分析用户查询: case_id={case_id}, node_id={node_id}")

            # 获取当前任务
            job = get_current_job()
            if job:
                job.meta['status'] = 'processing'
                job.meta['progress'] = 0
                job.save_meta()

            # 获取节点
            node = Node.query.get(node_id)
            if not node:
                raise Exception(f"节点 {node_id} 不存在")

            # 获取案例
            case = Case.query.get(case_id)
            if not case:
                raise Exception(f"案例 {case_id} 不存在")

            # 更新任务进度
            if job:
                job.meta['progress'] = 20
                job.save_meta()

            # 使用AI服务分析查询
            logger.info(f"开始AI分析用户查询: {query}")

            try:
                # 调用LLM服务进行查询分析
                llm_service = LLMService()
                analysis_result = llm_service.analyze_query(query)

                # 调用检索服务获取相关知识
                retrieval_service = RetrievalService()
                context = retrieval_service.search(query)

            except Exception as e:
                logger.warning(f"AI服务调用失败，使用模拟分析: {str(e)}")
                # 如果AI服务不可用，使用简单的查询分析逻辑
                analysis_result = _analyze_query_content(query)
                context = []

            # 更新任务进度
            if job:
                job.meta['progress'] = 60
                job.save_meta()

            # 根据分析结果决定下一步
            if analysis_result.get('need_more_info'):
                # 需要更多信息，生成追问
                try:
                    clarification = llm_service.generate_clarification(query, analysis_result, context)
                except:
                    clarification = _generate_clarification(query, analysis_result)

                node.type = 'AI_CLARIFICATION'
                node.title = '需要更多信息'
                node.status = 'AWAITING_USER_INPUT'
                node.content = {
                    'analysis': analysis_result.get('analysis'),
                    'suggestedQuestions': clarification.get('questions'),
                    'reasoning': clarification.get('reasoning')
                }
            else:
                # 可以直接提供解决方案
                try:
                    solution = llm_service.generate_solution(query, context, analysis_result)
                except:
                    solution = _generate_solution(query, analysis_result)

                node.type = 'SOLUTION'
                node.title = '解决方案'
                node.status = 'COMPLETED'
                node.content = {
                    'answer': solution.get('answer'),
                    'sources': solution.get('sources', []),
                    'commands': solution.get('commands', []),
                    'reasoning': solution.get('reasoning')
                }

            # 更新节点元数据
            if node.node_metadata is None:
                node.node_metadata = {}
            node.node_metadata.update({
                'processed_at': datetime.utcnow().isoformat(),
                'analysis_result': analysis_result,
                'context_count': len(context),
                'processing_time': time.time() - (job.started_at.timestamp() if job and job.started_at else time.time())
            })

            # 更新案例时间
            case.updated_at = datetime.utcnow()

            # 提交数据库更改
            db.session.commit()

            # 更新任务进度
            if job:
                job.meta['status'] = 'completed'
                job.meta['progress'] = 100
                job.save_meta()

            logger.info(f"用户查询分析完成: case_id={case_id}, node_id={node_id}")

        except Exception as e:
            # 错误处理
            logger.error(f"分析用户查询失败: {str(e)}")

            # 更新节点状态为错误
            try:
                node = Node.query.get(node_id)
                if node:
                    node.status = 'COMPLETED'
                    node.content = {
                        'error': '处理过程中发生错误，请重试',
                        'error_details': str(e)
                    }
                    db.session.commit()
            except:
                pass

            # 更新任务状态
            if job:
                job.meta['status'] = 'failed'
                job.meta['error'] = str(e)
                job.save_meta()

            raise


@with_monitoring_and_retry(max_retries=3, retry_intervals=[10, 30, 60])
def process_user_response(case_id: str, node_id: str, response_data: Dict[str, Any],
                         retrieval_weight: float = 0.7, filter_tags: Optional[List[str]] = None):
    """
    处理用户响应的异步任务

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
            # 获取当前任务
            job = get_current_job()
            if job:
                job.meta['status'] = 'processing'
                job.meta['progress'] = 0
                job.save_meta()

            # 获取节点
            node = Node.query.get(node_id)
            if not node:
                raise Exception(f"节点 {node_id} 不存在")

            # 获取案例
            case = Case.query.get(case_id)
            if not case:
                raise Exception(f"案例 {case_id} 不存在")

            app.logger.info(f"开始处理用户响应: case_id={case_id}")

            # 更新任务进度
            if job:
                job.meta['progress'] = 30
                job.save_meta()

            # 处理用户响应（模拟）
            processed_response = _process_response_content(response_data, retrieval_weight, filter_tags)

            # 更新任务进度
            if job:
                job.meta['progress'] = 70
                job.save_meta()

            # 生成最终解决方案
            solution = _generate_final_solution(case_id, processed_response)

            # 更新节点
            node.type = 'SOLUTION'
            node.title = '解决方案'
            node.status = 'COMPLETED'
            node.content = {
                'answer': solution.get('answer'),
                'steps': solution.get('steps'),
                'reasoning': solution.get('reasoning'),
                'confidence': solution.get('confidence', 0.8)
            }

            # 更新节点元数据
            if node.node_metadata is None:
                node.node_metadata = {}
            node.node_metadata.update({
                'processed_at': datetime.utcnow().isoformat(),
                'retrieval_weight': retrieval_weight,
                'filter_tags': filter_tags or [],
                'processing_time': time.time() - (job.started_at.timestamp() if job and job.started_at else time.time())
            })

            # 更新案例时间
            case.updated_at = datetime.utcnow()

            # 提交数据库更改
            db.session.commit()

            # 更新任务进度
            if job:
                job.meta['status'] = 'completed'
                job.meta['progress'] = 100
                job.save_meta()

            app.logger.info(f"用户响应处理完成: case_id={case_id}, node_id={node_id}")

        except Exception as e:
            # 错误处理
            app.logger.error(f"处理用户响应失败: {str(e)}")

            # 更新节点状态为错误
            try:
                node = Node.query.get(node_id)
                if node:
                    node.status = 'COMPLETED'
                    node.content = {
                        'error': '处理过程中发生错误，请重试',
                        'error_details': str(e)
                    }
                    db.session.commit()
            except:
                pass

            # 更新任务状态
            if job:
                job.meta['status'] = 'failed'
                job.meta['error'] = str(e)
                job.save_meta()

            raise

def _analyze_query_content(query):
    """分析查询内容（模拟实现）"""
    # 简单的关键词分析
    query_lower = query.lower()

    # 检查是否包含网络相关关键词
    network_keywords = ['网络', '连接', '路由', '交换', 'ip', 'ping', 'ospf', 'bgp']
    has_network_keywords = any(keyword in query_lower for keyword in network_keywords)

    # 检查查询的复杂度
    is_complex = len(query) > 50 or '?' in query or '如何' in query or '怎么' in query

    return {
        'category': 'network' if has_network_keywords else 'general',
        'complexity': 'high' if is_complex else 'low',
        'need_more_info': is_complex and len(query) < 30,  # 复杂但描述简单时需要更多信息
        'analysis': f"查询分析: 类别={'网络' if has_network_keywords else '通用'}, 复杂度={'高' if is_complex else '低'}"
    }

def _generate_clarification(query, analysis_result):
    """生成追问内容（模拟实现）"""
    category = analysis_result.get('category', 'general')

    if category == 'network':
        questions = [
            "请描述具体的网络拓扑结构",
            "问题出现的具体时间和频率是什么？",
            "使用的是什么品牌和型号的设备？",
            "有没有相关的错误日志或告警信息？"
        ]
    else:
        questions = [
            "请提供更详细的问题描述",
            "问题的具体表现是什么？",
            "之前是否尝试过解决方法？",
            "问题的影响范围有多大？"
        ]

    return {
        'questions': questions[:2],  # 只返回前两个问题
        'reasoning': f"基于{analysis_result.get('analysis', '')}，需要更多信息来提供准确的解决方案"
    }

def _generate_solution(query, analysis_result):
    """生成解决方案（模拟实现）"""
    category = analysis_result.get('category', 'general')

    if category == 'network':
        return {
            'answer': '基于您的网络问题描述，建议按以下步骤排查',
            'steps': [
                '1. 检查物理连接是否正常',
                '2. 验证IP配置是否正确',
                '3. 测试网络连通性（ping测试）',
                '4. 检查路由表配置'
            ],
            'reasoning': '这是网络问题的标准排查流程'
        }
    else:
        return {
            'answer': '基于您的问题描述，建议采用以下解决方案',
            'steps': [
                '1. 确认问题的具体表现',
                '2. 检查相关配置',
                '3. 尝试重启相关服务',
                '4. 如问题持续，请联系技术支持'
            ],
            'reasoning': '这是通用问题的处理方法'
        }

def _process_response_content(response_data, retrieval_weight, filter_tags):
    """处理响应内容（模拟实现）"""
    # 模拟处理用户的补充信息
    return {
        'processed_content': response_data,
        'retrieval_weight': retrieval_weight,
        'filter_tags': filter_tags or [],
        'processed_at': datetime.utcnow().isoformat()
    }

def _generate_final_solution(case_id, processed_response):
    """生成最终解决方案（模拟实现）"""
    return {
        'answer': '基于您提供的补充信息，这是针对性的解决方案',
        'steps': [
            '1. 根据补充信息调整配置',
            '2. 执行特定的修复步骤',
            '3. 验证问题是否解决',
            '4. 监控系统状态'
        ],
        'reasoning': '结合用户补充信息生成的定制化解决方案',
        'confidence': 0.85
    }


# 任务提交的便捷函数
def submit_query_analysis_task(case_id: str, node_id: str, query: str) -> str:
    """
    提交查询分析任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        query: 用户查询

    Returns:
        str: 任务ID
    """
    queue = get_task_queue()
    job = queue.enqueue(
        analyze_user_query,
        case_id,
        node_id,
        query,
        timeout='10m'  # 10分钟超时
    )

    logger.info(f"查询分析任务已提交: {job.id}")
    return job.id


def submit_response_processing_task(case_id: str, node_id: str, response_data: Dict[str, Any],
                                  retrieval_weight: float = 0.7,
                                  filter_tags: Optional[List[str]] = None) -> str:
    """
    提交响应处理任务

    Args:
        case_id: 案例ID
        node_id: 节点ID
        response_data: 用户响应数据
        retrieval_weight: 检索权重
        filter_tags: 过滤标签

    Returns:
        str: 任务ID
    """
    queue = get_task_queue()
    job = queue.enqueue(
        process_user_response,
        case_id,
        node_id,
        response_data,
        retrieval_weight,
        filter_tags,
        timeout='10m'  # 10分钟超时
    )

    logger.info(f"响应处理任务已提交: {job.id}")
    return job.id


def get_agent_task_status(job_id: str) -> Dict[str, Any]:
    """
    获取Agent任务状态

    Args:
        job_id: 任务ID

    Returns:
        Dict: 任务状态信息
    """
    from app.services.task_monitor import TaskMonitor
    return TaskMonitor.get_task_status(job_id)
