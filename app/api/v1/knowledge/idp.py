"""
IP智慧解答专家系统 - IDP文档解析API

本模块实现了基于阿里云文档智能（大模型版）的文档解析API接口。
"""

import os
import json
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from rq import Queue
from app.api.v1.knowledge import knowledge_bp as bp
from app.models.knowledge import KnowledgeDocument, ParsingJob, DocumentChunk
from app.services.document.idp_service import IDPService
from app.services.document.idp_task_processor import (
    parse_document_with_idp,
    reprocess_document,
    batch_process_documents,
    get_processing_statistics
)
from app import db, redis_client
from datetime import datetime


@bp.route('/knowledge/documents/<document_id>/parse-idp', methods=['POST'])
@jwt_required()
def parse_document_idp(document_id):
    """
    使用阿里云IDP服务解析文档

    URL参数:
    - document_id: 文档ID

    请求体参数:
    - enable_llm: 是否开启大模型增强 (可选, 默认true)
    - enable_formula: 是否开启公式识别 (可选, 默认true)
    - async_mode: 是否异步处理 (可选, 默认true)
    """
    try:
        user_id = get_jwt_identity()

        # 获取文档
        document = KnowledgeDocument.query.filter_by(
            id=document_id,
            user_id=user_id
        ).first()

        if not document:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文档不存在'
                }
            }), 404

        # 检查文档状态
        if document.status == 'PARSING':
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_STATE',
                    'message': '文档正在解析中'
                }
            }), 400

        # 获取请求参数
        data = request.get_json() or {}
        enable_llm = data.get('enable_llm', True)
        enable_formula = data.get('enable_formula', True)
        async_mode = data.get('async_mode', True)

        # 检查文件是否存在
        file_path = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'instance/uploads'),
            document.file_path
        )

        if not os.path.exists(file_path):
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'FILE_NOT_FOUND',
                    'message': '文档文件不存在'
                }
            }), 400

        # 创建解析任务
        job = ParsingJob(
            document_id=document.id,
            task_type='idp_parse',
            status='PENDING',
            created_at=datetime.utcnow(),
            config=json.dumps({
                'enable_llm': enable_llm,
                'enable_formula': enable_formula,
                'async_mode': async_mode
            })
        )
        db.session.add(job)
        db.session.commit()

        if async_mode:
            # 异步处理
            queue = Queue('document_processing', connection=redis_client)
            rq_job = queue.enqueue(
                parse_document_with_idp,
                job.id,
                timeout=1800  # 30分钟超时
            )

            job.rq_job_id = rq_job.id
            db.session.commit()

            return jsonify({
                'code': 200,
                'status': 'success',
                'data': {
                    'job_id': job.id,
                    'rq_job_id': rq_job.id,
                    'message': '文档解析任务已提交，请查询进度'
                }
            })
        else:
            # 同步处理
            try:
                result = parse_document_with_idp(job.id)
                return jsonify({
                    'code': 200,
                    'status': 'success',
                    'data': result
                })
            except Exception as e:
                return jsonify({
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'PROCESSING_ERROR',
                        'message': str(e)
                    }
                }), 500

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@bp.route('/knowledge/parsing-jobs/<job_id>/status', methods=['GET'])
@jwt_required()
def get_parsing_job_status(job_id):
    """
    查询解析任务状态

    URL参数:
    - job_id: 任务ID
    """
    try:
        user_id = get_jwt_identity()

        # 获取任务
        job = ParsingJob.query.join(KnowledgeDocument).filter(
            ParsingJob.id == job_id,
            KnowledgeDocument.user_id == user_id
        ).first()

        if not job:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '解析任务不存在'
                }
            }), 404

        # 获取文档信息
        document = job.document

        # 构建响应数据
        response_data = {
            'job_id': job.id,
            'status': job.status,
            'task_type': job.task_type,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'document': {
                'id': document.id,
                'filename': document.original_filename,
                'status': document.status,
                'progress': document.progress,
                'chunk_count': document.chunk_count
            }
        }

        # 添加结果或错误信息
        if job.status == 'COMPLETED' and job.result:
            try:
                response_data['result'] = json.loads(job.result)
            except:
                response_data['result'] = job.result

        if job.status == 'FAILED' and job.error_message:
            response_data['error_message'] = job.error_message

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': response_data
        })

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@bp.route('/knowledge/documents/<document_id>/chunks', methods=['GET'])
@jwt_required()
def get_document_chunks(document_id):
    """
    获取文档的切分块

    URL参数:
    - document_id: 文档ID

    查询参数:
    - page: 页码 (可选, 默认1)
    - per_page: 每页数量 (可选, 默认20)
    - chunk_type: 块类型过滤 (可选)
    """
    try:
        user_id = get_jwt_identity()

        # 获取文档
        document = KnowledgeDocument.query.filter_by(
            id=document_id,
            user_id=user_id
        ).first()

        if not document:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文档不存在'
                }
            }), 404

        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        chunk_type = request.args.get('chunk_type')

        # 构建查询
        query = DocumentChunk.query.filter_by(document_id=document.id)

        if chunk_type:
            query = query.filter_by(chunk_type=chunk_type)

        query = query.order_by(DocumentChunk.chunk_index)

        # 分页查询
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # 构建响应数据
        chunks_data = []
        for chunk in pagination.items:
            chunk_data = {
                'id': chunk.id,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'title': chunk.title,
                'chunk_type': chunk.chunk_type,
                'page_number': chunk.page_number,
                'vector_id': chunk.vector_id,
                'created_at': chunk.created_at.isoformat() if chunk.created_at else None
            }

            # 解析元数据
            if chunk.metadata:
                try:
                    chunk_data['metadata'] = json.loads(chunk.metadata)
                except:
                    chunk_data['metadata'] = {}
            else:
                chunk_data['metadata'] = {}

            chunks_data.append(chunk_data)

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'chunks': chunks_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@bp.route('/knowledge/idp/statistics', methods=['GET'])
@jwt_required()
def get_idp_statistics():
    """
    获取IDP处理统计信息
    """
    try:
        user_id = get_jwt_identity()

        # 获取用户的文档统计
        user_docs = KnowledgeDocument.query.filter_by(user_id=user_id)

        document_stats = {
            'total': user_docs.count(),
            'parsed': user_docs.filter_by(status='PARSED').count(),
            'parsing': user_docs.filter_by(status='PARSING').count(),
            'failed': user_docs.filter_by(status='PARSE_FAILED').count()
        }

        # 获取块统计
        chunk_stats = db.session.query(
            db.func.count(DocumentChunk.id).label('total_chunks')
        ).join(KnowledgeDocument).filter(
            KnowledgeDocument.user_id == user_id
        ).first()

        # 获取任务统计
        job_stats = db.session.query(
            ParsingJob.status,
            db.func.count(ParsingJob.id).label('count')
        ).join(KnowledgeDocument).filter(
            KnowledgeDocument.user_id == user_id
        ).group_by(ParsingJob.status).all()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'documents': document_stats,
                'total_chunks': chunk_stats.total_chunks if chunk_stats else 0,
                'jobs': {stat.status: stat.count for stat in job_stats}
            }
        })

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@bp.route('/knowledge/idp/supported-formats', methods=['GET'])
def get_supported_formats():
    """
    获取IDP支持的文档格式
    """
    try:
        idp_service = IDPService()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'document_formats': idp_service.get_supported_formats(),
                'video_formats': idp_service.get_supported_video_formats()
            }
        })

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@bp.route('/knowledge/documents/<document_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_document_api(document_id):
    """
    重新处理文档

    URL参数:
    - document_id: 文档ID
    """
    try:
        user_id = get_jwt_identity()

        # 检查文档权限
        document = KnowledgeDocument.query.filter_by(
            id=document_id,
            user_id=user_id
        ).first()

        if not document:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文档不存在'
                }
            }), 404

        # 异步重新处理
        queue = Queue('document_processing', connection=redis_client)
        rq_job = queue.enqueue(
            reprocess_document,
            document_id,
            timeout=1800
        )

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'message': '重新处理任务已提交',
                'rq_job_id': rq_job.id
            }
        })

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500


