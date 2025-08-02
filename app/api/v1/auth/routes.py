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
        return jsonify({
            'code': 400,
            'status': 'error',
            'error': {
                'type': 'INVALID_REQUEST',
                'message': '请求参数格式错误'
            }
        }), 400

    try:
        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '用户名和密码不能为空'
                }
            }), 400

        # 查找用户
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password) or not user.is_active:
            return jsonify({
                'code': 401,
                'status': 'error',
                'error': {
                    'type': 'UNAUTHORIZED',
                    'message': '用户名或密码错误'
                }
            }), 401

        # 创建访问令牌和刷新令牌
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        # 更新用户最后登录时间
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()) if hasattr(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'], 'total_seconds') else current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
                'user_info': user.to_dict()
            }
        })

    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '登录过程中发生错误'
            }
        }), 500


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
@jwt_required(refresh=True)
def refresh():
    """
    刷新访问令牌接口

    Returns:
        JSON: 包含新访问令牌的响应
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)

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
                'expires_in': current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
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
        JSON: 当前用户信息
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '用户不存在'
                }
            }), 404

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': user.to_dict()
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
