"""
案例相关API

包含诊断案例的创建、管理、交互等功能。
"""

from flask import Blueprint

# 创建案例蓝图
cases_bp = Blueprint('cases', __name__, url_prefix='/cases')

# 导入路由
from app.api.v1.cases import routes
