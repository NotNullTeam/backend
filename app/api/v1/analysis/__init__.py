"""
智能分析接口模块

提供AI智能分析功能。
"""

from flask import Blueprint

analysis_bp = Blueprint('analysis', __name__)

from app.api.v1.analysis import routes
