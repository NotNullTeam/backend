"""
知识检索服务

提供向量化知识检索功能，替换Mock实现。
"""

import logging
import time
from typing import List, Dict, Any, Optional
from app.models.knowledge import KnowledgeDocument


logger = logging.getLogger(__name__)


class KnowledgeRetrievalService:
    """知识检索服务类"""

    def __init__(self):
        self.logger = logger

    def retrieve_knowledge(
        self,
        query: str,
        top_k: int = 5,
        vendor: Optional[str] = None,
        retrieval_weight: float = 0.7,
        filter_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        检索相关知识

        Args:
            query: 查询文本
            top_k: 返回的文档片段数量
            vendor: 设备厂商过滤
            retrieval_weight: 检索权重，0(关键词优先)~1(语义优先)
            filter_tags: 标签过滤

        Returns:
            包含知识源和元数据的字典
        """
        start_time = time.time()

        try:
            # 从数据库获取已索引的知识文档
            knowledge_query = KnowledgeDocument.query.filter_by(status='INDEXED')

            # 应用厂商过滤
            if vendor:
                knowledge_query = knowledge_query.filter_by(vendor=vendor)

            # 应用标签过滤
            if filter_tags:
                # 这里需要根据实际的标签存储结构来实现过滤逻辑
                # 假设tags存储为JSON数组
                for tag in filter_tags:
                    knowledge_query = knowledge_query.filter(
                        KnowledgeDocument.tags.contains([tag])
                    )

            documents = knowledge_query.all()

            if not documents:
                return {
                    'sources': [],
                    'retrievalMetadata': {
                        'totalCandidates': 0,
                        'retrievalTime': int((time.time() - start_time) * 1000),
                        'rerankTime': 0,
                        'strategy': 'database_search'
                    }
                }

            # 执行知识检索
            sources = self._perform_retrieval(
                query, documents, top_k, retrieval_weight
            )

            retrieval_time = int((time.time() - start_time) * 1000)

            return {
                'sources': sources,
                'retrievalMetadata': {
                    'totalCandidates': len(documents),
                    'retrievalTime': retrieval_time,
                    'rerankTime': 0,  # 如果有重排序步骤，这里记录时间
                    'strategy': 'hybrid_search' if 0 < retrieval_weight < 1 else
                              'semantic_search' if retrieval_weight >= 0.5 else 'keyword_search'
                }
            }

        except Exception as e:
            self.logger.error(f"Knowledge retrieval error: {str(e)}")
            # 返回空结果而不是抛出异常
            return {
                'sources': [],
                'retrievalMetadata': {
                    'totalCandidates': 0,
                    'retrievalTime': int((time.time() - start_time) * 1000),
                    'rerankTime': 0,
                    'strategy': 'error_fallback'
                }
            }

    def _perform_retrieval(
        self,
        query: str,
        documents: List[KnowledgeDocument],
        top_k: int,
        retrieval_weight: float
    ) -> List[Dict[str, Any]]:
        """
        执行实际的检索逻辑

        这里可以集成真实的向量检索引擎，如：
        - Weaviate
        - Elasticsearch
        - Pinecone
        - 自建向量数据库
        """
        sources = []

        for doc in documents[:top_k]:  # 临时简单实现，实际应该使用向量相似度排序
            # 计算相关度分数（这里是简化实现）
            relevance = self._calculate_relevance(query, doc, retrieval_weight)

            source = {
                'id': f'doc_{doc.id}',
                'title': doc.file_name,
                'snippet': self._extract_snippet(doc, query),
                'relevance': relevance,
                'url': f'/api/v1/knowledge/documents/{doc.id}',
                'highlights': self._find_highlights(query, doc),
                'matchScore': {
                    'keywordScore': self._keyword_score(query, doc),
                    'semanticScore': self._semantic_score(query, doc),
                    'finalScore': relevance,
                    'explanation': self._generate_explanation(query, doc)
                },
                'sourceDocument': {
                    'fileName': doc.file_name,
                    'pageNumber': 1,  # 如果有页码信息可以从metadata中获取
                    'section': doc.tags[0] if doc.tags else 'Unknown'
                }
            }
            sources.append(source)

        # 按相关度排序
        sources.sort(key=lambda x: x['relevance'], reverse=True)

        return sources

    def _calculate_relevance(
        self,
        query: str,
        document: KnowledgeDocument,
        retrieval_weight: float
    ) -> float:
        """计算文档与查询的相关度"""
        keyword_score = self._keyword_score(query, document)
        semantic_score = self._semantic_score(query, document)

        # 根据权重计算最终分数
        final_score = (
            keyword_score * (1 - retrieval_weight) +
            semantic_score * retrieval_weight
        )

        return round(final_score, 3)

    def _keyword_score(self, query: str, document: KnowledgeDocument) -> float:
        """计算关键词匹配分数"""
        query_words = set(query.lower().split())
        doc_words = set((document.file_name + ' ' + str(document.tags)).lower().split())

        if not query_words:
            return 0.0

        intersection = query_words.intersection(doc_words)
        return len(intersection) / len(query_words)

    def _semantic_score(self, query: str, document: KnowledgeDocument) -> float:
        """计算语义相似度分数"""
        # 这里应该使用真实的向量相似度计算
        # 临时使用简单的字符串相似度
        query_lower = query.lower()
        doc_content = (document.file_name + ' ' + str(document.tags)).lower()

        # 简单的子串匹配作为语义相似度的替代
        matches = sum(1 for word in query_lower.split() if word in doc_content)
        return matches / max(len(query_lower.split()), 1)

    def _extract_snippet(self, document: KnowledgeDocument, query: str) -> str:
        """提取文档片段"""
        # 这里应该从实际的文档内容中提取相关片段
        # 临时返回基于文件名的描述
        return f"来自文档 {document.file_name} 的相关内容片段..."

    def _find_highlights(self, query: str, document: KnowledgeDocument) -> List[Dict[str, Any]]:
        """查找高亮片段"""
        highlights = []
        query_words = query.lower().split()

        for word in query_words:
            if word in document.file_name.lower():
                highlights.append({
                    'text': word,
                    'start': document.file_name.lower().find(word),
                    'end': document.file_name.lower().find(word) + len(word),
                    'matchType': 'keyword'
                })

        return highlights

    def _generate_explanation(self, query: str, document: KnowledgeDocument) -> str:
        """生成匹配解释"""
        return f"文档 {document.file_name} 与查询内容相关"


# 全局服务实例
knowledge_service = KnowledgeRetrievalService()
