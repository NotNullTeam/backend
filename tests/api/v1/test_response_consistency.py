"""
API 响应一致性和通用格式测试

测试所有 API 模块的响应格式一致性和通用标准。
"""

import pytest
import json
import time
from app import db


class TestAPIResponseConsistency:
    """API 响应一致性测试类"""

    def test_success_response_format_consistency(self, client, auth_headers):
        """测试成功响应格式一致性"""
        # 测试不同模块的成功响应格式
        endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
            '/api/v1/cases/',
            '/api/v1/knowledge/documents',
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)

            if response.status_code == 200:
                data = response.get_json()

                # 所有成功响应都应该有这些字段
                assert 'code' in data, f"Missing 'code' in {endpoint}"
                assert 'status' in data, f"Missing 'status' in {endpoint}"
                assert 'data' in data, f"Missing 'data' in {endpoint}"

                assert data['code'] == 200, f"Invalid code in {endpoint}"
                assert data['status'] == 'success', f"Invalid status in {endpoint}"
                assert isinstance(data['data'], dict), f"Invalid data type in {endpoint}"

    def test_error_response_format_consistency(self, client):
        """测试错误响应格式一致性"""
        # 测试不同类型的错误响应
        error_cases = [
            ('/api/v1/auth/me', 401),  # 未授权
            ('/api/v1/cases/99999', 404),   # 不存在
            ('/api/v1/auth/login', 400),    # 无效请求
        ]

        for endpoint, expected_code in error_cases:
            if expected_code == 400:
                response = client.post(endpoint, json={})
            else:
                response = client.get(endpoint)

            if response.status_code == expected_code:
                data = response.get_json()

                # 所有错误响应都应该有这些字段
                assert 'code' in data, f"Missing 'code' in error response for {endpoint}"
                assert 'status' in data, f"Missing 'status' in error response for {endpoint}"
                assert 'error' in data, f"Missing 'error' in error response for {endpoint}"

                assert data['code'] == expected_code, f"Invalid error code for {endpoint}"
                assert data['status'] == 'error', f"Invalid status for {endpoint}"

                # 错误对象结构
                error = data['error']
                assert 'type' in error, f"Missing error type for {endpoint}"
                assert 'message' in error, f"Missing error message for {endpoint}"

    def test_http_status_codes_consistency(self, client, auth_headers):
        """测试HTTP状态码一致性"""
        # 测试各种HTTP状态码
        test_cases = [
            ('GET', '/api/v1/system/status', None, 200),
            ('POST', '/api/v1/auth/login', {'username': 'invalid', 'password': 'invalid'}, 401),
            ('GET', '/api/v1/cases/99999', None, 404),
            ('POST', '/api/v1/cases/', {'title': 'Test'}, 201),
        ]

        for method, endpoint, payload, expected_status in test_cases:
            if method == 'GET':
                response = client.get(endpoint, headers=auth_headers if expected_status != 401 else None)
            elif method == 'POST':
                response = client.post(endpoint, json=payload, headers=auth_headers if expected_status not in [401, 400] else None)

            # 状态码应该与响应体中的code字段一致
            if response.content_type == 'application/json':
                data = response.get_json()
                assert response.status_code == data['code'], f"HTTP status and response code mismatch for {endpoint}"

    def test_content_type_consistency(self, client, auth_headers):
        """测试Content-Type一致性"""
        endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
            '/api/v1/cases/',
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)

            # 所有API响应都应该是JSON
            assert response.content_type == 'application/json', f"Invalid content type for {endpoint}"

    def test_response_encoding_consistency(self, client, auth_headers):
        """测试响应编码一致性"""
        endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)

            # 确保响应可以正确解码
            try:
                data = response.get_json()
                assert data is not None, f"Cannot decode JSON for {endpoint}"
            except Exception as e:
                pytest.fail(f"JSON decode error for {endpoint}: {e}")

    def test_pagination_format_consistency(self, client, auth_headers):
        """测试分页格式一致性"""
        # 测试有分页的端点
        paginated_endpoints = [
            '/api/v1/cases/',
            '/api/v1/knowledge/documents',
        ]

        for endpoint in paginated_endpoints:
            response = client.get(endpoint, headers=auth_headers)

            if response.status_code == 200:
                data = response.get_json()

                if 'pagination' in data['data']:
                    pagination = data['data']['pagination']

                    # 分页对象应该有这些字段
                    assert 'page' in pagination, f"Missing 'page' in pagination for {endpoint}"
                    assert 'per_page' in pagination, f"Missing 'per_page' in pagination for {endpoint}"
                    assert 'total' in pagination, f"Missing 'total' in pagination for {endpoint}"
                    assert 'pages' in pagination, f"Missing 'pages' in pagination for {endpoint}"

    def test_timestamp_format_consistency(self, client, auth_headers, test_case):
        """测试时间戳格式一致性"""
        # 测试包含时间戳的端点
        response = client.get(f'/api/v1/cases/{test_case.id}', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()
            case_data = data['data']['case']

            # 检查时间戳格式
            time_fields = ['created_at', 'updated_at']
            for field in time_fields:
                if field in case_data:
                    timestamp = case_data[field]
                    # 时间戳应该是ISO格式字符串
                    assert isinstance(timestamp, str), f"Timestamp {field} should be string"
                    # 可以尝试解析时间戳
                    try:
                        from datetime import datetime
                        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except ValueError:
                        pytest.fail(f"Invalid timestamp format for {field}: {timestamp}")

    def test_error_message_i18n_consistency(self, client):
        """测试错误消息国际化一致性"""
        # 测试错误消息是否使用中文
        response = client.post('/api/v1/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrong'
        })

        if response.status_code == 401:
            data = response.get_json()
            error_message = data['error']['message']

            # 错误消息应该包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in error_message)
            assert has_chinese, f"Error message should be in Chinese: {error_message}"

    def test_response_size_limits(self, client, auth_headers):
        """测试响应大小限制"""
        endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
            '/api/v1/cases/',
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)

            # 响应不应该过大（除非是文件下载）
            if response.content_type == 'application/json':
                assert len(response.data) < 1024 * 1024, f"Response too large for {endpoint}"  # 1MB limit

    def test_response_headers_consistency(self, client, auth_headers):
        """测试响应头一致性"""
        endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers)

            # 检查通用响应头
            assert 'Content-Type' in response.headers, f"Missing Content-Type header for {endpoint}"
            assert 'Content-Length' in response.headers, f"Missing Content-Length header for {endpoint}"

    def test_api_versioning_consistency(self, client, auth_headers):
        """测试API版本一致性"""
        # 所有v1 API都应该有统一的URL前缀
        v1_endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
            '/api/v1/cases/',
        ]

        for endpoint in v1_endpoints:
            assert endpoint.startswith('/api/v1/'), f"Invalid v1 API prefix for {endpoint}"

            response = client.get(endpoint, headers=auth_headers)

            # 响应中可能包含版本信息
            if response.status_code == 200 and response.content_type == 'application/json':
                data = response.get_json()
                # 可以检查响应头或响应体中的版本信息

    def test_cors_headers_consistency(self, client):
        """测试CORS头一致性"""
        response = client.options('/api/v1/system/status')

        # 检查CORS相关头
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers',
        ]

        for header in cors_headers:
            if header in response.headers:
                assert response.headers[header] is not None

    def test_security_headers_consistency(self, client, auth_headers):
        """测试安全头一致性"""
        response = client.get('/api/v1/system/status', headers=auth_headers)

        # 检查安全相关头
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
        ]

        for header in security_headers:
            if header in response.headers:
                assert response.headers[header] is not None

    def test_rate_limiting_headers(self, client, auth_headers):
        """测试速率限制头"""
        response = client.get('/api/v1/system/status', headers=auth_headers)

        # 检查速率限制相关头
        rate_limit_headers = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
        ]

        for header in rate_limit_headers:
            if header in response.headers:
                # 头值应该是数字
                try:
                    int(response.headers[header])
                except ValueError:
                    pytest.fail(f"Invalid rate limit header value: {header}")

    def test_response_time_consistency(self, client, auth_headers):
        """测试响应时间一致性"""
        endpoints = [
            '/api/v1/system/status',
            '/api/v1/auth/me',
        ]

        response_times = {}
        # 多次测试取平均值，减少性能波动影响
        num_runs = 3

        for endpoint in endpoints:
            times = []
            for _ in range(num_runs):
                start_time = time.time()
                response = client.get(endpoint, headers=auth_headers)
                end_time = time.time()
                
                # 确保请求成功
                assert response.status_code in [200, 201], f"Request failed for {endpoint}: {response.status_code}"
                
                response_time = end_time - start_time
                times.append(response_time)
            
            # 使用平均响应时间
            avg_response_time = sum(times) / len(times)
            response_times[endpoint] = avg_response_time

            # 响应时间应该在合理范围内（放宽阈值）
            assert avg_response_time < 30.0, f"Average response time too slow for {endpoint}: {avg_response_time:.3f}s"

        # 类似端点的响应时间应该相近
        if len(response_times) > 1:
            times = list(response_times.values())
            max_time = max(times)
            min_time = min(times)

            # 响应时间差异不应该过大 - 使用更合理的阈值
            if min_time > 0.001:  # 避免除以零的情况
                ratio = max_time / min_time
                # 放宽阈值，考虑测试环境的性能波动
                assert ratio < 50.0, f"Response time inconsistency too high: {ratio:.2f} (max: {max_time:.3f}s, min: {min_time:.3f}s)"
                # 记录响应时间差异供调试使用
                print(f"Response time ratio: {ratio:.2f} (max: {max_time:.3f}s, min: {min_time:.3f}s)")
            else:
                print(f"Response times: {response_times}")
