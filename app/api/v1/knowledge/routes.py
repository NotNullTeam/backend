"""
知识管理模块路由

整合文档管理、检索、解析等功能的路由。
"""

from app.api.v1.knowledge import knowledge_bp as bp

# 导入各个子模块的路由
from app.api.v1.knowledge.documents import *
from app.api.v1.knowledge.search import *
from app.api.v1.knowledge.idp import *
