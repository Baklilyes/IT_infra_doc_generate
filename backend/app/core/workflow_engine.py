"""Workflow engine implementing project lifecycle, transitions, SoD, locking, and version branching."""
import uuid
import re
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models.project import Project, ProjectStatus, Site, Location
from app.models.equipment import Equipment
from app.models.network import Interface, NetworkSegment, ConfigurationParam
from app.models.workflow import WorkflowDecision, WorkflowAction
from app.models.user import User, UserRole
from app.core.consistency_engine import run_consistency_checks


def verify_project_not_locked(project: Project) -> None:
    """
    Ensure the project is not in CLOSED (locked) status.
    Raises HTTP 423 Locked if modification is attempted on a sealed project.
    """
    if project.status == ProjectStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                f"Le projet '{project.reference}' (v{project.version}) est verrouillé et scellé. "
                "Aucune modification n'est permise. "
                "Veuillez créer une nouvelle version de travail (branch-version) pour apporter des modifications."
            )
        )


async def invalidate_approvals_if_in_review(
    project: Project,
    db: AsyncSession,
    user_id: Optional[str] = None,
    reason: str = "Modifications techniques apportées après soumission"
) -> bool:
    """
    MASTER_PROMPT Section 6.14:
    'toute modification après soumission invalide les approbations précédentes de cette version'
    If the project is IN_REVIEW or VALIDATED, resets it back to DRAFT and logs an audit decision.
    Returns True if a reset occurred, False otherwise.
    """
    if project.status in (ProjectStatus.IN_REVIEW, ProjectStatus.VALIDATED):
        old_status = project.status.value
        project.status = ProjectStatus.DRAFT
        
        reset_decision = WorkflowDecision(
            id=str(uuid.uuid4()),
            project_id=project.id,
            action=WorkflowAction.RESET_DRAFT.value,
            from_status=old_status,
            to_status=ProjectStatus.DRAFT.value,
            version=project.version,
            comment=f"{reason} - réinitialisation automatique en statut Brouillon",
            user_id=user_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(reset_decision)
        return True
    return False


async def get_workflow_status(
    project_id: str,
    db: AsyncSession,
    current_user: Optional[User] = None
) -> Dict[str, Any]:
    """Retrieve current workflow state, blockers, allowed actions, and last decision."""
    project_stmt = select(Project).where(Project.id == project_id)
    project_res = await db.execute(project_stmt)
    project = project_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    # Run consistency checks to check can_publish
    findings, stats = await run_consistency_checks(project_id, db)
    can_publish = stats.get("blocking_count", 0) == 0

    # Get last decision
    dec_stmt = select(WorkflowDecision).where(
        WorkflowDecision.project_id == project_id
    ).order_by(desc(WorkflowDecision.created_at)).limit(1)
    dec_res = await db.execute(dec_stmt)
    last_decision = dec_res.scalars().first()

    # Determine allowed actions based on current status and user role
    allowed_actions: List[str] = []
    is_locked = project.status == ProjectStatus.CLOSED
    user_role = current_user.role if current_user else None

    if not is_locked:
        if project.status in (ProjectStatus.DRAFT, ProjectStatus.IN_PREPARATION):
            if user_role in (UserRole.ADMINISTRATOR, UserRole.ENGINEER):
                allowed_actions.append("submit")
        elif project.status == ProjectStatus.IN_REVIEW:
            if user_role in (UserRole.ADMINISTRATOR, UserRole.TECHNICAL_LEAD):
                allowed_actions.append("tech_approve")
                allowed_actions.append("tech_reject")
        elif project.status == ProjectStatus.VALIDATED:
            if user_role in (UserRole.ADMINISTRATOR, UserRole.FINAL_VALIDATOR):
                allowed_actions.append("final_approve")
                allowed_actions.append("final_reject")
    else:
        # Locked project can be branched into a new version
        if user_role in (UserRole.ADMINISTRATOR, UserRole.ENGINEER):
            allowed_actions.append("branch_version")

    return {
        "project_id": project.id,
        "reference": project.reference,
        "name": project.name,
        "version": project.version,
        "status": project.status,
        "is_locked": is_locked,
        "can_publish": can_publish,
        "blocking_issues_count": stats.get("blocking_count", 0),
        "allowed_actions": allowed_actions,
        "last_decision": last_decision
    }


async def submit_for_review(
    project: Project,
    user: User,
    comment: Optional[str],
    db: AsyncSession
) -> WorkflowDecision:
    """Submit project for technical review (draft -> in_review)."""
    verify_project_not_locked(project)

    if project.status not in (ProjectStatus.DRAFT, ProjectStatus.IN_PREPARATION):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet ne peut pas être soumis depuis le statut '{project.status.value}'. Statut attendu: 'draft'."
        )

    # Gatekeeper check: consistency blocking errors
    findings, stats = await run_consistency_checks(project.id, db)
    blocking_count = stats.get("blocking_count", 0)
    if blocking_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Impossible de soumettre le projet : {blocking_count} anomalie(s) bloquante(s) non dérogée(s) détectée(s). "
                "Résolvez ou accordez une dérogation formelle à toutes les erreurs bloquantes avant soumission."
            )
        )

    old_status = project.status.value
    project.status = ProjectStatus.IN_REVIEW

    decision = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=project.id,
        action=WorkflowAction.SUBMIT.value,
        from_status=old_status,
        to_status=ProjectStatus.IN_REVIEW.value,
        version=project.version,
        comment=comment or "Soumission pour revue technique",
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    await db.refresh(project)
    return decision


