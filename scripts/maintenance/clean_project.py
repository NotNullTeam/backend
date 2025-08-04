#!/usr/bin/env python3
"""
项目清理脚本

清理项目中的临时文件、缓存文件等
"""

import os
import shutil
import sys
from pathlib import Path


def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent.parent


def clean_cache_files():
    """清理缓存文件"""
    project_root = get_project_root()

    cache_patterns = [
        '**/__pycache__',
        '.pytest_cache',
        '.coverage',
        'htmlcov',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '.mypy_cache',
        '.ruff_cache'
    ]

    print("🧹 清理缓存文件...")

    for pattern in cache_patterns:
        for path in project_root.glob(pattern):
            if path.exists():
                if path.is_dir():
                    print(f"删除目录: {path}")
                    shutil.rmtree(path)
                else:
                    print(f"删除文件: {path}")
                    path.unlink()

    print("✅ 缓存清理完成！")


def clean_temp_files():
    """清理临时文件"""
    project_root = get_project_root()

    temp_patterns = [
        '**/.DS_Store',
        '**/Thumbs.db',
        '**/*.tmp',
        '**/*.temp',
        '**/*.log.1',
        '**/*.log.2',
        '**/*.log.3'
    ]

    print("🧹 清理临时文件...")

    for pattern in temp_patterns:
        for path in project_root.glob(pattern):
            if path.exists():
                print(f"删除文件: {path}")
                path.unlink()

    print("✅ 临时文件清理完成！")


def clean_empty_dirs():
    """清理空目录"""
    project_root = get_project_root()

    print("🧹 清理空目录...")

    # 从最深层开始检查，避免删除父目录时子目录还没检查
    for root, dirs, files in os.walk(project_root, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                # 检查目录是否为空（忽略隐藏文件）
                if dir_path.exists() and not any(dir_path.iterdir()):
                    print(f"删除空目录: {dir_path}")
                    dir_path.rmdir()
            except (OSError, PermissionError):
                # 目录可能不为空或没有权限
                pass

    print("✅ 空目录清理完成！")


def main():
    """主函数"""
    print("🔧 IP智慧解答专家系统 - 项目清理工具")
    print("=" * 50)

    try:
        clean_cache_files()
        clean_temp_files()
        clean_empty_dirs()

        print("\n🎉 项目清理完成！")

    except Exception as e:
        print(f"❌ 清理过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
