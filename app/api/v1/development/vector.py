"""
向量数据库管理API
提供向量数据库的状态查询、测试和管理功能
"""
from flask import Blueprint, jsonify, request
from app.api.v1.development import dev_bp as bp
from app.services.retrieval.vector_service import get_vector_service
from app.services.storage.vector_db_config import vector_db_config
import logging

logger = logging.getLogger(__name__)


@bp.route('/status', methods=['GET'])
def get_vector_status():
    """获取向量数据库状态"""
    try:
        vector_service = get_vector_service()
        stats = vector_service.get_stats()

        # 添加配置信息
        stats['config'] = {
            'db_type': vector_db_config.db_type.value,
            'is_valid': vector_db_config.is_valid()
        }

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        logger.error(f"Error getting vector status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/test', methods=['POST'])
def test_vector_connection():
    """测试向量数据库连接"""
    try:
        vector_service = get_vector_service()
        connection_ok = vector_service.test_connection()

        return jsonify({
            'success': True,
            'data': {
                'connection_ok': connection_ok,
                'db_type': vector_db_config.db_type.value
            }
        })

    except Exception as e:
        logger.error(f"Error testing vector connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/search', methods=['POST'])
def search_vectors():
    """搜索相似向量"""
    try:
        data = request.get_json()
        query_text = data.get('query_text')
        top_k = data.get('top_k', 5)
        document_id = data.get('document_id')

        if not query_text:
            return jsonify({
                'success': False,
                'error': 'query_text is required'
            }), 400

        vector_service = get_vector_service()
        results = vector_service.search_similar(
            query_text=query_text,
            top_k=top_k,
            document_id=document_id
        )

        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'total': len(results)
            }
        })

    except Exception as e:
        logger.error(f"Error searching vectors: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/documents/<document_id>', methods=['DELETE'])
def delete_document_vectors(document_id):
    """删除文档的向量数据"""
    try:
        vector_service = get_vector_service()
        success = vector_service.delete_document(document_id)

        return jsonify({
            'success': success,
            'message': f'Document {document_id} vectors deleted' if success else 'Failed to delete vectors'
        })

    except Exception as e:
        logger.error(f"Error deleting document vectors: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/embedding/test', methods=['POST'])
def test_embedding():
    """测试嵌入服务"""
    try:
        data = request.get_json()
        text = data.get('text', '这是一个测试文本')

        vector_service = get_vector_service()
        embedding = vector_service.embedding_service.embed_text(text)

        return jsonify({
            'success': True,
            'data': {
                'text': text,
                'embedding_dimension': len(embedding),
                'embedding_sample': embedding[:10]  # 只返回前10个值作为示例
            }
        })

    except Exception as e:
        logger.error(f"Error testing embedding: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/config', methods=['GET'])
def get_vector_config():
    """获取向量数据库配置信息"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'db_type': vector_db_config.db_type.value,
                'is_valid': vector_db_config.is_valid(),
                'config': {
                    k: v for k, v in vector_db_config.config.items()
                    if k not in ['api_key', 'password']  # 隐藏敏感信息
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting vector config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
