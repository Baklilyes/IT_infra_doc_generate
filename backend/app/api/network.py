from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.network_validator import is_valid_ipv4, is_valid_cidr, is_valid_vlan
from app.models.user import User, UserRole
from app.models.project import Project, Site
from app.models.equipment import Equipment
from app.models.network import Interface, NetworkSegment
from app.schemas.network import (
    InterfaceCreate,
    InterfaceUpdate,
    InterfaceResponse,
    NetworkSegmentCreate,
    NetworkSegmentUpdate,
    NetworkSegmentResponse
)
from app.api.deps import get_current_user, require_role
from app.core.workflow_engine import verify_project_not_locked, invalidate_approvals_if_in_review

router = APIRouter(tags=["Network & Interfaces"])

# -------------------------------------------------------------
# Interface Endpoints
# -------------------------------------------------------------
@router.get("/equipment/{equipment_id}/interfaces", response_model=List[InterfaceResponse])
async def list_equipment_interfaces(
    equipment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all physical and logical interfaces for an equipment item."""
    stmt = (
        select(Interface)
        .options(selectinload(Interface.connected_equipment))
        .where(Interface.equipment_id == equipment_id)
        .order_by(Interface.name)
    )
    result = await db.execute(stmt)
    interfaces = result.scalars().all()

    response = []
    for intf in interfaces:
        i_dict = InterfaceResponse(
            id=intf.id,
            equipment_id=intf.equipment_id,
            name=intf.name,
            interface_type=intf.interface_type,
            mac_address=intf.mac_address,
            ip_address=intf.ip_address,
            subnet_mask=intf.subnet_mask,
            mode=intf.mode,
            access_vlan=intf.access_vlan,
            allowed_vlans=intf.allowed_vlans,
            speed_duplex=intf.speed_duplex,
            admin_status=intf.admin_status,
            operational_status=intf.operational_status,
            description=intf.description,
            connected_equipment_id=intf.connected_equipment_id,
            connected_equipment_name=intf.connected_equipment.name if intf.connected_equipment else None,
            connected_interface_name=intf.connected_interface_name,
            link_type=intf.link_type,
            aggregation_group=intf.aggregation_group,
            verification_status=intf.verification_status,
            created_at=intf.created_at,
            updated_at=intf.updated_at
        )
        response.append(i_dict)

    return response


@router.post("/equipment/{equipment_id}/interfaces", response_model=InterfaceResponse, status_code=status.HTTP_201_CREATED)
async def create_interface(
    equipment_id: str,
    intf_in: InterfaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Add a network interface to an equipment item."""
    # Check equipment exists
    eq = (await db.execute(select(Equipment).where(Equipment.id == equipment_id))).scalars().first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipement introuvable.")

    # Validations
    if intf_in.ip_address and not is_valid_ipv4(intf_in.ip_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"L'adresse IP '{intf_in.ip_address}' n'est pas une adresse IPv4 valide."
        )

    if intf_in.access_vlan is not None and not is_valid_vlan(intf_in.access_vlan):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le VLAN {intf_in.access_vlan} est hors plage (doit être compris entre 1 et 4094)."
        )

    # Check connected equipment if provided
    if intf_in.connected_equipment_id:
        remote_eq = (await db.execute(select(Equipment).where(Equipment.id == intf_in.connected_equipment_id))).scalars().first()
        if not remote_eq or remote_eq.project_id != eq.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'équipement distant connecté n'appartient pas au même projet."
            )

    new_intf = Interface(
        equipment_id=equipment_id,
        name=intf_in.name,
        interface_type=intf_in.interface_type,
        mac_address=intf_in.mac_address,
        ip_address=intf_in.ip_address,
        subnet_mask=intf_in.subnet_mask,
        mode=intf_in.mode,
        access_vlan=intf_in.access_vlan,
        allowed_vlans=intf_in.allowed_vlans,
        speed_duplex=intf_in.speed_duplex,
        admin_status=intf_in.admin_status,
        operational_status=intf_in.operational_status,
        description=intf_in.description,
        connected_equipment_id=intf_in.connected_equipment_id,
        connected_interface_name=intf_in.connected_interface_name,
        link_type=intf_in.link_type,
        aggregation_group=intf_in.aggregation_group,
        verification_status=intf_in.verification_status
    )
    db.add(new_intf)
    await db.commit()
    await db.refresh(new_intf)

    return await get_interface(new_intf.id, db, current_user)


