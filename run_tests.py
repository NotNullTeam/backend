#!/usr/bin/env python3
"""
测试运行脚本

提供便捷的测试运行命令。
"""

import os
import sys
import argparse
import subprocess

def run_tests(test_type=None, verbose=False, coverage=False, parallel=False):
    """运行测试"""
    # 使用虚拟环境中的Python
    python_path = sys.executable
    cmd = [python_path, '-m', 'pytest']

    # 根据测试类型选择测试目录
    if test_type == 'unit':
        cmd.append('tests/unit')
    elif test_type == 'api':
        cmd.append('tests/api')
    elif test_type == 'services':
        cmd.append('tests/services')
    elif test_type == 'models':
        cmd.append('tests/models')
    elif test_type == 'integration':
        cmd.append('tests/integration')
    elif test_type == 'all':
        cmd.append('tests')
    else:
        cmd.append('tests')

    # 添加选项
    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend(['--cov=app', '--cov-report=html', '--cov-report=term-missing'])

    if parallel:
        cmd.extend(['-n', 'auto'])

    # 运行测试
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode

def main():
    parser = argparse.ArgumentParser(description='运行测试套件')
    parser.add_argument('--type', '-t',
                       choices=['unit', 'api', 'services', 'models', 'integration', 'all'],
                       default='all',
                       help='测试类型')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--coverage', '-c', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--parallel', '-p', action='store_true', help='并行运行测试')

    args = parser.parse_args()

    print(f"🧪 运行{args.type}测试...")
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel
    )

    if exit_code == 0:
        print("✅ 测试全部通过!")
    else:
        print("❌ 测试失败!")

    sys.exit(exit_code)

if __name__ == '__main__':
    main()
