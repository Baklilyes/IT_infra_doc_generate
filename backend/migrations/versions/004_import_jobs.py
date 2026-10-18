"""004_import_jobs

Revision ID: 004_import_jobs
Revises: 003_inventory_and_network
Create Date: 2026-10-18 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_import_jobs'
down_revision: Union[str, None] = '003_inventory_and_network'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'import_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False, server_default='equipment'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mappings', sa.JSON(), nullable=True),
        sa.Column('preview_data', sa.JSON(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_jobs_project_id'), 'import_jobs', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_import_jobs_project_id'), table_name='import_jobs')
    op.drop_table('import_jobs')
