"""
IP智慧解答专家系统 - 文档解析服务

专注于阿里云IDP服务，简化备用方案。
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from rq import get_current_job
from app import create_app, db
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.services.idp_service import IDPService
from app.services.semantic_splitter import SemanticSplitter
from app.services.vector_service import VectorService
from app.services.task_monitor import with_monitoring_and_retry

logger = logging.getLogger(__name__)


@with_monitoring_and_retry(max_retries=3, retry_intervals=[10, 30, 60])
def parse_document(job_id: str):
    """
    解析文档的异步任务 - 专注于IDP服务

    Args:
        job_id: 解析任务ID
    """
    app = create_app()
    with app.app_context():
        job = ParsingJob.query.get(job_id)
        if not job:
            logger.error(f"解析任务未找到: {job_id}")
            return

        document = KnowledgeDocument.query.get(job.document_id)
        if not document:
            logger.error(f"知识文档未找到: {job.document_id}")
            return

        try:
            logger.info(f"开始解析文档: {document.original_filename}")

            # 更新状态
            job.status = 'PROCESSING'
            job.started_at = datetime.utcnow()
            document.status = 'PARSING'
            document.progress = 10
            db.session.commit()

            # 优先使用阿里云IDP服务
            try:
                logger.info("调用阿里云IDP服务解析文档...")
                idp_service = IDPService()

                # 验证文件格式
                if not idp_service.validate_file_format(document.file_path):
                    raise Exception(f"不支持的文件格式: {document.file_path}")

                parsed_result = idp_service.parse_document(document.file_path)
                document.progress = 50
                db.session.commit()

                logger.info("IDP服务解析完成")

            except Exception as e:
                logger.warning(f"IDP服务解析失败: {str(e)}")

                # 简化的备用方案：只支持纯文本文件
                file_ext = os.path.splitext(document.file_path)[1].lower()
                if file_ext in ['.txt', '.md']:
                    parsed_result = _simple_text_extraction(document.file_path)
                    document.progress = 50
                    db.session.commit()
                    logger.info("使用简单文本提取作为备用方案")
                else:
                    # 对于复杂文档，直接失败并提示用户
                    raise Exception(f"文档格式 {file_ext} 需要使用阿里云IDP服务解析，请检查服务配置或网络连接")

            # 语义切分
            try:
                logger.info("开始语义切分...")
                splitter = SemanticSplitter(max_chunk_size=1000, overlap=100)
                chunks = splitter.split_document(parsed_result, document)

                # 为每个chunk添加元数据
                for chunk in chunks:
                    chunk.update(splitter.extract_metadata(chunk, document))

                document.progress = 70
                db.session.commit()

                logger.info(f"语义切分完成，生成 {len(chunks)} 个文档块")

            except Exception as e:
                logger.error(f"语义切分失败: {str(e)}")
                raise

            # 向量化并存储
            try:
                logger.info("开始向量化和存储...")
                vector_service = VectorService()
                vector_service.index_chunks(chunks, document.id)
                document.progress = 90
                db.session.commit()

                logger.info("向量化和存储完成")

            except Exception as e:
                logger.warning(f"向量化失败，但文档解析已完成: {str(e)}")
                # 向量化失败不影响主流程

            # 更新状态
            job.status = 'COMPLETED'
            job.completed_at = datetime.utcnow()
            job.result_data = {
                'chunks_count': len(chunks),
                'text_length': sum(len(chunk.get('content', '')) for chunk in chunks),
                'vendor': document.vendor,
                'categories': list(set(chunk.get('category', '其他') for chunk in chunks if chunk.get('category'))),
                'processed_with_idp': 'IDP服务' if 'layouts' in parsed_result else '简单文本提取'
            }
            document.status = 'INDEXED'
            document.progress = 100
            document.processed_at = datetime.utcnow()

            db.session.commit()
            logger.info(f"文档解析任务完成: {document.original_filename}")

        except Exception as e:
            # 错误处理
            logger.error(f"文档解析任务失败: {str(e)}")
            job.status = 'FAILED'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            document.status = 'FAILED'
            document.error_message = str(e)

            db.session.commit()
            raise


def _simple_text_extraction(file_path: str) -> Dict[str, Any]:
    """
    简化的文本提取（仅支持纯文本文件）

    Args:
        file_path: 文件路径

    Returns:
        Dict: 兼容IDP格式的解析结果
    """
    try:
        # 检查文件扩展名
        if not file_path.lower().endswith(('.txt', '.md', '.markdown')):
            return {
                'layouts': [],
                'markdown': '',
                'content': '不支持的文件格式',
                'format': 'unsupported',
                'source': 'simple_extraction'
            }

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 创建简单的layouts结构，兼容语义切分器
        layouts = [{
            'text': content,
            'type': 'text',
            'subType': 'content',
            'pageNum': [1],
            'uniqueId': 'simple_extraction_0',
            'markdownContent': content,
            'x': 0, 'y': 0, 'w': 100, 'h': 100
        }]

        return {
            'layouts': layouts,
            'markdown': content,
            'content': content,
            'format': 'text',
            'source': 'simple_extraction'
        }

    except Exception as e:
        logger.error(f"文本提取失败: {str(e)}")
        return {
            'layouts': [],
            'markdown': '',
            'content': '不支持的文件格式',
            'format': 'error',
            'source': 'simple_extraction'
        }


def _simple_text_split(parsed_result: Dict[str, Any], document, chunk_size: int = 1000) -> List[Dict[str, Any]]:
    """
    简单的文本分割函数，用于测试

    Args:
        parsed_result: 解析结果
        document: 文档对象
        chunk_size: 每个块的字符数

    Returns:
        List[Dict]: 文档块列表
    """
    content = parsed_result.get('content', '')
    chunks = []

    # 简单按字符数分割
    for i in range(0, len(content), chunk_size):
        chunk_text = content[i:i + chunk_size]
        chunk = {
            'text': chunk_text,
            'content': chunk_text,
            'metadata': {
                'document_id': document.id,
                'chunk_id': f"chunk_{i // chunk_size}",
                'start_char': i,
                'end_char': min(i + chunk_size, len(content)),
                'chunk_index': i // chunk_size
            }
        }
        chunks.append(chunk)

    return chunks


def submit_parsing_job(document_id: str) -> str:
    """
    提交文档解析任务

    Args:
        document_id: 知识文档ID

    Returns:
        str: 任务ID
    """
    from app.services import get_task_queue
    from uuid import uuid4

    job_id = str(uuid4())

    # 创建解析任务记录
    parsing_job = ParsingJob(
        id=job_id,
        document_id=document_id,
        status='PENDING'
    )

    db.session.add(parsing_job)
    db.session.commit()

    # 提交到任务队列
    queue = get_task_queue()
    rq_job = queue.enqueue(
        parse_document,
        job_id,
        job_id=job_id,
        job_timeout='30m'  # 30分钟超时
    )

    logger.info(f"文档解析任务已提交: {job_id}")
    return job_id


def get_parsing_status(job_id: str) -> Dict[str, Any]:
    """
    获取解析任务状态

    Args:
        job_id: 任务ID

    Returns:
        Dict: 任务状态信息
    """
    from app.services.task_monitor import TaskMonitor

    # 从数据库获取任务信息
    job = ParsingJob.query.get(job_id)
    if not job:
        return {'error': '任务不存在'}

    # 从RQ获取任务状态
    rq_status = TaskMonitor.get_task_status(job_id)

    return {
        'id': job.id,
        'document_id': job.document_id,
        'status': job.status,
        'started_at': job.started_at.isoformat() + 'Z' if job.started_at else None,
        'completed_at': job.completed_at.isoformat() + 'Z' if job.completed_at else None,
        'error_message': job.error_message,
        'result_data': job.result_data,
        'rq_status': rq_status
    }


def get_supported_formats() -> Dict[str, List[str]]:
    """
    获取支持的文档格式信息

    Returns:
        Dict: 支持的格式分类
    """
    return {
        'idp_supported': [
            'pdf', 'doc', 'docx', 'ppt', 'pptx',
            'xls', 'xlsx', 'txt', 'rtf', 'odt',
            'jpg', 'jpeg', 'png', 'bmp', 'tiff'
        ],
        'simple_extraction': ['txt', 'md'],
        'recommended': [
            'pdf',   # 推荐：IDP服务能很好处理
            'docx',  # 推荐：包含丰富格式信息
            'pptx'   # 推荐：支持图文混合内容
        ]
    }
