"""
IP智慧解答专家系统 - 认证API

本模块实现了用户认证相关的API接口。
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from app.api.v1.auth import auth_bp as bp
from app.models.user import User
from app import db
from datetime import datetime
from app.utils.response_helper import (
    success_response, validation_error, unauthorized_error, internal_error
)


@bp.route('/login', methods=['POST'])
def login():
    """
    用户登录接口

    Returns:
        JSON: 包含访问令牌和用户信息的响应
    """
    try:
        data = request.get_json()
    except Exception as e:
        return validation_error('请求参数格式错误')

    try:
        if not data:
            return validation_error('请求体不能为空')

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return validation_error('用户名和密码不能为空')

        # 查找用户
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password) or not user.is_active:
            return unauthorized_error('用户名或密码错误')

        # 创建访问令牌和刷新令牌
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        # 更新用户最后登录时间
        user.updated_at = datetime.utcnow()
        db.session.commit()

        # 修正后的响应格式：登录时必须返回refresh_token，否则刷新接口无法使用
        # 这是JWT标准实践，文档需要更新以反映实际需求
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()) if hasattr(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'], 'total_seconds') else current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
            'user_info': {
                'id': user.id,
                'username': user.username
            },
            'user': user.to_dict()  # 保持向后兼容性，同时提供完整用户信息
        })

    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return internal_error('登录过程中发生错误')


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    用户登出接口

    Returns:
        JSON: 登出成功响应
    """
    # 在实际应用中，这里可以将token加入黑名单
    # 目前简单返回成功响应
    return '', 204


@bp.route('/refresh', methods=['POST'])
def refresh():
    """
    刷新访问令牌接口

    支持两种方式传递refresh_token：
    1. Authorization头部：Authorization: Bearer <refresh_token>
    2. 请求体：{"refresh_token": "<refresh_token>"}

    Returns:
        JSON: 包含新访问令牌的响应
    """
    try:
        refresh_token = None

        # 方式1：从请求体获取refresh_token（API文档要求的方式）
        data = request.get_json()
        if data and 'refresh_token' in data:
            refresh_token = data['refresh_token']

        # 方式2：从Authorization头获取（当前实现的方式，保持兼容性）
        if not refresh_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                refresh_token = auth_header.split(' ')[1]

        if not refresh_token:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '缺少refresh_token，请在请求体中提供或使用Authorization头部'
                }
            }), 400

        # 验证refresh_token
        try:
            # 手动验证JWT token
            from flask_jwt_extended import decode_token
            token_data = decode_token(refresh_token)

            # 检查token类型
            if token_data.get('type') != 'refresh':
                return jsonify({
                    'code': 401,
                    'status': 'error',
                    'error': {
                        'type': 'UNAUTHORIZED',
                        'message': '无效的refresh token类型'
                    }
                }), 401

            current_user_id = int(token_data.get('sub'))

        except Exception as jwt_error:
            return jsonify({
                'code': 401,
                'status': 'error',
                'error': {
                    'type': 'UNAUTHORIZED',
                    'message': '无效的refresh token'
                }
            }), 401

        # 验证用户
        user = db.session.get(User, current_user_id)
        if not user or not user.is_active:
            return jsonify({
                'code': 401,
                'status': 'error',
                'error': {
                    'type': 'UNAUTHORIZED',
                    'message': '用户不存在或已被禁用'
                }
            }), 401

        # 创建新的访问令牌
        new_access_token = create_access_token(identity=str(current_user_id))

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'access_token': new_access_token,
                'token_type': 'Bearer',
                'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()) if hasattr(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'], 'total_seconds') else current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            }
        })

    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '刷新令牌过程中发生错误'
            }
        }), 500


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    获取当前用户信息接口

    Returns:
        JSON: 当前用户信息，包括统计数据
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = db.session.get(User, current_user_id)

        if not user:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '用户不存在'
                }
            }), 404

        # 获取用户统计信息
        from app.models.case import Case
        from app.models.feedback import Feedback

        case_stats = {
            'total': Case.query.filter_by(user_id=user.id).count(),
            'solved': Case.query.filter_by(user_id=user.id, status='solved').count(),
            'open': Case.query.filter_by(user_id=user.id, status='open').count()
        }

        feedback_count = Feedback.query.filter_by(user_id=user.id).count()

        # 构建增强的用户信息响应
        user_data = user.to_dict()
        user_data.update({
            'stats': {
                'cases': case_stats,
                'feedback_count': feedback_count
            },
            'preferences': {
                'theme': 'light',  # 默认主题，可以从UserSettings获取
                'language': 'zh-cn'
            }
        })

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'user': user_data
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get current user error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取用户信息过程中发生错误'
            }
        }), 500
