"""
API 文档模块

使用 Flask-RESTX 为所有 API 接口提供统一的文档管理。
所有业务 API 都将通过这个模块进行注册和文档化。
"""
from flask import Blueprint
from flask_restx import Api, Namespace

# 主 API文档蓝图
docs_bp = None

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
    global api, system_ns, knowledge_ns, cases_ns, files_ns, user_ns, notifications_ns, auth_ns, analysis_ns, development_ns, docs_bp

    # 检查是否已经在当前应用上下文中初始化过
    if hasattr(app, '_docs_initialized'):
        return
    app._docs_initialized = True

    # 动态创建蓝图，避免跨应用复用（与业务 /api/v1 路由隔离，防止冲突）
    docs_bp = Blueprint("api_docs", __name__, url_prefix="/api/v1/docs")

    # 创建主 API 实例
    api = Api(
        docs_bp,
        version='1.0.0',
        title='IP 智慧解答专家 API',
        description='基于RAG与大小模型协同的数通知识问答系统 API 文档',
        doc=False,  # 关闭默认 Swagger UI，由自定义模板提供
        validate=True,
        ordered=True,
        catch_all_404s=False,  # 使用我们自定义的404错误处理器
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

    # 初始化所有 API 接口（在蓝图注册之前进行，使用蓝图延迟注册机制）
    from app.api_restx import init_all_apis
    init_all_apis()

    # 自定义文档路由，使用本地模板 swagger-ui.html
    from flask import render_template, render_template_string, jsonify
    from jinja2 import TemplateNotFound

    def _render_swagger_ui():
        try:
            return render_template('swagger-ui.html')
        except TemplateNotFound:
            # 降级HTML，确保测试与运行环境在缺少模板时也能访问
            fallback_html = """
            <!DOCTYPE html>
            <html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>API Docs</title></head>
            <body>
              <div id=\"swagger-ui\"></div>
              <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
              <script>
                const ui = SwaggerUIBundle({ url: '/api/v1/docs/swagger.json', dom_id: '#swagger-ui' });
              </script>
            </body></html>
            """
            return render_template_string(fallback_html)

    # 标准访问：/api/v1/docs/
    @docs_bp.route('/')
    def custom_swagger_ui():
        return _render_swagger_ui()

    # 兼容无斜杠访问：/api/v1/docs
    @docs_bp.route('')
    def custom_swagger_ui_no_slash():
        return _render_swagger_ui()

    # 兼容旧路径：/api/v1/docs/docs/
    @docs_bp.route('/docs/')
    def custom_swagger_ui_compat():
        return _render_swagger_ui()

    # 加一层应用级URL规则，避免极端情况下蓝图未匹配导致的404
    try:
        def _render_swagger_ui_app():
            return _render_swagger_ui()

        app.add_url_rule('/api/v1/docs/', endpoint='api_docs_root_with_slash', view_func=_render_swagger_ui_app, methods=['GET'])
        app.add_url_rule('/api/v1/docs', endpoint='api_docs_root_no_slash', view_func=_render_swagger_ui_app, methods=['GET'])
        app.add_url_rule('/api/v1/docs/docs/', endpoint='api_docs_root_compat', view_func=_render_swagger_ui_app, methods=['GET'])
    except Exception as e:
        print(f"⚠️ 应用级文档URL注册失败: {e}")

    # 兼容开发文档与OpenAPI规范端点
    @docs_bp.route('/dev/docs')
    def dev_docs():
        """开发环境API文档页面"""
        html_template = """
        <!DOCTYPE html><html><head><meta charset='utf-8'><title>API Docs</title></head>
        <body><h1>IP智慧解答专家系统 API 文档</h1>
        <ul>
            <li><a href="/api/v1/docs/dev/openapi.json">OpenAPI规范</a></li>
            <li><a href="/api/v1/docs/">Swagger UI</a></li>
        </ul>
        </body></html>
        """
        return render_template_string(html_template)

    @docs_bp.route('/dev/openapi.json')
    def dev_openapi():
        """获取OpenAPI规范文档"""
        return jsonify({
            'openapi': '3.0.0',
            'info': {
                'title': 'IP智慧解答专家系统 API',
                'version': '1.0.0',
                'description': 'IP网络专家诊断系统的RESTful API文档'
            },
            'servers': [{'url': '/api/v1', 'description': 'API v1'}],
            'paths': {},
            'components': {
                'schemas': {},
                'securitySchemes': {
                    'BearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT'
                    }
                }
            }
        })

    # 通过蓝图提供规范与文档页面（如果蓝图被注册）
    @docs_bp.route('/swagger.json')
    def swagger_json():
        return jsonify(api.__schema__)

    # 确保文档蓝图已注册到应用
    try:
        if 'api_docs' not in app.blueprints:
            app.register_blueprint(docs_bp)
    except Exception as e:
        print(f"⚠️ 注册文档蓝图失败: {e}")

    print("✅ API 文档系统已初始化 - 访问 /api/v1/docs/ 查看文档 (自定义 UI)，/api/v1/docs/swagger.json 获取规范")


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
        'auth': auth_ns,
        'analysis': analysis_ns,
        'development': development_ns
    }
    return namespaces.get(name)
