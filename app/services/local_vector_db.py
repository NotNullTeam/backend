"""
本地文件向量数据库实现
使用JSON文件存储向量数据，支持基本的CRUD和相似度搜索
"""
import os
import json
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalFileVectorDB:
    """本地文件向量数据库"""

    def __init__(self, storage_path: str = "instance/vectors"):
        """
        初始化本地文件向量数据库

        Args:
            storage_path: 存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 存储文件路径
        self.metadata_file = self.storage_path / "metadata.json"
        self.vectors_file = self.storage_path / "vectors.pkl"
        self.index_file = self.storage_path / "index.json"

        # 内存中的数据
        self.metadata = self._load_metadata()
        self.vectors = self._load_vectors()
        self.index = self._load_index()

        logger.info(f"LocalFileVectorDB initialized at {self.storage_path}")

    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {
            "total_documents": 0,
            "total_vectors": 0,
            "dimension": 1536,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

    def _load_vectors(self) -> Dict[str, List[float]]:
        """加载向量数据"""
        if self.vectors_file.exists():
            try:
                with open(self.vectors_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading vectors: {e}")
        return {}

    def _load_index(self) -> Dict[str, Any]:
        """加载索引数据"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading index: {e}")
        return {}

    def _save_metadata(self):
        """保存元数据"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def _save_vectors(self):
        """保存向量数据"""
        with open(self.vectors_file, 'wb') as f:
            pickle.dump(self.vectors, f)

    def _save_index(self):
        """保存索引数据"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def add_document(self, document_id: str, chunks: List[Dict[str, Any]],
                    vectors: List[List[float]]) -> List[str]:
        """
        添加文档的向量数据

        Args:
            document_id: 文档ID
            chunks: 文档块列表，每个块包含内容和元数据
            vectors: 对应的向量列表

        Returns:
            向量ID列表
        """
        if len(chunks) != len(vectors):
            raise ValueError("Chunks and vectors must have the same length")

        vector_ids = []

        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            vector_id = f"{document_id}_chunk_{i}_{datetime.now().timestamp()}"
            vector_ids.append(vector_id)

            # 存储向量
            self.vectors[vector_id] = vector

            # 存储索引信息
            self.index[vector_id] = {
                "document_id": document_id,
                "chunk_index": i,
                "content": chunk.get("content", ""),
                "metadata": chunk.get("metadata", {}),
                "created_at": datetime.now().isoformat()
            }

        # 更新元数据
        self.metadata["total_vectors"] += len(vectors)
        if document_id not in [item.get("document_id") for item in self.index.values()]:
            self.metadata["total_documents"] += 1

        # 保存到文件
        self._save_metadata()
        self._save_vectors()
        self._save_index()

        logger.info(f"Added {len(vectors)} vectors for document {document_id}")
        return vector_ids

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档的所有向量

        Args:
            document_id: 文档ID

        Returns:
            删除是否成功
        """
        try:
            # 找到所有相关的向量ID
            vector_ids_to_delete = [
                vid for vid, info in self.index.items()
                if info.get("document_id") == document_id
            ]

            if not vector_ids_to_delete:
                logger.warning(f"No vectors found for document {document_id}")
                return False

            # 删除向量和索引
            for vector_id in vector_ids_to_delete:
                self.vectors.pop(vector_id, None)
                self.index.pop(vector_id, None)

            # 更新元数据
            self.metadata["total_vectors"] -= len(vector_ids_to_delete)
            self.metadata["total_documents"] -= 1

            # 保存到文件
            self._save_metadata()
            self._save_vectors()
            self._save_index()

            logger.info(f"Deleted {len(vector_ids_to_delete)} vectors for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def search_similar(self, query_vector: List[float], top_k: int = 5,
                      document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索相似向量

        Args:
            query_vector: 查询向量
            top_k: 返回的结果数量
            document_id: 可选，限制在特定文档内搜索

        Returns:
            相似结果列表，每个结果包含向量ID、相似度分数和元数据
        """
        if not self.vectors:
            return []

        similarities = []
        query_vec = np.array(query_vector)

        for vector_id, vector in self.vectors.items():
            # 如果指定了文档ID，只搜索该文档的向量
            if document_id and self.index[vector_id].get("document_id") != document_id:
                continue

            # 计算余弦相似度
            doc_vec = np.array(vector)
            similarity = self._cosine_similarity(query_vec, doc_vec)

            similarities.append({
                "vector_id": vector_id,
                "similarity": similarity,
                "content": self.index[vector_id].get("content", ""),
                "metadata": self.index[vector_id].get("metadata", {}),
                "document_id": self.index[vector_id].get("document_id"),
                "chunk_index": self.index[vector_id].get("chunk_index")
            })

        # 按相似度排序并返回top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        return {
            "total_documents": self.metadata.get("total_documents", 0),
            "total_vectors": self.metadata.get("total_vectors", 0),
            "dimension": self.metadata.get("dimension", 1536),
            "storage_path": str(self.storage_path),
            "created_at": self.metadata.get("created_at"),
            "last_updated": self.metadata.get("last_updated")
        }

    def clear_all(self):
        """清空所有数据"""
        self.vectors = {}
        self.index = {}
        self.metadata = {
            "total_documents": 0,
            "total_vectors": 0,
            "dimension": 1536,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        # 删除文件
        for file_path in [self.metadata_file, self.vectors_file, self.index_file]:
            if file_path.exists():
                file_path.unlink()

        logger.info("Cleared all vector data")
