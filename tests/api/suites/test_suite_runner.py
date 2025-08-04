"""
综合测试套件运行器

用于运行多个测试文件并生成综合报告的工具。
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path


class TestSuiteRunner:
    """测试套件运行器基类"""

    def __init__(self, suite_name="测试套件"):
        self.suite_name = suite_name
        self.project_root = Path(__file__).parent.parent.parent.parent

    def run_test_file(self, test_file_path, test_name=None):
        """运行单个测试文件"""
        if not test_name:
            test_name = Path(test_file_path).stem

        full_path = self.project_root / test_file_path

        if not full_path.exists():
            raise FileNotFoundError(f"测试文件不存在: {full_path}")

        print(f"🧪 运行 {test_name} 测试...")

        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            str(full_path),
            '-v', '--tb=short'
        ], capture_output=True, text=True, cwd=str(self.project_root))

        return {
            'name': test_name,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'passed': result.returncode == 0
        }

    def run_multiple_tests(self, test_files):
        """运行多个测试文件"""
        print(f"🚀 开始运行{self.suite_name}...")
        print("=" * 60)

        results = []

        for test_file in test_files:
            try:
                if isinstance(test_file, dict):
                    result = self.run_test_file(test_file['path'], test_file.get('name'))
                else:
                    result = self.run_test_file(test_file)

                results.append(result)

                if result['passed']:
                    print(f"✅ {result['name']} 测试通过")
                    self._print_test_summary(result['stdout'])
                else:
                    print(f"❌ {result['name']} 测试失败")
                    print(f"错误: {result['stderr']}")

            except Exception as e:
                print(f"💥 {test_file} 执行异常: {str(e)}")
                results.append({
                    'name': str(test_file),
                    'passed': False,
                    'error': str(e)
                })

        self._print_final_summary(results)
        return results

    def _print_test_summary(self, stdout):
        """打印测试结果摘要"""
        lines = stdout.split('\n')
        for line in lines:
            if 'passed' in line and ('failed' in line or 'error' in line or '::' not in line):
                print(f"   📊 {line.strip()}")
                break

    def _print_final_summary(self, results):
        """打印最终汇总"""
        print("\n" + "=" * 60)
        passed_count = sum(1 for r in results if r['passed'])
        total_count = len(results)

        if passed_count == total_count:
            print(f"🎉 所有测试通过！({passed_count}/{total_count})")
        else:
            print(f"⚠️  部分测试失败 ({passed_count}/{total_count} 通过)")

        return passed_count == total_count


class DeprecatedFeaturesTestSuite(TestSuiteRunner):
    """已废弃功能测试套件"""

    def __init__(self):
        super().__init__("已废弃功能测试套件")

    def run_deprecated_tests(self):
        """运行已废弃的功能测试"""
        test_files = [
            {
                'path': 'tests/api/deprecated/test_v1_token_refresh_compatibility.py',
                'name': 'Token刷新兼容性测试'
            },
            {
                'path': 'tests/api/deprecated/test_v1_attachment_filter.py',
                'name': '附件类型过滤测试'
            },
            {
                'path': 'tests/api/deprecated/test_v1_auth_me_response.py',
                'name': 'auth/me响应格式测试'
            }
        ]

        return self.run_multiple_tests(test_files)


class MainTestSuite(TestSuiteRunner):
    """主要测试套件"""

    def __init__(self):
        super().__init__("主要API测试套件")

    def run_v1_api_tests(self):
        """运行v1 API测试"""
        test_files = [
            {
                'path': 'tests/api/v1/test_v1_auth_responses.py',
                'name': '认证API响应测试'
            },
            {
                'path': 'tests/api/v1/test_v1_cases_responses.py',
                'name': '案例API响应测试'
            },
            {
                'path': 'tests/api/v1/test_v1_knowledge_responses.py',
                'name': '知识库API响应测试'
            },
            {
                'path': 'tests/api/v1/test_v1_system_responses.py',
                'name': '系统API响应测试'
            },
            {
                'path': 'tests/api/v1/test_v1_development_responses.py',
                'name': '开发工具API响应测试'
            },
            {
                'path': 'tests/api/v1/test_response_consistency.py',
                'name': '响应一致性测试'
            }
        ]

        return self.run_multiple_tests(test_files)


def main():
    """主函数"""
    print("🔧 测试套件选择器")
    print("1. 运行主要API测试套件")
    print("2. 运行已废弃功能测试")
    print("3. 运行所有测试")

    choice = input("请选择要运行的测试套件 (1-3): ").strip()

    if choice == "1":
        suite = MainTestSuite()
        results = suite.run_v1_api_tests()
    elif choice == "2":
        suite = DeprecatedFeaturesTestSuite()
        results = suite.run_deprecated_tests()
    elif choice == "3":
        print("运行所有测试...")
        main_suite = MainTestSuite()
        deprecated_suite = DeprecatedFeaturesTestSuite()

        main_results = main_suite.run_v1_api_tests()
        deprecated_results = deprecated_suite.run_deprecated_tests()

        all_passed = all(r['passed'] for r in main_results + deprecated_results)
        results = main_results + deprecated_results
    else:
        print("无效选择")
        return 1

    # 返回退出码
    all_passed = all(r['passed'] for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
