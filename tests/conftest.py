"""
IP智慧解答专家系统 - 测试配置

本模块包含pytest的全局配置和fixture定义。
"""

import os
import tempfile
import pytest
from app import create_app, db
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback
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
