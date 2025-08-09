"""
用户管理 API 接口 (Flask-RESTX)

将原有的用户管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.models.user_settings import UserSettings
from app.utils.response_helper import validation_error

def init_user_api():
    """初始化用户管理API接口"""
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    user_ns = get_namespace('user')

    # 用户设置模型
    user_settings_model = user_ns.model('UserSettings', {
        'theme': fields.String(description='主题设置', enum=['light', 'dark', 'auto']),
        'language': fields.String(description='语言设置', enum=['zh-CN', 'en-US']),
        'notifications': fields.Raw(description='通知设置'),
        'preferences': fields.Raw(description='用户偏好设置'),
        'display_settings': fields.Raw(description='显示设置')
    })

    # 更新用户设置请求模型
    update_settings_model = user_ns.model('UpdateUserSettingsRequest', {
        'theme': fields.String(description='主题设置', enum=['light', 'dark', 'auto']),
        'language': fields.String(description='语言设置', enum=['zh-CN', 'en-US']),
        'notifications': fields.Raw(description='通知设置'),
        'preferences': fields.Raw(description='用户偏好设置'),
        'display_settings': fields.Raw(description='显示设置')
    })

    @user_ns.route('/settings')
    class UserSettingsResource(Resource):
        @user_ns.doc('get_user_settings')
        @user_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取用户设置

            获取当前登录用户的个性化设置信息。
            """
            try:
                user_id_raw = get_jwt_identity()
                try:
                    user_id = int(user_id_raw)
                except Exception:
                    return {
                        'code': 401,
                        'status': 'error',
                        'error': {'type': 'UNAUTHORIZED', 'message': '无效的用户身份'}
                    }, 401

                # 获取或创建用户设置（使用 db.session.get 以避免 query 属性问题）
                settings = db.session.get(UserSettings, user_id)
                if not settings:
                    settings = UserSettings(user_id=user_id)
                    db.session.add(settings)
                    db.session.commit()

                data = settings.to_dict()
                return {
                    'code': 200,
                    'status': 'success',
                    'data': data
                }, 200

            except Exception as e:
                current_app.logger.exception(f"获取用户设置失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {'type': 'INTERNAL_ERROR', 'message': '获取用户设置失败'}
                }, 500

        @user_ns.doc('update_user_settings')
        @user_ns.doc(security='Bearer Auth')
        @user_ns.expect(update_settings_model)
        @jwt_required()
        def put(self):
            """更新用户设置

            更新当前登录用户的个性化设置。
            """
            try:
                user_id_raw = get_jwt_identity()
                try:
                    user_id = int(user_id_raw)
                except Exception:
                    return {
                        'code': 401,
                        'status': 'error',
                        'error': {'type': 'UNAUTHORIZED', 'message': '无效的用户身份'}
                    }, 401
                data = request.get_json()

                if not data:
                    return {
                        'code': 400,
                        'status': 'error',
                        'error': {'type': 'INVALID_REQUEST', 'message': '请求体不能为空'}
                    }, 400

                # 获取或创建用户设置（使用 db.session.get 以避免 query 属性问题）
                settings = db.session.get(UserSettings, user_id)
                if not settings:
                    settings = UserSettings(user_id=user_id)
                    db.session.add(settings)
                    db.session.flush()

                # 更新设置
                if 'theme' in data:
                    settings.theme = data['theme']
                if 'language' in data:
                    settings.language = data['language']
                if 'notifications' in data:
                    settings.notifications = data['notifications']
                if 'preferences' in data:
                    settings.preferences = data['preferences']
                if 'display_settings' in data:
                    settings.display_settings = data['display_settings']

                db.session.commit()

                return {
                    'code': 200,
                    'status': 'success',
                    'data': settings.to_dict()
                }, 200

            except Exception as e:
                current_app.logger.exception(f"更新用户设置失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {'type': 'INTERNAL_ERROR', 'message': '更新用户设置失败'}
                }, 500

    print("✅ 用户管理API接口已注册到Flask-RESTX文档系统")
