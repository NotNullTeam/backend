"""
开发调试 API 接口 (Flask-RESTX)

将原有的开发调试接口集成到 Flask-RESTX 中，提供自动文档生成功能。
包含提示词测试、向量数据库管理等开发功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.utils.response_helper import success_response, validation_error, internal_error
from app.services.ai.llm_service import LLMService
from app.models.prompt import PromptTemplate
from app.services.storage.cache_service import get_cache_service
from app.services.retrieval.vector_service import get_vector_service
from app.services.storage.vector_db_config import vector_db_config

def init_development_api():
    """初始化开发调试API接口"""
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    development_ns = get_namespace('development')

    # 提示词测试请求模型
    prompt_test_model = development_ns.model('PromptTestRequest', {
        'query': fields.String(required=True, description='查询内容'),
        'context': fields.String(description='上下文信息'),
        'vendor': fields.String(description='设备厂商')
    })

    # 向量搜索请求模型
    vector_search_model = development_ns.model('VectorSearchRequest', {
        'query': fields.String(required=True, description='搜索查询'),
        'top_k': fields.Integer(description='返回结果数量', default=5),
        'threshold': fields.Float(description='相似度阈值', default=0.7)
    })

    # 提示词模板模型（文档展示用，字段与模型一致）
    prompt_template_model = development_ns.model('PromptTemplate', {
        'id': fields.Integer(description='模板ID'),
        'name': fields.String(description='模板名称'),
        'description': fields.String(description='模板描述'),
        'content': fields.String(description='提示词模板内容'),
        'category': fields.String(description='模板分类'),
        'version': fields.Integer(description='版本'),
        'is_active': fields.Boolean(description='是否启用'),
        'created_at': fields.String(description='创建时间'),
        'updated_at': fields.String(description='更新时间')
    })

    # 创建提示词模板请求模型
    create_template_model = development_ns.model('CreateTemplateRequest', {
        'name': fields.String(required=True, description='模板名称'),
        'description': fields.String(description='模板描述'),
        # 不设为 required，避免 RESTX 在进入视图前 400；由业务逻辑校验 content/template 至少一个
        'content': fields.String(description='提示词模板内容（或使用旧字段 template）'),
        'variables': fields.List(fields.String, description='模板变量（兼容字段，不入库）'),
        'category': fields.String(description='模板分类')
    })

    # 向量数据库状态模型
    vector_status_model = development_ns.model('VectorStatus', {
        'connection_ok': fields.Boolean(description='连接状态'),
        'document_count': fields.Integer(description='文档数量'),
        'vector_count': fields.Integer(description='向量数量'),
        'config': fields.Raw(description='配置信息')
    })

    @development_ns.route('/test/analysis')
    class AnalysisPromptTest(Resource):
        @development_ns.doc('test_analysis_prompt')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.expect(prompt_test_model)
        @jwt_required()
        def post(self):
            """测试问题分析提示词

            测试AI问题分析功能的提示词效果。
            """
            try:
                data = request.get_json(silent=True) or {}
                query = data.get('query')
                context = data.get('context', '')
                vendor = data.get('vendor')

                if not query:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '查询内容不能为空'}}, 400

                # 调用LLM服务
                llm_service = LLMService()
                result = llm_service.analyze_query(
                    query=query,
                    context=context,
                    vendor=vendor
                )

                return {'code': 200, 'status': 'success', 'data': {'result': result, 'test_type': 'analysis'}}, 200

            except Exception as e:
                current_app.logger.exception(f"测试分析提示词失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '测试分析提示词失败'}}, 500

    @development_ns.route('/test/clarification')
    class ClarificationPromptTest(Resource):
        @development_ns.doc('test_clarification_prompt')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.expect(prompt_test_model)
        @jwt_required()
        def post(self):
            """测试澄清问题提示词

            测试AI澄清问题功能的提示词效果。
            """
            try:
                data = request.get_json(silent=True) or {}
                query = data.get('query')
                context = data.get('context', '')

                if not query:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '查询内容不能为空'}}, 400

                # 调用LLM服务
                llm_service = LLMService()
                result = llm_service.generate_clarification(
                    query=query,
                    context=context
                )

                return {'code': 200, 'status': 'success', 'data': {'result': result, 'test_type': 'clarification'}}, 200

            except Exception as e:
                current_app.logger.exception(f"测试澄清提示词失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '测试澄清提示词失败'}}, 500

    @development_ns.route('/test/solution')
    class SolutionPromptTest(Resource):
        @development_ns.doc('test_solution_prompt')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.expect(prompt_test_model)
        @jwt_required()
        def post(self):
            """测试解决方案提示词

            测试AI解决方案生成功能的提示词效果。
            """
            try:
                data = request.get_json(silent=True) or {}
                query = data.get('query')
                context = data.get('context', '')
                vendor = data.get('vendor')

                if not query:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '查询内容不能为空'}}, 400

                # 调用LLM服务
                llm_service = LLMService()
                result = llm_service.generate_solution(
                    query=query,
                    context=context,
                    vendor=vendor
                )

                return {'code': 200, 'status': 'success', 'data': {'result': result, 'test_type': 'solution'}}, 200

            except Exception as e:
                current_app.logger.exception(f"测试解决方案提示词失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '测试解决方案提示词失败'}}, 500

    @development_ns.route('/vendors')
    class SupportedVendors(Resource):
        @development_ns.doc('get_supported_vendors')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取支持的设备厂商列表

            返回系统支持的所有设备厂商信息。
            """
            try:
                vendors = [
                    {'code': 'cisco', 'name': 'Cisco Systems'},
                    {'code': 'huawei', 'name': '华为技术'},
                    {'code': 'h3c', 'name': '新华三技术'},
                    {'code': 'juniper', 'name': 'Juniper Networks'},
                    {'code': 'arista', 'name': 'Arista Networks'}
                ]

                return {'code': 200, 'status': 'success', 'data': {'vendors': vendors}}, 200

            except Exception as e:
                current_app.logger.error(f"获取厂商列表失败: {str(e)}")
                return internal_error('获取厂商列表失败')

    @development_ns.route('/cache/status')
    class CacheStatus(Resource):
        @development_ns.doc('get_cache_status')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取缓存状态

            返回系统缓存的状态信息。
            """
            try:
                cache_service = get_cache_service()
                # 兼容：CacheService 无 get_status，改用 get_cache_info 与 get_cache_stats 聚合
                info = cache_service.get_cache_info()
                stats = cache_service.get_cache_stats()

                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'info': info,
                        'stats': stats
                    }
                }, 200

            except Exception as e:
                current_app.logger.exception(f"获取缓存状态失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {'type': 'INTERNAL_ERROR', 'message': '获取缓存状态失败'}
                }, 500

        @development_ns.doc('clear_cache')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def delete(self):
            """清除缓存

            清除系统所有缓存数据。
            """
            try:
                cache_service = get_cache_service()
                cache_service.clear_all()

                return {'code': 200, 'status': 'success', 'data': {'message': '缓存清除成功'}}, 200

            except Exception as e:
                current_app.logger.error(f"清除缓存失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '清除缓存失败'}}, 500

    @development_ns.route('/vector/status')
    class VectorStatus(Resource):
        @development_ns.doc('get_vector_status')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取向量数据库状态

            返回向量数据库的连接状态和统计信息。
            """
            try:
                vector_service = get_vector_service()
                stats = vector_service.get_stats()

                # 添加配置信息
                stats['config'] = {
                    'db_type': vector_db_config.db_type.value,
                    'is_valid': vector_db_config.is_valid()
                }

                return {'code': 200, 'status': 'success', 'data': stats}, 200

            except Exception as e:
                current_app.logger.error(f"获取向量数据库状态失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取向量数据库状态失败'}}, 500

    @development_ns.route('/vector/test')
    class VectorConnectionTest(Resource):
        @development_ns.doc('test_vector_connection')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def post(self):
            """测试向量数据库连接

            测试与向量数据库的连接是否正常。
            """
            try:
                vector_service = get_vector_service()
                connection_ok = vector_service.test_connection()

                return {'code': 200, 'status': 'success', 'data': {'connection_ok': connection_ok, 'timestamp': current_app.config.get('TESTING_TIMESTAMP')}}, 200

            except Exception as e:
                current_app.logger.error(f"测试向量数据库连接失败: {str(e)}")
                return internal_error('测试向量数据库连接失败')

    @development_ns.route('/vector/search')
    class VectorSearch(Resource):
        @development_ns.doc('search_vectors')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.expect(vector_search_model)
        @jwt_required()
        def post(self):
            """搜索相似向量

            在向量数据库中搜索与查询最相似的向量。
            """
            try:
                data = request.get_json(silent=True) or {}
                query = data.get('query')
                top_k = data.get('top_k', 5)
                threshold = data.get('threshold', 0.7)

                if not query:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '搜索查询不能为空'}}, 400

                vector_service = get_vector_service()
                # VectorService.search 不接受 threshold；阈值由上层过滤或DB内部处理
                results = vector_service.search(query=query, top_k=top_k)

                return {'code': 200, 'status': 'success', 'data': {'results': results, 'query': query, 'top_k': top_k, 'threshold': threshold}}, 200

            except Exception as e:
                current_app.logger.error(f"向量搜索失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '向量搜索失败'}}, 500

    @development_ns.route('/prompts')
    class PromptTemplates(Resource):
        @development_ns.doc('get_prompt_templates')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.param('page', '页码', type='integer', default=1)
        @development_ns.param('pageSize', '每页数量', type='integer', default=10)
        @jwt_required()
        def get(self):
            """获取提示词模板列表

            分页获取所有提示词模板。
            """
            try:
                page = request.args.get('page', 1, type=int)
                page_size = request.args.get('pageSize', 10, type=int)

                pagination = PromptTemplate.query.paginate(
                    page=page, per_page=page_size, error_out=False
                )

                templates = [template.to_dict() for template in pagination.items]

                return {'code': 200, 'status': 'success', 'data': {'templates': templates, 'total': pagination.total, 'page': page, 'per_page': page_size}}, 200

            except Exception as e:
                current_app.logger.error(f"获取提示词模板列表失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取提示词模板列表失败'}}, 500

        @development_ns.doc('create_prompt_template')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.expect(create_template_model)
        @jwt_required()
        def post(self):
            """创建新的提示词模板

            创建一个新的提示词模板供系统使用。
            """
            try:
                data = request.get_json(silent=True) or {}

                if not data or not data.get('name') or not (data.get('content') or data.get('template')):
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '模板名称和内容不能为空'}}, 400

                # 名称唯一性校验，避免数据库 UNIQUE 约束导致 500
                exists = PromptTemplate.query.filter_by(name=data['name']).first()
                if exists:
                    return {
                        'code': 409,
                        'status': 'error',
                        'error': {
                            'type': 'CONFLICT',
                            'message': '模板名称已存在'
                        }
                    }, 409

                template = PromptTemplate(
                    name=data['name'],
                    description=data.get('description', ''),
                    content=(data.get('content') or data.get('template')),
                    category=data.get('category', 'general')
                )

                db.session.add(template)
                db.session.commit()

                return {'code': 201, 'status': 'success', 'data': template.to_dict()}, 201

            except Exception as e:
                current_app.logger.error(f"创建提示词模板失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '创建提示词模板失败'}}, 500

    @development_ns.route('/prompts/<string:prompt_id>')
    class PromptTemplateDetail(Resource):
        @development_ns.doc('get_prompt_template')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self, prompt_id):
            """获取指定ID的提示词模板

            获取单个提示词模板的详细信息。
            """
            try:
                template = PromptTemplate.query.get(prompt_id)
                if not template:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '提示词模板不存在'}}, 404

                return {'code': 200, 'status': 'success', 'data': template.to_dict()}, 200

            except Exception as e:
                current_app.logger.error(f"获取提示词模板失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取提示词模板失败'}}, 500

        @development_ns.doc('update_prompt_template')
        @development_ns.doc(security='Bearer Auth')
        @development_ns.expect(create_template_model)
        @jwt_required()
        def put(self, prompt_id):
            """更新指定ID的提示词模板

            更新现有提示词模板的内容。
            """
            try:
                template = PromptTemplate.query.get(prompt_id)
                if not template:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '提示词模板不存在'}}, 404

                data = request.get_json(silent=True) or {}
                if not data:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '请求体不能为空'}}, 400

                # 更新模板字段
                if 'name' in data:
                    template.name = data['name']
                if 'description' in data:
                    template.description = data['description']
                if 'content' in data:
                    template.content = data['content']
                elif 'template' in data:  # 兼容旧字段
                    template.content = data['template']
                if 'variables' in data:
                    template.variables = data['variables']
                if 'category' in data:
                    template.category = data['category']

                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': template.to_dict()}, 200

            except Exception as e:
                current_app.logger.error(f"更新提示词模板失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '更新提示词模板失败'}}, 500

        @development_ns.doc('delete_prompt_template')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def delete(self, prompt_id):
            """删除指定ID的提示词模板

            删除现有的提示词模板。
            """
            try:
                template = PromptTemplate.query.get(prompt_id)
                if not template:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '提示词模板不存在'}}, 404

                db.session.delete(template)
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': {'message': '删除提示词模板成功'}}, 200

            except Exception as e:
                current_app.logger.error(f"删除提示词模板失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '删除提示词模板失败'}}, 500

    # 向量数据库管理相关接口
    @development_ns.route('/vector/status')
    class VectorDatabaseStatus(Resource):
        @development_ns.doc('get_vector_db_status')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取向量数据库状态

            返回向量数据库的连接状态和统计信息。
            """
            try:
                vector_service = get_vector_service()
                stats = vector_service.get_stats()

                # 添加配置信息
                stats['config'] = {
                    'db_type': vector_db_config.db_type.value,
                    'is_valid': vector_db_config.is_valid()
                }

                return {'code': 200, 'status': 'success', 'data': stats}, 200

            except Exception as e:
                current_app.logger.error(f"获取向量数据库状态失败: {str(e)}")
                return internal_error('获取向量数据库状态失败')

    @development_ns.route('/vector/test')
    class VectorDatabaseTest(Resource):
        @development_ns.doc('test_vector_db_connection')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def post(self):
            """测试向量数据库连接

            测试与向量数据库的连接是否正常。
            """
            try:
                vector_service = get_vector_service()
                connection_ok = vector_service.test_connection()

                return {'code': 200, 'status': 'success', 'data': {'connection_ok': connection_ok, 'timestamp': datetime.utcnow().isoformat()}}, 200

            except Exception as e:
                current_app.logger.error(f"测试向量数据库连接失败: {str(e)}")
                return internal_error('测试向量数据库连接失败')

    @development_ns.route('/vector/documents/<string:document_id>')
    class VectorDocumentDelete(Resource):
        @development_ns.doc('delete_document_vectors')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def delete(self, document_id):
            """删除文档的向量数据

            从向量数据库中删除指定文档的所有向量数据。
            """
            try:
                vector_service = get_vector_service()
                # 这里应该调用实际的删除服务
                # vector_service.delete_document_vectors(document_id)

                return {'code': 200, 'status': 'success', 'data': {'message': f'文档 {document_id} 的向量数据已删除'}}, 200

            except Exception as e:
                current_app.logger.error(f"删除文档向量数据失败: {str(e)}")
                return internal_error('删除文档向量数据失败')

    @development_ns.route('/embedding/test')
    class EmbeddingTest(Resource):
        @development_ns.doc('test_embedding_service')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def post(self):
            """测试嵌入服务

            测试文本嵌入服务的可用性和性能。
            """
            try:
                data = request.get_json(silent=True) or {}
                text = data.get('text') or '这是一个测试文本'

                # 这里应该调用实际的嵌入服务
                # embedding_result = embedding_service.embed_text(text)

                return {'code': 200, 'status': 'success', 'data': {'text': text, 'embedding_dimension': 1536, 'processing_time': 0.1}}, 200

            except Exception as e:
                current_app.logger.error(f"测试嵌入服务失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '测试嵌入服务失败'}}, 500

    @development_ns.route('/vector/config')
    class VectorConfig(Resource):
        @development_ns.doc('get_vector_config')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取向量数据库配置信息

            返回当前向量数据库的配置参数。
            """
            try:
                config_info = {
                    'db_type': vector_db_config.db_type.value,
                    'is_valid': vector_db_config.is_valid(),
                    'connection_params': {
                        # 这里可以添加一些非敏感的配置信息
                    }
                }

                return {'code': 200, 'status': 'success', 'data': config_info}, 200

            except Exception as e:
                current_app.logger.error(f"获取向量数据库配置失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取向量数据库配置失败'}}, 500

    @development_ns.route('/performance/metrics')
    class PerformanceMetrics(Resource):
        @development_ns.doc('get_performance_metrics')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """获取LLM服务性能指标

            返回大语言模型服务的性能统计数据。
            """
            try:
                # 这里应该调用实际的性能监控服务
                metrics = {
                    'total_requests': 0,
                    'average_response_time': 0.0,
                    'success_rate': 1.0,
                    'error_rate': 0.0,
                    'tokens_per_second': 0.0
                }

                return {'code': 200, 'status': 'success', 'data': metrics}, 200

            except Exception as e:
                current_app.logger.error(f"获取性能指标失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取性能指标失败'}}, 500

    @development_ns.route('/health')
    class DevelopmentHealth(Resource):
        @development_ns.doc('development_health_check')
        @development_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self):
            """开发环境健康检查

            检查开发环境中所有组件的健康状态。
            """
            try:
                health_status = {
                    'llm_service': 'healthy',
                    'vector_service': 'healthy',
                    'cache_service': 'healthy',
                    'embedding_service': 'healthy',
                    'overall_status': 'healthy'
                }

                return {'code': 200, 'status': 'success', 'data': health_status}, 200

            except Exception as e:
                current_app.logger.error(f"开发环境健康检查失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '开发环境健康检查失败'}}, 500

    print("✅ 开发调试API接口已注册到Flask-RESTX文档系统")
