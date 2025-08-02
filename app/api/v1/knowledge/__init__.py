"""
知识管理相关API

包含知识文档管理、检索、解析等功能。
"""

from flask import Blueprint

# 创建知识管理蓝图
knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')

# 导入路由
from app.api.v1.knowledge import routes
