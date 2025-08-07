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
from app.docs import knowledge_ns
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.utils.response_helper import success_response, error_response
from datetime import datetime

# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_knowledge_api():
    """初始化知识库API接口"""
    # 直接使用导入的 knowledge_ns 命名空间
    
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
        @knowledge_ns.marshal_with(documents_list_model)
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
                
                # 分页
                total = query.count()
                documents = query.offset((page - 1) * page_size).limit(page_size).all()
                
                result = {
                    'documents': [doc.to_dict() for doc in documents],
                    'total': total,
                    'page': page,
                    'pageSize': page_size,
                    'totalPages': (total + page_size - 1) // page_size
                }
                
                return success_response(result)
                
            except Exception as e:
                current_app.logger.error(f"获取文档列表失败: {e}")
                return error_response("获取文档列表失败", str(e), 500)

        @knowledge_ns.doc('upload_document')
        @knowledge_ns.marshal_with(upload_response_model)
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
                    return error_response("没有选择文件", "INVALID_REQUEST", 400)
                
                file = request.files['file']
                if file.filename == '':
                    return error_response("没有选择文件", "INVALID_REQUEST", 400)
                
                if not allowed_file(file.filename):
                    return error_response(
                        f"不支持的文件类型，支持的类型: {', '.join(ALLOWED_EXTENSIONS)}", 
                        "UNSUPPORTED_FILE_TYPE", 400
                    )
                
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
                    'document_id': file_id,
                    'filename': filename,
                    'status': 'uploaded'
                }
                
                return success_response(result, 201)
                
            except Exception as e:
                current_app.logger.error(f"文档上传失败: {e}")
                return error_response("文档上传失败", str(e), 500)

    @knowledge_ns.route('/documents/<string:doc_id>')
    class DocumentDetail(Resource):
        @knowledge_ns.doc('get_document_detail')
        @knowledge_ns.marshal_with(document_model)
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
                    return error_response("文档不存在", "NOT_FOUND", 404)
                
                return success_response(document.to_dict())
                
            except Exception as e:
                current_app.logger.error(f"获取文档详情失败: {e}")
                return error_response("获取文档详情失败", str(e), 500)

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
                    return error_response("文档不存在", "NOT_FOUND", 404)
                
                # 更新元数据
                if 'tags' in data:
                    document.tags = data['tags']
                if 'vendor' in data:
                    document.vendor = data['vendor']
                
                document.updated_at = datetime.utcnow()
                db.session.commit()
                
                return success_response(document.to_dict())
                
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
                    return error_response("文档不存在", "NOT_FOUND", 404)
                
                # 删除文件
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)
                
                # 删除数据库记录
                db.session.delete(document)
                db.session.commit()
                
                return success_response({"message": "文档删除成功"})
                
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
                    return error_response("文档不存在", "NOT_FOUND", 404)
                
                # 获取解析任务状态
                parsing_job = ParsingJob.query.filter_by(document_id=doc_id).first()
                
                status_info = {
                    'document_id': doc_id,
                    'status': document.status,
                    'parsing_progress': parsing_job.progress if parsing_job else 0,
                    'error_message': parsing_job.error_message if parsing_job else None,
                    'updated_at': document.updated_at.isoformat() if document.updated_at else None
                }
                
                return success_response(status_info)
                
            except Exception as e:
                current_app.logger.error(f"获取文档状态失败: {e}")
                return error_response("获取文档状态失败", str(e), 500)

    @knowledge_ns.route('/documents/<string:doc_id>/reparse')
    class DocumentReparse(Resource):
        @knowledge_ns.doc('reparse_document')
        @jwt_required()
        def post(self, doc_id):
            """重新解析知识文档
            
            对解析失败或需要重新处理的文档重新触发解析流程。
            """
            try:
                user_id = get_jwt_identity()
                
                document = KnowledgeDocument.query.filter_by(
                    id=doc_id, user_id=user_id
                ).first()
                
                if not document:
                    return error_response("文档不存在", "NOT_FOUND", 404)
                
                # 重置文档状态
                document.status = 'pending'
                document.updated_at = datetime.utcnow()
                
                # 创建新的解析任务
                parsing_job = ParsingJob(
                    document_id=doc_id,
                    status='pending',
                    progress=0
                )
                
                db.session.add(parsing_job)
                db.session.commit()
                
                return success_response({
                    "message": "重新解析任务已创建",
                    "document_id": doc_id,
                    "status": "pending"
                })
                
            except Exception as e:
                current_app.logger.error(f"重新解析文档失败: {e}")
                return error_response("重新解析文档失败", str(e), 500)

    @knowledge_ns.route('/tags')
    class TagsList(Resource):
        @knowledge_ns.doc('get_all_tags')
        @knowledge_ns.marshal_with(tags_model)
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
                
                return success_response({
                    'tags': sorted(list(all_tags))
                })
                
            except Exception as e:
                current_app.logger.error(f"获取标签列表失败: {e}")
                return error_response("获取标签列表失败", str(e), 500)

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

    @knowledge_ns.route('/search')
    class KnowledgeSearch(Resource):
        @knowledge_ns.doc('search_knowledge')
        @knowledge_ns.doc(security='Bearer Auth')
        @knowledge_ns.expect(search_model)
        @knowledge_ns.marshal_with(search_result_model)
        @jwt_required()
        def post(self):
            """知识库搜索
            
            在知识库中搜索相关文档和内容片段。
            """
            try:
                user_id = get_jwt_identity()
                data = request.get_json()
                
                if not data or not data.get('query'):
                    return validation_error('搜索查询不能为空')
                
                query = data['query']
                top_k = data.get('top_k', 5)
                threshold = data.get('threshold', 0.7)
                vendor = data.get('vendor')
                tags = data.get('tags', [])
                
                # 这里应该调用实际的搜索服务
                # 暂时返回模拟数据
                results = {
                    'documents': [],
                    'total': 0,
                    'query': query,
                    'suggestions': []
                }
                
                return success_response(
                    message='知识库搜索成功',
                    data=results
                )
                
            except Exception as e:
                current_app.logger.error(f"知识库搜索失败: {str(e)}")
                return internal_error('知识库搜索失败')

    @knowledge_ns.route('/search/suggest')
    class SearchSuggestions(Resource):
        @knowledge_ns.doc('get_search_suggestions')
        @knowledge_ns.doc(security='Bearer Auth')
        @jwt_required()
        def post(self):
            """获取搜索建议
            
            根据用户输入提供搜索建议。
            """
            try:
                data = request.get_json()
                query = data.get('query') if data else None
                
                if not query:
                    return validation_error('查询参数不能为空')
                
                # 这里应该调用实际的建议服务
                suggestions = []
                
                return success_response(
                    message='获取搜索建议成功',
                    data={'suggestions': suggestions}
                )
                
            except Exception as e:
                current_app.logger.error(f"获取搜索建议失败: {str(e)}")
                return internal_error('获取搜索建议失败')

    @knowledge_ns.route('/documents/<string:doc_id>/reparse')
    class DocumentReparse(Resource):
        @knowledge_ns.doc('reparse_document')
        @knowledge_ns.doc(security='Bearer Auth')
        @knowledge_ns.expect(reparse_model)
        @jwt_required()
        def put(self, doc_id):
            """重新解析文档
            
            对解析失败或需要重新处理的文档重新触发解析流水线。
            """
            try:
                user_id = get_jwt_identity()
                document = KnowledgeDocument.query.filter_by(id=doc_id).first()
                
                if not document:
                    return not_found_error('文档不存在')
                
                # 检查权限
                if document.created_by != user_id:
                    return error_response('无权限操作此文档', 403)
                
                data = request.get_json() or {}
                force = data.get('force', False)
                
                # 这里应该调用实际的重新解析服务
                document.status = 'parsing'
                document.updated_at = datetime.utcnow()
                db.session.commit()
                
                return success_response(
                    message='文档重新解析已启动',
                    data=document.to_dict()
                )
                
            except Exception as e:
                current_app.logger.error(f"重新解析文档失败: {str(e)}")
                return internal_error('重新解析文档失败')
