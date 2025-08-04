"""
通知接口响应测试

测试通知相关API的响应格式和状态码。
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from app import db
from app.models.notification import Notification
from app.models.user import User


class TestNotificationsAPIResponses:
    """通知API响应测试类"""

    def test_get_notifications_success_response(self, client, auth_headers, test_user):
        """测试获取通知列表成功响应格式"""
        # 创建测试通知
        notification1 = Notification(
            type='solution',
            title='诊断案例已生成解决方案',
            content='您的诊断案例《网络连接问题》已生成解决方案，请查看。',
            user_id=test_user.id,
            related_case_id='test-case-id',
            related_node_id='test-node-id'
        )
        notification2 = Notification(
            type='system',
            title='系统维护通知',
            content='系统将于今晚进行维护升级。',
            user_id=test_user.id,
            read=True,
            read_at=datetime.utcnow()
        )
        db.session.add_all([notification1, notification2])
        db.session.commit()

        response = client.get('/api/v1/notifications/', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        
        response_data = data['data']
        assert 'page' in response_data
        assert 'pageSize' in response_data
        assert 'total' in response_data
        assert 'pages' in response_data
        assert 'items' in response_data
        assert isinstance(response_data['items'], list)
        assert len(response_data['items']) >= 2
        
        # 检查通知数据结构
        notification = response_data['items'][0]
        assert 'id' in notification
        assert 'type' in notification
        assert 'title' in notification
        assert 'content' in notification
        assert 'read' in notification
        assert 'createdAt' in notification

    def test_get_notifications_with_pagination(self, client, auth_headers, test_user):
        """测试分页参数的通知列表响应"""
        # 创建多个测试通知
        notifications = []
        for i in range(5):
            notification = Notification(
                type='system',
                title=f'测试通知 {i+1}',
                content=f'这是第 {i+1} 个测试通知',
                user_id=test_user.id
            )
            notifications.append(notification)
        db.session.add_all(notifications)
        db.session.commit()

        response = client.get('/api/v1/notifications/?page=1&pageSize=3', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        response_data = data['data']
        assert response_data['page'] == 1
        assert response_data['pageSize'] == 3
        assert len(response_data['items']) <= 3

    def test_get_notifications_with_type_filter(self, client, auth_headers, test_user):
        """测试按类型过滤的通知列表响应"""
        # 创建不同类型的通知
        solution_notification = Notification(
            type='solution',
            title='解决方案通知',
            content='解决方案已生成',
            user_id=test_user.id
        )
        system_notification = Notification(
            type='system',
            title='系统通知',
            content='系统更新',
            user_id=test_user.id
        )
        db.session.add_all([solution_notification, system_notification])
        db.session.commit()

        response = client.get('/api/v1/notifications/?type=solution', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        response_data = data['data']
        
        # 验证所有返回的通知都是 solution 类型
        for notification in response_data['items']:
            assert notification['type'] == 'solution'

    def test_get_notifications_with_read_filter(self, client, auth_headers, test_user):
        """测试按已读状态过滤的通知列表响应"""
        # 创建已读和未读通知
        unread_notification = Notification(
            type='system',
            title='未读通知',
            content='这是未读通知',
            user_id=test_user.id,
            read=False
        )
        read_notification = Notification(
            type='system',
            title='已读通知',
            content='这是已读通知',
            user_id=test_user.id,
            read=True,
            read_at=datetime.utcnow()
        )
        db.session.add_all([unread_notification, read_notification])
        db.session.commit()

        response = client.get('/api/v1/notifications/?read=false', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        response_data = data['data']
        
        # 验证所有返回的通知都是未读的
        for notification in response_data['items']:
            assert notification['read'] is False

    def test_get_notifications_invalid_pagination(self, client, auth_headers):
        """测试无效分页参数的响应"""
        response = client.get('/api/v1/notifications/?page=0&pageSize=-1', headers=auth_headers)
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['code'] == 400
        assert data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'INVALID_REQUEST'

    def test_get_notifications_invalid_type_filter(self, client, auth_headers):
        """测试无效类型过滤参数的响应"""
        response = client.get('/api/v1/notifications/?type=invalid_type', headers=auth_headers)
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['code'] == 400
        assert data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'INVALID_REQUEST'

    def test_mark_notification_read_success(self, client, auth_headers, test_user):
        """测试标记通知已读成功响应"""
        # 创建未读通知
        notification = Notification(
            type='system',
            title='测试通知',
            content='这是测试通知',
            user_id=test_user.id,
            read=False
        )
        db.session.add(notification)
        db.session.commit()

        response = client.post(f'/api/v1/notifications/{notification.id}/read', headers=auth_headers)
        assert response.status_code == 204
        assert response.data == b''

        # 验证通知已被标记为已读
        db.session.refresh(notification)
        assert notification.read is True
        assert notification.read_at is not None

    def test_mark_notification_read_not_found(self, client, auth_headers):
        """测试标记不存在的通知已读的响应"""
        response = client.post('/api/v1/notifications/non-existent-id/read', headers=auth_headers)
        assert response.status_code == 404
        
        data = response.get_json()
        assert data['code'] == 404
        assert data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'NOT_FOUND'

    def test_batch_mark_notifications_read_success(self, client, auth_headers, test_user):
        """测试批量标记通知已读成功响应"""
        # 创建多个未读通知
        notifications = []
        for i in range(3):
            notification = Notification(
                type='system',
                title=f'测试通知 {i+1}',
                content=f'这是第 {i+1} 个测试通知',
                user_id=test_user.id,
                read=False
            )
            notifications.append(notification)
        db.session.add_all(notifications)
        db.session.commit()

        notification_ids = [n.id for n in notifications]
        response = client.post('/api/v1/notifications/batch/read', 
                             json={'notificationIds': notification_ids},
                             headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert data['data']['markedCount'] == 3
        assert 'message' in data['data']

        # 验证通知已被标记为已读
        for notification in notifications:
            db.session.refresh(notification)
            assert notification.read is True

    def test_batch_mark_all_notifications_read(self, client, auth_headers, test_user):
        """测试批量标记所有通知已读的响应"""
        # 创建多个未读通知
        notifications = []
        for i in range(3):
            notification = Notification(
                type='system',
                title=f'测试通知 {i+1}',
                content=f'这是第 {i+1} 个测试通知',
                user_id=test_user.id,
                read=False
            )
            notifications.append(notification)
        db.session.add_all(notifications)
        db.session.commit()

        # 不传递 notificationIds，应该标记所有未读通知
        response = client.post('/api/v1/notifications/batch/read', 
                             json={},
                             headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['markedCount'] == 3

    def test_get_unread_count_success(self, client, auth_headers, test_user):
        """测试获取未读通知数量成功响应"""
        # 创建不同类型的未读通知
        solution_notification = Notification(
            type='solution',
            title='解决方案通知',
            content='解决方案已生成',
            user_id=test_user.id,
            read=False
        )
        mention_notification = Notification(
            type='mention',
            title='提及通知',
            content='有人提及了您',
            user_id=test_user.id,
            read=False
        )
        system_notification = Notification(
            type='system',
            title='系统通知',
            content='系统更新',
            user_id=test_user.id,
            read=False
        )
        read_notification = Notification(
            type='system',
            title='已读通知',
            content='这是已读通知',
            user_id=test_user.id,
            read=True,
            read_at=datetime.utcnow()
        )
        db.session.add_all([solution_notification, mention_notification, system_notification, read_notification])
        db.session.commit()

        response = client.get('/api/v1/notifications/unread-count', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        
        response_data = data['data']
        assert 'total' in response_data
        assert 'byType' in response_data
        assert response_data['total'] == 3
        
        by_type = response_data['byType']
        assert 'solution' in by_type
        assert 'mention' in by_type
        assert 'system' in by_type
        assert by_type['solution'] == 1
        assert by_type['mention'] == 1
        assert by_type['system'] == 1

    def test_unauthorized_access_response(self, client):
        """测试未授权访问的响应"""
        response = client.get('/api/v1/notifications/')
        assert response.status_code == 401

    def test_notifications_isolation_between_users(self, client, test_user):
        """测试用户间通知隔离的响应"""
        # 创建另一个用户
        other_user = User(
            username='other_user',
            email='other@example.com',
            password_hash='hashed_password'
        )
        db.session.add(other_user)
        db.session.commit()

        # 为两个用户分别创建通知
        user1_notification = Notification(
            type='system',
            title='用户1的通知',
            content='这是用户1的通知',
            user_id=test_user.id
        )
        user2_notification = Notification(
            type='system',
            title='用户2的通知',
            content='这是用户2的通知',
            user_id=other_user.id
        )
        db.session.add_all([user1_notification, user2_notification])
        db.session.commit()

        # 用户1登录并获取通知
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(test_user.id))
        headers = {'Authorization': f'Bearer {access_token}'}

        response = client.get('/api/v1/notifications/', headers=headers)
        assert response.status_code == 200
        
        data = response.get_json()
        response_data = data['data']
        
        # 验证用户1只能看到自己的通知
        assert response_data['total'] == 1
        assert response_data['items'][0]['title'] == '用户1的通知'

    def test_response_time_reasonable(self, client, auth_headers, test_user):
        """测试响应时间合理性"""
        # 创建大量通知
        notifications = []
        for i in range(50):
            notification = Notification(
                type='system',
                title=f'测试通知 {i+1}',
                content=f'这是第 {i+1} 个测试通知',
                user_id=test_user.id
            )
            notifications.append(notification)
        db.session.add_all(notifications)
        db.session.commit()

        import time
        start_time = time.time()
        response = client.get('/api/v1/notifications/', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        # 响应时间应该在合理范围内（小于2秒）
        assert (end_time - start_time) < 2.0

    def test_notification_content_encoding(self, client, auth_headers, test_user):
        """测试通知内容编码正确性"""
        # 创建包含中文和特殊字符的通知
        notification = Notification(
            type='system',
            title='测试中文标题 & 特殊字符 <script>',
            content='这是包含中文内容的通知 & 特殊字符 <script>alert("test")</script>',
            user_id=test_user.id
        )
        db.session.add(notification)
        db.session.commit()

        response = client.get('/api/v1/notifications/', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        notification_data = data['data']['items'][0]
        
        # 验证中文和特殊字符正确编码
        assert '测试中文标题' in notification_data['title']
        assert '这是包含中文内容的通知' in notification_data['content']
        assert '&' in notification_data['title']
        assert '<script>' in notification_data['content']

    def test_notification_timestamps_format(self, client, auth_headers, test_user):
        """测试通知时间戳格式正确性"""
        notification = Notification(
            type='system',
            title='时间戳测试',
            content='测试时间戳格式',
            user_id=test_user.id,
            read=True,
            read_at=datetime.utcnow()
        )
        db.session.add(notification)
        db.session.commit()

        response = client.get('/api/v1/notifications/', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        notification_data = data['data']['items'][0]
        
        # 验证时间戳格式（ISO 8601 格式）
        assert 'createdAt' in notification_data
        assert notification_data['createdAt'].endswith('Z')
        assert 'readAt' in notification_data
        assert notification_data['readAt'].endswith('Z')
        
        # 验证时间戳可以被解析
        created_at = datetime.fromisoformat(notification_data['createdAt'].replace('Z', '+00:00'))
        read_at = datetime.fromisoformat(notification_data['readAt'].replace('Z', '+00:00'))
        assert isinstance(created_at, datetime)
        assert isinstance(read_at, datetime)
