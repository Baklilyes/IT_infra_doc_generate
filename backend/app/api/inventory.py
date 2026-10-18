from typing import List, Optional, Dict
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.network_validator import is_valid_ipv4
from app.models.user import User, UserRole
from app.models.project import Project, Site, Location
from app.models.equipment import Equipment, EquipmentCategory, InstallationStatus, VerificationStatus
from app.schemas.inventory import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    DuplicateFinding
)
from app.api.deps import get_current_user, require_role
from app.core.workflow_engine import verify_project_not_locked, invalidate_approvals_if_in_review

router = APIRouter(tags=["Inventory & Equipment"])

@router.get("/projects/{project_id}/equipment", response_model=List[EquipmentResponse])
async def list_project_equipment(
    project_id: str,
    category: Optional[EquipmentCategory] = Query(None, description="Filtrer par famille d'équipement"),
    site_id: Optional[str] = Query(None, description="Filtrer par site"),
    manufacturer: Optional[str] = Query(None, description="Filtrer par constructeur"),
    search: Optional[str] = Query(None, description="Recherche par nom, modèle ou IP"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all equipment for a project with rich filtering and relationships.
    """
    stmt = (
        select(Equipment)
        .options(
            selectinload(Equipment.site),
            selectinload(Equipment.location),
            selectinload(Equipment.interfaces),
            selectinload(Equipment.configurations)
        )
        .where(Equipment.project_id == project_id)
        .order_by(Equipment.category, Equipment.name)
    )

    if category:
        stmt = stmt.where(Equipment.category == category)
    if site_id:
        stmt = stmt.where(Equipment.site_id == site_id)
    if manufacturer:
        stmt = stmt.where(Equipment.manufacturer.ilike(f"%{manufacturer}%"))
    if search:
        search_filter = or_(
            Equipment.name.ilike(f"%{search}%"),
            Equipment.model.ilike(f"%{search}%"),
            Equipment.management_ip.ilike(f"%{search}%"),
            Equipment.serial_number.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    result = await db.execute(stmt)
    equipments = result.scalars().all()

    response = []
    for eq in equipments:
        eq_dict = EquipmentResponse(
            id=eq.id,
            project_id=eq.project_id,
            site_id=eq.site_id,
            site_name=eq.site.name if eq.site else None,
            location_id=eq.location_id,
            location_name=eq.location.name if eq.location else None,
            name=eq.name,
            category=eq.category,
            subcategory=eq.subcategory,
            manufacturer=eq.manufacturer,
            model=eq.model,
            serial_number=eq.serial_number,
            management_ip=eq.management_ip,
            firmware_version=eq.firmware_version,
            role=eq.role,
            installation_status=eq.installation_status,
            verification_status=eq.verification_status,
            data_source=eq.data_source,
            notes=eq.notes,
            specific_attributes=eq.specific_attributes or {},
            interfaces_count=len(eq.interfaces),
            configurations_count=len(eq.configurations),
            created_at=eq.created_at,
            updated_at=eq.updated_at
        )
        response.append(eq_dict)

    return response


@router.post("/projects/{project_id}/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    project_id: str,
    eq_in: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Create a new infrastructure equipment item attached to a project.
    """
    # 1. Verify project exists
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    verify_project_not_locked(project)
    await invalidate_approvals_if_in_review(project, db, user_id=current_user.id)

    # 2. Validate IP format if provided
    if eq_in.management_ip and not is_valid_ipv4(eq_in.management_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"L'adresse IP de gestion '{eq_in.management_ip}' n'est pas une adresse IPv4 valide."
        )

    # 3. Verify site belongs to project if specified
    if eq_in.site_id:
        site = (await db.execute(select(Site).where(Site.id == eq_in.site_id))).scalars().first()
        if not site or site.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le site spécifié n'appartient pas à ce projet."
            )

    new_eq = Equipment(
        project_id=project_id,
        site_id=eq_in.site_id,
        location_id=eq_in.location_id,
        name=eq_in.name,
        category=eq_in.category,
        subcategory=eq_in.subcategory,
        manufacturer=eq_in.manufacturer,
        model=eq_in.model,
        serial_number=eq_in.serial_number,
        management_ip=eq_in.management_ip,
        firmware_version=eq_in.firmware_version,
        role=eq_in.role,
        installation_status=eq_in.installation_status,
        verification_status=eq_in.verification_status,
        data_source=eq_in.data_source,
        notes=eq_in.notes,
        specific_attributes=eq_in.specific_attributes or {}
    )
    db.add(new_eq)
    await db.commit()
    await db.refresh(new_eq)

    return await get_equipment(new_eq.id, db, current_user)


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve single equipment with relations.
    """
    stmt = (
        select(Equipment)
        .options(
            selectinload(Equipment.site),
            selectinload(Equipment.location),
            selectinload(Equipment.interfaces),
            selectinload(Equipment.configurations)
        )
        .where(Equipment.id == equipment_id)
    )
    eq = (await db.execute(stmt)).scalars().first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipement introuvable.")

    return EquipmentResponse(
        id=eq.id,
        project_id=eq.project_id,
        site_id=eq.site_id,
        site_name=eq.site.name if eq.site else None,
        location_id=eq.location_id,
        location_name=eq.location.name if eq.location else None,
        name=eq.name,
        category=eq.category,
        subcategory=eq.subcategory,
        manufacturer=eq.manufacturer,
        model=eq.model,
        serial_number=eq.serial_number,
        management_ip=eq.management_ip,
        firmware_version=eq.firmware_version,
        role=eq.role,
        installation_status=eq.installation_status,
        verification_status=eq.verification_status,
        data_source=eq.data_source,
        notes=eq.notes,
        specific_attributes=eq.specific_attributes or {},
        interfaces_count=len(eq.interfaces),
        configurations_count=len(eq.configurations),
        created_at=eq.created_at,
        updated_at=eq.updated_at
    )


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: str,
    eq_update: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Update an equipment item.
    """
    stmt = select(Equipment).where(Equipment.id == equipment_id)
    eq = (await db.execute(stmt)).scalars().first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipement introuvable.")

    # Check project lock & invalidate review if needed
    project = (await db.execute(select(Project).where(Project.id == eq.project_id))).scalars().first()
    if project:
        verify_project_not_locked(project)
        await invalidate_approvals_if_in_review(project, db, user_id=current_user.id)

    update_data = eq_update.model_dump(exclude_unset=True)

    if "management_ip" in update_data and update_data["management_ip"]:
        if not is_valid_ipv4(update_data["management_ip"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'adresse IP '{update_data['management_ip']}' n'est pas une adresse IPv4 valide."
            )

    for field, val in update_data.items():
        setattr(eq, field, val)

    await db.commit()
    return await get_equipment(equipment_id, db, current_user)


@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Delete an equipment item and cascade-delete its interfaces and configs.
    """
    stmt = select(Equipment).where(Equipment.id == equipment_id)
    eq = (await db.execute(stmt)).scalars().first()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipement introuvable.")

    project = (await db.execute(select(Project).where(Project.id == eq.project_id))).scalars().first()
    if project:
        verify_project_not_locked(project)
        await invalidate_approvals_if_in_review(project, db, user_id=current_user.id)

    await db.delete(eq)
    await db.commit()
    return None


@router.get("/projects/{project_id}/equipment/duplicates", response_model=List[DuplicateFinding])
async def detect_duplicates(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Detect potential duplicates within a project (matching hostname, serial number, or management IP).
    """
    stmt = select(Equipment).where(Equipment.project_id == project_id)
    result = await db.execute(stmt)
    equipments = result.scalars().all()

    names: Dict[str, List[Equipment]] = defaultdict(list)
    serials: Dict[str, List[Equipment]] = defaultdict(list)
    ips: Dict[str, List[Equipment]] = defaultdict(list)

    for eq in equipments:
        if eq.name:
            names[eq.name.strip().lower()].append(eq)
        if eq.serial_number:
            serials[eq.serial_number.strip().upper()].append(eq)
        if eq.management_ip:
            ips[eq.management_ip.strip()].append(eq)

    findings: List[DuplicateFinding] = []

    for name_val, eqs in names.items():
        if len(eqs) > 1:
            findings.append(DuplicateFinding(
                field="name",
                value=name_val,
                equipment_ids=[e.id for e in eqs],
                equipment_names=[e.name for e in eqs]
            ))

    for serial_val, eqs in serials.items():
        if len(eqs) > 1:
            findings.append(DuplicateFinding(
                field="serial_number",
                value=serial_val,
                equipment_ids=[e.id for e in eqs],
                equipment_names=[e.name for e in eqs]
            ))

    for ip_val, eqs in ips.items():
        if len(eqs) > 1:
            findings.append(DuplicateFinding(
                field="management_ip",
                value=ip_val,
                equipment_ids=[e.id for e in eqs],
                equipment_names=[e.name for e in eqs]
            ))

    return findings