@router.get("/interfaces/{interface_id}", response_model=InterfaceResponse)
async def get_interface(
    interface_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve an interface."""
    stmt = (
        select(Interface)
        .options(selectinload(Interface.connected_equipment))
        .where(Interface.id == interface_id)
    )
    intf = (await db.execute(stmt)).scalars().first()
    if not intf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interface introuvable.")

    return InterfaceResponse(
        id=intf.id,
        equipment_id=intf.equipment_id,
        name=intf.name,
        interface_type=intf.interface_type,
        mac_address=intf.mac_address,
        ip_address=intf.ip_address,
        subnet_mask=intf.subnet_mask,
        mode=intf.mode,
        access_vlan=intf.access_vlan,
        allowed_vlans=intf.allowed_vlans,
        speed_duplex=intf.speed_duplex,
        admin_status=intf.admin_status,
        operational_status=intf.operational_status,
        description=intf.description,
        connected_equipment_id=intf.connected_equipment_id,
        connected_equipment_name=intf.connected_equipment.name if intf.connected_equipment else None,
        connected_interface_name=intf.connected_interface_name,
        link_type=intf.link_type,
        aggregation_group=intf.aggregation_group,
        verification_status=intf.verification_status,
        created_at=intf.created_at,
        updated_at=intf.updated_at
    )


@router.put("/interfaces/{interface_id}", response_model=InterfaceResponse)
async def update_interface(
    interface_id: str,
    intf_update: InterfaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Update an interface."""
    stmt = select(Interface).where(Interface.id == interface_id)
    intf = (await db.execute(stmt)).scalars().first()
    if not intf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interface introuvable.")

    update_data = intf_update.model_dump(exclude_unset=True)

    if "ip_address" in update_data and update_data["ip_address"]:
        if not is_valid_ipv4(update_data["ip_address"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'adresse IP '{update_data['ip_address']}' n'est pas une adresse IPv4 valide."
            )

    if "access_vlan" in update_data and update_data["access_vlan"] is not None:
        if not is_valid_vlan(update_data["access_vlan"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le VLAN {update_data['access_vlan']} est hors plage (1 à 4094)."
            )

    for field, val in update_data.items():
        setattr(intf, field, val)

    await db.commit()
    return await get_interface(interface_id, db, current_user)


@router.delete("/interfaces/{interface_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interface(
    interface_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Delete an interface."""
    stmt = select(Interface).where(Interface.id == interface_id)
    intf = (await db.execute(stmt)).scalars().first()
    if not intf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interface introuvable.")

    await db.delete(intf)
    await db.commit()
    return None


# -------------------------------------------------------------
# Network Segments (VLAN / Subnets) Endpoints
# -------------------------------------------------------------
@router.get("/projects/{project_id}/segments", response_model=List[NetworkSegmentResponse])
async def list_project_segments(
    project_id: str,
    site_id: Optional[str] = Query(None, description="Filtrer par site"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all VLANs and subnets defined for a project."""
    stmt = (
        select(NetworkSegment)
        .options(selectinload(NetworkSegment.site))
        .where(NetworkSegment.project_id == project_id)
        .order_by(NetworkSegment.vlan_id.nulls_last(), NetworkSegment.name)
    )
    if site_id:
        stmt = stmt.where(NetworkSegment.site_id == site_id)

    result = await db.execute(stmt)
    segments = result.scalars().all()

    return [
        NetworkSegmentResponse(
            id=seg.id,
            project_id=seg.project_id,
            site_id=seg.site_id,
            site_name=seg.site.name if seg.site else None,
            vlan_id=seg.vlan_id,
            name=seg.name,
            cidr=seg.cidr,
            gateway=seg.gateway,
            dhcp_range=seg.dhcp_range,
            dns_servers=seg.dns_servers,
            ntp_servers=seg.ntp_servers,
            zone=seg.zone,
            description=seg.description,
            created_at=seg.created_at,
            updated_at=seg.updated_at
        )
        for seg in segments
    ]


@router.post("/projects/{project_id}/segments", response_model=NetworkSegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_network_segment(
    project_id: str,
    seg_in: NetworkSegmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Add a VLAN / subnet segment to a project."""
    # Check project exists
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    verify_project_not_locked(project)
    await invalidate_approvals_if_in_review(project, db, user_id=current_user.id)

    # Validations
    if seg_in.vlan_id is not None and not is_valid_vlan(seg_in.vlan_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le VLAN ID '{seg_in.vlan_id}' est hors plage (doit être compris entre 1 et 4094)."
        )

    if seg_in.cidr and not is_valid_cidr(seg_in.cidr):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le sous-réseau '{seg_in.cidr}' n'est pas un format CIDR IPv4 valide (ex. 192.168.10.0/24)."
        )

    if seg_in.gateway and not is_valid_ipv4(seg_in.gateway):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La passerelle '{seg_in.gateway}' n'est pas une adresse IPv4 valide."
        )

    new_seg = NetworkSegment(
        project_id=project_id,
        site_id=seg_in.site_id,
        vlan_id=seg_in.vlan_id,
        name=seg_in.name,
        cidr=seg_in.cidr,
        gateway=seg_in.gateway,
        dhcp_range=seg_in.dhcp_range,
        dns_servers=seg_in.dns_servers,
        ntp_servers=seg_in.ntp_servers,
        zone=seg_in.zone,
        description=seg_in.description
    )
    db.add(new_seg)
    await db.commit()
    await db.refresh(new_seg)

    return NetworkSegmentResponse(
        id=new_seg.id,
        project_id=new_seg.project_id,
        site_id=new_seg.site_id,
        site_name=None,
        vlan_id=new_seg.vlan_id,
        name=new_seg.name,
        cidr=new_seg.cidr,
        gateway=new_seg.gateway,
        dhcp_range=new_seg.dhcp_range,
        dns_servers=new_seg.dns_servers,
        ntp_servers=new_seg.ntp_servers,
        zone=new_seg.zone,
        description=new_seg.description,
        created_at=new_seg.created_at,
        updated_at=new_seg.updated_at
    )


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_network_segment(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Delete a network segment."""
    stmt = select(NetworkSegment).where(NetworkSegment.id == segment_id)
    seg = (await db.execute(stmt)).scalars().first()
    if not seg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment introuvable.")

    await db.delete(seg)
    await db.commit()
    return None