async def technical_approve(
    project: Project,
    user: User,
    comment: Optional[str],
    db: AsyncSession,
    bypass_sod: bool = False
) -> WorkflowDecision:
    """Approve technical stage (in_review -> validated)."""
    verify_project_not_locked(project)

    if project.status != ProjectStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet ne peut pas recevoir d'approbation technique depuis le statut '{project.status.value}'. Statut attendu: 'in_review'."
        )

    # Separation of Duties (SoD) check: cannot be the same user who submitted current version
    if not bypass_sod:
        submit_stmt = select(WorkflowDecision).where(
            and_(
                WorkflowDecision.project_id == project.id,
                WorkflowDecision.action == WorkflowAction.SUBMIT.value,
                WorkflowDecision.version == project.version
            )
        ).order_by(desc(WorkflowDecision.created_at)).limit(1)
        sub_res = await db.execute(submit_stmt)
        last_submit = sub_res.scalars().first()

        if last_submit and last_submit.user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Principe de séparation des responsabilités (SoD) : L'approbateur technique "
                    "ne peut pas être le même utilisateur que celui ayant soumis ce dossier pour cette version."
                )
            )

    old_status = project.status.value
    project.status = ProjectStatus.VALIDATED

    decision = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=project.id,
        action=WorkflowAction.TECH_APPROVE.value,
        from_status=old_status,
        to_status=ProjectStatus.VALIDATED.value,
        version=project.version,
        comment=comment or "Validation technique approuvée",
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    await db.refresh(project)
    return decision


async def technical_reject(
    project: Project,
    user: User,
    comment: str,
    db: AsyncSession
) -> WorkflowDecision:
    """Reject technical review with mandatory motive, returning dossier to engineer (in_review -> draft)."""
    verify_project_not_locked(project)

    if project.status != ProjectStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet ne peut pas être renvoyé pour correction depuis le statut '{project.status.value}'."
        )

    if not comment or len(comment.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le motif de renvoi pour correction est obligatoire (minimum 5 caractères)."
        )

    old_status = project.status.value
    project.status = ProjectStatus.DRAFT

    decision = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=project.id,
        action=WorkflowAction.TECH_REJECT.value,
        from_status=old_status,
        to_status=ProjectStatus.DRAFT.value,
        version=project.version,
        comment=comment.strip(),
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    await db.refresh(project)
    return decision


