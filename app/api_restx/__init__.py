"""
Flask-RESTX API 接口初始化模块

负责初始化和注册所有的 API 接口到 Flask-RESTX 中。
"""

def init_all_apis():
    """初始化所有API接口"""
    
    # 初始化系统管理API
    from app.api_restx.system import init_system_api
    init_system_api()
    
    # 初始化知识库管理API
    from app.api_restx.knowledge import init_knowledge_api
    init_knowledge_api()
    
    # 初始化身份认证API
    from app.api_restx.auth import init_auth_api
    init_auth_api()
    
    # 初始化案例管理API
    from app.api_restx.cases import init_cases_api
    init_cases_api()
    
    # 初始化文件管理API
    from app.api_restx.files import init_files_api
    init_files_api()
    
    # 初始化用户管理API
    from app.api_restx.user import init_user_api
    init_user_api()
    
    # 初始化通知管理API
    from app.api_restx.notifications import init_notifications_api
    init_notifications_api()
    
    # 初始化智能分析API
    from app.api_restx.analysis import init_analysis_api
    init_analysis_api()
    
    # 初始化开发调试API
    from app.api_restx.development import init_development_api
    init_development_api()
    
    print("✅ 所有API接口已注册到Flask-RESTX文档系统")
