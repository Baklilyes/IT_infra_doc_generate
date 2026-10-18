"""003_inventory_and_network

Revision ID: 003_inventory_and_network
Revises: 002_projects_and_sites
Create Date: 2026-10-18 14:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_inventory_and_network'
down_revision: Union[str, None] = '002_projects_and_sites'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

equipment_cat_enum = sa.Enum(
    'switch', 'router', 'firewall', 'physical_server', 'hypervisor',
    'virtual_machine', 'storage', 'wifi', 'generic',
    name='equipmentcategory'
)
install_status_enum = sa.Enum('planned', 'installed', 'in_service', 'decommissioned', name='installationstatus')
verif_status_enum = sa.Enum('unverified', 'ai_proposed', 'verified', name='verificationstatus')
interface_type_enum = sa.Enum(
    'physical', 'vlan_interface', 'port_channel', 'loopback', 'subinterface', 'management', 'tunnel',
    name='interfacetype'
)
interface_mode_enum = sa.Enum('access', 'trunk', 'routed', 'unconfigured', name='interfacemode')

def upgrade() -> None:
    # 1. Equipment table
    op.create_table(
        'equipment',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('site_id', sa.String(length=36), nullable=True),
        sa.Column('location_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', equipment_cat_enum, nullable=False),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('management_ip', sa.String(length=50), nullable=True),
        sa.Column('firmware_version', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=150), nullable=True),
        sa.Column('installation_status', install_status_enum, nullable=False, server_default='in_service'),
        sa.Column('verification_status', verif_status_enum, nullable=False, server_default='verified'),
        sa.Column('data_source', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('specific_attributes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_equipment_project_id'), 'equipment', ['project_id'], unique=False)
    op.create_index(op.f('ix_equipment_name'), 'equipment', ['name'], unique=False)
    op.create_index(op.f('ix_equipment_category'), 'equipment', ['category'], unique=False)
    op.create_index(op.f('ix_equipment_serial_number'), 'equipment', ['serial_number'], unique=False)
    op.create_index(op.f('ix_equipment_management_ip'), 'equipment', ['management_ip'], unique=False)

    # 2. Interfaces table
    op.create_table(
        'interfaces',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('equipment_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('interface_type', interface_type_enum, nullable=False, server_default='physical'),
        sa.Column('mac_address', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('subnet_mask', sa.String(length=50), nullable=True),
        sa.Column('mode', interface_mode_enum, nullable=False, server_default='access'),
        sa.Column('access_vlan', sa.Integer(), nullable=True),
        sa.Column('allowed_vlans', sa.String(length=255), nullable=True),
        sa.Column('speed_duplex', sa.String(length=50), nullable=True),
        sa.Column('admin_status', sa.String(length=20), nullable=False, server_default='up'),
        sa.Column('operational_status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('connected_equipment_id', sa.String(length=36), nullable=True),
        sa.Column('connected_interface_name', sa.String(length=100), nullable=True),
        sa.Column('link_type', sa.String(length=50), nullable=True),
        sa.Column('aggregation_group', sa.String(length=50), nullable=True),
        sa.Column('verification_status', verif_status_enum, nullable=False, server_default='verified'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connected_equipment_id'], ['equipment.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interfaces_equipment_id'), 'interfaces', ['equipment_id'], unique=False)
    op.create_index(op.f('ix_interfaces_name'), 'interfaces', ['name'], unique=False)
    op.create_index(op.f('ix_interfaces_ip_address'), 'interfaces', ['ip_address'], unique=False)

    # 3. Network segments table
    op.create_table(
        'network_segments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('site_id', sa.String(length=36), nullable=True),
        sa.Column('vlan_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('cidr', sa.String(length=50), nullable=True),
        sa.Column('gateway', sa.String(length=50), nullable=True),
        sa.Column('dhcp_range', sa.String(length=100), nullable=True),
        sa.Column('dns_servers', sa.String(length=150), nullable=True),
        sa.Column('ntp_servers', sa.String(length=150), nullable=True),
        sa.Column('zone', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_network_segments_project_id'), 'network_segments', ['project_id'], unique=False)
    op.create_index(op.f('ix_network_segments_vlan_id'), 'network_segments', ['vlan_id'], unique=False)
    op.create_index(op.f('ix_network_segments_cidr'), 'network_segments', ['cidr'], unique=False)

    # 4. Configurations table
    op.create_table(
        'configurations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('equipment_id', sa.String(length=36), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('is_secret', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('verification_status', verif_status_enum, nullable=False, server_default='verified'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_configurations_project_id'), 'configurations', ['project_id'], unique=False)
    op.create_index(op.f('ix_configurations_category'), 'configurations', ['category'], unique=False)
    op.create_index(op.f('ix_configurations_key'), 'configurations', ['key'], unique=False)


def downgrade() -> None:
    op.drop_table('configurations')
    op.drop_table('network_segments')
    op.drop_table('interfaces')
    op.drop_table('equipment')
    interface_mode_enum.drop(op.get_bind(), checkfirst=True)
    interface_type_enum.drop(op.get_bind(), checkfirst=True)
    verif_status_enum.drop(op.get_bind(), checkfirst=True)
    install_status_enum.drop(op.get_bind(), checkfirst=True)
    equipment_cat_enum.drop(op.get_bind(), checkfirst=True)
