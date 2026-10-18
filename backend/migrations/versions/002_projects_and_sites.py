"""002_projects_and_sites

Revision ID: 002_projects_and_sites
Revises: 001_initial_users
Create Date: 2026-10-18 14:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_projects_and_sites'
down_revision: Union[str, None] = '001_initial_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

project_status_enum = sa.Enum('draft', 'in_preparation', 'in_review', 'validated', 'closed', name='projectstatus')
document_lang_enum = sa.Enum('fr', 'en', name='documentlanguage')

def upgrade() -> None:
    # 1. Projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('reference', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('client_name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('lead_name', sa.String(length=100), nullable=False),
        sa.Column('contributors', sa.Text(), nullable=True),
        sa.Column('status', project_status_enum, nullable=False, server_default='draft'),
        sa.Column('document_language', document_lang_enum, nullable=False, server_default='fr'),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_by_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_reference'), 'projects', ['reference'], unique=True)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)
    op.create_index(op.f('ix_projects_client_name'), 'projects', ['client_name'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)
    op.create_index(op.f('ix_projects_is_archived'), 'projects', ['is_archived'], unique=False)

    # 2. Sites table
    op.create_table(
        'sites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sites_project_id'), 'sites', ['project_id'], unique=False)
    op.create_index(op.f('ix_sites_name'), 'sites', ['name'], unique=False)
    op.create_index(op.f('ix_sites_code'), 'sites', ['code'], unique=False)

    # 3. Locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('site_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('room', sa.String(length=100), nullable=True),
        sa.Column('rack', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locations_site_id'), 'locations', ['site_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_locations_site_id'), table_name='locations')
    op.drop_table('locations')
    op.drop_index(op.f('ix_sites_code'), table_name='sites')
    op.drop_index(op.f('ix_sites_name'), table_name='sites')
    op.drop_index(op.f('ix_sites_project_id'), table_name='sites')
    op.drop_table('sites')
    op.drop_index(op.f('ix_projects_is_archived'), table_name='projects')
    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_client_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_reference'), table_name='projects')
    op.drop_table('projects')
    document_lang_enum.drop(op.get_bind(), checkfirst=True)
    project_status_enum.drop(op.get_bind(), checkfirst=True)
