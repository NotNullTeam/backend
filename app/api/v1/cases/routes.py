"""
IP智慧解答专家系统 - 案例API

本模块实现了诊断案例相关的API接口。
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1.cases import cases_bp as bp
from app.models.case import Case, Node, Edge
from app.models.user import User
from app.models.feedback import Feedback
from app import db
from datetime import datetime
import uuid
from app.utils.response_helper import (
    success_response, error_response, validation_error, not_found_error,
    internal_error, paginated_response
)
from app.services.retrieval.knowledge_service import knowledge_service
from app.services.network.vendor_command_service import vendor_command_service


@bp.route('/', methods=['GET'])
@jwt_required()
def get_cases():
    """
    获取案例列表

    支持的查询参数:
    - status: 案例状态过滤 (open, solved, closed)
    - vendor: 厂商过滤
    - category: 分类过滤
    - attachmentType: 附件类型过滤 (image, document, log, config, other)
    - page: 页码 (默认1)
    - pageSize: 每页大小 (默认10)
    """
    try:
        user_id = get_jwt_identity()

        # 获取查询参数
        status = request.args.get('status')
        vendor = request.args.get('vendor')
        category = request.args.get('category')
        attachment_type = request.args.get('attachmentType')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))

        # 构建查询
        query = Case.query.filter_by(user_id=user_id)

        # 应用过滤条件
        if status:
            query = query.filter_by(status=status)

        # 如果需要按厂商或分类过滤，需要通过节点的元数据进行联合查询
        if vendor or category:
            # 子查询获取符合条件的案例ID
            subquery = db.session.query(Node.case_id).distinct()
            if vendor:
                subquery = subquery.filter(Node.node_metadata['vendor'].astext == vendor)
            if category:
                subquery = subquery.filter(Node.node_metadata['category'].astext == category)

            case_ids = [row[0] for row in subquery.all()]
            if case_ids:
                query = query.filter(Case.id.in_(case_ids))
            else:
                # 如果没有符合条件的案例，返回空结果
                return jsonify({
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'items': [],
                        'total': 0,
                        'page': page,
                        'pageSize': page_size
                    }
                })

        # 按附件类型过滤
        if attachment_type:
            from app.models.files import UserFile
            # 获取所有指定类型的文件
            files_with_type = UserFile.query.filter(
                UserFile.file_type == attachment_type,
                UserFile.user_id == str(user_id),
                UserFile.is_deleted == False
            ).all()

            # 从 associated_cases JSON 字段中提取案例ID
            case_ids_with_attachments = []
            for file in files_with_type:
                if file.associated_cases:
                    case_ids_with_attachments.extend(file.associated_cases)

            # 去重
            case_ids_with_attachments = list(set(case_ids_with_attachments))

            if case_ids_with_attachments:
                query = query.filter(Case.id.in_(case_ids_with_attachments))
            else:
                # 如果没有符合条件的案例，返回空结果
                return jsonify({
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'items': [],
                        'total': 0,
                        'page': page,
                        'pageSize': page_size
                    }
                })

        # 分页查询
        pagination = query.order_by(Case.updated_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )

        cases = pagination.items

        return paginated_response(
            items=[case.to_dict() for case in cases],
            pagination_info={
                'total': pagination.total,
                'page': page,
                'per_page': page_size,
                'pages': pagination.pages
            }
        )

    except ValueError as e:
        return validation_error('分页参数必须为正整数')
    except Exception as e:
        current_app.logger.error(f"Get cases error: {str(e)}")
        return internal_error('获取案例列表时发生错误')


@bp.route('/<case_id>/nodes/<node_id>/regenerate', methods=['POST'])
@jwt_required()
def regenerate_node(case_id, node_id):
    """
    重新生成节点内容

    请求体参数:
    - prompt: 用户的指导性提示 (可选)
    - regeneration_strategy: 生成策略 (可选, e.g., 'more_detailed', 'simpler')
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        # 验证案例和节点
        node = Node.query.join(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id,
            Node.id == node_id
        ).first()

        if not node:
            return not_found_error('案例或节点不存在')

        # 模拟调用AI服务重新生成内容
        # 在真实实现中，这里会调用一个类似 case_service.regenerate_node 的服务
        from app.services.ai.llm_service import LLMService
        llm_service = LLMService()

        # 构建上下文
        parent_node = Node.query.get(node.parent_id) if node.parent_id else None
        context = {
            'original_query': parent_node.content if parent_node else 'N/A',
            'original_analysis': node.content,
            'user_prompt': data.get('prompt', ''),
            'strategy': data.get('regeneration_strategy', 'default')
        }

        # 假设LLM服务有这样一个方法
        new_content = llm_service.regenerate_content(context)

        # 更新节点
        node.content = new_content
        node.updated_at = datetime.utcnow()
        db.session.commit()

        return success_response({
            'message': '节点已成功重新生成',
            'node': node.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Regenerate node error: {str(e)}")
        return internal_error('重新生成节点时发生错误')


@bp.route('/<case_id>/nodes/<node_id>/rate', methods=['POST'])
@jwt_required()
def rate_node(case_id, node_id):
    """
    评价节点

    请求体参数:
    - rating: 评分 (必需, 1-5)
    - comment: 评论 (可选)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return validation_error('请求体不能为空')

        rating = data.get('rating')
        if rating is None or not (isinstance(rating, int) and 1 <= rating <= 5):
            return validation_error('评分必须是1到5之间的整数')

        # 验证案例和节点
        node = Node.query.join(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id,
            Node.id == node_id
        ).first()

        if not node:
            return not_found_error('案例或节点不存在')

        # 更新节点的元数据以包含评分
        if not node.metadata:
            node.metadata = {}

        node.metadata['rating'] = {
            'value': rating,
            'comment': data.get('comment', ''),
            'rated_at': datetime.utcnow().isoformat()
        }

        # 标记为需要更新
        db.session.add(node)
        db.session.commit()

        return success_response({
            'message': '节点评价已提交',
            'rating': node.metadata['rating']
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Rate node error: {str(e)}")
        return internal_error('评价节点时发生错误')


@bp.route('/', methods=['POST'])
@jwt_required()
def create_case():
    """
    创建新案例

    请求体参数:
    - query: 用户问题描述 (必需)
    - attachments: 附件列表 (可选)
    - useLanggraph: 是否使用langgraph Agent (可选，默认false)
    - vendor: 设备厂商 (可选)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        query = data.get('query')
        title = data.get('title')  # 支持直接设置标题
        attachments = data.get('attachments', [])
        use_langgraph = data.get('useLanggraph', False)
        vendor = data.get('vendor')

        if not query or not query.strip():
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '问题描述不能为空'
                }
            }), 400

        # 验证标题长度
        if title and len(title) > 200:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'VALIDATION_ERROR',
                    'message': '标题长度不能超过200个字符',
                    'details': {
                        'field': 'title',
                        'max_length': 200,
                        'current_length': len(title)
                    }
                }
            }), 400

        # 创建案例
        case_title = title if title else (query[:100] + '...' if len(query) > 100 else query)
        case = Case(
            title=case_title,
            user_id=user_id,
            metadata={
                'vendor': vendor,
                'use_langgraph': use_langgraph,
                'original_query': query,
                'created_with_langgraph': use_langgraph
            }
        )
        db.session.add(case)
        db.session.flush()  # 获取case.id

        # 创建用户问题节点
        user_node = Node(
            case_id=case.id,
            type='USER_QUERY',
            title='用户问题',
            status='COMPLETED',
            content={
                'text': query,
                'attachments': attachments
            },
            node_metadata={
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        db.session.add(user_node)
        db.session.flush()

        # 创建AI分析节点
        ai_node = Node(
            case_id=case.id,
            type='AI_ANALYSIS',
            title='AI分析中...',
            status='PROCESSING',
            node_metadata={
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        db.session.add(ai_node)
        db.session.flush()

        # 创建边
        edge = Edge(
            case_id=case.id,
            source=user_node.id,
            target=ai_node.id
        )
        db.session.add(edge)

        db.session.commit()

        # 触发异步AI分析任务
        try:
            if use_langgraph:
                # 使用langgraph Agent服务
                from app.services.ai import submit_langgraph_query_analysis_task
                job_id = submit_langgraph_query_analysis_task(case.id, ai_node.id, query)
                current_app.logger.info(f"langgraph异步AI分析任务已提交: job_id={job_id}, case_id={case.id}")
            else:
                # 使用传统Agent服务
                from app.services.ai.agent_service import analyze_user_query
                from app.services import get_task_queue

                queue = get_task_queue()
                job = queue.enqueue(analyze_user_query, case.id, ai_node.id, query)
                current_app.logger.info(f"传统异步AI分析任务已提交: job_id={job.id}, case_id={case.id}")
        except Exception as e:
            current_app.logger.error(f"提交异步任务失败: {str(e)}")
            # 不影响API响应，任务失败时节点状态会保持PROCESSING

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'caseId': case.id,
                'title': case.title,
                'status': case.status,
                'useLanggraph': use_langgraph,
                'vendor': vendor,
                'nodes': [user_node.to_dict(), ai_node.to_dict()],
                'edges': [edge.to_dict()],
                'createdAt': case.created_at.isoformat() + 'Z',
                'updatedAt': case.updated_at.isoformat() + 'Z'
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create case error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '创建案例时发生错误'
            }
        }), 500


@bp.route('/<case_id>', methods=['GET'])
@jwt_required()
def get_case_detail(case_id):
    """
    获取案例详情

    返回完整的案例信息，包括所有节点和边
    """
    try:
        user_id = get_jwt_identity()

        # 查找案例
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 获取所有节点
        nodes = Node.query.filter_by(case_id=case_id).order_by(Node.created_at.asc()).all()

        # 获取所有边
        edges = Edge.query.filter_by(case_id=case_id).all()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'case': {
                    'id': case.id,
                    'title': case.title,
                    'status': case.status,
                    'user_id': case.user_id,
                    'created_at': case.created_at.isoformat() + 'Z',
                    'updated_at': case.updated_at.isoformat() + 'Z'
                },
                'nodes': [node.to_dict() for node in nodes],
                'edges': [edge.to_dict() for edge in edges]
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get case detail error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取案例详情时发生错误'
            }
        }), 500


