"""
API v1 模块

提供版本化的API接口。
"""

from flask import Blueprint

# 创建v1蓝图
v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# 导入各个子模块
from app.api.v1.auth import auth_bp
from app.api.v1.cases import cases_bp
from app.api.v1.knowledge import knowledge_bp
from app.api.v1.system import system_bp
from app.api.v1.development import dev_bp

# 注册子蓝图
v1_bp.register_blueprint(auth_bp)
v1_bp.register_blueprint(cases_bp)
v1_bp.register_blueprint(knowledge_bp)
v1_bp.register_blueprint(system_bp)
v1_bp.register_blueprint(dev_bp)
