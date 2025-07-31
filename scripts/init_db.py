"""
IP智慧解答专家系统 - 数据库初始化脚本

本脚本用于初始化数据库表结构和创建默认用户。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User
from app.models.case import Case, Node, Edge
from app.models.knowledge import KnowledgeDocument, ParsingJob
from app.models.feedback import Feedback


def init_database():
    """初始化数据库"""
    app = create_app()

    with app.app_context():
        print("正在创建数据库表...")

        # 确保instance目录存在
        instance_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance')
        os.makedirs(instance_dir, exist_ok=True)

        # 创建所有表
        db.create_all()

        print("✅ 数据库表创建成功！")

        # 检查是否已有用户
        if User.query.first() is None:
            print("正在创建默认管理员用户...")

            # 创建默认管理员用户
            admin_user = User(
                username='admin',
                email='admin@example.com',
                roles='admin,user'
            )
            admin_user.set_password('admin123')

            db.session.add(admin_user)
            db.session.commit()

            print("✅ 默认管理员用户创建成功！")
            print("   用户名: admin")
            print("   密码: admin123")
        else:
            print("ℹ️  用户已存在，跳过默认用户创建")

        print("\n🎉 数据库初始化完成！")
        print("\n📋 数据库表结构:")
        print("   - users: 用户表")
        print("   - cases: 诊断案例表")
        print("   - nodes: 节点表")
        print("   - edges: 边表")
        print("   - knowledge_documents: 知识文档表")
        print("   - parsing_jobs: 解析任务表")
        print("   - feedback: 反馈表")


if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