@bp.route('/<case_id>', methods=['PUT'])
@jwt_required()
def update_case(case_id):
    """
    更新案例信息

    支持更新的字段:
    - title: 案例标题
    - status: 案例状态
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 查找案例
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 更新字段
        if 'title' in data:
            case.title = data['title']

        if 'status' in data:
            if data['status'] not in ['open', 'solved', 'closed']:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '无效的案例状态'
                    }
                }), 400
            case.status = data['status']

        case.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'case': case.to_dict()
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update case error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '更新案例时发生错误'
            }
        }), 500


@bp.route('/<case_id>', methods=['DELETE'])
@jwt_required()
def delete_case(case_id):
    """
    删除案例

    删除案例及其所有相关的节点和边
    """
    try:
        user_id = get_jwt_identity()

        # 查找案例
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 删除案例（级联删除会自动删除相关的节点和边）
        db.session.delete(case)
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete case error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '删除案例时发生错误'
            }
        }), 500


@bp.route('/<case_id>/interactions', methods=['POST'])
@jwt_required()
def handle_interaction(case_id):
    """
    处理多轮交互

    请求体参数:
    - parentNodeId: 父节点ID (必需)
    - response: 用户响应数据 (必需)
    - retrievalWeight: 检索权重 (可选，默认0.7)
    - filterTags: 过滤标签 (可选)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        parent_node_id = data.get('parentNodeId')
        response_data = data.get('response')
        retrieval_weight = data.get('retrievalWeight', 0.7)
        filter_tags = data.get('filterTags', [])

        if not parent_node_id:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '父节点ID不能为空'
                }
            }), 400

        if not response_data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '响应数据不能为空'
                }
            }), 400

        # 验证父节点存在且属于该案例
        parent_node = Node.query.filter_by(id=parent_node_id, case_id=case_id).first()
        if not parent_node:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '父节点不存在'
                }
            }), 404

        # 创建用户响应节点
        user_response_node = Node(
            case_id=case_id,
            type='USER_RESPONSE',
            title='用户补充信息',
            status='COMPLETED',
            content=response_data,
            node_metadata={
                'timestamp': datetime.utcnow().isoformat(),
                'retrieval_weight': retrieval_weight,
                'filter_tags': filter_tags
            }
        )
        db.session.add(user_response_node)
        db.session.flush()

        # 创建AI处理节点
        ai_processing_node = Node(
            case_id=case_id,
            type='AI_ANALYSIS',
            title='AI分析中...',
            status='PROCESSING',
            node_metadata={
                'timestamp': datetime.utcnow().isoformat(),
                'parent_response_id': user_response_node.id
            }
        )
        db.session.add(ai_processing_node)
        db.session.flush()

        # 创建边
        edge1 = Edge(case_id=case_id, source=parent_node_id, target=user_response_node.id)
        edge2 = Edge(case_id=case_id, source=user_response_node.id, target=ai_processing_node.id)
        db.session.add_all([edge1, edge2])

        # 更新案例的更新时间
        case.updated_at = datetime.utcnow()

        db.session.commit()

        # 触发异步处理
        try:
            # 检查案例是否使用langgraph
            use_langgraph = case.metadata.get('use_langgraph', False) if case.metadata else False

            if use_langgraph:
                # 使用langgraph响应处理服务
                from app.services.ai import submit_langgraph_response_processing_task
                job_id = submit_langgraph_response_processing_task(
                    case_id,
                    ai_processing_node.id,
                    response_data,
                    retrieval_weight,
                    filter_tags
                )
                current_app.logger.info(f"langgraph异步响应处理任务已提交: job_id={job_id}, case_id={case_id}")
            else:
                # 使用传统响应处理服务
                from app.services.ai.agent_service import process_user_response
                from app.services import get_task_queue

                queue = get_task_queue()
                job = queue.enqueue(
                    process_user_response,
                    case_id,
                    ai_processing_node.id,
                    response_data,
                    retrieval_weight,
                    filter_tags
                )
                current_app.logger.info(f"传统异步响应处理任务已提交: job_id={job.id}, case_id={case_id}")
        except Exception as e:
            current_app.logger.error(f"提交异步任务失败: {str(e)}")
            # 不影响API响应，任务失败时节点状态会保持PROCESSING

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'newNodes': [
                    user_response_node.to_dict(),
                    ai_processing_node.to_dict()
                ],
                'newEdges': [
                    edge1.to_dict(),
                    edge2.to_dict()
                ],
                'processingNodeId': ai_processing_node.id
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Handle interaction error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '处理交互时发生错误'
            }
        }), 500


