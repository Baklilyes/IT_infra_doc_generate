from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.network_validator import is_secret_field, mask_secret
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.equipment import Equipment
from app.models.network import ConfigurationParam
from app.schemas.network import (
    ConfigurationParamCreate,
    ConfigurationParamUpdate,
    ConfigurationParamResponse
)
from app.api.deps import get_current_user, require_role

router = APIRouter(tags=["Technical Configurations"])

@router.get("/projects/{project_id}/configurations", response_model=List[ConfigurationParamResponse])
async def list_project_configurations(
    project_id: str,
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    equipment_id: Optional[str] = Query(None, description="Filtrer par équipement"),
    unmask: bool = Query(False, description="Afficher les secrets en clair (Admin uniquement)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List structured technical configuration parameters.
    Secrets are automatically masked with <SECRET_MASQUÉ> unless unmask is explicitly requested by an Administrator.
    """
    stmt = (
        select(ConfigurationParam)
        .options(selectinload(ConfigurationParam.equipment))
        .where(ConfigurationParam.project_id == project_id)
        .order_by(ConfigurationParam.category, ConfigurationParam.key)
    )
    if category:
        stmt = stmt.where(ConfigurationParam.category == category)
    if equipment_id:
        stmt = stmt.where(ConfigurationParam.equipment_id == equipment_id)

    result = await db.execute(stmt)
    params = result.scalars().all()

    allow_unmask = unmask and (current_user.role == UserRole.ADMINISTRATOR)

    response = []
    for p in params:
        display_val = p.value
        if (p.is_secret or is_secret_field(p.key)) and not allow_unmask:
            display_val = mask_secret(p.value)

        response.append(ConfigurationParamResponse(
            id=p.id,
            project_id=p.project_id,
            equipment_id=p.equipment_id,
            equipment_name=p.equipment.name if p.equipment else None,
            category=p.category,
            key=p.key,
            value=display_val,
            is_secret=p.is_secret,
            description=p.description,
            data_source=p.data_source,
            verification_status=p.verification_status,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))

    return response


@router.post("/projects/{project_id}/configurations", response_model=ConfigurationParamResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration_param(
    project_id: str,
    param_in: ConfigurationParamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Add a technical configuration parameter to a project or equipment."""
    # Check project exists
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    # Check equipment belongs to project if specified
    if param_in.equipment_id:
        eq = (await db.execute(select(Equipment).where(Equipment.id == param_in.equipment_id))).scalars().first()
        if not eq or eq.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'équipement spécifié n'appartient pas à ce projet."
            )

    # Auto-detect secret
    is_secret = param_in.is_secret or is_secret_field(param_in.key)

    new_param = ConfigurationParam(
        project_id=project_id,
        equipment_id=param_in.equipment_id,
        category=param_in.category,
        key=param_in.key,
        value=param_in.value,
        is_secret=is_secret,
        description=param_in.description,
        data_source=param_in.data_source,
        verification_status=param_in.verification_status
    )
    db.add(new_param)
    await db.commit()
    await db.refresh(new_param)

    # Mask value on return
    return ConfigurationParamResponse(
        id=new_param.id,
        project_id=new_param.project_id,
        equipment_id=new_param.equipment_id,
        equipment_name=None,
        category=new_param.category,
        key=new_param.key,
        value=mask_secret(new_param.value) if is_secret else new_param.value,
        is_secret=new_param.is_secret,
        description=new_param.description,
        data_source=new_param.data_source,
        verification_status=new_param.verification_status,
        created_at=new_param.created_at,
        updated_at=new_param.updated_at
    )


@router.delete("/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration_param(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Delete a configuration parameter."""
    stmt = select(ConfigurationParam).where(ConfigurationParam.id == config_id)
    param = (await db.execute(stmt)).scalars().first()
    if not param:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paramètre introuvable.")

    await db.delete(param)
    await db.commit()
    return None
