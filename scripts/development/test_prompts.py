"""
提示词工程测试脚本

本脚本用于测试LLM服务的各种功能。
"""

import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.ai.llm_service import LLMService
from app.services.storage.cache_service import get_cache_service
from app.utils.monitoring import get_monitor


def test_analysis_prompt():
    """测试问题分析提示词"""
    print("=" * 50)
    print("测试问题分析提示词")
    print("=" * 50)

    test_cases = [
        {
            "query": "OSPF邻居建立不起来，状态一直在Init",
            "vendor": "华为",
            "context": ""
        },
        {
            "query": "BGP路由黑洞问题，数据包丢失",
            "vendor": "思科",
            "context": ""
        },
        {
            "query": "交换机端口经常down掉",
            "vendor": "H3C",
            "context": ""
        }
    ]

    llm_service = LLMService()

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"问题: {test_case['query']}")
        print(f"厂商: {test_case['vendor']}")

        try:
            result = llm_service.analyze_query(
                query=test_case['query'],
                context=test_case['context'],
                vendor=test_case['vendor']
            )

            print(f"分析结果:")
            print(f"- 类别: {result.get('category')}")
            print(f"- 严重程度: {result.get('severity')}")
            print(f"- 需要更多信息: {result.get('need_more_info')}")
            print(f"- 分析内容: {result.get('analysis')[:200]}...")

        except Exception as e:
            print(f"错误: {str(e)}")


def test_clarification_prompt():
    """测试澄清问题提示词"""
    print("\n" + "=" * 50)
    print("测试澄清问题提示词")
    print("=" * 50)

    analysis_result = {
        "category": "OSPF",
        "severity": "高",
        "analysis": "OSPF邻居建立失败，可能的原因包括配置错误、网络连通性问题等"
    }

    llm_service = LLMService()

    try:
        result = llm_service.generate_clarification(
            query="OSPF邻居建立不起来",
            analysis=analysis_result,
            vendor="华为"
        )

        print(f"澄清问题:")
        print(result.get('clarification'))
        print(f"\n具体问题:")
        print(result.get('questions'))

    except Exception as e:
        print(f"错误: {str(e)}")


def test_solution_prompt():
    """测试解决方案提示词"""
    print("\n" + "=" * 50)
    print("测试解决方案提示词")
    print("=" * 50)

    context = [
        {
            "title": "OSPF邻居建立故障排除",
            "content": "OSPF邻居建立失败的常见原因包括：1. Area ID不匹配 2. Hello间隔不一致 3. 认证配置错误",
            "source": "华为技术文档"
        }
    ]

    analysis_result = {
        "category": "OSPF",
        "severity": "高"
    }

    llm_service = LLMService()

    try:
        result = llm_service.generate_solution(
            query="OSPF邻居建立不起来",
            context=context,
            analysis=analysis_result,
            vendor="华为"
        )

        print(f"解决方案:")
        print(result.get('answer')[:500] + "...")
        print(f"\n提取的命令:")
        for cmd in result.get('commands', [])[:3]:
            print(f"- {cmd}")

    except Exception as e:
        print(f"错误: {str(e)}")


def test_conversation_flow():
    """测试多轮对话流程"""
    print("\n" + "=" * 50)
    print("测试多轮对话流程")
    print("=" * 50)

    conversation_history = [
        {"role": "user", "content": "OSPF邻居建立不起来"},
        {"role": "assistant", "content": "请提供更多信息，比如设备型号、区域配置等"},
        {"role": "user", "content": "设备是华为NE40E，area 0配置"}
    ]

    llm_service = LLMService()

    try:
        result = llm_service.continue_conversation(
            conversation_history=conversation_history,
            new_query="我检查了配置，area ID是正确的",
            problem_status="诊断中"
        )

        print(f"对话回复:")
        print(result.get('response'))

    except Exception as e:
        print(f"错误: {str(e)}")


def test_performance_monitoring():
    """测试性能监控"""
    print("\n" + "=" * 50)
    print("测试性能监控")
    print("=" * 50)

    monitor = get_monitor()

    # 获取统计信息
    stats = monitor.get_all_stats(time_window=3600)
    health = monitor.get_health_status()

    print(f"健康状态: {health.get('status')}")
    print(f"整体成功率: {health.get('overall_success_rate')}")
    print(f"监控的操作数量: {stats.get('total_operations')}")

    for op_name, op_stats in stats.get('operations', {}).items():
        if op_stats.get('total_count', 0) > 0:
            print(f"\n操作: {op_name}")
            print(f"- 总次数: {op_stats.get('total_count')}")
            print(f"- 成功率: {op_stats.get('success_rate'):.2%}")
            print(f"- 平均耗时: {op_stats.get('avg_duration'):.2f}秒")


def test_cache_service():
    """测试缓存服务"""
    print("\n" + "=" * 50)
    print("测试缓存服务")
    print("=" * 50)

    cache_service = get_cache_service()

    # 获取缓存信息
    cache_info = cache_service.get_cache_info()
    print(f"缓存类型: {cache_info.get('type')}")
    print(f"连接状态: {cache_info.get('connected')}")

    if cache_info.get('type') == 'redis':
        print(f"内存使用: {cache_info.get('used_memory')}")
        print(f"连接客户端: {cache_info.get('connected_clients')}")
    elif cache_info.get('type') == 'memory':
        print(f"缓存键数量: {cache_info.get('cached_keys')}")

    # 测试缓存操作
    test_key = cache_service.generate_cache_key("test", "prompt", "example")
    test_data = {"test": True, "timestamp": datetime.now().isoformat()}

    # 设置缓存
    success = cache_service.cache_result(test_key, test_data, 60)
    print(f"\n缓存设置: {'成功' if success else '失败'}")

    # 获取缓存
    cached_data = cache_service.get_cached_result(test_key)
    print(f"缓存获取: {'成功' if cached_data else '失败'}")

    # 删除缓存
    deleted = cache_service.delete_cache(test_key)
    print(f"缓存删除: {'成功' if deleted else '失败'}")


def run_all_tests():
    """运行所有测试"""
    print("开始运行提示词工程测试...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 测试分析提示词
        test_analysis_prompt()

        # 测试澄清提示词
        test_clarification_prompt()

        # 测试解决方案提示词
        test_solution_prompt()

        # 测试多轮对话
        test_conversation_flow()

        # 测试性能监控
        test_performance_monitoring()

        # 测试缓存服务
        test_cache_service()

    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    # 创建应用上下文
    app = create_app()

    with app.app_context():
        run_all_tests()
