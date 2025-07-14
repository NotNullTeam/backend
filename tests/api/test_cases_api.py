"""
IP智慧解答专家系统 - 案例管理API测试

本模块测试案例管理相关的API接口。
"""

import pytest
import json
from app.models.case import Case, Node, Edge


@pytest.mark.api
@pytest.mark.cases
class TestCasesListAPI:
    """测试案例列表API"""

    def test_get_cases_success(self, client, auth_headers, sample_user, database):
        """测试成功获取案例列表"""
        # 创建测试案例
        case1 = Case(title='测试案例1', status='open', user_id=sample_user.id)
        case2 = Case(title='测试案例2', status='solved', user_id=sample_user.id)
        database.session.add_all([case1, case2])
        database.session.commit()

        response = client.get('/api/v1/cases', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert len(data['data']['items']) >= 2
        assert data['data']['total'] >= 2

    def test_get_cases_with_status_filter(self, client, auth_headers, sample_user, database):
        """测试按状态过滤案例列表"""
        # 创建不同状态的案例
        case1 = Case(title='开放案例', status='open', user_id=sample_user.id)
        case2 = Case(title='已解决案例', status='solved', user_id=sample_user.id)
        database.session.add_all([case1, case2])
        database.session.commit()

        # 测试过滤开放案例
        response = client.get('/api/v1/cases?status=open', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        # 验证返回的案例都是open状态
        for item in data['data']['items']:
            assert item['status'] == 'open'

    def test_get_cases_unauthorized(self, client):
        """测试未授权访问案例列表"""
        response = client.get('/api/v1/cases')

        assert response.status_code == 401

    def test_get_cases_pagination(self, client, auth_headers, sample_user, database):
        """测试案例列表分页"""
        # 创建多个案例
        cases = []
        for i in range(15):
            case = Case(title=f'测试案例{i}', user_id=sample_user.id)
            cases.append(case)
        database.session.add_all(cases)
        database.session.commit()

        # 测试第一页
        response = client.get('/api/v1/cases?page=1&pageSize=10', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert len(data['data']['items']) <= 10
        assert data['data']['page'] == 1
        assert data['data']['pageSize'] == 10


@pytest.mark.api
@pytest.mark.cases
class TestCaseCreateAPI:
    """测试案例创建API"""

    def test_create_case_success(self, client, auth_headers):
        """测试成功创建案例"""
        case_data = {
            'query': '网络连接问题，无法ping通网关',
            'attachments': []
        }

        response = client.post('/api/v1/cases', 
                             json=case_data, 
                             headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'caseId' in data['data']
        assert data['data']['title'] == case_data['query']
        assert data['data']['status'] == 'open'
        assert len(data['data']['nodes']) == 2  # 用户问题节点 + AI分析节点
        assert len(data['data']['edges']) == 1

    def test_create_case_with_attachments(self, client, auth_headers):
        """测试创建带附件的案例"""
        case_data = {
            'query': '路由器配置问题',
            'attachments': [
                {'name': 'config.txt', 'url': 'http://example.com/config.txt'}
            ]
        }

        response = client.post('/api/v1/cases', 
                             json=case_data, 
                             headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        # 验证附件信息保存在用户问题节点中
        user_node = next(node for node in data['data']['nodes'] if node['type'] == 'USER_QUERY')
        assert user_node['content']['attachments'] == case_data['attachments']

    def test_create_case_empty_query(self, client, auth_headers):
        """测试创建空查询的案例"""
        case_data = {
            'query': '',
            'attachments': []
        }

        response = client.post('/api/v1/cases', 
                             json=case_data, 
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '问题描述不能为空' in data['error']['message']

    def test_create_case_missing_query(self, client, auth_headers):
        """测试创建缺少查询字段的案例"""
        case_data = {
            'attachments': []
        }

        response = client.post('/api/v1/cases', 
                             json=case_data, 
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'

    def test_create_case_unauthorized(self, client):
        """测试未授权创建案例"""
        case_data = {
            'query': '测试问题',
            'attachments': []
        }

        response = client.post('/api/v1/cases', json=case_data)

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.cases
class TestCaseDetailAPI:
    """测试案例详情API"""

    def test_get_case_detail_success(self, client, auth_headers, sample_case):
        """测试成功获取案例详情"""
        response = client.get(f'/api/v1/cases/{sample_case.id}', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['caseId'] == sample_case.id
        assert data['data']['title'] == sample_case.title
        assert data['data']['status'] == sample_case.status

    def test_get_case_detail_not_found(self, client, auth_headers):
        """测试获取不存在的案例详情"""
        fake_case_id = 'non-existent-case-id'
        response = client.get(f'/api/v1/cases/{fake_case_id}', headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'

    def test_get_case_detail_unauthorized(self, client, sample_case):
        """测试未授权访问案例详情"""
        response = client.get(f'/api/v1/cases/{sample_case.id}')

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.cases
class TestCaseUpdateAPI:
    """测试案例更新API"""

    def test_update_case_success(self, client, auth_headers, sample_case):
        """测试成功更新案例"""
        update_data = {
            'title': '更新后的标题',
            'status': 'solved'
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}', 
                            json=update_data, 
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['title'] == update_data['title']
        assert data['data']['status'] == update_data['status']

    def test_update_case_not_found(self, client, auth_headers):
        """测试更新不存在的案例"""
        fake_case_id = 'non-existent-case-id'
        update_data = {
            'title': '更新后的标题'
        }

        response = client.put(f'/api/v1/cases/{fake_case_id}', 
                            json=update_data, 
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'


@pytest.mark.api
@pytest.mark.cases
class TestCaseDeleteAPI:
    """测试案例删除API"""

    def test_delete_case_success(self, client, auth_headers, sample_case):
        """测试成功删除案例"""
        response = client.delete(f'/api/v1/cases/{sample_case.id}', headers=auth_headers)

        assert response.status_code == 204

    def test_delete_case_not_found(self, client, auth_headers):
        """测试删除不存在的案例"""
        fake_case_id = 'non-existent-case-id'
        response = client.delete(f'/api/v1/cases/{fake_case_id}', headers=auth_headers)

        assert response.status_code == 404
