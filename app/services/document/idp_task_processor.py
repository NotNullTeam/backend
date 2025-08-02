"""
IP智慧解答专家系统 - 文档解析异步任务

基于阿里云文档智能（大模型版）API的文档解析任务处理器
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from rq import get_current_job
from app import create_app, db
from app.models.knowledge import KnowledgeDocument, ParsingJob, DocumentChunk
from app.services.document.idp_service import IDPService
from app.services.document.semantic_splitter import SemanticSplitter
from app.services.retrieval.vector_service import VectorService

logger = logging.getLogger(__name__)


def parse_document_with_idp(job_id: str) -> Dict[str, Any]:
    """
    使用阿里云IDP服务解析文档的异步任务

    Args:
        job_id: 解析任务ID

    Returns:
        Dict[str, Any]: 解析结果
    """
    app = create_app()
    with app.app_context():
        try:
            # 获取任务和文档信息
            job = ParsingJob.query.get(job_id)
            if not job:
                raise Exception(f"解析任务未找到: {job_id}")

            document = KnowledgeDocument.query.get(job.document_id)
            if not document:
                raise Exception(f"知识文档未找到: {job.document_id}")

            logger.info(f"开始IDP解析任务: {document.original_filename}")

            # 更新状态
            job.status = 'PROCESSING'
            job.started_at = datetime.utcnow()
            document.status = 'PARSING'
            document.progress = 10
            db.session.commit()

            # 初始化服务
            idp_service = IDPService()
            splitter = SemanticSplitter(max_chunk_size=1000, overlap=100)
            vector_service = VectorService()

            # 步骤1: IDP文档解析
            logger.info("步骤1: 执行IDP文档解析")
            document.progress = 20
            db.session.commit()

            # 获取文件路径
            file_path = os.path.join(
                app.config.get('UPLOAD_FOLDER', 'instance/uploads'),
                document.file_path
            )

            if not os.path.exists(file_path):
                raise Exception(f"文档文件不存在: {file_path}")

            # 执行IDP解析
            idp_result = idp_service.parse_document(
                file_path=file_path,
                enable_llm=True,  # 开启大模型增强
                enable_formula=True  # 开启公式识别
            )

            document.progress = 50
            db.session.commit()

            # 步骤2: 语义切分
            logger.info("步骤2: 执行语义切分")
            chunks = splitter.split_document(idp_result, document)

            document.progress = 70
            db.session.commit()

            # 步骤3: 保存文档块到数据库
            logger.info(f"步骤3: 保存 {len(chunks)} 个文档块到数据库")

            # 删除旧的文档块
            DocumentChunk.query.filter_by(document_id=document.id).delete()

            saved_chunks = []
            for i, chunk_data in enumerate(chunks):
                try:
                    # 提取元数据
                    metadata = splitter.extract_metadata(chunk_data, document)

                    # 创建文档块记录
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=i,
                        content=chunk_data['content'],
                        title=chunk_data.get('title', ''),
                        chunk_type=chunk_data.get('type', 'text'),
                        page_number=chunk_data.get('page_number', 0),
                        metadata=json.dumps(metadata, ensure_ascii=False),
                        vector_id=None  # 将在向量化时设置
                    )

                    db.session.add(chunk)
                    saved_chunks.append(chunk)

                except Exception as e:
                    logger.warning(f"保存文档块 {i} 失败: {str(e)}")
                    continue

            db.session.commit()
            document.progress = 85
            db.session.commit()

            # 步骤4: 向量化处理
            logger.info("步骤4: 执行向量化处理")

            try:
                # 批量向量化
                chunk_texts = [chunk.content for chunk in saved_chunks]
                vectors = vector_service.embed_batch(chunk_texts)

                # 批量存储到向量数据库
                vector_ids = vector_service.index_chunks_batch(
                    chunks=saved_chunks,
                    vectors=vectors,
                    document_id=document.id
                )

                # 更新文档块的向量ID
                for chunk, vector_id in zip(saved_chunks, vector_ids):
                    chunk.vector_id = vector_id

                db.session.commit()

            except Exception as e:
                logger.warning(f"向量化处理失败: {str(e)}")
                # 向量化失败不影响整体解析成功

            # 步骤5: 更新文档状态
            document.status = 'PARSED'
            document.progress = 100
            document.chunk_count = len(saved_chunks)
            document.parsed_at = datetime.utcnow()

            # 保存IDP原始结果
            document.parsing_result = json.dumps({
                'idp_result': idp_result,
                'statistics': idp_service.get_document_statistics(idp_result),
                'chunks_count': len(saved_chunks)
            }, ensure_ascii=False)

            job.status = 'COMPLETED'
            job.completed_at = datetime.utcnow()
            job.result = json.dumps({
                'success': True,
                'chunks_count': len(saved_chunks),
                'statistics': idp_service.get_document_statistics(idp_result)
            }, ensure_ascii=False)

            db.session.commit()

            logger.info(f"文档解析完成: {document.original_filename}, 生成 {len(saved_chunks)} 个文档块")

            return {
                'success': True,
                'document_id': document.id,
                'chunks_count': len(saved_chunks),
                'statistics': idp_service.get_document_statistics(idp_result)
            }

        except Exception as e:
            logger.error(f"文档解析失败: {str(e)}")

            # 更新失败状态
            if 'job' in locals():
                job.status = 'FAILED'
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)

            if 'document' in locals():
                document.status = 'PARSE_FAILED'
                document.error_message = str(e)

            db.session.commit()

            return {
                'success': False,
                'error': str(e)
            }


def reprocess_document(document_id: str, use_enhanced_llm: bool = True) -> Dict[str, Any]:
    """
    重新处理已上传的文档

    Args:
        document_id: 文档ID
        use_enhanced_llm: 是否使用增强的大模型功能

    Returns:
        Dict[str, Any]: 处理结果
    """
    app = create_app()
    with app.app_context():
        try:
            document = KnowledgeDocument.query.get(document_id)
            if not document:
                raise Exception(f"文档未找到: {document_id}")

            # 创建新的解析任务
            job = ParsingJob(
                document_id=document.id,
                task_type='reprocess',
                status='PENDING',
                created_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()

            # 重置文档状态
            document.status = 'UPLOADING'
            document.progress = 0
            document.error_message = None
            db.session.commit()

            # 执行重新处理
            return parse_document_with_idp(job.id)

        except Exception as e:
            logger.error(f"重新处理文档失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


def batch_process_documents(document_ids: List[str]) -> Dict[str, Any]:
    """
    批量处理文档

    Args:
        document_ids: 文档ID列表

    Returns:
        Dict[str, Any]: 批量处理结果
    """
    app = create_app()
    with app.app_context():
        results = {
            'success_count': 0,
            'failed_count': 0,
            'results': []
        }

        for doc_id in document_ids:
            try:
                result = reprocess_document(doc_id)
                if result['success']:
                    results['success_count'] += 1
                else:
                    results['failed_count'] += 1
                results['results'].append({
                    'document_id': doc_id,
                    'result': result
                })
            except Exception as e:
                results['failed_count'] += 1
                results['results'].append({
                    'document_id': doc_id,
                    'result': {'success': False, 'error': str(e)}
                })

        return results


def cleanup_failed_documents() -> Dict[str, Any]:
    """
    清理解析失败的文档

    Returns:
        Dict[str, Any]: 清理结果
    """
    app = create_app()
    with app.app_context():
        try:
            # 查找解析失败的文档
            failed_documents = KnowledgeDocument.query.filter_by(
                status='PARSE_FAILED'
            ).all()

            cleanup_count = 0
            for document in failed_documents:
                try:
                    # 删除文档块
                    DocumentChunk.query.filter_by(document_id=document.id).delete()

                    # 删除解析任务
                    ParsingJob.query.filter_by(document_id=document.id).delete()

                    # 删除文档记录
                    db.session.delete(document)

                    cleanup_count += 1

                except Exception as e:
                    logger.warning(f"清理文档 {document.id} 失败: {str(e)}")

            db.session.commit()

            return {
                'success': True,
                'cleaned_count': cleanup_count
            }

        except Exception as e:
            logger.error(f"清理失败文档时出错: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


def get_processing_statistics() -> Dict[str, Any]:
    """
    获取文档处理统计信息

    Returns:
        Dict[str, Any]: 统计信息
    """
    app = create_app()
    with app.app_context():
        try:
            # 文档状态统计
            document_stats = db.session.query(
                KnowledgeDocument.status,
                db.func.count(KnowledgeDocument.id).label('count')
            ).group_by(KnowledgeDocument.status).all()

            # 任务状态统计
            job_stats = db.session.query(
                ParsingJob.status,
                db.func.count(ParsingJob.id).label('count')
            ).group_by(ParsingJob.status).all()

            # 厂商分布统计
            vendor_stats = db.session.query(
                KnowledgeDocument.vendor,
                db.func.count(KnowledgeDocument.id).label('count')
            ).group_by(KnowledgeDocument.vendor).all()

            return {
                'document_status': {stat.status: stat.count for stat in document_stats},
                'job_status': {stat.status: stat.count for stat in job_stats},
                'vendor_distribution': {stat.vendor: stat.count for stat in vendor_stats},
                'total_documents': KnowledgeDocument.query.count(),
                'total_chunks': DocumentChunk.query.count()
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                'error': str(e)
            }


def parse_document_from_url_task(job_id: str, file_url: str, file_name: str,
                                enable_llm: bool = True, enable_formula: bool = True) -> Dict[str, Any]:
    """
    通过URL解析文档的异步任务

    Args:
        job_id: 解析任务ID
        file_url: 文档URL
        file_name: 文件名
        enable_llm: 是否开启大模型增强
        enable_formula: 是否开启公式识别增强

    Returns:
        Dict[str, Any]: 解析结果
    """
    app = create_app()
    with app.app_context():
        try:
            # 获取任务和文档信息
            job = ParsingJob.query.get(job_id)
            if not job:
                raise Exception(f"解析任务未找到: {job_id}")

            document = KnowledgeDocument.query.get(job.document_id)
            if not document:
                raise Exception(f"知识文档未找到: {job.document_id}")

            logger.info(f"开始URL文档IDP解析任务: {file_name} ({file_url})")

            # 更新状态
            job.status = 'PROCESSING'
            job.started_at = datetime.utcnow()
            document.status = 'PARSING'
            document.progress = 10
            db.session.commit()

            # 初始化服务
            idp_service = IDPService()
            splitter = SemanticSplitter(max_chunk_size=1000, overlap=100)
            vector_service = VectorService()

            # 步骤1: IDP文档解析（通过URL）
            logger.info("步骤1: 执行IDP URL文档解析")
            document.progress = 20
            db.session.commit()

            # 执行URL解析
            idp_result = idp_service.parse_document_from_url(
                file_url=file_url,
                file_name=file_name,
                enable_llm=enable_llm,
                enable_formula=enable_formula
            )

            document.progress = 50
            db.session.commit()

            # 步骤2: 语义切分
            logger.info("步骤2: 执行语义切分")
            chunks = splitter.split_document(idp_result, document)

            document.progress = 70
            db.session.commit()

            # 步骤3: 保存文档块到数据库
            logger.info(f"步骤3: 保存 {len(chunks)} 个文档块到数据库")

            # 删除旧的文档块
            DocumentChunk.query.filter_by(document_id=document.id).delete()

            saved_chunks = []
            for i, chunk_data in enumerate(chunks):
                try:
                    # 提取元数据
                    metadata = splitter.extract_metadata(chunk_data, document)

                    # 创建文档块记录
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=i,
                        content=chunk_data['content'],
                        title=chunk_data.get('title', ''),
                        chunk_type=chunk_data.get('type', 'text'),
                        page_number=chunk_data.get('page_number', 0),
                        metadata=json.dumps(metadata, ensure_ascii=False),
                        vector_id=None  # 将在向量化时设置
                    )

                    db.session.add(chunk)
                    saved_chunks.append(chunk)

                except Exception as e:
                    logger.warning(f"保存文档块 {i} 失败: {str(e)}")
                    continue

            db.session.commit()
            document.progress = 85
            db.session.commit()

            # 步骤4: 向量化处理
            logger.info("步骤4: 执行向量化处理")

            try:
                # 批量向量化
                chunk_texts = [chunk.content for chunk in saved_chunks]
                vectors = vector_service.embed_batch(chunk_texts)

                # 批量存储到向量数据库
                vector_ids = vector_service.index_chunks_batch(
                    chunks=saved_chunks,
                    vectors=vectors,
                    document_id=document.id
                )

                # 更新文档块的向量ID
                for chunk, vector_id in zip(saved_chunks, vector_ids):
                    chunk.vector_id = vector_id

                db.session.commit()

            except Exception as e:
                logger.warning(f"向量化处理失败: {str(e)}")
                # 向量化失败不影响整体解析成功

            # 步骤5: 更新文档状态
            document.status = 'PARSED'
            document.progress = 100
            document.chunk_count = len(saved_chunks)
            document.parsed_at = datetime.utcnow()

            # 保存IDP原始结果
            document.parsing_result = json.dumps({
                'idp_result': idp_result,
                'statistics': idp_service.get_document_statistics(idp_result),
                'chunks_count': len(saved_chunks),
                'source_type': 'url',
                'source_url': file_url
            }, ensure_ascii=False)

            job.status = 'COMPLETED'
            job.completed_at = datetime.utcnow()
            job.result = json.dumps({
                'success': True,
                'chunks_count': len(saved_chunks),
                'statistics': idp_service.get_document_statistics(idp_result),
                'source_type': 'url'
            }, ensure_ascii=False)

            db.session.commit()

            logger.info(f"URL文档解析完成: {file_name}, 生成 {len(saved_chunks)} 个文档块")

            return {
                'success': True,
                'document_id': document.id,
                'chunks_count': len(saved_chunks),
                'statistics': idp_service.get_document_statistics(idp_result),
                'source_type': 'url'
            }

        except Exception as e:
            logger.error(f"URL文档解析失败: {str(e)}")

            # 更新失败状态
            if 'job' in locals():
                job.status = 'FAILED'
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)

            if 'document' in locals():
                document.status = 'PARSE_FAILED'
                document.error_message = str(e)

            db.session.commit()

            return {
                'success': False,
                'error': str(e)
            }
