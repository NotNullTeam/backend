"""
IP智慧解答专家系统 - 混合检索算法测试

本模块测试混合检索算法的功能。
"""

import pytest
from unittest.mock import Mock, patch
from app.services.retrieval.hybrid_retrieval import HybridRetrieval, SearchResult, search_knowledge


@pytest.mark.hybrid_retrieval
class TestHybridRetrieval:
    """混合检索算法测试类"""

    def setup_method(self):
        """测试设置"""
        self.retrieval = HybridRetrieval(
            vector_weight=0.7,
            keyword_weight=0.3,
            rerank_top_k=20,
            final_top_k=10
        )

    def test_init(self):
        """测试初始化"""
        assert self.retrieval.vector_weight == 0.7
        assert self.retrieval.keyword_weight == 0.3
        assert self.retrieval.rerank_top_k == 20
        assert self.retrieval.final_top_k == 10

    def test_extract_keywords(self):
        """测试关键词提取"""
        query = "OSPF邻居建立失败，华为路由器配置问题"
        keywords = self.retrieval._extract_keywords(query)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # 应该提取到技术术语
        assert any('OSPF' in keyword for keyword in keywords)

    def test_extract_tech_terms(self):
        """测试技术术语提取"""
        query = "配置OSPF和BGP协议，使用华为设备"
        terms = self.retrieval._extract_tech_terms(query)

        assert 'OSPF' in terms
        assert 'BGP' in terms
        assert '华为' in terms

    def test_is_tech_term(self):
        """测试技术术语判断"""
        assert self.retrieval._is_tech_term('OSPF') == True
        assert self.retrieval._is_tech_term('BGP') == True
        assert self.retrieval._is_tech_term('华为') == True
        assert self.retrieval._is_tech_term('普通词汇') == False

    def test_calculate_keyword_score(self):
        """测试关键词评分"""
        keywords = ['OSPF', '配置']
        document = {
            'content': '这是一个关于OSPF配置的文档，详细介绍了OSPF协议的配置方法',
            'title': 'OSPF配置指南'
        }

        score = self.retrieval._calculate_keyword_score(keywords, document)
        assert score > 0

    def test_has_query_terms_in_title(self):
        """测试标题匹配"""
        query = "OSPF配置"
        title = "OSPF协议配置指南"

        assert self.retrieval._has_query_terms_in_title(query, title) == True

        title2 = "BGP路由配置"
        assert self.retrieval._has_query_terms_in_title(query, title2) == False

    def test_has_vendor_match(self):
        """测试厂商匹配"""
        query = "华为路由器OSPF配置"
        vendor = "华为"

        assert self.retrieval._has_vendor_match(query, vendor) == True

        vendor2 = "思科"
        assert self.retrieval._has_vendor_match(query, vendor2) == False

    def test_calculate_quality_score(self):
        """测试质量评分"""
        result = SearchResult(
            content="这是一个详细的配置指南，包含以下步骤：1. 基础配置 2. 高级配置。在实际部署中，需要仔细考虑各种配置参数和网络环境因素。",
            title="配置指南",
            score=1.0,
            source_type="vector",
            document_id="doc1",
            chunk_id="chunk1",
            metadata={}
        )

        score = self.retrieval._calculate_quality_score(result)
        assert score > 1.0  # 应该有加分

    @patch('app.services.retrieval.hybrid_retrieval.get_vector_service')
    def test_vector_search(self, mock_get_vector_service):
        """测试向量检索"""
        # Mock向量服务
        mock_vector_service = Mock()
        mock_vector_service.search_similar.return_value = [
            {
                'content': 'OSPF配置内容',
                'title': 'OSPF配置',
                'score': 0.9,
                'document_id': 'doc1',
                'chunk_id': 'chunk1',
                'metadata': {'category': '路由协议'}
            }
        ]
        mock_get_vector_service.return_value = mock_vector_service

        # 重新初始化retrieval以使用mock
        retrieval = HybridRetrieval()
        retrieval.vector_service = mock_vector_service

        results = retrieval._vector_search("OSPF配置")

        assert len(results) == 1
        assert results[0].content == 'OSPF配置内容'
        assert results[0].source_type == 'vector'

    def test_fuse_results(self):
        """测试结果融合"""
        vector_results = [
            SearchResult(
                content="内容1", title="标题1", score=0.8, source_type="vector",
                document_id="doc1", chunk_id="chunk1", metadata={}
            )
        ]

        keyword_results = [
            SearchResult(
                content="内容2", title="标题2", score=0.6, source_type="keyword",
                document_id="doc2", chunk_id="chunk2", metadata={}
            ),
            SearchResult(
                content="内容1", title="标题1", score=0.7, source_type="keyword",
                document_id="doc1", chunk_id="chunk1", metadata={}
            )
        ]

        fused = self.retrieval._fuse_results(vector_results, keyword_results, "测试查询")

        # 应该有两个结果，其中一个是融合的
        assert len(fused) == 2

        # 找到融合的结果
        fused_result = next((r for r in fused if r.source_type == 'hybrid'), None)
        assert fused_result is not None
        assert fused_result.document_id == "doc1"


@pytest.mark.hybrid_retrieval
class TestSearchKnowledge:
    """知识检索函数测试"""

    @patch('app.services.retrieval.hybrid_retrieval.HybridRetrieval')
    def test_search_knowledge(self, mock_hybrid_retrieval_class):
        """测试便捷检索函数"""
        # Mock检索结果
        mock_retrieval = Mock()
        mock_retrieval.search.return_value = [
            SearchResult(
                content="测试内容",
                title="测试标题",
                score=0.8,
                source_type="hybrid",
                document_id="doc1",
                chunk_id="chunk1",
                metadata={'category': '测试'},
                relevance_explanation="测试匹配"
            )
        ]
        mock_hybrid_retrieval_class.return_value = mock_retrieval

        results = search_knowledge("测试查询", top_k=5)

        assert len(results) == 1
        assert results[0]['content'] == "测试内容"
        assert results[0]['score'] == 0.8
        assert results[0]['source_type'] == "hybrid"


@pytest.mark.hybrid_retrieval
class TestSearchSuggestions:
    """搜索建议测试"""

    def test_generate_search_suggestions_ospf(self):
        """测试OSPF相关建议"""
        from app.api.v1.knowledge.search import _generate_search_suggestions

        suggestions = _generate_search_suggestions("OSPF", 5)

        assert len(suggestions) <= 5
        assert any('OSPF' in s for s in suggestions)

    def test_generate_search_suggestions_generic(self):
        """测试通用建议"""
        from app.api.v1.knowledge.search import _generate_search_suggestions

        suggestions = _generate_search_suggestions("未知技术", 5)

        assert len(suggestions) <= 5
        assert any('未知技术' in s for s in suggestions)


if __name__ == '__main__':
    pytest.main([__file__])
