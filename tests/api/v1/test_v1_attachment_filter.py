"""
案例attachmentType过滤功能测试

测试案例列表接口的附件类型过滤功能
"""

import pytest
import json
from app import db
from app.models.user import User
from app.models.case import Case
from app.models.files import UserFile
from flask_jwt_extended import create_access_token


class TestAttachmentTypeFilter:
    """attachmentType过滤功能测试类"""

    @pytest.fixture
    def test_user(self, app):
        """创建测试用户"""
        with app.app_context():
            user = User(username='test_filter_user', email='filter@test.com')
            user.set_password('test_password')
            db.session.add(user)
            db.session.commit()
            user_id = user.id  # 保存 user_id
            db.session.refresh(user)  # 刷新对象
            return user

    @pytest.fixture
    def access_token(self, app, test_user):
        """创建access token"""
        with app.app_context():
            # 重新获取用户以避免DetachedInstanceError
            user = db.session.get(User, test_user.id)
            return create_access_token(identity=str(user.id))

    @pytest.fixture
    def test_cases_with_files(self, app, test_user):
        """创建带有不同类型附件的测试案例"""
        with app.app_context():
            # 案例1: 带有图片附件
            case1 = Case(
                title='案例1-图片',
                user_id=test_user.id,
                status='open'
            )
            db.session.add(case1)
            db.session.flush()  # 获取case1.id

            file1 = UserFile(
                filename='network_topology.png',
                original_filename='network_topology.png',
                file_path='/uploads/test1.png',
                file_size=1024,
                file_type='image',
                mime_type='image/png',
                user_id=str(test_user.id),
                associated_cases=[case1.id]
            )
            db.session.add(file1)

            # 案例2: 带有文档附件
            case2 = Case(
                title='案例2-文档',
                user_id=test_user.id,
                status='open'
            )
            db.session.add(case2)
            db.session.flush()

            file2 = UserFile(
                filename='config_guide.pdf',
                original_filename='config_guide.pdf',
                file_path='/uploads/test2.pdf',
                file_size=2048,
                file_type='document',
                mime_type='application/pdf',
                user_id=str(test_user.id),
                associated_cases=[case2.id]
            )
            db.session.add(file2)

            # 案例3: 带有日志附件
            case3 = Case(
                title='案例3-日志',
                user_id=test_user.id,
                status='solved'
            )
            db.session.add(case3)
            db.session.flush()

            file3 = UserFile(
                filename='system.log',
                original_filename='system.log',
                file_path='/uploads/test3.log',
                file_size=4096,
                file_type='log',
                mime_type='text/plain',
                user_id=str(test_user.id),
                associated_cases=[case3.id]
            )
            db.session.add(file3)

            # 案例4: 带有配置文件附件
            case4 = Case(
                title='案例4-配置',
                user_id=test_user.id,
                status='open'
            )
            db.session.add(case4)
            db.session.flush()

            file4 = UserFile(
                filename='router.cfg',
                original_filename='router.cfg',
                file_path='/uploads/test4.cfg',
                file_size=512,
                file_type='config',
                mime_type='text/plain',
                user_id=str(test_user.id),
                associated_cases=[case4.id]
            )
            db.session.add(file4)

            # 案例5: 没有附件
            case5 = Case(
                title='案例5-无附件',
                user_id=test_user.id,
                status='open'
            )
            db.session.add(case5)

            db.session.commit()
            return [case1, case2, case3, case4, case5]

    def test_filter_by_image_type(self, client, access_token, test_cases_with_files):
        """测试按图片类型过滤"""
        response = client.get(
            '/api/v1/cases/?attachmentType=image',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['title'] == '案例1-图片'

    def test_filter_by_document_type(self, client, access_token, test_cases_with_files):
        """测试按文档类型过滤"""
        response = client.get(
            '/api/v1/cases/?attachmentType=document',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['title'] == '案例2-文档'

    def test_filter_by_log_type(self, client, access_token, test_cases_with_files):
        """测试按日志类型过滤"""
        response = client.get(
            '/api/v1/cases/?attachmentType=log',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['title'] == '案例3-日志'

    def test_filter_by_config_type(self, client, access_token, test_cases_with_files):
        """测试按配置文件类型过滤"""
        response = client.get(
            '/api/v1/cases/?attachmentType=config',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['title'] == '案例4-配置'

    def test_filter_by_nonexistent_type(self, client, access_token, test_cases_with_files):
        """测试按不存在的附件类型过滤"""
        response = client.get(
            '/api/v1/cases/?attachmentType=video',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 0  # 没有视频类型的附件

    def test_no_attachment_filter(self, client, access_token, test_cases_with_files):
        """测试不使用附件过滤（返回所有案例）"""
        response = client.get(
            '/api/v1/cases/',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 5  # 所有案例都应该返回

    def test_combined_filters(self, client, access_token, test_cases_with_files):
        """测试组合过滤（attachmentType + status）"""
        response = client.get(
            '/api/v1/cases/?attachmentType=image&status=open',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 1
        assert items[0]['title'] == '案例1-图片'
        assert items[0]['status'] == 'open'

    def test_attachment_filter_with_pagination(self, client, access_token, test_cases_with_files):
        """测试附件过滤与分页组合"""
        response = client.get(
            '/api/v1/cases/?attachmentType=document&page=1&pageSize=10',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 1

        # 检查分页信息
        pagination = data['data']['pagination']
        assert pagination['total'] == 1
        assert pagination['page'] == 1
        assert pagination['per_page'] == 10

    def test_attachment_filter_unauthorized(self, client, test_cases_with_files):
        """测试未授权情况下的附件过滤"""
        response = client.get('/api/v1/cases/?attachmentType=image')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['code'] == 401
        assert data['status'] == 'error'
        assert '需要认证Token' in data['error']['message']

    def test_attachment_filter_case_isolation(self, app, client, test_cases_with_files):
        """测试用户隔离（用户只能看到自己的案例）"""
        with app.app_context():
            # 创建另一个用户
            other_user = User(username='other_user', email='other@test.com')
            other_user.set_password('test_password')
            db.session.add(other_user)
            db.session.commit()

            other_token = create_access_token(identity=str(other_user.id))

        response = client.get(
            '/api/v1/cases/?attachmentType=image',
            headers={'Authorization': f'Bearer {other_token}'}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['code'] == 200
        assert data['status'] == 'success'

        items = data['data']['items']
        assert len(items) == 0  # 其他用户看不到测试用户的案例
