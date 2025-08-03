#!/usr/bin/env python3
"""
Weaviate 向量数据库测试脚本
"""
import os
import sys
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.services.retrieval.vector_service import VectorService
from app.services.ai.embedding_service import get_embedding_service
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_weaviate_vector_db():
    """测试 Weaviate 向量数据库功能"""
    try:
        print("=" * 50)
        print("测试 Weaviate 向量数据库")
        print("=" * 50)

        # 1. 测试嵌入服务
        print("\n1. 测试嵌入服务...")
        embedding_service = get_embedding_service()

        if hasattr(embedding_service, 'test_connection'):
            if embedding_service.test_connection():
                print("✅ 嵌入服务连接正常")
            else:
                print("❌ 嵌入服务连接失败")
                assert False, "测试失败"
        else:
            print("⚠️  嵌入服务没有 test_connection 方法")

        # 2. 测试向量服务初始化
        print("\n2. 测试向量服务初始化...")
        vector_service = VectorService()
        print("✅ 向量服务初始化成功")

        # 3. 测试向量数据库连接
        print("\n3. 测试向量数据库连接...")
        if vector_service.vector_db.test_connection():
            print("✅ Weaviate 连接正常")
        else:
            print("❌ Weaviate 连接失败")
            assert False, "测试失败"

        # 4. 测试数据库统计信息
        print("\n4. 获取数据库统计信息...")
        stats = vector_service.vector_db.get_stats()
        print(f"统计信息: {stats}")

        # 5. 测试文本向量化
        print("\n5. 测试文本向量化...")
        test_texts = [
            "网络设备配置管理是网络运维的重要环节",
            "OSPF协议是一种链路状态路由协议",
            "交换机端口镜像可以用于网络监控和故障排查"
        ]

        vectors = vector_service.embed_batch(test_texts)
        print(f"✅ 成功向量化 {len(vectors)} 个文本")
        print(f"向量维度: {len(vectors[0]) if vectors else 0}")

        # 6. 测试文档存储
        print("\n6. 测试文档存储...")
        test_documents = []
        for i, text in enumerate(test_texts):
            doc = {
                "content": text,
                "title": f"测试文档 {i+1}",
                "source": "test_data",
                "doc_type": "test",
                "chunk_index": i
            }
            test_documents.append(doc)

        success = vector_service.vector_db.add_documents(test_documents, vectors)
        if success:
            print("✅ 文档存储成功")
        else:
            print("❌ 文档存储失败")
            assert False, "测试失败"

        # 7. 测试向量搜索
        print("\n7. 测试向量搜索...")
        query_text = "路由协议配置"
        query_vector = vector_service.embed_batch([query_text])[0]

        search_results = vector_service.vector_db.search(query_vector, k=3)
        print(f"✅ 搜索返回 {len(search_results)} 个结果")

        for i, result in enumerate(search_results[:2]):  # 只显示前2个结果
            print(f"  结果 {i+1}:")
            print(f"    标题: {result.get('title', 'N/A')}")
            print(f"    内容: {result.get('content', 'N/A')[:50]}...")
            print(f"    得分: {result.get('score', 0):.4f}")

        # 8. 获取最终统计信息
        print("\n8. 获取最终统计信息...")
        final_stats = vector_service.vector_db.get_stats()
        print(f"最终统计: {final_stats}")

        print("\n" + "=" * 50)
        print("✅ 所有测试通过！Weaviate 向量数据库工作正常")
        print("=" * 50)

        assert True  # 测试通过

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, "测试失败"

if __name__ == "__main__":
    test_weaviate_vector_db()
