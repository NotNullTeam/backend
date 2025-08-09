"""
IP智慧解答专家系统 - 模型测试

本模块测试所有数据模型的功能。
"""

import pytest
from datetime import datetime
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback


@pytest.mark.unit
@pytest.mark.models
class TestUserModel:
    """测试User模型"""

    def test_user_creation(self, database):
        """测试用户创建"""
        user = User(
            username='newuser',
            email='newuser@example.com',
            roles='user'
        )
        user.set_password('password123')

        database.session.add(user)
        database.session.commit()

        assert user.id is not None
        assert user.username == 'newuser'
        assert user.email == 'newuser@example.com'
        assert user.roles == 'user'
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.password_hash is not None
        assert user.password_hash != 'password123'  # 确保密码被哈希

    def test_set_password(self, database):
        """测试密码设置"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('mypassword')

        assert user.password_hash is not None
        assert user.password_hash != 'mypassword'
        assert len(user.password_hash) > 20  # 哈希后的密码应该很长

    def test_check_password(self, database):
        """测试密码验证"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('correctpassword')

        assert user.check_password('correctpassword') is True
        assert user.check_password('wrongpassword') is False
        assert user.check_password('') is False

    def test_get_roles(self, database):
        """测试角色获取"""
        # 单个角色
        user1 = User(username='user1', email='user1@example.com', roles='user')
        assert user1.get_roles() == ['user']

        # 多个角色
        user2 = User(username='user2', email='user2@example.com', roles='admin,user,moderator')
        assert user2.get_roles() == ['admin', 'user', 'moderator']

        # 空角色
        user3 = User(username='user3', email='user3@example.com', roles='')
        assert user3.get_roles() == []

        # None角色
        user4 = User(username='user4', email='user4@example.com', roles=None)
        assert user4.get_roles() == []

    def test_has_role(self, database):
        """测试角色检查"""
        user = User(username='testuser', email='test@example.com', roles='admin,user')

        assert user.has_role('admin') is True
        assert user.has_role('user') is True
        assert user.has_role('moderator') is False
        assert user.has_role('') is False

    def test_to_dict(self, database):
        """测试序列化为字典"""
        user = User(
            username='testuser',
            email='test@example.com',
            roles='admin,user',
            is_active=True
        )
        user.set_password('password123')

        database.session.add(user)
        database.session.commit()

        user_dict = user.to_dict()

        assert isinstance(user_dict, dict)
        assert user_dict['id'] == user.id
        assert user_dict['username'] == 'testuser'
        assert user_dict['email'] == 'test@example.com'
        assert user_dict['roles'] == ['admin', 'user']
        assert user_dict['is_active'] is True
        assert 'created_at' in user_dict
        assert 'updated_at' in user_dict
        assert user_dict['created_at'].endswith('Z')  # ISO格式
        assert 'password_hash' not in user_dict  # 密码不应该被序列化

    def test_user_repr(self, database):
        """测试用户字符串表示"""
        user = User(username='testuser', email='test@example.com')
        assert repr(user) == '<User testuser>'

    def test_username_unique_constraint(self, database):
        """测试用户名唯一约束"""
        from sqlalchemy.exc import IntegrityError
        
        user1 = User(username='duplicate', email='user1@example.com')
        user1.set_password('password123')
        user2 = User(username='duplicate', email='user2@example.com')
        user2.set_password('password456')

        database.session.add(user1)
        database.session.commit()

        database.session.add(user2)

        with pytest.raises(IntegrityError):  # 应该抛出完整性错误
            database.session.commit()
        
        # 确保回滚后会话状态正常
        database.session.rollback()

    def test_email_unique_constraint(self, database):
        """测试邮箱唯一约束"""
        from sqlalchemy.exc import IntegrityError
        
        user1 = User(username='user1', email='duplicate@example.com')
        user1.set_password('password123')
        user2 = User(username='user2', email='duplicate@example.com')
        user2.set_password('password456')

        database.session.add(user1)
        database.session.commit()

        database.session.add(user2)

        with pytest.raises(IntegrityError):  # 应该抛出完整性错误
            database.session.commit()
        
        # 确保回滚后会话状态正常
        database.session.rollback()


