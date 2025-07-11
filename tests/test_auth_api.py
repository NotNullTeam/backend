"""
IP智慧解答专家系统 - 认证API测试

本模块测试所有认证相关的API接口。
"""

import pytest
import json
from flask import url_for
from app.models.user import User


@pytest.mark.api
@pytest.mark.auth
class TestAuthLogin:
    """测试用户登录API"""

    def test_login_success(self, client, sample_user):
        """测试成功登录"""
        response = client.post('/api/v1/auth/login', json={
            'username': sample_user.username,
            'password': 'testpass123'
        })

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert data['data']['token_type'] == 'Bearer'
        assert 'user_info' in data['data']
        assert data['data']['user_info']['username'] == sample_user.username

    def test_login_invalid_username(self, client):
        """测试无效用户名登录"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'nonexistent',
            'password': 'password123'
        })

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'
        assert '用户名或密码错误' in data['error']['message']

    def test_login_invalid_password(self, client, sample_user):
        """测试无效密码登录"""
        response = client.post('/api/v1/auth/login', json={
            'username': sample_user.username,
            'password': 'wrongpassword'
        })

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_login_inactive_user(self, client, inactive_user):
        """测试非活跃用户登录"""
        response = client.post('/api/v1/auth/login', json={
            'username': inactive_user.username,
            'password': 'inactive123'
        })

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_login_missing_username(self, client):
        """测试缺少用户名"""
        response = client.post('/api/v1/auth/login', json={
            'password': 'password123'
        })

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'
        assert '用户名和密码不能为空' in data['error']['message']

    def test_login_missing_password(self, client):
        """测试缺少密码"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser'
        })

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'

    def test_login_empty_request_body(self, client):
        """测试空请求体"""
        response = client.post('/api/v1/auth/login',
                             data='',
                             content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'
        assert '请求参数格式错误' in data['error']['message']

    def test_login_invalid_json(self, client):
        """测试无效JSON格式"""
        response = client.post('/api/v1/auth/login',
                             data='invalid json',
                             content_type='application/json')

        assert response.status_code == 400


@pytest.mark.api
@pytest.mark.auth
class TestAuthLogout:
    """测试用户登出API"""

    def test_logout_success(self, client, auth_headers):
        """测试成功登出"""
        response = client.post('/api/v1/auth/logout', headers=auth_headers)

        assert response.status_code == 204
        assert response.data == b''

    def test_logout_without_token(self, client):
        """测试未提供令牌的登出"""
        response = client.post('/api/v1/auth/logout')

        assert response.status_code == 401

    def test_logout_invalid_token(self, client):
        """测试无效令牌的登出"""
        headers = {'Authorization': 'Bearer invalid_token'}
        response = client.post('/api/v1/auth/logout', headers=headers)

        assert response.status_code == 422


@pytest.mark.api
@pytest.mark.auth
class TestAuthRefresh:
    """测试令牌刷新API"""

    def test_refresh_success(self, client, sample_user):
        """测试成功刷新令牌"""
        # 先登录获取刷新令牌
        login_response = client.post('/api/v1/auth/login', json={
            'username': sample_user.username,
            'password': 'testpass123'
        })

        login_data = login_response.get_json()
        refresh_token = login_data['data']['refresh_token']

        # 使用刷新令牌获取新的访问令牌
        headers = {'Authorization': f'Bearer {refresh_token}'}
        response = client.post('/api/v1/auth/refresh', headers=headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert data['data']['token_type'] == 'Bearer'

    def test_refresh_without_token(self, client):
        """测试未提供刷新令牌"""
        response = client.post('/api/v1/auth/refresh')

        assert response.status_code == 401

    def test_refresh_with_access_token(self, client, auth_headers):
        """测试使用访问令牌而非刷新令牌"""
        response = client.post('/api/v1/auth/refresh', headers=auth_headers)

        assert response.status_code == 422

    def test_refresh_inactive_user(self, client, inactive_user, database):
        """测试非活跃用户的令牌刷新"""
        # 先激活用户并登录
        inactive_user.is_active = True
        database.session.commit()

        login_response = client.post('/api/v1/auth/login', json={
            'username': inactive_user.username,
            'password': 'inactive123'
        })

        login_data = login_response.get_json()
        refresh_token = login_data['data']['refresh_token']

        # 然后禁用用户
        inactive_user.is_active = False
        database.session.commit()

        # 尝试刷新令牌
        headers = {'Authorization': f'Bearer {refresh_token}'}
        response = client.post('/api/v1/auth/refresh', headers=headers)

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'


@pytest.mark.api
@pytest.mark.auth
class TestAuthMe:
    """测试获取当前用户信息API"""

    def test_get_current_user_success(self, client, auth_headers, sample_user):
        """测试成功获取当前用户信息"""
        response = client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['id'] == sample_user.id
        assert data['data']['username'] == sample_user.username
        assert data['data']['email'] == sample_user.email
        assert data['data']['roles'] == ['user']
        assert data['data']['is_active'] is True
        assert 'created_at' in data['data']
        assert 'updated_at' in data['data']

    def test_get_current_user_without_token(self, client):
        """测试未提供令牌获取用户信息"""
        response = client.get('/api/v1/auth/me')

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """测试无效令牌获取用户信息"""
        headers = {'Authorization': 'Bearer invalid_token'}
        response = client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code == 422

    def test_get_current_user_deleted_user(self, client, sample_user, database):
        """测试已删除用户的令牌"""
        # 先获取有效令牌
        login_response = client.post('/api/v1/auth/login', json={
            'username': sample_user.username,
            'password': 'testpass123'
        })

        login_data = login_response.get_json()
        token = login_data['data']['access_token']

        # 删除用户
        database.session.delete(sample_user)
        database.session.commit()

        # 尝试获取用户信息
        headers = {'Authorization': f'Bearer {token}'}
        response = client.get('/api/v1/auth/me', headers=headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert data['error']['type'] == 'NOT_FOUND'


@pytest.mark.integration
@pytest.mark.auth
class TestAuthIntegration:
    """测试认证流程的集成测试"""

    def test_complete_auth_flow(self, client, sample_user):
        """测试完整的认证流程"""
        # 1. 登录
        login_response = client.post('/api/v1/auth/login', json={
            'username': sample_user.username,
            'password': 'testpass123'
        })

        assert login_response.status_code == 200
        login_data = login_response.get_json()
        access_token = login_data['data']['access_token']
        refresh_token = login_data['data']['refresh_token']

        # 2. 使用访问令牌获取用户信息
        auth_headers = {'Authorization': f'Bearer {access_token}'}
        me_response = client.get('/api/v1/auth/me', headers=auth_headers)

        assert me_response.status_code == 200
        me_data = me_response.get_json()
        assert me_data['data']['username'] == sample_user.username

        # 3. 刷新令牌
        refresh_headers = {'Authorization': f'Bearer {refresh_token}'}
        refresh_response = client.post('/api/v1/auth/refresh', headers=refresh_headers)

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.get_json()
        new_access_token = refresh_data['data']['access_token']

        # 4. 使用新令牌获取用户信息
        new_auth_headers = {'Authorization': f'Bearer {new_access_token}'}
        me_response2 = client.get('/api/v1/auth/me', headers=new_auth_headers)

        assert me_response2.status_code == 200

        # 5. 登出
        logout_response = client.post('/api/v1/auth/logout', headers=new_auth_headers)

        assert logout_response.status_code == 204
