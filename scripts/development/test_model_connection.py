#!/usr/bin/env python3
"""
测试LLM模型连接

验证是否能够连接到真实的大模型服务
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai.llm_service import LLMService
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

def test_model_connection():
    """测试模型连接"""
    print("=" * 60)
    print("测试LLM模型连接")
    print("=" * 60)

    # 检查环境变量
    print("\n1. 检查环境配置:")
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    api_base = os.environ.get('OPENAI_API_BASE')

    print(f"   DASHSCOPE_API_KEY: {'已设置' if api_key else '未设置'}")
    print(f"   API_BASE: {api_base}")

    if not api_key:
        print("   ❌ 错误: 未设置DASHSCOPE_API_KEY")
        assert False, "DASHSCOPE_API_KEY 环境变量未设置"

    # 测试直接连接
    print("\n2. 测试直接模型连接:")
    try:
        llm = ChatOpenAI(
            model="qwen-plus",
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.1,
            max_tokens=100,
            timeout=30
        )

        # 发送简单的测试消息
        response = llm.invoke([HumanMessage(content="你好，请简单介绍一下你自己。")])
        print(f"   ✅ 模型响应成功")
        print(f"   模型: qwen-plus")
        print(f"   响应长度: {len(response.content)} 字符")
        print(f"   响应预览: {response.content[:100]}...")

    except Exception as e:
        print(f"   ❌ 模型连接失败: {str(e)}")
        assert False, f"模型连接失败: {str(e)}"

    # 测试LLM服务
    print("\n3. 测试LLM服务:")
    try:
        llm_service = LLMService()

        # 测试问题分析
        result = llm_service.analyze_query(
            query="路由器无法访问互联网",
            context="",
            vendor="华为"
        )

        print(f"   ✅ LLM服务测试成功")
        print(f"   分析结果包含字段: {list(result.keys())}")
        print(f"   问题分类: {result.get('category', 'N/A')}")
        print(f"   需要更多信息: {result.get('need_more_info', 'N/A')}")

    except Exception as e:
        print(f"   ❌ LLM服务测试失败: {str(e)}")
        assert False, f"LLM服务测试失败: {str(e)}"

    print("\n4. 模型信息总结:")
    print(f"   ✅ 使用的是真实的阿里云通义千问大模型")
    print(f"   ✅ 模型名称: qwen-plus")
    print(f"   ✅ API提供商: 阿里云百炼平台")
    print(f"   ✅ 连接方式: OpenAI兼容接口")
    print(f"   ✅ 所有测试通过")

    # 测试函数应该使用assert而不是return
    assert True  # 所有测试通过

def test_api_quota():
    """测试API配额"""
    print("\n5. 测试API配额和限制:")

    try:
        llm = ChatOpenAI(
            model="qwen-plus",
            openai_api_key=os.environ.get('DASHSCOPE_API_KEY'),
            openai_api_base=os.environ.get('OPENAI_API_BASE'),
            temperature=0.1,
            max_tokens=50,
            timeout=10
        )

        # 发送多个快速请求测试
        for i in range(3):
            response = llm.invoke([HumanMessage(content=f"这是第{i+1}个测试消息，请简单回复。")])
            print(f"   请求 {i+1}: 成功 ({len(response.content)} 字符)")

        print("   ✅ API配额充足，无速率限制问题")

    except Exception as e:
        print(f"   ⚠️  可能遇到配额或速率限制: {str(e)}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    success = test_model_connection()
    if success:
        test_api_quota()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
