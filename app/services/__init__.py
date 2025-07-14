"""
IP智慧解答专家系统 - 服务模块

本模块提供各种业务服务的实现。
"""

import redis
from rq import Queue
from flask import current_app

def get_redis_connection():
    """获取Redis连接"""
    return redis.from_url(current_app.config['REDIS_URL'])

def get_task_queue():
    """获取任务队列"""
    return Queue('default', connection=get_redis_connection())
