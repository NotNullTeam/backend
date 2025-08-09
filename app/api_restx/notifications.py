"""
通知管理 API 接口 (Flask-RESTX)

将原有的通知管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from datetime import datetime
from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.models.notification import Notification
from app.utils.response_helper import success_response, validation_error, not_found_error, internal_error, paginated_response

def init_notifications_api():
    """初始化通知管理API接口"""
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    notifications_ns = get_namespace('notifications')

    # 通知信息模型
    notification_model = notifications_ns.model('Notification', {
        'id': fields.String(description='通知ID'),
        'title': fields.String(description='通知标题'),
        'content': fields.String(description='通知内容'),
        'type': fields.String(description='通知类型'),
        'read': fields.Boolean(description='是否已读'),
        'created_at': fields.String(description='创建时间'),
        'read_at': fields.String(description='阅读时间'),
        'metadata': fields.Raw(description='通知元数据')
    })

    # 通知列表响应模型
    notifications_list_model = notifications_ns.model('NotificationsList', {
        'notifications': fields.List(fields.Nested(notification_model), description='通知列表'),
        'total': fields.Integer(description='总数量'),
        'page': fields.Integer(description='当前页码'),
        'per_page': fields.Integer(description='每页数量'),
        'unread_count': fields.Integer(description='未读数量')
    })

    # 批量标记已读请求模型
    batch_read_model = notifications_ns.model('BatchReadRequest', {
        'notificationIds': fields.List(fields.String, description='通知ID列表（可选，如果为空则标记所有未读通知）')
    })

    # 未读数量响应模型
    unread_count_model = notifications_ns.model('UnreadCount', {
        'unread_count': fields.Integer(description='未读通知数量'),
        'total_count': fields.Integer(description='总通知数量')
    })

    # 仅保留基础路径'/'，避免重复路由定义
    @notifications_ns.route('/')
    class NotificationsList(Resource):
        @notifications_ns.doc('get_notifications')
        @notifications_ns.doc(security='Bearer Auth')
        @notifications_ns.param('page', '页码', type='integer', default=1)
        @notifications_ns.param('pageSize', '每页数量', type='integer', default=20)
        @notifications_ns.param('type', '通知类型过滤')
        @notifications_ns.param('read', '已读状态过滤', type='boolean')
        @jwt_required()
        def get(self):
            """获取通知列表

            支持分页查询和多种过滤条件。
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
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '分页参数必须为正整数'}}, 400

                if page_size > 100:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '每页数量不能超过100'}}, 400

                # 构建查询
                query = Notification.query.filter_by(user_id=user_id)

                if notification_type:
                    allowed_types = {'solution', 'mention', 'system'}
                    if notification_type not in allowed_types:
                        return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '无效的通知类型'}}, 400
                    query = query.filter_by(type=notification_type)

                if read_status is not None:
                    is_read = str(read_status).lower() == 'true'
                    query = query.filter_by(read=is_read)

                # 分页查询
                pagination = query.order_by(Notification.created_at.desc()).paginate(
                    page=page, per_page=page_size, error_out=False
                )

                # 获取未读数量
                unread_count = Notification.query.filter_by(
                    user_id=user_id, read=False
                ).count()

                items = [notification.to_dict() for notification in pagination.items]
                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'items': items,
                        'page': page,
                        'pageSize': page_size,
                        'total': pagination.total,
                        'pages': pagination.pages
                    }
                }, 200

            except Exception as e:
                current_app.logger.error(f"获取通知列表失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取通知列表失败'}}, 500

    @notifications_ns.route('/<string:notification_id>/read')
    class NotificationRead(Resource):
        @notifications_ns.doc('mark_notification_read')
        @notifications_ns.doc(security='Bearer Auth')
        @jwt_required()
        def post(self, notification_id):
            """标记通知已读

            将指定通知标记为已读状态（使用 POST）。
            """
            try:
                user_id = get_jwt_identity()
                notification = Notification.query.filter_by(
                    id=notification_id, user_id=user_id
                ).first()

                if not notification:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '通知不存在'}}, 404

                if not notification.read:
                    notification.read = True
                    notification.read_at = datetime.utcnow()
                    db.session.commit()

                return '', 204
            except Exception as e:
                current_app.logger.exception(f"标记通知已读失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '标记通知已读失败'}}, 500

    @notifications_ns.route('/batch/read')
    class BatchNotificationRead(Resource):
        @notifications_ns.doc('mark_notifications_read_batch')
        @notifications_ns.doc(security='Bearer Auth')
        @notifications_ns.expect(batch_read_model)
        @jwt_required()
        def post(self):
            """批量标记通知已读（使用 POST）

            批量将通知标记为已读状态。如果不提供通知ID列表，则标记所有未读通知。
            """
            try:
                user_id = get_jwt_identity()
                data = request.get_json() or {}
                notification_ids = data.get('notificationIds', [])

                # 构建查询
                query = Notification.query.filter_by(user_id=user_id, read=False)

                if notification_ids:
                    query = query.filter(Notification.id.in_(notification_ids))

                # 批量更新
                updated_count = query.update({
                    Notification.read: True,
                    Notification.read_at: datetime.utcnow()
                }, synchronize_session=False)

                db.session.commit()

                return {
                    'code': 200,
                    'status': 'success',
                    'data': {'markedCount': updated_count, 'message': f'已标记 {updated_count} 条通知为已读'}
                }, 200
            except Exception as e:
                current_app.logger.exception(f"批量标记通知已读失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '批量标记通知已读失败'}}, 500

    @notifications_ns.route('/unread-count')
    class UnreadCount(Resource):
        @notifications_ns.doc('get_unread_count')
        @notifications_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取未读通知数量

            返回当前用户的未读通知数量统计。
            """
            try:
                user_id = get_jwt_identity()

                unread_count = Notification.query.filter_by(
                    user_id=user_id, read=False
                ).count()

                # 按类型统计
                solution_unread = Notification.query.filter_by(user_id=user_id, read=False, type='solution').count()
                mention_unread = Notification.query.filter_by(user_id=user_id, read=False, type='mention').count()
                system_unread = Notification.query.filter_by(user_id=user_id, read=False, type='system').count()

                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'total': unread_count,
                        'byType': {
                            'solution': solution_unread,
                            'mention': mention_unread,
                            'system': system_unread
                        }
                    }
                }

            except Exception as e:
                current_app.logger.error(f"获取未读通知数量失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取未读通知数量失败'}}, 500

    print("✅ 通知管理API接口已注册到Flask-RESTX文档系统")
