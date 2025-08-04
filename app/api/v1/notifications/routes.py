"""
通知接口路由

提供系统通知管理功能。
"""

from datetime import datetime
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1.notifications import notifications_bp as bp
from app.models.notification import Notification
from app import db


@bp.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    获取通知列表

    查询参数:
    - page: 页码 (可选，默认1)
    - pageSize: 每页数量 (可选，默认20)
    - type: 通知类型过滤 (可选)
    - read: 已读状态过滤 (可选)
    """
    try:
        user_id = get_jwt_identity()

        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 20, type=int)
        notification_type = request.args.get('type')
        read_status = request.args.get('read')

        # 验证分页参数
        if page < 1 or page_size < 1:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '分页参数必须为正整数'
                }
            }), 400

        if page_size > 100:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '每页数量不能超过100'
                }
            }), 400

        # 构建查询
        query = Notification.query.filter_by(user_id=user_id)

        # 应用过滤器
        if notification_type:
            if notification_type not in ['solution', 'mention', 'system']:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '无效的通知类型，支持: solution, mention, system'
                    }
                }), 400
            query = query.filter_by(type=notification_type)

        if read_status is not None:
            if read_status.lower() == 'true':
                query = query.filter_by(read=True)
            elif read_status.lower() == 'false':
                query = query.filter_by(read=False)

        # 执行分页查询
        pagination = query.order_by(Notification.created_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )

        notifications = pagination.items

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'page': page,
                'pageSize': page_size,
                'total': pagination.total,
                'pages': pagination.pages,
                'items': [notification.to_dict() for notification in notifications]
            }
        })

    except ValueError:
        return jsonify({
            'code': 400,
            'status': 'error',
            'error': {
                'type': 'INVALID_REQUEST',
                'message': '分页参数必须为正整数'
            }
        }), 400
    except Exception as e:
        current_app.logger.error(f"Get notifications error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取通知列表时发生错误'
            }
        }), 500


@bp.route('/<notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    """标记通知已读"""
    try:
        user_id = get_jwt_identity()

        # 查找通知
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()

        if not notification:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '通知不存在'
                }
            }), 404

        # 标记为已读
        notification.mark_as_read()
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Mark notification read error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '标记通知已读时发生错误'
            }
        }), 500


@bp.route('/batch/read', methods=['POST'])
@jwt_required()
def mark_notifications_read_batch():
    """
    批量标记通知已读

    请求体:
    - notificationIds: 通知ID列表 (可选，如果为空则标记所有未读通知)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        notification_ids = data.get('notificationIds', [])

        # 构建查询
        query = Notification.query.filter_by(user_id=user_id, read=False)

        if notification_ids:
            # 标记指定的通知
            query = query.filter(Notification.id.in_(notification_ids))

        # 批量更新
        count = query.update({
            'read': True,
            'read_at': datetime.utcnow()
        }, synchronize_session=False)

        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'markedCount': count,
                'message': f'已标记 {count} 条通知为已读'
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Batch mark notifications read error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '批量标记通知已读时发生错误'
            }
        }), 500


@bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """获取未读通知数量"""
    try:
        user_id = get_jwt_identity()

        # 统计未读通知数量
        total_unread = Notification.query.filter_by(
            user_id=user_id,
            read=False
        ).count()

        # 按类型统计
        solution_count = Notification.query.filter_by(
            user_id=user_id,
            read=False,
            type='solution'
        ).count()

        mention_count = Notification.query.filter_by(
            user_id=user_id,
            read=False,
            type='mention'
        ).count()

        system_count = Notification.query.filter_by(
            user_id=user_id,
            read=False,
            type='system'
        ).count()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'total': total_unread,
                'byType': {
                    'solution': solution_count,
                    'mention': mention_count,
                    'system': system_count
                }
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get unread count error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取未读通知数量时发生错误'
            }
        }), 500
