"""
IP智慧解答专家系统 - 通知API

本模块实现了通知相关的API接口。
"""

from app.api import bp


@bp.route('/notifications', methods=['GET'])
def get_notifications():
    """获取通知列表 - 占位实现"""
    return {'message': 'Notifications API placeholder'}
