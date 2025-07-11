#!/usr/bin/env python3
"""
IP智慧解答专家系统 - 测试运行脚本

本脚本提供了便捷的测试运行命令。
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent  # 因为脚本在scripts目录下
sys.path.insert(0, str(project_root))


def run_command(cmd, description):
    """运行命令并处理结果"""
    print(f"\n🔄 {description}")
    print(f"命令: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        # 切换到项目根目录执行命令
        result = subprocess.run(cmd, check=True, capture_output=False, cwd=project_root)
        print(f"✅ {description} - 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失败 (退出码: {e.returncode})")
        return False
    except FileNotFoundError:
        print(f"❌ {description} - 命令未找到: {cmd[0]}")
        return False


def check_environment():
    """检查测试环境"""
    print("🔍 检查测试环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 9):
        print("❌ Python版本过低，需要3.9+")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查pytest是否安装
    try:
        import pytest
        print(f"✅ pytest版本: {pytest.__version__}")
    except ImportError:
        print("❌ pytest未安装，请运行: pip install -r requirements.txt")
        return False
    
    # 检查项目结构
    required_files = [
        'app/__init__.py',
        'tests/conftest.py',
        'pytest.ini',
        'requirements.txt'
    ]
    
    for file_path in required_files:
        if not (project_root / file_path).exists():
            print(f"❌ 缺少文件: {file_path}")
            return False
    
    print("✅ 项目结构检查通过")
    return True


def run_all_tests():
    """运行所有测试"""
    cmd = ['python', '-m', 'pytest', '-v']
    return run_command(cmd, "运行所有测试")


def run_unit_tests():
    """运行单元测试"""
    cmd = ['python', '-m', 'pytest', '-v', '-m', 'unit']
    return run_command(cmd, "运行单元测试")


def run_integration_tests():
    """运行集成测试"""
    cmd = ['python', '-m', 'pytest', '-v', '-m', 'integration']
    return run_command(cmd, "运行集成测试")


def run_auth_tests():
    """运行认证测试"""
    cmd = ['python', '-m', 'pytest', '-v', '-m', 'auth']
    return run_command(cmd, "运行认证测试")


def run_model_tests():
    """运行模型测试"""
    cmd = ['python', '-m', 'pytest', '-v', '-m', 'models']
    return run_command(cmd, "运行模型测试")


def run_api_tests():
    """运行API测试"""
    cmd = ['python', '-m', 'pytest', '-v', '-m', 'api']
    return run_command(cmd, "运行API测试")


def run_coverage_report():
    """生成覆盖率报告"""
    cmd = ['python', '-m', 'pytest', '--cov=app', '--cov-report=term-missing', '--cov-report=html']
    return run_command(cmd, "生成覆盖率报告")


def run_specific_test(test_path):
    """运行特定测试"""
    cmd = ['python', '-m', 'pytest', '-v', test_path]
    return run_command(cmd, f"运行测试: {test_path}")


def open_coverage_report():
    """打开覆盖率报告"""
    coverage_file = project_root / 'htmlcov' / 'index.html'
    
    if not coverage_file.exists():
        print("❌ 覆盖率报告不存在，请先运行覆盖率测试")
        return False
    
    try:
        if sys.platform.startswith('darwin'):  # macOS
            subprocess.run(['open', str(coverage_file)])
        elif sys.platform.startswith('linux'):  # Linux
            subprocess.run(['xdg-open', str(coverage_file)])
        elif sys.platform.startswith('win'):  # Windows
            subprocess.run(['start', str(coverage_file)], shell=True)
        else:
            print(f"请手动打开: {coverage_file}")
        
        print(f"✅ 覆盖率报告已打开: {coverage_file}")
        return True
    except Exception as e:
        print(f"❌ 无法打开覆盖率报告: {e}")
        return False


def install_dependencies():
    """安装测试依赖"""
    cmd = ['pip', 'install', '-r', 'requirements.txt']
    return run_command(cmd, "安装测试依赖")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='IP智慧解答专家系统测试运行器')
    parser.add_argument('command', nargs='?', default='all',
                       choices=['all', 'unit', 'integration', 'auth', 'models', 'api', 
                               'coverage', 'install', 'check', 'open-coverage'],
                       help='要执行的测试命令')
    parser.add_argument('--test', '-t', help='运行特定测试文件或测试方法')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    parser.add_argument('--no-check', action='store_true', help='跳过环境检查')
    
    args = parser.parse_args()
    
    print("🧪 IP智慧解答专家系统 - 测试运行器")
    print("=" * 50)
    
    # 环境检查
    if not args.no_check:
        if not check_environment():
            print("\n❌ 环境检查失败，请修复问题后重试")
            sys.exit(1)
    
    success = True
    
    # 执行命令
    if args.test:
        success = run_specific_test(args.test)
    elif args.command == 'all':
        success = run_all_tests()
    elif args.command == 'unit':
        success = run_unit_tests()
    elif args.command == 'integration':
        success = run_integration_tests()
    elif args.command == 'auth':
        success = run_auth_tests()
    elif args.command == 'models':
        success = run_model_tests()
    elif args.command == 'api':
        success = run_api_tests()
    elif args.command == 'coverage':
        success = run_coverage_report()
    elif args.command == 'install':
        success = install_dependencies()
    elif args.command == 'check':
        success = check_environment()
    elif args.command == 'open-coverage':
        success = open_coverage_report()
    
    # 输出结果
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试运行完成")
        
        if args.command == 'coverage':
            print("\n💡 提示:")
            print("   - 查看HTML报告: python scripts/run_tests.py open-coverage")
            print("   - 覆盖率目标: ≥ 80%")
        
        sys.exit(0)
    else:
        print("❌ 测试运行失败")
        print("\n💡 调试提示:")
        print("   - 查看详细错误: python scripts/run_tests.py all -v")
        print("   - 运行特定测试: python scripts/run_tests.py --test tests/test_auth_api.py")
        print("   - 检查环境: python scripts/run_tests.py check")
        
        sys.exit(1)


if __name__ == '__main__':
    main()
