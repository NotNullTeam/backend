"""
用户设置接口模块

提供用户个性化配置管理功能。
"""

from flask import Blueprint

user_bp = Blueprint('user', __name__)

from app.api.v1.user import routes
