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


@bp.route('/', methods=['GET'])
@jwt_required()
def get_cases():
    """
    获取案例列表

    支持的查询参数:
    - status: 案例状态过滤 (open, solved, closed)
    - vendor: 厂商过滤
    - category: 分类过滤
    - page: 页码 (默认1)
    - pageSize: 每页大小 (默认10)
    """
    try:
        user_id = get_jwt_identity()

        # 获取查询参数
        status = request.args.get('status')
        vendor = request.args.get('vendor')
        category = request.args.get('category')
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

        # 分页查询
        pagination = query.order_by(Case.updated_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )

        cases = pagination.items

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'items': [case.to_dict() for case in cases],
                'total': pagination.total,
                'page': page,
                'pageSize': page_size
            }
        })

    except ValueError as e:
        return jsonify({
            'code': 400,
            'status': 'error',
            'error': {
                'type': 'INVALID_REQUEST',
                'message': '分页参数必须为正整数'
            }
        }), 400
    except Exception as e:
        current_app.logger.error(f"Get cases error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取案例列表时发生错误'
            }
        }), 500


@bp.route('/', methods=['POST'])
@jwt_required()
def create_case():
    """
    创建新案例

    请求体参数:
    - query: 用户问题描述 (必需)
    - attachments: 附件列表 (可选)
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
        attachments = data.get('attachments', [])

        if not query or not query.strip():
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '问题描述不能为空'
                }
            }), 400

        # 创建案例
        case = Case(
            title=query[:100] + '...' if len(query) > 100 else query,
            user_id=user_id
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
            from app.services.agent_service import analyze_user_query
            from app.services import get_task_queue

            queue = get_task_queue()
            job = queue.enqueue(analyze_user_query, case.id, ai_node.id, query)

            current_app.logger.info(f"异步AI分析任务已提交: job_id={job.id}, case_id={case.id}")
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
                'caseId': case.id,
                'title': case.title,
                'status': case.status,
                'nodes': [node.to_dict() for node in nodes],
                'edges': [edge.to_dict() for edge in edges],
                'createdAt': case.created_at.isoformat() + 'Z',
                'updatedAt': case.updated_at.isoformat() + 'Z'
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
            'data': case.to_dict()
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
            from app.services.agent_service import process_user_response
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

            current_app.logger.info(f"异步响应处理任务已提交: job_id={job.id}, case_id={case_id}")
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


@bp.route('/<case_id>/feedback', methods=['POST'])
@jwt_required()
def submit_feedback(case_id):
    """
    提交案例反馈

    请求体参数:
    - outcome: 解决结果 (solved, unsolved, partially_solved) (必需)
    - rating: 评分 1-5 (可选)
    - comment: 评论 (可选)
    - corrected_solution: 修正的解决方案 (可选)
    - knowledge_contribution: 知识贡献 (可选)
    - additional_context: 额外上下文 (可选)
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

        outcome = data.get('outcome')
        if not outcome:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '解决结果不能为空'
                }
            }), 400

        if outcome not in ['solved', 'unsolved', 'partially_solved']:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'INVALID_REQUEST',
                    'message': '无效的解决结果'
                }
            }), 400

        # 验证评分
        rating = data.get('rating')
        if rating is not None:
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '评分必须是1-5之间的整数'
                    }
                }), 400

        # 检查是否已经提交过反馈
        existing_feedback = Feedback.query.filter_by(
            case_id=case_id,
            user_id=user_id
        ).first()

        if existing_feedback:
            return jsonify({
                'code': 400,
                'status': 'error',
                'error': {
                    'type': 'DUPLICATE_FEEDBACK',
                    'message': '该案例已经提交过反馈'
                }
            }), 400

        # 创建反馈记录
        feedback = Feedback(
            case_id=case_id,
            user_id=user_id,
            outcome=outcome,
            rating=rating,
            comment=data.get('comment'),
            corrected_solution=data.get('corrected_solution'),
            knowledge_contribution=data.get('knowledge_contribution'),
            additional_context=data.get('additional_context')
        )

        db.session.add(feedback)

        # 根据反馈结果更新案例状态
        if outcome == 'solved':
            case.status = 'solved'
        elif outcome == 'unsolved':
            # 保持案例为open状态，可能需要进一步处理
            pass

        case.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': {
                'feedbackId': feedback.id,
                'outcome': feedback.outcome,
                'rating': feedback.rating,
                'comment': feedback.comment,
                'message': '反馈已收到',
                'caseStatus': case.status
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Submit feedback error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '提交反馈时发生错误'
            }
        }), 500


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
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '案例不存在'
                }
            }), 404

        # 查找反馈
        feedback = Feedback.query.filter_by(
            case_id=case_id,
            user_id=user_id
        ).first()

        if not feedback:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '该案例暂无反馈'
                }
            }), 404

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': feedback.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Get feedback error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '获取反馈时发生错误'
            }
        }), 500


@bp.route('/<case_id>/feedback', methods=['PUT'])
@jwt_required()
def update_feedback(case_id):
    """
    更新案例反馈

    允许用户修改已提交的反馈
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

        # 查找反馈
        feedback = Feedback.query.filter_by(
            case_id=case_id,
            user_id=user_id
        ).first()

        if not feedback:
            return jsonify({
                'code': 404,
                'status': 'error',
                'error': {
                    'type': 'NOT_FOUND',
                    'message': '反馈不存在'
                }
            }), 404

        # 更新字段
        if 'outcome' in data:
            if data['outcome'] not in ['solved', 'unsolved', 'partially_solved']:
                return jsonify({
                    'code': 400,
                    'status': 'error',
                    'error': {
                        'type': 'INVALID_REQUEST',
                        'message': '无效的解决结果'
                    }
                }), 400
            feedback.outcome = data['outcome']

            # 同步更新案例状态
            if data['outcome'] == 'solved':
                case.status = 'solved'
            elif data['outcome'] == 'unsolved':
                case.status = 'open'  # 重新打开案例

        if 'rating' in data:
            rating = data['rating']
            if rating is not None:
                if not isinstance(rating, int) or rating < 1 or rating > 5:
                    return jsonify({
                        'code': 400,
                        'status': 'error',
                        'error': {
                            'type': 'INVALID_REQUEST',
                            'message': '评分必须是1-5之间的整数'
                        }
                    }), 400
            feedback.rating = rating

        if 'comment' in data:
            feedback.comment = data['comment']

        if 'corrected_solution' in data:
            feedback.corrected_solution = data['corrected_solution']

        if 'knowledge_contribution' in data:
            feedback.knowledge_contribution = data['knowledge_contribution']

        if 'additional_context' in data:
            feedback.additional_context = data['additional_context']

        case.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'code': 200,
            'status': 'success',
            'data': feedback.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update feedback error: {str(e)}")
        return jsonify({
            'code': 500,
            'status': 'error',
            'error': {
                'type': 'INTERNAL_ERROR',
                'message': '更新反馈时发生错误'
            }
        }), 500
