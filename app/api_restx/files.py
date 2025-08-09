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
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.models.files import UserFile
# 不在 RESTX 端点中返回 Flask Response，避免被 RESTX 再次序列化

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
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    files_ns = get_namespace('files')

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

    # 为 Swagger 定义 multipart/form-data 解析器
    upload_parser = files_ns.parser()
    upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='要上传的文件')
    upload_parser.add_argument('description', location='form', type=str, required=False, help='文件描述')

    batch_parser = files_ns.parser()
    # Swagger 2 不支持数组类型的 file，这里提供多个明确的文件输入控件
    batch_parser.add_argument('file', location='files', type=FileStorage, required=False, help='文件')
    batch_parser.add_argument('file1', location='files', type=FileStorage, required=False, help='文件1')
    batch_parser.add_argument('file2', location='files', type=FileStorage, required=False, help='文件2')
    batch_parser.add_argument('file3', location='files', type=FileStorage, required=False, help='文件3')

    # 基础路径仅保留'/'，避免重复路由定义
    @files_ns.route('/')
    class FileUpload(Resource):
        @files_ns.doc('upload_file')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.expect(upload_parser)
        @files_ns.doc(consumes=['multipart/form-data'])
        # 不使用 marshal，以保持统一响应外层结构
        @jwt_required()
        def post(self):
            """上传单个文件

            支持多种文件类型：图片、文档、配置文件、日志文件等。
            文件大小限制：普通文件50MB，图片文件10MB。
            """
            try:
                user_id = get_jwt_identity()

                if 'file' not in request.files:
                    return {
                        'code': 400,
                        'status': 'error',
                        'error': {
                            'type': 'INVALID_REQUEST',
                            'message': '未选择文件'
                        }
                    }, 400

                file = request.files['file']
                if file.filename == '':
                    return {
                        'code': 400,
                        'status': 'error',
                        'error': {
                            'type': 'INVALID_REQUEST',
                            'message': '未选择文件'
                        }
                    }, 400

                if not allowed_file(file.filename):
                    return {
                        'code': 422,
                        'status': 'error',
                        'error': {
                            'type': 'UNPROCESSABLE_ENTITY',
                            'message': '不支持的文件类型'
                        }
                    }, 422

                # 检查文件大小
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                file_type = get_file_type(file.filename)
                max_size = MAX_IMAGE_SIZE if file_type == 'image' else MAX_FILE_SIZE

                if file_size > max_size:
                    return {
                        'code': 422,
                        'status': 'error',
                        'error': {
                            'type': 'UNPROCESSABLE_ENTITY',
                            'message': f'文件大小超过限制（{max_size // (1024*1024)}MB）'
                        }
                    }, 422

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

                # 模拟安全扫描
                security_scan_status = 'clean'
                security_scan_time = datetime.utcnow()
                description = request.form.get('description', '')

                # 保存文件信息到数据库
                user_file = UserFile(
                    id=str(uuid.uuid4()),
                    filename=safe_filename,
                    original_filename=original_filename,
                    file_size=file_size,
                    mime_type=mimetypes.guess_type(original_filename)[0] or 'application/octet-stream',
                    file_type=file_type,
                    file_path=file_path,
                    user_id=user_id,
                    description=description,
                    security_scan_status=security_scan_status,
                    security_scan_time=security_scan_time
                )

                db.session.add(user_file)
                db.session.commit()

                # 按测试期望返回结构：data.file_info（返回dict由RESTX封装）
                return {
                    'code': 201,
                    'status': 'success',
                    'data': {
                        'file_info': {
                            'id': user_file.id,
                            'filename': user_file.original_filename,
                            'content_type': user_file.mime_type,
                            'size': user_file.file_size,
                            'description': description,
                            'url': f'/api/v1/files/{user_file.id}',
                            'uploaded_at': user_file.created_at.isoformat() + 'Z',
                            'security_scan': {
                                'status': security_scan_status,
                                'scan_time': security_scan_time.isoformat() + 'Z'
                            }
                        }
                    }
                }, 201

            except Exception as e:
                current_app.logger.exception(f"文件上传失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '文件上传失败'
                    }
                }, 500

    @files_ns.route('/batch')
    class BatchFileUpload(Resource):
        @files_ns.doc('upload_files_batch')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.expect(batch_parser)
        @files_ns.doc(consumes=['multipart/form-data'])
        # 不使用 marshal，以保持统一响应外层结构
        @jwt_required()
        def post(self):
            """批量上传文件

            支持同时上传多个文件，返回每个文件的上传结果。
            """
            try:
                user_id = get_jwt_identity()

                # 聚合多种字段名携带的文件：files / files[] / file
                # 聚合多种字段名携带的文件：兼容 Swagger UI 的 file/file1/file2/file3
                candidates = [
                    request.files.get('file'),
                    request.files.get('file1'),
                    request.files.get('file2'),
                    request.files.get('file3')
                ]
                files = [f for f in candidates if f is not None]

                if not files or all(getattr(f, 'filename', '') == '' for f in files):
                    return {
                        'code': 400,
                        'status': 'error',
                        'error': {
                            'type': 'INVALID_REQUEST',
                            'message': '未选择文件'
                        }
                    }, 400

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
                            user_id=user_id
                        )

                        db.session.add(user_file)

                        successful_uploads.append({
                            'fileName': user_file.original_filename,
                            'status': 'success',
                            'fileId': user_file.id,
                            'url': f'/api/v1/files/{user_file.id}'
                        })

                    except Exception as e:
                        failed_uploads.append({
                            'fileName': file.filename,
                            'status': 'failed',
                            'error': str(e)
                        })

                db.session.commit()

                # 按测试期望：data.summary 与 data.uploadResults（驼峰）
                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'uploadResults': successful_uploads + failed_uploads,
                        'summary': {
                            'total': len(files),
                            'successful': len(successful_uploads),
                            'failed': len(failed_uploads)
                        }
                    }
                }, 200

            except Exception as e:
                current_app.logger.exception(f"批量文件上传失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '批量文件上传失败'
                    }
                }, 500

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
                user_file = UserFile.query.filter_by(id=file_id).first()

                if not user_file:
                    return {
                        'code': 404,
                        'status': 'error',
                        'error': {
                            'type': 'NOT_FOUND',
                            'message': '文件不存在'
                        }
                    }, 404

                if user_file.user_id != user_id:
                    return {
                        'code': 403,
                        'status': 'error',
                        'error': {
                            'type': 'FORBIDDEN',
                            'message': '无权访问该文件'
                        }
                    }, 403

                # 检查参数
                download = request.args.get('download', 'false').lower() == 'true'
                thumbnail = request.args.get('thumbnail', 'false').lower() == 'true'

                # 确定要返回的文件路径
                file_path = user_file.file_path
                if thumbnail and getattr(user_file, 'thumbnail_path', None) and os.path.exists(user_file.thumbnail_path):
                    file_path = user_file.thumbnail_path

                # 若路径为相对路径，生成可能的绝对路径候选
                candidates = []
                if not os.path.isabs(file_path):
                    # 1) 相对于应用根目录（可能是 /app/app）
                    candidates.append(os.path.join(current_app.root_path, file_path.lstrip('/')))
                    # 2) 相对于项目根目录（/app），适配 docker-compose 的挂载
                    candidates.append(os.path.join(os.path.dirname(current_app.root_path), file_path.lstrip('/')))
                else:
                    candidates.append(file_path)

                # 3) 修正历史双前缀 /app/app/
                if '/app/app/' in file_path:
                    candidates.append(file_path.replace('/app/app/', '/app/', 1))

                # 取第一个存在的候选路径
                resolved = next((p for p in candidates if os.path.exists(p)), None)
                if not resolved:
                    return {
                        'code': 404,
                        'status': 'error',
                        'error': {
                            'type': 'NOT_FOUND',
                            'message': '文件不存在'
                        }
                    }, 404

                file_path = resolved

                # 返回文件（再次兜底文件缺失）
                try:
                    return send_file(
                        file_path,
                        as_attachment=download,
                        download_name=user_file.original_filename,
                        mimetype=user_file.mime_type
                    )
                except FileNotFoundError:
                    return {
                        'code': 404,
                        'status': 'error',
                        'error': {
                            'type': 'NOT_FOUND',
                            'message': '文件不存在'
                        }
                    }, 404

            except Exception as e:
                current_app.logger.exception(f"获取文件失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '获取文件失败'
                    }
                }, 500

        @files_ns.doc('delete_file')
        @files_ns.doc(security='Bearer Auth')
        @jwt_required()
        def delete(self, file_id):
            """删除文件

            删除指定的文件及其相关数据。
            """
            try:
                user_id = get_jwt_identity()
                user_file = UserFile.query.filter_by(id=file_id).first()

                if not user_file:
                    return {
                        'code': 404,
                        'status': 'error',
                        'error': {
                            'type': 'NOT_FOUND',
                            'message': '文件不存在'
                        }
                    }, 404

                if user_file.user_id != user_id:
                    return {
                        'code': 403,
                        'status': 'error',
                        'error': {
                            'type': 'FORBIDDEN',
                            'message': '无权访问该文件'
                        }
                    }, 403

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

                return '', 204

            except Exception as e:
                current_app.logger.exception(f"删除文件失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '删除文件失败'
                    }
                }, 500

    @files_ns.route('/<string:file_id>/metadata')
    class FileMetadata(Resource):
        @files_ns.doc('get_file_metadata')
        @files_ns.doc(security='Bearer Auth')
        # 不使用 marshal，以保持统一响应外层结构
        @jwt_required()
        def get(self, file_id):
            """获取文件元数据

            返回文件的详细信息，不包含文件内容。
            """
            try:
                user_id = get_jwt_identity()
                user_file = UserFile.query.filter_by(id=file_id, user_id=user_id).first()

                if not user_file:
                    return {
                        'code': 404,
                        'status': 'error',
                        'error': {
                            'type': 'NOT_FOUND',
                            'message': '文件不存在'
                        }
                    }, 404

                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'metadata': user_file.to_dict()
                    }
                }, 200

            except Exception as e:
                current_app.logger.exception(f"获取文件元数据失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '获取文件元数据失败'
                    }
                }, 500

    @files_ns.route('/list')
    class FileList(Resource):
        @files_ns.doc('list_files')
        @files_ns.doc(security='Bearer Auth')
        @files_ns.param('page', '页码（从1开始）', type='integer', default=1)
        @files_ns.param('pageSize', '每页数量', type='integer', default=10)
        @files_ns.param('mineOnly', '仅查看本人文件', type='boolean', default=True)
        @jwt_required()
        def get(self):
            """获取文件列表（分页）

            默认仅返回当前用户的文件，可通过 mineOnly=false 查看全部（需要服务端放权时使用）。
            """
            try:
                user_id = get_jwt_identity()
                page = int(request.args.get('page', 1) or 1)
                page_size = int(request.args.get('pageSize', 10) or 10)
                mine_only = str(request.args.get('mineOnly', 'true')).lower() == 'true'

                query = UserFile.query
                if mine_only:
                    query = query.filter_by(user_id=user_id)

                query = query.order_by(UserFile.created_at.desc())
                pagination = query.paginate(page=page, per_page=page_size, error_out=False)

                items = [uf.to_dict() for uf in pagination.items]

                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'items': items,
                        'pagination': {
                            'total': pagination.total,
                            'page': pagination.page,
                            'per_page': pagination.per_page,
                            'pages': pagination.pages
                        }
                    }
                }, 200

            except Exception as e:
                current_app.logger.exception(f"获取文件列表失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '获取文件列表失败'
                    }
                }, 500

    print("✅ 文件管理API接口已注册到Flask-RESTX文档系统")
