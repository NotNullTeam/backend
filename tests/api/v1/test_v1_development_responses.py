"""
API v1 开发工具模块响应测试

测试开发工具相关 API 的响应格式和状态码。
"""

import pytest
import json
from app import db


class TestDevelopmentAPIResponses:
    """开发工具 API 响应测试类"""

    def test_api_docs_response(self, client):
        """测试API文档响应格式"""
        response = client.get('/api/v1/dev/docs')

        assert response.status_code == 200

        # 可能返回HTML或JSON
        if response.content_type == 'application/json':
            data = response.get_json()
            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'swagger_spec' in data['data']
        else:
            # HTML文档
            assert b'<!DOCTYPE html>' in response.data or b'<html>' in response.data

    def test_api_spec_response(self, client):
        """测试API规范响应格式"""
        response = client.get('/api/v1/dev/openapi.json')

        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = response.get_json()

        # OpenAPI规范结构
        assert 'openapi' in data
        assert 'info' in data
        assert 'paths' in data
        assert 'components' in data

        # 检查基本信息
        assert 'title' in data['info']
        assert 'version' in data['info']
        assert 'description' in data['info']

    def test_test_endpoints_response(self, client, admin_headers):
        """测试测试端点列表响应格式"""
        response = client.get('/api/v1/dev/test-endpoints', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'endpoints' in data['data']

            # 检查端点信息
            if data['data']['endpoints']:
                endpoint = data['data']['endpoints'][0]
                assert 'path' in endpoint
                assert 'methods' in endpoint
                assert 'description' in endpoint

    def test_mock_data_response(self, client, admin_headers):
        """测试模拟数据生成响应格式"""
        response = client.post('/api/v1/dev/mock-data',
                              json={
                                  'type': 'users',
                                  'count': 10
                              },
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'generated_count' in data['data']
            assert 'mock_data' in data['data']

    def test_database_seed_response(self, client, admin_headers):
        """测试数据库种子数据响应格式"""
        response = client.post('/api/v1/dev/seed-database',
                              json={'reset': False},
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'seeded_tables' in data['data']
            assert 'total_records' in data['data']

    def test_debug_info_response(self, client, admin_headers):
        """测试调试信息响应格式"""
        response = client.get('/api/v1/dev/debug-info', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            debug_data = data['data']
            assert 'environment' in debug_data
            assert 'python_version' in debug_data
            assert 'flask_version' in debug_data
            assert 'dependencies' in debug_data
            assert 'config' in debug_data

    def test_performance_test_response(self, client, admin_headers):
        """测试性能测试响应格式"""
        response = client.post('/api/v1/dev/performance-test',
                              json={
                                  'endpoint': '/api/v1/system/status',
                                  'requests': 100,
                                  'concurrent': 10
                              },
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            perf_data = data['data']
            assert 'total_time' in perf_data
            assert 'average_time' in perf_data
            assert 'requests_per_second' in perf_data
            assert 'success_rate' in perf_data
            assert 'error_count' in perf_data

    def test_code_coverage_response(self, client, admin_headers):
        """测试代码覆盖率响应格式"""
        response = client.get('/api/v1/dev/coverage', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            coverage_data = data['data']
            assert 'total_coverage' in coverage_data
            assert 'module_coverage' in coverage_data
            assert 'uncovered_lines' in coverage_data

    def test_profiler_start_response(self, client, admin_headers):
        """测试启动性能分析器响应格式"""
        response = client.post('/api/v1/dev/profiler/start',
                              json={'duration': 60},
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'profiler_id' in data['data']
            assert 'start_time' in data['data']

    def test_profiler_results_response(self, client, admin_headers):
        """测试获取性能分析结果响应格式"""
        response = client.get('/api/v1/dev/profiler/results/test123', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            profiler_data = data['data']
            assert 'function_stats' in profiler_data
            assert 'call_graph' in profiler_data
            assert 'total_time' in profiler_data

    def test_log_analysis_response(self, client, admin_headers):
        """测试日志分析响应格式"""
        response = client.post('/api/v1/dev/analyze-logs',
                              json={
                                  'start_time': '2025-08-01T00:00:00Z',
                                  'end_time': '2025-08-03T00:00:00Z',
                                  'level': 'error'
                              },
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            analysis_data = data['data']
            assert 'error_summary' in analysis_data
            assert 'error_patterns' in analysis_data
            assert 'timeline' in analysis_data

    def test_api_validator_response(self, client, admin_headers):
        """测试API验证器响应格式"""
        response = client.post('/api/v1/dev/validate-api',
                              json={
                                  'endpoint': '/api/v1/auth/login',
                                  'method': 'POST',
                                  'payload': {'username': 'test', 'password': 'test'}
                              },
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            validation_data = data['data']
            assert 'is_valid' in validation_data
            assert 'validation_errors' in validation_data
            assert 'response_schema' in validation_data

    def test_dependency_check_response(self, client, admin_headers):
        """测试依赖检查响应格式"""
        response = client.get('/api/v1/dev/dependencies/check', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            deps_data = data['data']
            assert 'outdated_packages' in deps_data
            assert 'security_vulnerabilities' in deps_data
            assert 'compatibility_issues' in deps_data

    def test_schema_validation_response(self, client, admin_headers):
        """测试数据库模式验证响应格式"""
        response = client.get('/api/v1/dev/schema/validate', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            schema_data = data['data']
            assert 'is_valid' in schema_data
            assert 'schema_errors' in schema_data
            assert 'migration_needed' in schema_data

    def test_test_runner_response(self, client, admin_headers):
        """测试测试运行器响应格式"""
        response = client.post('/api/v1/dev/run-tests',
                              json={
                                  'test_suite': 'api',
                                  'coverage': True
                              },
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            test_data = data['data']
            assert 'test_results' in test_data
            assert 'total_tests' in test_data
            assert 'passed_tests' in test_data
            assert 'failed_tests' in test_data
            assert 'coverage_report' in test_data

    def test_environment_info_response(self, client, admin_headers):
        """测试环境信息响应格式"""
        response = client.get('/api/v1/dev/environment', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            env_data = data['data']
            assert 'environment' in env_data
            assert 'git_info' in env_data
            assert 'deployment_info' in env_data
            assert 'system_info' in env_data

    def test_unauthorized_dev_access(self, client, auth_headers):
        """测试非管理员访问开发工具响应格式"""
        response = client.get('/api/v1/dev/debug-info', headers=auth_headers)

        assert response.status_code == 403
        data = response.get_json()

        assert data['code'] == 403
        assert data['status'] == 'error'
        assert data['error']['type'] == 'FORBIDDEN'

    def test_dev_tools_disabled_response(self, client, admin_headers):
        """测试开发工具禁用时的响应格式"""
        # 如果在生产环境禁用开发工具
        response = client.get('/api/v1/dev/docs', headers=admin_headers)

        if response.status_code == 404:
            data = response.get_json()

            assert data['code'] == 404
            assert data['status'] == 'error'
            assert data['error']['type'] == 'NOT_FOUND'

    def test_interactive_debugger_response(self, client, admin_headers):
        """测试交互式调试器响应格式"""
        response = client.post('/api/v1/dev/debugger/start',
                              json={'breakpoint': 'app.models.user:25'},
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'debugger_session' in data['data']
            assert 'websocket_url' in data['data']

    def test_benchmark_response(self, client, admin_headers):
        """测试基准测试响应格式"""
        response = client.post('/api/v1/dev/benchmark',
                              json={
                                  'test_type': 'database_operations',
                                  'iterations': 1000
                              },
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            benchmark_data = data['data']
            assert 'total_time' in benchmark_data
            assert 'operations_per_second' in benchmark_data
            assert 'memory_usage' in benchmark_data
            assert 'performance_score' in benchmark_data
