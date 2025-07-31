"""
IP智慧解答专家系统 - API蓝图

本模块定义了API蓝图，用于组织和管理所有的API路由。
"""

from flask import Blueprint

# 创建API蓝图
bp = Blueprint('api', __name__)

# 导入所有API模块以注册路由
from app.api import auth, cases, knowledge, statistics, files, user_settings, notifications, tasks
