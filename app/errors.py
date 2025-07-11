"""
IP智慧解答专家系统 - 错误处理

本模块定义了全局错误处理器，确保API返回统一格式的错误响应。
"""

from flask import jsonify
from app import db


def register_error_handlers(app):
    """
    注册全局错误处理器
    
    Args:
        app: Flask应用实例
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """处理400错误 - 请求参数错误"""
        return jsonify({
            'code': 400,
            'status': 'error',
            'error': {
                'type': 'INVALID_REQUEST',
                'message': '请求参数错误'
            }
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """处理401错误 - 未认证"""
        return jsonify({
            'code': 401,
            'status': 'error',
            'error': {
                'type': 'UNAUTHORIZED',
                'message': '未授权访问'
            }
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """处理403错误 - 无权限"""
        return jsonify({
            'code': 403,
            'status': 'error',
            'error': {
                'type': 'FORBIDDEN',
                'message': '无权限访问该资源'
            }
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        """处理404错误 - 资源不存在"""
        return jsonify({
            'code': 404,
            'status': 'error',
            'error': {
                'type': 'NOT_FOUND',
                'message': '请求的资源不存在'
            }
        }), 404

    @app.errorhandler(409)
    def conflict(error):
        """处理409错误 - 资源冲突"""
        return jsonify({
            'code': 409,
            'status': 'error',
            'error': {
                'type': 'CONFLICT',
                'message': '资源状态冲突'
            }
        }), 409

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """处理422错误 - 业务规则校验失败"""
        return jsonify({
            'code': 422,
            'status': 'error',
            'error': {
                'type': 'UNPROCESSABLE_ENTITY',
                'message': '请求格式正确，但不满足业务规则'
            }
        }), 422

    @app.errorhandler(429)
    def rate_limited(error):
        """处理429错误 - 触发限流"""
        return jsonify({
            'code': 429,
            'status': 'error',
            'error': {
                'type': 'RATE_LIMITED',
                'message': '请求过于频繁，请稍后再试'
            }
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        """处理500错误 - 服务器内部错误"""
        db.session.rollback()
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '服务器内部错误'
            }
        }), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """处理503错误 - 服务暂不可用"""
        return jsonify({
            'code': 503,
            'status': 'error',
            'error': {
                'type': 'SERVICE_UNAVAILABLE',
                'message': '服务暂不可用，请稍后再试'
            }
        }), 503
