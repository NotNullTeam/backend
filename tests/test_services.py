"""
IP智慧解答专家系统 - 服务测试

本模块测试各种服务功能。
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from app.services.document_service import parse_document, _simple_text_extraction, _simple_text_split
from app.services.agent_service import analyze_user_query, process_user_response
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.case import Case, Node
from app import db


class TestDocumentService:
    """文档服务测试类"""

    def test_simple_text_extraction_txt(self, app):
        """测试文本文件提取"""
        with app.app_context():
            # 创建临时文本文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('这是测试文档内容\n包含多行文本')
                temp_path = f.name

            try:
                result = _simple_text_extraction(temp_path)
                assert result['format'] == 'text'
                assert '这是测试文档内容' in result['content']
                assert '包含多行文本' in result['content']
            finally:
                os.unlink(temp_path)

    def test_simple_text_extraction_unsupported(self, app):
        """测试不支持的文件格式"""
        with app.app_context():
            with tempfile.NamedTemporaryFile(suffix='.unknown', delete=False) as f:
                temp_path = f.name

            try:
                result = _simple_text_extraction(temp_path)
                assert '不支持的文件格式' in result['content']
            finally:
                os.unlink(temp_path)

    def test_simple_text_split(self, app):
        """测试简单文本切分"""
        with app.app_context():
            # 创建测试文档对象
            document = KnowledgeDocument(
                id='test-doc',
                filename='test.txt',
                original_filename='test.txt',
                file_path='/tmp/test.txt',
                user_id=1
            )

            parsed_result = {
                'content': '这是第一句话。这是第二句话。这是第三句话。这是第四句话。'
            }

            chunks = _simple_text_split(parsed_result, document, chunk_size=20)

            assert len(chunks) > 1
            assert all('text' in chunk for chunk in chunks)
            assert all('metadata' in chunk for chunk in chunks)
            assert all(chunk['metadata']['document_id'] == 'test-doc' for chunk in chunks)

    @patch('app.services.document_service.IDPService')
    @patch('app.services.document_service.SemanticSplitter')
    @patch('app.services.document_service.VectorService')
    def test_parse_document_success(self, mock_vector, mock_splitter, mock_idp, app, test_document):
        """测试文档解析成功"""
        with app.app_context():
            # 创建解析任务
            job = ParsingJob(document_id=test_document.id)
            db.session.add(job)
            db.session.commit()

            # 配置模拟对象
            mock_idp_instance = MagicMock()
            mock_idp_instance.parse_document.return_value = {
                'content': '测试内容',
                'format': 'text'
            }
            mock_idp.return_value = mock_idp_instance

            mock_splitter_instance = MagicMock()
            mock_splitter_instance.split_document.return_value = [
                {'text': 'chunk1', 'metadata': {}},
                {'text': 'chunk2', 'metadata': {}}
            ]
            mock_splitter.return_value = mock_splitter_instance

            mock_vector_instance = MagicMock()
            mock_vector.return_value = mock_vector_instance

            # 执行解析
            parse_document(job.id)

            # 验证结果
            updated_job = ParsingJob.query.get(job.id)
            updated_doc = KnowledgeDocument.query.get(test_document.id)

            assert updated_job.status == 'COMPLETED'
            assert updated_doc.status == 'INDEXED'
            assert updated_doc.progress == 100
            assert updated_doc.processed_at is not None

    def test_parse_document_job_not_found(self, app):
        """测试解析任务不存在"""
        with app.app_context():
            # 应该不会抛出异常，只是记录错误日志
            parse_document('nonexistent-job-id')

    @patch('app.services.document_service.IDPService')
    def test_parse_document_idp_failure(self, mock_idp, app, test_document):
        """测试IDP服务失败时的处理"""
        with app.app_context():
            job = ParsingJob(document_id=test_document.id)
            db.session.add(job)
            db.session.commit()

            # 模拟IDP服务失败
            mock_idp.side_effect = Exception("IDP service error")

            # 执行解析（应该使用简单文本提取作为后备）
            parse_document(job.id)

            # 验证仍然完成了解析
            updated_job = ParsingJob.query.get(job.id)
            updated_doc = KnowledgeDocument.query.get(test_document.id)

            assert updated_job.status == 'COMPLETED'
            assert updated_doc.status == 'INDEXED'


class TestAgentService:
    """Agent服务测试类"""

    def test_analyze_user_query_success(self, app, test_case):
        """测试用户查询分析成功"""
        with app.app_context():
            # 创建AI节点
            ai_node = Node(
                case_id=test_case.id,
                type='AI_ANALYSIS',
                title='AI分析中...',
                status='PROCESSING'
            )
            db.session.add(ai_node)
            db.session.commit()

            # 执行分析
            analyze_user_query(test_case.id, ai_node.id, '我的路由器无法连接')

            # 验证结果
            updated_node = Node.query.get(ai_node.id)
            assert updated_node.status == 'COMPLETED'
            assert updated_node.title == 'AI分析完成'
            assert updated_node.content is not None
            assert 'analysis' in updated_node.content

    def test_analyze_user_query_node_not_found(self, app):
        """测试节点不存在的情况"""
        with app.app_context():
            # 应该不会抛出异常，只是记录错误日志
            analyze_user_query('case-id', 'nonexistent-node-id', 'query')

    def test_process_user_response_answers(self, app, test_case):
        """测试处理用户回答"""
        with app.app_context():
            ai_node = Node(
                case_id=test_case.id,
                type='AI_ANALYSIS',
                title='AI处理中...',
                status='PROCESSING'
            )
            db.session.add(ai_node)
            db.session.commit()

            response_data = {
                'type': 'answers',
                'answers': {
                    '设备型号': 'Router-X1000',
                    '问题时间': '昨天'
                }
            }

            # 执行处理
            process_user_response(test_case.id, ai_node.id, response_data)

            # 验证结果
            updated_node = Node.query.get(ai_node.id)
            assert updated_node.status == 'COMPLETED'
            assert updated_node.content['type'] == 'solution'
            assert 'solutions' in updated_node.content

    def test_process_user_response_clarification(self, app, test_case):
        """测试处理澄清请求"""
        with app.app_context():
            ai_node = Node(
                case_id=test_case.id,
                type='AI_ANALYSIS',
                status='PROCESSING'
            )
            db.session.add(ai_node)
            db.session.commit()

            response_data = {
                'type': 'clarification',
                'clarification': '什么是VLAN？'
            }

            process_user_response(test_case.id, ai_node.id, response_data)

            updated_node = Node.query.get(ai_node.id)
            assert updated_node.status == 'COMPLETED'
            assert updated_node.content['type'] == 'clarification'
            assert 'explanation' in updated_node.content

    def test_process_user_response_general(self, app, test_case):
        """测试处理通用响应"""
        with app.app_context():
            ai_node = Node(
                case_id=test_case.id,
                type='AI_ANALYSIS',
                status='PROCESSING'
            )
            db.session.add(ai_node)
            db.session.commit()

            response_data = {
                'text': '我已经尝试了重启，但问题依然存在'
            }

            process_user_response(test_case.id, ai_node.id, response_data)

            updated_node = Node.query.get(ai_node.id)
            assert updated_node.status == 'COMPLETED'
            assert updated_node.content['type'] == 'analysis'
            assert 'recommendations' in updated_node.content
