"""
开发调试模块路由

整合提示词测试、向量数据库管理等开发功能的路由。
"""

import os
import sys
import flask
from datetime import datetime
from flask import jsonify, render_template_string, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.api.v1.development import dev_bp as bp

# 导入各个子模块的路由
from app.api.v1.development.prompts import *
from app.api.v1.development.vector import *


@bp.route('/docs', methods=['GET'])
def api_docs():
    """API文档页面"""
    html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>IP智慧解答专家系统 API 文档</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>IP智慧解答专家系统 API 文档</h1>
    <p>这是开发环境的API文档页面。</p>
    <ul>
        <li><a href="/api/v1/dev/openapi.json">OpenAPI规范</a></li>
        <li><a href="/api/v1/auth/">认证API</a></li>
        <li><a href="/api/v1/cases/">案例API</a></li>
        <li><a href="/api/v1/knowledge/">知识库API</a></li>
        <li><a href="/api/v1/system/">系统API</a></li>
    </ul>
</body>
</html>
    '''
    return render_template_string(html_template)


@bp.route('/openapi.json', methods=['GET'])
def api_spec():
    """OpenAPI规范"""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "IP智慧解答专家系统 API",
            "version": "1.0.0",
            "description": "IP网络专家诊断系统的RESTful API文档"
        },
        "servers": [
            {
                "url": "/api/v1",
                "description": "API v1"
            }
        ],
        "paths": {
            "/auth/login": {
                "post": {
                    "summary": "用户登录",
                    "tags": ["认证"],
                    "responses": {
                        "200": {"description": "登录成功"}
                    }
                }
            },
            "/cases": {
                "get": {
                    "summary": "获取案例列表",
                    "tags": ["案例"],
                    "responses": {
                        "200": {"description": "获取成功"}
                    }
                }
            },
            "/knowledge/documents": {
                "get": {
                    "summary": "获取文档列表",
                    "tags": ["知识库"],
                    "responses": {
                        "200": {"description": "获取成功"}
                    }
                }
            },
            "/system/status": {
                "get": {
                    "summary": "获取系统状态",
                    "tags": ["系统"],
                    "responses": {
                        "200": {"description": "获取成功"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "ApiResponse": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer"},
                        "status": {"type": "string"},
                        "data": {"type": "object"}
                    }
                }
            },
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
    return jsonify(spec)


@bp.route('/debug-info', methods=['GET'])
@jwt_required()
def debug_info():
    """调试信息（仅管理员）"""
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

    # 返回调试信息
    debug_data = {
        'server_time': datetime.utcnow().isoformat(),
        'debug_mode': current_app.debug,
        'environment': os.environ.get('FLASK_ENV', 'unknown'),
        'python_version': sys.version,
        'flask_version': flask.__version__,
        'dependencies': {},
        'config': {}
    }

    return jsonify({
        'code': 200,
        'status': 'success',
        'data': debug_data
    })
