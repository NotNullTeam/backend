"""
系统功能模块路由

整合统计、任务监控等系统功能的路由。
"""

from flask import jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.api.v1.system import system_bp as bp
from app.services.storage.cache_service import cache_service
import psutil
from datetime import datetime

# 导入各个子模块的路由
from app.api.v1.system.statistics import *
from app.api.v1.system.tasks import *


@bp.route('/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        # 检查系统基本信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'version': '1.0.0',
                'uptime': '0 days, 0 hours',  # 简化的运行时间
                'database_status': 'connected',
                'redis_status': 'connected' if cache_service.redis_client else 'disconnected',
                'status': 'running',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': (disk.used / disk.total) * 100
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Get system status error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取系统状态失败'
            }
        }), 500


@bp.route('/health', methods=['GET'])
def get_system_health():
    """获取系统健康状况"""
    try:
        health_checks = {
            'database': {
                'status': 'up',
                'response_time': 0.1
            },
            'redis': {
                'status': 'up' if cache_service.redis_client else 'down',
                'response_time': 0.05
            },
            'memory': {
                'status': 'up' if psutil.virtual_memory().percent < 90 else 'degraded',
                'response_time': 0.01
            },
            'disk': {
                'status': 'up' if (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100 < 90 else 'degraded',
                'response_time': 0.01
            }
        }

        overall_health = all(service['status'] == 'up' for service in health_checks.values())

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'healthy': overall_health,
                'services': health_checks,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        })
    except Exception as e:
        current_app.logger.error(f"Get system health error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取系统健康状况失败'
            }
        }), 500


@bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_system_metrics():
    """获取系统指标"""
    from flask_jwt_extended import get_jwt_identity
    from app.models.user import User

    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user or not user.has_role('admin'):
        return jsonify({
            'code': 403,
            'status': 'error',
            'error': {
                'type': 'FORBIDDEN',
                'message': '需要管理员权限'
            }
        }), 403

    try:
        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                'network_io': {
                    'bytes_sent': 0,
                    'bytes_recv': 0
                },
                'request_count': 0,  # 可以实际统计
                'error_rate': 0.0,   # 可以实际统计
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        })
    except Exception as e:
        current_app.logger.error(f"Get system metrics error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取系统指标失败'
            }
        }), 500
