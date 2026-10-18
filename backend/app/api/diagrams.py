"""API Router for Architecture Diagrams (Physical Infrastructure, Logical Topology, Application Flows)."""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.equipment import Equipment
from app.models.network import NetworkSegment
from app.schemas.diagram import DiagramResponse
from app.core.diagrams.physical_diagram import generate_physical_svg
from app.core.diagrams.logical_topology import generate_logical_svg
from app.core.diagrams.flow_diagram import generate_flow_svg

router = APIRouter(prefix="/projects/{project_id}/diagrams", tags=["Architecture Diagrams"])


async def get_project_and_assets(project_id: str, db: AsyncSession):
    """Helper to fetch project, equipment, interfaces, and network segments."""
    p_res = await db.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    eq_res = await db.execute(
        select(Equipment)
        .options(
            selectinload(Equipment.site),
            selectinload(Equipment.location),
            selectinload(Equipment.interfaces)
        )
        .where(Equipment.project_id == project_id)
        .order_by(Equipment.name)
    )
    equipment_list = eq_res.scalars().all()

    seg_res = await db.execute(
        select(NetworkSegment)
        .where(NetworkSegment.project_id == project_id)
        .order_by(NetworkSegment.vlan_id)
    )
    segments = seg_res.scalars().all()

    return project, equipment_list, segments


@router.get("/physical", response_model=DiagramResponse)
async def get_physical_diagram(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and return physical infrastructure SVG diagram."""
    project, equipment_list, _ = await get_project_and_assets(project_id, db)
    svg_content = generate_physical_svg(project, equipment_list)

    return DiagramResponse(
        diagram_type="physical",
        title="Schéma d'Infrastructure Physique (Sites & Baies)",
        svg=svg_content,
        elements_count=len(equipment_list),
        generated_at=datetime.now(timezone.utc)
    )


@router.get("/physical/raw")
async def get_physical_diagram_raw(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download or view raw SVG image for physical infrastructure."""
    project, equipment_list, _ = await get_project_and_assets(project_id, db)
    svg_content = generate_physical_svg(project, equipment_list)
    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/logical", response_model=DiagramResponse)
async def get_logical_diagram(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and return logical network topology SVG diagram."""
    project, equipment_list, segments = await get_project_and_assets(project_id, db)
    svg_content = generate_logical_svg(project, equipment_list, segments)

    return DiagramResponse(
        diagram_type="logical",
        title="Topologie Réseau Logique (VLANs & Routage)",
        svg=svg_content,
        elements_count=len(segments),
        generated_at=datetime.now(timezone.utc)
    )


@router.get("/logical/raw")
async def get_logical_diagram_raw(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download or view raw SVG image for logical topology."""
    project, equipment_list, segments = await get_project_and_assets(project_id, db)
    svg_content = generate_logical_svg(project, equipment_list, segments)
    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/flows", response_model=DiagramResponse)
async def get_flow_diagram(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and return application flow matrix SVG diagram."""
    project, _, segments = await get_project_and_assets(project_id, db)
    svg_content = generate_flow_svg(project, segments)

    return DiagramResponse(
        diagram_type="flows",
        title="Matrice des Flux Applicatifs & Règles Inter-Zones",
        svg=svg_content,
        elements_count=len(segments),
        generated_at=datetime.now(timezone.utc)
    )


@router.get("/flows/raw")
async def get_flow_diagram_raw(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download or view raw SVG image for flow matrix."""
    project, _, segments = await get_project_and_assets(project_id, db)
    svg_content = generate_flow_svg(project, segments)
    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/all", response_model=List[DiagramResponse])
async def get_all_diagrams(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all architecture diagrams available for the project."""
    project, equipment_list, segments = await get_project_and_assets(project_id, db)

    svg_phys = generate_physical_svg(project, equipment_list)
    svg_log = generate_logical_svg(project, equipment_list, segments)
    svg_flows = generate_flow_svg(project, segments)

    return [
        DiagramResponse(
            diagram_type="physical",
            title="Schéma d'Infrastructure Physique (Sites & Baies)",
            svg=svg_phys,
            elements_count=len(equipment_list),
            generated_at=datetime.now(timezone.utc)
        ),
        DiagramResponse(
            diagram_type="logical",
            title="Topologie Réseau Logique (VLANs & Routage)",
            svg=svg_log,
            elements_count=len(segments),
            generated_at=datetime.now(timezone.utc)
        ),
        DiagramResponse(
            diagram_type="flows",
            title="Matrice des Flux Applicatifs & Règles Inter-Zones",
            svg=svg_flows,
            elements_count=len(segments),
            generated_at=datetime.now(timezone.utc)
        )
    ]
