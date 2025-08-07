"""
响应格式统一助手

提供统一的API响应格式化功能，确保所有接口返回一致的响应结构。
"""

from flask import jsonify


def success_response(data=None, code=200, message=None):
    """
    生成成功响应

    Args:
        data: 响应数据
        code: HTTP状态码，默认200
        message: 可选的消息（为了兼容性，通常不使用）

    Returns:
        Flask Response对象
    """
    response = {
        'code': code,
        'status': 'success'
    }

    if data is not None:
        response['data'] = data

    # message参数为了兼容性而添加，但通常不使用
    if message is not None:
        response['message'] = message

    return jsonify(response), code


def error_response(error_type, message, code=400):
    """
    生成错误响应

    Args:
        error_type: 错误类型，如 'INVALID_REQUEST', 'NOT_FOUND' 等
        message: 错误消息
        code: HTTP状态码，默认400

    Returns:
        Flask Response对象
    """
    response = {
        'code': code,
        'status': 'error',
        'error': {
            'type': error_type,
            'message': message
        }
    }

    return jsonify(response), code


def validation_error(message, code=400):
    """生成参数校验错误响应"""
    return error_response('INVALID_REQUEST', message, code)


def not_found_error(message="资源不存在", code=404):
    """生成资源不存在错误响应"""
    return error_response('NOT_FOUND', message, code)


def unauthorized_error(message="未认证或认证失败", code=401):
    """生成未认证错误响应"""
    return error_response('UNAUTHORIZED', message, code)


def forbidden_error(message="无权限访问该资源", code=403):
    """生成无权限错误响应"""
    return error_response('FORBIDDEN', message, code)


def conflict_error(message="资源冲突", code=409):
    """生成资源冲突错误响应"""
    return error_response('CONFLICT', message, code)


def unprocessable_error(message="业务规则校验失败", code=422):
    """生成业务规则校验失败错误响应"""
    return error_response('UNPROCESSABLE_ENTITY', message, code)


def rate_limit_error(message="请求过于频繁", code=429):
    """生成限流错误响应"""
    return error_response('RATE_LIMITED', message, code)


def internal_error(message="服务器内部错误", code=500):
    """生成服务器错误响应"""
    return error_response('INTERNAL_ERROR', message, code)


def service_unavailable_error(message="服务暂不可用", code=503):
    """生成服务不可用错误响应"""
    return error_response('SERVICE_UNAVAILABLE', message, code)


def paginated_response(items, pagination_info, code=200):
    """
    生成分页响应

    Args:
        items: 数据项列表
        pagination_info: 分页信息字典，包含 total, page, per_page, pages
        code: HTTP状态码，默认200

    Returns:
        Flask Response对象
    """
    data = {
        'items': items,
        'pagination': pagination_info
    }

    return success_response(data, code)
