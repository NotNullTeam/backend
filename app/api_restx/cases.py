"""
案例管理 API 接口 (Flask-RESTX)

将原有的案例管理接口集成到 Flask-RESTX 中，提供自动文档生成功能。
"""

from flask import request, current_app
from flask_restx import Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.docs import cases_ns
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

                return paginated_response(
                    data=cases_data,
                    page=page,
                    per_page=page_size,
                    total=pagination.total,
                    message='获取案例列表成功'
                )

            except Exception as e:
                current_app.logger.error(f"获取案例列表失败: {str(e)}")
                return internal_error('获取案例列表失败')

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
                case = Case(
                    id=str(uuid.uuid4()),
                    title=data.get('query')[:100] + '...' if len(data.get('query', '')) > 100 else data.get('query'),
                    query=data.get('query'),
                    user_id=user_id,
                    vendor=data.get('vendor'),
                    status='open',
                    created_at=datetime.utcnow()
                )
                
                db.session.add(case)
                db.session.commit()

                return success_response(
                    message='案例创建成功',
                    data=case.to_dict()
                )

            except Exception as e:
                current_app.logger.error(f"创建案例失败: {str(e)}")
                return internal_error('创建案例失败')

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
                    return not_found_error('案例不存在')

                # 获取案例的所有节点和边
                nodes = Node.query.filter_by(case_id=case_id).all()
                edges = Edge.query.filter_by(case_id=case_id).all()

                case_data = case.to_dict()
                case_data['nodes'] = [node.to_dict() for node in nodes]
                case_data['edges'] = [edge.to_dict() for edge in edges]

                return success_response(
                    message='获取案例详情成功',
                    data=case_data
                )

            except Exception as e:
                current_app.logger.error(f"获取案例详情失败: {str(e)}")
                return internal_error('获取案例详情失败')

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
                    return not_found_error('案例不存在')

                data = request.get_json()
                if not data:
                    return validation_error('请求体不能为空')

                # 更新案例信息
                if 'title' in data:
                    case.title = data['title']
                if 'status' in data:
                    case.status = data['status']
                
                case.updated_at = datetime.utcnow()
                db.session.commit()

                return success_response(
                    message='案例更新成功',
                    data=case.to_dict()
                )

            except Exception as e:
                current_app.logger.error(f"更新案例失败: {str(e)}")
                return internal_error('更新案例失败')

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
                    return not_found_error('案例不存在')

                # 删除相关的节点和边
                Node.query.filter_by(case_id=case_id).delete()
                Edge.query.filter_by(case_id=case_id).delete()
                
                # 删除案例
                db.session.delete(case)
                db.session.commit()

                return success_response(message='案例删除成功')

            except Exception as e:
                current_app.logger.error(f"删除案例失败: {str(e)}")
                return internal_error('删除案例失败')

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
                    return not_found_error('案例不存在')

                data = request.get_json()
                if not data or not data.get('parentNodeId') or not data.get('response'):
                    return validation_error('缺少必需参数')

                # 这里应该调用实际的交互处理逻辑
                # 暂时返回成功响应
                return success_response(message='交互处理成功')

            except Exception as e:
                current_app.logger.error(f"处理交互失败: {str(e)}")
                return internal_error('处理交互失败')

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
                    return not_found_error('案例不存在')

                node = Node.query.filter_by(id=node_id, case_id=case_id).first()
                if not node:
                    return not_found_error('节点不存在')

                data = request.get_json()
                if not data or 'rating' not in data:
                    return validation_error('评分不能为空')

                # 更新节点评分信息
                if not node.metadata:
                    node.metadata = {}
                
                node.metadata['rating'] = data['rating']
                if data.get('comment'):
                    node.metadata['comment'] = data['comment']
                
                db.session.commit()

                return success_response(message='节点评价成功')

            except Exception as e:
                current_app.logger.error(f"节点评价失败: {str(e)}")
                return internal_error('节点评价失败')

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
                    return not_found_error('案例不存在')

                data = request.get_json()
                if not data:
                    return validation_error('请求体不能为空')

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

                return success_response(
                    message='反馈提交成功',
                    data=feedback.to_dict()
                )

            except Exception as e:
                current_app.logger.error(f"提交反馈失败: {str(e)}")
                return internal_error('提交反馈失败')

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
                    return not_found_error('案例不存在')

                feedback = Feedback.query.filter_by(case_id=case_id).first()
                if not feedback:
                    return not_found_error('暂无反馈信息')

                return success_response(
                    message='获取反馈成功',
                    data=feedback.to_dict()
                )

            except Exception as e:
                current_app.logger.error(f"获取反馈失败: {str(e)}")
                return internal_error('获取反馈失败')

    print("✅ 案例管理API接口已注册到Flask-RESTX文档系统")
