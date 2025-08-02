"""
提示词工程API

本模块提供用于测试和管理提示词的API端点。
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1.development import dev_bp as bp
from app.services.llm_service import LLMService
from app.services.cache_service import get_cache_service
from app.utils.monitoring import get_monitor
import logging

logger = logging.getLogger(__name__)


@bp.route('/test/analysis', methods=['POST'])
@jwt_required()
def test_analysis_prompt():
    """测试问题分析提示词"""
    try:
        data = request.get_json()
        query = data.get('query')
        context = data.get('context', '')
        vendor = data.get('vendor')

        if not query:
            return jsonify({
                'success': False,
                'error': '查询内容不能为空'
            }), 400

        # 调用LLM服务
        llm_service = LLMService()
        result = llm_service.analyze_query(
            query=query,
            context=context,
            vendor=vendor
        )

        return jsonify({
            'success': True,
            'data': result,
            'test_type': 'analysis'
        })

    except Exception as e:
        logger.error(f"分析提示词测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/test/clarification', methods=['POST'])
@jwt_required()
def test_clarification_prompt():
    """测试澄清问题提示词"""
    try:
        data = request.get_json()
        query = data.get('query')
        analysis = data.get('analysis', {})
        vendor = data.get('vendor')

        if not query:
            return jsonify({
                'success': False,
                'error': '查询内容不能为空'
            }), 400

        # 调用LLM服务
        llm_service = LLMService()
        result = llm_service.generate_clarification(
            query=query,
            analysis=analysis,
            vendor=vendor
        )

        return jsonify({
            'success': True,
            'data': result,
            'test_type': 'clarification'
        })

    except Exception as e:
        logger.error(f"澄清提示词测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/test/solution', methods=['POST'])
@jwt_required()
def test_solution_prompt():
    """测试解决方案提示词"""
    try:
        data = request.get_json()
        query = data.get('query')
        context = data.get('context', [])
        analysis = data.get('analysis', {})
        user_context = data.get('user_context', '')
        vendor = data.get('vendor', '通用')

        if not query:
            return jsonify({
                'success': False,
                'error': '查询内容不能为空'
            }), 400

        # 调用LLM服务
        llm_service = LLMService()
        result = llm_service.generate_solution(
            query=query,
            context=context,
            analysis=analysis,
            user_context=user_context,
            vendor=vendor
        )

        return jsonify({
            'success': True,
            'data': result,
            'test_type': 'solution'
        })

    except Exception as e:
        logger.error(f"解决方案提示词测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/test/conversation', methods=['POST'])
@jwt_required()
def test_conversation_prompt():
    """测试多轮对话提示词"""
    try:
        data = request.get_json()
        conversation_history = data.get('conversation_history', [])
        new_query = data.get('new_query')
        problem_status = data.get('problem_status', '进行中')

        if not new_query:
            return jsonify({
                'success': False,
                'error': '新查询内容不能为空'
            }), 400

        # 调用LLM服务
        llm_service = LLMService()
        result = llm_service.continue_conversation(
            conversation_history=conversation_history,
            new_query=new_query,
            problem_status=problem_status
        )

        return jsonify({
            'success': True,
            'data': result,
            'test_type': 'conversation'
        })

    except Exception as e:
        logger.error(f"对话提示词测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/test/feedback', methods=['POST'])
@jwt_required()
def test_feedback_prompt():
    """测试反馈处理提示词"""
    try:
        data = request.get_json()
        original_problem = data.get('original_problem')
        provided_solution = data.get('provided_solution')
        user_feedback = data.get('user_feedback')

        if not all([original_problem, provided_solution, user_feedback]):
            return jsonify({
                'success': False,
                'error': '原问题、解决方案和用户反馈都不能为空'
            }), 400

        # 调用LLM服务
        llm_service = LLMService()
        result = llm_service.process_feedback(
            original_problem=original_problem,
            provided_solution=provided_solution,
            user_feedback=user_feedback
        )

        return jsonify({
            'success': True,
            'data': result,
            'test_type': 'feedback'
        })

    except Exception as e:
        logger.error(f"反馈提示词测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/vendors', methods=['GET'])
@jwt_required()
def get_supported_vendors():
    """获取支持的设备厂商列表"""
    try:
        vendors = [
            {'name': '华为', 'value': '华为', 'description': '华为VRP系统'},
            {'name': '思科', 'value': '思科', 'description': '思科IOS/IOS-XE系统'},
            {'name': 'H3C', 'value': 'H3C', 'description': 'H3C Comware系统'},
            {'name': '锐捷', 'value': '锐捷', 'description': '锐捷RGOS系统'},
            {'name': '通用', 'value': '通用', 'description': '通用网络设备'}
        ]

        return jsonify({
            'success': True,
            'data': vendors
        })

    except Exception as e:
        logger.error(f"获取厂商列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/performance', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """获取LLM服务性能指标"""
    try:
        monitor = get_monitor()

        # 获取各个操作的统计信息
        stats = monitor.get_all_stats(time_window=3600)  # 1小时窗口
        health = monitor.get_health_status()

        return jsonify({
            'success': True,
            'data': {
                'statistics': stats,
                'health': health
            }
        })

    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/cache/status', methods=['GET'])
@jwt_required()
def get_cache_status():
    """获取缓存状态"""
    try:
        cache_service = get_cache_service()
        cache_info = cache_service.get_cache_info()

        return jsonify({
            'success': True,
            'data': cache_info
        })

    except Exception as e:
        logger.error(f"获取缓存状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/cache/clear', methods=['POST'])
@jwt_required()
def clear_cache():
    """清除缓存"""
    try:
        data = request.get_json()
        pattern = data.get('pattern', 'llm:*')  # 默认清除所有LLM缓存

        cache_service = get_cache_service()
        cleared_count = cache_service.clear_pattern(pattern)

        return jsonify({
            'success': True,
            'data': {
                'cleared_count': cleared_count,
                'pattern': pattern
            }
        })

    except Exception as e:
        logger.error(f"清除缓存失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 测试LLM服务连接
        llm_service = LLMService()

        # 简单的连通性测试
        test_result = llm_service.analyze_query(
            query="测试连接",
            context="",
            vendor=None
        )

        llm_healthy = 'error' not in test_result

        # 获取缓存状态
        cache_service = get_cache_service()
        cache_info = cache_service.get_cache_info()
        cache_healthy = cache_info.get('connected', False)

        overall_status = 'healthy' if llm_healthy and cache_healthy else 'degraded'

        return jsonify({
            'status': overall_status,
            'services': {
                'llm': 'healthy' if llm_healthy else 'unhealthy',
                'cache': 'healthy' if cache_healthy else 'unhealthy'
            },
            'timestamp': get_monitor().get_health_status().get('timestamp')
        })

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
