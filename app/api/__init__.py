"""
IP智慧解答专家系统 - API蓝图

本模块定义了API蓝图，用于组织和管理所有的API路由。

重构说明：
- 原有的平铺API文件已经重构为模块化结构
- 新的API结构位于 v1/ 目录下
- 此文件保留用于向后兼容性
"""

from flask import Blueprint

# 创建API蓝图（保留用于向后兼容）
bp = Blueprint('api', __name__)

# 新的模块化API结构已迁移到 v1/ 目录
# 请使用 from app.api.v1 import v1_bp 来访问新的API结构
