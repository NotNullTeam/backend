"""
智能分析接口路由

提供AI智能分析功能，包括日志解析等。
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1.analysis import analysis_bp as bp
from app.utils.response_helper import (
    success_response, validation_error, internal_error
)
from app.services.ai.log_parsing_service import log_parsing_service


@bp.route('/log-parsing', methods=['POST'])
@jwt_required()
def parse_log():
    """
    解析技术日志

    请求体:
    - logType: 日志类型 (必需)
    - vendor: 设备厂商 (必需)
    - logContent: 日志内容 (必需)
    - contextInfo: 上下文信息 (可选)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return validation_error('请求体不能为空')

        # 验证必需参数
        log_type = data.get('logType')
        vendor = data.get('vendor')
        log_content = data.get('logContent')

        if not log_type:
            return validation_error('日志类型不能为空')

        if not vendor:
            return validation_error('设备厂商不能为空')

        if not log_content or not log_content.strip():
            return validation_error('日志内容不能为空')

        # 验证日志类型
        valid_log_types = ['debug_ip_packet', 'ospf_debug', 'bgp_debug', 'system_log']
        if log_type not in valid_log_types:
            return validation_error(f'无效的日志类型，支持: {", ".join(valid_log_types)}')

        # 验证厂商
        valid_vendors = ['Huawei', 'Cisco', 'Juniper', 'H3C']
        if vendor not in valid_vendors:
            return validation_error(f'无效的设备厂商，支持: {", ".join(valid_vendors)}')

        # 获取上下文信息
        context_info = data.get('contextInfo', {})

        # 调用真实的AI日志解析服务
        try:
            analysis_result = log_parsing_service.parse_log(
                log_type=log_type,
                vendor=vendor,
                log_content=log_content,
                context_info=context_info
            )

            return success_response(analysis_result)

        except Exception as parsing_error:
            current_app.logger.error(f"Log parsing service error: {str(parsing_error)}")
            # 如果解析服务失败，返回基础分析结果
            return success_response({
                'summary': '日志解析服务暂不可用，请稍后重试',
                'anomalies': [],
                'suggestedActions': [],
                'keyEvents': [],
                'logMetrics': {
                    'totalLines': len(log_content.split('\n')) if log_content else 0,
                    'anomalyCount': 0,
                    'timeRange': None,
                    'vendor': vendor,
                    'logType': log_type
                }
            })

    except Exception as e:
        current_app.logger.error(f"Log parsing error: {str(e)}")
        return internal_error('日志解析时发生错误')
