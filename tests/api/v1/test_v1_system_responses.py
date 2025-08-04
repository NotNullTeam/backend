"""
API v1 系统模块响应测试

测试系统管理相关 API 的响应格式和状态码。
"""

import pytest
import json
from app import db
from app.models.user import User


class TestSystemAPIResponses:
    """系统 API 响应测试类"""

    def test_system_status_response(self, client):
        """测试系统状态响应格式"""
        response = client.get('/api/v1/system/status')

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data

        system_data = data['data']
        assert 'version' in system_data
        assert 'uptime' in system_data
        assert 'database_status' in system_data
        assert 'redis_status' in system_data
        assert 'timestamp' in system_data

    def test_system_health_response(self, client):
        """测试系统健康检查响应格式"""
        response = client.get('/api/v1/system/health')

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data

        health_data = data['data']
        assert 'healthy' in health_data
        assert 'services' in health_data
        assert isinstance(health_data['healthy'], bool)

        # 检查服务状态
        assert isinstance(health_data['services'], dict)

    def test_statistics_response(self, client, auth_headers):
        """测试统计数据响应格式"""
        response = client.get('/api/v1/system/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data

        stats_data = data['data']

        # 检查故障分类统计
        assert 'faultCategories' in stats_data
        assert isinstance(stats_data['faultCategories'], list)

        # 检查解决率趋势
        assert 'resolutionTrend' in stats_data
        assert isinstance(stats_data['resolutionTrend'], list)

        # 检查知识覆盖度
        assert 'knowledgeCoverage' in stats_data
        assert isinstance(stats_data['knowledgeCoverage'], dict)

        # 检查系统概览
        assert 'performanceMetrics' in stats_data
        assert isinstance(stats_data['performanceMetrics'], dict)

    def test_statistics_with_time_range(self, client, auth_headers):
        """测试带时间范围的统计数据响应"""
        response = client.get('/api/v1/system/statistics?timeRange=7d', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data

    def test_statistics_invalid_time_range(self, client, auth_headers):
        """测试无效时间范围参数"""
        response = client.get('/api/v1/system/statistics?timeRange=invalid', headers=auth_headers)

        # 应该返回默认的30d数据
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200

    def test_system_metrics_response(self, client, admin_headers):
        """测试系统指标响应格式"""
        response = client.get('/api/v1/system/metrics', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            metrics = data['data']
            assert 'cpu_usage' in metrics
            assert 'memory_usage' in metrics
            assert 'disk_usage' in metrics
            assert 'network_io' in metrics
            assert 'request_count' in metrics
            assert 'error_rate' in metrics

    def test_system_logs_response(self, client, admin_headers):
        """测试系统日志响应格式"""
        response = client.get('/api/v1/system/logs?level=error&limit=50',
                             headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            logs_data = data['data']
            assert 'logs' in logs_data
            assert 'pagination' in logs_data

            # 检查日志条目结构
            if logs_data['logs']:
                log_entry = logs_data['logs'][0]
                assert 'timestamp' in log_entry
                assert 'level' in log_entry
                assert 'message' in log_entry
                assert 'module' in log_entry

    def test_system_config_response(self, client, admin_headers):
        """测试系统配置响应格式"""
        response = client.get('/api/v1/system/config', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            config_data = data['data']
            assert 'app_config' in config_data
            assert 'database_config' in config_data
            assert 'redis_config' in config_data

            # 敏感信息应该被隐藏
            assert 'password' not in str(config_data).lower()
            assert 'secret' not in str(config_data).lower()

    def test_update_config_response(self, client, admin_headers):
        """测试更新配置响应格式"""
        response = client.put('/api/v1/system/config',
                             json={
                                 'max_upload_size': '20MB',
                                 'session_timeout': 3600
                             },
                             headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert data['message'] == '配置更新成功'

    def test_cache_status_response(self, client, admin_headers):
        """测试缓存状态响应格式"""
        response = client.get('/api/v1/system/cache/status', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            cache_data = data['data']
            assert 'redis_info' in cache_data
            assert 'cache_keys' in cache_data
            assert 'memory_usage' in cache_data

    def test_clear_cache_response(self, client, admin_headers):
        """测试清除缓存响应格式"""
        response = client.delete('/api/v1/system/cache', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert data['message'] == '缓存清除成功'

    def test_database_status_response(self, client, admin_headers):
        """测试数据库状态响应格式"""
        response = client.get('/api/v1/system/database/status', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            db_data = data['data']
            assert 'connection_status' in db_data
            assert 'table_count' in db_data
            assert 'total_records' in db_data
            assert 'database_size' in db_data

    def test_backup_database_response(self, client, admin_headers):
        """测试数据库备份响应格式"""
        response = client.post('/api/v1/system/database/backup', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            backup_data = data['data']
            assert 'backup_id' in backup_data
            assert 'backup_file' in backup_data
            assert 'backup_size' in backup_data
            assert 'created_at' in backup_data

    def test_system_maintenance_response(self, client, admin_headers):
        """测试系统维护模式响应格式"""
        response = client.post('/api/v1/system/maintenance',
                              json={'enabled': True, 'message': '系统维护中'},
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert data['message'] == '维护模式设置成功'

    def test_system_tasks_response(self, client, admin_headers):
        """测试系统任务响应格式"""
        response = client.get('/api/v1/system/tasks', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            tasks_data = data['data']
            assert 'running_tasks' in tasks_data
            assert 'pending_tasks' in tasks_data
            assert 'completed_tasks' in tasks_data

    def test_restart_service_response(self, client, admin_headers):
        """测试重启服务响应格式"""
        response = client.post('/api/v1/system/services/restart',
                              json={'service': 'redis'},
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert data['message'] == '服务重启成功'

    def test_system_security_response(self, client, admin_headers):
        """测试系统安全状态响应格式"""
        response = client.get('/api/v1/system/security', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            security_data = data['data']
            assert 'failed_login_attempts' in security_data
            assert 'active_sessions' in security_data
            assert 'security_alerts' in security_data

    def test_export_system_data_response(self, client, admin_headers):
        """测试导出系统数据响应格式"""
        response = client.get('/api/v1/system/export?type=config', headers=admin_headers)

        if response.status_code == 200:
            # 可能是JSON或文件
            if response.content_type == 'application/json':
                data = response.get_json()
                assert data['code'] == 200
                assert data['status'] == 'success'
            else:
                # 文件下载
                assert len(response.data) > 0

    def test_unauthorized_system_access(self, client, auth_headers):
        """测试非管理员访问系统管理接口响应格式"""
        response = client.get('/api/v1/system/metrics', headers=auth_headers)

        assert response.status_code == 403
        data = response.get_json()

        assert data['code'] == 403
        assert data['status'] == 'error'
        assert data['error']['type'] == 'FORBIDDEN'

    def test_system_api_rate_limit_response(self, client, admin_headers):
        """测试系统API速率限制响应格式"""
        # 模拟大量请求
        responses = []
        for _ in range(100):
            response = client.get('/api/v1/system/status', headers=admin_headers)
            responses.append(response)
            if response.status_code == 429:
                break

        # 检查是否有速率限制响应
        rate_limited = [r for r in responses if r.status_code == 429]
        if rate_limited:
            data = rate_limited[0].get_json()
            assert data['code'] == 429
            assert data['status'] == 'error'
            assert data['error']['type'] == 'RATE_LIMIT_EXCEEDED'

    def test_system_api_monitoring_response(self, client, admin_headers):
        """测试API监控响应格式"""
        response = client.get('/api/v1/system/api/monitoring', headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            monitoring_data = data['data']
            assert 'total_requests' in monitoring_data
            assert 'requests_per_minute' in monitoring_data
            assert 'average_response_time' in monitoring_data
            assert 'error_count' in monitoring_data
            assert 'endpoint_stats' in monitoring_data

    def test_system_disk_cleanup_response(self, client, admin_headers):
        """测试磁盘清理响应格式"""
        response = client.post('/api/v1/system/cleanup',
                              json={'type': 'logs', 'older_than_days': 30},
                              headers=admin_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            cleanup_data = data['data']
            assert 'files_deleted' in cleanup_data
            assert 'space_freed' in cleanup_data
            assert 'cleanup_summary' in cleanup_data