@bp.route('/knowledge/documents/parse-from-url', methods=['POST'])
@jwt_required()
def parse_document_from_url():
    """
    通过URL解析文档

    请求体参数:
    - file_url: 文档URL (必需)
    - file_name: 文件名 (必需)
    - enable_llm: 是否开启大模型增强 (可选, 默认true)
    - enable_formula: 是否开启公式识别 (可选, 默认true)
    - async_mode: 是否异步处理 (可选, 默认true)
    - vendor: 厂商 (可选)
    - tags: 标签列表 (可选)
    """
    try:
        user_id = get_jwt_identity()

        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 验证必需参数
        file_url = data.get('file_url')
        file_name = data.get('file_name')

        if not file_url:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'MISSING_PARAMETER',
                    'message': '缺少file_url参数'
                }
            }), 400

        if not file_name:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'MISSING_PARAMETER',
                    'message': '缺少file_name参数'
                }
            }), 400

        # 验证URL格式
        if not file_url.startswith(('http://', 'https://')):
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_URL',
                    'message': 'URL格式无效，必须以http://或https://开头'
                }
            }), 400

        # 获取可选参数
        enable_llm = data.get('enable_llm', True)
        enable_formula = data.get('enable_formula', True)
        async_mode = data.get('async_mode', True)
        vendor = data.get('vendor', '')
        tags = data.get('tags', [])

        # 验证文件格式
        idp_service = IDPService()
        file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        if not idp_service.validate_file_format(f"test.{file_ext}"):
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'UNSUPPORTED_FORMAT',
                    'message': f'不支持的文件格式: {file_ext}'
                }
            }), 400

        # 创建文档记录
        import uuid
        document_id = str(uuid.uuid4())
        document = KnowledgeDocument(
            id=document_id,
            filename=file_name,
            original_filename=file_name,
            file_path=file_url,  # 对于URL文档，存储URL
            file_size=0,  # URL文档暂时无法获取文件大小
            mime_type='',  # 暂时无法确定MIME类型
            vendor=vendor,
            tags=tags if isinstance(tags, list) else [],
            user_id=user_id,
            status='UPLOADING'
        )

        db.session.add(document)
        db.session.commit()

        # 创建解析任务
        job = ParsingJob(
            document_id=document.id,
            task_type='idp_parse_url',
            status='PENDING',
            created_at=datetime.utcnow(),
            config=json.dumps({
                'file_url': file_url,
                'enable_llm': enable_llm,
                'enable_formula': enable_formula,
                'async_mode': async_mode
            })
        )
        db.session.add(job)
        db.session.commit()

        if async_mode:
            # 异步处理
            queue = Queue('document_processing', connection=redis_client)
            rq_job = queue.enqueue(
                'app.services.idp_task_processor.parse_document_from_url_task',
                job.id,
                file_url,
                file_name,
                enable_llm,
                enable_formula,
                timeout=1800
            )

            job.rq_job_id = rq_job.id
            db.session.commit()

            return jsonify({
                'code': 200,
                'status': 'success',
                'data': {
                    'document_id': document.id,
                    'job_id': job.id,
                    'rq_job_id': rq_job.id,
                    'message': 'URL文档解析任务已提交，请查询进度'
                }
            })
        else:
            # 同步处理
            try:
                # 直接调用IDP服务解析URL
                result = idp_service.parse_document_from_url(
                    file_url=file_url,
                    file_name=file_name,
                    enable_llm=enable_llm,
                    enable_formula=enable_formula
                )

                # 更新文档状态
                document.status = 'PARSED'
                document.progress = 100
                document.parsed_at = datetime.utcnow()

                job.status = 'COMPLETED'
                job.completed_at = datetime.utcnow()
                job.result = json.dumps({
                    'success': True,
                    'statistics': idp_service.get_document_statistics(result)
                })

                db.session.commit()

                return jsonify({
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'document_id': document.id,
                        'job_id': job.id,
                        'result': {
                            'success': True,
                            'statistics': idp_service.get_document_statistics(result)
                        }
                    }
                })

            except Exception as e:
                # 更新失败状态
                document.status = 'PARSE_FAILED'
                document.error_message = str(e)

                job.status = 'FAILED'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()

                db.session.commit()

                return jsonify({
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'PROCESSING_ERROR',
                        'message': str(e)
                    }
                }), 500

    except Exception as e:
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': str(e)
            }
        }), 500
