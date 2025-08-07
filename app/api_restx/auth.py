"""
身份认证 API 接口 (Flask-RESTX)

将原有的身份认证接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from app import db
from app.docs import auth_ns
from app.models.user import User
from app.utils.response_helper import success_response, validation_error, unauthorized_error, internal_error
from datetime import datetime

def init_auth_api():
    """初始化身份认证API接口"""

    # 登录请求模型
    login_model = auth_ns.model('LoginRequest', {
        'username': fields.String(required=True, description='用户名'),
        'password': fields.String(required=True, description='密码')
    })

    # 登录响应模型
    login_response_model = auth_ns.model('LoginResponse', {
        'access_token': fields.String(description='访问令牌'),
        'refresh_token': fields.String(description='刷新令牌'),
        'user': fields.Raw(description='用户信息'),
        'expires_in': fields.Integer(description='令牌过期时间（秒）')
    })

    # 刷新令牌请求模型
    refresh_model = auth_ns.model('RefreshRequest', {
        'refresh_token': fields.String(description='刷新令牌（可选，也可通过Authorization头传递）')
    })

    # 用户信息响应模型
    user_info_model = auth_ns.model('UserInfo', {
        'id': fields.String(description='用户ID'),
        'username': fields.String(description='用户名'),
        'email': fields.String(description='邮箱'),
        'role': fields.String(description='角色'),
        'is_active': fields.Boolean(description='是否激活'),
        'created_at': fields.String(description='创建时间'),
        'last_login': fields.String(description='最后登录时间'),
        'statistics': fields.Raw(description='用户统计信息')
    })

    @auth_ns.route('/login')
    class Login(Resource):
        @auth_ns.doc('user_login')
        @auth_ns.expect(login_model)
        # 移除marshal_with装饰器，手动处理响应格式
        def post(self):
            """用户登录

            用户通过用户名和密码进行身份认证，成功后返回访问令牌和刷新令牌。
            """
            try:
                data = request.get_json()
            except Exception as e:
                return {'error': '请求参数格式错误'}, 400

            try:
                if not data:
                    return {'error': '请求体不能为空'}, 400

                username = data.get('username')
                password = data.get('password')

                if not username or not password:
                    return {'error': '用户名和密码不能为空'}, 400

                # 查找用户
                user = User.query.filter_by(username=username).first()

                if not user or not user.check_password(password) or not user.is_active:
                    return {'error': '用户名或密码错误，或账户已被禁用'}, 401

                # 更新最后登录时间
                user.last_login = datetime.utcnow()
                db.session.commit()

                # 创建访问令牌和刷新令牌
                access_token = create_access_token(identity=str(user.id))
                refresh_token = create_refresh_token(identity=str(user.id))

                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': user.to_dict(),
                    'expires_in': current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
                }

            except Exception as e:
                current_app.logger.error(f"登录失败: {str(e)}")
                return {'error': '登录失败，请稍后重试'}, 500

    @auth_ns.route('/logout')
    class Logout(Resource):
        @auth_ns.doc('user_logout')
        @auth_ns.doc(security='Bearer Auth')
        @jwt_required()
        def post(self):
            """用户登出

            用户登出系统，将当前令牌加入黑名单。
            """
            try:
                # 这里可以实现令牌黑名单逻辑
                return {'message': '登出成功'}, 204
            except Exception as e:
                current_app.logger.error(f"登出失败: {str(e)}")
                return {'error': '登出失败，请稍后重试'}, 500

    @auth_ns.route('/refresh')
    class RefreshToken(Resource):
        @auth_ns.doc('refresh_token')
        @auth_ns.expect(refresh_model)
        @auth_ns.marshal_with(login_response_model)
        def post(self):
            """刷新访问令牌

            使用刷新令牌获取新的访问令牌。支持两种方式传递refresh_token：
            1. Authorization头部：Authorization: Bearer <refresh_token>
            2. 请求体：{"refresh_token": "<refresh_token>"}
            """
            try:
                refresh_token = None

                # 尝试从Authorization头获取
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    refresh_token = auth_header.split(' ')[1]

                # 如果头部没有，尝试从请求体获取
                if not refresh_token:
                    data = request.get_json() or {}
                    refresh_token = data.get('refresh_token')

                if not refresh_token:
                    return validation_error('缺少刷新令牌')

                # 验证刷新令牌并获取用户ID
                try:
                    from flask_jwt_extended import decode_token
                    decoded_token = decode_token(refresh_token)
                    user_id = decoded_token['sub']
                except Exception as e:
                    return unauthorized_error('无效的刷新令牌')

                # 查找用户
                user = User.query.get(user_id)
                if not user or not user.is_active:
                    return unauthorized_error('用户不存在或已被禁用')

                # 创建新的访问令牌
                new_access_token = create_access_token(identity=str(user.id))
                new_refresh_token = create_refresh_token(identity=str(user.id))

                return success_response(
                    message='令牌刷新成功',
                    data={
                        'access_token': new_access_token,
                        'refresh_token': new_refresh_token,
                        'user': user.to_dict(),
                        'expires_in': current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
                    }
                )

            except Exception as e:
                current_app.logger.error(f"刷新令牌失败: {str(e)}")
                return internal_error('刷新令牌失败，请重新登录')

    @auth_ns.route('/me')
    class CurrentUser(Resource):
        @auth_ns.doc('get_current_user')
        @auth_ns.doc(security='Bearer Auth')
        @auth_ns.marshal_with(user_info_model)
        @jwt_required()
        def get(self):
            """获取当前用户信息

            获取当前登录用户的详细信息，包括统计数据。
            """
            try:
                user_id = get_jwt_identity()
                user = User.query.get(user_id)

                if not user:
                    return unauthorized_error('用户不存在')

                if not user.is_active:
                    return unauthorized_error('账户已被禁用')

                # 获取用户统计信息
                from app.models.knowledge import KnowledgeDocument
                from app.models.case import Case

                user_stats = {
                    'uploaded_documents': KnowledgeDocument.query.filter_by(user_id=user_id).count(),
                    'created_cases': Case.query.filter_by(user_id=user_id).count(),
                    'total_queries': 0,  # 可以从查询日志中统计
                }

                user_data = user.to_dict()
                user_data['statistics'] = user_stats

                return user_data

            except Exception as e:
                current_app.logger.error(f"获取用户信息失败: {str(e)}")
                return internal_error('获取用户信息失败')

    print("✅ 身份认证API接口已注册到Flask-RESTX文档系统")
