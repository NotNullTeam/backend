"""
文件管理 API 接口 (Flask-RESTX)

将原有的文件管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

import os
import uuid
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from flask import request, current_app, send_file, abort
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import files_ns
from app.models.files import UserFile
from app.utils.response_helper import success_response, error_response, validation_error, not_found_error, internal_error

# 支持的文件类型
ALLOWED_EXTENSIONS = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp'},
    'document': {'pdf', 'doc', 'docx', 'txt', 'md'},
    'config': {'cfg', 'conf', 'config', 'xml', 'json', 'yaml', 'yml'},
    'log': {'log', 'txt'},
    'archive': {'zip', 'tar', 'gz', 'rar', '7z'},
    'topo': {'vsd', 'vsdx', 'drawio', 'xml'}
}

ALL_ALLOWED_EXTENSIONS = set()
for exts in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(exts)

# 文件大小限制（字节）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALL_ALLOWED_EXTENSIONS

def get_file_type(filename):
    """根据文件扩展名推断文件类型"""
    if '.' not in filename:
        return 'other'
    
    ext = filename.rsplit('.', 1)[1].lower()
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return 'other'

def init_files_api():
    """初始化文件管理API接口"""
    
    # 文件信息模型
    file_model = files_ns.model('File', {
        'id': fields.String(description='文件ID'),
        'filename': fields.String(description='文件名'),
        'original_filename': fields.String(description='原始文件名'),
        'file_size': fields.Integer(description='文件大小（字节）'),
        'mime_type': fields.String(description='MIME类型'),
        'file_type': fields.String(description='文件类型'),
        'file_path': fields.String(description='文件路径'),
        'thumbnail_path': fields.String(description='缩略图路径'),
        'upload_time': fields.String(description='上传时间'),
        'user_id': fields.String(description='上传用户ID')
    })
    
    # 文件上传响应模型
    upload_response_model = files_ns.model('UploadResponse', {
        'file_id': fields.String(description='文件ID'),
        'filename': fields.String(description='文件名'),
        'file_size': fields.Integer(description='文件大小'),
        'file_type': fields.String(description='文件类型'),
        'upload_url': fields.String(description='访问URL')
    })
    
    # 批量上传响应模型
    batch_upload_response_model = files_ns.model('BatchUploadResponse', {
        'successful_uploads': fields.List(fields.Nested(upload_response_model), description='成功上传的文件'),
        'failed_uploads': fields.List(fields.Raw, description='上传失败的文件'),
        'total_count': fields.Integer(description='总文件数'),
        'success_count': fields.Integer(description='成功数量'),
        'failure_count': fields.Integer(description='失败数量')
    })

    @files_ns.route('/')
    class FileUpload(Resource):
        @files_ns.doc('upload_file')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.param('file', '要上传的文件', type='file', required=True, location='files')
        @files_ns.marshal_with(upload_response_model)
        @jwt_required()
        def post(self):
            """上传单个文件
            
            支持多种文件类型：图片、文档、配置文件、日志文件等。
            文件大小限制：普通文件50MB，图片文件10MB。
            """
            try:
                user_id = get_jwt_identity()
                
                if 'file' not in request.files:
                    return validation_error('未选择文件')
                
                file = request.files['file']
                if file.filename == '':
                    return validation_error('未选择文件')
                
                if not allowed_file(file.filename):
                    return validation_error('不支持的文件类型')
                
                # 检查文件大小
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                file_type = get_file_type(file.filename)
                max_size = MAX_IMAGE_SIZE if file_type == 'image' else MAX_FILE_SIZE
                
                if file_size > max_size:
                    return validation_error(f'文件大小超过限制（{max_size // (1024*1024)}MB）')
                
                # 生成安全的文件名
                original_filename = file.filename
                file_extension = original_filename.rsplit('.', 1)[1].lower()
                safe_filename = f"{uuid.uuid4().hex}.{file_extension}"
                
                # 确保上传目录存在
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], file_type)
                os.makedirs(upload_dir, exist_ok=True)
                
                # 保存文件
                file_path = os.path.join(upload_dir, safe_filename)
                file.save(file_path)
                
                # 为图片创建缩略图
                thumbnail_path = None
                if file_type == 'image':
                    try:
                        thumbnail_dir = os.path.join(upload_dir, 'thumbnails')
                        os.makedirs(thumbnail_dir, exist_ok=True)
                        thumbnail_path = os.path.join(thumbnail_dir, f"thumb_{safe_filename}")
                        
                        with Image.open(file_path) as img:
                            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                            img.save(thumbnail_path)
                    except Exception as e:
                        current_app.logger.warning(f"创建缩略图失败: {str(e)}")
                
                # 保存文件信息到数据库
                user_file = UserFile(
                    id=str(uuid.uuid4()),
                    filename=safe_filename,
                    original_filename=original_filename,
                    file_size=file_size,
                    mime_type=mimetypes.guess_type(original_filename)[0] or 'application/octet-stream',
                    file_type=file_type,
                    file_path=file_path,
                    thumbnail_path=thumbnail_path,
                    user_id=user_id,
                    upload_time=datetime.utcnow()
                )
                
                db.session.add(user_file)
                db.session.commit()
                
                return success_response(
                    message='文件上传成功',
                    data={
                        'file_id': user_file.id,
                        'filename': user_file.original_filename,
                        'file_size': user_file.file_size,
                        'file_type': user_file.file_type,
                        'upload_url': f'/api/v1/files/{user_file.id}'
                    }
                )
                
            except Exception as e:
                current_app.logger.error(f"文件上传失败: {str(e)}")
                return internal_error('文件上传失败')

    @files_ns.route('/batch')
    class BatchFileUpload(Resource):
        @files_ns.doc('upload_files_batch')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.param('files', '要上传的文件列表', type='file', required=True, location='files')
        @files_ns.marshal_with(batch_upload_response_model)
        @jwt_required()
        def post(self):
            """批量上传文件
            
            支持同时上传多个文件，返回每个文件的上传结果。
            """
            try:
                user_id = get_jwt_identity()
                
                if 'files' not in request.files:
                    return validation_error('未选择文件')
                
                files = request.files.getlist('files')
                if not files or all(f.filename == '' for f in files):
                    return validation_error('未选择文件')
                
                successful_uploads = []
                failed_uploads = []
                
                for file in files:
                    if file.filename == '':
                        continue
                    
                    try:
                        if not allowed_file(file.filename):
                            failed_uploads.append({
                                'filename': file.filename,
                                'error': '不支持的文件类型'
                            })
                            continue
                        
                        # 检查文件大小
                        file.seek(0, os.SEEK_END)
                        file_size = file.tell()
                        file.seek(0)
                        
                        file_type = get_file_type(file.filename)
                        max_size = MAX_IMAGE_SIZE if file_type == 'image' else MAX_FILE_SIZE
                        
                        if file_size > max_size:
                            failed_uploads.append({
                                'filename': file.filename,
                                'error': f'文件大小超过限制（{max_size // (1024*1024)}MB）'
                            })
                            continue
                        
                        # 处理文件上传逻辑（与单文件上传相同）
                        original_filename = file.filename
                        file_extension = original_filename.rsplit('.', 1)[1].lower()
                        safe_filename = f"{uuid.uuid4().hex}.{file_extension}"
                        
                        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], file_type)
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        file_path = os.path.join(upload_dir, safe_filename)
                        file.save(file_path)
                        
                        # 保存到数据库
                        user_file = UserFile(
                            id=str(uuid.uuid4()),
                            filename=safe_filename,
                            original_filename=original_filename,
                            file_size=file_size,
                            mime_type=mimetypes.guess_type(original_filename)[0] or 'application/octet-stream',
                            file_type=file_type,
                            file_path=file_path,
                            user_id=user_id,
                            upload_time=datetime.utcnow()
                        )
                        
                        db.session.add(user_file)
                        
                        successful_uploads.append({
                            'file_id': user_file.id,
                            'filename': user_file.original_filename,
                            'file_size': user_file.file_size,
                            'file_type': user_file.file_type,
                            'upload_url': f'/api/v1/files/{user_file.id}'
                        })
                        
                    except Exception as e:
                        failed_uploads.append({
                            'filename': file.filename,
                            'error': str(e)
                        })
                
                db.session.commit()
                
                return success_response(
                    message='批量上传完成',
                    data={
                        'successful_uploads': successful_uploads,
                        'failed_uploads': failed_uploads,
                        'total_count': len(files),
                        'success_count': len(successful_uploads),
                        'failure_count': len(failed_uploads)
                    }
                )
                
            except Exception as e:
                current_app.logger.error(f"批量文件上传失败: {str(e)}")
                return internal_error('批量文件上传失败')

    @files_ns.route('/<string:file_id>')
    class FileDetail(Resource):
        @files_ns.doc('get_file')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.param('download', '是否强制下载', type='boolean', default=False)
        @files_ns.param('thumbnail', '是否返回缩略图（仅图片）', type='boolean', default=False)
        @jwt_required()
        def get(self, file_id):
            """获取/下载文件
            
            根据文件ID获取文件内容，支持下载和缩略图模式。
            """
            try:
                user_id = get_jwt_identity()
                user_file = UserFile.query.filter_by(id=file_id, user_id=user_id).first()
                
                if not user_file:
                    return not_found_error('文件不存在')
                
                # 检查参数
                download = request.args.get('download', 'false').lower() == 'true'
                thumbnail = request.args.get('thumbnail', 'false').lower() == 'true'
                
                # 确定要返回的文件路径
                file_path = user_file.file_path
                if thumbnail and user_file.thumbnail_path and os.path.exists(user_file.thumbnail_path):
                    file_path = user_file.thumbnail_path
                
                if not os.path.exists(file_path):
                    return not_found_error('文件不存在')
                
                # 返回文件
                return send_file(
                    file_path,
                    as_attachment=download,
                    download_name=user_file.original_filename,
                    mimetype=user_file.mime_type
                )
                
            except Exception as e:
                current_app.logger.error(f"获取文件失败: {str(e)}")
                return internal_error('获取文件失败')

        @files_ns.doc('delete_file')
        @files_ns.doc(security='Bearer Auth')
        @jwt_required()
        def delete(self, file_id):
            """删除文件
            
            删除指定的文件及其相关数据。
            """
            try:
                user_id = get_jwt_identity()
                user_file = UserFile.query.filter_by(id=file_id, user_id=user_id).first()
                
                if not user_file:
                    return not_found_error('文件不存在')
                
                # 删除物理文件
                try:
                    if os.path.exists(user_file.file_path):
                        os.remove(user_file.file_path)
                    
                    if user_file.thumbnail_path and os.path.exists(user_file.thumbnail_path):
                        os.remove(user_file.thumbnail_path)
                except Exception as e:
                    current_app.logger.warning(f"删除物理文件失败: {str(e)}")
                
                # 删除数据库记录
                db.session.delete(user_file)
                db.session.commit()
                
                return success_response(message='文件删除成功')
                
            except Exception as e:
                current_app.logger.error(f"删除文件失败: {str(e)}")
                return internal_error('删除文件失败')

    @files_ns.route('/<string:file_id>/metadata')
    class FileMetadata(Resource):
        @files_ns.doc('get_file_metadata')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.marshal_with(file_model)
        @jwt_required()
        def get(self, file_id):
            """获取文件元数据
            
            返回文件的详细信息，不包含文件内容。
            """
            try:
                user_id = get_jwt_identity()
                user_file = UserFile.query.filter_by(id=file_id, user_id=user_id).first()
                
                if not user_file:
                    return not_found_error('文件不存在')
                
                return success_response(
                    message='获取文件元数据成功',
                    data=user_file.to_dict()
                )
                
            except Exception as e:
                current_app.logger.error(f"获取文件元数据失败: {str(e)}")
                return internal_error('获取文件元数据失败')

    print("✅ 文件管理API接口已注册到Flask-RESTX文档系统")
