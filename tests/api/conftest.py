"""
API 响应测试的 pytest 配置

专门用于API响应测试的配置文件。
"""

import pytest
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def pytest_configure(config):
    """pytest配置"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "api_response: mark test as API response test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "cases: mark test as cases related"
    )
    config.addinivalue_line(
        "markers", "knowledge: mark test as knowledge related"
    )
    config.addinivalue_line(
        "markers", "system: mark test as system related"
    )
    config.addinivalue_line(
        "markers", "development: mark test as development tools related"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

def pytest_collection_modifyitems(config, items):
    """修改测试项目收集"""
    for item in items:
        # 为所有API测试添加标记
        if "test_api" in item.nodeid or "api" in item.parent.name:
            item.add_marker(pytest.mark.api_response)

        # 根据文件名添加模块标记
        if "auth" in item.parent.name:
            item.add_marker(pytest.mark.auth)
        elif "cases" in item.parent.name:
            item.add_marker(pytest.mark.cases)
        elif "knowledge" in item.parent.name:
            item.add_marker(pytest.mark.knowledge)
        elif "system" in item.parent.name:
            item.add_marker(pytest.mark.system)
        elif "development" in item.parent.name:
            item.add_marker(pytest.mark.development)

        # 标记慢速测试
        if "performance" in item.name or "large" in item.name:
            item.add_marker(pytest.mark.slow)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 确保测试目录存在
    test_results_dir = os.path.join(project_root, 'test-results')
    os.makedirs(test_results_dir, exist_ok=True)

    # 确保覆盖率报告目录存在
    htmlcov_dir = os.path.join(project_root, 'htmlcov', 'api_responses')
    os.makedirs(htmlcov_dir, exist_ok=True)

    print("🔧 API响应测试环境已准备就绪")

def pytest_sessionstart(session):
    """测试会话开始"""
    print("🚀 开始API响应测试会话")

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束"""
    if exitstatus == 0:
        print("🎉 API响应测试会话成功完成")
    else:
        print("❌ API响应测试会话存在失败")

def pytest_runtest_logstart(nodeid, location):
    """测试开始前的日志"""
    pass

def pytest_runtest_logfinish(nodeid, location):
    """测试结束后的日志"""
    pass

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """终端摘要"""
    terminalreporter.write_sep("=", "API响应测试总结")

    if hasattr(terminalreporter.stats, 'passed'):
        passed = len(terminalreporter.stats.get('passed', []))
        terminalreporter.write_line(f"✅ 通过测试: {passed}")

    if hasattr(terminalreporter.stats, 'failed'):
        failed = len(terminalreporter.stats.get('failed', []))
        if failed > 0:
            terminalreporter.write_line(f"❌ 失败测试: {failed}")

    if hasattr(terminalreporter.stats, 'error'):
        errors = len(terminalreporter.stats.get('error', []))
        if errors > 0:
            terminalreporter.write_line(f"🔥 错误测试: {errors}")

    if hasattr(terminalreporter.stats, 'skipped'):
        skipped = len(terminalreporter.stats.get('skipped', []))
        if skipped > 0:
            terminalreporter.write_line(f"⏭️  跳过测试: {skipped}")

    terminalreporter.write_line("📊 详细报告请查看 htmlcov/api_responses/index.html")
