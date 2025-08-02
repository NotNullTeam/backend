#!/usr/bin/env python3
"""
API重构脚本

将现有的平铺API结构重构为按功能模块分类的层次结构。
"""

import os
import re
import shutil
from pathlib import Path

def update_blueprint_imports(file_path, old_import, new_import):
    """更新文件中的蓝图导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换导入语句
    content = content.replace(old_import, new_import)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_route_decorators(file_path, route_mappings):
    """更新路由装饰器"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换路由装饰器
    for old_route, new_route in route_mappings.items():
        content = re.sub(
            rf"@bp\.route\('{old_route}'",
            f"@bp.route('{new_route}'",
            content
        )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """主函数"""
    print("🔧 开始API重构...")

    # 定义重构映射
    refactor_mapping = {
        'auth.py': {
            'target': 'v1/auth/routes.py',
            'blueprint_import': 'from app.api.v1.auth import auth_bp as bp',
            'route_mappings': {
                '/auth/login': '/login',
                '/auth/logout': '/logout',
                '/auth/refresh': '/refresh',
                '/auth/me': '/me'
            }
        },
        'cases.py': {
            'target': 'v1/cases/routes.py',
            'blueprint_import': 'from app.api.v1.cases import cases_bp as bp',
            'route_mappings': {
                '/cases': '/',
                '/cases/<': '/<'  # 处理带参数的路由
            }
        },
        'knowledge.py': {
            'target': 'v1/knowledge/documents.py',
            'blueprint_import': 'from app.api.v1.knowledge import knowledge_bp as bp',
            'route_mappings': {
                '/knowledge/documents': '/documents',
                '/knowledge/': '/'
            }
        },
        'search.py': {
            'target': 'v1/knowledge/search.py',
            'blueprint_import': 'from app.api.v1.knowledge import knowledge_bp as bp',
            'route_mappings': {
                '/search': '/search'
            }
        },
        'statistics.py': {
            'target': 'v1/system/statistics.py',
            'blueprint_import': 'from app.api.v1.system import system_bp as bp',
            'route_mappings': {
                '/dashboard': '/dashboard'
            }
        }
    }

    base_path = Path('/Users/ue-dnd/code/project/backend/app/api')

    # 处理每个文件
    for source_file, config in refactor_mapping.items():
        source_path = base_path / source_file
        target_path = base_path / config['target']

        if source_path.exists() and target_path.exists():
            print(f"📝 更新 {config['target']}...")

            # 更新蓝图导入
            update_blueprint_imports(
                target_path,
                'from app.api import bp',
                config['blueprint_import']
            )

            # 更新路由装饰器
            update_route_decorators(target_path, config['route_mappings'])

    print("✅ API重构完成！")

if __name__ == '__main__':
    main()
