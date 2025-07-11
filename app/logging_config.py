"""
IP智慧解答专家系统 - 日志配置

本模块负责配置应用的日志系统。
"""

import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(app):
    """
    设置应用日志配置
    
    Args:
        app: Flask应用实例
    """
    if not app.debug and not app.testing:
        # 创建日志目录
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # 配置文件日志处理器
        file_handler = RotatingFileHandler(
            'logs/ip_expert.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('IP Expert startup')
    else:
        # 开发环境使用控制台日志
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