@bp.route('/<case_id>/nodes', methods=['GET'])
@jwt_required()
def get_case_nodes(case_id):
    """
    获取案例节点列表

    返回指定案例的所有节点
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 获取案例的所有节点
        nodes = Node.query.filter_by(case_id=case_id).order_by(Node.created_at.asc()).all()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'nodes': [node.to_dict() for node in nodes]
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get case nodes error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取案例节点时发生错误'
            }
        }), 500


@bp.route('/<case_id>/edges', methods=['GET'])
@jwt_required()
def get_case_edges(case_id):
    """
    获取案例边列表

    返回指定案例的所有边
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 获取案例的所有边
        edges = Edge.query.filter_by(case_id=case_id).order_by(Edge.id.asc()).all()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'edges': [edge.to_dict() for edge in edges]
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get case edges error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取案例边时发生错误'
            }
        }), 500


@bp.route('/<case_id>/nodes/<node_id>', methods=['GET'])
@jwt_required()
def get_node_detail(case_id, node_id):
    """
    获取节点详情

    返回指定节点的详细信息
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 查找节点
        node = Node.query.filter_by(id=node_id, case_id=case_id).first()
        if not node:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '节点不存在'
                }
            }), 404

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': node.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Get node detail error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取节点详情时发生错误'
            }
        }), 500


@bp.route('/<case_id>/nodes/<node_id>', methods=['PUT'])
@jwt_required()
def update_node(case_id, node_id):
    """
    更新节点信息

    支持更新的字段:
    - title: 节点标题
    - status: 节点状态
    - content: 节点内容
    - metadata: 节点元数据
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 查找节点
        node = Node.query.filter_by(id=node_id, case_id=case_id).first()
        if not node:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '节点不存在'
                }
            }), 404

        # 更新字段
        if 'title' in data:
            node.title = data['title']

        if 'status' in data:
            valid_statuses = ['COMPLETED', 'AWAITING_USER_INPUT', 'PROCESSING']
            if data['status'] not in valid_statuses:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '无效的节点状态'
                    }
                }), 400
            node.status = data['status']

        if 'content' in data:
            node.content = data['content']

        if 'metadata' in data:
            # 合并元数据而不是完全替换
            if node.node_metadata:
                node.node_metadata.update(data['metadata'])
            else:
                node.node_metadata = data['metadata']

        # 更新案例的更新时间
        case.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': node.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update node error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '更新节点时发生错误'
            }
        }), 500


