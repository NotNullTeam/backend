"""
IP智慧解答专家系统 - 应用启动文件

本文件用于启动Flask开发服务器。
"""

import os
from app import create_app, db
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback

# 创建Flask应用实例
app = create_app()


@app.shell_context_processor
def make_shell_context():
    """
    为Flask shell提供上下文

    Returns:
        dict: shell上下文字典
    """
    return {
        'db': db,
        'User': User,
        'Case': Case,
        'Node': Node,
        'Edge': Edge,
        'KnowledgeDocument': KnowledgeDocument,
        'ParsingJob': ParsingJob,
        'Feedback': Feedback
    }


def check_database_initialized():
    """检查数据库是否已初始化"""
    with app.app_context():
        try:
            # 确保instance目录存在
            instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
            os.makedirs(instance_dir, exist_ok=True)

            # 尝试创建表（如果不存在）
            db.create_all()

            # 检查是否有默认用户
            if User.query.first() is None:
                print("\n⚠️  检测到数据库未初始化（无默认用户）")
                print("请运行以下命令之一来创建默认用户：")
                print("  1. python scripts/init_db.py")
                return False
            return True
        except Exception as e:
            print(f"\n⚠️  数据库初始化失败: {str(e)}")
            print("请检查数据库配置或运行: python scripts/init_db.py")
            return False


if __name__ == '__main__':
    # 检查数据库初始化状态（可选）
    if not check_database_initialized():
        print("\n是否继续启动服务？(y/N): ", end="")
        if input().lower() != 'y':
            exit(1)

    # 开发环境启动配置
    print("\n🚀 启动IP智慧解答专家系统...")
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )
