import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project, Site, Location, ProjectStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectDuplicateRequest,
    SiteDetailResponse,
    LocationResponse
)
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    search: Optional[str] = Query(None, description="Recherche par nom, référence ou client"),
    status: Optional[ProjectStatus] = Query(None, description="Filtrer par statut"),
    client_name: Optional[str] = Query(None, description="Filtrer par client"),
    is_archived: bool = Query(False, description="Afficher les projets archivés"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List projects with search, status filters, and site counts.
    """
    stmt = (
        select(Project)
        .options(selectinload(Project.sites))
        .where(Project.is_archived == is_archived)
        .order_by(Project.updated_at.desc())
    )

    if status:
        stmt = stmt.where(Project.status == status)
    
    if client_name:
        stmt = stmt.where(Project.client_name.ilike(f"%{client_name}%"))

    if search:
        search_filter = or_(
            Project.name.ilike(f"%{search}%"),
            Project.reference.ilike(f"%{search}%"),
            Project.client_name.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    # Format response with computed sites_count
    response = []
    for p in projects:
        p_dict = ProjectResponse.model_validate(p)
        p_dict.sites_count = len(p.sites)
        response.append(p_dict)

    return response


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Create a new infrastructure project (Engineer or Administrator).
    Ensures unique reference and optionally creates initial site.
    """
    # Check reference uniqueness
    existing_stmt = select(Project).where(Project.reference == project_in.reference)
    existing = (await db.execute(existing_stmt)).scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un projet avec la référence '{project_in.reference}' existe déjà."
        )

    new_project = Project(
        reference=project_in.reference,
        name=project_in.name,
        client_name=project_in.client_name,
        description=project_in.description,
        scope=project_in.scope,
        lead_name=project_in.lead_name,
        contributors=project_in.contributors,
        status=project_in.status,
        document_language=project_in.document_language,
        target_date=project_in.target_date,
        created_by_id=current_user.id
    )
    db.add(new_project)
    await db.flush()

    # Create optional initial site if specified
    if project_in.initial_site_name:
        initial_site = Site(
            project_id=new_project.id,
            name=project_in.initial_site_name,
            code="SITE-01"
        )
        db.add(initial_site)
        await db.flush()

    await db.commit()

    # Reload with full relations
    return await get_project(new_project.id, db, current_user)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve project details, including all associated sites and locations.
    """
    stmt = (
        select(Project)
        .options(
            selectinload(Project.sites).selectinload(Site.locations)
        )
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable."
        )

    sites_resp = []
    for s in project.sites:
        locations_resp = [LocationResponse.model_validate(loc) for loc in s.locations]
        sites_resp.append(SiteDetailResponse(
            id=s.id,
            project_id=s.project_id,
            name=s.name,
            code=s.code,
            address=s.address,
            city=s.city,
            country=s.country,
            notes=s.notes,
            locations=locations_resp,
            locations_count=len(locations_resp),
            created_at=s.created_at,
            updated_at=s.updated_at
        ))

    return ProjectDetailResponse(
        id=project.id,
        reference=project.reference,
        name=project.name,
        client_name=project.client_name,
        description=project.description,
        scope=project.scope,
        lead_name=project.lead_name,
        contributors=project.contributors,
        status=project.status,
        document_language=project.document_language,
        target_date=project.target_date,
        is_archived=project.is_archived,
        created_by_id=project.created_by_id,
        sites=sites_resp,
        sites_count=len(sites_resp),
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.put("/{project_id}", response_model=ProjectDetailResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Update project metadata or status (Engineer or Administrator).
    """
    stmt = (
        select(Project)
        .options(selectinload(Project.sites).selectinload(Site.locations))
        .where(Project.id == project_id)
    )
    project = (await db.execute(stmt)).scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable."
        )

    update_data = project_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(project, field, val)

    await db.commit()
    return await get_project(project_id, db, current_user)


@router.post("/{project_id}/duplicate", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_project(
    project_id: str,
    dup_req: ProjectDuplicateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Duplicate a project, cloning its sites and locations with new UUIDs.
    Resets status to DRAFT and creates an isolated copy with no historical cross-contamination.
    """
    # 1. Verify unique reference for duplicate
    ref_check = (await db.execute(select(Project).where(Project.reference == dup_req.new_reference))).scalars().first()
    if ref_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La référence '{dup_req.new_reference}' est déjà utilisée par un autre projet."
        )

    # 2. Load original project
    stmt = (
        select(Project)
        .options(selectinload(Project.sites).selectinload(Site.locations))
        .where(Project.id == project_id)
    )
    original = (await db.execute(stmt)).scalars().first()
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet source introuvable."
        )

    # 3. Create cloned project
    cloned_project = Project(
        id=str(uuid.uuid4()),
        reference=dup_req.new_reference,
        name=dup_req.new_name or f"{original.name} - Copie",
        client_name=original.client_name,
        description=original.description,
        scope=original.scope,
        lead_name=current_user.full_name,
        contributors=original.contributors,
        status=ProjectStatus.DRAFT,
        document_language=original.document_language,
        target_date=None,
        is_archived=False,
        created_by_id=current_user.id
    )
    db.add(cloned_project)
    await db.flush()

    # 4. Clone sites and locations
    for orig_site in original.sites:
        cloned_site = Site(
            id=str(uuid.uuid4()),
            project_id=cloned_project.id,
            name=orig_site.name,
            code=orig_site.code,
            address=orig_site.address,
            city=orig_site.city,
            country=orig_site.country,
            notes=orig_site.notes
        )
        db.add(cloned_site)
        await db.flush()

        for orig_loc in orig_site.locations:
            cloned_loc = Location(
                id=str(uuid.uuid4()),
                site_id=cloned_site.id,
                name=orig_loc.name,
                room=orig_loc.room,
                rack=orig_loc.rack,
                notes=orig_loc.notes
            )
            db.add(cloned_loc)

    await db.commit()
    return await get_project(cloned_project.id, db, current_user)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def toggle_archive_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Toggle archive status of a project.
    """
    stmt = select(Project).options(selectinload(Project.sites)).where(Project.id == project_id)
    project = (await db.execute(stmt)).scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable."
        )

    project.is_archived = not project.is_archived
    await db.commit()

    p_dict = ProjectResponse.model_validate(project)
    p_dict.sites_count = len(project.sites)
    return p_dict


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """
    Delete a project and cascade-delete its sites and locations.
    """
    stmt = select(Project).where(Project.id == project_id)
    project = (await db.execute(stmt)).scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable."
        )

    await db.delete(project)
    await db.commit()
    return None