@bp.route('/<case_id>/status', methods=['GET'])
@jwt_required()
def get_case_status(case_id):
    """
    获取案例状态

    返回案例的当前状态和处理中的节点信息，用于前端轮询
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 查找处理中的节点
        processing_nodes = Node.query.filter_by(
            case_id=case_id,
            status='PROCESSING'
        ).all()

        # 查找等待用户输入的节点
        awaiting_nodes = Node.query.filter_by(
            case_id=case_id,
            status='AWAITING_USER_INPUT'
        ).all()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'caseId': case.id,
                'caseStatus': case.status,
                'updatedAt': case.updated_at.isoformat() + 'Z',
                'processingNodes': [node.to_dict() for node in processing_nodes],
                'awaitingNodes': [node.to_dict() for node in awaiting_nodes],
                'hasProcessingNodes': len(processing_nodes) > 0,
                'hasAwaitingNodes': len(awaiting_nodes) > 0
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get case status error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取案例状态时发生错误'
            }
        }), 500


@bp.route('/<case_id>/feedback', methods=['PUT'])
@jwt_required()
def create_or_update_feedback(case_id):
    """
    创建或更新案例反馈

    对应文档: 3.9 创建/更新案例反馈
    Endpoint: PUT /cases/{caseId}/feedback
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return not_found_error('案例不存在')

        # 验证输入数据
        if not data or 'outcome' not in data or data['outcome'] not in ['solved', 'unsolved', 'partially_solved']:
            return validation_error('outcome 字段是必需的，且必须是 solved, unsolved, 或 partially_solved 之一')

        feedback = Feedback.query.filter_by(case_id=case_id).first()

        is_new = False
        if not feedback:
            # 创建新反馈
            is_new = True
            feedback = Feedback(
                id=str(uuid.uuid4()),
                case_id=case_id,
                user_id=user_id
            )
            db.session.add(feedback)

        # 更新字段
        feedback.outcome = data['outcome']
        feedback.rating = data.get('rating', feedback.rating)
        feedback.comment = data.get('comment', feedback.comment)
        feedback.corrected_solution = data.get('corrected_solution', feedback.corrected_solution)

        # 处理知识贡献
        if 'knowledge_contribution' in data and isinstance(data.get('knowledge_contribution'), dict):
            current_kc = feedback.knowledge_contribution or {}
            current_kc.update(data['knowledge_contribution'])
            feedback.knowledge_contribution = current_kc

        # 处理额外上下文
        if 'additional_context' in data and isinstance(data.get('additional_context'), dict):
            current_ac = feedback.additional_context or {}
            current_ac.update(data['additional_context'])
            feedback.additional_context = current_ac

        feedback.updated_at = datetime.utcnow()

        # 同步案例状态
        if feedback.outcome == 'solved':
            case.status = 'solved'
        elif case.status == 'solved': # 从 'solved' 改为其他状态
            case.status = 'open'

        db.session.commit()

        if is_new:
            return success_response(feedback.to_dict(), 201) # 201 Created
        else:
            return success_response(feedback.to_dict(), 200) # 200 OK

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Submit/Update feedback error for case {case_id}: {str(e)}")
        return internal_error('提交或更新反馈时发生错误')


