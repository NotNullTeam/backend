"""
IP智慧解答专家系统 - 错误处理

本模块定义了全局错误处理器，确保API返回统一格式的错误响应。
"""

from flask import jsonify
from app import db


def register_error_handlers(app):
    """
    注册全局错误处理器

    统一错误响应格式:
    {
        'code': HTTP状态码,
        'status': 'error',
        'error': {
            'type': 错误类型,
            'message': 错误信息
        }
    }
    """

    @app.errorhandler(400)
    def bad_request(error):
        """处理400错误"""
        return jsonify({
            'code': 400,
            'status': 'error',
            'error': {
                'type': 'BAD_REQUEST',
                'message': '请求格式错误'
            }
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """处理401错误"""
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
        """处理403错误"""
        return jsonify({
            'code': 403,
            'status': 'error',
            'error': {
                'type': 'FORBIDDEN',
                'message': '权限不足'
            }
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        """处理404错误"""
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
        """处理409错误"""
        return jsonify({
            'code': 409,
            'status': 'error',
            'error': {
                'type': 'CONFLICT',
                'message': '资源冲突'
            }
        }), 409

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """处理422错误"""
        return jsonify({
            'code': 422,
            'status': 'error',
            'error': {
                'type': 'UNPROCESSABLE_ENTITY',
                'message': '请求无法处理'
            }
        }), 422

    @app.errorhandler(429)
    def too_many_requests(error):
        """处理429错误"""
        return jsonify({
            'code': 429,
            'status': 'error',
            'error': {
                'type': 'TOO_MANY_REQUESTS',
                'message': '请求过于频繁，请稍后再试'
            }
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        """处理500错误"""
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
        """处理503错误"""
        return jsonify({
            'code': 503,
            'status': 'error',
            'error': {
                'type': 'SERVICE_UNAVAILABLE',
                'message': '服务暂不可用，请稍后再试'
            }
        }), 503

    # JWT 错误处理器
    from app import jwt

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'code': 401,
            'status': 'error',
            'error': {
                'type': 'UNAUTHORIZED',
                'message': 'Token已过期'
            }
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'code': 401,
            'status': 'error',
            'error': {
                'type': 'UNAUTHORIZED',
                'message': '无效的Token'
            }
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'code': 401,
            'status': 'error',
            'error': {
                'type': 'UNAUTHORIZED',
                'message': '需要认证Token'
            }
        }), 401
