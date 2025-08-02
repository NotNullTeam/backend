"""
开发调试模块路由

整合提示词测试、向量数据库管理等开发功能的路由。
"""

from app.api.v1.development import dev_bp as bp

# 导入各个子模块的路由
from app.api.v1.development.prompts import *
from app.api.v1.development.vector import *
