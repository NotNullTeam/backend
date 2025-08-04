"""
API 响应测试套件

运行所有 API 模块的响应测试，并生成详细的测试报告。
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_api_response_tests():
    """运行所有API响应测试"""

    # 测试文件列表
    test_files = [
        'tests/api/test_v1_auth_responses.py',
        'tests/api/test_v1_cases_responses.py',
        'tests/api/test_v1_knowledge_responses.py',
        'tests/api/test_v1_system_responses.py',
        'tests/api/test_v1_development_responses.py',
        'tests/api/test_response_consistency.py',
    ]

    # pytest参数配置
    pytest_args = [
        '-v',  # 详细输出
        '--tb=short',  # 简短的错误回溯
        '--strict-markers',  # 严格标记模式
        '--disable-warnings',  # 禁用警告
        '--color=yes',  # 彩色输出
        '--durations=10',  # 显示最慢的10个测试
        '--cov=app.api',  # 代码覆盖率检查
        '--cov-report=html:htmlcov/api_responses',  # HTML覆盖率报告
        '--cov-report=term-missing',  # 终端覆盖率报告
        '--junit-xml=test-results/api_responses.xml',  # JUnit XML报告
    ]

    # 添加测试文件
    pytest_args.extend(test_files)

    print("🧪 开始运行API响应测试...")
    print("=" * 60)

    # 运行测试
    exit_code = pytest.main(pytest_args)

    print("=" * 60)
    if exit_code == 0:
        print("✅ 所有API响应测试通过！")
    else:
        print("❌ 部分API响应测试失败，请查看详细报告")

    return exit_code


def run_specific_module_tests(module_name):
    """运行特定模块的API响应测试"""

    module_mapping = {
        'auth': 'tests/api/test_v1_auth_responses.py',
        'cases': 'tests/api/test_v1_cases_responses.py',
        'knowledge': 'tests/api/test_v1_knowledge_responses.py',
        'system': 'tests/api/test_v1_system_responses.py',
        'development': 'tests/api/test_v1_development_responses.py',
        'consistency': 'tests/api/test_response_consistency.py',
    }

    if module_name not in module_mapping:
        print(f"❌ 未知模块: {module_name}")
        print(f"可用模块: {', '.join(module_mapping.keys())}")
        return 1

    test_file = module_mapping[module_name]

    pytest_args = [
        '-v',
        '--tb=short',
        '--color=yes',
        test_file
    ]

    print(f"🧪 运行 {module_name} 模块API响应测试...")
    return pytest.main(pytest_args)


def generate_test_summary():
    """生成测试摘要"""

    summary = """
# API响应测试摘要

## 测试模块概览

### 1. 认证模块 (auth)
- ✅ 登录/登出响应格式
- ✅ 用户信息响应格式
- ✅ 令牌刷新响应格式
- ✅ 错误响应一致性

### 2. 案例模块 (cases)
- ✅ CRUD操作响应格式
- ✅ 案例交互响应格式
- ✅ 搜索和分页响应格式
- ✅ 批量操作响应格式

### 3. 知识库模块 (knowledge)
- ✅ 文档上传响应格式
- ✅ 搜索和语义搜索响应格式
- ✅ 文档解析状态响应格式
- ✅ 嵌入向量响应格式

### 4. 系统模块 (system)
- ✅ 系统状态和健康检查响应格式
- ✅ 系统指标和日志响应格式
- ✅ 配置管理响应格式
- ✅ 数据库和缓存状态响应格式

### 5. 开发工具模块 (development)
- ✅ API文档和规范响应格式
- ✅ 调试信息和性能测试响应格式
- ✅ 代码覆盖率和分析响应格式
- ✅ 测试运行器响应格式

### 6. 响应一致性 (consistency)
- ✅ 成功/错误响应格式统一
- ✅ HTTP状态码一致性
- ✅ 分页格式标准化
- ✅ 时间戳格式统一
- ✅ 国际化消息一致性

## 测试覆盖范围

### 响应格式验证
- [x] JSON结构验证
- [x] 状态码一致性
- [x] 错误类型分类
- [x] 数据类型检查

### 性能测试
- [x] 响应时间合理性
- [x] 响应大小限制
- [x] 并发请求处理

### 安全测试
- [x] 未授权访问响应
- [x] 权限验证响应
- [x] 输入验证响应

### 边界条件测试
- [x] 空数据处理
- [x] 大文件处理
- [x] 无效参数处理
- [x] 资源不存在处理

## 运行命令

```bash
# 运行所有API响应测试
python tests/api/test_suite.py

# 运行特定模块测试
python tests/api/test_suite.py auth
python tests/api/test_suite.py cases
python tests/api/test_suite.py knowledge
python tests/api/test_suite.py system
python tests/api/test_suite.py development
python tests/api/test_suite.py consistency

# 运行pytest命令
pytest tests/api/ -v --cov=app.api
```

## 报告生成

测试完成后会生成以下报告：
- HTML覆盖率报告: `htmlcov/api_responses/index.html`
- JUnit XML报告: `test-results/api_responses.xml`
- 终端覆盖率报告: 实时显示

## 注意事项

1. 确保测试数据库已配置
2. 确保Redis服务正在运行
3. 部分测试需要管理员权限
4. 测试会创建临时数据，测试后自动清理
"""

    with open('tests/api/API_RESPONSE_TEST_SUMMARY.md', 'w', encoding='utf-8') as f:
        f.write(summary)

    print("📊 测试摘要已生成: tests/api/API_RESPONSE_TEST_SUMMARY.md")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='API响应测试套件')
    parser.add_argument('module', nargs='?', help='指定要测试的模块 (auth/cases/knowledge/system/development/consistency)')
    parser.add_argument('--summary', action='store_true', help='生成测试摘要')

    args = parser.parse_args()

    if args.summary:
        generate_test_summary()
        sys.exit(0)

    if args.module:
        exit_code = run_specific_module_tests(args.module)
    else:
        exit_code = run_api_response_tests()

    sys.exit(exit_code)
