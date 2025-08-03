#!/usr/bin/env python3
"""
向量数据库设置测试脚本

测试向量数据库的基本功能：
1. 嵌入服务连接测试
2. 向量数据库连接测试
3. 基本向量操作测试
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.services.ai.embedding_service import get_embedding_service
from app.services.retrieval.vector_service import get_vector_service
from app.services.storage.vector_db_config import vector_db_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_embedding_service():
    """测试嵌入服务"""
    print("\n" + "="*50)
    print("测试嵌入服务")
    print("="*50)

    try:
        embedding_service = get_embedding_service()

        # 测试单个文本向量化
        test_text = "这是一个测试文本，用于验证向量化功能"
        print(f"测试文本: {test_text}")

        vector = embedding_service.embed_text(test_text)
        print(f"向量维度: {len(vector)}")
        print(f"向量前5个值: {vector[:5]}")

        # 测试批量向量化
        test_texts = [
            "网络协议OSPF配置",
            "交换机VLAN设置",
            "路由器BGP路由配置"
        ]

        vectors = embedding_service.embed_batch(test_texts)
        print(f"批量向量化成功，处理了 {len(vectors)} 个文本")

        print("✅ 嵌入服务测试通过")
        assert True  # 测试通过

    except Exception as e:
        print(f"❌ 嵌入服务测试失败: {str(e)}")
        assert False, f"嵌入服务测试失败: {str(e)}"


def test_vector_database():
    """测试向量数据库"""
    print("\n" + "="*50)
    print("测试向量数据库")
    print("="*50)

    try:
        # 显示当前配置
        print(f"当前向量数据库类型: {vector_db_config.db_type.value}")
        print(f"配置有效性: {vector_db_config.is_valid()}")

        vector_service = get_vector_service()

        # 连接测试
        if vector_service.test_connection():
            print("✅ 向量数据库连接测试通过")
        else:
            print("❌ 向量数据库连接测试失败")
            assert False, "测试失败"

        # 测试数据
        test_chunks = [
            {
                "content": "OSPF（Open Shortest Path First）是一种链路状态路由协议，用于IP网络中的路由选择。",
                "metadata": {"source": "test", "type": "protocol"}
            },
            {
                "content": "VLAN（Virtual Local Area Network）虚拟局域网技术可以将一个物理网络分割成多个逻辑网络。",
                "metadata": {"source": "test", "type": "network"}
            }
        ]

        document_id = "test_doc_001"

        # 测试向量存储
        print(f"存储测试文档块: {len(test_chunks)} 个")
        vector_ids = vector_service.index_chunks(test_chunks, document_id)
        print(f"✅ 向量存储成功，向量ID: {vector_ids}")

        # 测试相似性搜索
        query = "什么是OSPF路由协议"
        print(f"搜索查询: {query}")

        results = vector_service.search_similar(query, top_k=2)
        print(f"✅ 搜索成功，找到 {len(results)} 个相似结果")

        for i, result in enumerate(results):
            print(f"  结果 {i+1}:")
            print(f"    相似度: {result.get('score', 'N/A')}")
            print(f"    内容: {result.get('content', 'N/A')[:100]}...")

        # 测试统计信息
        stats = vector_service.get_stats()
        print(f"✅ 数据库统计: {stats}")

        # 清理测试数据
        if vector_service.delete_document(document_id):
            print("✅ 测试数据清理成功")

        assert True  # 测试通过

    except Exception as e:
        print(f"❌ 向量数据库测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        assert False, "测试失败"


def main():
    """主测试函数"""
    print("IP智慧解答专家系统 - 向量数据库设置测试")
    print("="*60)

    # 检查环境变量
    print("\n环境变量检查:")
    dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
    if dashscope_key:
        print(f"✅ DASHSCOPE_API_KEY: {dashscope_key[:10]}...")
    else:
        print("❌ DASHSCOPE_API_KEY 未设置")
        assert False, "测试失败"

    # 运行测试
    tests = [
        ("嵌入服务", test_embedding_service),
        ("向量数据库", test_vector_database)
    ]

    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))

    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 所有测试都通过了！向量数据库设置成功！")
    else:
        print("\n⚠️  部分测试失败，请检查配置和日志")

    return all_passed


if __name__ == "__main__":
    main()
