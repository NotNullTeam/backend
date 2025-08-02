"""
IP智慧解答专家系统 - 检索服务API

本模块提供混合检索相关的API接口。
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.api.v1.knowledge import knowledge_bp as bp
from app.services.retrieval.hybrid_retrieval import search_knowledge
import logging

logger = logging.getLogger(__name__)


@bp.route('/search', methods=['POST'])
@jwt_required()
def search_knowledge_api():
    """
    知识检索API接口

    请求体:
    {
        "query": "OSPF邻居建立失败",
        "filters": {
            "vendor": "华为",
            "category": "路由协议"
        },
        "vector_weight": 0.7,
        "keyword_weight": 0.3,
        "top_k": 10
    }
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '查询参数不能为空'
                }
            }), 400

        query = data['query']
        filters = data.get('filters', {})
        vector_weight = data.get('vector_weight', 0.7)
        keyword_weight = data.get('keyword_weight', 0.3)
        top_k = data.get('top_k', 10)

        # 参数验证
        if not isinstance(query, str) or len(query.strip()) == 0:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '查询文本不能为空'
                }
            }), 400

        if not (0 <= vector_weight <= 1) or not (0 <= keyword_weight <= 1):
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '权重参数必须在0-1之间'
                }
            }), 400

        if abs(vector_weight + keyword_weight - 1.0) > 0.001:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '向量权重和关键词权重之和必须等于1'
                }
            }), 400

        logger.info(f"执行知识检索: query='{query}', filters={filters}")

        # 执行检索
        results = search_knowledge(
            query=query,
            filters=filters,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            top_k=min(top_k, 50)  # 限制最大返回数量
        )

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'query': query,
                'total': len(results),
                'results': results,
                'search_params': {
                    'vector_weight': vector_weight,
                    'keyword_weight': keyword_weight,
                    'filters': filters
                }
            }
        })

    except Exception as e:
        logger.error(f"知识检索API失败: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '检索服务暂时不可用'
            }
        }), 500


@bp.route('/search/suggest', methods=['POST'])
@jwt_required()
def suggest_search_terms():
    """
    搜索建议API接口

    请求体:
    {
        "query": "OSPF",
        "limit": 10
    }
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '查询参数不能为空'
                }
            }), 400

        query = data['query'].strip()
        limit = data.get('limit', 10)

        if not query:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '查询文本不能为空'
                }
            }), 400

        # 生成搜索建议
        suggestions = _generate_search_suggestions(query, limit)

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'query': query,
                'suggestions': suggestions
            }
        })

    except Exception as e:
        logger.error(f"搜索建议API失败: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '建议服务暂时不可用'
            }
        }), 500


def _generate_search_suggestions(query: str, limit: int) -> list:
    """生成搜索建议"""
    suggestions = []
    query_lower = query.lower()

    # 基于技术领域的建议
    tech_suggestions = {
        'ospf': [
            'OSPF邻居建立失败',
            'OSPF区域配置',
            'OSPF LSA类型',
            'OSPF路由计算',
            'OSPF网络类型配置'
        ],
        'bgp': [
            'BGP邻居建立',
            'BGP路由策略',
            'BGP属性配置',
            'BGP路由反射器',
            'BGP联盟配置'
        ],
        'vlan': [
            'VLAN配置命令',
            'VLAN间路由',
            'VLAN Trunk配置',
            'VLAN划分原则',
            'VLAN故障排除'
        ],
        '华为': [
            '华为交换机配置',
            '华为路由器命令',
            '华为防火墙策略',
            '华为VRP系统',
            '华为设备调试'
        ],
        '思科': [
            '思科IOS配置',
            '思科交换机命令',
            '思科路由协议',
            '思科网络安全',
            '思科故障排除'
        ]
    }

    # 查找匹配的建议
    for key, values in tech_suggestions.items():
        if key in query_lower:
            suggestions.extend(values)

    # 通用建议
    if not suggestions:
        generic_suggestions = [
            f'{query} 配置方法',
            f'{query} 故障排除',
            f'{query} 命令大全',
            f'{query} 最佳实践',
            f'{query} 案例分析'
        ]
        suggestions.extend(generic_suggestions)

    # 去重并限制数量
    suggestions = list(dict.fromkeys(suggestions))  # 去重保持顺序
    return suggestions[:limit]
