"""
系统功能模块路由

整合统计、任务监控等系统功能的路由。
"""

from app.api.v1.system import system_bp as bp

# 导入各个子模块的路由
from app.api.v1.system.statistics import *
from app.api.v1.system.tasks import *
