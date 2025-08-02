"""
IPfrom flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1.system import system_bp as bp
from app.services.task_monitor import TaskMonitor
from app.services.document_service import get_parsing_status
from app.services.agent_service import get_agent_task_status
from app import db
from app.models.knowledge import ParsingJob
from datetime import datetime, timedelta - 任务监控API

本模块提供异步任务状态监控和管理的API接口。
"""

"""
IP智慧解答专家系统 - 任务监控API

本模块提供异步任务状态监控和管理的API接口。
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1.system import system_bp as bp
from app.services.task_monitor import TaskMonitor
from app.services.document_service import get_parsing_status
from app.services.agent_service import get_agent_task_status
from app import db
from app.models.knowledge import ParsingJob
from datetime import datetime, timedelta

# 任务监控API路由


@bp.route('/queue/stats', methods=['GET'])
@jwt_required()
def get_queue_stats():
    """获取任务队列统计信息"""
    try:
        stats = TaskMonitor.get_queue_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/task/<job_id>/status', methods=['GET'])
@jwt_required()
def get_task_status(job_id):
    """获取特定任务的状态"""
    try:
        status = TaskMonitor.get_task_status(job_id)

        if not status:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404

        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/task/<job_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_task(job_id):
    """取消任务"""
    try:
        success = TaskMonitor.cancel_task(job_id)

        if success:
            return jsonify({
                'success': True,
                'message': '任务已取消'
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法取消任务，任务可能不存在或已完成'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/parsing/jobs', methods=['GET'])
@jwt_required()
def get_parsing_jobs():
    """获取文档解析任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status')

        query = ParsingJob.query

        if status_filter:
            query = query.filter(ParsingJob.status == status_filter)

        pagination = query.order_by(ParsingJob.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        jobs = []
        for job in pagination.items:
            job_data = job.to_dict()
            # 获取RQ任务状态
            rq_status = TaskMonitor.get_task_status(job.id)
            job_data['rq_status'] = rq_status
            jobs.append(job_data)

        return jsonify({
            'success': True,
            'data': {
                'jobs': jobs,
                'pagination': {
                    'page': page,
                    'pages': pagination.pages,
                    'per_page': per_page,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/parsing/<job_id>/status', methods=['GET'])
@jwt_required()
def get_parsing_job_status(job_id):
    """获取文档解析任务状态"""
    try:
        status = get_parsing_status(job_id)

        if 'error' in status:
            return jsonify({
                'success': False,
                'error': status['error']
            }), 404

        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/cleanup/failed', methods=['POST'])
@jwt_required()
def cleanup_failed_jobs():
    """清理失败的任务"""
    try:
        max_age_hours = request.json.get('max_age_hours', 24)

        cleaned_count = TaskMonitor.cleanup_failed_jobs(max_age_hours)

        return jsonify({
            'success': True,
            'data': {
                'cleaned_count': cleaned_count,
                'message': f'已清理 {cleaned_count} 个过期的失败任务'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/health', methods=['GET'])
@jwt_required()
def health_check():
    """异步任务系统健康检查"""
    try:
        stats = TaskMonitor.get_queue_stats()

        # 检查是否有活跃的worker
        active_workers = len([w for w in stats.get('workers', []) if w.get('state') == 'busy'])
        total_workers = stats.get('workers_count', 0)

        # 检查队列积压情况
        queue_length = stats.get('queue_length', 0)

        health_status = 'healthy'
        issues = []

        if total_workers == 0:
            health_status = 'critical'
            issues.append('没有可用的worker')
        elif active_workers == 0 and queue_length > 0:
            health_status = 'warning'
            issues.append(f'队列中有 {queue_length} 个任务但没有活跃的worker')
        elif queue_length > 100:
            health_status = 'warning'
            issues.append(f'队列积压较多: {queue_length} 个任务')

        # 检查最近的失败任务
        recent_failed = ParsingJob.query.filter(
            ParsingJob.status == 'FAILED',
            ParsingJob.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()

        if recent_failed > 10:
            health_status = 'warning'
            issues.append(f'最近1小时有 {recent_failed} 个任务失败')

        return jsonify({
            'success': True,
            'data': {
                'status': health_status,
                'issues': issues,
                'stats': {
                    'total_workers': total_workers,
                    'active_workers': active_workers,
                    'queue_length': queue_length,
                    'recent_failed_jobs': recent_failed
                },
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'status': 'critical',
                'issues': [f'健康检查失败: {str(e)}'],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }), 500


@bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_metrics():
    """获取任务系统指标"""
    try:
        # 获取时间范围参数
        hours = request.args.get('hours', 24, type=int)
        since = datetime.utcnow() - timedelta(hours=hours)

        # 统计解析任务
        total_parsing_jobs = ParsingJob.query.filter(
            ParsingJob.created_at >= since
        ).count()

        completed_parsing_jobs = ParsingJob.query.filter(
            ParsingJob.created_at >= since,
            ParsingJob.status == 'COMPLETED'
        ).count()

        failed_parsing_jobs = ParsingJob.query.filter(
            ParsingJob.created_at >= since,
            ParsingJob.status == 'FAILED'
        ).count()

        processing_parsing_jobs = ParsingJob.query.filter(
            ParsingJob.created_at >= since,
            ParsingJob.status == 'PROCESSING'
        ).count()

        # 计算成功率
        success_rate = (completed_parsing_jobs / total_parsing_jobs * 100) if total_parsing_jobs > 0 else 0

        # 获取队列统计
        queue_stats = TaskMonitor.get_queue_stats()

        # 计算平均处理时间
        completed_jobs = ParsingJob.query.filter(
            ParsingJob.created_at >= since,
            ParsingJob.status == 'COMPLETED',
            ParsingJob.started_at.isnot(None),
            ParsingJob.completed_at.isnot(None)
        ).all()

        avg_processing_time = 0
        if completed_jobs:
            total_time = sum([
                (job.completed_at - job.started_at).total_seconds()
                for job in completed_jobs
            ])
            avg_processing_time = total_time / len(completed_jobs)

        return jsonify({
            'success': True,
            'data': {
                'time_range_hours': hours,
                'parsing_jobs': {
                    'total': total_parsing_jobs,
                    'completed': completed_parsing_jobs,
                    'failed': failed_parsing_jobs,
                    'processing': processing_parsing_jobs,
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time_seconds': round(avg_processing_time, 2)
                },
                'queue': {
                    'current_length': queue_stats.get('queue_length', 0),
                    'workers_count': queue_stats.get('workers_count', 0),
                    'failed_jobs_count': queue_stats.get('failed_jobs_count', 0)
                },
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
