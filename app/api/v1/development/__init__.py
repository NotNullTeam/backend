"""
开发调试相关API

包含提示词测试、向量数据库管理等开发和调试功能。
"""

from flask import Blueprint

# 创建开发调试蓝图
dev_bp = Blueprint('development', __name__, url_prefix='/dev')

# 导入路由
from app.api.v1.development import routes
