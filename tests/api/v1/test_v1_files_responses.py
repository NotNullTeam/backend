"""
API v1 文件模块响应测试

测试文件管理相关 API 的响应格式和状态码。
"""

import pytest
import io
import json
import os

from app import db
from app.models.files import UserFile

class TestFilesAPIResponses:
    """文件 API 响应测试类"""

    def test_upload_file_success_response(self, client, auth_headers):
        """测试上传文件成功响应格式"""
        data = {
            'file': (io.BytesIO(b"my file contents"), 'test.txt'),
            'description': 'A test file for upload'
        }
        response = client.post('/api/v1/files',
                              data=data,
                              headers=auth_headers,
                              content_type='multipart/form-data')

        assert response.status_code == 201
        json_data = response.get_json()

        assert json_data['code'] == 201
        assert json_data['status'] == 'success'
        assert 'data' in json_data
        assert 'file_info' in json_data['data']

        file_info = json_data['data']['file_info']
        assert 'id' in file_info
        assert 'filename' in file_info
        assert 'content_type' in file_info
        assert 'size' in file_info
        assert 'description' in file_info
        assert file_info['filename'] == 'test.txt'
        assert file_info['description'] == 'A test file for upload'

    def test_get_file_metadata_success_response(self, client, auth_headers, test_user_file):
        """测试获取文件元数据成功响应格式"""
        file_id = test_user_file.id
        response = client.get(f'/api/v1/files/{file_id}/metadata', headers=auth_headers)

        assert response.status_code == 200
        json_data = response.get_json()

        assert json_data['code'] == 200
        assert json_data['status'] == 'success'
        assert 'data' in json_data
        assert 'metadata' in json_data['data']

        metadata = json_data['data']['metadata']
        assert metadata['fileId'] == file_id
        assert metadata['fileName'] == 'test_fixture.txt'
        assert metadata['fileSize'] > 0

    def test_download_file_success_response(self, client, auth_headers, test_user_file):
        """测试文件下载成功响应"""
        file_id = test_user_file.id
        response = client.get(f'/api/v1/files/{file_id}?download=true', headers=auth_headers)

        assert response.status_code == 200
        assert 'attachment; filename=test_fixture.txt' in response.headers['Content-Disposition']
        assert response.mimetype == 'text/plain'
        assert response.data == b'This is a test file from fixture.'

    def test_delete_file_success_response(self, client, auth_headers, test_user_file):
        """测试文件删除成功响应"""
        file_id = test_user_file.id
        file_path = test_user_file.file_path

        response = client.delete(f'/api/v1/files/{file_id}', headers=auth_headers)

        assert response.status_code == 204

        # 验证数据库记录和物理文件是否已删除
        deleted_file_record = db.session.get(UserFile, file_id)
        assert deleted_file_record is None
        assert not os.path.exists(file_path)

    def test_upload_files_batch_success_response(self, client, auth_headers):
        """测试批量上传文件成功响应"""
        # 准备要上传的多个文件
        files_data = {
            'files': [
                (io.BytesIO(b'first file content'), 'test1.txt'),
                (io.BytesIO(b'second file content'), 'test2.txt')
            ]
        }

        response = client.post(
            '/api/v1/files/batch',
            headers=auth_headers,
            data=files_data,
            content_type='multipart/form-data'
        )

        # 1. 验证响应状态码和基本结构
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['code'] == 200
        assert json_data['status'] == 'success'

        # 2. 验证摘要信息
        summary = json_data['data']['summary']
        assert summary['total'] == 2
        assert summary['successful'] == 2
        assert summary['failed'] == 0

        # 3. 验证上传结果和清理
        upload_results = json_data['data']['uploadResults']
        assert len(upload_results) == 2
        
        file_ids_to_clean = []
        for result in upload_results:
            assert result['status'] == 'success'
            assert 'fileId' in result
            file_id = result['fileId']
            file_ids_to_clean.append(file_id)

            # 验证数据库和物理文件
            user_file = db.session.get(UserFile, file_id)
            assert user_file is not None
            assert os.path.exists(user_file.file_path)

            # 立即清理物理文件
            os.remove(user_file.file_path)

        # 统一清理数据库记录
        for file_id in file_ids_to_clean:
            user_file = db.session.get(UserFile, file_id)
            if user_file:
                db.session.delete(user_file)
        db.session.commit()
