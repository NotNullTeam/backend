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

    # 使用内存数据库
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
    token = data['data']['access_token']

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
    token = data['data']['access_token']

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

import os
import tempfile
import pytest
from app import create_app, db
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback
from app.models.files import UserFile
import uuid
from config.settings import TestingConfig


class TestConfig(TestingConfig):
    """测试专用配置"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    # 使用内存SQLite数据库进行测试
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # 禁用JWT过期检查以便测试
    JWT_ACCESS_TOKEN_EXPIRES = False
    JWT_REFRESH_TOKEN_EXPIRES = False


@pytest.fixture(scope='session')
def app():
    """创建测试应用实例"""
    app = create_app(TestConfig)

    # 建立应用上下文
    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """创建CLI测试运行器"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def database(app):
    """创建测试数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()

        yield db

        # 清理数据库
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def sample_user(database):
    """创建示例用户"""
    user = User(
        username='testuser',
        email='test@example.com',
        roles='user'
    )
    user.set_password('testpass123')

    database.session.add(user)
    database.session.commit()

    return user


@pytest.fixture(scope='function')
def admin_user(database):
    """创建管理员用户"""
    admin = User(
        username='admin',
        email='admin@example.com',
        roles='admin,user'
    )
    admin.set_password('admin123')

    database.session.add(admin)
    database.session.commit()

    return admin


@pytest.fixture(scope='function')
def inactive_user(database):
    """创建非活跃用户"""
    user = User(
        username='inactive',
        email='inactive@example.com',
        roles='user',
        is_active=False
    )
    user.set_password('inactive123')

    database.session.add(user)
    database.session.commit()

    return user


@pytest.fixture(scope='function')
def auth_headers(client, sample_user):
    """获取认证头部"""
    response = client.post('/api/v1/auth/login', json={
        'username': sample_user.username,
        'password': 'testpass123'
    })

    data = response.get_json()
    token = data['data']['access_token']

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='function')
def admin_auth_headers(client, admin_user):
    """获取管理员认证头部"""
    response = client.post('/api/v1/auth/login', json={
        'username': admin_user.username,
        'password': 'admin123'
    })

    data = response.get_json()
    token = data['data']['access_token']

    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='function')
def sample_case(database, sample_user):
    """创建示例案例"""
    case = Case(
        title='测试网络故障案例',
        status='open',
        user_id=sample_user.id
    )

    database.session.add(case)
    database.session.commit()

    return case


@pytest.fixture(scope='function')
def sample_node(database, sample_case):
    """创建示例节点"""
    node = Node(
        case_id=sample_case.id,
        type='USER_QUERY',
        title='用户问题',
        status='COMPLETED',
        content={
            'text': '网络连接问题',
            'attachments': []
        },
        node_metadata={
            'timestamp': '2024-01-01T00:00:00'
        }
    )

    database.session.add(node)
    database.session.commit()

    return node


@pytest.fixture(scope='function')
def sample_feedback(database, sample_case, sample_user):
    """创建示例反馈"""
    feedback = Feedback(
        case_id=sample_case.id,
        user_id=sample_user.id,
        outcome='solved',
        rating=4,
        comment='问题已解决'
    )

    database.session.add(feedback)
    database.session.commit()

    return feedback


@pytest.fixture(scope='function')
def sample_knowledge_document(database, sample_user):
    """创建示例知识文档"""
    doc = KnowledgeDocument(
        filename='test_doc.pdf',
        original_filename='测试文档.pdf',
        file_path='/tmp/test_doc.pdf',
        file_size=1024,
        mime_type='application/pdf',
        vendor='华为',
        tags=['OSPF', '路由'],
        user_id=sample_user.id
    )

    database.session.add(doc)
    database.session.commit()

    return doc


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(database):
    """
    为所有测试启用数据库访问
    这个fixture会自动应用到所有测试函数
    """
    pass


@pytest.fixture
def sample_cases_data(database, sample_user):
    """创建统计测试用的案例数据"""
    from datetime import datetime, timedelta

    cases = []
    # 创建多个测试案例，包含不同状态和时间
    for i in range(15):
        created_time = datetime.utcnow() - timedelta(days=i * 2)
        status = 'solved' if i % 3 == 0 else ('closed' if i % 3 == 1 else 'open')

        case = Case(
            title=f'测试案例 {i+1}',
            status=status,
            user_id=sample_user.id,
            created_at=created_time,
            updated_at=created_time + timedelta(hours=2)
        )
        database.session.add(case)
        database.session.flush()

        # 为每个案例创建用户查询节点
        node = Node(
            case_id=case.id,
            type='USER_QUERY',
            title=f'用户查询 {i+1}',
            status='COMPLETED',
            content={'query': f'如何配置OSPF路由 {i+1}'},
            node_metadata={'category': 'OSPF路由' if i % 4 == 0 else ('BGP配置' if i % 4 == 1 else ('VLAN设置' if i % 4 == 2 else '接口故障'))},
            created_at=created_time
        )
        database.session.add(node)

        cases.append(case)

    # 创建一些反馈数据
    for i, case in enumerate(cases[:5]):
        feedback = Feedback(
            case_id=case.id,
            user_id=sample_user.id,
            outcome='solved' if case.status == 'solved' else 'unsolved',
            rating=4 + (i % 2),  # 4 或 5 分
            comment=f'反馈内容 {i+1}',
            created_at=case.created_at + timedelta(hours=1)
        )
        database.session.add(feedback)

    database.session.commit()
    return cases
