"""
IP智慧解答专家系统 - Flask应用工厂

本模块负责创建和配置Flask应用实例，初始化各种扩展组件。
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config.settings import Config

# 初始化扩展实例
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_class=Config):
    """
    应用工厂函数，创建并配置Flask应用实例。

    Args:
        config_class: 配置类，默认使用Config

    Returns:
        Flask: 配置好的Flask应用实例
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # 注册蓝图
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

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


# 导入模型以确保它们被SQLAlchemy识别
# 这些导入是必要的，即使看起来未使用，它们确保模型被正确注册
from app.models import user, case, knowledge, feedback  # noqa: F401
