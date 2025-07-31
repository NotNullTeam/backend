"""
IP智慧解答专家系统 - 统计API测试

本模块测试数据看板相关的统计API接口 - 任务6实现
"""

import pytest
import json
from datetime import datetime, timedelta
from app.models.user import User
from app.models.case import Case, Node
from app.models.knowledge import KnowledgeDocument
from app.models.feedback import Feedback


@pytest.mark.api
@pytest.mark.statistics
class TestStatisticsAPI:
    """测试统计API"""

    def test_get_statistics_success(self, client, auth_headers, sample_cases_data):
        """测试获取统计数据成功"""
        response = client.get('/api/v1/statistics', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # 验证返回数据结构
        assert 'faultCategories' in data
        assert 'resolutionTrend' in data
        assert 'knowledgeCoverage' in data
        assert 'systemOverview' in data
        assert 'timestamp' in data

        # 验证故障分类数据
        fault_categories = data['faultCategories']
        assert isinstance(fault_categories, list)
        assert len(fault_categories) > 0

        # 验证解决率趋势数据
        resolution_trend = data['resolutionTrend']
        assert isinstance(resolution_trend, list)

        # 验证知识覆盖度数据
        knowledge_coverage = data['knowledgeCoverage']
        assert isinstance(knowledge_coverage, list)

        # 验证系统概览数据
        system_overview = data['systemOverview']
        assert isinstance(system_overview, dict)
        assert 'totalCases' in system_overview
        assert 'resolutionRate' in system_overview

    def test_get_statistics_with_time_ranges(self, client, auth_headers):
        """测试不同时间范围的统计数据"""
        time_ranges = ['7d', '30d', '90d']

        for time_range in time_ranges:
            response = client.get(
                f'/api/v1/statistics?timeRange={time_range}',
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data is not None, f"时间范围 {time_range} 返回了 None"
            assert 'resolutionTrend' in data
            assert 'systemOverview' in data

    def test_get_statistics_unauthorized(self, client):
        """测试未授权访问统计API"""
        response = client.get('/api/v1/statistics')
        assert response.status_code == 401

    def test_get_cases_timeline_success(self, client, auth_headers):
        """测试获取案例时间线成功"""
        response = client.get('/api/v1/statistics/cases-timeline', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert 'timeline' in data
        timeline = data['timeline']
        assert isinstance(timeline, list)

    def test_get_cases_timeline_with_days_parameter(self, client, auth_headers):
        """测试带天数参数的案例时间线"""
        response = client.get(
            '/api/v1/statistics/cases-timeline?days=7',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data is not None, "案例时间线API返回了 None"

        timeline = data['timeline']
        assert len(timeline) == 7  # 应该返回7天的数据    def test_get_top_issues_success(self, client, auth_headers):
        """测试获取常见问题成功"""
        response = client.get('/api/v1/statistics/top-issues', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert 'topIssues' in data
        top_issues = data['topIssues']
        assert isinstance(top_issues, list)

    def test_get_top_issues_with_limit(self, client, auth_headers):
        """测试带限制参数的常见问题"""
        limit = 5
        response = client.get(
            f'/api/v1/statistics/top-issues?limit={limit}',
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data is not None, "常见问题API返回了 None"

        top_issues = data['topIssues']
        assert len(top_issues) <= limit
@pytest.mark.integration
@pytest.mark.statistics
class TestStatisticsPerformance:
    """测试统计API性能"""

    def test_statistics_database_indexes(self, app, database):
        """测试数据库索引是否存在"""
        with app.app_context():
            from sqlalchemy import text

            # 在测试环境中，我们只检查基本索引是否存在
            # 因为测试数据库是内存数据库，不会运行迁移
            basic_indexes_to_check = [
                "ix_users_created_at",
                "ix_users_email",
                "ix_users_username",
                "ix_cases_created_at"
            ]

            for index_name in basic_indexes_to_check:
                result = database.session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=:index_name"
                ), {"index_name": index_name}).fetchone()

                assert result is not None, f"基本索引 {index_name} 不存在"

        # 注意：这个测试主要验证索引查询逻辑，而不是实际的性能索引
        # 实际的性能索引在生产环境中通过迁移添加

    def test_statistics_response_time(self, client, auth_headers):
        """测试统计API响应时间"""
        import time

        start_time = time.time()
        response = client.get('/api/v1/statistics', headers=auth_headers)
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0, f"统计API响应时间过长: {response_time}秒"


@pytest.mark.unit
class TestStatisticsHelpers:
    """测试统计辅助函数"""

    def test_fault_categories_with_no_data(self, app, database):
        """测试无数据时的故障分类"""
        with app.app_context():
            from app.api.statistics import _get_fault_categories
            from datetime import datetime, timedelta

            start_date = datetime.utcnow() - timedelta(days=30)
            categories = _get_fault_categories(start_date)

            assert isinstance(categories, list)
            assert len(categories) > 0  # 应该返回默认分类

    def test_system_overview_calculation(self, app, database, sample_cases_data):
        """测试系统概览计算"""
        with app.app_context():
            from app.api.statistics import _get_system_overview
            from datetime import datetime, timedelta

            start_date = datetime.utcnow() - timedelta(days=30)
            overview = _get_system_overview(start_date)

            assert isinstance(overview, dict)
            assert 'totalCases' in overview
            assert 'resolutionRate' in overview
            assert 'totalDocuments' in overview
            assert overview['resolutionRate'] >= 0
            assert overview['resolutionRate'] <= 100


# 辅助函数，用于创建测试数据
def create_sample_statistics_data(db):
    """创建统计测试数据"""
    from app.models.user import User
    from app.models.case import Case, Node
    from datetime import datetime, timedelta

    # 创建测试用户
    user = User(
        username='stats_test_user',
        email='stats@test.com'
    )
    user.set_password('testpass')
    db.session.add(user)
    db.session.flush()

    # 创建测试案例
    for i in range(10):
        case = Case(
            title=f'测试案例 {i+1}',
            status='solved' if i % 3 == 0 else 'open',
            user_id=user.id,
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        db.session.add(case)
        db.session.flush()

        # 为每个案例创建节点
        node = Node(
            case_id=case.id,
            type='USER_QUERY',
            title=f'查询节点 {i+1}',
            created_at=case.created_at
        )
        db.session.add(node)

    db.session.commit()
    return user
