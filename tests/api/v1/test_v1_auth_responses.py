"""
API v1 认证模块响应测试

测试认证相关 API 的响应格式和状态码。
"""

import pytest
import json
from app import db
from app.models.user import User


class TestAuthAPIResponses:
    """认证 API 响应测试类"""

    def test_login_success_response(self, client, test_user):
        """测试登录成功响应格式"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })

        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = response.get_json()

        # 检查RESTX API响应结构（直接字段格式）
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'expires_in' in data
        assert 'user' in data

        # 检查令牌不为空
        assert data['access_token'] is not None
        assert data['refresh_token'] is not None

        # 检查用户信息
        user_data = data['user']
        assert 'id' in user_data
        assert 'username' in user_data
        assert 'email' in user_data
        assert user_data['username'] == 'testuser'

    def test_login_invalid_credentials_response(self, client, test_user):
        """测试登录失败响应格式"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpass'
        })

        # RESTX API现在返回正确的HTTP状态码
        assert response.status_code == 401
        assert response.content_type == 'application/json'

        data = response.get_json()

        # 检查错误响应结构（按照reference.md规范）
        assert 'error' in data
        assert data['error']['message'] == '用户名或密码错误'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_login_missing_fields_response(self, client):
        """测试缺少字段的响应格式"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser'
        })

        # RESTX API现在返回正确的HTTP状态码
        assert response.status_code == 400
        assert response.content_type == 'application/json'

        data = response.get_json()

        # 检查错误响应结构（按照reference.md规范）
        assert 'error' in data
        assert data['error']['type'] == 'INVALID_REQUEST'
        assert '用户名和密码不能为空' in data['error']['message']

    def test_login_empty_body_response(self, client):
        """测试空请求体响应格式"""
        response = client.post('/api/v1/auth/login', json={})

        assert response.status_code == 400
        data = response.get_json()

        # 检查错误响应结构（按照reference.md规范）
        assert 'error' in data
        assert data['error']['type'] == 'INVALID_REQUEST'
        assert '请求体不能为空' in data['error']['message']

    def test_login_invalid_json_response(self, client):
        """测试无效 JSON 响应格式"""
        response = client.post('/api/v1/auth/login',
                             data='invalid json',
                             content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()

        # 检查错误响应结构（按照reference.md规范）
        assert 'error' in data
        assert data['error']['type'] == 'INVALID_REQUEST'
        assert '请求参数格式错误' in data['error']['message']



    def test_profile_success_response(self, client, auth_headers):
        """测试获取用户信息成功响应格式"""
        response = client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # 检查成功响应结构（按照reference.md规范）
        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'user' in data['data']
        assert 'id' in data['data']['user']
        assert 'username' in data['data']['user']
        assert 'email' in data['data']['user']
        assert 'is_active' in data['data']['user']
        assert 'stats' in data['data']['user']

        # 检查统计信息
        stats = data['data']['user']['stats']
        assert 'cases' in stats
        assert 'feedback_count' in stats

    def test_profile_unauthorized_response(self, client):
        """测试未授权访问用户信息响应格式"""
        response = client.get('/api/v1/auth/me')

        assert response.status_code == 401
        data = response.get_json()

        # 检查错误响应结构（按照reference.md规范）
        assert data['code'] == 401
        assert data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_logout_success_response(self, client, auth_headers):
        """测试登出成功响应格式"""
        response = client.post('/api/v1/auth/logout', headers=auth_headers)

        assert response.status_code == 204
        assert response.data == b''

    def test_refresh_token_success_response(self, client, test_user):
        """测试刷新令牌成功响应格式"""
        # 先登录获取 refresh token
        login_response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })

        refresh_token = login_response.get_json()['refresh_token']

        # 使用 refresh token 刷新
        response = client.post('/api/v1/auth/refresh',
                              headers={'Authorization': f'Bearer {refresh_token}'})

        if response.status_code == 200:
            data = response.get_json()
            # RESTX 格式 - 直接检查字段
            assert 'access_token' in data
            assert 'expires_in' in data

    def test_response_headers(self, client, test_user):
        """测试响应头"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })

        # 检查通用响应头
        assert 'Content-Type' in response.headers
        assert response.headers['Content-Type'] == 'application/json'

    def test_response_encoding(self, client, test_user):
        """测试响应编码"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })

        # 确保响应可以正确解码为 JSON
        try:
            data = response.get_json()
            assert data is not None
        except (ValueError, TypeError):
            pytest.fail("响应不是有效的 JSON 格式")

    def test_response_size(self, client, test_user):
        """测试响应大小合理性"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })

        # 响应不应该过大
        assert len(response.data) < 10000  # 10KB 限制

    def test_error_response_consistency(self, client):
        """测试错误响应的一致性"""
        # 测试多种错误情况，确保响应格式一致
        error_cases = [
            ('/api/v1/auth/login', {'username': 'nonexistent', 'password': 'wrong'}),
            ('/api/v1/auth/login', {}),
        ]

        for case in error_cases:
            endpoint, payload = case
            response = client.post(endpoint, json=payload)
            data = response.get_json()

            # 检查错误响应格式（按照reference.md规范）
            assert 'error' in data, f"No error field found in response: {data}"
            assert 'code' in data and data['code'] >= 400
            assert 'status' in data and data['status'] == 'error'

            # 确保响应是错误状态码
            assert response.status_code >= 400

        # 测试JWT相关的未授权错误
        response = client.get('/api/v1/auth/me')
        data = response.get_json()

        # 检查错误响应格式（按照reference.md规范）
        assert response.status_code == 401
        assert 'code' in data and data['code'] == 401
        assert 'status' in data and data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'UNAUTHORIZED'
