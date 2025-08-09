"""
智能分析 API 接口 (Flask-RESTX)

将原有的智能分析接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.utils.response_helper import success_response, validation_error, internal_error
from app.services.ai.log_parsing_service import log_parsing_service

def init_analysis_api():
    """初始化智能分析API接口"""
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    analysis_ns = get_namespace('analysis')

    # 日志解析请求模型
    log_parsing_model = analysis_ns.model('LogParsingRequest', {
        'logType': fields.String(required=True, description='日志类型',
                                enum=['syslog', 'error', 'debug', 'access', 'security']),
        'vendor': fields.String(required=True, description='设备厂商',
                               enum=['cisco', 'huawei', 'h3c', 'juniper', 'arista']),
        'logContent': fields.String(required=True, description='日志内容'),
        'contextInfo': fields.Raw(description='上下文信息')
    })

    # 日志解析响应模型
    log_parsing_response_model = analysis_ns.model('LogParsingResponse', {
        'parsed_data': fields.Raw(description='解析后的结构化数据'),
        'analysis_result': fields.Raw(description='分析结果'),
        'severity': fields.String(description='严重程度'),
        'recommendations': fields.List(fields.String, description='建议措施'),
        'related_knowledge': fields.List(fields.Raw, description='相关知识')
    })

    @analysis_ns.route('/log-parsing')
    class LogParsing(Resource):
        @analysis_ns.doc('parse_log')
        @analysis_ns.doc(security='Bearer Auth')
        @analysis_ns.expect(log_parsing_model)
        @analysis_ns.marshal_with(log_parsing_response_model)
        @jwt_required()
        def post(self):
            """解析技术日志

            使用AI技术解析各种设备的技术日志，提取关键信息并提供分析结果。
            支持多种日志类型和设备厂商。
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
                valid_log_types = ['syslog', 'error', 'debug', 'access', 'security']
                if log_type not in valid_log_types:
                    return validation_error(f'不支持的日志类型，支持的类型: {", ".join(valid_log_types)}')

                # 验证厂商
                valid_vendors = ['cisco', 'huawei', 'h3c', 'juniper', 'arista']
                if vendor not in valid_vendors:
                    return validation_error(f'不支持的设备厂商，支持的厂商: {", ".join(valid_vendors)}')

                # 调用日志解析服务
                context_info = data.get('contextInfo', {})

                try:
                    # 服务签名不接受 user_id，将其合并进 context_info
                    context_info = context_info or {}
                    if user_id is not None:
                        context_info['userId'] = user_id

                    parsing_result = log_parsing_service.parse_log(
                        log_type=log_type,
                        vendor=vendor,
                        log_content=log_content,
                        context_info=context_info
                    )

                    return {
                        'code': 200,
                        'status': 'success',
                        'data': parsing_result
                    }, 200

                except Exception as parsing_error:
                    current_app.logger.exception(f"日志解析服务错误: {str(parsing_error)}")
                    return {
                        'code': 500,
                        'status': 'error',
                        'error': {'type': 'INTERNAL_ERROR', 'message': '日志解析失败，请稍后重试'}
                    }, 500

            except Exception as e:
                current_app.logger.exception(f"解析日志失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {'type': 'INTERNAL_ERROR', 'message': '解析日志失败'}
                }, 500

    print("✅ 智能分析API接口已注册到Flask-RESTX文档系统")
