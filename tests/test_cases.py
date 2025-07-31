"""
IP智慧解答专家系统 - 案例API测试

本模块测试案例相关的API接口。
"""

import pytest
import json
from app.models.case import Case, Node, Edge
from app.models.feedback import Feedback
from app import db


class TestCasesAPI:
    """案例API测试类"""

    def test_create_case_success(self, client, auth_headers):
        """测试创建案例成功"""
        response = client.post('/api/v1/cases',
                             headers=auth_headers,
                             json={
                                 'query': '我的网络设备无法连接互联网',
                                 'attachments': []
                             })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'caseId' in data['data']
        assert len(data['data']['nodes']) == 2  # 用户问题节点 + AI分析节点
        assert len(data['data']['edges']) == 1

    def test_create_case_empty_query(self, client, auth_headers):
        """测试创建案例时查询为空"""
        response = client.post('/api/v1/cases',
                             headers=auth_headers,
                             json={'query': ''})

        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'

    def test_get_cases_list(self, client, auth_headers, test_case):
        """测试获取案例列表"""
        response = client.get('/api/v1/cases', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'items' in data['data']
        assert data['data']['total'] >= 1

    def test_get_cases_with_pagination(self, client, auth_headers):
        """测试分页获取案例"""
        response = client.get('/api/v1/cases?page=1&pageSize=5',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['page'] == 1
        assert data['data']['pageSize'] == 5

    def test_get_cases_with_status_filter(self, client, auth_headers, test_case):
        """测试按状态过滤案例"""
        response = client.get('/api/v1/cases?status=open',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_get_case_detail(self, client, auth_headers, test_case):
        """测试获取案例详情"""
        response = client.get(f'/api/v1/cases/{test_case.id}',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['caseId'] == test_case.id

    def test_get_case_detail_not_found(self, client, auth_headers):
        """测试获取不存在的案例"""
        response = client.get('/api/v1/cases/nonexistent-id',
                            headers=auth_headers)

        assert response.status_code == 404

    def test_update_case(self, client, auth_headers, test_case):
        """测试更新案例"""
        response = client.put(f'/api/v1/cases/{test_case.id}',
                            headers=auth_headers,
                            json={
                                'title': '更新后的标题',
                                'status': 'solved'
                            })

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['title'] == '更新后的标题'
        assert data['data']['status'] == 'solved'

    def test_delete_case(self, client, auth_headers, test_case):
        """测试删除案例"""
        response = client.delete(f'/api/v1/cases/{test_case.id}',
                               headers=auth_headers)

        assert response.status_code == 204

        # 验证案例已删除
        response = client.get(f'/api/v1/cases/{test_case.id}',
                            headers=auth_headers)
        assert response.status_code == 404

    def test_handle_interaction(self, client, auth_headers, test_case):
        """测试处理交互"""
        # 先创建一个节点作为父节点
        node = Node(
            case_id=test_case.id,
            type='AI_ANALYSIS',
            title='AI分析',
            status='COMPLETED'
        )
        db.session.add(node)
        db.session.commit()

        response = client.post(f'/api/v1/cases/{test_case.id}/interactions',
                             headers=auth_headers,
                             json={
                                 'parentNodeId': node.id,
                                 'response': {
                                     'type': 'answers',
                                     'answers': {
                                         '设备型号': 'Router-X1000',
                                         '问题时间': '今天早上'
                                     }
                                 },
                                 'retrievalWeight': 0.8,
                                 'filterTags': ['network', 'router']
                             })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']['newNodes']) == 2
        assert len(data['data']['newEdges']) == 2

    def test_get_node_detail(self, client, auth_headers, test_case):
        """测试获取节点详情"""
        # 创建一个节点
        node = Node(
            case_id=test_case.id,
            type='USER_QUERY',
            title='用户问题',
            status='COMPLETED',
            content={'text': '测试问题'}
        )
        db.session.add(node)
        db.session.commit()

        response = client.get(f'/api/v1/cases/{test_case.id}/nodes/{node.id}',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['id'] == node.id
        assert data['data']['type'] == 'USER_QUERY'

    def test_submit_feedback(self, client, auth_headers, test_case):
        """测试提交反馈"""
        response = client.post(f'/api/v1/cases/{test_case.id}/feedback',
                             headers=auth_headers,
                             json={
                                 'outcome': 'solved',
                                 'rating': 5,
                                 'comment': '解决方案很有效',
                                 'corrected_solution': {
                                     'steps': ['步骤1', '步骤2']
                                 }
                             })

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

        # 验证案例状态已更新
        updated_case = Case.query.get(test_case.id)
        assert updated_case.status == 'solved'

    def test_get_feedback(self, client, auth_headers, test_case):
        """测试获取反馈"""
        # 先创建反馈
        feedback = Feedback(
            case_id=test_case.id,
            user_id=1,  # 从auth_headers中的用户
            outcome='solved',
            rating=4,
            comment='不错的解决方案'
        )
        db.session.add(feedback)
        db.session.commit()

        response = client.get(f'/api/v1/cases/{test_case.id}/feedback',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['outcome'] == 'solved'
        assert data['data']['rating'] == 4

    def test_update_feedback(self, client, auth_headers, test_case):
        """测试更新反馈"""
        # 先创建反馈
        feedback = Feedback(
            case_id=test_case.id,
            user_id=1,
            outcome='unsolved',
            rating=2
        )
        db.session.add(feedback)
        db.session.commit()

        response = client.put(f'/api/v1/cases/{test_case.id}/feedback',
                            headers=auth_headers,
                            json={
                                'outcome': 'solved',
                                'rating': 5,
                                'comment': '最终解决了问题'
                            })

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['outcome'] == 'solved'
        assert data['data']['rating'] == 5

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get('/api/v1/cases')
        assert response.status_code == 422  # JWT missing

        response = client.post('/api/v1/cases', json={'query': 'test'})
        assert response.status_code == 422

    def test_access_other_user_case(self, client, auth_headers):
        """测试访问其他用户的案例"""
        # 创建另一个用户的案例
        from app.models.user import User
        other_user = User(username='other', email='other@example.com')
        other_user.set_password('pass')
        db.session.add(other_user)
        db.session.flush()

        other_case = Case(title='其他用户案例', user_id=other_user.id)
        db.session.add(other_case)
        db.session.commit()

        # 尝试访问
        response = client.get(f'/api/v1/cases/{other_case.id}',
                            headers=auth_headers)
        assert response.status_code == 404
