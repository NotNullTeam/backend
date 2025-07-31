"""
IP智慧解答专家系统 - 简单API测试

本测试文件验证主要API端点是否正常工作。
"""

import pytest
import json
import tempfile
import io
from app import create_app, db
from app.models.user import User
from app.models.case import Case
from app.models.knowledge import KnowledgeDocument


class TestConfig:
    """测试配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    JWT_SECRET_KEY = 'test-jwt-secret'
    UPLOAD_FOLDER = tempfile.mkdtemp()
    # 禁用Redis以避免测试时连接问题
    REDIS_URL = 'redis://localhost:6379/15'  # 使用测试数据库


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """获取认证token"""
    # 创建测试用户
    user = User(
        username='testuser',
        email='test@example.com',
        roles='user'
    )
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()

    # 登录获取token
    response = client.post('/api/v1/auth/login', json={
        'username': 'testuser',
        'password': 'testpass'
    })

    data = response.get_json()
    return data['data']['access_token']


def test_app_creation(app):
    """测试应用创建"""
    assert app is not None
    assert app.config['TESTING'] is True


def test_auth_login(client):
    """测试用户登录"""
    # 创建用户
    user = User(username='test', email='test@example.com')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    # 登录
    response = client.post('/api/v1/auth/login', json={
        'username': 'test',
        'password': 'password'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'access_token' in data['data']


def test_auth_login_failure(client):
    """测试登录失败"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'nonexistent',
        'password': 'wrong'
    })

    assert response.status_code == 401


def test_get_current_user(client, auth_token):
    """测试获取当前用户"""
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.get('/api/v1/auth/me', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['username'] == 'testuser'


def test_create_case(client, auth_token):
    """测试创建案例"""
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.post('/api/v1/cases',
                          headers=headers,
                          json={'query': '测试问题'})

    assert response.status_code == 200
    data = response.get_json()
    assert 'caseId' in data['data']


def test_get_cases(client, auth_token):
    """测试获取案例列表"""
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.get('/api/v1/cases', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert 'items' in data['data']


def test_upload_document(client, auth_token):
    """测试文档上传"""
    headers = {'Authorization': f'Bearer {auth_token}'}

    # 创建测试文件
    test_content = b'Test document content'

    response = client.post('/api/v1/knowledge/documents',
                          headers=headers,
                          data={
                              'file': (io.BytesIO(test_content), 'test.txt'),
                              'vendor': 'Huawei'
                          },
                          content_type='multipart/form-data')

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['status'] == 'QUEUED'


def test_get_documents(client, auth_token):
    """测试获取文档列表"""
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.get('/api/v1/knowledge/documents', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert 'items' in data['data']


def test_unauthorized_access(client):
    """测试未授权访问"""
    response = client.get('/api/v1/cases')
    assert response.status_code == 401  # 修正期望的状态码

    response = client.get('/api/v1/knowledge/documents')
    assert response.status_code == 401  # 修正期望的状态码
