"""
系统功能相关API

包含统计、通知、文件管理、任务监控等系统级功能。
"""

from flask import Blueprint

# 创建系统功能蓝图
system_bp = Blueprint('system', __name__, url_prefix='/system')

# 导入路由
from app.api.v1.system import routes
