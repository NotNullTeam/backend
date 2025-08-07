"""
API 文档模块

使用 Flask-RESTX 为所有 API 接口提供统一的文档管理。
所有业务 API 都将通过这个模块进行注册和文档化。
"""
from flask import Blueprint
from flask_restx import Api, Namespace

# 主 API文档蓝图
docs_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# 全局 API 实例
api = None

# API 命名空间
system_ns = None
knowledge_ns = None
cases_ns = None
files_ns = None
user_ns = None
notifications_ns = None
auth_ns = None
analysis_ns = None
development_ns = None


def init_docs(app):
    """初始化 API 文档系统"""
    global api, system_ns, knowledge_ns, cases_ns, files_ns, user_ns, notifications_ns, auth_ns, analysis_ns, development_ns
    
    # 创建主 API 实例
    api = Api(
        docs_bp,
        version='1.0.0',
        title='IP 智慧解答专家 API',
        description='基于RAG与大小模型协同的数通知识问答系统 API 文档',
        doc=False,  # 关闭默认 Swagger UI，由自定义模板提供
        validate=True,
        ordered=True,
        catch_all_404s=True,
        authorizations={
            'Bearer Auth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'JWT令牌认证，格式：Bearer <token>'
            }
        },
        security='Bearer Auth'
    )
    
    # 创建 API 命名空间
    system_ns = api.namespace('system', description='系统管理相关接口')
    knowledge_ns = api.namespace('knowledge', description='知识库管理相关接口')
    cases_ns = api.namespace('cases', description='案例管理相关接口')
    files_ns = api.namespace('files', description='文件管理相关接口')
    user_ns = api.namespace('user', description='用户管理相关接口')
    notifications_ns = api.namespace('notifications', description='通知管理相关接口')
    auth_ns = api.namespace('auth', description='身份认证相关接口')
    analysis_ns = api.namespace('analysis', description='智能分析相关接口')
    development_ns = api.namespace('development', description='开发调试相关接口')
    
    # 初始化所有 API 接口
    from app.api_restx import init_all_apis
    init_all_apis()

    # 自定义文档路由，使用本地模板 swagger-ui.html
    from flask import render_template

    @docs_bp.route('/docs/')
    def custom_swagger_ui():
        """自定义 Swagger UI 页面，使用项目内模板"""
        return render_template('swagger-ui.html')

    print("✅ API 文档系统已初始化 - 访问 /api/v1/docs/ 查看文档 (自定义 UI)")


def get_api():
    """获取全局 API 实例"""
    return api


def get_namespace(name):
    """获取指定的命名空间"""
    namespaces = {
        'system': system_ns,
        'knowledge': knowledge_ns,
        'cases': cases_ns,
        'files': files_ns,
        'user': user_ns,
        'notifications': notifications_ns,
        'auth': auth_ns
    }
    return namespaces.get(name)
