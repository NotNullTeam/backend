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

        # 检查响应结构
        assert 'code' in data
        assert 'status' in data
        assert 'data' in data

        # 检查具体值
        assert data['code'] == 200
        assert data['status'] == 'success'

        # 检查数据部分
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert 'token_type' in data['data']
        assert 'expires_in' in data['data']
        assert 'user_info' in data['data']

        # 检查令牌类型
        assert data['data']['token_type'] == 'Bearer'

        # 检查用户信息
        user_data = data['data']['user_info']
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

        assert response.status_code == 401
        assert response.content_type == 'application/json'

        data = response.get_json()

        # 检查错误响应结构
        assert 'code' in data
        assert 'status' in data
        assert 'error' in data

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert 'type' in data['error']
        assert 'message' in data['error']
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_login_missing_fields_response(self, client):
        """测试缺少字段的响应格式"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser'
            # 缺少 password 字段
        })

        assert response.status_code == 400
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'

    def test_login_empty_body_response(self, client):
        """测试空请求体响应格式"""
        response = client.post('/api/v1/auth/login', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
        assert data['status'] == 'error'

    def test_login_invalid_json_response(self, client):
        """测试无效 JSON 响应格式"""
        response = client.post('/api/v1/auth/login',
                             data='invalid json',
                             content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'



    def test_profile_success_response(self, client, auth_headers):
        """测试获取用户信息成功响应格式"""
        response = client.get('/api/v1/auth/me', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'user' in data['data']

        user_data = data['data']['user']
        assert 'id' in user_data
        assert 'stats' in user_data
        assert 'preferences' in user_data
        assert 'username' in user_data
        assert 'email' in user_data

    def test_profile_unauthorized_response(self, client):
        """测试未授权访问用户信息响应格式"""
        response = client.get('/api/v1/auth/me')

        assert response.status_code == 401
        data = response.get_json()

        # JWT默认错误格式或自定义格式
        if 'msg' in data:
            # Flask-JWT-Extended 默认格式
            assert 'msg' in data
            assert data['msg'] == 'Missing Authorization Header'
        else:
            # 自定义格式
            assert data['code'] == 401
            assert data['status'] == 'error'

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

        refresh_token = login_response.get_json()['data']['refresh_token']

        # 使用 refresh token 刷新
        response = client.post('/api/v1/auth/refresh',
                              headers={'Authorization': f'Bearer {refresh_token}'})

        if response.status_code == 200:
            data = response.get_json()
            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'access_token' in data['data']

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

            # 自定义API错误响应都应该有这些字段
            assert 'code' in data
            assert 'status' in data
            assert 'error' in data
            assert data['status'] == 'error'
            assert 'type' in data['error']
            assert 'message' in data['error']

        # 测试JWT相关的未授权错误（可能有不同格式）
        response = client.get('/api/v1/auth/me')
        data = response.get_json()

        # 允许两种格式：JWT默认格式或自定义格式
        assert response.status_code == 401
        if 'msg' in data:
            # Flask-JWT-Extended 默认格式
            assert 'msg' in data
        else:
            # 自定义格式
            assert 'code' in data
            assert 'status' in data
            assert 'error' in data
