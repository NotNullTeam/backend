"""
案例管理 API 接口 (Flask-RESTX)

将原有的案例管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import get_namespace
from app.models.case import Case, Node, Edge
from app.models.user import User
from app.models.feedback import Feedback
from app.utils.response_helper import (
    success_response, error_response, validation_error, not_found_error,
    internal_error, paginated_response
)
from app.services.retrieval.knowledge_service import knowledge_service
from app.services.network.vendor_command_service import vendor_command_service
from datetime import datetime
import uuid

def init_cases_api():
    """初始化案例管理API接口"""
    # 动态获取 RESTX 命名空间，避免测试中复用陈旧实例导致重复注册
    cases_ns = get_namespace('cases')

    # 案例基本信息模型
    case_model = cases_ns.model('Case', {
        'id': fields.String(description='案例ID'),
        'title': fields.String(description='案例标题'),
        'query': fields.String(description='用户问题描述'),
        'status': fields.String(description='案例状态', enum=['open', 'solved', 'closed']),
        'vendor': fields.String(description='设备厂商'),
        'category': fields.String(description='问题分类'),
        'created_at': fields.String(description='创建时间'),
        'updated_at': fields.String(description='更新时间'),
        'user_id': fields.String(description='用户ID')
    })

    # 节点信息模型
    node_model = cases_ns.model('Node', {
        'id': fields.String(description='节点ID'),
        'title': fields.String(description='节点标题'),
        'content': fields.String(description='节点内容'),
        'node_type': fields.String(description='节点类型'),
        'status': fields.String(description='节点状态'),
        'metadata': fields.Raw(description='节点元数据'),
        'created_at': fields.String(description='创建时间')
    })

    # 边信息模型
    edge_model = cases_ns.model('Edge', {
        'id': fields.String(description='边ID'),
        'source_node_id': fields.String(description='源节点ID'),
        'target_node_id': fields.String(description='目标节点ID'),
        'edge_type': fields.String(description='边类型'),
        'metadata': fields.Raw(description='边元数据')
    })

    # 创建案例请求模型
    create_case_model = cases_ns.model('CreateCaseRequest', {
        'query': fields.String(required=True, description='用户问题描述'),
        'attachments': fields.List(fields.Raw, description='附件列表'),
        'useLanggraph': fields.Boolean(description='是否使用langgraph Agent', default=False),
        'vendor': fields.String(description='设备厂商')
    })

    # 更新案例请求模型
    update_case_model = cases_ns.model('UpdateCaseRequest', {
        'title': fields.String(description='案例标题'),
        'status': fields.String(description='案例状态', enum=['open', 'solved', 'closed'])
    })

    # 交互处理请求模型
    interaction_model = cases_ns.model('InteractionRequest', {
        'parentNodeId': fields.String(required=True, description='父节点ID'),
        'response': fields.Raw(required=True, description='用户响应数据'),
        'retrievalWeight': fields.Float(description='检索权重', default=0.7),
        'filterTags': fields.List(fields.String, description='过滤标签')
    })

    # 节点评价请求模型
    rate_node_model = cases_ns.model('RateNodeRequest', {
        'rating': fields.Integer(required=True, description='评分 (1-5)', min=1, max=5),
        'comment': fields.String(description='评论')
    })

    # 反馈请求模型
    feedback_model = cases_ns.model('FeedbackRequest', {
        'rating': fields.Integer(description='整体评分 (1-5)', min=1, max=5),
        'comment': fields.String(description='反馈评论'),
        'is_helpful': fields.Boolean(description='是否有帮助'),
        'suggestions': fields.String(description='改进建议')
    })

    @cases_ns.route('/')
    class CasesList(Resource):
        @cases_ns.doc('get_cases')
        @cases_ns.doc(security='Bearer Auth')
        @cases_ns.param('status', '案例状态过滤', enum=['open', 'solved', 'closed'])
        @cases_ns.param('vendor', '厂商过滤')
        @cases_ns.param('category', '分类过滤')
        @cases_ns.param('attachmentType', '附件类型过滤', enum=['image', 'document', 'log', 'config', 'other'])
        @cases_ns.param('page', '页码', type='integer', default=1)
        @cases_ns.param('pageSize', '每页大小', type='integer', default=10)
        @jwt_required()
        def get(self):
            """获取案例列表

            支持多种过滤条件和分页查询。
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

                if status:
                    query = query.filter_by(status=status)
                if vendor:
                    query = query.filter_by(vendor=vendor)
                if category:
                    query = query.filter_by(category=category)

                # 分页查询
                pagination = query.order_by(Case.created_at.desc()).paginate(
                    page=page, per_page=page_size, error_out=False
                )

                cases_data = []
                for case in pagination.items:
                    case_dict = case.to_dict()
                    # 添加统计信息
                    case_dict['nodes_count'] = Node.query.filter_by(case_id=case.id).count()
                    case_dict['edges_count'] = Edge.query.filter_by(case_id=case.id).count()
                    cases_data.append(case_dict)

                # RESTX 返回纯 dict + 状态码，避免 Response 再序列化
                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'items': cases_data,
                        'pagination': {
                            'total': pagination.total,
                            'page': page,
                            'per_page': page_size,
                            'pages': pagination.pages
                        }
                    }
                }, 200

            except Exception as e:
                current_app.logger.error(f"获取案例列表失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '获取案例列表失败'
                    }
                }, 500

        @cases_ns.doc('create_case')
        @cases_ns.doc(security='Bearer Auth')
        @cases_ns.expect(create_case_model)
        @jwt_required()
        def post(self):
            """创建新案例

            根据用户问题描述创建新的诊断案例，支持附件上传和厂商指定。
            """
            try:
                user_id = get_jwt_identity()
                data = request.get_json()

                if not data or not data.get('query'):
                    return validation_error('问题描述不能为空')

                # 创建新案例
                # Case 模型无 query/vendor 字段，仅存储 title/status/user_id
                title = data.get('query') or '新案例'
                if len(title) > 100:
                    title = title[:100] + '...'
                case = Case(
                    id=str(uuid.uuid4()),
                    title=title,
                    user_id=user_id,
                    status='open',
                    created_at=datetime.utcnow()
                )

                db.session.add(case)
                db.session.flush()

                # 自动创建根节点（用户问题）
                root_node = Node(
                    case_id=case.id,
                    type='USER_QUERY',
                    title='用户问题',
                    status='COMPLETED',
                    content={
                        'query': data.get('query'),
                        'attachments': data.get('attachments') or []
                    },
                    node_metadata={
                        'created_from': 'create_case'
                    }
                )
                db.session.add(root_node)
                db.session.commit()

                return {
                    'code': 201,
                    'status': 'success',
                    'data': {
                        **case.to_dict(),
                        'rootNodeId': root_node.id
                    }
                }, 201

            except Exception as e:
                current_app.logger.error(f"创建案例失败: {str(e)}")
                return {
                    'code': 500,
                    'status': 'error',
                    'error': {
                        'type': 'INTERNAL_ERROR',
                        'message': '创建案例失败'
                    }
                }, 500

    @cases_ns.route('/<string:case_id>')
    class CaseDetail(Resource):
        @cases_ns.doc('get_case_detail')
        @cases_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self, case_id):
            """获取案例详情

            返回完整的案例信息，包括所有节点和边。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                # 获取案例的所有节点和边
                nodes = Node.query.filter_by(case_id=case_id).all()
                edges = Edge.query.filter_by(case_id=case_id).all()

                case_data = case.to_dict()
                case_data['nodes'] = [node.to_dict() for node in nodes]
                case_data['edges'] = [edge.to_dict() for edge in edges]

                return {'code': 200, 'status': 'success', 'data': case_data}, 200

            except Exception as e:
                current_app.logger.error(f"获取案例详情失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取案例详情失败'}}, 500

        @cases_ns.doc('update_case')
        @cases_ns.doc(security='Bearer Auth')
        @cases_ns.expect(update_case_model)
        @jwt_required()
        def put(self, case_id):
            """更新案例信息

            支持更新案例标题和状态。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                data = request.get_json()
                if not data:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '请求体不能为空'}}, 400

                # 更新案例信息
                if 'title' in data:
                    case.title = data['title']
                if 'status' in data:
                    case.status = data['status']

                case.updated_at = datetime.utcnow()
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': case.to_dict()}, 200

            except Exception as e:
                current_app.logger.error(f"更新案例失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '更新案例失败'}}, 500

        @cases_ns.doc('delete_case')
        @cases_ns.doc(security='Bearer Auth')
        @jwt_required()
        def delete(self, case_id):
            """删除案例

            删除案例及其所有相关的节点和边。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                # 删除相关的节点和边
                Node.query.filter_by(case_id=case_id).delete()
                Edge.query.filter_by(case_id=case_id).delete()

                # 删除案例
                db.session.delete(case)
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': {'message': '案例删除成功'}}, 200

            except Exception as e:
                current_app.logger.error(f"删除案例失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '删除案例失败'}}, 500

    @cases_ns.route('/<string:case_id>/interaction')
    class CaseInteraction(Resource):
        @cases_ns.doc('handle_interaction')
        @cases_ns.doc(security='Bearer Auth')
        @cases_ns.expect(interaction_model)
        @jwt_required()
        def post(self, case_id):
            """处理多轮交互

            处理用户与案例的交互，生成新的节点和边。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                data = request.get_json(silent=True) or {}
                # 宽松校验：允许 parentNodeId 或 response 任一存在；另一个使用默认
                parent_node_id = data.get('parentNodeId')
                response_payload = data.get('response')
                if parent_node_id is None and response_payload is None:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '缺少必需参数（parentNodeId/response 至少一个）'}}, 400

                # 当未提供 parentNodeId 时，选择该案例最新节点作为父节点
                if parent_node_id is None:
                    parent_node = Node.query.filter_by(case_id=case_id).order_by(Node.created_at.desc()).first()
                    if not parent_node:
                        return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '该案例暂无可引用的父节点'}}, 404
                    parent_node_id = parent_node.id
                else:
                    parent_node = Node.query.filter_by(id=parent_node_id, case_id=case_id).first()
                    if not parent_node:
                        return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '父节点不存在'}}, 404

                # 创建用户响应节点
                new_node = Node(
                    case_id=case.id,
                    type='USER_RESPONSE',
                    title='用户回复',
                    status='COMPLETED',
                    content=(response_payload if response_payload is not None else {'text': ''}),
                    node_metadata={
                        'created_from': 'interaction',
                        'parent_node_id': parent_node_id
                    }
                )
                db.session.add(new_node)
                db.session.flush()

                # 记录边（可选）
                try:
                    edge = Edge(
                        case_id=case.id,
                        source=parent_node_id,
                        target=new_node.id
                    )
                    db.session.add(edge)
                except Exception:
                    pass

                db.session.commit()

                return {
                    'code': 200,
                    'status': 'success',
                    'data': {
                        'message': '交互处理成功',
                        'nodeId': new_node.id
                    }
                }, 200

            except Exception as e:
                current_app.logger.error(f"处理交互失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '处理交互失败'}}, 500

    @cases_ns.route('/<string:case_id>/nodes/<string:node_id>/rate')
    class NodeRating(Resource):
        @cases_ns.doc('rate_node')
        @cases_ns.doc(security='Bearer Auth')
        @cases_ns.expect(rate_node_model)
        @jwt_required()
        def post(self, case_id, node_id):
            """评价节点

            对指定节点进行评分和评论。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                node = Node.query.filter_by(id=node_id, case_id=case_id).first()
                if not node:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '节点不存在'}}, 404

                data = request.get_json()
                if not data or 'rating' not in data:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '评分不能为空'}}, 400

                # 更新节点评分信息（字段为 node_metadata）
                if not node.node_metadata:
                    node.node_metadata = {}

                node.node_metadata['rating'] = data['rating']
                if data.get('comment'):
                    node.node_metadata['comment'] = data['comment']

                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': {'message': '节点评价成功'}}, 200

            except Exception as e:
                current_app.logger.error(f"节点评价失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '节点评价失败'}}, 500

    @cases_ns.route('/<string:case_id>/feedback')
    class CaseFeedback(Resource):
        @cases_ns.doc('create_or_update_feedback')
        @cases_ns.doc(security='Bearer Auth')
        @cases_ns.expect(feedback_model)
        @jwt_required()
        def put(self, case_id):
            """创建或更新案例反馈

            对整个案例进行反馈评价。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                data = request.get_json()
                if not data:
                    return {'code': 400, 'status': 'error', 'error': {'type': 'INVALID_REQUEST', 'message': '请求体不能为空'}}, 400

                # 查找或创建反馈记录
                feedback = Feedback.query.filter_by(case_id=case_id).first()
                if not feedback:
                    feedback = Feedback(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        user_id=user_id,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(feedback)

                # 更新反馈信息
                # outcome 为必填枚举，未提供时按案例状态推断，默认 'unsolved'
                if feedback.outcome is None:
                    case_status = case.status if hasattr(case, 'status') else 'open'
                    inferred = 'unsolved'
                    if case_status == 'solved':
                        inferred = 'solved'
                    feedback.outcome = inferred
                if 'rating' in data:
                    feedback.rating = data['rating']
                if 'comment' in data:
                    feedback.comment = data['comment']
                if 'is_helpful' in data:
                    feedback.is_helpful = data['is_helpful']
                if 'suggestions' in data:
                    feedback.suggestions = data['suggestions']

                feedback.updated_at = datetime.utcnow()
                db.session.commit()

                return {'code': 200, 'status': 'success', 'data': feedback.to_dict()}, 200

            except Exception as e:
                current_app.logger.error(f"提交反馈失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '提交反馈失败'}}, 500

        @cases_ns.doc('get_feedback')
        @cases_ns.doc(security='Bearer Auth')
        @jwt_required()
        def get(self, case_id):
            """获取案例反馈

            返回指定案例的反馈信息。
            """
            try:
                user_id = get_jwt_identity()
                case = Case.query.filter_by(id=case_id, user_id=user_id).first()

                if not case:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '案例不存在'}}, 404

                feedback = Feedback.query.filter_by(case_id=case_id).first()
                if not feedback:
                    return {'code': 404, 'status': 'error', 'error': {'type': 'NOT_FOUND', 'message': '暂无反馈信息'}}, 404

                return {'code': 200, 'status': 'success', 'data': feedback.to_dict()}, 200

            except Exception as e:
                current_app.logger.error(f"获取反馈失败: {str(e)}")
                return {'code': 500, 'status': 'error', 'error': {'type': 'INTERNAL_ERROR', 'message': '获取反馈失败'}}, 500

    print("✅ 案例管理API接口已注册到Flask-RESTX文档系统")