@bp.route('/<case_id>/feedback', methods=['GET'])
@jwt_required()
def get_feedback(case_id):
    """
    获取案例反馈

    返回指定案例的反馈信息
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return not_found_error('案例不存在')

        feedback = Feedback.query.filter_by(case_id=case_id).first()

        if not feedback:
            return not_found_error('此案例暂无反馈信息')

        return success_response(feedback.to_dict())

    except Exception as e:
        current_app.logger.error(f"Get feedback error for case {case_id}: {str(e)}")
        return internal_error('获取反馈信息时发生错误')


@bp.route('/<case_id>/nodes/<node_id>/knowledge', methods=['GET'])
@jwt_required()
def get_node_knowledge(case_id, node_id):
    """
    获取节点知识溯源

    查询参数:
    - topK: 返回的文档片段数量 (可选，默认5)
    - vendor: 按指定厂商过滤 (可选)
    - retrievalWeight: 检索权重 (可选，默认0.7)
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 查找节点
        node = Node.query.filter_by(id=node_id, case_id=case_id).first()
        if not node:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '节点不存在'
                }
            }), 404

        # 获取查询参数
        top_k = request.args.get('topK', 5, type=int)
        vendor = request.args.get('vendor')
        retrieval_weight = request.args.get('retrievalWeight', 0.7, type=float)

        # 验证参数
        if top_k < 1 or top_k > 20:
            return validation_error('topK参数必须在1-20之间')

        if retrieval_weight < 0 or retrieval_weight > 1:
            return validation_error('retrievalWeight参数必须在0-1之间')

        # 调用真实的知识检索服务
        try:
            # 构建查询文本
            query_text = ""
            if node.content:
                if isinstance(node.content, dict):
                    query_text = node.content.get('text', '') or node.content.get('analysis', '') or node.content.get('answer', '')
                else:
                    query_text = str(node.content)

            if not query_text and node.title:
                query_text = node.title

            # 执行知识检索
            retrieval_result = knowledge_service.retrieve_knowledge(
                query=query_text,
                top_k=top_k,
                vendor=vendor,
                retrieval_weight=retrieval_weight
            )

            return success_response({
                'nodeId': node_id,
                'sources': retrieval_result['sources'],
                'retrievalMetadata': retrieval_result['retrievalMetadata']
            })

        except Exception as retrieval_error:
            current_app.logger.error(f"Knowledge retrieval service error: {str(retrieval_error)}")
            # 如果服务失败，返回空结果
            return success_response({
                'nodeId': node_id,
                'sources': [],
                'retrievalMetadata': {
                    'totalCandidates': 0,
                    'retrievalTime': 0,
                    'rerankTime': 0,
                    'strategy': 'service_unavailable'
                }
            })

    except Exception as e:
        current_app.logger.error(f"Get node knowledge error: {str(e)}")
        return internal_error('获取节点知识溯源时发生错误')


