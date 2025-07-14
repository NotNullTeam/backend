"""
IP智慧解答专家系统 - 多轮交互API测试

本模块测试多轮交互相关的API接口。
"""

import pytest
import json
from app.models.case import Case, Node, Edge


@pytest.mark.api
@pytest.mark.interactions
class TestInteractionsAPI:
    """测试多轮交互API"""

    def test_handle_interaction_success(self, client, auth_headers, sample_case, sample_node, database):
        """测试成功处理交互"""
        interaction_data = {
            'parentNodeId': sample_node.id,
            'response': {
                'text': '网络拓扑是星型结构，使用华为交换机',
                'additionalInfo': '问题出现在早上9点左右'
            },
            'retrievalWeight': 0.8,
            'filterTags': ['华为', '交换机']
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/interactions',
                             json=interaction_data,
                             headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert len(data['data']['newNodes']) == 2  # 用户响应节点 + AI处理节点
        assert len(data['data']['newEdges']) == 2
        assert 'processingNodeId' in data['data']

    def test_handle_interaction_missing_parent_node(self, client, auth_headers, sample_case):
        """测试缺少父节点ID的交互"""
        interaction_data = {
            'response': {
                'text': '补充信息'
            }
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/interactions',
                             json=interaction_data,
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '父节点ID不能为空' in data['error']['message']

    def test_handle_interaction_missing_response(self, client, auth_headers, sample_case, sample_node):
        """测试缺少响应数据的交互"""
        interaction_data = {
            'parentNodeId': sample_node.id
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/interactions',
                             json=interaction_data,
                             headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '响应数据不能为空' in data['error']['message']

    def test_handle_interaction_invalid_parent_node(self, client, auth_headers, sample_case):
        """测试无效的父节点ID"""
        interaction_data = {
            'parentNodeId': 'invalid-node-id',
            'response': {
                'text': '补充信息'
            }
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/interactions',
                             json=interaction_data,
                             headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '父节点不存在' in data['error']['message']

    def test_handle_interaction_case_not_found(self, client, auth_headers, sample_node):
        """测试案例不存在的交互"""
        fake_case_id = 'non-existent-case-id'
        interaction_data = {
            'parentNodeId': sample_node.id,
            'response': {
                'text': '补充信息'
            }
        }

        response = client.post(f'/api/v1/cases/{fake_case_id}/interactions',
                             json=interaction_data,
                             headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '案例不存在' in data['error']['message']

    def test_handle_interaction_unauthorized(self, client, sample_case, sample_node):
        """测试未授权的交互"""
        interaction_data = {
            'parentNodeId': sample_node.id,
            'response': {
                'text': '补充信息'
            }
        }

        response = client.post(f'/api/v1/cases/{sample_case.id}/interactions',
                             json=interaction_data)

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.interactions
class TestNodeDetailAPI:
    """测试节点详情API"""

    def test_get_node_detail_success(self, client, auth_headers, sample_case, sample_node):
        """测试成功获取节点详情"""
        response = client.get(f'/api/v1/cases/{sample_case.id}/nodes/{sample_node.id}',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['id'] == sample_node.id
        assert data['data']['type'] == sample_node.type
        assert data['data']['title'] == sample_node.title
        assert data['data']['status'] == sample_node.status

    def test_get_node_detail_not_found(self, client, auth_headers, sample_case):
        """测试获取不存在的节点详情"""
        fake_node_id = 'non-existent-node-id'
        response = client.get(f'/api/v1/cases/{sample_case.id}/nodes/{fake_node_id}',
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '节点不存在' in data['error']['message']

    def test_get_node_detail_case_not_found(self, client, auth_headers, sample_node):
        """测试案例不存在时获取节点详情"""
        fake_case_id = 'non-existent-case-id'
        response = client.get(f'/api/v1/cases/{fake_case_id}/nodes/{sample_node.id}',
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert '案例不存在' in data['error']['message']

    def test_get_node_detail_unauthorized(self, client, sample_case, sample_node):
        """测试未授权获取节点详情"""
        response = client.get(f'/api/v1/cases/{sample_case.id}/nodes/{sample_node.id}')

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.interactions
class TestNodeUpdateAPI:
    """测试节点更新API"""

    def test_update_node_success(self, client, auth_headers, sample_case, sample_node):
        """测试成功更新节点"""
        update_data = {
            'title': '更新后的节点标题',
            'status': 'COMPLETED',
            'content': {
                'answer': '这是更新后的答案',
                'steps': ['步骤1', '步骤2']
            },
            'metadata': {
                'updated_by': 'test_user'
            }
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/nodes/{sample_node.id}',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert data['data']['title'] == update_data['title']
        assert data['data']['status'] == update_data['status']
        assert data['data']['content'] == update_data['content']

    def test_update_node_invalid_status(self, client, auth_headers, sample_case, sample_node):
        """测试更新节点为无效状态"""
        update_data = {
            'status': 'INVALID_STATUS'
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/nodes/{sample_node.id}',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert '无效的节点状态' in data['error']['message']

    def test_update_node_not_found(self, client, auth_headers, sample_case):
        """测试更新不存在的节点"""
        fake_node_id = 'non-existent-node-id'
        update_data = {
            'title': '更新后的标题'
        }

        response = client.put(f'/api/v1/cases/{sample_case.id}/nodes/{fake_node_id}',
                            json=update_data,
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'


@pytest.mark.api
@pytest.mark.interactions
class TestCaseStatusAPI:
    """测试案例状态API"""

    def test_get_case_status_success(self, client, auth_headers, sample_case, database):
        """测试成功获取案例状态"""
        # 创建一个处理中的节点
        processing_node = Node(
            case_id=sample_case.id,
            type='AI_ANALYSIS',
            title='AI分析中...',
            status='PROCESSING'
        )
        database.session.add(processing_node)
        database.session.commit()

        response = client.get(f'/api/v1/cases/{sample_case.id}/status',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'processingNodes' in data['data']
        assert 'awaitingNodes' in data['data']
        assert len(data['data']['processingNodes']) >= 1

    def test_get_case_status_not_found(self, client, auth_headers):
        """测试获取不存在案例的状态"""
        fake_case_id = 'non-existent-case-id'
        response = client.get(f'/api/v1/cases/{fake_case_id}/status',
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'

    def test_get_case_status_unauthorized(self, client, sample_case):
        """测试未授权获取案例状态"""
        response = client.get(f'/api/v1/cases/{sample_case.id}/status')

        assert response.status_code == 401
