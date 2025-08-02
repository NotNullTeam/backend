"""
Weaviate 向量数据库实现 (Weaviate v4 客户端)
"""
import logging
from typing import List, Dict, Any, Optional
import weaviate
import uuid

logger = logging.getLogger(__name__)


class MockWeaviateClient:
    """模拟Weaviate客户端用于开发测试"""

    def __init__(self):
        self.data_store = {}
        self.collections = MockCollections()

    def close(self):
        pass

class MockCollections:
    """模拟Collections"""

    def __init__(self):
        self.store = {}

    def exists(self, name):
        return name in self.store

    def create(self, name, description="", properties=None):
        self.store[name] = MockCollection(name)
        return self.store[name]

    def get(self, name):
        if name not in self.store:
            self.store[name] = MockCollection(name)
        return self.store[name]

    def list_all(self):
        return list(self.store.keys())

class MockCollection:
    """模拟Collection"""

    def __init__(self, name):
        self.name = name
        self.data = MockData()
        self.query = MockQuery()

class MockData:
    """模拟Data操作"""

    def __init__(self):
        self.objects = {}

    def insert(self, uuid, properties, vector):
        self.objects[uuid] = {
            'properties': properties,
            'vector': vector,
            'uuid': uuid
        }

    def delete_many(self, where):
        # 简单实现，实际应该根据where条件过滤
        deleted = len(self.objects)
        self.objects.clear()
        return type('Result', (), {'matches': deleted})()

class MockQuery:
    """模拟Query操作"""

    def __init__(self):
        pass

    def near_vector(self, near_vector, limit=5, where=None, return_metadata=None):
        # 返回模拟结果
        return type('QueryResult', (), {
            'objects': [
                type('Object', (), {
                    'properties': {
                        'content': '网络设备配置管理是网络运维的重要环节',
                        'title': '测试文档',
                        'source': 'test',
                        'doc_type': 'test',
                        'chunk_index': 0,
                        'document_id': 'test_doc'
                    },
                    'metadata': type('Metadata', (), {'score': 0.9, 'distance': 0.1})()
                })(),
                type('Object', (), {
                    'properties': {
                        'content': 'OSPF协议是一种链路状态路由协议',
                        'title': '测试文档2',
                        'source': 'test',
                        'doc_type': 'test',
                        'chunk_index': 1,
                        'document_id': 'test_doc2'
                    },
                    'metadata': type('Metadata', (), {'score': 0.8, 'distance': 0.2})()
                })()
            ][:limit]
        })()


