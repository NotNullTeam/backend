"""
API响应格式化工具

提供统一的API响应格式。
"""

from flask import jsonify
from typing import Any, Dict, Optional

def success_response(data: Any = None, message: str = "操作成功", code: int = 200) -> Dict:
    """
    成功响应格式

    Args:
        data: 响应数据
        message: 响应消息
        code: 状态码

    Returns:
        Dict: 格式化的响应
    """
    response = {
        'code': code,
        'status': 'success',
        'message': message
    }

    if data is not None:
        response['data'] = data

    return response

def error_response(message: str, code: int = 400, error_type: str = "BUSINESS_ERROR") -> Dict:
    """
    错误响应格式

    Args:
        message: 错误消息
        code: 状态码
        error_type: 错误类型

    Returns:
        Dict: 格式化的错误响应
    """
    return {
        'code': code,
        'status': 'error',
        'error': {
            'type': error_type,
            'message': message
        }
    }

def paginated_response(items: list, total: int, page: int, page_size: int) -> Dict:
    """
    分页响应格式

    Args:
        items: 数据列表
        total: 总数
        page: 当前页
        page_size: 每页大小

    Returns:
        Dict: 格式化的分页响应
    """
    return success_response({
        'items': items,
        'pagination': {
            'total': total,
            'page': page,
            'pageSize': page_size,
            'pages': (total + page_size - 1) // page_size
        }
    })
