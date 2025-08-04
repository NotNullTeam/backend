"""
API v1 案例模块响应测试

测试案例管理相关 API 的响应格式和状态码。
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from app import db
from app.models.case import Case, Node, Edge
from app.services.ai.agent_service import analyze_user_query
from app.models.user import User
from flask import current_app


class TestCasesAPIResponses:
    """案例 API 响应测试类"""

    def test_create_case_success_response(self, client, auth_headers):
        """测试创建案例成功响应格式"""
        response = client.post('/api/v1/cases/',
                              json={'query': '我的网络连接有问题'},
                              headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        # 检查响应结构
        assert 'code' in data
        assert 'status' in data
        assert 'data' in data

        assert data['code'] == 200
        assert data['status'] == 'success'

        # 检查案例数据
        case_data = data['data']
        assert 'caseId' in case_data
        assert 'title' in case_data
        assert 'createdAt' in case_data
        # 后端会根据query生成一个title
        assert '网络连接' in case_data['title']

    def test_get_cases_list_response(self, client, auth_headers, test_case):
        """测试获取案例列表响应格式"""
        response = client.get('/api/v1/cases/', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'items' in data['data']
        assert 'pagination' in data['data']

        # 检查分页信息
        pagination = data['data']['pagination']
        assert 'page' in pagination
        assert 'per_page' in pagination
        assert 'total' in pagination
        assert 'pages' in pagination

    def test_get_case_detail_response(self, client, auth_headers, test_case):
        """测试获取案例详情响应格式"""
        case_id = test_case.id
        response = client.get(f'/api/v1/cases/{case_id}', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'case' in data['data']

            case_data = data['data']['case']
            assert 'id' in case_data
            assert 'title' in case_data
            assert 'user_id' in case_data
            assert 'created_at' in case_data
            assert 'updated_at' in case_data

    def test_get_nonexistent_case_response(self, client, auth_headers):
        """测试获取不存在案例的响应格式"""
        response = client.get('/api/v1/cases/99999', headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert 'error' in data
        assert data['error']['type'] == 'NOT_FOUND'

    def test_update_case_success_response(self, client, auth_headers, test_case):
        """测试更新案例成功响应格式"""
        case_id = test_case.id
        response = client.put(f'/api/v1/cases/{case_id}',
                             json={'title': '更新后的案例'},
                             headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'case' in data['data']
            assert data['data']['case']['title'] == '更新后的案例'

    def test_delete_case_success_response(self, client, auth_headers, test_case):
        """测试删除案例成功响应格式"""
        case_id = test_case.id
        response = client.delete(f'/api/v1/cases/{case_id}', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert data['message'] == '案例删除成功'

    def test_unauthorized_access_response(self, client):
        """测试未授权访问响应格式"""
        response = client.get('/api/v1/cases/')

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_invalid_case_data_response(self, client, auth_headers):
        """测试无效案例数据响应格式"""
        response = client.post('/api/v1/cases/',
                              json={},  # 空数据
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()

            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'INVALID_REQUEST'

    def test_case_interaction_response(self, client, auth_headers, test_case):
        """测试案例交互响应格式"""
        case_id = test_case.id
        response = client.post(f'/api/v1/cases/{case_id}/interact',
                              json={
                                  'message': '这是一个测试问题',
                                  'type': 'question'
                              },
                              headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            # 检查交互响应数据
            if 'interaction' in data['data']:
                interaction = data['data']['interaction']
                assert 'id' in interaction
                assert 'message' in interaction
                assert 'response' in interaction
                assert 'timestamp' in interaction

    @patch('app.services.get_task_queue')
    @patch('app.services.ai.agent_service.analyze_user_query')
    def test_case_nodes_response(self, mock_analyze_user_query, mock_get_task_queue, client, auth_headers):
        """测试获取案例节点响应格式"""
        # 配置模拟队列
        mock_queue = MagicMock()
        mock_get_task_queue.return_value = mock_queue

        # 配置模拟分析函数
        def mock_analysis(case_id, node_id, query):
            # 手动创建测试所需的节点和边
            ai_node = Node.query.get(node_id)
            if ai_node:
                ai_node.status = 'COMPLETED'
                ai_node.title = 'AI分析结果'
                ai_node.content = {'analysis': '网络连接问题分析结果'}
                
                # 创建新的解决方案节点
                solution_node = Node(
                    case_id=case_id,
                    type='SOLUTION',
                    title='解决方案',
                    status='COMPLETED',
                    content={'solution': '检查网络连接和配置'}
                )
                db.session.add(solution_node)
                db.session.flush()
                
                # 创建边
                edge = Edge(
                    case_id=case_id,
                    source=node_id,
                    target=solution_node.id
                )
                db.session.add(edge)
                db.session.commit()
        
        mock_analyze_user_query.side_effect = mock_analysis

        # 1. 通过API创建案例
        create_response = client.post('/api/v1/cases/', json={'query': '网络连接失败如何排查？'}, headers=auth_headers)
        assert create_response.status_code == 200
        response_data = create_response.get_json()['data']
        case_id = response_data['caseId']
        ai_node_id = next(node['id'] for node in response_data['nodes'] if node['type'] == 'AI_ANALYSIS')

        # 2. 执行模拟的分析任务
        mock_analysis(case_id, ai_node_id, '网络连接失败如何排查？')

        # 3. 获取节点
        response = client.get(f'/api/v1/cases/{case_id}/nodes', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'nodes' in data['data']
        assert len(data['data']['nodes']) > 0  # 确保至少有一个节点

        # 检查节点数据结构
        node = data['data']['nodes'][0]
        assert 'id' in node
        assert 'type' in node
        assert 'content' in node

    @patch('app.services.get_task_queue')
    @patch('app.services.ai.agent_service.analyze_user_query')
    def test_case_edges_response(self, mock_analyze_user_query, mock_get_task_queue, client, auth_headers):
        """测试获取案例边响应格式"""
        # 配置模拟队列
        mock_queue = MagicMock()
        mock_get_task_queue.return_value = mock_queue

        # 配置模拟分析函数
        def mock_analysis(case_id, node_id, query):
            # 手动创建测试所需的节点和边
            ai_node = Node.query.get(node_id)
            if ai_node:
                ai_node.status = 'COMPLETED'
                ai_node.title = 'AI分析结果'
                ai_node.content = {'analysis': 'ping命令分析结果'}
                
                # 创建新的解决方案节点
                solution_node = Node(
                    case_id=case_id,
                    type='SOLUTION',
                    title='解决方案',
                    status='COMPLETED',
                    content={'solution': '使用ping命令测试网络连接'}
                )
                db.session.add(solution_node)
                db.session.flush()
                
                # 创建边
                edge = Edge(
                    case_id=case_id,
                    source=node_id,
                    target=solution_node.id
                )
                db.session.add(edge)
                db.session.commit()
        
        mock_analyze_user_query.side_effect = mock_analysis

        # 1. 通过API创建案例
        create_response = client.post('/api/v1/cases/', json={'query': '如何ping一个IP地址？'}, headers=auth_headers)
        assert create_response.status_code == 200
        response_data = create_response.get_json()['data']
        case_id = response_data['caseId']
        ai_node_id = next(node['id'] for node in response_data['nodes'] if node['type'] == 'AI_ANALYSIS')

        # 2. 执行模拟的分析任务
        mock_analysis(case_id, ai_node_id, '如何ping一个IP地址？')

        # 3. 获取边
        response = client.get(f'/api/v1/cases/{case_id}/edges', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'edges' in data['data']
        assert len(data['data']['edges']) > 0  # 确保至少有一个边

    def test_search_cases_response(self, client, auth_headers):
        """测试搜索案例响应格式"""
        response = client.get('/api/v1/cases/search?q=测试', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'items' in data['data']
            assert 'query' in data['data']
            assert 'total' in data['data']

    def test_case_export_response(self, client, auth_headers, test_case):
        """测试导出案例响应格式"""
        case_id = test_case.id
        response = client.get(f'/api/v1/cases/{case_id}/export', headers=auth_headers)

        # 可能返回 JSON 或文件
        if response.status_code == 200:
            if response.content_type == 'application/json':
                data = response.get_json()
                assert data['code'] == 200
                assert data['status'] == 'success'
            else:
                # 文件下载响应
                assert len(response.data) > 0

    def test_batch_operation_response(self, client, auth_headers):
        """测试批量操作响应格式"""
        response = client.post('/api/v1/cases/batch',
                              json={
                                  'action': 'delete',
                                  'case_ids': [1, 2, 3]
                              },
                              headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'results' in data['data']

    def test_response_time_reasonable(self, client, auth_headers):
        """测试响应时间合理性"""
        import time

        start_time = time.time()
        response = client.get('/api/v1/cases/', headers=auth_headers)
        end_time = time.time()

        response_time = end_time - start_time

        # 响应时间应该在合理范围内（< 5秒）
        assert response_time < 5.0

    def test_large_case_list_response(self, client, auth_headers):
        """测试大量案例列表响应格式"""
        # 测试分页参数
        response = client.get('/api/v1/cases/?page=1&per_page=50', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'

        # 检查分页限制
        pagination = data['data']['pagination']
        assert pagination['per_page'] <= 100  # 假设最大限制为100

    def test_case_validation_error_response(self, client, auth_headers):
        """测试案例验证错误响应格式"""
        # 提供过长的标题
        long_title = 'x' * 1000
        response = client.post('/api/v1/cases/',
                              json={
                                  'query': '测试查询问题',
                                  'title': long_title
                              },
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()

            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'VALIDATION_ERROR'
            assert 'details' in data['error']

    @patch('app.services.get_task_queue')
    @patch('app.services.ai.agent_service.analyze_user_query')
    def test_get_node_detail_success_response(self, mock_analyze_user_query, mock_get_task_queue, client, auth_headers):
        """测试获取案例节点详情成功响应格式"""
        # 配置模拟队列
        mock_queue = MagicMock()
        mock_get_task_queue.return_value = mock_queue

        # 配置模拟分析函数
        def mock_analysis(case_id, node_id, query):
            # 手动创建测试所需的节点和边
            ai_node = Node.query.get(node_id)
            if ai_node:
                ai_node.status = 'COMPLETED'
                ai_node.title = 'AI分析结果'
                ai_node.content = {'analysis': 'DNS解析问题分析结果'}
                
                # 创建新的解决方案节点
                solution_node = Node(
                    case_id=case_id,
                    type='SOLUTION',
                    title='解决方案',
                    status='COMPLETED',
                    content={'solution': '检查DNS设置和网络配置'}
                )
                db.session.add(solution_node)
                db.session.flush()
                
                # 创建边
                edge = Edge(
                    case_id=case_id,
                    source=node_id,
                    target=solution_node.id
                )
                db.session.add(edge)
                db.session.commit()
        
        mock_analyze_user_query.side_effect = mock_analysis

        # 1. 通过API创建案例
        create_response = client.post('/api/v1/cases/', json={'query': 'DNS无法解析怎么办？'}, headers=auth_headers)
        assert create_response.status_code == 200
        response_data = create_response.get_json()['data']
        case_id = response_data['caseId']
        ai_node_id = next(node['id'] for node in response_data['nodes'] if node['type'] == 'AI_ANALYSIS')

        # 2. 执行模拟的分析任务
        mock_analysis(case_id, ai_node_id, 'DNS无法解析怎么办？')

        # 3. 获取节点列表以获得一个有效的 node_id
        nodes_response = client.get(f'/api/v1/cases/{case_id}/nodes', headers=auth_headers)
        assert nodes_response.status_code == 200
        nodes_data = nodes_response.get_json()
        assert len(nodes_data['data']['nodes']) > 0
        # 选择一个非用户查询的节点进行详情测试
        target_node = next((n for n in nodes_data['data']['nodes'] if n['type'] != 'USER_QUERY'), None)
        assert target_node is not None, "No non-user-query node found to test detail view"
        node_id = target_node['id']

        # 4. 测试获取节点详情
        response = client.get(f'/api/v1/cases/{case_id}/nodes/{node_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        node_data = data['data']
        assert node_data['id'] == node_id
        assert 'type' in node_data
        assert 'content' in node_data

    def test_get_case_status_success_response(self, client, auth_headers, test_case):
        """测试获取案例状态成功响应格式"""
        case_id = test_case.id
        response = client.get(f'/api/v1/cases/{case_id}/status', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'caseStatus' in data['data']
        assert data['data']['caseStatus'] in ['PROCESSING', 'DONE', 'ERROR', 'open']
