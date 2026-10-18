"""005_consistency_validation

Revision ID: 005_consistency_validation
Revises: 004_import_jobs
Create Date: 2026-10-18 15:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_consistency_validation'
down_revision: Union[str, None] = '004_import_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'consistency_reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('executed_by_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='passed'),
        sa.Column('blocking_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('info_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resolved_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings', sa.JSON(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['executed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consistency_reports_project_id'), 'consistency_reports', ['project_id'], unique=False)

    op.create_table(
        'consistency_overrides',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('overridden_by_id', sa.String(length=36), nullable=True),
        sa.Column('rule_code', sa.String(length=100), nullable=False),
        sa.Column('target_id', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['overridden_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consistency_overrides_project_id'), 'consistency_overrides', ['project_id'], unique=False)
    op.create_index(op.f('ix_consistency_overrides_rule_code'), 'consistency_overrides', ['rule_code'], unique=False)
    op.create_index(op.f('ix_consistency_overrides_target_id'), 'consistency_overrides', ['target_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_consistency_overrides_target_id'), table_name='consistency_overrides')
    op.drop_index(op.f('ix_consistency_overrides_rule_code'), table_name='consistency_overrides')
    op.drop_index(op.f('ix_consistency_overrides_project_id'), table_name='consistency_overrides')
    op.drop_table('consistency_overrides')
    op.drop_index(op.f('ix_consistency_reports_project_id'), table_name='consistency_reports')
    op.drop_table('consistency_reports')
