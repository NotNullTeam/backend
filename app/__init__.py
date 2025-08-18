"""
IP智慧解答专家系统 - Flask应用工厂

本模块负责创建和配置Flask应用实例，初始化各种扩展组件。
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import redis
from config.settings import Config

# 初始化扩展实例
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
redis_client = None


def create_app(config_class=Config):
    """
    应用工厂函数，创建并配置Flask应用实例。

    Args:
        config_class: 配置类，默认使用Config

    Returns:
        Flask: 配置好的Flask应用实例
    """
    global redis_client

    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # 初始化Redis客户端
    try:
        redis_client = redis.from_url(app.config['REDIS_URL'])
        redis_client.ping()  # 测试连接
        app.logger.info("Redis连接成功")
    except Exception as e:
        app.logger.warning(f"Redis连接失败: {e}")
        redis_client = None

    # 预加载jieba以避免资源警告
    try:
        import jieba
        jieba.initialize()  # 预先初始化jieba
    except Exception as e:
        app.logger.warning(f"jieba初始化失败: {e}")

    # 注册 v1 业务蓝图
    from app.api.v1 import v1_bp
    app.register_blueprint(v1_bp)

    # 注册错误处理器
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # 配置日志
    from app.logging_config import setup_logging
    setup_logging(app)

    # 注册CLI命令
    register_cli_commands(app)

    return app


def register_cli_commands(app):
    """注册Flask CLI命令"""

    @app.cli.command()
    def init_db():
        """初始化数据库表结构和默认用户"""
        from app.models.user import User

        print("正在创建数据库表...")
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

    @app.cli.command()
    def test_vector():
        """测试向量数据库连接"""
        from app.services.retrieval.vector_service import get_vector_service
        from app.services.storage.vector_db_config import vector_db_config

        print(f"向量数据库类型: {vector_db_config.db_type.value}")
        print(f"配置是否有效: {vector_db_config.is_valid()}")

        try:
            vector_service = get_vector_service()
            print("正在测试向量服务连接...")

            if vector_service.test_connection():
                print("✅ 向量服务连接成功！")

                # 获取统计信息
                stats = vector_service.get_stats()
                print(f"📊 统计信息:")
                print(f"   文档数量: {stats.get('total_documents', 0)}")
                print(f"   向量数量: {stats.get('total_vectors', 0)}")

                # 测试嵌入功能
                print("正在测试嵌入功能...")
                test_text = "这是一个测试文本"
                embedding = vector_service.embedding_service.embed_text(test_text)
                print(f"✅ 嵌入测试成功！向量维度: {len(embedding)}")

            else:
                print("❌ 向量服务连接失败！")

        except Exception as e:
            print(f"❌ 向量服务测试失败: {str(e)}")

    @app.cli.command()
    def vector_stats():
        """显示向量数据库统计信息"""
        from app.services.retrieval.vector_service import get_vector_service

        try:
            vector_service = get_vector_service()
            stats = vector_service.get_stats()

            print("📊 向量数据库统计信息:")
            print(f"   数据库类型: {stats.get('db_type', 'unknown')}")
            print(f"   文档数量: {stats.get('total_documents', 0)}")
            print(f"   向量数量: {stats.get('total_vectors', 0)}")

            if 'storage_path' in stats:
                print(f"   存储路径: {stats['storage_path']}")
            if 'collection_name' in stats:
                print(f"   集合名称: {stats['collection_name']}")

        except Exception as e:
            print(f"❌ 获取统计信息失败: {str(e)}")

    @app.cli.command()
    def clear_vectors():
        """清空所有向量数据"""
        from app.services.retrieval.vector_service import get_vector_service

        import click
        if click.confirm('确定要清空所有向量数据吗？此操作不可逆！'):
            try:
                vector_service = get_vector_service()
                vector_service.vector_db.clear_all()
                print("✅ 向量数据已清空！")
            except Exception as e:
                print(f"❌ 清空向量数据失败: {str(e)}")
        else:
            print("操作已取消")


# 导入模型以确保它们被SQLAlchemy识别
# 这些导入是必要的，即使看起来未使用，它们确保模型被正确注册
from app.models import user, case, knowledge, feedback  # noqa: F401
