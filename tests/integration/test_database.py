"""
IP智慧解答专家系统 - 数据库操作测试

本模块测试数据库的CRUD操作、关系映射和约束。
"""

import pytest
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback


@pytest.mark.integration
@pytest.mark.models
class TestDatabaseCRUD:
    """测试数据库CRUD操作"""

    def test_user_crud_operations(self, database):
        """测试用户的CRUD操作"""
        # Create
        user = User(
            username='cruduser',
            email='crud@example.com',
            roles='user'
        )
        user.set_password('password123')

        database.session.add(user)
        database.session.commit()

        user_id = user.id
        assert user_id is not None

        # Read
        retrieved_user = User.query.get(user_id)
        assert retrieved_user is not None
        assert retrieved_user.username == 'cruduser'
        assert retrieved_user.email == 'crud@example.com'

        # Update
        retrieved_user.email = 'updated@example.com'
        database.session.commit()

        updated_user = User.query.get(user_id)
        assert updated_user.email == 'updated@example.com'

        # Delete
        database.session.delete(updated_user)
        database.session.commit()

        deleted_user = User.query.get(user_id)
        assert deleted_user is None

    def test_case_crud_operations(self, database, sample_user):
        """测试案例的CRUD操作"""
        # Create
        case = Case(
            title='CRUD测试案例',
            status='open',
            user_id=sample_user.id
        )

        database.session.add(case)
        database.session.commit()

        case_id = case.id
        assert case_id is not None

        # Read
        retrieved_case = Case.query.get(case_id)
        assert retrieved_case is not None
        assert retrieved_case.title == 'CRUD测试案例'
        assert retrieved_case.status == 'open'

        # Update
        retrieved_case.status = 'solved'
        retrieved_case.title = '已解决的案例'
        database.session.commit()

        updated_case = Case.query.get(case_id)
        assert updated_case.status == 'solved'
        assert updated_case.title == '已解决的案例'

        # Delete
        database.session.delete(updated_case)
        database.session.commit()

        deleted_case = Case.query.get(case_id)
        assert deleted_case is None

    def test_knowledge_document_crud_operations(self, database, sample_user):
        """测试知识文档的CRUD操作"""
        # Create
        doc = KnowledgeDocument(
            filename='crud_test.pdf',
            original_filename='CRUD测试文档.pdf',
            file_path='/tmp/crud_test.pdf',
            file_size=2048,
            mime_type='application/pdf',
            vendor='华为',
            tags=['测试', 'CRUD'],
            user_id=sample_user.id
        )

        database.session.add(doc)
        database.session.commit()

        doc_id = doc.id
        assert doc_id is not None

        # Read
        retrieved_doc = KnowledgeDocument.query.get(doc_id)
        assert retrieved_doc is not None
        assert retrieved_doc.original_filename == 'CRUD测试文档.pdf'
        assert retrieved_doc.vendor == '华为'

        # Update
        retrieved_doc.status = 'INDEXED'
        retrieved_doc.progress = 100
        retrieved_doc.vendor = '思科'
        database.session.commit()

        updated_doc = KnowledgeDocument.query.get(doc_id)
        assert updated_doc.status == 'INDEXED'
        assert updated_doc.progress == 100
        assert updated_doc.vendor == '思科'

        # Delete
        database.session.delete(updated_doc)
        database.session.commit()

        deleted_doc = KnowledgeDocument.query.get(doc_id)
        assert deleted_doc is None


