"""
API装饰器

提供通用的API装饰器功能。
"""

from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app import db
import logging

logger = logging.getLogger(__name__)

def handle_exceptions(func):
    """
    异常处理装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API异常 in {func.__name__}: {str(e)}")
            return jsonify({
                'code': 500,
                'status': 'error',
                'error': {
                    'type': 'INTERNAL_ERROR',
                    'message': '服务器内部错误'
                }
            }), 500
    return wrapper

def admin_required(func):
    """
    管理员权限装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()

        # 这里需要根据实际的用户模型来检查权限
        from app.models.user import User
        user = db.session.get(User, user_id)

        if not user or not user.has_role('admin'):
            return jsonify({
                'code': 403,
                'status': 'error',
                'error': {
                    'type': 'FORBIDDEN',
                    'message': '需要管理员权限'
                }
            }), 403

        return func(*args, **kwargs)
    return wrapper

def rate_limit(requests_per_minute: int = 60):
    """
    速率限制装饰器

    Args:
        requests_per_minute: 每分钟允许的请求数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 这里可以实现基于Redis的速率限制
            # 简化实现，实际项目中应该使用Flask-Limiter
            return func(*args, **kwargs)
        return wrapper
    return decorator
