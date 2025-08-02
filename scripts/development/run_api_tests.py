#!/usr/bin/env python3
"""
API响应测试快速运行脚本

使用方法：
    python scripts/development/run_api_tests.py                    # 运行所有API响应测试
    python scripts/development/run_api_tests.py auth              # 运行认证模块测试
    python scripts/development/run_api_tests.py cases             # 运行案例模块测试
    python scripts/development/run_api_tests.py knowledge         # 运行知识库模块测试
    python scripts/development/run_api_tests.py system            # 运行系统模块测试
    python scripts/development/run_api_tests.py development       # 运行开发工具模块测试
    python scripts/development/run_api_tests.py consistency       # 运行响应一致性测试
    python scripts/development/run_api_tests.py --coverage        # 运行测试并生成覆盖率报告
"""

import sys
import os
import subprocess
import argparse

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if not os.path.exists(os.path.join(project_root, 'app')):
    print("❌ 找不到项目根目录")
    sys.exit(1)

sys.path.insert(0, project_root)

def get_venv_python():
    """获取虚拟环境的Python路径"""
    venv_python = os.path.join(project_root, '.venv', 'bin', 'python')
    if os.path.exists(venv_python):
        return venv_python
    return 'python'

def run_tests(module=None, coverage=False, verbose=True):
    """运行API响应测试"""

    python_cmd = get_venv_python()

    # 构建pytest命令
    cmd = [python_cmd, '-m', 'pytest']

    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend([
            '--cov=app.api',
            '--cov-report=html:htmlcov/api_responses',
            '--cov-report=term-missing'
        ])

    # 添加测试文件
    if module:
        module_files = {
            'auth': 'tests/api/test_v1_auth_responses.py',
            'cases': 'tests/api/test_v1_cases_responses.py',
            'knowledge': 'tests/api/test_v1_knowledge_responses.py',
            'system': 'tests/api/test_v1_system_responses.py',
            'development': 'tests/api/test_v1_development_responses.py',
            'consistency': 'tests/api/test_response_consistency.py',
            'all': 'tests/api/',  # 添加显式的全部测试选项
        }

        if module not in module_files:
            print(f"❌ 未知模块: {module}")
            print(f"可用模块: {', '.join(module_files.keys())}")
            return 1

        cmd.append(module_files[module])
    else:
        cmd.append('tests/api/')

    # 添加其他参数
    cmd.extend([
        '--tb=short',
        '--disable-warnings'
    ])

    print(f"🧪 运行API响应测试...")
    if module:
        print(f"📦 模块: {module}")
    if coverage:
        print("📊 启用覆盖率报告")

    print("=" * 60)

    # 运行测试
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode
    except FileNotFoundError:
        print(f"❌ 找不到Python解释器: {python_cmd}")
        print("请确保虚拟环境已激活或Python已安装")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='API响应测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'module',
        nargs='?',
        choices=['auth', 'cases', 'knowledge', 'system', 'development', 'consistency', 'all'],
        help='要测试的模块（all表示所有模块）'
    )

    parser.add_argument(
        '--coverage',
        action='store_true',
        help='生成覆盖率报告'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式'
    )

    args = parser.parse_args()

    exit_code = run_tests(
        module=args.module,
        coverage=args.coverage,
        verbose=not args.quiet
    )

    print("=" * 60)
    if exit_code == 0:
        print("✅ 所有测试通过！")
        if args.coverage:
            print("📊 覆盖率报告: htmlcov/api_responses/index.html")
    else:
        print("❌ 部分测试失败")

    sys.exit(exit_code)

if __name__ == '__main__':
    main()
