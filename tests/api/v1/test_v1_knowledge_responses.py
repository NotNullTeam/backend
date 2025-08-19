"""
API v1 知识库模块响应测试

测试知识库相关 API 的响应格式和状态码。
"""

import pytest
import json
import io
from app import db
from app.models.knowledge import KnowledgeDocument


class TestKnowledgeAPIResponses:
    """知识库 API 响应测试类"""

    def test_upload_document_success_response(self, client, auth_headers):
        """测试文档上传成功响应格式"""
        # 创建模拟文件
        file_data = io.BytesIO(b'Test document content')
        file_data.name = 'test.txt'

        response = client.post('/api/v1/knowledge/documents',
                              data={
                                  'file': (file_data, 'test.txt'),
                                  'category': 'general'
                              },
                              content_type='multipart/form-data',
                              headers=auth_headers)

        if response.status_code == 201:
            data = response.get_json()

            assert data['code'] == 201
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'document' in data['data']

            doc_data = data['data']['document']
            assert 'id' in doc_data
            assert 'filename' in doc_data
            assert 'category' in doc_data
            assert 'upload_time' in doc_data
            assert 'file_size' in doc_data

    def test_get_documents_list_response(self, client, auth_headers):
        """测试获取文档列表响应格式"""
        response = client.get('/api/v1/knowledge/documents', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'documents' in data['data']
        assert 'pagination' in data['data']

        # 检查分页信息
        pagination = data['data']['pagination']
        assert 'page' in pagination
        assert 'per_page' in pagination
        assert 'total' in pagination
        assert 'pages' in pagination

    def test_get_document_detail_response(self, client, auth_headers):
        """测试获取文档详情响应格式"""
        # 假设文档ID为1
        response = client.get('/api/v1/knowledge/documents/1', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'document' in data['data']

            doc_data = data['data']['document']
            assert 'id' in doc_data
            assert 'filename' in doc_data
            assert 'content' in doc_data
            assert 'metadata' in doc_data

    def test_search_knowledge_response(self, client, auth_headers):
        """测试知识搜索响应格式"""
        response = client.post('/api/v1/knowledge/search',
                              json={
                                  'query': '网络配置',
                                  'limit': 10
                              },
                              headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'results' in data['data']
            assert 'query' in data['data']
            assert 'total' in data['data']

            # 检查搜索结果结构
            if data['data']['results']:
                result = data['data']['results'][0]
                assert 'id' in result
                assert 'title' in result
                assert 'content' in result
                assert 'score' in result
                assert 'metadata' in result

    def test_semantic_search_response(self, client, auth_headers):
        """测试语义搜索响应格式"""
        response = client.post('/api/v1/knowledge/semantic-search',
                              json={
                                  'query': 'OSPF路由协议配置',
                                  'top_k': 5
                              },
                              headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'results' in data['data']
            assert 'embeddings_used' in data['data']

            # 检查语义搜索结果
            if data['data']['results']:
                result = data['data']['results'][0]
                assert 'document_id' in result
                assert 'content' in result
                assert 'similarity_score' in result
                assert 0 <= result['similarity_score'] <= 1

    def test_delete_document_response(self, client, auth_headers):
        """测试删除文档响应格式"""
        response = client.delete('/api/v1/knowledge/documents/1', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert data['message'] == '文档删除成功'

    def test_parse_document_response(self, client, auth_headers):
        """测试文档解析响应格式"""
        response = client.post('/api/v1/knowledge/parse/1', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'job_id' in data['data']
            assert 'status' in data['data']

    def test_get_parse_status_response(self, client, auth_headers):
        """测试获取解析状态响应格式"""
        response = client.get('/api/v1/knowledge/parse-status/job123', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'job_status' in data['data']
            assert 'progress' in data['data']

            # 检查作业状态值
            job_status = data['data']['job_status']
            assert job_status in ['pending', 'processing', 'completed', 'failed']

    def test_get_categories_response(self, client, auth_headers):
        """测试获取分类列表响应格式"""
        response = client.get('/api/v1/knowledge/categories', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'categories' in data['data']

            # 检查分类结构
            if data['data']['categories']:
                category = data['data']['categories'][0]
                assert 'name' in category
                assert 'count' in category

    def test_create_embedding_response(self, client, auth_headers):
        """测试创建嵌入向量响应格式"""
        response = client.post('/api/v1/knowledge/embeddings',
                              json={
                                  'document_id': 1,
                                  'text_chunks': ['chunk1', 'chunk2']
                              },
                              headers=auth_headers)

        if response.status_code == 201:
            data = response.get_json()

            assert data['code'] == 201
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'embeddings_created' in data['data']
            assert 'vector_count' in data['data']

    def test_invalid_file_upload_response(self, client, auth_headers):
        """测试无效文件上传响应格式"""
        # 尝试上传空文件
        response = client.post('/api/v1/knowledge/documents',
                              data={},
                              content_type='multipart/form-data',
                              headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()

        assert data['code'] == 400
        assert data['status'] == 'error'
        assert data['error']['type'] == 'INVALID_REQUEST'

    def test_unsupported_file_type_response(self, client, auth_headers):
        """测试不支持的文件类型响应格式"""
        file_data = io.BytesIO(b'binary data')
        file_data.name = 'test.exe'

        response = client.post('/api/v1/knowledge/documents',
                              data={
                                  'file': (file_data, 'test.exe'),
                                  'category': 'general'
                              },
                              content_type='multipart/form-data',
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()

            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'UNSUPPORTED_FILE_TYPE'

    def test_document_not_found_response(self, client, auth_headers):
        """测试文档不存在响应格式"""
        response = client.get('/api/v1/knowledge/documents/99999', headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()

        assert data['code'] == 404
        assert data['status'] == 'error'
        assert data['error']['type'] == 'NOT_FOUND'

    def test_search_empty_query_response(self, client, auth_headers):
        """测试空查询搜索响应格式"""
        response = client.post('/api/v1/knowledge/search',
                              json={'query': ''},
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()

            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'INVALID_REQUEST'

    def test_large_file_upload_response(self, client, auth_headers):
        """测试大文件上传响应格式"""
        # 创建模拟大文件（超过限制）
        large_data = b'x' * (20 * 1024 * 1024)  # 20MB
        file_data = io.BytesIO(large_data)
        file_data.name = 'large_file.txt'

        response = client.post('/api/v1/knowledge/documents',
                              data={
                                  'file': (file_data, 'large_file.txt'),
                                  'category': 'general'
                              },
                              content_type='multipart/form-data',
                              headers=auth_headers)

        if response.status_code == 413:
            data = response.get_json()

            assert data['code'] == 413
            assert data['status'] == 'error'
            assert data['error']['type'] == 'FILE_TOO_LARGE'

    def test_concurrent_parse_jobs_response(self, client, auth_headers):
        """测试并发解析作业响应格式"""
        response = client.get('/api/v1/knowledge/parse-jobs', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'jobs' in data['data']
            assert 'active_count' in data['data']
            assert 'pending_count' in data['data']

    def test_knowledge_statistics_response(self, client, auth_headers):
        """测试知识库统计响应格式"""
        response = client.get('/api/v1/knowledge/statistics', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data
            assert 'total_documents' in data['data']
            assert 'total_size' in data['data']
            assert 'categories_count' in data['data']
            assert 'embeddings_count' in data['data']

    def test_export_knowledge_response(self, client, auth_headers):
        """测试导出知识库响应格式"""
        response = client.get('/api/v1/knowledge/export?format=json', headers=auth_headers)

        if response.status_code == 200:
            # 可能是JSON或文件下载
            if response.content_type == 'application/json':
                data = response.get_json()
                assert data['code'] == 200
                assert data['status'] == 'success'
            else:
                # 文件下载
                assert len(response.data) > 0
                assert 'attachment' in response.headers.get('Content-Disposition', '')

    def test_unauthorized_knowledge_access(self, client):
        """测试未授权访问知识库响应格式"""
        response = client.get('/api/v1/knowledge/documents')

        assert response.status_code == 401
        data = response.get_json()

        assert data['code'] == 401
        assert data['status'] == 'error'
        assert data['error']['type'] == 'UNAUTHORIZED'

    def test_reparse_document_response(self, client, auth_headers):
        """测试重新解析文档响应格式"""
        # 假设文档ID为1
        response = client.post('/api/v1/knowledge/documents/1/reparse', headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            reparse_data = data['data']
            assert 'docId' in reparse_data
            assert 'status' in reparse_data
            assert 'message' in reparse_data
            assert reparse_data['status'] == 'QUEUED'

        elif response.status_code == 404:
            data = response.get_json()
            assert data['code'] == 404
            assert data['status'] == 'error'
            assert data['error']['type'] == 'NOT_FOUND'

    def test_update_document_metadata_response(self, client, auth_headers):
        """测试更新文档元数据响应格式"""
        # 假设文档ID为1
        response = client.patch('/api/v1/knowledge/documents/1',
                               json={
                                   'tags': ['OSPF', 'BGP'],
                                   'vendor': 'Huawei'
                               },
                               headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'message' in data

        elif response.status_code == 404:
            data = response.get_json()
            assert data['code'] == 404
            assert data['status'] == 'error'
            assert data['error']['type'] == 'NOT_FOUND'

    def test_update_document_metadata_invalid_data(self, client, auth_headers):
        """测试使用无效数据更新文档元数据"""
        # 假设文档ID为1
        response = client.patch('/api/v1/knowledge/documents/1',
                               json={
                                   'tags': 'invalid_format',  # 应该是数组
                               },
                               headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()
            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'INVALID_REQUEST'