@pytest.mark.integration
@pytest.mark.models
class TestDatabaseRelationships:
    """测试数据库关系映射"""

    def test_user_case_relationship(self, database, sample_user):
        """测试用户与案例的关系"""
        # 创建多个案例
        case1 = Case(title='案例1', user_id=sample_user.id)
        case2 = Case(title='案例2', user_id=sample_user.id)
        case3 = Case(title='案例3', user_id=sample_user.id)

        database.session.add_all([case1, case2, case3])
        database.session.commit()

        # 测试一对多关系
        user_cases = sample_user.cases.all()
        assert len(user_cases) == 3
        assert case1 in user_cases
        assert case2 in user_cases
        assert case3 in user_cases

        # 测试反向关系
        assert case1.user == sample_user
        assert case2.user == sample_user
        assert case3.user == sample_user

    def test_case_node_relationship(self, database, sample_case):
        """测试案例与节点的关系"""
        # 创建多个节点
        node1 = Node(case_id=sample_case.id, type='USER_QUERY', title='节点1')
        node2 = Node(case_id=sample_case.id, type='AI_ANALYSIS', title='节点2')
        node3 = Node(case_id=sample_case.id, type='SOLUTION', title='节点3')

        database.session.add_all([node1, node2, node3])
        database.session.commit()

        # 测试一对多关系
        case_nodes = sample_case.nodes.all()
        assert len(case_nodes) == 3
        assert node1 in case_nodes
        assert node2 in case_nodes
        assert node3 in case_nodes

        # 测试反向关系
        assert node1.case == sample_case
        assert node2.case == sample_case
        assert node3.case == sample_case

    def test_case_edge_relationship(self, database, sample_case):
        """测试案例与边的关系"""
        # 创建节点
        node1 = Node(case_id=sample_case.id, type='USER_QUERY', title='节点1')
        node2 = Node(case_id=sample_case.id, type='AI_ANALYSIS', title='节点2')

        database.session.add_all([node1, node2])
        database.session.commit()

        # 创建边
        edge1 = Edge(case_id=sample_case.id, source=node1.id, target=node2.id)
        edge2 = Edge(case_id=sample_case.id, source=node2.id, target=node1.id)

        database.session.add_all([edge1, edge2])
        database.session.commit()

        # 测试一对多关系
        case_edges = sample_case.edges.all()
        assert len(case_edges) == 2
        assert edge1 in case_edges
        assert edge2 in case_edges

        # 测试反向关系
        assert edge1.case == sample_case
        assert edge2.case == sample_case

    def test_user_knowledge_document_relationship(self, database, sample_user):
        """测试用户与知识文档的关系"""
        # 创建多个文档
        doc1 = KnowledgeDocument(
            filename='doc1.pdf',
            original_filename='文档1.pdf',
            file_path='/tmp/doc1.pdf',
            user_id=sample_user.id
        )
        doc2 = KnowledgeDocument(
            filename='doc2.pdf',
            original_filename='文档2.pdf',
            file_path='/tmp/doc2.pdf',
            user_id=sample_user.id
        )

        database.session.add_all([doc1, doc2])
        database.session.commit()

        # 测试一对多关系
        user_docs = sample_user.knowledge_documents.all()
        assert len(user_docs) == 2
        assert doc1 in user_docs
        assert doc2 in user_docs

        # 测试反向关系
        assert doc1.user == sample_user
        assert doc2.user == sample_user

    def test_knowledge_document_parsing_job_relationship(self, database, sample_knowledge_document):
        """测试知识文档与解析任务的关系"""
        # 创建多个解析任务
        job1 = ParsingJob(document_id=sample_knowledge_document.id, status='PENDING')
        job2 = ParsingJob(document_id=sample_knowledge_document.id, status='COMPLETED')

        database.session.add_all([job1, job2])
        database.session.commit()

        # 测试一对多关系
        doc_jobs = sample_knowledge_document.parsing_jobs.all()
        assert len(doc_jobs) == 2
        assert job1 in doc_jobs
        assert job2 in doc_jobs

        # 测试反向关系
        assert job1.document == sample_knowledge_document
        assert job2.document == sample_knowledge_document

    def test_case_feedback_relationship(self, database, sample_case, sample_user):
        """测试案例与反馈的关系"""
        # 创建反馈
        feedback1 = Feedback(
            case_id=sample_case.id,
            user_id=sample_user.id,
            outcome='solved',
            rating=5
        )
        feedback2 = Feedback(
            case_id=sample_case.id,
            user_id=sample_user.id,
            outcome='unsolved',
            rating=2
        )

        database.session.add_all([feedback1, feedback2])
        database.session.commit()

        # 测试一对多关系
        case_feedback = sample_case.feedback.all()
        assert len(case_feedback) == 2
        assert feedback1 in case_feedback
        assert feedback2 in case_feedback

        # 测试反向关系
        assert feedback1.case == sample_case
        assert feedback2.case == sample_case


