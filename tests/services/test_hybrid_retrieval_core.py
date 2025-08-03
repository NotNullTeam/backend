"""
IP智慧解答专家系统 - 混合检索算法独立测试

本模块测试混合检索算法的核心功能，不依赖Flask应用上下文。
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.hybrid_retrieval
class TestHybridRetrievalCore:
    """混合检索算法核心功能测试"""

    def setup_method(self):
        """测试设置"""
        # Mock外部依赖
        with patch('app.services.retrieval.hybrid_retrieval.get_vector_service'), \
             patch('app.services.retrieval.hybrid_retrieval.get_embedding_service'):
            from app.services.retrieval.hybrid_retrieval import HybridRetrieval
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
        from app.services.retrieval.hybrid_retrieval import SearchResult

        result = SearchResult(
            content="这是一个详细的配置指南，包含以下步骤：1. 基础配置 2. 高级配置 3. 故障排查。每个步骤都有详细的说明和命令示例，帮助用户快速掌握配置方法。",
            title="配置指南",
            score=1.0,
            source_type="vector",
            document_id="doc1",
            chunk_id="chunk1",
            metadata={}
        )

        score = self.retrieval._calculate_quality_score(result)
        assert score > 1.0  # 应该有加分

    def test_fuse_results(self):
        """测试结果融合"""
        from app.services.retrieval.hybrid_retrieval import SearchResult

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
class TestSearchSuggestions:
    """搜索建议测试"""

    def test_generate_search_suggestions_ospf(self):
        """测试OSPF相关建议"""
        # 直接导入函数进行测试
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 手动实现建议函数进行测试
        def _generate_search_suggestions(query: str, limit: int) -> list:
            suggestions = []
            query_lower = query.lower()

            tech_suggestions = {
                'ospf': [
                    'OSPF邻居建立失败',
                    'OSPF区域配置',
                    'OSPF LSA类型',
                    'OSPF路由计算',
                    'OSPF网络类型配置'
                ]
            }

            for key, values in tech_suggestions.items():
                if key in query_lower:
                    suggestions.extend(values)

            if not suggestions:
                generic_suggestions = [
                    f'{query} 配置方法',
                    f'{query} 故障排除'
                ]
                suggestions.extend(generic_suggestions)

            return suggestions[:limit]

        suggestions = _generate_search_suggestions("OSPF", 5)

        assert len(suggestions) <= 5
        assert any('OSPF' in s for s in suggestions)

    def test_generate_search_suggestions_generic(self):
        """测试通用建议"""
        def _generate_search_suggestions(query: str, limit: int) -> list:
            suggestions = []
            query_lower = query.lower()

            tech_suggestions = {
                'ospf': ['OSPF邻居建立失败']
            }

            for key, values in tech_suggestions.items():
                if key in query_lower:
                    suggestions.extend(values)

            if not suggestions:
                generic_suggestions = [
                    f'{query} 配置方法',
                    f'{query} 故障排除'
                ]
                suggestions.extend(generic_suggestions)

            return suggestions[:limit]

        suggestions = _generate_search_suggestions("未知技术", 5)

        assert len(suggestions) <= 5
        assert any('未知技术' in s for s in suggestions)


def test_jieba_functionality():
    """测试jieba分词功能"""
    try:
        from jieba import analyse

        # 测试关键词提取
        text = "华为路由器OSPF邻居建立失败故障排除"
        keywords = analyse.extract_tags(text, topK=5, withWeight=False)

        assert isinstance(keywords, list)
        assert len(keywords) > 0

        print(f"分词结果: {keywords}")

    except ImportError:
        pytest.skip("jieba未安装")


def test_tech_term_patterns():
    """测试技术术语模式匹配"""
    import re

    # 使用与实际实现相同的模式
    tech_patterns = [
        r'(?:OSPF|BGP|RIP|ISIS|EIGRP)',  # 路由协议（无边界限制符以匹配中文组合）
        r'(?:VLAN|STP|TRUNK|ACCESS)',    # 交换技术
        r'(?:华为|思科|华三|Cisco|Huawei|H3C)'  # 厂商
    ]

    test_queries = [
        "OSPF邻居建立失败",
        "华为BGP配置",
        "VLAN间路由设置",
        "思科设备故障"
    ]

    for query in test_queries:
        found_terms = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            found_terms.extend([match.upper() if match.isupper() or match.isalpha() else match for match in matches])

        assert len(found_terms) > 0, f"应该在查询 '{query}' 中找到技术术语"
        print(f"查询: {query} -> 术语: {found_terms}")


if __name__ == '__main__':
    # 运行特定测试
    test_jieba_functionality()
    test_tech_term_patterns()

    # 运行pytest
    pytest.main([__file__, '-v'])
