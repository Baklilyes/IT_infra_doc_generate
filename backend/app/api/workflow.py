"""API router for project lifecycle workflow, approvals, locking, and version branching."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.user import User, UserRole
from app.models.workflow import WorkflowDecision
from app.schemas.workflow import (
    WorkflowDecisionResponse,
    WorkflowStatusResponse,
    WorkflowActionRequest,
    WorkflowRejectRequest,
    BranchVersionRequest
)
from app.schemas.project import ProjectResponse
from app.api.deps import (
    get_current_user,
    require_engineer,
    require_technical_lead,
    require_final_validator
)
from app.core.workflow_engine import (
    get_workflow_status,
    submit_for_review,
    technical_approve,
    technical_reject,
    final_approve,
    final_reject,
    branch_new_version
)

router = APIRouter(prefix="/projects/{project_id}/workflow", tags=["Workflow & Approbations"])


def format_decision_response(dec: WorkflowDecision) -> WorkflowDecisionResponse:
    """Format WorkflowDecision ORM into Pydantic response with user metadata."""
    u_name = None
    u_role = None
    if dec.user:
        u_name = dec.user.full_name or dec.user.username
        u_role = dec.user.role.value if hasattr(dec.user.role, "value") else str(dec.user.role)

    return WorkflowDecisionResponse(
        id=dec.id,
        project_id=dec.project_id,
        action=dec.action,
        from_status=dec.from_status,
        to_status=dec.to_status,
        version=dec.version,
        comment=dec.comment,
        user_id=dec.user_id,
        user_name=u_name,
        user_role=u_role,
        created_at=dec.created_at
    )


@router.get("", response_model=WorkflowStatusResponse)
async def get_project_workflow_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve current workflow lifecycle state, blocker stats, allowed actions, and last decision."""
    raw_status = await get_workflow_status(project_id, db, current_user)
    last_dec_resp = None
    if raw_status.get("last_decision"):
        last_dec_resp = format_decision_response(raw_status["last_decision"])

    return WorkflowStatusResponse(
        project_id=raw_status["project_id"],
        reference=raw_status["reference"],
        name=raw_status["name"],
        version=raw_status["version"],
        status=raw_status["status"],
        is_locked=raw_status["is_locked"],
        can_publish=raw_status["can_publish"],
        blocking_issues_count=raw_status["blocking_issues_count"],
        allowed_actions=raw_status["allowed_actions"],
        last_decision=last_dec_resp
    )


@router.get("/history", response_model=List[WorkflowDecisionResponse])
async def get_workflow_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve complete audit trail of lifecycle decisions for the project."""
    stmt = select(WorkflowDecision).options(
        selectinload(WorkflowDecision.user)
    ).where(
        WorkflowDecision.project_id == project_id
    ).order_by(desc(WorkflowDecision.created_at))

    res = await db.execute(stmt)
    decisions = res.scalars().all()
    return [format_decision_response(d) for d in decisions]


@router.post("/submit", response_model=WorkflowDecisionResponse)
async def submit_project(
    project_id: str,
    payload: WorkflowActionRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Step 1: Engineer submits dossier for technical review (draft -> in_review).
    Pre-condition: must have zero blocking consistency errors (or all overridden).
    """
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    comment = payload.comment if payload else None
    decision = await submit_for_review(project, current_user, comment, db)
    return format_decision_response(decision)


@router.post("/tech-approve", response_model=WorkflowDecisionResponse)
async def approve_technical_review(
    project_id: str,
    payload: WorkflowActionRequest = None,
    bypass_sod: bool = Query(False, description="Dérogation SoD (Séparation des devoirs)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_technical_lead)
):
    """
    Step 2: Technical Lead approves technical review (in_review -> validated).
    Enforces Separation of Duties (SoD): cannot be the submitter.
    """
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    # If non-admin user tries bypass_sod, forbid it
    if bypass_sod and current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un administrateur peut autoriser une dérogation de séparation des responsabilités."
        )

    comment = payload.comment if payload else None
    decision = await technical_approve(project, current_user, comment, db, bypass_sod=bypass_sod)
    return format_decision_response(decision)


@router.post("/tech-reject", response_model=WorkflowDecisionResponse)
async def reject_technical_review(
    project_id: str,
    payload: WorkflowRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_technical_lead)
):
    """
    Technical Lead rejects dossier with mandatory explanation, returning to engineer (in_review -> draft).
    """
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    decision = await technical_reject(project, current_user, payload.comment, db)
    return format_decision_response(decision)


@router.post("/final-approve", response_model=WorkflowDecisionResponse)
async def approve_final_validation(
    project_id: str,
    payload: WorkflowActionRequest = None,
    bypass_sod: bool = Query(False, description="Dérogation SoD (Séparation des devoirs)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_final_validator)
):
    """
    Step 3: Final Validator grants final approval, locking and sealing the project (validated -> closed).
    Enforces Separation of Duties (SoD): cannot be the technical approver.
    """
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    if bypass_sod and current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un administrateur peut autoriser une dérogation de séparation des responsabilités."
        )

    comment = payload.comment if payload else None
    decision = await final_approve(project, current_user, comment, db, bypass_sod=bypass_sod)
    return format_decision_response(decision)


@router.post("/final-reject", response_model=WorkflowDecisionResponse)
async def reject_final_validation(
    project_id: str,
    payload: WorkflowRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_final_validator)
):
    """
    Final Validator rejects dossier with mandatory explanation, returning to engineer (validated -> draft).
    """
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    decision = await final_reject(project, current_user, payload.comment, db)
    return format_decision_response(decision)


@router.post("/branch-version", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_branched_version(
    project_id: str,
    payload: BranchVersionRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Branch a new editable draft version from an existing (or locked) project.
    Performs deep copy of sites, racks, equipments, interfaces, network segments, and configs.
    The parent project remains locked and untouched.
    """
    proj_res = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet source non trouvé")

    version_bump = payload.version_bump if payload else "minor"
    new_version = payload.new_version if payload else None
    comment = payload.comment if payload else None

    new_project = await branch_new_version(
        original=project,
        user=current_user,
        version_bump=version_bump,
        new_version=new_version,
        comment=comment,
        db=db
    )
    return new_project
