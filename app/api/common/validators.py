"""
API验证器

提供通用的请求参数验证功能。
"""

from functools import wraps
from flask import request, jsonify
from typing import Dict, List, Any, Optional

def validate_json(*required_fields: str):
    """
    验证JSON请求体装饰器

    Args:
        required_fields: 必需的字段名列表
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '请求内容类型必须是application/json'
                    }
                }), 400

            data = request.get_json()
            if not data:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '请求体不能为空'
                    }
                }), 400

            # 检查必需字段
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None:
                    missing_fields.append(field)

            if missing_fields:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'MISSING_FIELDS',
                        'message': f'缺少必需的字段: {", ".join(missing_fields)}'
                    }
                }), 400

            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_pagination():
    """
    验证分页参数装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                page = int(request.args.get('page', 1))
                page_size = int(request.args.get('pageSize', 10))

                if page < 1:
                    page = 1
                if page_size < 1 or page_size > 100:
                    page_size = 10

                # 将验证后的参数传递给视图函数
                return func(*args, page=page, page_size=page_size, **kwargs)
            except ValueError:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_PAGINATION',
                        'message': '分页参数必须是有效的数字'
                    }
                }), 400
        return wrapper
    return decorator
