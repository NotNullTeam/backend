"""
文件与附件接口路由

实现文件上传、下载、元数据管理等功能。
"""

import os
import uuid
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from flask import request, jsonify, current_app, send_file, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1.files import files_bp as bp
from app.models.files import UserFile
from app import db


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


def create_thumbnail(file_path, max_size=(200, 200)):
    """为图片创建缩略图"""
    try:
        with Image.open(file_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # 创建缩略图路径
            base_path, ext = os.path.splitext(file_path)
            thumbnail_path = f"{base_path}_thumb{ext}"

            # 保存缩略图
            img.save(thumbnail_path, optimize=True, quality=85)
            return thumbnail_path
    except Exception as e:
        current_app.logger.warning(f"Failed to create thumbnail for {file_path}: {str(e)}")
        return None


@bp.route('', methods=['POST'])
@jwt_required()
def upload_file():
    """
    上传单个文件

    对应文档: 5.1 上传单个文件
    Endpoint: POST /files
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
                'code': 422,
                'status': 'error',
                'error': {
                    'type': 'UNPROCESSABLE_ENTITY',
                    'message': f'不支持的文件类型，支持的扩展名: {", ".join(sorted(ALL_ALLOWED_EXTENSIONS))}'
                }
            }), 422

        # 检查文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'code': 422,
                'status': 'error',
                'error': {
                    'type': 'UNPROCESSABLE_ENTITY',
                    'message': f'文件大小超过限制，最大允许 {MAX_FILE_SIZE // 1024 // 1024}MB'
                }
            }), 422

        # 对图片文件有更严格的大小限制
        file_type = get_file_type(file.filename)
        if file_type == 'image' and file_size > MAX_IMAGE_SIZE:
            return jsonify({
                'code': 422,
                'status': 'error',
                'error': {
                    'type': 'UNPROCESSABLE_ENTITY',
                    'message': f'图片文件大小超过限制，最大允许 {MAX_IMAGE_SIZE // 1024 // 1024}MB'
                }
            }), 422

        # 获取表单数据
        user_file_type = request.form.get('fileType', file_type)
        description = request.form.get('description', '')

        # 处理文件保存
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        new_filename = f"{file_id}.{file_extension}" if file_extension else file_id

        # 创建上传目录
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, new_filename)

        # 保存文件
        file.save(file_path)
        current_app.logger.info(f"File saved to: {file_path}")

        # 创建缩略图（如果是图片）
        thumbnail_path = None
        if file_type == 'image':
            thumbnail_path = create_thumbnail(file_path)

        # 模拟安全扫描（实际项目中应集成真实的安全扫描服务）
        security_scan_status = 'clean'
        security_scan_time = datetime.utcnow()
        security_scan_details = {
            'scanEngine': 'MockScanner',
            'threats': [],
            'score': 100
        }

        # 保存文件记录
        user_file = UserFile(
            id=file_id,
            filename=new_filename,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=user_file_type,
            mime_type=file.content_type or mimetypes.guess_type(filename)[0],
            description=description,
            user_id=user_id,
            security_scan_status=security_scan_status,
            security_scan_time=security_scan_time,
            security_scan_details=security_scan_details
        )

        db.session.add(user_file)
        db.session.commit()

        return jsonify({
            'code': 201,
            'status': 'success',
            'data': {
                'file_info': {
                    'id': user_file.id,
                    'filename': user_file.original_filename,
                    'content_type': user_file.mime_type,
                    'size': user_file.file_size,
                    'description': user_file.description,
                    'url': f'/api/v1/files/{user_file.id}',
                    'uploaded_at': user_file.created_at.isoformat() + 'Z',
                    'security_scan': {
                        'status': user_file.security_scan_status,
                        'scan_time': user_file.security_scan_time.isoformat() + 'Z'
                    }
                }
            }
        }), 201

    except Exception as e:
        current_app.logger.error(f"Upload file error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '文件上传失败'
            }
        }), 500


@bp.route('/<file_id>', methods=['GET'])
@jwt_required()
def get_file(file_id):
    """
    获取/下载附件

    查询参数:
    - download: 是否强制下载 (可选)
    - thumbnail: 是否返回缩略图 (可选，仅图片)
    """
    try:
        user_id = get_jwt_identity()

        # 查找文件
        user_file = UserFile.query.filter_by(
            id=file_id,
            is_deleted=False
        ).first()

        if not user_file:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文件不存在'
                }
            }), 404

        # 检查权限（文件属于当前用户或在其案例中）
        if user_file.user_id != user_id:
            # TODO: 添加更复杂的权限检查，比如检查是否在用户的案例中被引用
            return jsonify({
                'code': 403,
                'status': 'error',
                'error': {
                    'type': 'FORBIDDEN',
                    'message': '无权访问该文件'
                }
            }), 403

        # 更新访问统计
        user_file.download_count += 1
        user_file.last_accessed = datetime.utcnow()
        db.session.commit()

        # 检查文件是否存在
        if not os.path.exists(user_file.file_path):
            current_app.logger.error(f"File not found on disk: {user_file.file_path}")
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文件不存在'
                }
            }), 404

        # 处理缩略图请求
        thumbnail = request.args.get('thumbnail', '').lower() == 'true'
        if thumbnail and user_file.file_type == 'image':
            base_path, ext = os.path.splitext(user_file.file_path)
            thumbnail_path = f"{base_path}_thumb{ext}"
            if os.path.exists(thumbnail_path):
                file_path = thumbnail_path
            else:
                # 如果缩略图不存在，尝试创建
                thumbnail_path = create_thumbnail(user_file.file_path)
                file_path = thumbnail_path if thumbnail_path and os.path.exists(thumbnail_path) else user_file.file_path
        else:
            file_path = user_file.file_path

        # 设置下载模式
        download = request.args.get('download', '').lower() == 'true'
        as_attachment = download

        return send_file(
            file_path,
            as_attachment=as_attachment,
            download_name=user_file.original_filename,
            mimetype=user_file.mime_type
        )

    except Exception as e:
        current_app.logger.error(f"Get file error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取文件时发生错误'
            }
        }), 500


@bp.route('/<file_id>/metadata', methods=['GET'])
@jwt_required()
def get_file_metadata(file_id):
    """获取文件元数据"""
    try:
        user_id = get_jwt_identity()

        # 查找文件
        user_file = UserFile.query.filter_by(
            id=file_id,
            is_deleted=False
        ).first()

        if not user_file:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文件不存在'
                }
            }), 404

        # 检查权限
        if user_file.user_id != user_id:
            return jsonify({
                'code': 403,
                'status': 'error',
                'error': {
                    'type': 'FORBIDDEN',
                    'message': '无权访问该文件'
                }
            }), 403

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'metadata': user_file.to_dict()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get file metadata error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取文件元数据时发生错误'
            }
        }), 500


@bp.route('/batch', methods=['POST'])
@jwt_required()
def upload_files_batch():
    """
    批量上传附件

    支持多个files[]字段
    """
    try:
        user_id = get_jwt_identity()

        # 获取所有文件
        files = request.files.getlist('files[]') or request.files.getlist('files')

        if not files:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '没有选择文件'
                }
            }), 400

        upload_results = []
        successful_count = 0
        failed_count = 0

        for file in files:
            result = {
                'fileName': file.filename,
                'status': 'failed',
                'error': None,
                'fileId': None,
                'url': None
            }

            try:
                # 基本验证
                if file.filename == '':
                    result['error'] = '文件名为空'
                    upload_results.append(result)
                    failed_count += 1
                    continue

                if not allowed_file(file.filename):
                    result['error'] = '不支持的文件类型'
                    upload_results.append(result)
                    failed_count += 1
                    continue

                # 检查文件大小
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                if file_size > MAX_FILE_SIZE:
                    result['error'] = f'文件大小超过限制（{MAX_FILE_SIZE // 1024 // 1024}MB）'
                    upload_results.append(result)
                    failed_count += 1
                    continue

                file_type = get_file_type(file.filename)
                if file_type == 'image' and file_size > MAX_IMAGE_SIZE:
                    result['error'] = f'图片文件大小超过限制（{MAX_IMAGE_SIZE // 1024 // 1024}MB）'
                    upload_results.append(result)
                    failed_count += 1
                    continue

                # 保存文件
                filename = secure_filename(file.filename)
                file_id = str(uuid.uuid4())
                file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                new_filename = f"{file_id}.{file_extension}" if file_extension else file_id

                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, new_filename)

                file.save(file_path)

                # 创建缩略图
                if file_type == 'image':
                    create_thumbnail(file_path)

                # 模拟安全扫描
                security_scan_status = 'clean'
                security_scan_time = datetime.utcnow()

                # 保存记录
                user_file = UserFile(
                    id=file_id,
                    filename=new_filename,
                    original_filename=filename,
                    file_path=file_path,
                    file_size=file_size,
                    file_type=file_type,
                    mime_type=file.content_type or mimetypes.guess_type(filename)[0],
                    user_id=user_id,
                    security_scan_status=security_scan_status,
                    security_scan_time=security_scan_time
                )

                db.session.add(user_file)
                db.session.flush()  # 获取ID

                result['status'] = 'success'
                result['fileId'] = user_file.id
                result['url'] = f'/api/v1/files/{user_file.id}'
                successful_count += 1

            except Exception as e:
                result['error'] = str(e)
                failed_count += 1
                current_app.logger.error(f"Batch upload file {file.filename} error: {str(e)}")

            upload_results.append(result)

        # 提交事务
        if successful_count > 0:
            db.session.commit()
        else:
            db.session.rollback()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'uploadResults': upload_results,
                'summary': {
                    'total': len(files),
                    'successful': successful_count,
                    'failed': failed_count
                }
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Batch upload error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '批量上传时发生错误'
            }
        }), 500


@bp.route('/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    """
    删除指定的文件

    对应文档: 5.4 删除文件
    Endpoint: DELETE /files/{fileId}
    """
    try:
        user_id = get_jwt_identity()
        user_file = db.session.get(UserFile, file_id)

        if not user_file:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '文件不存在'
                }
            }), 404

        # 仅文件所有者可以删除
        if user_file.user_id != user_id:
            return jsonify({
                'code': 403,
                'status': 'error',
                'error': {
                    'type': 'FORBIDDEN',
                    'message': '无权删除此文件'
                }
            }), 403

        # 删除物理文件
        try:
            if os.path.exists(user_file.file_path):
                os.remove(user_file.file_path)

            # 如果是图片，尝试删除缩略图
            if user_file.file_type == 'image':
                base_path, ext = os.path.splitext(user_file.file_path)
                thumbnail_path = f"{base_path}_thumb{ext}"
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)

        except OSError as e:
            current_app.logger.error(f"Error deleting physical file {user_file.file_path}: {str(e)}")
            # 即使物理文件删除失败，也继续删除数据库记录，以避免悬空引用

        # 从数据库删除记录
        db.session.delete(user_file)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting file record {file_id}: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '删除文件时发生错误'
            }
        }), 500
