"""
IP智慧解答专家系统 - 嵌入服务

本模块实现了文本向量化功能，集成阿里云百炼平台的text-embedding-v4模型。
"""

import os
import logging
from typing import List, Optional
from langchain_community.embeddings import DashScopeEmbeddings

logger = logging.getLogger(__name__)


class QwenEmbedding:
    """Qwen向量化服务"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化Qwen向量化服务

        Args:
            api_key: DashScope API密钥，如果不提供则从环境变量获取
        """
        self.api_key = api_key or os.environ.get('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY环境变量未设置或api_key参数未提供")

        try:
            # 使用Langchain集成的DashScope向量模型
            self.embeddings = DashScopeEmbeddings(
                model="text-embedding-v4",
                dashscope_api_key=self.api_key
            )
            logger.info("Qwen向量化服务初始化成功")
        except Exception as e:
            logger.error(f"Qwen向量化服务初始化失败: {str(e)}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """
        单个文本向量化

        Args:
            text: 待向量化的文本

        Returns:
            List[float]: 文本向量

        Raises:
            Exception: 向量化失败时抛出异常
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回零向量")
            return [0.0] * 1024  # text-embedding-v4实际维度

        try:
            vector = self.embeddings.embed_query(text)
            logger.debug(f"文本向量化成功，向量维度: {len(vector)}")
            return vector
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise Exception(f"向量化失败: {str(e)}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 待向量化的文本列表

        Returns:
            List[List[float]]: 文本向量列表
        """
        if not texts:
            logger.warning("输入文本列表为空")
            return []

        try:
            vectors = self.embeddings.embed_documents(texts)
            logger.info(f"批量向量化成功，处理了 {len(texts)} 个文本")
            return vectors
        except Exception as e:
            logger.error(f"批量向量化失败，降级到单个处理: {str(e)}")
            # 降级到单个处理
            embeddings = []
            for i, text in enumerate(texts):
                try:
                    vector = self.embed_text(text)
                    embeddings.append(vector)
                except Exception as single_error:
                    logger.error(f"第 {i+1} 个文本向量化失败: {single_error}")
                    embeddings.append([0.0] * 1024)  # 实际维度，使用零向量
            return embeddings

    def get_dimension(self) -> int:
        """
        获取向量维度

        Returns:
            int: 向量维度
        """
        return 1024  # text-embedding-v4的实际向量维度

    def test_connection(self) -> bool:
        """
        测试向量化服务连接

        Returns:
            bool: 连接是否正常
        """
        try:
            # 测试向量化一个简单文本
            test_vector = self.embed_text("测试连接")
            return len(test_vector) > 0
        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            return False


# 全局嵌入服务实例
_embedding_service: Optional[QwenEmbedding] = None


def get_embedding_service() -> QwenEmbedding:
    """
    获取全局嵌入服务实例（单例模式）

    Returns:
        QwenEmbedding: 嵌入服务实例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = QwenEmbedding()
    return _embedding_service


def reset_embedding_service():
    """重置全局嵌入服务实例（主要用于测试）"""
    global _embedding_service
    _embedding_service = None
