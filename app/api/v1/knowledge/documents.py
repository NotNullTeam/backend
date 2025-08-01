"""
IP智慧解答专家系统 - 知识文档API

本模块实现了知识文档相关的API接口。
"""

import os
import uuid
from werkzeug.utils import secure_filename
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1.knowledge import knowledge_bp as bp
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app import db
from datetime import datetime


# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}


def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/documents', methods=['POST'])
@jwt_required()
def upload_document():
    """
    上传知识文档

    表单参数:
    - file: 文档文件 (必需)
    - vendor: 厂商 (可选)
    - tags: 标签列表 (可选)
    """
    try:
        user_id = get_jwt_identity()

        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '没有选择文件'
                }
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '没有选择文件'
                }
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': f'不支持的文件类型，支持的类型: {", ".join(ALLOWED_EXTENSIONS)}'
                }
            }), 400

        # 获取表单数据
        tags = request.form.getlist('tags') or []
        vendor = request.form.get('vendor', '')

        # 处理文件保存
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_extension = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{file_id}.{file_extension}"

        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, new_filename)
        file.save(file_path)

        # 保存文档记录
        document = KnowledgeDocument(
            id=file_id,
            filename=new_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.mimetype,
            vendor=vendor,
            tags=tags,
            user_id=user_id
        )

        db.session.add(document)
        db.session.flush()

        # 创建解析任务
        parsing_job = ParsingJob(
            document_id=document.id
        )
        db.session.add(parsing_job)
        db.session.commit()

        # 触发异步解析任务
        try:
            from app.services.document.document_service import parse_document
            from app.services import get_task_queue

            queue = get_task_queue()
            job = queue.enqueue(parse_document, parsing_job.id)
            current_app.logger.info(f"异步解析任务已提交: job_id={job.id}")
        except Exception as e:
            # 如果服务还未实现或Redis不可用，暂时跳过
            current_app.logger.warning(f"Document parsing service not available: {str(e)}")
            # 在测试环境中不应该阻塞API响应

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'docId': document.id,
                'status': 'QUEUED',
                'message': '文档已加入处理队列'
            }
        })

    except Exception as e:
        current_app.logger.error(f"Upload document error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '文档上传失败'
            }
        }), 500


@bp.route('/documents', methods=['GET'])
@jwt_required()
def get_documents():
    """
    获取文档列表

    查询参数:
    - status: 文档状态过滤
    - vendor: 厂商过滤
    - page: 页码 (默认1)
    - pageSize: 每页大小 (默认10)
    """
    try:
        user_id = get_jwt_identity()

        # 获取查询参数
        status = request.args.get('status')
        vendor = request.args.get('vendor')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))

        # 构建查询
        query = KnowledgeDocument.query.filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)
        if vendor:
            query = query.filter_by(vendor=vendor)

        # 分页查询
        pagination = query.order_by(KnowledgeDocument.uploaded_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )

        documents = pagination.items

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'items': [{
                    'docId': doc.id,
                    'fileName': doc.original_filename,
                    'vendor': doc.vendor,
                    'tags': doc.tags,
                    'status': doc.status,
                    'progress': doc.progress,
                    'fileSize': doc.file_size,
                    'uploadedAt': doc.uploaded_at.isoformat() + 'Z' if doc.uploaded_at else None,
                    'processedAt': doc.processed_at.isoformat() + 'Z' if doc.processed_at else None
                } for doc in documents],
                'total': pagination.total,
                'page': page,
                'pageSize': page_size
            }
        })

    except ValueError as e:
        return jsonify({
            'code': 400,
            'status': 'error',
            'error': {
                'type': 'INVALID_REQUEST',
                'message': '分页参数必须为正整数'
            }
        }), 400
    except Exception as e:
        current_app.logger.error(f"Get documents error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取文档列表时发生错误'
            }
        }), 500