@bp.route('/<case_id>/nodes/<node_id>/commands', methods=['GET'])
@jwt_required()
def get_node_commands(case_id, node_id):
    """
    获取节点厂商命令

    查询参数:
    - vendor: 设备厂商 (必需)
    """
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 查找节点
        node = Node.query.filter_by(id=node_id, case_id=case_id).first()
        if not node:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '节点不存在'
                }
            }), 404

        # 获取厂商参数
        vendor = request.args.get('vendor')
        if not vendor:
            return validation_error('厂商参数不能为空')

        # 验证厂商
        supported_vendors = vendor_command_service.get_supported_vendors()
        if vendor not in supported_vendors:
            return validation_error(f'无效的设备厂商，支持: {", ".join(supported_vendors)}')

        # 调用真实的厂商命令生成服务
        try:
            commands = vendor_command_service.generate_commands(node, vendor)

            return success_response({
                'vendor': vendor,
                'commands': commands
            })

        except Exception as command_error:
            current_app.logger.error(f"Vendor command service error: {str(command_error)}")
            # 如果服务失败，返回基础命令
            return success_response({
                'vendor': vendor,
                'commands': []
            })

    except Exception as e:
        current_app.logger.error(f"Get node commands error: {str(e)}")
        return internal_error('获取节点厂商命令时发生错误')


