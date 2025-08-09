"""
IP智慧解答专家系统 - 测试配置

本模块提供测试用的配置和fixture。
"""

import pytest
import tempfile
import os
from app import create_app, db
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback
from app.models.files import UserFile
import uuid


class TestConfig:
    """测试配置"""
    TESTING = True
    WTF_CSRF_ENABLED = False

    # 使用内存数据库避免并发锁定问题，但保留外键约束支持
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT配置
    JWT_SECRET_KEY = 'test-jwt-secret'
    from datetime import timedelta
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=3600)

    # Redis配置（测试时使用假的Redis）
    REDIS_URL = 'redis://localhost:6379/1'

    # 文件上传配置
    UPLOAD_FOLDER = tempfile.mkdtemp()
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024


@pytest.fixture(scope='function')
def app():
    """创建测试应用（每个测试函数独立实例）"""
    app = create_app(TestConfig)

    with app.app_context():
        # 启用SQLite外键约束支持
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        import sqlite3

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建CLI测试运行器"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client):
    """创建认证头"""
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

    assert response.status_code == 200
    data = response.get_json()
    token = data['access_token']  # RESTX API格式：直接字段

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(client):
    """创建管理员认证头"""
    # 创建管理员用户
    admin = User(
        username='admin',
        email='admin@example.com',
        roles='admin,user'
    )
    admin.set_password('adminpass')
    db.session.add(admin)
    db.session.commit()

    # 登录获取token
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': 'adminpass'
    })

    assert response.status_code == 200
    data = response.get_json()
    token = data['access_token']  # RESTX API格式：直接字段

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def test_user():
    """创建测试用户"""
    # 先检查是否已存在同名用户，如果存在则删除
    existing_user = User.query.filter_by(username='testuser').first()
    if existing_user:
        db.session.delete(existing_user)
        db.session.commit()

    user = User(
        username='testuser',
        email='test@example.com',
        roles='user'
    )
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()

    yield user

    # 清理用户数据
    db.session.delete(user)
    db.session.commit()


@pytest.fixture
def test_case(test_user):
    """创建测试案例"""
    case = Case(
        title='测试案例',
        user_id=test_user.id
    )
    db.session.add(case)
    db.session.commit()
    return case


@pytest.fixture
def sample_user():
    """创建样例用户（用于模型测试）"""
    user = User(
        username='sampleuser',
        email='sample@example.com',
        roles='user'
    )
    user.set_password('samplepass')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_case(sample_user):
    """创建样例案例（用于模型测试）"""
    case = Case(
        title='样例案例',
        user_id=sample_user.id
    )
    db.session.add(case)
    db.session.commit()
    return case


@pytest.fixture
def sample_knowledge_document(sample_user):
    """创建样例知识文档（用于模型测试）"""
    from app.models.knowledge import KnowledgeDocument
    import tempfile
    import os

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
    temp_file.write(b'Sample knowledge document content')
    temp_file.close()

    document = KnowledgeDocument(
        filename='sample_doc.txt',
        original_filename='sample_doc.txt',
        file_path=temp_file.name,
        file_size=len(b'Sample knowledge document content'),
        mime_type='text/plain',
        vendor='sample_vendor',
        tags=['sample', 'test'],
        status='INDEXED',
        user_id=sample_user.id
    )
    db.session.add(document)
    db.session.commit()

    yield document

    # 清理临时文件
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def test_document(auth_headers):
    """创建测试文档"""
    # 获取当前认证用户
    from app.models.user import User
    user = User.query.filter_by(username='testuser').first()
    assert user is not None

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
    temp_file.write(b'Test document content')
    temp_file.close()

    document = KnowledgeDocument(
        filename='test.txt',
        original_filename='test.txt',
        file_path=temp_file.name,
        file_size=20,
        mime_type='text/plain',
        user_id=user.id,
        vendor='Huawei',
        tags=['network', 'router']
    )
    db.session.add(document)
    db.session.commit()

    yield document

    # 清理临时文件
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def test_user_file(test_user):
    """创建一个测试文件记录"""
    # In case the test needs a physical file
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, 'test_fixture.txt')
    with open(file_path, 'w') as f:
        f.write('This is a test file from fixture.')

    file = UserFile(
        id=str(uuid.uuid4()),
        filename='test_fixture.txt',
        original_filename='test_fixture.txt',
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_type='document',
        mime_type='text/plain',
        user_id=test_user.id
    )
    db.session.add(file)
    db.session.commit()

    yield file

    # Cleanup
    db.session.delete(file)
    db.session.commit()
    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.fixture(scope='function')
def database(app):
    """创建测试数据库（为每个测试函数提供干净的数据库）"""
    with app.app_context():
        # 由于app fixture已经创建了表，这里只需要确保在测试后清理
        yield db
        # 测试后清理数据（保留表结构）
        try:
            # 确保会话处于干净状态
            if db.session.is_active:
                db.session.rollback()

            # 清理所有表数据
            for table in reversed(db.metadata.sorted_tables):
                db.session.execute(table.delete())
            db.session.commit()
        except Exception as e:
            # 如果清理失败，强制回滚并重新开始
            db.session.rollback()
            try:
                # 再次尝试清理
                for table in reversed(db.metadata.sorted_tables):
                    db.session.execute(table.delete())
                db.session.commit()
            except Exception:
                # 最后的保险措施：移除会话
                db.session.remove()


