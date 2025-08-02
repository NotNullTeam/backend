"""
IP智慧解答专家系统 - 配置管理

本模块定义了应用的各种配置选项，包括数据库、JWT、Redis等配置。
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# 项目根目录
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """应用配置类"""

    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "instance", "ip_expert.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)))  # 1小时
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))  # 30天

    # Redis配置
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'

    # 文件上传配置
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

    # AI服务相关配置 - Langchain统一集成
    DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')
    OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE') or 'https://dashscope.aliyuncs.com/compatible-mode/v1'

    # 阿里云文档智能服务配置
    ALIBABA_ACCESS_KEY_ID = os.environ.get('ALIBABA_ACCESS_KEY_ID')
    ALIBABA_ACCESS_KEY_SECRET = os.environ.get('ALIBABA_ACCESS_KEY_SECRET')

    # IDP文档解析配置
    IDP_ENDPOINT = os.environ.get('IDP_ENDPOINT') or 'docmind-api.cn-hangzhou.aliyuncs.com'
    IDP_DEFAULT_ENABLE_LLM = os.environ.get('IDP_DEFAULT_ENABLE_LLM', 'true').lower() == 'true'
    IDP_DEFAULT_ENABLE_FORMULA = os.environ.get('IDP_DEFAULT_ENABLE_FORMULA', 'true').lower() == 'true'
    IDP_MAX_POLLING_ATTEMPTS = int(os.environ.get('IDP_MAX_POLLING_ATTEMPTS', 120))  # 20分钟
    IDP_POLLING_INTERVAL = int(os.environ.get('IDP_POLLING_INTERVAL', 10))  # 10秒

    # OLLAMA本地重排序模型服务配置
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL') or 'http://localhost:11434'

    # Weaviate向量数据库配置
    WEAVIATE_URL = os.environ.get('WEAVIATE_URL') or 'http://localhost:8080'

    # 应用配置
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 10))

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "instance", "test.db")}'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # 生产环境日志配置
        import logging
        from logging.handlers import RotatingFileHandler

        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/ip_expert.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('IP Expert startup')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
