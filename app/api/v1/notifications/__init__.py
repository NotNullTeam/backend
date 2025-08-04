"""
通知接口模块

提供系统通知管理功能。
"""

from flask import Blueprint

notifications_bp = Blueprint('notifications', __name__)

from app.api.v1.notifications import routes
