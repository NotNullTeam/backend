"""
IP智慧解答专家系统 - 知识文档API

本模块实现了知识文档相关的API接口。
"""

from app.api import bp


@bp.route('/knowledge/documents', methods=['GET'])
def get_documents():
    """获取文档列表 - 占位实现"""
    return {'message': 'Knowledge API placeholder'}