@pytest.mark.unit
@pytest.mark.models
class TestCaseModel:
    """测试Case模型"""

    def test_case_creation(self, database, sample_user):
        """测试案例创建"""
        case = Case(
            title='测试案例',
            status='open',
            user_id=sample_user.id
        )

        database.session.add(case)
        database.session.commit()

        assert case.id is not None
        assert len(case.id) == 36  # UUID长度
        assert case.title == '测试案例'
        assert case.status == 'open'
        assert case.user_id == sample_user.id
        assert case.created_at is not None
        assert case.updated_at is not None

    def test_case_to_dict(self, database, sample_user):
        """测试案例序列化"""
        case = Case(
            title='测试案例',
            status='solved',
            user_id=sample_user.id
        )

        database.session.add(case)
        database.session.commit()

        case_dict = case.to_dict()

        assert isinstance(case_dict, dict)
        assert case_dict['caseId'] == case.id
        assert case_dict['title'] == '测试案例'
        assert case_dict['status'] == 'solved'
        assert 'createdAt' in case_dict
        assert 'updatedAt' in case_dict
        assert case_dict['createdAt'].endswith('Z')

    def test_case_user_relationship(self, database, sample_user):
        """测试案例与用户的关系"""
        case = Case(
            title='测试案例',
            user_id=sample_user.id
        )

        database.session.add(case)
        database.session.commit()

        # 测试反向关系
        assert case.user == sample_user
        assert case in sample_user.cases


@pytest.mark.unit
@pytest.mark.models
class TestNodeModel:
    """测试Node模型"""

    def test_node_creation(self, database, sample_case):
        """测试节点创建"""
        node = Node(
            case_id=sample_case.id,
            type='USER_QUERY',
            title='用户问题',
            status='COMPLETED',
            content={'text': '网络连接问题'},
            node_metadata={'category': 'network'}
        )

        database.session.add(node)
        database.session.commit()

        assert node.id is not None
        assert len(node.id) == 36  # UUID长度
        assert node.case_id == sample_case.id
        assert node.type == 'USER_QUERY'
        assert node.title == '用户问题'
        assert node.status == 'COMPLETED'
        assert node.content == {'text': '网络连接问题'}
        assert node.node_metadata == {'category': 'network'}
        assert node.created_at is not None

    def test_node_to_dict(self, database, sample_case):
        """测试节点序列化"""
        node = Node(
            case_id=sample_case.id,
            type='AI_ANALYSIS',
            title='AI分析',
            status='PROCESSING',
            content={'analysis': '正在分析...'},
            node_metadata={'confidence': 0.8}
        )

        database.session.add(node)
        database.session.commit()

        node_dict = node.to_dict()

        assert isinstance(node_dict, dict)
        assert node_dict['id'] == node.id
        assert node_dict['type'] == 'AI_ANALYSIS'
        assert node_dict['title'] == 'AI分析'
        assert node_dict['status'] == 'PROCESSING'
        assert node_dict['content'] == {'analysis': '正在分析...'}
        assert node_dict['metadata'] == {'confidence': 0.8}

    def test_node_case_relationship(self, database, sample_case):
        """测试节点与案例的关系"""
        node = Node(
            case_id=sample_case.id,
            type='USER_QUERY',
            title='测试节点'
        )

        database.session.add(node)
        database.session.commit()

        # 测试关系
        assert node.case == sample_case
        assert node in sample_case.nodes


@pytest.mark.unit
@pytest.mark.models
class TestEdgeModel:
    """测试Edge模型"""

    def test_edge_creation(self, database, sample_case):
        """测试边创建"""
        # 创建两个节点
        node1 = Node(case_id=sample_case.id, type='USER_QUERY', title='节点1')
        node2 = Node(case_id=sample_case.id, type='AI_ANALYSIS', title='节点2')

        database.session.add_all([node1, node2])
        database.session.commit()

        # 创建边
        edge = Edge(
            case_id=sample_case.id,
            source=node1.id,
            target=node2.id
        )

        database.session.add(edge)
        database.session.commit()

        assert edge.id is not None
        assert edge.case_id == sample_case.id
        assert edge.source == node1.id
        assert edge.target == node2.id

    def test_edge_to_dict(self, database, sample_case):
        """测试边序列化"""
        # 创建节点
        node1 = Node(case_id=sample_case.id, type='USER_QUERY', title='节点1')
        node2 = Node(case_id=sample_case.id, type='AI_ANALYSIS', title='节点2')

        database.session.add_all([node1, node2])
        database.session.commit()

        # 创建边
        edge = Edge(
            case_id=sample_case.id,
            source=node1.id,
            target=node2.id
        )

        database.session.add(edge)
        database.session.commit()

        edge_dict = edge.to_dict()

        assert isinstance(edge_dict, dict)
        assert edge_dict['source'] == node1.id
        assert edge_dict['target'] == node2.id