async def final_approve(
    project: Project,
    user: User,
    comment: Optional[str],
    db: AsyncSession,
    bypass_sod: bool = False
) -> WorkflowDecision:
    """Final approval, locking and sealing the project (validated -> closed)."""
    verify_project_not_locked(project)

    if project.status != ProjectStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet ne peut pas recevoir de validation finale depuis le statut '{project.status.value}'. Statut attendu: 'validated'."
        )

    # Separation of Duties (SoD) check: cannot be the same user who gave technical approval
    if not bypass_sod:
        tech_stmt = select(WorkflowDecision).where(
            and_(
                WorkflowDecision.project_id == project.id,
                WorkflowDecision.action == WorkflowAction.TECH_APPROVE.value,
                WorkflowDecision.version == project.version
            )
        ).order_by(desc(WorkflowDecision.created_at)).limit(1)
        tech_res = await db.execute(tech_stmt)
        last_tech = tech_res.scalars().first()

        if last_tech and last_tech.user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Principe de séparation des responsabilités (SoD) : Le validateur final "
                    "ne peut pas être le même utilisateur ayant réalisé la revue technique pour cette version."
                )
            )

    old_status = project.status.value
    project.status = ProjectStatus.CLOSED

    decision = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=project.id,
        action=WorkflowAction.FINAL_APPROVE.value,
        from_status=old_status,
        to_status=ProjectStatus.CLOSED.value,
        version=project.version,
        comment=comment or "Validation finale accordée. Dossier scellé et verrouillé.",
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    await db.refresh(project)
    return decision


async def final_reject(
    project: Project,
    user: User,
    comment: str,
    db: AsyncSession
) -> WorkflowDecision:
    """Final validator rejects dossier with mandatory motive, returning to engineer (validated -> draft)."""
    verify_project_not_locked(project)

    if project.status != ProjectStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet ne peut pas être renvoyé pour correction depuis le statut '{project.status.value}'."
        )

    if not comment or len(comment.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le motif de renvoi pour correction est obligatoire (minimum 5 caractères)."
        )

    old_status = project.status.value
    project.status = ProjectStatus.DRAFT

    decision = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=project.id,
        action=WorkflowAction.FINAL_REJECT.value,
        from_status=old_status,
        to_status=ProjectStatus.DRAFT.value,
        version=project.version,
        comment=comment.strip(),
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    await db.refresh(project)
    return decision


def compute_next_version(current_ver: str, bump_type: str = "minor") -> str:
    """Calculate next version string based on current version and bump type."""
    if not current_ver:
        return "1.0"
    
    parts = current_ver.split(".")
    try:
        major = int(parts[0])
    except (ValueError, IndexError):
        major = 1

    try:
        minor = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        minor = 0

    if bump_type == "major":
        return f"{major + 1}.0"
    else:
        return f"{major}.{minor + 1}"