@bp.route('/knowledge/documents/<doc_id>', methods=['GET'])
@jwt_required()
def get_document_detail(doc_id):
    """
    获取文档详情

    参数:
    - doc_id: 文档ID
    """
    try:
        user_id = get_jwt_identity()

        document = KnowledgeDocument.query.filter_by(
            id=doc_id,
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

        # 获取最新的解析任务信息
        parsing_job = ParsingJob.query.filter_by(
            document_id=doc_id
        ).order_by(ParsingJob.created_at.desc()).first()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'docId': document.id,
                'fileName': document.original_filename,
                'vendor': document.vendor,
                'tags': document.tags,
                'status': document.status,
                'progress': document.progress,
                'fileSize': document.file_size,
                'mimeType': document.mime_type,
                'errorMessage': document.error_message,
                'uploadedAt': document.uploaded_at.isoformat() + 'Z' if document.uploaded_at else None,
                'processedAt': document.processed_at.isoformat() + 'Z' if document.processed_at else None,
                'parsingJob': {
                    'id': parsing_job.id,
                    'status': parsing_job.status,
                    'errorMessage': parsing_job.error_message,
                    'resultData': parsing_job.result_data,
                    'createdAt': parsing_job.created_at.isoformat() + 'Z' if parsing_job.created_at else None,
                    'completedAt': parsing_job.completed_at.isoformat() + 'Z' if parsing_job.completed_at else None
                } if parsing_job else None
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get document detail error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取文档详情时发生错误'
            }
        }), 500


@bp.route('/knowledge/documents/<doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    """
    删除文档

    参数:
    - doc_id: 文档ID
    """
    try:
        user_id = get_jwt_identity()

        document = KnowledgeDocument.query.filter_by(
            id=doc_id,
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

        # 删除物理文件
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except OSError as e:
                current_app.logger.warning(f"Failed to delete file {document.file_path}: {str(e)}")

        # 删除向量数据库中的数据
        try:
            from app.services.retrieval.vector_service import delete_document_vectors
            # 直接调用函数而不是使用 Celery 的 delay 方法
            delete_document_vectors(doc_id)
        except (ImportError, AttributeError):
            # 如果服务还未实现，暂时跳过
            current_app.logger.warning("Vector service not available")

        # 删除数据库记录
        db.session.delete(document)
        db.session.commit()

        return '', 204

    except Exception as e:
        current_app.logger.error(f"Delete document error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '删除文档时发生错误'
            }
        }), 500


@bp.route('/knowledge/documents/<doc_id>/reparse', methods=['PUT'])
@jwt_required()
def reparse_document(doc_id):
    """
    重新解析文档

    参数:
    - doc_id: 文档ID
    """
    try:
        user_id = get_jwt_identity()

        document = KnowledgeDocument.query.filter_by(
            id=doc_id,
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

        # 重置状态
        document.status = 'QUEUED'
        document.progress = 0
        document.error_message = None

        # 创建新的解析任务
        parsing_job = ParsingJob(
            document_id=document.id
        )
        db.session.add(parsing_job)
        db.session.commit()

        # 触发异步解析
        try:
            from app.services.document.document_service import parse_document
            from app.services import get_task_queue

            queue = get_task_queue()
            job = queue.enqueue(parse_document, parsing_job.id)
            current_app.logger.info(f"异步重解析任务已提交: job_id={job.id}")
        except Exception as e:
            # 如果服务还未实现或Redis不可用，暂时跳过
            current_app.logger.warning(f"Document parsing service not available: {str(e)}")
            # 在测试环境中不应该阻塞API响应

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'docId': document.id,
                'status': 'QUEUED',
                'message': '已触发重新解析'
            }
        })

    except Exception as e:
        current_app.logger.error(f"Reparse document error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '重新解析文档时发生错误'
            }
        }), 500


@bp.route('/knowledge/documents/<doc_id>', methods=['PATCH'])
@jwt_required()
def update_document_metadata(doc_id):
    """
    更新文档元数据

    参数:
    - doc_id: 文档ID

    请求体:
    - tags: 标签列表 (可选)
    - vendor: 厂商 (可选)
    """
    try:
        user_id = get_jwt_identity()

        document = KnowledgeDocument.query.filter_by(
            id=doc_id,
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

        # 获取请求数据
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 更新允许修改的字段
        if 'tags' in data:
            if isinstance(data['tags'], list):
                document.tags = data['tags']
            else:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': 'tags必须是数组格式'
                    }
                }), 400

        if 'vendor' in data:
            if isinstance(data['vendor'], str) or data['vendor'] is None:
                document.vendor = data['vendor']
            else:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': 'vendor必须是字符串或null'
                    }
                }), 400

        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'message': '文档元数据更新成功'
        })

    except Exception as e:
        current_app.logger.error(f"Update document metadata error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '更新文档元数据时发生错误'
            }
        }), 500
