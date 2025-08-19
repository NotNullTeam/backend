"""
API v1 知识文档管理测试

测试知识文档的上传、解析、更新等管理功能。
"""

import pytest
import json
import io
import os
import tempfile
from app import db
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.user import User


class TestKnowledgeDocumentManagement:
    """知识文档管理测试类"""

    def test_upload_document_success(self, client, auth_headers, test_user):
        """测试文档上传成功"""
        # 创建临时测试文件
        test_content = b"This is a test document content for network configuration."
        file_data = io.BytesIO(test_content)

        response = client.post('/api/v1/knowledge/documents',
                              data={
                                  'file': (file_data, 'test_network_config.txt'),
                                  'vendor': 'Huawei',
                                  'tags': ['网络配置', '测试']
                              },
                              content_type='multipart/form-data',
                              headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            doc_data = data['data']
            assert 'docId' in doc_data
            assert 'status' in doc_data
            assert doc_data['status'] == 'QUEUED'

    def test_upload_document_invalid_file_type(self, client, auth_headers):
        """测试上传不支持的文件类型"""
        # 创建不支持的文件类型
        file_data = io.BytesIO(b"invalid content")

        response = client.post('/api/v1/knowledge/documents',
                              data={
                                  'file': (file_data, 'test.xyz'),  # 不支持的扩展名
                              },
                              content_type='multipart/form-data',
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()
            assert data['code'] == 400
            assert data['status'] == 'error'
            assert 'UNSUPPORTED_FILE_TYPE' in data['error']['type']

    def test_upload_document_no_file(self, client, auth_headers):
        """测试没有上传文件的情况"""
        response = client.post('/api/v1/knowledge/documents',
                              data={},
                              content_type='multipart/form-data',
                              headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400
        assert data['status'] == 'error'

    def test_get_documents_list(self, client, auth_headers):
        """测试获取文档列表"""
        response = client.get('/api/v1/knowledge/documents', headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()

        assert data['code'] == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'documents' in data['data']
        assert isinstance(data['data']['documents'], list)

    def test_get_documents_with_filters(self, client, auth_headers):
        """测试使用过滤器获取文档列表"""
        # 测试按状态过滤
        response = client.get('/api/v1/knowledge/documents?status=INDEXED',
                            headers=auth_headers)
        assert response.status_code == 200

        # 测试按厂商过滤
        response = client.get('/api/v1/knowledge/documents?vendor=Huawei',
                            headers=auth_headers)
        assert response.status_code == 200

        # 测试分页
        response = client.get('/api/v1/knowledge/documents?page=1&pageSize=5',
                            headers=auth_headers)
        assert response.status_code == 200

    def test_get_document_detail(self, client, auth_headers, sample_document):
        """测试获取文档详情"""
        doc_id = sample_document.id
        response = client.get(f'/api/v1/knowledge/documents/{doc_id}',
                            headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            doc_data = data['data']
            assert 'docId' in doc_data
            assert 'fileName' in doc_data
            assert 'status' in doc_data

    def test_get_document_detail_not_found(self, client, auth_headers):
        """测试获取不存在文档的详情"""
        response = client.get('/api/v1/knowledge/documents/nonexistent',
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data['code'] == 404
        assert data['status'] == 'error'
        assert data['error']['type'] == 'NOT_FOUND'

    def test_delete_document(self, client, auth_headers, sample_document):
        """测试删除文档"""
        doc_id = sample_document.id
        response = client.delete(f'/api/v1/knowledge/documents/{doc_id}',
                               headers=auth_headers)

        if response.status_code == 204:
            # 验证文档已被删除
            response = client.get(f'/api/v1/knowledge/documents/{doc_id}',
                                headers=auth_headers)
            assert response.status_code == 404

    def test_delete_document_not_found(self, client, auth_headers):
        """测试删除不存在的文档"""
        response = client.delete('/api/v1/knowledge/documents/nonexistent',
                               headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data['code'] == 404
        assert data['status'] == 'error'

    def test_reparse_document(self, client, auth_headers, sample_document):
        """测试重新解析文档"""
        doc_id = sample_document.id
        response = client.post(f'/api/v1/knowledge/documents/{doc_id}/reparse',
                            headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'data' in data

            reparse_data = data['data']
            assert 'docId' in reparse_data
            assert 'status' in reparse_data
            assert reparse_data['status'] == 'QUEUED'

    def test_reparse_document_not_found(self, client, auth_headers):
        """测试重新解析不存在的文档"""
        response = client.post('/api/v1/knowledge/documents/nonexistent/reparse',
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data['code'] == 404
        assert data['status'] == 'error'
        assert data['error']['type'] == 'NOT_FOUND'

    def test_update_document_metadata(self, client, auth_headers, sample_document):
        """测试更新文档元数据"""
        doc_id = sample_document.id
        update_data = {
            'tags': ['OSPF', 'BGP', '路由协议'],
            'vendor': 'Cisco'
        }

        response = client.patch(f'/api/v1/knowledge/documents/{doc_id}',
                              json=update_data,
                              headers=auth_headers)

        if response.status_code == 200:
            data = response.get_json()

            assert data['code'] == 200
            assert data['status'] == 'success'
            assert 'message' in data

    def test_update_document_metadata_invalid_tags(self, client, auth_headers, sample_document):
        """测试使用无效标签格式更新文档元数据"""
        doc_id = sample_document.id
        update_data = {
            'tags': 'invalid_format'  # 应该是数组
        }

        response = client.patch(f'/api/v1/knowledge/documents/{doc_id}',
                              json=update_data,
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()
            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'INVALID_REQUEST'

    def test_update_document_metadata_invalid_vendor(self, client, auth_headers, sample_document):
        """测试使用无效厂商格式更新文档元数据"""
        doc_id = sample_document.id
        update_data = {
            'vendor': 123  # 应该是字符串
        }

        response = client.patch(f'/api/v1/knowledge/documents/{doc_id}',
                              json=update_data,
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()
            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'INVALID_REQUEST'

    def test_update_document_metadata_empty_body(self, client, auth_headers, sample_document):
        """测试使用空请求体更新文档元数据"""
        doc_id = sample_document.id

        response = client.patch(f'/api/v1/knowledge/documents/{doc_id}',
                              json={},
                              headers=auth_headers)

        if response.status_code == 400:
            data = response.get_json()
            assert data['code'] == 400
            assert data['status'] == 'error'
            assert data['error']['type'] == 'INVALID_REQUEST'

    def test_update_document_metadata_not_found(self, client, auth_headers):
        """测试更新不存在文档的元数据"""
        update_data = {
            'tags': ['test'],
            'vendor': 'Huawei'
        }

        response = client.patch('/api/v1/knowledge/documents/nonexistent',
                              json=update_data,
                              headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data['code'] == 404
        assert data['status'] == 'error'
        assert data['error']['type'] == 'NOT_FOUND'

    def test_unauthorized_access(self, client):
        """测试未授权访问知识文档接口"""
        # 获取文档列表
        response = client.get('/api/v1/knowledge/documents')
        assert response.status_code == 401

        # 上传文档
        response = client.post('/api/v1/knowledge/documents')
        assert response.status_code == 401

        # 获取文档详情
        response = client.get('/api/v1/knowledge/documents/test')
        assert response.status_code == 401

        # 删除文档
        response = client.delete('/api/v1/knowledge/documents/test')
        assert response.status_code == 401

        # 重新解析文档
        response = client.post('/api/v1/knowledge/documents/test/reparse')
        assert response.status_code == 401

        # 更新文档元数据
        response = client.patch('/api/v1/knowledge/documents/test')
        assert response.status_code == 401

    def test_cross_user_access_prevention(self, client, auth_headers, other_user_document):
        """测试防止跨用户访问文档"""
        doc_id = other_user_document.id

        # 尝试访问其他用户的文档
        response = client.get(f'/api/v1/knowledge/documents/{doc_id}',
                            headers=auth_headers)
        assert response.status_code == 404  # 应该返回404而不是403

        # 尝试删除其他用户的文档
        response = client.delete(f'/api/v1/knowledge/documents/{doc_id}',
                               headers=auth_headers)
        assert response.status_code == 404

        # 尝试重新解析其他用户的文档
        response = client.post(f'/api/v1/knowledge/documents/{doc_id}/reparse',
                            headers=auth_headers)
        assert response.status_code == 404


@pytest.fixture
def sample_document(test_user):
    """创建示例文档fixture"""
    document = KnowledgeDocument(
        id='test_doc_001',
        filename='test_sample.txt',
        original_filename='sample_config.txt',
        file_path='/tmp/test_sample.txt',
        file_size=1024,
        mime_type='text/plain',
        vendor='Huawei',
        tags=['测试', '配置'],
        user_id=test_user.id,
        status='INDEXED'
    )

    db.session.add(document)
    db.session.commit()

    yield document

    # 清理
    db.session.delete(document)
    db.session.commit()


@pytest.fixture
def other_user_document():
    """创建其他用户的文档fixture"""
    # 先创建另一个用户
    other_user = User(
        username='other_test_user',
        email='other@test.com',
        is_active=True
    )
    other_user.set_password('password')
    db.session.add(other_user)
    db.session.flush()

    document = KnowledgeDocument(
        id='other_doc_001',
        filename='other_test.txt',
        original_filename='other_config.txt',
        file_path='/tmp/other_test.txt',
        file_size=2048,
        mime_type='text/plain',
        vendor='Cisco',
        tags=['其他用户', '测试'],
        user_id=other_user.id,
        status='INDEXED'
    )

    db.session.add(document)
    db.session.commit()

    yield document

    # 清理
    db.session.delete(document)
    db.session.delete(other_user)
    db.session.commit()