async def branch_new_version(
    original: Project,
    user: User,
    version_bump: str = "minor",
    new_version: Optional[str] = None,
    comment: Optional[str] = None,
    db: AsyncSession = None
) -> Project:
    """
    Create a new draft version cloned deeply from an existing project.
    Parent project remains untouched and locked.
    """
    target_version = new_version.strip() if new_version and new_version.strip() else compute_next_version(original.version, version_bump)

    # Generate new unique reference: replace old -vX.Y suffix or append new one
    base_ref = re.sub(r"-v\d+(\.\d+)?$", "", original.reference)
    candidate_ref = f"{base_ref}-v{target_version}"

    # Check reference collision
    ref_check = await db.execute(select(Project).where(Project.reference == candidate_ref))
    if ref_check.scalars().first():
        candidate_ref = f"{candidate_ref}-{uuid.uuid4().hex[:4]}"

    new_project = Project(
        id=str(uuid.uuid4()),
        reference=candidate_ref,
        name=original.name,
        client_name=original.client_name,
        description=original.description,
        scope=original.scope,
        lead_name=original.lead_name,
        contributors=original.contributors,
        status=ProjectStatus.DRAFT,
        version=target_version,
        parent_project_id=original.id,
        document_language=original.document_language,
        target_date=original.target_date,
        is_archived=False,
        created_by_id=user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_project)
    await db.flush()

    # Deep copy Sites & Locations
    site_map: Dict[str, str] = {}
    loc_map: Dict[str, str] = {}

    sites_res = await db.execute(select(Site).where(Site.project_id == original.id))
    original_sites = sites_res.scalars().all()

    for s in original_sites:
        new_site_id = str(uuid.uuid4())
        site_map[s.id] = new_site_id
        new_site = Site(
            id=new_site_id,
            project_id=new_project.id,
            name=s.name,
            code=s.code,
            address=s.address,
            city=s.city,
            country=s.country,
            notes=s.notes,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_site)

        # Clone locations for this site
        locs_res = await db.execute(select(Location).where(Location.site_id == s.id))
        for loc in locs_res.scalars().all():
            new_loc_id = str(uuid.uuid4())
            loc_map[loc.id] = new_loc_id
            new_loc = Location(
                id=new_loc_id,
                site_id=new_site_id,
                name=loc.name,
                room=loc.room,
                rack=loc.rack,
                notes=loc.notes,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(new_loc)

    await db.flush()

    # Deep copy Network Segments (VLANs)
    seg_map: Dict[str, str] = {}
    segs_res = await db.execute(select(NetworkSegment).where(NetworkSegment.project_id == original.id))
    for seg in segs_res.scalars().all():
        new_seg_id = str(uuid.uuid4())
        seg_map[seg.id] = new_seg_id
        new_seg = NetworkSegment(
            id=new_seg_id,
            project_id=new_project.id,
            site_id=site_map.get(seg.site_id),
            vlan_id=seg.vlan_id,
            name=seg.name,
            cidr=seg.cidr,
            gateway=seg.gateway,
            dhcp_range=seg.dhcp_range,
            dns_servers=seg.dns_servers,
            ntp_servers=seg.ntp_servers,
            zone=seg.zone,
            description=seg.description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_seg)

    await db.flush()

    # Deep copy Equipment & Interfaces
    equip_map: Dict[str, str] = {}
    iface_map: Dict[str, str] = {}

    equips_res = await db.execute(select(Equipment).where(Equipment.project_id == original.id))
    for eq in equips_res.scalars().all():
        new_eq_id = str(uuid.uuid4())
        equip_map[eq.id] = new_eq_id
        new_eq = Equipment(
            id=new_eq_id,
            project_id=new_project.id,
            site_id=site_map.get(eq.site_id),
            location_id=loc_map.get(eq.location_id),
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
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_eq)

        # Clone interfaces
        ifaces_res = await db.execute(select(Interface).where(Interface.equipment_id == eq.id))
        for iface in ifaces_res.scalars().all():
            new_iface_id = str(uuid.uuid4())
            iface_map[iface.id] = new_iface_id
            new_iface = Interface(
                id=new_iface_id,
                equipment_id=new_eq_id,
                name=iface.name,
                interface_type=iface.interface_type,
                mac_address=iface.mac_address,
                ip_address=iface.ip_address,
                subnet_mask=iface.subnet_mask,
                mode=iface.mode,
                access_vlan=iface.access_vlan,
                allowed_vlans=iface.allowed_vlans,
                speed_duplex=iface.speed_duplex,
                admin_status=iface.admin_status,
                operational_status=iface.operational_status,
                description=iface.description,
                connected_equipment_id=equip_map.get(iface.connected_equipment_id),
                connected_interface_name=iface.connected_interface_name,
                link_type=iface.link_type,
                aggregation_group=iface.aggregation_group,
                verification_status=iface.verification_status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(new_iface)

        # Clone configuration parameters
        cfg_res = await db.execute(select(ConfigurationParam).where(ConfigurationParam.equipment_id == eq.id))
        for cfg in cfg_res.scalars().all():
            new_cfg = ConfigurationParam(
                id=str(uuid.uuid4()),
                project_id=new_project.id,
                equipment_id=new_eq_id,
                category=cfg.category,
                key=cfg.key,
                value=cfg.value,
                is_secret=cfg.is_secret,
                description=cfg.description,
                data_source=cfg.data_source,
                verification_status=cfg.verification_status,
                created_at=datetime.now(timezone.utc)
            )
            db.add(new_cfg)

    await db.flush()

    # Log workflow decisions
    branch_comment = comment or f"Création de la version de travail {target_version} clonée depuis {original.reference} v{original.version} (scellée)"
    new_dec = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=new_project.id,
        action=WorkflowAction.BRANCH_VERSION.value,
        from_status=original.status.value,
        to_status=ProjectStatus.DRAFT.value,
        version=target_version,
        comment=branch_comment,
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_dec)

    parent_dec = WorkflowDecision(
        id=str(uuid.uuid4()),
        project_id=original.id,
        action=WorkflowAction.BRANCH_VERSION.value,
        from_status=original.status.value,
        to_status=original.status.value,
        version=original.version,
        comment=f"Création de la version dérivée {target_version} ({new_project.reference})",
        user_id=user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(parent_dec)

    await db.commit()
    await db.refresh(new_project)
    return new_project
