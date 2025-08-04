"""
API v1 统计接口测试

测试数据看板统计相关 API 的响应格式和功能。
"""

import pytest
import json
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.case import Case
from app.models.knowledge import KnowledgeDocument
from app.models.feedback import Feedback


class TestStatisticsAPI:
    """统计 API 测试类"""

    def test_get_statistics_success(self, client, auth_headers):
        """测试获取统计数据成功响应"""
        response = client.get('/api/v1/system/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data

    def test_get_statistics_structure(self, client, auth_headers):
        """测试统计数据结构完整性"""
        response = client.get('/api/v1/system/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()['data']

        # 检查必需字段
        required_fields = [
            'faultCategories',
            'resolutionTrend',
            'knowledgeCoverage',
            'systemOverview'
        ]

        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"

        # 检查故障分类数据结构
        fault_categories = data['faultCategories']
        assert isinstance(fault_categories, list)

        if fault_categories:
            category = fault_categories[0]
            assert 'name' in category
            assert 'value' in category
            assert isinstance(category['value'], int)

        # 检查解决率趋势数据结构
        resolution_trend = data['resolutionTrend']
        assert isinstance(resolution_trend, list)

        if resolution_trend:
            trend_item = resolution_trend[0]
            assert 'date' in trend_item
            assert 'rate' in trend_item
            assert isinstance(trend_item['rate'], (int, float))

        # 检查知识覆盖度数据结构
        knowledge_coverage = data['knowledgeCoverage']
        assert isinstance(knowledge_coverage, dict)
        assert 'heatmapData' in knowledge_coverage
        assert 'overallStats' in knowledge_coverage

        # 检查heatmapData结构
        heatmap_data = knowledge_coverage['heatmapData']
        assert isinstance(heatmap_data, list)

        if heatmap_data:
            coverage_item = heatmap_data[0]
            assert 'topic' in coverage_item
            assert 'vendor' in coverage_item
            assert 'coverage' in coverage_item
            assert isinstance(coverage_item['coverage'], (int, float))

        # 检查系统概览数据结构
        system_overview = data['systemOverview']
        assert isinstance(system_overview, dict)

        overview_fields = [
            'totalCases',
            'solvedCases',
            'resolutionRate',
            'totalDocuments',
            'activeUsers'
        ]

        for field in overview_fields:
            assert field in system_overview, f"系统概览缺少字段: {field}"

    def test_get_statistics_time_ranges(self, client, auth_headers):
        """测试不同时间范围的统计数据"""
        time_ranges = ['7d', '30d', '90d']

        for time_range in time_ranges:
            response = client.get(f'/api/v1/system/statistics?timeRange={time_range}',
                                headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

    def test_get_statistics_invalid_time_range(self, client, auth_headers):
        """测试无效时间范围参数"""
        response = client.get('/api/v1/system/statistics?timeRange=invalid',
                            headers=auth_headers)

        # 应该使用默认值，不报错
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200

    def test_get_statistics_unauthorized(self, client):
        """测试未授权访问统计数据"""
        response = client.get('/api/v1/system/statistics')

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_statistics_response_format_consistency(self, client, auth_headers):
        """测试统计数据响应格式一致性"""
        response = client.get('/api/v1/system/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # 检查响应格式是否符合API文档规范
        assert 'code' in data
        assert 'status' in data
        assert 'data' in data
        assert data['code'] == 200
        assert data['status'] == 'success'

    def test_statistics_data_consistency(self, client, auth_headers):
        """测试统计数据的数据一致性"""
        response = client.get('/api/v1/system/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()['data']

        system_overview = data['systemOverview']

        # 检查数据逻辑一致性
        if 'totalCases' in system_overview and 'solvedCases' in system_overview:
            total_cases = system_overview['totalCases']
            solved_cases = system_overview['solvedCases']

            # 解决的案例数不应超过总案例数
            assert solved_cases <= total_cases

            # 如果有解决率字段，检查计算是否正确
            if 'resolutionRate' in system_overview and total_cases > 0:
                expected_rate = round((solved_cases / total_cases) * 100, 1)
                actual_rate = system_overview['resolutionRate']
                # 允许小的浮点误差
                assert abs(actual_rate - expected_rate) < 0.1

    def test_statistics_caching_behavior(self, client, auth_headers):
        """测试统计数据缓存行为"""
        # 第一次请求
        response1 = client.get('/api/v1/system/statistics', headers=auth_headers)
        assert response1.status_code == 200

        # 第二次请求（应该从缓存获取）
        response2 = client.get('/api/v1/system/statistics', headers=auth_headers)
        assert response2.status_code == 200

        # 两次响应的数据结构应该一致
        data1 = response1.get_json()['data']
        data2 = response2.get_json()['data']

        assert data1.keys() == data2.keys()

    def test_statistics_performance(self, client, auth_headers):
        """测试统计数据接口性能"""
        import time

        start_time = time.time()
        response = client.get('/api/v1/system/statistics', headers=auth_headers)
        end_time = time.time()

        assert response.status_code == 200

        # 响应时间应该在合理范围内（这里设置为3秒）
        response_time = end_time - start_time
        assert response_time < 3.0, f"统计接口响应时间过长: {response_time:.2f}秒"

    def test_statistics_empty_database(self, client, auth_headers):
        """测试空数据库情况下的统计数据"""
        # 在空数据库情况下，接口应该正常返回默认值
        response = client.get('/api/v1/system/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data

        # 即使数据库为空，也应该返回基本的数据结构
        stats_data = data['data']
        assert 'faultCategories' in stats_data
        assert 'resolutionTrend' in stats_data
        assert 'knowledgeCoverage' in stats_data
        assert 'systemOverview' in stats_data

    def test_statistics_with_mock_data(self, client, auth_headers, test_user):
        """测试带有模拟数据的统计功能"""
        # 这个测试需要在有实际数据的情况下运行
        # 可以在测试前创建一些模拟数据来验证统计功能

        # 创建一些测试案例
        test_cases = []
        for i in range(5):
            case = Case(
                title=f"测试案例 {i+1}",
                user_id=test_user.id,
                status='solved' if i < 3 else 'open'
            )
            test_cases.append(case)

        db.session.add_all(test_cases)
        db.session.commit()

        try:
            response = client.get('/api/v1/system/statistics', headers=auth_headers)

            assert response.status_code == 200
            data = response.get_json()['data']

            # 验证系统概览数据反映了我们创建的测试数据
            system_overview = data['systemOverview']
            assert system_overview['totalCases'] >= 5
            assert system_overview['solvedCases'] >= 3

        finally:
            # 清理测试数据
            for case in test_cases:
                db.session.delete(case)
            db.session.commit()
