from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project, Site, Location
from app.schemas.project import (
    SiteCreate,
    SiteUpdate,
    SiteDetailResponse,
    LocationCreate,
    LocationUpdate,
    LocationResponse
)
from app.api.deps import get_current_user, require_role

router = APIRouter(tags=["Sites & Locations"])

# -------------------------------------------------------------
# Sites Endpoints
# -------------------------------------------------------------
@router.get("/projects/{project_id}/sites", response_model=List[SiteDetailResponse])
async def list_project_sites(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sites and locations belonging to a specific project."""
    stmt = (
        select(Site)
        .options(selectinload(Site.locations))
        .where(Site.project_id == project_id)
        .order_by(Site.name)
    )
    result = await db.execute(stmt)
    sites = result.scalars().all()

    response = []
    for s in sites:
        locs = [LocationResponse.model_validate(loc) for loc in s.locations]
        response.append(SiteDetailResponse(
            id=s.id,
            project_id=s.project_id,
            name=s.name,
            code=s.code,
            address=s.address,
            city=s.city,
            country=s.country,
            notes=s.notes,
            locations=locs,
            locations_count=len(locs),
            created_at=s.created_at,
            updated_at=s.updated_at
        ))

    return response


@router.post("/projects/{project_id}/sites", response_model=SiteDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_project_site(
    project_id: str,
    site_in: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Add a site to a project (Engineer or Administrator)."""
    # Check project exists
    project_stmt = select(Project).where(Project.id == project_id)
    project = (await db.execute(project_stmt)).scalars().first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable."
        )

    new_site = Site(
        project_id=project_id,
        name=site_in.name,
        code=site_in.code,
        address=site_in.address,
        city=site_in.city,
        country=site_in.country,
        notes=site_in.notes
    )
    db.add(new_site)
    await db.commit()
    await db.refresh(new_site)

    return SiteDetailResponse(
        id=new_site.id,
        project_id=new_site.project_id,
        name=new_site.name,
        code=new_site.code,
        address=new_site.address,
        city=new_site.city,
        country=new_site.country,
        notes=new_site.notes,
        locations=[],
        locations_count=0,
        created_at=new_site.created_at,
        updated_at=new_site.updated_at
    )


@router.get("/sites/{site_id}", response_model=SiteDetailResponse)
async def get_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve site details with all locations."""
    stmt = (
        select(Site)
        .options(selectinload(Site.locations))
        .where(Site.id == site_id)
    )
    site = (await db.execute(stmt)).scalars().first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site introuvable."
        )

    locs = [LocationResponse.model_validate(loc) for loc in site.locations]
    return SiteDetailResponse(
        id=site.id,
        project_id=site.project_id,
        name=site.name,
        code=site.code,
        address=site.address,
        city=site.city,
        country=site.country,
        notes=site.notes,
        locations=locs,
        locations_count=len(locs),
        created_at=site.created_at,
        updated_at=site.updated_at
    )


@router.put("/sites/{site_id}", response_model=SiteDetailResponse)
async def update_site(
    site_id: str,
    site_update: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Update site information."""
    stmt = (
        select(Site)
        .options(selectinload(Site.locations))
        .where(Site.id == site_id)
    )
    site = (await db.execute(stmt)).scalars().first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site introuvable."
        )

    update_data = site_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(site, field, val)

    await db.commit()
    await db.refresh(site)

    locs = [LocationResponse.model_validate(loc) for loc in site.locations]
    return SiteDetailResponse(
        id=site.id,
        project_id=site.project_id,
        name=site.name,
        code=site.code,
        address=site.address,
        city=site.city,
        country=site.country,
        notes=site.notes,
        locations=locs,
        locations_count=len(locs),
        created_at=site.created_at,
        updated_at=site.updated_at
    )


@router.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Delete a site and its locations."""
    stmt = select(Site).where(Site.id == site_id)
    site = (await db.execute(stmt)).scalars().first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site introuvable."
        )

    await db.delete(site)
    await db.commit()
    return None


# -------------------------------------------------------------
# Locations Endpoints (Rooms & Racks)
# -------------------------------------------------------------
@router.post("/sites/{site_id}/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    site_id: str,
    loc_in: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Add a room / rack location to a site."""
    site_stmt = select(Site).where(Site.id == site_id)
    site = (await db.execute(site_stmt)).scalars().first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site introuvable."
        )

    new_loc = Location(
        site_id=site_id,
        name=loc_in.name,
        room=loc_in.room,
        rack=loc_in.rack,
        notes=loc_in.notes
    )
    db.add(new_loc)
    await db.commit()
    await db.refresh(new_loc)
    return LocationResponse.model_validate(new_loc)


@router.put("/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: str,
    loc_update: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Update a location."""
    stmt = select(Location).where(Location.id == location_id)
    loc = (await db.execute(stmt)).scalars().first()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emplacement introuvable."
        )

    update_data = loc_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(loc, field, val)

    await db.commit()
    await db.refresh(loc)
    return LocationResponse.model_validate(loc)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR, UserRole.ENGINEER))
):
    """Delete a location."""
    stmt = select(Location).where(Location.id == location_id)
    loc = (await db.execute(stmt)).scalars().first()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emplacement introuvable."
        )

    await db.delete(loc)
    await db.commit()
    return None