class WeaviateVectorDB:
    """Weaviate向量数据库实现"""

    def __init__(self, config: dict):
        """
        初始化 Weaviate 客户端

        Args:
            config: 配置字典，包含连接信息
        """
        self.config = config
        self.class_name = config.get('class_name', 'Document')
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化 Weaviate 客户端"""
        try:
            # 本地 Weaviate 配置 (v4 客户端)
            url = self.config.get('url', 'http://localhost:8080')

            # 尝试使用v4客户端直接连接
            import weaviate.classes.config as wvc
            self.client = weaviate.connect_to_local(
                host="localhost",
                port=8080,
                secure=False
            )

            logger.info(f"Weaviate v4 客户端初始化成功，连接到: {url}")
            self._create_schema_if_not_exists()

        except Exception as e:
            logger.error(f"Weaviate v4 客户端初始化失败: {e}")
            # 如果连接失败，使用模拟客户端进行开发
            try:
                logger.info("尝试使用模拟客户端...")
                self.client = MockWeaviateClient()
                logger.info("使用模拟Weaviate客户端")
                self._create_schema_if_not_exists()
            except Exception as e2:
                logger.error(f"模拟客户端初始化也失败: {e2}")
                raise e2

    def ensure_schema(self):
        """确保 schema 存在"""
        return self._create_schema_if_not_exists()

    def _create_schema_if_not_exists(self):
        """创建 schema 如果不存在"""
        try:
            # 检查使用的客户端版本
            if hasattr(self.client, 'collections'):
                # v4 客户端
                self._create_schema_v4()
            else:
                # v3 客户端
                self._create_schema_v3()

        except Exception as e:
            logger.error(f"创建 schema 失败: {e}")
            raise

    def _create_schema_v4(self):
        """使用v4 API创建schema"""
        try:
            # 检查collection是否存在
            if not self.client.collections.exists(self.class_name):
                # 创建collection
                from weaviate.classes.config import Property, DataType

                collection = self.client.collections.create(
                    name=self.class_name,
                    description="IP专家系统文档集合",
                    properties=[
                        Property(name="content", data_type=DataType.TEXT, description="文档内容"),
                        Property(name="title", data_type=DataType.TEXT, description="文档标题"),
                        Property(name="source", data_type=DataType.TEXT, description="文档来源"),
                        Property(name="doc_type", data_type=DataType.TEXT, description="文档类型"),
                        Property(name="chunk_index", data_type=DataType.INT, description="分块索引"),
                        Property(name="document_id", data_type=DataType.TEXT, description="文档ID"),
                    ]
                )
                logger.info(f"v4: 创建collection {self.class_name} 成功")
            else:
                logger.info(f"v4: collection {self.class_name} 已存在")

        except Exception as e:
            logger.error(f"v4 schema创建失败: {e}")
            raise

    def _create_schema_v3(self):
        """使用v3 API创建schema"""
        try:
            # 检查类是否存在
            schema = self.client.schema.get()
            existing_classes = [cls['class'] for cls in schema.get('classes', [])]

            if self.class_name not in existing_classes:
                # 创建类定义
                class_obj = {
                    "class": self.class_name,
                    "description": "IP专家系统文档集合",
                    "vectorizer": "none",  # 我们手动提供向量
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "文档内容"
                        },
                        {
                            "name": "title",
                            "dataType": ["text"],
                            "description": "文档标题"
                        },
                        {
                            "name": "source",
                            "dataType": ["text"],
                            "description": "文档来源"
                        },
                        {
                            "name": "doc_type",
                            "dataType": ["text"],
                            "description": "文档类型"
                        },
                        {
                            "name": "chunk_index",
                            "dataType": ["int"],
                            "description": "分块索引"
                        },
                        {
                            "name": "document_id",
                            "dataType": ["text"],
                            "description": "文档ID"
                        }
                    ]
                }

                self.client.schema.create_class(class_obj)
                logger.info(f"v3: 创建类 {self.class_name} 成功")
            else:
                logger.info(f"v3: 类 {self.class_name} 已存在")

        except Exception as e:
            logger.error(f"v3 schema创建失败: {e}")
            raise

    def test_connection(self) -> bool:
        """
        测试数据库连接

        Returns:
            bool: 连接是否正常
        """
        try:
            # 检查使用的客户端版本
            if hasattr(self.client, 'collections'):
                # v4 客户端
                self.client.collections.list_all()
            else:
                # v3 客户端
                self.client.schema.get()
            logger.info("Weaviate 连接测试成功")
            return True

        except Exception as e:
            logger.error(f"Weaviate 连接测试失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            Dict: 统计信息
        """
        try:
            total_count = 0

            # 检查使用的客户端版本
            if hasattr(self.client, 'collections'):
                # v4 客户端
                try:
                    collection = self.client.collections.get(self.class_name)
                    # v4中获取总数的方法
                    response = collection.aggregate.over_all(total_count=True)
                    total_count = response.total_count if response.total_count else 0
                except Exception:
                    total_count = 0
            else:
                # v3 客户端
                result = (
                    self.client.query
                    .aggregate(self.class_name)
                    .with_meta_count()
                    .do()
                )

                if 'data' in result and 'Aggregate' in result['data'] and self.class_name in result['data']['Aggregate']:
                    aggregate_data = result['data']['Aggregate'][self.class_name]
                    if aggregate_data and len(aggregate_data) > 0:
                        total_count = aggregate_data[0].get('meta', {}).get('count', 0)

            return {
                "total_documents": total_count,
                "collection_name": self.class_name,
                "status": "healthy",
                "db_type": "weaviate_local"
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "total_documents": 0,
                "collection_name": self.class_name,
                "status": "error",
                "error": str(e),
                "db_type": "weaviate_local"
            }

    def add_document(self, document_id: str, chunks: List[Dict[str, Any]],
                    vectors: List[List[float]]) -> List[str]:
        """
        添加单个文档的多个分块

        Args:
            document_id: 文档ID
            chunks: 文档分块列表
            vectors: 对应的向量列表

        Returns:
            List[str]: 向量ID列表
        """
        try:
            vector_ids = []

            # 检查使用的客户端版本
            if hasattr(self.client, 'collections'):
                # v4 客户端
                collection = self.client.collections.get(self.class_name)

                for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                    # 生成UUID
                    vector_id = str(uuid.uuid4())
                    properties = {
                        "content": chunk.get("content", ""),
                        "title": chunk.get("title", ""),
                        "source": chunk.get("source", ""),
                        "doc_type": chunk.get("doc_type", ""),
                        "chunk_index": chunk.get("chunk_index", i),
                        "document_id": document_id
                    }

                    # 插入数据
                    collection.data.insert(
                        uuid=vector_id,
                        properties=properties,
                        vector=vector
                    )
                    vector_ids.append(vector_id)
            else:
                # v3 客户端
                with self.client.batch as batch:
                    batch.batch_size = 100

                    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                        # 生成有效的UUID
                        vector_id = str(uuid.uuid4())
                        properties = {
                            "content": chunk.get("content", ""),
                            "title": chunk.get("title", ""),
                            "source": chunk.get("source", ""),
                            "doc_type": chunk.get("doc_type", ""),
                            "chunk_index": chunk.get("chunk_index", i),
                            "document_id": document_id
                        }

                        batch.add_data_object(
                            data_object=properties,
                            class_name=self.class_name,
                            vector=vector,
                            uuid=vector_id
                        )
                        vector_ids.append(vector_id)

            logger.info(f"成功添加文档 {document_id} 的 {len(chunks)} 个分块")
            return vector_ids

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return []

    def search_similar(self, query_vector: List[float], top_k: int = 5,
                      document_id: Optional[str] = None, filters: Optional[Dict] = None) -> List[Dict]:
        """
        相似性搜索

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            document_id: 文档ID过滤（可选）
            filters: 其他过滤条件

        Returns:
            List[Dict]: 搜索结果
        """
        try:
            results = []

            # 检查使用的客户端版本
            if hasattr(self.client, 'collections'):
                # v4 客户端
                collection = self.client.collections.get(self.class_name)

                # 构建查询
                query_builder = collection.query.near_vector(
                    near_vector=query_vector,
                    limit=top_k,
                    return_metadata=["score", "distance"]
                )

                # 应用文档ID过滤
                if document_id:
                    from weaviate.classes.query import Filter
                    query_builder = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=top_k,
                        where=Filter.by_property("document_id").equal(document_id),
                        return_metadata=["score", "distance"]
                    )

                response = query_builder

                # 处理结果
                for obj in response.objects:
                    result = {
                        "content": obj.properties.get("content", ""),
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "doc_type": obj.properties.get("doc_type", ""),
                        "chunk_index": obj.properties.get("chunk_index", 0),
                        "document_id": obj.properties.get("document_id", ""),
                        "score": getattr(obj.metadata, 'score', 0) if obj.metadata else 0,
                        "distance": getattr(obj.metadata, 'distance', 0) if obj.metadata else 0
                    }
                    results.append(result)

            else:
                # v3 客户端
                query_builder = (
                    self.client.query
                    .get(self.class_name, ["content", "title", "source", "doc_type", "chunk_index", "document_id"])
                    .with_near_vector({"vector": query_vector})
                    .with_limit(top_k)
                    .with_additional(["score", "distance"])
                )

                # 应用文档ID过滤
                if document_id:
                    query_builder = query_builder.with_where({
                        "path": ["document_id"],
                        "operator": "Equal",
                        "valueText": document_id
                    })

                response = query_builder.do()

                if 'data' in response and 'Get' in response['data'] and self.class_name in response['data']['Get']:
                    for obj in response['data']['Get'][self.class_name]:
                        result = {
                            "content": obj.get("content", ""),
                            "title": obj.get("title", ""),
                            "source": obj.get("source", ""),
                            "doc_type": obj.get("doc_type", ""),
                            "chunk_index": obj.get("chunk_index", 0),
                            "document_id": obj.get("document_id", ""),
                            "score": obj.get("_additional", {}).get("score", 0),
                            "distance": obj.get("_additional", {}).get("distance", 0)
                        }
                        results.append(result)

            logger.info(f"搜索返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档的所有分块

        Args:
            document_id: 文档ID

        Returns:
            bool: 是否成功
        """
        try:
            # 检查使用的客户端版本
            if hasattr(self.client, 'collections'):
                # v4 客户端
                collection = self.client.collections.get(self.class_name)

                # 删除所有匹配的对象
                from weaviate.classes.query import Filter
                result = collection.data.delete_many(
                    where=Filter.by_property("document_id").equal(document_id)
                )

                deleted_count = result.matches if hasattr(result, 'matches') else 0
                logger.info(f"成功删除文档 {document_id} 的 {deleted_count} 个分块")
                return True

            else:
                # v3 客户端
                query_result = (
                    self.client.query
                    .get(self.class_name, ["document_id"])
                    .with_where({
                        "path": ["document_id"],
                        "operator": "Equal",
                        "valueText": document_id
                    })
                    .with_additional(["id"])
                    .do()
                )

                # 删除找到的所有对象
                if 'data' in query_result and 'Get' in query_result['data'] and self.class_name in query_result['data']['Get']:
                    objects = query_result['data']['Get'][self.class_name]
                    for obj in objects:
                        obj_id = obj.get('_additional', {}).get('id')
                        if obj_id:
                            self.client.data_object.delete(
                                uuid=obj_id,
                                class_name=self.class_name
                            )

                    logger.info(f"成功删除文档 {document_id} 的 {len(objects)} 个分块")
                    return True
                else:
                    logger.warning(f"未找到文档 {document_id} 的分块")
                    return True

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        try:
            if hasattr(self.client, 'close'):
                self.client.close()
            logger.info("Weaviate 连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")

    # 保持向后兼容的方法
    def add_documents(self, documents: List[Dict[str, Any]], vectors: List[List[float]]) -> bool:
        """向后兼容方法"""
        try:
            document_id = "batch_" + str(uuid.uuid4())
            self.add_document(document_id, documents, vectors)
            return True
        except:
            return False

    def search(self, query_vector: List[float], k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """向后兼容方法"""
        return self.search_similar(query_vector, k, None, filters)

    def delete_documents(self, document_ids: List[str]) -> bool:
        """向后兼容方法"""
        try:
            for doc_id in document_ids:
                self.delete_document(doc_id)
            return True
        except:
            return False
