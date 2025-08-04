"""
检索服务模块

包含所有检索相关的服务：
- 向量服务：向量数据库操作
- 混合检索：结合多种检索策略
- 知识检索服务：统一的知识检索接口
"""

from .vector_service import VectorService, get_vector_service, delete_document_vectors
from .hybrid_retrieval import get_hybrid_retrieval, search_knowledge
from .knowledge_service import knowledge_service

__all__ = [
    'VectorService',
    'get_vector_service',
    'delete_document_vectors',
    'get_hybrid_retrieval',
    'search_knowledge',
    'knowledge_service'
]
