"""Add indexes for statistics performance

Revision ID: 863162781f67
Revises: 91af21e011c8
Create Date: 2025-07-31 20:43:48.771318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '863162781f67'
down_revision = '91af21e011c8'
branch_labels = None
depends_on = None


def upgrade():
    # 为Cases表添加状态索引
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.create_index('ix_cases_status', ['status'], unique=False)
        batch_op.create_index('ix_cases_updated_at', ['updated_at'], unique=False)
        batch_op.create_index('ix_cases_status_created_at', ['status', 'created_at'], unique=False)

    # 为Nodes表添加类型和创建时间索引
    with op.batch_alter_table('nodes', schema=None) as batch_op:
        batch_op.create_index('ix_nodes_type', ['type'], unique=False)
        batch_op.create_index('ix_nodes_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_nodes_type_created_at', ['type', 'created_at'], unique=False)

    # 为KnowledgeDocuments表添加状态和厂商索引
    with op.batch_alter_table('knowledge_documents', schema=None) as batch_op:
        batch_op.create_index('ix_knowledge_documents_status', ['status'], unique=False)
        batch_op.create_index('ix_knowledge_documents_vendor', ['vendor'], unique=False)
        batch_op.create_index('ix_knowledge_documents_status_vendor', ['status', 'vendor'], unique=False)

    # 为Feedback表添加评分和创建时间索引
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.create_index('ix_feedback_rating', ['rating'], unique=False)
        batch_op.create_index('ix_feedback_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_feedback_rating_created_at', ['rating', 'created_at'], unique=False)


def downgrade():
    # 删除Feedback表索引
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.drop_index('ix_feedback_rating_created_at')
        batch_op.drop_index('ix_feedback_created_at')
        batch_op.drop_index('ix_feedback_rating')

    # 删除KnowledgeDocuments表索引
    with op.batch_alter_table('knowledge_documents', schema=None) as batch_op:
        batch_op.drop_index('ix_knowledge_documents_status_vendor')
        batch_op.drop_index('ix_knowledge_documents_vendor')
        batch_op.drop_index('ix_knowledge_documents_status')

    # 删除Nodes表索引
    with op.batch_alter_table('nodes', schema=None) as batch_op:
        batch_op.drop_index('ix_nodes_type_created_at')
        batch_op.drop_index('ix_nodes_created_at')
        batch_op.drop_index('ix_nodes_type')

    # 删除Cases表索引
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_index('ix_cases_status_created_at')
        batch_op.drop_index('ix_cases_updated_at')
        batch_op.drop_index('ix_cases_status')
