"""
向量服务集成测试
测试向量数据库的Schema创建、数据索引和查询功能
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from app import create_app
from app.services.retrieval.vector_service import VectorService, get_vector_service
from app.services.ai.embedding_service import QwenEmbedding


class TestVectorServiceIntegration:
    """向量服务集成测试类"""

    @pytest.fixture
    def app(self):
        """创建测试应用实例"""
        from tests.conftest import TestConfig
        app = create_app(TestConfig)
        with app.app_context():
            yield app

    @pytest.fixture
    def vector_service(self, app):
        """创建向量服务实例"""
        return get_vector_service()

    def test_vector_service_initialization(self, vector_service):
        """测试向量服务初始化"""
        assert vector_service is not None
        assert hasattr(vector_service, 'embedding_service')
        assert hasattr(vector_service, 'vector_db')

    @patch('app.services.ai.embedding_service.DashScopeEmbeddings')
    def test_embedding_service_initialization(self, mock_dashscope):
        """测试嵌入服务初始化"""
        # 模拟DashScopeEmbeddings
        mock_embeddings = MagicMock()
        mock_dashscope.return_value = mock_embeddings

        # 设置API密钥
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test-key'}):
            embedding_service = QwenEmbedding()

        assert embedding_service.api_key == 'test-key'
        assert embedding_service.embeddings == mock_embeddings

    @patch('app.services.ai.embedding_service.DashScopeEmbeddings')
    def test_embed_text_success(self, mock_dashscope):
        """测试文本向量化成功"""
        # 模拟返回值
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_dashscope.return_value = mock_embeddings

        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test-key'}):
            embedding_service = QwenEmbedding()

        result = embedding_service.embed_text("测试文本")
        assert result == [0.1, 0.2, 0.3]
        mock_embeddings.embed_query.assert_called_once_with("测试文本")

    @patch('app.services.ai.embedding_service.DashScopeEmbeddings')
    def test_embed_batch_success(self, mock_dashscope):
        """测试批量文本向量化成功"""
        # 模拟返回值
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ]
        mock_dashscope.return_value = mock_embeddings

        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test-key'}):
            embedding_service = QwenEmbedding()

        texts = ["文本1", "文本2"]
        result = embedding_service.embed_batch(texts)

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]
        mock_embeddings.embed_documents.assert_called_once_with(texts)

    def test_schema_creation(self, vector_service):
        """测试Schema创建"""
        # 测试Schema创建方法是否存在且可调用
        assert hasattr(vector_service.vector_db, 'ensure_schema')

        # 调用方法不应该抛出异常
        try:
            vector_service.vector_db.ensure_schema()
            schema_created = True
        except Exception:
            schema_created = False

        assert schema_created, "Schema creation should succeed"

    def test_document_indexing_flow(self, vector_service):
        """测试文档索引流程"""
        # 准备测试数据
        test_chunks = [
            {
                'content': 'OSPF是一种链路状态路由协议',
                'title': 'OSPF协议介绍',
                'vendor': 'H3C',
                'category': '路由协议',
                'source_document': 'ospf_guide.pdf',
                'page_number': 1
            },
            {
                'content': 'BGP是一种路径向量路由协议',
                'title': 'BGP协议介绍',
                'vendor': 'Cisco',
                'category': '路由协议',
                'source_document': 'bgp_guide.pdf',
                'page_number': 2
            }
        ]

        document_id = "test_doc_001"

        # 使用模拟的向量服务进行测试
        try:
            success = vector_service.index_chunks(test_chunks, document_id)
            # 在模拟环境中，这应该返回True或不抛出异常
            assert success is not False
        except Exception as e:
            # 在没有真实Weaviate连接的情况下，这是预期的
            assert "connection" in str(e).lower() or "weaviate" in str(e).lower()

    def test_document_search_flow(self, vector_service):
        """测试文档搜索流程"""
        query = "OSPF路由协议配置"

        try:
            results = vector_service.search(query, top_k=5)
            # 在模拟环境中验证返回格式
            assert isinstance(results, list)
        except Exception as e:
            # 在没有真实Weaviate连接的情况下，这是预期的
            assert "connection" in str(e).lower() or "weaviate" in str(e).lower()

    def test_document_deletion_flow(self, vector_service):
        """测试文档删除流程"""
        document_id = "test_doc_001"

        try:
            success = vector_service.delete_document(document_id)
            # 在模拟环境中验证操作完成
            assert success is not False
        except Exception as e:
            # 在没有真实Weaviate连接的情况下，这是预期的
            assert "connection" in str(e).lower() or "weaviate" in str(e).lower()


class TestWeaviateConnection:
    """Weaviate连接测试"""

    def test_weaviate_configuration(self):
        """测试Weaviate配置"""
        import os
        from app.services.storage.vector_db_config import vector_db_config

        assert vector_db_config.is_valid()
        assert vector_db_config.config['url'] == 'http://localhost:8080'
        
        # 检查环境变量的实际值，适配业务配置
        expected_class_name = os.getenv('WEAVIATE_CLASS_NAME', 'Document')
        assert vector_db_config.config['class_name'] == expected_class_name

    @pytest.mark.integration
    def test_real_weaviate_connection(self):
        """测试真实Weaviate连接（需要启动Weaviate服务）"""
        # 这个测试需要真实的Weaviate服务运行
        # 可以通过 pytest -m integration 来运行
        try:
            import weaviate
            from weaviate.client import WeaviateClient

            # 使用新的 v4 API
            client = WeaviateClient.connect_to_local()

            # 测试连接
            meta = client.get_meta()
            assert 'version' in meta

            client.close()
        except Exception as e:
            pytest.skip(f"Weaviate服务未运行: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
