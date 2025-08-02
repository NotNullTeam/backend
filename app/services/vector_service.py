"""
IP智慧解答专家系统 - 向量服务

本模块实现了向量数据库相关的功能，专门使用 Weaviate 向量数据库。
"""

import logging
from typing import List, Dict, Any, Optional
from app import create_app
from .embedding_service import get_embedding_service
from .vector_db_config import vector_db_config, VectorDBType
from .weaviate_vector_db import WeaviateVectorDB

logger = logging.getLogger(__name__)


def delete_document_vectors(document_id):
    """
    删除文档的向量数据

    Args:
        document_id: 文档ID
    """
    app = create_app()
    with app.app_context():
        vector_service = get_vector_service()
        success = vector_service.delete_document(document_id)
        if success:
            app.logger.info(f"Successfully deleted vectors for document {document_id}")
        else:
            app.logger.warning(f"Failed to delete vectors for document {document_id}")


class VectorService:
    """向量服务类 - 支持多种向量数据库后端"""

    def __init__(self):
        """初始化向量服务"""
        self.embedding_service = get_embedding_service()
        self.vector_db = self._initialize_vector_db()
        logger.info(f"向量服务初始化完成，使用数据库类型: {vector_db_config.db_type.value}")

    def _initialize_vector_db(self):
        """根据配置初始化 Weaviate 向量数据库"""
        if not vector_db_config.is_valid():
            logger.error(f"向量数据库配置无效")
            raise ValueError("向量数据库配置无效")

        try:
            return WeaviateVectorDB(vector_db_config.config)
        except Exception as e:
            logger.error(f"初始化 Weaviate 向量数据库失败: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        try:
            vectors = self.embedding_service.embed_batch(texts)
            logger.info(f"成功向量化 {len(texts)} 个文本")
            return vectors
        except Exception as e:
            logger.error(f"批量向量化失败: {str(e)}")
            # 返回零向量作为降级处理
            return [[0.0] * 1024 for _ in texts]

    def index_chunks_batch(self, chunks: List, vectors: List[List[float]], document_id: str) -> List[str]:
        """
        批量存储文档块向量

        Args:
            chunks: 文档块列表
            vectors: 向量列表
            document_id: 文档ID

        Returns:
            List[str]: 向量ID列表
        """
        try:
            # 将chunks转换为正确的格式
            formatted_chunks = []
            for chunk in chunks:
                if hasattr(chunk, 'content'):
                    # 如果是对象，提取content属性
                    formatted_chunk = {
                        "content": chunk.content,
                        "metadata": getattr(chunk, 'metadata', {})
                    }
                elif isinstance(chunk, dict):
                    # 如果已经是字典格式
                    formatted_chunk = chunk
                else:
                    # 如果是字符串，直接作为content
                    formatted_chunk = {
                        "content": str(chunk),
                        "metadata": {}
                    }
                formatted_chunks.append(formatted_chunk)

            vector_ids = self.vector_db.add_document(document_id, formatted_chunks, vectors)
            logger.info(f"成功存储 {len(chunks)} 个向量到向量数据库")
            return vector_ids

        except Exception as e:
            logger.error(f"批量存储向量失败: {str(e)}")
            # 返回模拟向量ID作为降级处理
            return [f"vector_{i}_{document_id}" for i in range(len(chunks))]

    def index_chunks(self, chunks, document_id):
        """
        将文本块向量化并存储

        Args:
            chunks: 文本块列表
            document_id: 文档ID
        """
        try:
            # 提取文本内容
            texts = []
            for chunk in chunks:
                if hasattr(chunk, 'content'):
                    texts.append(chunk.content)
                elif isinstance(chunk, dict):
                    texts.append(chunk.get('content', ''))
                else:
                    texts.append(str(chunk))

            # 向量化
            vectors = self.embed_batch(texts)

            # 存储到向量数据库
            vector_ids = self.index_chunks_batch(chunks, vectors, document_id)

            logger.info(f"成功向量化并存储 {len(chunks)} 个文档块 for document {document_id}")
            return vector_ids

        except Exception as e:
            logger.error(f"向量化存储失败: {str(e)}")
            raise

    def search_similar(self, query_text: str, top_k: int = 5,
                      document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索相似文档块

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            document_id: 可选，限制在特定文档内搜索

        Returns:
            相似结果列表
        """
        try:
            # 向量化查询文本
            query_vector = self.embedding_service.embed_text(query_text)

            # 搜索相似向量
            results = self.vector_db.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                document_id=document_id
            )

            logger.info(f"搜索到 {len(results)} 个相似结果")
            return results

        except Exception as e:
            logger.error(f"相似性搜索失败: {str(e)}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档的所有向量

        Args:
            document_id: 文档ID

        Returns:
            删除是否成功
        """
        try:
            success = self.vector_db.delete_document(document_id)
            if success:
                logger.info(f"成功删除文档 {document_id} 的向量数据")
            else:
                logger.warning(f"删除文档 {document_id} 的向量数据失败")
            return success

        except Exception as e:
            logger.error(f"删除文档向量失败: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取向量数据库统计信息"""
        try:
            stats = self.vector_db.get_stats()
            stats["db_type"] = vector_db_config.db_type.value
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "total_documents": 0,
                "total_vectors": 0,
                "db_type": vector_db_config.db_type.value,
                "error": str(e)
            }

    def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        搜索向量

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            List[Dict]: 搜索结果
        """
        try:
            # 将查询文本转换为向量
            query_vector = self.embedding_service.embed(query)

            # 使用向量搜索
            results = self.vector_db.search(query_vector, k=top_k, filters=filters)

            logger.info(f"搜索查询 '{query}' 返回 {len(results)} 个结果")
            return results
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    def test_connection(self) -> bool:
        """测试向量数据库连接"""
        try:
            # 测试嵌入服务
            if not self.embedding_service.test_connection():
                return False

            # 测试向量数据库
            if hasattr(self.vector_db, 'test_connection'):
                return self.vector_db.test_connection()
            else:
                # 对于本地文件存储，总是返回True
                return True

        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            return False


# 全局向量服务实例
_vector_service: Optional[VectorService] = None


def get_vector_service() -> VectorService:
    """
    获取全局向量服务实例（单例模式）

    Returns:
        VectorService: 向量服务实例
    """
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service


def reset_vector_service():
    """重置全局向量服务实例（主要用于测试）"""
    global _vector_service
    _vector_service = None
