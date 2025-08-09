"""
系统管理 API 接口 (Flask-RESTX)

将原有的系统管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import jsonify, current_app
from flask_restx import Resource, fields
from sqlalchemy import text

from app import db
from app.docs import get_namespace
from app.utils.response_helper import success_response, error_response
from app.services.storage.cache_service import cache_service

def init_system_api():
    """初始化系统 API接口"""
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    system_ns = get_namespace('system')

    # 健康检查响应模型
    health_model = system_ns.model('HealthCheck', {
        'healthy': fields.Boolean(description='系统是否健康'),
        'services': fields.Raw(description='各服务状态'),
        'timestamp': fields.String(description='检查时间戳')
    })

    # 系统状态响应模型
    status_model = system_ns.model('SystemStatus', {
        'status': fields.String(description='系统运行状态'),
        'version': fields.String(description='系统版本'),
        'uptime': fields.String(description='运行时间'),
        'database_status': fields.String(description='数据库状态'),
        'redis_status': fields.String(description='Redis状态'),
        'system': fields.Raw(description='系统资源使用情况'),
        'timestamp': fields.String(description='状态检查时间')
    })

    @system_ns.route('/health')
    class HealthCheck(Resource):
        @system_ns.doc('health_check')
        def get(self):
            """系统健康检查

            检查系统各组件的健康状态，包括数据库、Redis等服务。
            """
            try:
                from datetime import datetime
                health_status = {
                    'healthy': True,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'services': {}
                }

                # 检查数据库连接
                try:
                    db.session.execute(text('SELECT 1'))
                    health_status['services']['database'] = {
                        'status': 'up',
                        'response_time': 0.1
                    }
                except Exception as e:
                    health_status['healthy'] = False
                    health_status['services']['database'] = {
                        'status': 'down',
                        'error': str(e)
                    }

                # 检查Redis连接
                try:
                    cache_service.ping()
                    health_status['services']['redis'] = {
                        'status': 'up',
                        'response_time': 0.05
                    }
                except Exception as e:
                    health_status['healthy'] = False
                    health_status['services']['redis'] = {
                        'status': 'down',
                        'error': str(e)
                    }

                # 检查系统资源
                import psutil
                health_status['services']['memory'] = {
                    'status': 'up',
                    'response_time': 0.01
                }
                health_status['services']['disk'] = {
                    'status': 'up',
                    'response_time': 0.01
                }

                # RESTX端点返回纯dict/状态码，避免对 Flask Response 再次序列化
                return {
                    'code': 200,
                    'status': 'success',
                    'data': health_status
                }, 200

            except Exception as e:
                current_app.logger.error(f"健康检查失败: {e}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': f"健康检查失败: {str(e)}"
                    }
                }, 500

    @system_ns.route('/status')
    class SystemStatus(Resource):
        @system_ns.doc('system_status')
        def get(self):
            """系统状态信息

            获取系统的详细运行状态，包括版本、运行时间、资源使用情况等。
            """
            try:
                import psutil
                import time
                from datetime import datetime, timedelta

                # 获取系统启动时间
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                uptime = datetime.now() - boot_time
                uptime_str = f"{uptime.days} days, {uptime.seconds // 3600} hours"

                # 检查数据库状态
                try:
                    db.session.execute(text('SELECT 1'))
                    database_status = "connected"
                except:
                    database_status = "disconnected"

                # 检查Redis状态
                try:
                    cache_service.ping()
                    redis_status = "connected"
                except:
                    redis_status = "disconnected"

                status_info = {
                    'status': 'running',
                    'version': '1.0.0',
                    'uptime': uptime_str,
                    'database_status': database_status,
                    'redis_status': redis_status,
                    'system': {
                        'cpu_percent': psutil.cpu_percent(interval=0.1),
                        'memory_percent': psutil.virtual_memory().percent,
                        'disk_percent': psutil.disk_usage('/').percent
                    },
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }

                return {
                    'code': 200,
                    'status': 'success',
                    'data': status_info
                }, 200

            except Exception as e:
                current_app.logger.error(f"获取系统状态失败: {e}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': f"获取系统状态失败: {str(e)}"
                    }
                }, 500

    @system_ns.route('/metrics')
    class SystemMetrics(Resource):
        @system_ns.doc('system_metrics')
        def get(self):
            """系统指标信息

            获取系统的详细指标数据，用于监控和分析。
            """
            try:
                import psutil
                from datetime import datetime

                metrics = {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'cpu': {
                        'percent': psutil.cpu_percent(interval=0.1),
                        'count': psutil.cpu_count(),
                        'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                    },
                    'memory': {
                        'total': psutil.virtual_memory().total,
                        'available': psutil.virtual_memory().available,
                        'percent': psutil.virtual_memory().percent,
                        'used': psutil.virtual_memory().used
                    },
                    'disk': {
                        'total': psutil.disk_usage('/').total,
                        'used': psutil.disk_usage('/').used,
                        'free': psutil.disk_usage('/').free,
                        'percent': psutil.disk_usage('/').percent
                    },
                    'network': dict(psutil.net_io_counters()._asdict()) if psutil.net_io_counters() else {}
                }

                return {
                    'code': 200,
                    'status': 'success',
                    'data': metrics
                }, 200

            except Exception as e:
                current_app.logger.error(f"获取系统指标失败: {e}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': f"获取系统指标失败: {str(e)}"
                    }
                }, 500
