"""
知识库管理 API 接口 (Flask-RESTX)

将原有的知识库管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

import os
import uuid
from werkzeug.utils import secure_filename
from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.utils.response_helper import success_response, error_response, validation_error, not_found_error, internal_error
from datetime import datetime

# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_knowledge_api():
    """初始化知识库API接口"""
    # 动态获取命名空间，避免模块缓存导致的过期引用
    knowledge_ns = get_namespace('knowledge')

    # 文档信息模型
    document_model = knowledge_ns.model('Document', {
        'id': fields.String(description='文档ID'),
        'filename': fields.String(description='文件名'),
        'original_filename': fields.String(description='原始文件名'),
        'file_size': fields.Integer(description='文件大小（字节）'),
        'mime_type': fields.String(description='MIME类型'),
        'vendor': fields.String(description='厂商'),
        'tags': fields.List(fields.String, description='标签列表'),
        'status': fields.String(description='处理状态'),
        'created_at': fields.String(description='创建时间'),
        'updated_at': fields.String(description='更新时间')
    })

    # 文档列表响应模型
    documents_list_model = knowledge_ns.model('DocumentsList', {
        'documents': fields.List(fields.Nested(document_model), description='文档列表'),
        'total': fields.Integer(description='总数量'),
        'page': fields.Integer(description='当前页码'),
        'pageSize': fields.Integer(description='每页大小'),
        'totalPages': fields.Integer(description='总页数')
    })

    # 文档上传响应模型
    upload_response_model = knowledge_ns.model('UploadResponse', {
        'document_id': fields.String(description='文档ID'),
        'filename': fields.String(description='文件名'),
        'status': fields.String(description='上传状态')
    })

    # 标签列表模型
    tags_model = knowledge_ns.model('TagsList', {
        'tags': fields.List(fields.String, description='标签列表')
    })

    @knowledge_ns.route('/documents')
    class DocumentList(Resource):
        @knowledge_ns.doc('get_documents')
        @knowledge_ns.param('status', '文档状态过滤', type='string')
        @knowledge_ns.param('vendor', '厂商过滤', type='string')
        @knowledge_ns.param('page', '页码', type='int', default=1)
        @knowledge_ns.param('pageSize', '每页大小', type='int', default=10)
        @jwt_required()
        def get(self):
            """获取文档列表

            获取用户的知识文档列表，支持分页和筛选。
            """
            try:
                # 验证并规范化用户身份
                user_id_raw = get_jwt_identity()
                try:
                    user_id = int(user_id_raw)
                except Exception:
                    return {'code': 401, 'status': 'error', 'error': {'type': 'UNAUTHORIZED', 'message': '无效的用户身份'}}, 401

                from app.models.user import User
                user = User.query.get(user_id)
                if not user or not getattr(user, 'is_active', True):
                    return {'code': 401, 'status': 'error', 'error': {'type': 'UNAUTHORIZED', 'message': '用户不存在或已被禁用'}}, 401

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

                # 分页
                total = query.count()
                documents = query.offset((page - 1) * page_size).limit(page_size).all()

                result = {
                    'documents': [doc.to_dict() for doc in documents],
                    'pagination': {
                        'total': total,
                        'page': page,
                        'per_page': page_size,
                        'pages': (total + page_size - 1) // page_size
                    }
                }
                return {'code': 200, 'status': 'success', 'data': result}, 200

            except Exception as e:
                current_app.logger.error(f"获取文档列表失败: {e}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取文档列表失败'}}, 500

        @knowledge_ns.doc('upload_document')
        @knowledge_ns.expect(knowledge_ns.parser()
                           .add_argument('file', location='files', type='file', required=True, help='文档文件')
                           .add_argument('vendor', location='form', type=str, help='厂商')
                           .add_argument('tags', location='form', action='append', help='标签列表'))
        @jwt_required()
        def post(self):
            """上传知识文档

            上传新的知识文档到系统中进行处理和索引。
            """
            try:
                user_id = get_jwt_identity()

                # 检查文件
                if 'file' not in request.files:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '未选择文件'}}, 400

                file = request.files['file']
                if file.filename == '':
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '未选择文件'}}, 400

                if not allowed_file(file.filename):
                    return {'code': 400, 'status': 'error', 'error': {'type': 'UNSUPPORTED_FILE_TYPE', 'message': '不支持的文件类型'}}, 400

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
                db.session.commit()

                result = {
                    'document': {
                        'id': file_id,
                        'filename': filename,
                        'category': request.form.get('category', ''),
                        'upload_time': datetime.utcnow().isoformat() + 'Z',
                        'file_size': os.path.getsize(file_path)
                    }
                }
                return {'code': 201, 'status': 'success', 'data': result}, 201

            except Exception as e:
                # 打印完整堆栈，便于定位具体原因（路径/权限/数据库/类型转换等）
                current_app.logger.exception(f"文档上传失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '文档上传失败'
                    }
                }, 500

    # 已废弃：历史别名路由 /upload 已移除，统一使用 POST /knowledge/documents

    @knowledge_ns.route('/documents/<string:doc_id>')
    class DocumentDetail(Resource):
        @knowledge_ns.doc('get_document_detail')
        @jwt_required()
        def get(self, doc_id):
            """获取文档详情

            获取指定文档的详细信息。
            """
            try:
                user_id = get_jwt_identity()

                document = KnowledgeDocument.query.filter_by(
                    id=doc_id, user_id=user_id
                ).first()

                if not document:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '文档不存在'}}, 404
                return {'code': 200, 'status': 'success', 'data': {'document': document.to_dict()}}, 200

            except Exception as e:
                current_app.logger.error(f"获取文档详情失败: {e}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取文档详情失败'}}, 500

        @knowledge_ns.doc('update_document_metadata')
        @knowledge_ns.expect(knowledge_ns.model('UpdateDocument', {
            'tags': fields.List(fields.String, description='标签列表'),
            'vendor': fields.String(description='厂商')
        }))
        @jwt_required()
        def put(self, doc_id):
            """更新文档元数据

            更新指定文档的标签和厂商信息。
            """
            try:
                user_id = get_jwt_identity()
                data = request.get_json()

                document = KnowledgeDocument.query.filter_by(
                    id=doc_id, user_id=user_id
                ).first()

                if not document:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '文档不存在'}}, 404

                # 更新元数据
                if 'tags' in data:
                    document.tags = data['tags']
                if 'vendor' in data:
                    document.vendor = data['vendor']

                document.updated_at = datetime.utcnow()
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': document.to_dict()}, 200

            except Exception as e:
                current_app.logger.error(f"更新文档元数据失败: {e}")
                return error_response("更新文档元数据失败", str(e), 500)

        @knowledge_ns.doc('delete_document')
        @jwt_required()
        def delete(self, doc_id):
            """删除知识文档

            删除指定的知识文档及其相关数据。
            """
            try:
                user_id = get_jwt_identity()

                document = KnowledgeDocument.query.filter_by(
                    id=doc_id, user_id=user_id
                ).first()

                if not document:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '文档不存在'}}, 404

                # 删除文件
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)

                # 删除数据库记录
                db.session.delete(document)
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': {"message": "文档删除成功"}}, 200

            except Exception as e:
                current_app.logger.error(f"删除文档失败: {e}")
                return error_response("删除文档失败", str(e), 500)

    @knowledge_ns.route('/documents/<string:doc_id>/status')
    class DocumentStatus(Resource):
        @knowledge_ns.doc('get_document_status')
        @jwt_required()
        def get(self, doc_id):
            """获取文档解析状态

            获取指定文档的解析处理状态。
            """
            try:
                user_id = get_jwt_identity()

                document = KnowledgeDocument.query.filter_by(
                    id=doc_id, user_id=user_id
                ).first()

                if not document:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '文档不存在'}}, 404

                # 获取解析任务状态
                parsing_job = ParsingJob.query.filter_by(document_id=doc_id).first()

                # 当前模型不包含 progress 字段，统一返回 0 或由状态推断
                inferred_progress = 0
                if parsing_job and parsing_job.status == 'COMPLETED':
                    inferred_progress = 100
                status_info = {
                    'document_id': doc_id,
                    'status': document.status,
                    'parsing_progress': inferred_progress,
                    'error_message': parsing_job.error_message if parsing_job else None,
                    'updated_at': document.updated_at.isoformat() if document.updated_at else None
                }

                return {'code': 200, 'status': 'success', 'data': status_info}, 200

            except Exception as e:
                current_app.logger.error(f"获取文档状态失败: {e}")
                return error_response("获取文档状态失败", str(e), 500)

    @knowledge_ns.route('/documents/<string:doc_id>/reparse')
    class DocumentReparse(Resource):
        @knowledge_ns.doc('reparse_document')
        @jwt_required()
        def put(self, doc_id):
            """重新解析知识文档

            对解析失败或需要重新处理的文档重新触发解析流程。
            """
            try:
                user_id = get_jwt_identity()

                document = KnowledgeDocument.query.filter_by(
                    id=doc_id, user_id=user_id
                ).first()

                if not document:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '文档不存在'}}, 404

                # 重置文档状态到队列中（与模型枚举一致）
                document.status = 'QUEUED'
                document.updated_at = datetime.utcnow()

                # 创建新的解析任务
                parsing_job = ParsingJob(
                    document_id=doc_id,
                    status='PENDING'
                )

                db.session.add(parsing_job)
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': {"message": "重新解析任务已创建", "docId": doc_id, "status": "QUEUED"}}, 200

            except Exception as e:
                current_app.logger.error(f"重新解析文档失败: {e}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '重新解析文档失败'}}, 500

    @knowledge_ns.route('/tags')
    class TagsList(Resource):
        @knowledge_ns.doc('get_all_tags')
        @jwt_required()
        def get(self):
            """获取所有标签

            获取系统中所有唯一的文档标签列表。
            """
            try:
                user_id = get_jwt_identity()

                # 获取用户所有文档的标签
                documents = KnowledgeDocument.query.filter_by(user_id=user_id).all()

                all_tags = set()
                for doc in documents:
                    if doc.tags:
                        all_tags.update(doc.tags)

                return {'code': 200, 'status': 'success', 'data': {
                    'tags': sorted(list(all_tags))
                }}, 200

            except Exception as e:
                current_app.logger.error(f"获取搜索建议失败: {e}")
                return error_response("获取搜索建议失败", str(e), 500)

    # 搜索相关接口
    search_model = knowledge_ns.model('SearchRequest', {
        'query': fields.String(required=True, description='搜索查询'),
        'top_k': fields.Integer(description='返回结果数量', default=5),
        'threshold': fields.Float(description='相似度阈值', default=0.7),
        'vendor': fields.String(description='厂商过滤'),
        'tags': fields.List(fields.String, description='标签过滤')
    })

    search_result_model = knowledge_ns.model('SearchResult', {
        'documents': fields.List(fields.Raw, description='搜索结果'),
        'total': fields.Integer(description='总数量'),
        'query': fields.String(description='搜索查询'),
        'suggestions': fields.List(fields.String, description='搜索建议')
    })

    # 文档重新解析请求模型
    reparse_model = knowledge_ns.model('ReparseRequest', {
        'force': fields.Boolean(description='是否强制重新解析', default=False)
    })

    # 搜索建议请求模型（用于Swagger UI输入）
    suggestion_request_model = knowledge_ns.model('SuggestionRequest', {
        'query': fields.String(required=True, description='查询前缀或关键词')
    })

    @knowledge_ns.route('/search')
    class KnowledgeSearch(Resource):
        @knowledge_ns.doc('search_knowledge')
        @knowledge_ns.doc(security='Bearer Auth')
        @knowledge_ns.expect(search_model)
        @jwt_required()
        def post(self):
            """知识库搜索

            在知识库中搜索相关文档和内容片段。
            """
            try:
                user_id = get_jwt_identity()
                data = request.get_json()

                if not data or not data.get('query'):
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '搜索查询不能为空'}}, 400

                query = data['query']
                top_k = data.get('top_k', 5)
                threshold = data.get('threshold', 0.7)
                vendor = data.get('vendor')
                tags = data.get('tags', [])

                # 这里应该调用实际的搜索服务
                # 暂时返回模拟数据
                results = {
                    'results': [],
                    'total': 0,
                    'query': query
                }
                return {'code': 200, 'status': 'success', 'data': results}, 200

            except Exception as e:
                current_app.logger.error(f"知识库搜索失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '知识库搜索失败'}}, 500

    @knowledge_ns.route('/search/suggest')
    class SearchSuggestions(Resource):
        @knowledge_ns.doc('get_search_suggestions')
        @knowledge_ns.doc(security='Bearer Auth')
        @knowledge_ns.expect(suggestion_request_model)
        @jwt_required()
        def post(self):
            """获取搜索建议

            根据用户输入提供搜索建议。
            """
            try:
                # 兼容非 JSON Content-Type 的请求
                data = request.get_json(silent=True) or {}
                query = data.get('query') or request.args.get('query') or request.form.get('query')

                if not query:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '查询参数不能为空'}}, 400

                # TODO: 调用实际建议服务
                suggestions = []

                return {'code': 200, 'status': 'success', 'data': {'suggestions': suggestions}}, 200

            except Exception as e:
                current_app.logger.exception(f"获取搜索建议失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取搜索建议失败'}}, 500