@pytest.mark.unit
@pytest.mark.models
class TestKnowledgeDocumentModel:
    """测试KnowledgeDocument模型"""

    def test_knowledge_document_creation(self, database, sample_user):
        """测试知识文档创建"""
        doc = KnowledgeDocument(
            filename='test.pdf',
            original_filename='测试文档.pdf',
            file_path='/tmp/test.pdf',
            file_size=1024,
            mime_type='application/pdf',
            vendor='华为',
            tags=['OSPF', '路由'],
            status='QUEUED',
            user_id=sample_user.id
        )

        database.session.add(doc)
        database.session.commit()

        assert doc.id is not None
        assert len(doc.id) == 36  # UUID长度
        assert doc.filename == 'test.pdf'
        assert doc.original_filename == '测试文档.pdf'
        assert doc.file_path == '/tmp/test.pdf'
        assert doc.file_size == 1024
        assert doc.mime_type == 'application/pdf'
        assert doc.vendor == '华为'
        assert doc.tags == ['OSPF', '路由']
        assert doc.status == 'QUEUED'
        assert doc.progress == 0
        assert doc.user_id == sample_user.id
        assert doc.uploaded_at is not None

    def test_knowledge_document_to_dict(self, database, sample_user):
        """测试知识文档序列化"""
        doc = KnowledgeDocument(
            filename='test.pdf',
            original_filename='测试文档.pdf',
            file_path='/tmp/test.pdf',
            file_size=1024,
            mime_type='application/pdf',
            vendor='思科',
            tags=['BGP'],
            status='INDEXED',
            progress=100,
            user_id=sample_user.id
        )

        database.session.add(doc)
        database.session.commit()

        doc_dict = doc.to_dict()

        assert isinstance(doc_dict, dict)
        assert doc_dict['docId'] == doc.id
        assert doc_dict['fileName'] == '测试文档.pdf'
        assert doc_dict['vendor'] == '思科'
        assert doc_dict['tags'] == ['BGP']
        assert doc_dict['status'] == 'INDEXED'
        assert doc_dict['progress'] == 100
        assert 'uploadedAt' in doc_dict
        assert doc_dict['uploadedAt'].endswith('Z')


@pytest.mark.unit
@pytest.mark.models
class TestParsingJobModel:
    """测试ParsingJob模型"""

    def test_parsing_job_creation(self, database, sample_knowledge_document):
        """测试解析任务创建"""
        job = ParsingJob(
            document_id=sample_knowledge_document.id,
            status='PENDING'
        )

        database.session.add(job)
        database.session.commit()

        assert job.id is not None
        assert len(job.id) == 36  # UUID长度
        assert job.document_id == sample_knowledge_document.id
        assert job.status == 'PENDING'
        assert job.created_at is not None

    def test_parsing_job_to_dict(self, database, sample_knowledge_document):
        """测试解析任务序列化"""
        job = ParsingJob(
            document_id=sample_knowledge_document.id,
            status='COMPLETED',
            error_message=None
        )

        database.session.add(job)
        database.session.commit()

        job_dict = job.to_dict()

        assert isinstance(job_dict, dict)
        assert job_dict['id'] == job.id
        assert job_dict['document_id'] == sample_knowledge_document.id
        assert job_dict['status'] == 'COMPLETED'
        assert job_dict['error_message'] is None

    def test_parsing_job_document_relationship(self, database, sample_knowledge_document):
        """测试解析任务与文档的关系"""
        job = ParsingJob(
            document_id=sample_knowledge_document.id,
            status='PENDING'
        )

        database.session.add(job)
        database.session.commit()

        # 测试关系
        assert job.document == sample_knowledge_document
        assert job in sample_knowledge_document.parsing_jobs


@pytest.mark.unit
@pytest.mark.models
class TestFeedbackModel:
    """测试Feedback模型"""

    def test_feedback_creation(self, database, sample_case, sample_user):
        """测试反馈创建"""
        feedback = Feedback(
            case_id=sample_case.id,
            user_id=sample_user.id,
            outcome='solved',
            rating=5,
            comment='问题已解决',
            corrected_solution={'solution': '重启路由器'}
        )

        database.session.add(feedback)
        database.session.commit()

        assert feedback.id is not None
        assert len(feedback.id) == 36  # UUID长度
        assert feedback.case_id == sample_case.id
        assert feedback.user_id == sample_user.id
        assert feedback.outcome == 'solved'
        assert feedback.rating == 5
        assert feedback.comment == '问题已解决'
        assert feedback.corrected_solution == {'solution': '重启路由器'}
        assert feedback.created_at is not None
