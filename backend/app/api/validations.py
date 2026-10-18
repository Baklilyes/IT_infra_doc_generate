"""API Router for Consistency Checks, Anomaly Detection, and Override Waivers."""
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, require_engineer
from app.models.user import User
from app.models.project import Project
from app.models.validation import ConsistencyReport, ConsistencyOverride
from app.schemas.validation import (
    ConsistencyReportResponse, FindingResponse,
    ConsistencyOverrideCreate, ConsistencyOverrideResponse,
    CanPublishResponse
)
from app.core.consistency_engine import run_consistency_checks
from app.core.workflow_engine import verify_project_not_locked

router = APIRouter(prefix="/projects/{project_id}/validations", tags=["Consistency & Validation Engine"])


@router.post("/run", response_model=ConsistencyReportResponse, status_code=status.HTTP_201_CREATED)
async def execute_validation_checks(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Execute all deterministic consistency rules on the project.
    Detects IP duplicates, unrouted VLANs, CIDR overlaps, topology orphans,
    and cleartext secrets. Matches findings against active overrides.
    """
    p_res = await db.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    findings, stats = await run_consistency_checks(project_id, db)

    # Determine status
    if stats["blocking_count"] > 0:
        overall_status = "failed"
    elif stats["warning_count"] > 0:
        overall_status = "warnings_only"
    else:
        overall_status = "passed"

    # Persist report
    report = ConsistencyReport(
        id=str(uuid.uuid4()),
        project_id=project_id,
        executed_by_id=current_user.id,
        status=overall_status,
        blocking_count=stats["blocking_count"],
        warning_count=stats["warning_count"],
        info_count=stats["info_count"],
        resolved_count=stats["resolved_count"],
        findings=[f.to_dict() for f in findings],
        summary=f"{stats['total_findings']} anomalies détectées : {stats['blocking_count']} bloquantes, {stats['warning_count']} avertissements, {stats['info_count']} infos, {stats['resolved_count']} dérogations."
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return ConsistencyReportResponse(
        id=report.id,
        project_id=project_id,
        status=overall_status,
        blocking_count=stats["blocking_count"],
        warning_count=stats["warning_count"],
        info_count=stats["info_count"],
        resolved_count=stats["resolved_count"],
        total_findings=stats["total_findings"],
        findings=[FindingResponse(**f.to_dict()) for f in findings],
        created_at=report.created_at,
        executed_by_name=current_user.full_name or current_user.username
    )


@router.get("/latest", response_model=ConsistencyReportResponse)
async def get_latest_validation_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest saved consistency report or execute an on-demand check if none exists."""
    p_res = await db.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    rep_res = await db.execute(
        select(ConsistencyReport)
        .options(selectinload(ConsistencyReport.executed_by))
        .where(ConsistencyReport.project_id == project_id)
        .order_by(desc(ConsistencyReport.created_at))
    )
    latest_report = rep_res.scalars().first()

    if not latest_report:
        # Run on demand
        findings, stats = await run_consistency_checks(project_id, db)
        overall_status = "failed" if stats["blocking_count"] > 0 else ("warnings_only" if stats["warning_count"] > 0 else "passed")
        latest_report = ConsistencyReport(
            id=str(uuid.uuid4()),
            project_id=project_id,
            executed_by_id=current_user.id,
            status=overall_status,
            blocking_count=stats["blocking_count"],
            warning_count=stats["warning_count"],
            info_count=stats["info_count"],
            resolved_count=stats["resolved_count"],
            findings=[f.to_dict() for f in findings],
            summary=f"Analyse initiale : {stats['blocking_count']} bloquantes, {stats['warning_count']} avertissements."
        )
        db.add(latest_report)
        await db.commit()
        await db.refresh(latest_report)

    findings_list = [FindingResponse(**f) for f in (latest_report.findings or [])]

    return ConsistencyReportResponse(
        id=latest_report.id,
        project_id=project_id,
        status=latest_report.status,
        blocking_count=latest_report.blocking_count,
        warning_count=latest_report.warning_count,
        info_count=latest_report.info_count,
        resolved_count=latest_report.resolved_count,
        total_findings=len(findings_list),
        findings=findings_list,
        created_at=latest_report.created_at,
        executed_by_name=latest_report.executed_by.full_name if latest_report.executed_by else None
    )


@router.post("/override", response_model=ConsistencyOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_consistency_override(
    project_id: str,
    payload: ConsistencyOverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Submit a formal justification / waiver (dérogation) for an anomaly.
    Section 8.3 & 6.8: Tout override d'un avertissement ou anomalie
    doit comporter un motif horodaté et nominatif.
    """
    p_res = await db.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    verify_project_not_locked(project)

    if not payload.justification or len(payload.justification.strip()) < 10:
        raise HTTPException(status_code=422, detail="Une justification détaillée d'au moins 10 caractères est obligatoire pour accorder une dérogation.")

    # Check if an override already exists for this rule and target
    existing_res = await db.execute(
        select(ConsistencyOverride).where(
            and_(
                ConsistencyOverride.project_id == project_id,
                ConsistencyOverride.rule_code == payload.rule_code,
                ConsistencyOverride.target_id == payload.target_id,
                ConsistencyOverride.is_active == True
            )
        )
    )
    existing = existing_res.scalars().first()
    if existing:
        existing.justification = payload.justification
        existing.overridden_by_id = current_user.id
        existing.severity = payload.severity
        await db.commit()
        await db.refresh(existing)
        return ConsistencyOverrideResponse(
            id=existing.id,
            project_id=project_id,
            rule_code=existing.rule_code,
            target_id=existing.target_id,
            target_type=existing.target_type,
            severity=existing.severity,
            justification=existing.justification,
            is_active=existing.is_active,
            created_at=existing.created_at,
            overridden_by_name=current_user.full_name or current_user.username
        )

    new_override = ConsistencyOverride(
        id=str(uuid.uuid4()),
        project_id=project_id,
        overridden_by_id=current_user.id,
        rule_code=payload.rule_code,
        target_id=payload.target_id,
        target_type=payload.target_type,
        severity=payload.severity,
        justification=payload.justification,
        is_active=True
    )
    db.add(new_override)
    await db.commit()
    await db.refresh(new_override)

    return ConsistencyOverrideResponse(
        id=new_override.id,
        project_id=project_id,
        rule_code=new_override.rule_code,
        target_id=new_override.target_id,
        target_type=new_override.target_type,
        severity=new_override.severity,
        justification=new_override.justification,
        is_active=new_override.is_active,
        created_at=new_override.created_at,
        overridden_by_name=current_user.full_name or current_user.username
    )


@router.delete("/override/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consistency_override(
    project_id: str,
    override_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """Remove or revoke an active waiver."""
    ovr_res = await db.execute(
        select(ConsistencyOverride).where(
            and_(
                ConsistencyOverride.id == override_id,
                ConsistencyOverride.project_id == project_id
            )
        )
    )
    override = ovr_res.scalars().first()
    if not override:
        raise HTTPException(status_code=404, detail="Dérogation non trouvée")

    await db.delete(override)
    await db.commit()
    return None


@router.get("/can-publish", response_model=CanPublishResponse)
async def check_can_publish(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Technical pre-condition check for document publication workflow (Lot 8 gatekeeper).
    A document cannot be submitted for final validation or published if active blocking
    errors remain un-justified.
    """
    findings, stats = await run_consistency_checks(project_id, db)
    can_publish = stats["blocking_count"] == 0

    if can_publish:
        msg = "Projet prêt pour publication : aucune anomalie bloquante non dérogée."
        status_label = "ready"
    else:
        msg = f"Publication bloquée : {stats['blocking_count']} anomalie(s) bloquante(s) nécessitent correction ou dérogation formelle."
        status_label = "blocked"

    return CanPublishResponse(
        project_id=project_id,
        can_publish=can_publish,
        status=status_label,
        blocking_count=stats["blocking_count"],
        unjustified_warnings=stats["warning_count"],
        message=msg
    )
