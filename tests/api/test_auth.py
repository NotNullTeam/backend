"""
IP智慧解答专家系统 - 认证API测试

本模块测试认证相关的API接口。
"""

import pytest
from app.models.user import User
from app import db


class TestAuthAPI:
    """认证API测试类"""

    def test_login_success(self, client):
        """测试登录成功"""
        # 创建测试用户
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        # 执行登录
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })

        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert data['data']['user_info']['username'] == 'testuser'

    def test_login_invalid_username(self, client):
        """测试用户名不存在"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'nonexistent',
            'password': 'testpass'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_login_invalid_password(self, client):
        """测试密码错误"""
        # 创建测试用户
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpass'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'

    def test_login_inactive_user(self, client):
        """测试非活跃用户登录"""
        # 创建非活跃用户
        user = User(
            username='inactive',
            email='inactive@example.com',
            is_active=False
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        response = client.post('/api/v1/auth/login', json={
            'username': 'inactive',
            'password': 'testpass'
        })

        assert response.status_code == 401

    def test_login_missing_data(self, client):
        """测试缺少登录数据"""
        response = client.post('/api/v1/auth/login', json={})
        assert response.status_code == 400

        response = client.post('/api/v1/auth/login', json={
            'username': 'test'
        })
        assert response.status_code == 400

    def test_get_current_user(self, client, auth_headers):
        """测试获取当前用户信息"""
        response = client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['username'] == 'testuser'

    def test_get_current_user_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get('/api/v1/auth/me')
        assert response.status_code == 401  # JWT missing

    def test_refresh_token(self, client, auth_headers):
        """测试刷新令牌"""
        # 先登录获取refresh token
        user = User(
            username='refreshuser',
            email='refresh@example.com'
        )
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        login_response = client.post('/api/v1/auth/login', json={
            'username': 'refreshuser',
            'password': 'testpass'
        })

        login_data = login_response.get_json()
        refresh_token = login_data['data']['refresh_token']

        # 使用refresh token获取新的access token
        response = client.post('/api/v1/auth/refresh',
                             headers={'Authorization': f'Bearer {refresh_token}'})

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data['data']
