"""
文件与附件接口模块

提供文件上传、下载、元数据管理等功能。
"""

from flask import Blueprint

files_bp = Blueprint('files', __name__)

from app.api.v1.files import routes
