"""
IP智慧解答专家系统 - 知识文档API测试

本模块测试知识文档相关的API接口。
"""

import pytest
import tempfile
import io
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app import db


class TestKnowledgeAPI:
    """知识文档API测试类"""

    def test_upload_document_success(self, client, auth_headers):
        """测试文档上传成功"""
        # 创建测试文件
        test_file = io.BytesIO(b'Test document content')
        test_file.name = 'test.txt'

        response = client.post('/api/v1/knowledge/documents',
                             headers=auth_headers,
                             data={
                                 'file': (test_file, 'test.txt'),
                                 'vendor': 'Huawei',
                                 'tags': ['network', 'router']
                             },
                             content_type='multipart/form-data')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'docId' in data['data']
        assert data['data']['status'] == 'QUEUED'

    def test_upload_document_no_file(self, client, auth_headers):
        """测试上传时没有文件"""
        response = client.post('/api/v1/knowledge/documents',
                             headers=auth_headers,
                             data={},
                             content_type='multipart/form-data')

        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert '没有选择文件' in data['error']['message']

    def test_upload_document_invalid_type(self, client, auth_headers):
        """测试上传不支持的文件类型"""
        test_file = io.BytesIO(b'Test content')
        test_file.name = 'test.exe'

        response = client.post('/api/v1/knowledge/documents',
                             headers=auth_headers,
                             data={
                                 'file': (test_file, 'test.exe')
                             },
                             content_type='multipart/form-data')

        assert response.status_code == 400
        data = response.get_json()
        assert '不支持的文件类型' in data['error']['message']

    def test_get_documents_list(self, client, auth_headers, test_document):
        """测试获取文档列表"""
        response = client.get('/api/v1/knowledge/documents',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'documents' in data['data']
        assert data['data']['pagination']['total'] >= 1

    def test_get_documents_with_filters(self, client, auth_headers, test_document):
        """测试使用过滤器获取文档"""
        response = client.get('/api/v1/knowledge/documents?status=QUEUED',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_get_documents_with_pagination(self, client, auth_headers):
        """测试分页获取文档"""
        response = client.get('/api/v1/knowledge/documents?page=1&pageSize=5',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['pagination']['page'] == 1
        assert data['data']['pagination']['per_page'] == 5

    def test_get_document_detail(self, client, auth_headers, test_document):
        """测试获取文档详情"""
        response = client.get(f'/api/v1/knowledge/documents/{test_document.id}',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['docId'] == test_document.id
        assert data['data']['fileName'] == test_document.original_filename

    def test_get_document_detail_not_found(self, client, auth_headers):
        """测试获取不存在的文档"""
        response = client.get('/api/v1/knowledge/documents/nonexistent-id',
                            headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'

    def test_delete_document(self, client, auth_headers, test_document):
        """测试删除文档"""
        response = client.delete(f'/api/v1/knowledge/documents/{test_document.id}',
                               headers=auth_headers)

        assert response.status_code == 204

        # 验证文档已删除
        response = client.get(f'/api/v1/knowledge/documents/{test_document.id}',
                            headers=auth_headers)
        assert response.status_code == 404

    def test_reparse_document(self, client, auth_headers, test_document):
        """测试重新解析文档"""
        # 先将文档状态设为失败
        test_document.status = 'FAILED'
        test_document.error_message = 'Test error'
        db.session.commit()

        response = client.post(f'/api/v1/knowledge/documents/{test_document.id}/reparse',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['data']['status'] == 'QUEUED'

        # 验证文档状态已重置
        updated_doc = KnowledgeDocument.query.get(test_document.id)
        assert updated_doc.status == 'QUEUED'
        assert updated_doc.progress == 0
        assert updated_doc.error_message is None

    def test_reparse_document_not_found(self, client, auth_headers):
        """测试重新解析不存在的文档"""
        response = client.post('/api/v1/knowledge/documents/nonexistent-id/reparse',
                            headers=auth_headers)

        assert response.status_code == 404

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get('/api/v1/knowledge/documents')
        assert response.status_code == 401  # JWT missing

        test_file = io.BytesIO(b'Test content')
        response = client.post('/api/v1/knowledge/documents',
                             data={'file': (test_file, 'test.txt')},
                             content_type='multipart/form-data')
        assert response.status_code == 401

    def test_access_other_user_document(self, client, auth_headers):
        """测试访问其他用户的文档"""
        # 创建另一个用户的文档
        from app.models.user import User
        other_user = User(username='other', email='other@example.com')
        other_user.set_password('pass')
        db.session.add(other_user)
        db.session.flush()

        other_doc = KnowledgeDocument(
            filename='other.txt',
            original_filename='other.txt',
            file_path='/tmp/other.txt',
            user_id=other_user.id
        )
        db.session.add(other_doc)
        db.session.commit()

        # 尝试访问
        response = client.get(f'/api/v1/knowledge/documents/{other_doc.id}',
                            headers=auth_headers)
        assert response.status_code == 404

    def test_document_with_parsing_job(self, client, auth_headers, test_document):
        """测试带有解析任务的文档详情"""
        # 创建解析任务
        parsing_job = ParsingJob(
            document_id=test_document.id,
            status='COMPLETED',
            result_data={'chunks_count': 5}
        )
        db.session.add(parsing_job)
        db.session.commit()

        response = client.get(f'/api/v1/knowledge/documents/{test_document.id}',
                            headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['parsingJob'] is not None
        assert data['data']['parsingJob']['status'] == 'COMPLETED'
        assert data['data']['parsingJob']['resultData']['chunks_count'] == 5

    def test_update_document_metadata_success(self, client, auth_headers, test_document):
        """测试成功更新文档元数据"""
        update_data = {
            'tags': ['OSPF', 'BGP', 'network'],
            'vendor': 'Cisco'
        }

        response = client.patch(f'/api/v1/knowledge/documents/{test_document.id}',
                              headers=auth_headers,
                              json=update_data)

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

        # 验证更新
        updated_doc = KnowledgeDocument.query.get(test_document.id)
        assert updated_doc.tags == ['OSPF', 'BGP', 'network']
        assert updated_doc.vendor == 'Cisco'

    def test_update_document_metadata_partial(self, client, auth_headers, test_document):
        """测试部分更新文档元数据"""
        # 只更新标签
        update_data = {
            'tags': ['new_tag']
        }

        response = client.patch(f'/api/v1/knowledge/documents/{test_document.id}',
                              headers=auth_headers,
                              json=update_data)

        assert response.status_code == 200

        # 验证只有标签被更新
        updated_doc = KnowledgeDocument.query.get(test_document.id)
        assert updated_doc.tags == ['new_tag']
        assert updated_doc.vendor == 'Huawei'  # 原值保持不变

    def test_update_document_metadata_invalid_tags(self, client, auth_headers, test_document):
        """测试使用无效格式的标签更新"""
        update_data = {
            'tags': 'invalid_format'  # 应该是数组
        }

        response = client.patch(f'/api/v1/knowledge/documents/{test_document.id}',
                              headers=auth_headers,
                              json=update_data)

        assert response.status_code == 400
        data = response.get_json()
        assert 'tags必须是数组格式' in data['error']['message']

    def test_update_document_metadata_not_found(self, client, auth_headers):
        """测试更新不存在的文档"""
        update_data = {'tags': ['test']}

        response = client.patch('/api/v1/knowledge/documents/nonexistent-id',
                              headers=auth_headers,
                              json=update_data)

        assert response.status_code == 404

    def test_update_document_metadata_empty_body(self, client, auth_headers, test_document):
        """测试空请求体"""
        response = client.patch(f'/api/v1/knowledge/documents/{test_document.id}',
                              headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert '请求体不能为空' in data['error']['message']