@bp.route('/<case_id>/layout', methods=['PUT'])
@jwt_required()
def save_canvas_layout(case_id):
    """
    保存画布布局

    请求体:
    - nodePositions: 节点位置信息 (必需)
    - viewportState: 视口状态信息 (可选)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '请求体不能为空'
                }
            }), 400

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        node_positions = data.get('nodePositions')
        viewport_state = data.get('viewportState', {})

        if not node_positions:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '节点位置信息不能为空'
                }
            }), 400

        # 验证节点位置格式
        if not isinstance(node_positions, list):
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '节点位置信息必须是数组格式'
                }
            }), 400

        for position in node_positions:
            if not isinstance(position, dict) or \
               'nodeId' not in position or \
               'x' not in position or \
               'y' not in position:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '节点位置信息格式不正确，需要包含nodeId、x、y字段'
                    }
                }), 400

        # 保存布局信息到案例元数据
        if not case.metadata:
            case.metadata = {}

        case.metadata['layout'] = {
            'nodePositions': node_positions,
            'viewportState': viewport_state,
            'lastSaved': datetime.utcnow().isoformat()
        }

        case.updated_at = datetime.utcnow()
        db.session.commit()

        return '', 204

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Save canvas layout error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '保存画布布局时发生错误'
            }
        }), 500


@bp.route('/<case_id>/layout', methods=['GET'])
@jwt_required()
def get_canvas_layout(case_id):
    """获取画布布局"""
    try:
        user_id = get_jwt_identity()

        # 验证案例存在且属于当前用户
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 获取布局信息
        layout = case.metadata.get('layout') if case.metadata else None

        if not layout:
            # 返回默认布局
            return jsonify({
                'code': 200,
                'status': 'success',
                'data': {
                    'nodePositions': [],
                    'viewportState': {
                        'zoom': 1.0,
                        'centerX': 0,
                        'centerY': 0
                    }
                }
            })

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'nodePositions': layout.get('nodePositions', []),
                'viewportState': layout.get('viewportState', {
                    'zoom': 1.0,
                    'centerX': 0,
                    'centerY': 0
                })
            }
        })

    except Exception as e:
        current_app.logger.error(f"Get canvas layout error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取画布布局时发生错误'
            }
        }), 500
