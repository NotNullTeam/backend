"""
认证相关API

包含用户认证、用户设置等功能。
"""

from flask import Blueprint

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 导入路由
from app.api.v1.auth import routes