@pytest.mark.integration
@pytest.mark.models
class TestDatabaseConstraints:
    """测试数据库约束"""

    def test_user_username_unique_constraint(self, database):
        """测试用户名唯一约束"""
        user1 = User(username='unique_test', email='user1@example.com')
        user1.set_password('password123')
        user2 = User(username='unique_test', email='user2@example.com')
        user2.set_password('password456')

        database.session.add(user1)
        database.session.commit()

        database.session.add(user2)

        with pytest.raises(IntegrityError):
            database.session.commit()

        database.session.rollback()

    def test_user_email_unique_constraint(self, database):
        """测试邮箱唯一约束"""
        user1 = User(username='user1', email='unique@example.com')
        user1.set_password('password123')
        user2 = User(username='user2', email='unique@example.com')
        user2.set_password('password456')

        database.session.add(user1)
        database.session.commit()

        database.session.add(user2)

        with pytest.raises(IntegrityError):
            database.session.commit()

        database.session.rollback()

    def test_case_user_foreign_key_constraint(self, database):
        """测试案例用户外键约束"""
        # SQLite在内存模式下可能不严格执行外键约束
        pytest.skip("SQLite内存数据库外键约束测试跳过")

    def test_node_case_foreign_key_constraint(self, database):
        """测试节点案例外键约束"""
        # SQLite在内存模式下可能不严格执行外键约束
        pytest.skip("SQLite内存数据库外键约束测试跳过")

    def test_cascade_delete_user_cases(self, database):
        """测试用户删除时的级联删除"""
        # 创建用户和案例
        user = User(username='cascade_test', email='cascade@example.com')
        user.set_password('password123')
        database.session.add(user)
        database.session.commit()

        case1 = Case(title='案例1', user_id=user.id)
        case2 = Case(title='案例2', user_id=user.id)
        database.session.add_all([case1, case2])
        database.session.commit()

        case1_id = case1.id
        case2_id = case2.id

        # 删除用户
        database.session.delete(user)
        database.session.commit()

        # 验证案例也被删除
        assert Case.query.get(case1_id) is None
        assert Case.query.get(case2_id) is None

    def test_cascade_delete_case_nodes_and_edges(self, database, sample_user):
        """测试案例删除时的级联删除"""
        # 创建案例
        case = Case(title='级联测试案例', user_id=sample_user.id)
        database.session.add(case)
        database.session.commit()

        # 创建节点和边
        node1 = Node(case_id=case.id, type='USER_QUERY', title='节点1')
        node2 = Node(case_id=case.id, type='AI_ANALYSIS', title='节点2')
        database.session.add_all([node1, node2])
        database.session.commit()

        edge = Edge(case_id=case.id, source=node1.id, target=node2.id)
        database.session.add(edge)
        database.session.commit()

        node1_id = node1.id
        node2_id = node2.id
        edge_id = edge.id

        # 删除案例
        database.session.delete(case)
        database.session.commit()

        # 验证节点和边也被删除
        assert Node.query.get(node1_id) is None
        assert Node.query.get(node2_id) is None
        assert Edge.query.get(edge_id) is None


@pytest.mark.integration
@pytest.mark.models
class TestDatabaseQueries:
    """测试数据库查询"""

    def test_user_query_by_username(self, database, sample_user):
        """测试按用户名查询用户"""
        user = User.query.filter_by(username=sample_user.username).first()
        assert user is not None
        assert user.id == sample_user.id

    def test_user_query_by_email(self, database, sample_user):
        """测试按邮箱查询用户"""
        user = User.query.filter_by(email=sample_user.email).first()
        assert user is not None
        assert user.id == sample_user.id

    def test_case_query_by_status(self, database, sample_user):
        """测试按状态查询案例"""
        # 创建不同状态的案例
        case1 = Case(title='开放案例', status='open', user_id=sample_user.id)
        case2 = Case(title='已解决案例', status='solved', user_id=sample_user.id)
        case3 = Case(title='已关闭案例', status='closed', user_id=sample_user.id)

        database.session.add_all([case1, case2, case3])
        database.session.commit()

        # 查询开放案例
        open_cases = Case.query.filter_by(status='open').all()
        assert len(open_cases) >= 1
        assert case1 in open_cases

        # 查询已解决案例
        solved_cases = Case.query.filter_by(status='solved').all()
        assert len(solved_cases) >= 1
        assert case2 in solved_cases

    def test_knowledge_document_query_by_vendor(self, database, sample_user):
        """测试按厂商查询知识文档"""
        # 创建不同厂商的文档
        doc1 = KnowledgeDocument(
            filename='huawei.pdf',
            original_filename='华为文档.pdf',
            file_path='/tmp/huawei.pdf',
            vendor='华为',
            user_id=sample_user.id
        )
        doc2 = KnowledgeDocument(
            filename='cisco.pdf',
            original_filename='思科文档.pdf',
            file_path='/tmp/cisco.pdf',
            vendor='思科',
            user_id=sample_user.id
        )

        database.session.add_all([doc1, doc2])
        database.session.commit()

        # 查询华为文档
        huawei_docs = KnowledgeDocument.query.filter_by(vendor='华为').all()
        assert len(huawei_docs) >= 1
        assert doc1 in huawei_docs

        # 查询思科文档
        cisco_docs = KnowledgeDocument.query.filter_by(vendor='思科').all()
        assert len(cisco_docs) >= 1
        assert doc2 in cisco_docs

    def test_complex_join_query(self, database, sample_user):
        """测试复杂的连接查询"""
        # 创建案例和节点
        case = Case(title='连接查询测试', user_id=sample_user.id)
        database.session.add(case)
        database.session.commit()

        node = Node(
            case_id=case.id,
            type='USER_QUERY',
            title='用户问题',
            content={'category': 'network'}
        )
        database.session.add(node)
        database.session.commit()

        # 执行连接查询：查找特定用户的所有节点
        user_nodes = database.session.query(Node).join(Case).filter(
            Case.user_id == sample_user.id
        ).all()

        assert len(user_nodes) >= 1
        assert node in user_nodes
