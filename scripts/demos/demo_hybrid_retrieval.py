#!/usr/bin/env python3
"""
IP智慧解答专家系统 - 混合检索算法演示

本脚本演示如何使用混合检索算法进行知识检索。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.services.retrieval.hybrid_retrieval import search_knowledge, get_hybrid_retrieval
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_basic_search():
    """演示基本搜索功能"""
    print("=" * 60)
    print("🔍 混合检索算法 - 基本搜索演示")
    print("=" * 60)

    # 测试查询
    test_queries = [
        "OSPF邻居建立失败",
        "华为路由器BGP配置",
        "VLAN间路由配置方法",
        "思科交换机端口镜像",
        "网络故障排除步骤"
    ]

    app = create_app()
    with app.app_context():
        for query in test_queries:
            print(f"\n📝 查询: {query}")
            print("-" * 40)

            try:
                results = search_knowledge(
                    query=query,
                    vector_weight=0.7,
                    keyword_weight=0.3,
                    top_k=3
                )

                if results:
                    print(f"✅ 找到 {len(results)} 个相关结果:")
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. 【{result['source_type'].upper()}】")
                        print(f"   标题: {result['title']}")
                        print(f"   评分: {result['score']:.3f}")
                        print(f"   内容预览: {result['content'][:100]}...")
                        print(f"   匹配说明: {result['relevance_explanation']}")
                        if result['metadata']:
                            print(f"   元数据: {result['metadata']}")
                else:
                    print("❌ 未找到相关结果")

            except Exception as e:
                print(f"❌ 搜索失败: {str(e)}")

            print("")


def demo_advanced_search():
    """演示高级搜索功能"""
    print("=" * 60)
    print("🔍 混合检索算法 - 高级搜索演示")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        # 演示带过滤条件的搜索
        print("\n📝 测试过滤条件搜索")
        print("-" * 40)

        query = "路由配置"
        filters = {
            "vendor": "华为",
            "category": "路由协议"
        }

        print(f"查询: {query}")
        print(f"过滤条件: {filters}")

        try:
            results = search_knowledge(
                query=query,
                filters=filters,
                top_k=5
            )

            print(f"✅ 过滤后找到 {len(results)} 个结果")

        except Exception as e:
            print(f"❌ 过滤搜索失败: {str(e)}")

        # 演示权重调整
        print("\n📝 测试不同权重配置")
        print("-" * 40)

        query = "OSPF配置命令"
        weight_configs = [
            (1.0, 0.0, "纯向量检索"),
            (0.0, 1.0, "纯关键词检索"),
            (0.7, 0.3, "向量主导"),
            (0.3, 0.7, "关键词主导")
        ]

        for vector_w, keyword_w, desc in weight_configs:
            print(f"\n🔧 {desc} (向量:{vector_w}, 关键词:{keyword_w})")

            try:
                results = search_knowledge(
                    query=query,
                    vector_weight=vector_w,
                    keyword_weight=keyword_w,
                    top_k=3
                )

                print(f"   结果数量: {len(results)}")
                if results:
                    avg_score = sum(r['score'] for r in results) / len(results)
                    print(f"   平均评分: {avg_score:.3f}")

                    source_types = [r['source_type'] for r in results]
                    print(f"   结果类型: {', '.join(set(source_types))}")

            except Exception as e:
                print(f"   ❌ 失败: {str(e)}")


def demo_retrieval_service():
    """演示检索服务的直接使用"""
    print("=" * 60)
    print("🔍 混合检索算法 - 检索服务演示")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        try:
            # 获取检索服务实例
            retrieval = get_hybrid_retrieval()

            print("\n📊 检索服务配置:")
            print(f"   向量权重: {retrieval.vector_weight}")
            print(f"   关键词权重: {retrieval.keyword_weight}")
            print(f"   重排序候选数: {retrieval.rerank_top_k}")
            print(f"   最终返回数: {retrieval.final_top_k}")

            # 测试关键词提取
            query = "华为交换机VLAN配置故障排除"
            print(f"\n🔤 关键词提取演示:")
            print(f"   查询: {query}")

            keywords = retrieval._extract_keywords(query)
            print(f"   提取的关键词: {keywords}")

            tech_terms = retrieval._extract_tech_terms(query)
            print(f"   技术术语: {tech_terms}")

            # 测试搜索
            print(f"\n🔍 执行搜索:")
            results = retrieval.search(query, top_k=5)

            print(f"   搜索结果: {len(results)} 个")
            for i, result in enumerate(results[:3], 1):
                print(f"   {i}. {result.title} (评分: {result.score:.3f})")

        except Exception as e:
            print(f"❌ 检索服务演示失败: {str(e)}")


def demo_performance_comparison():
    """演示性能对比"""
    print("=" * 60)
    print("🔍 混合检索算法 - 性能对比演示")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        import time

        queries = [
            "OSPF邻居建立失败",
            "BGP路由策略配置",
            "VLAN配置命令"
        ]

        for query in queries:
            print(f"\n📝 查询: {query}")
            print("-" * 30)

            # 测试不同检索方式的性能
            methods = [
                (1.0, 0.0, "向量检索"),
                (0.0, 1.0, "关键词检索"),
                (0.7, 0.3, "混合检索")
            ]

            for vector_w, keyword_w, method_name in methods:
                start_time = time.time()

                try:
                    results = search_knowledge(
                        query=query,
                        vector_weight=vector_w,
                        keyword_weight=keyword_w,
                        top_k=10
                    )

                    end_time = time.time()
                    duration = (end_time - start_time) * 1000  # 转换为毫秒

                    print(f"   {method_name:8s}: {duration:6.1f}ms, {len(results):2d} 结果")

                except Exception as e:
                    print(f"   {method_name:8s}: 失败 - {str(e)}")


def main():
    """主函数"""
    print("🚀 IP智慧解答专家系统 - 混合检索算法演示")
    print("=" * 80)

    demos = [
        ("1", "基本搜索演示", demo_basic_search),
        ("2", "高级搜索演示", demo_advanced_search),
        ("3", "检索服务演示", demo_retrieval_service),
        ("4", "性能对比演示", demo_performance_comparison),
        ("5", "运行所有演示", None)
    ]

    print("\n请选择演示类型:")
    for code, name, _ in demos:
        print(f"  {code}. {name}")

    choice = input("\n请输入选择 (1-5): ").strip()

    if choice == "1":
        demo_basic_search()
    elif choice == "2":
        demo_advanced_search()
    elif choice == "3":
        demo_retrieval_service()
    elif choice == "4":
        demo_performance_comparison()
    elif choice == "5":
        print("\n🏃‍♂️ 运行所有演示...")
        demo_basic_search()
        demo_advanced_search()
        demo_retrieval_service()
        demo_performance_comparison()
    else:
        print("❌ 无效选择")
        return

    print("\n✅ 演示完成!")


if __name__ == "__main__":
    main()
