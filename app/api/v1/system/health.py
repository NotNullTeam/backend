"""
系统健康检查和服务状态接口
"""

from flask import jsonify, current_app
from flask_jwt_extended import jwt_required

from app.api.v1.system import system_bp as bp
from app.utils.response_helper import success_response, internal_error
from app.config.service_config import service_config
from app.services.retrieval.knowledge_service import knowledge_service
from app.services.network.vendor_command_service import vendor_command_service
from app.services.ai.log_parsing_service import log_parsing_service
from app import db


@bp.route('/health', methods=['GET'])
def health_check():
    """
    系统健康检查

    Returns:
        JSON: 系统各组件的健康状态
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': db.func.now(),
            'services': {}
        }

        # 检查数据库连接
        try:
            db.session.execute(db.text('SELECT 1'))
            health_status['services']['database'] = {
                'status': 'healthy',
                'message': '数据库连接正常'
            }
        except Exception as e:
            health_status['status'] = 'degraded'
            health_status['services']['database'] = {
                'status': 'unhealthy',
                'message': f'数据库连接失败: {str(e)}'
            }

        # 检查服务配置
        config_validation = service_config.validate_config()
        if config_validation['errors']:
            health_status['status'] = 'degraded'
            health_status['services']['configuration'] = {
                'status': 'unhealthy',
                'errors': config_validation['errors'],
                'warnings': config_validation['warnings']
            }
        else:
            health_status['services']['configuration'] = {
                'status': 'healthy',
                'warnings': config_validation['warnings']
            }

        # 检查各个服务状态
        service_status = service_config.get_service_status()
        health_status['services'].update(service_status)

        return success_response(health_status)

    except Exception as e:
        current_app.logger.error(f"Health check error: {str(e)}")
        return internal_error('健康检查失败')


@bp.route('/services/status', methods=['GET'])
@jwt_required()
def get_services_status():
    """
    获取服务详细状态信息

    Returns:
        JSON: 各服务的详细状态和配置信息
    """
    try:
        status_info = {
            'knowledge_service': {
                'enabled': service_config.knowledge_service.vector_db_type != 'mock',
                'config': {
                    'type': service_config.knowledge_service.vector_db_type,
                    'embedding_model': service_config.knowledge_service.embedding_model,
                    'max_results': service_config.knowledge_service.max_results
                },
                'health': 'unknown'
            },
            'log_parsing_service': {
                'enabled': service_config.log_parsing_service.ai_provider != 'mock',
                'config': {
                    'provider': service_config.log_parsing_service.ai_provider,
                    'model': service_config.log_parsing_service.model_name,
                    'max_tokens': service_config.log_parsing_service.max_tokens
                },
                'health': 'unknown'
            },
            'vendor_command_service': {
                'enabled': True,
                'config': {
                    'supported_vendors': vendor_command_service.get_supported_vendors(),
                    'template_types': {}
                },
                'health': 'healthy'
            }
        }

        # 获取各厂商的模板类型
        for vendor in vendor_command_service.get_supported_vendors():
            status_info['vendor_command_service']['config']['template_types'][vendor] = \
                vendor_command_service.get_template_types(vendor)

        return success_response(status_info)

    except Exception as e:
        current_app.logger.error(f"Get services status error: {str(e)}")
        return internal_error('获取服务状态失败')


@bp.route('/services/test', methods=['POST'])
@jwt_required()
def test_services():
    """
    测试各服务功能

    Returns:
        JSON: 服务测试结果
    """
    try:
        test_results = {}

        # 测试知识检索服务
        try:
            test_query = "OSPF neighbor test"
            result = knowledge_service.retrieve_knowledge(
                query=test_query,
                top_k=1
            )
            test_results['knowledge_service'] = {
                'status': 'success',
                'response_time': result['retrievalMetadata']['retrievalTime'],
                'results_count': len(result['sources'])
            }
        except Exception as e:
            test_results['knowledge_service'] = {
                'status': 'failed',
                'error': str(e)
            }

        # 测试厂商命令服务
        try:
            from app.models.case import Node
            test_node = Node(
                type='AI_ANALYSIS',
                title='Test OSPF issue',
                content={'text': 'OSPF neighbor problem'}
            )
            commands = vendor_command_service.generate_commands(test_node, 'Huawei')
            test_results['vendor_command_service'] = {
                'status': 'success',
                'commands_count': len(commands)
            }
        except Exception as e:
            test_results['vendor_command_service'] = {
                'status': 'failed',
                'error': str(e)
            }

        # 测试日志解析服务
        try:
            test_log = "OSPF neighbor ExStart state timeout"
            result = log_parsing_service.parse_log(
                log_type='ospf_debug',
                vendor='Huawei',
                log_content=test_log
            )
            test_results['log_parsing_service'] = {
                'status': 'success',
                'anomalies_detected': len(result['anomalies']),
                'suggestions_count': len(result['suggestedActions'])
            }
        except Exception as e:
            test_results['log_parsing_service'] = {
                'status': 'failed',
                'error': str(e)
            }

        return success_response(test_results)

    except Exception as e:
        current_app.logger.error(f"Test services error: {str(e)}")
        return internal_error('服务测试失败')
