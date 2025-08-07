"""
用户管理 API 接口 (Flask-RESTX)

将原有的用户管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import user_ns
from app.models.user_settings import UserSettings
from app.utils.response_helper import success_response, validation_error, internal_error

def init_user_api():
    """初始化用户管理API接口"""
    
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
    class UserSettings(Resource):
        @user_ns.doc('get_user_settings')
        @user_ns.doc(security='Bearer Auth')
        @user_ns.marshal_with(user_settings_model)
        @jwt_required()
        def get(self):
            """获取用户设置
            
            获取当前登录用户的个性化设置信息。
            """
            try:
                user_id = get_jwt_identity()
                
                # 获取或创建用户设置
                settings = UserSettings.get_or_create_for_user(user_id)
                
                return success_response(
                    message='获取用户设置成功',
                    data=settings.to_dict()
                )
                
            except Exception as e:
                current_app.logger.error(f"获取用户设置失败: {str(e)}")
                return internal_error('获取用户设置失败')

        @user_ns.doc('update_user_settings')
        @user_ns.doc(security='Bearer Auth')
        @user_ns.expect(update_settings_model)
        @user_ns.marshal_with(user_settings_model)
        @jwt_required()
        def put(self):
            """更新用户设置
            
            更新当前登录用户的个性化设置。
            """
            try:
                user_id = get_jwt_identity()
                data = request.get_json()
                
                if not data:
                    return validation_error('请求体不能为空')
                
                # 获取或创建用户设置
                settings = UserSettings.get_or_create_for_user(user_id)
                
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
                
                return success_response(
                    message='用户设置更新成功',
                    data=settings.to_dict()
                )
                
            except Exception as e:
                current_app.logger.error(f"更新用户设置失败: {str(e)}")
                return internal_error('更新用户设置失败')

    print("✅ 用户管理API接口已注册到Flask-RESTX文档系统")
