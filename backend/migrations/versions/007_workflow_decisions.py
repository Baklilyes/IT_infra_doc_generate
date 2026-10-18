"""007_workflow_decisions

Revision ID: 007_workflow_decisions
Revises: 006_documents
Create Date: 2026-10-18 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_workflow_decisions'
down_revision: Union[str, None] = '006_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add version and parent_project_id to projects table
    op.add_column('projects', sa.Column('version', sa.String(length=20), nullable=False, server_default='1.0'))
    op.add_column('projects', sa.Column('parent_project_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_projects_parent_project_id',
        'projects',
        'projects',
        ['parent_project_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 2. Create workflow_decisions table
    op.create_table(
        'workflow_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=False),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False, server_default='1.0'),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_decisions_project_id'), 'workflow_decisions', ['project_id'], unique=False)
    op.create_index(op.f('ix_workflow_decisions_user_id'), 'workflow_decisions', ['user_id'], unique=False)
    op.create_index(op.f('ix_workflow_decisions_created_at'), 'workflow_decisions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_decisions_created_at'), table_name='workflow_decisions')
    op.drop_index(op.f('ix_workflow_decisions_user_id'), table_name='workflow_decisions')
    op.drop_index(op.f('ix_workflow_decisions_project_id'), table_name='workflow_decisions')
    op.drop_table('workflow_decisions')

    op.drop_constraint('fk_projects_parent_project_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'parent_project_id')
    op.drop_column('projects', 'version')
