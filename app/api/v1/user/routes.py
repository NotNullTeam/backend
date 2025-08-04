"""
用户设置接口路由

提供用户个性化配置管理功能。
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1.user import user_bp as bp
from app.models.user_settings import UserSettings
from app import db


@bp.route('/settings', methods=['GET'])
@jwt_required()
def get_user_settings():
    """获取用户设置"""
    try:
        user_id = get_jwt_identity()

        # 获取或创建用户设置
        settings = UserSettings.get_or_create_for_user(user_id)

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': settings.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Get user settings error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取用户设置时发生错误'
            }
        }), 500


@bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_user_settings():
    """更新用户设置"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 获取或创建用户设置
        settings = UserSettings.get_or_create_for_user(user_id)

        # 更新主题设置
        if 'theme' in data:
            theme = data['theme']
            if theme not in ['light', 'dark', 'system']:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '无效的主题设置，支持: light, dark, system'
                    }
                }), 400
            settings.theme = theme

        # 更新通知偏好
        if 'notifications' in data:
            notifications = data['notifications']
            if not isinstance(notifications, dict):
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '通知设置必须是对象格式'
                    }
                }), 400

            # 验证通知设置字段
            valid_notification_keys = {'solution', 'mention', 'system'}
            for key in notifications:
                if key not in valid_notification_keys:
                    return jsonify({
                        'code': 400,
                        'status': 'error',
                        'error': {
                            'type': 'INVALID_REQUEST',
                            'message': f'无效的通知设置字段: {key}'
                        }
                    }), 400
                if not isinstance(notifications[key], bool):
                    return jsonify({
                        'code': 400,
                        'status': 'error',
                        'error': {
                            'type': 'INVALID_REQUEST',
                            'message': f'通知设置值必须是布尔类型: {key}'
                        }
                    }), 400

            # 合并通知设置
            current_notifications = settings.notifications or {
                'solution': True,
                'mention': False,
                'system': True
            }
            current_notifications.update(notifications)
            settings.notifications = current_notifications

        # 更新其他偏好设置
        if 'preferences' in data:
            preferences = data['preferences']
            if not isinstance(preferences, dict):
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '偏好设置必须是对象格式'
                    }
                }), 400

            # 合并偏好设置
            current_preferences = settings.preferences or {
                'language': 'zh-cn',
                'autoSave': True,
                'showHints': True
            }
            current_preferences.update(preferences)
            settings.preferences = current_preferences

        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'status': 'success',
                'message': '用户设置已更新',
                'settings': settings.to_dict()
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update user settings error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '更新用户设置时发生错误'
            }
        }), 500
