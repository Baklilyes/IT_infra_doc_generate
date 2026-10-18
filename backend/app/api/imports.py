"""API Router for Data Ingestion, Tabular Imports, and CLI Config Parsers."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.core.database import get_db
from app.api.deps import get_current_user, require_engineer
from app.models.user import User
from app.models.project import Project, Site, Location
from app.models.equipment import Equipment, EquipmentCategory, InstallationStatus, VerificationStatus
from app.models.network import Interface, InterfaceType, InterfaceMode, NetworkSegment, ConfigurationParam
from app.models.import_job import ImportJob
from app.schemas.import_job import (
    ImportUploadResponse, ImportPreviewRequest, ImportPreviewItem,
    ImportPreviewResponse, ImportApplyRequest, ImportApplyResponse, ImportJobResponse
)
from app.core.parsers.tabular import (
    parse_csv_content, parse_excel_bytes, suggest_mapping,
    transform_equipment_row, transform_segment_row
)
from app.core.parsers.cisco import parse_cisco_ios
from app.core.parsers.fortinet import parse_fortinet_cli
from app.core.workflow_engine import verify_project_not_locked, invalidate_approvals_if_in_review

router = APIRouter(prefix="/imports", tags=["Imports & Ingestion"])


@router.post("/upload", response_model=ImportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_import_file(
    project_id: str = Form(...),
    target_type: str = Form("equipment"),  # 'equipment', 'network_segments', 'cli'
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Step 1: Upload a tabular (CSV, XLSX) or CLI config file.
    Analyzes the file, generates suggested mappings, and creates a pending import job.
    """
    # Verify project exists
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")

    filename = file.filename or "unknown_file"
    file_bytes = await file.read()
    
    # Detect file type
    lower_filename = filename.lower()
    if lower_filename.endswith(".xlsx") or lower_filename.endswith(".xls"):
        file_type = "excel"
    elif lower_filename.endswith(".csv"):
        file_type = "csv"
    elif any(lower_filename.endswith(ext) for ext in [".cfg", ".conf", ".txt", ".ios"]):
        # Check content to distinguish Cisco from Fortinet
        text_preview = file_bytes[:2048].decode("utf-8", errors="ignore")
        if "fortinet" in text_preview.lower() or "config system" in text_preview:
            file_type = "fortinet_cli"
        else:
            file_type = "cisco_ios"
    elif lower_filename.endswith(".json"):
        file_type = "json"
    else:
        file_type = "csv"

    headers: list[str] = []
    rows: list[dict[str, Any]] = []
    raw_content_str: str | None = None
    suggested_map: dict[str, str] = {}
    detected_target = target_type

    if file_type == "csv":
        try:
            raw_content_str = file_bytes.decode("utf-8-sig", errors="replace")
        except Exception:
            raw_content_str = file_bytes.decode("latin-1", errors="replace")
        headers, rows = parse_csv_content(raw_content_str)
        # Check if headers look like network segments or equipment
        norm_headers = [h.lower() for h in headers]
        if any("vlan" in h for h in norm_headers) and not any("serie" in h or "serial" in h for h in norm_headers):
            detected_target = "network_segments"
        suggested_map = suggest_mapping(headers, target_type=detected_target)

    elif file_type == "excel":
        headers, rows = parse_excel_bytes(file_bytes)
        norm_headers = [h.lower() for h in headers]
        if any("vlan" in h for h in norm_headers) and not any("serie" in h or "serial" in h for h in norm_headers):
            detected_target = "network_segments"
        suggested_map = suggest_mapping(headers, target_type=detected_target)
        raw_content_str = f"Excel file {filename} with {len(rows)} data rows"

    elif file_type in ["cisco_ios", "fortinet_cli"]:
        raw_content_str = file_bytes.decode("utf-8", errors="replace")
        detected_target = "cli"

    # Create ImportJob record
    import_job = ImportJob(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=current_user.id,
        filename=filename,
        file_type=file_type,
        target_type=detected_target,
        status="pending",
        total_rows=len(rows),
        mappings=suggested_map,
        preview_data={"headers": headers, "rows": rows[:100]} if rows else {},
        raw_content=raw_content_str
    )
    db.add(import_job)
    await db.commit()
    await db.refresh(import_job)

    return ImportUploadResponse(
        job_id=import_job.id,
        filename=filename,
        file_type=file_type,
        headers=headers,
        sample_rows=rows[:5],
        suggested_mapping=suggested_map,
        detected_target=detected_target,
        total_raw_rows=len(rows)
    )


@router.post("/{job_id}/preview", response_model=ImportPreviewResponse)
async def preview_import_job(
    job_id: str,
    payload: ImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Step 2: Generate preview with conflict & validation detection.
    Compares against existing project records (name, serial, IP).
    """
    res = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Tâche d'import non trouvée")

    target_type = payload.target_type or job.target_type
    mapping = payload.mappings or (job.mappings if isinstance(job.mappings, dict) else {})
    
    items: list[ImportPreviewItem] = []
    valid_count = 0
    conflict_count = 0
    error_count = 0

    if job.file_type in ["csv", "excel"]:
        raw_rows = []
        if job.preview_data and "rows" in job.preview_data:
            raw_rows = job.preview_data["rows"]
        elif job.file_type == "csv" and job.raw_content:
            _, raw_rows = parse_csv_content(job.raw_content)

        # Pre-fetch existing project equipment or segments for fast conflict lookup
        if target_type == "equipment":
            eq_res = await db.execute(select(Equipment).where(Equipment.project_id == job.project_id))
            existing_equipment = eq_res.scalars().all()
            existing_names = {e.name.lower(): e for e in existing_equipment}
            existing_serials = {e.serial_number.lower(): e for e in existing_equipment if e.serial_number}
            existing_ips = {e.management_ip: e for e in existing_equipment if e.management_ip}

            for idx, r in enumerate(raw_rows):
                transformed, row_errors = transform_equipment_row(r, mapping)
                conflicts = []

                if not row_errors:
                    name_key = transformed["name"].lower()
                    if name_key in existing_names:
                        conflicts.append(f"Un équipement nommé '{transformed['name']}' existe déjà dans ce projet.")
                    
                    sn = transformed.get("serial_number")
                    if sn and sn.lower() in existing_serials:
                        conflicts.append(f"Numéro de série en double : '{sn}'.")

                    ip = transformed.get("management_ip")
                    if ip and ip in existing_ips:
                        conflicts.append(f"Adresse IP '{ip}' déjà attribuée à '{existing_ips[ip].name}'.")

                status_str = "error" if row_errors else ("conflict" if conflicts else "valid")
                if status_str == "valid":
                    valid_count += 1
                elif status_str == "conflict":
                    conflict_count += 1
                else:
                    error_count += 1

                items.append(ImportPreviewItem(
                    row_number=idx + 1,
                    status=status_str,
                    data=transformed,
                    conflicts=conflicts,
                    errors=row_errors
                ))

        else:  # network_segments
            seg_res = await db.execute(select(NetworkSegment).where(NetworkSegment.project_id == job.project_id))
            existing_segs = seg_res.scalars().all()
            existing_vlans = {s.vlan_id: s for s in existing_segs}

            for idx, r in enumerate(raw_rows):
                transformed, row_errors = transform_segment_row(r, mapping)
                conflicts = []

                if not row_errors:
                    vlan_id = transformed.get("vlan_id")
                    if vlan_id and vlan_id in existing_vlans:
                        conflicts.append(f"Le VLAN {vlan_id} ('{existing_vlans[vlan_id].name}') existe déjà dans ce projet.")

                status_str = "error" if row_errors else ("conflict" if conflicts else "valid")
                if status_str == "valid":
                    valid_count += 1
                elif status_str == "conflict":
                    conflict_count += 1
                else:
                    error_count += 1

                items.append(ImportPreviewItem(
                    row_number=idx + 1,
                    status=status_str,
                    data=transformed,
                    conflicts=conflicts,
                    errors=row_errors
                ))

    elif job.file_type in ["cisco_ios", "fortinet_cli"]:
        # Parse CLI configuration
        parsed_cli = (
            parse_cisco_ios(job.raw_content or "")
            if job.file_type == "cisco_ios"
            else parse_fortinet_cli(job.raw_content or "")
        )
        eq_data = parsed_cli["equipment"]

        # Conflict check
        eq_res = await db.execute(
            select(Equipment).where(
                and_(
                    Equipment.project_id == job.project_id,
                    Equipment.name.ilike(eq_data["name"])
                )
            )
        )
        existing = eq_res.scalars().first()
        conflicts = []
        if existing:
            conflicts.append(f"Équipement '{eq_data['name']}' déjà existant dans le projet.")

        status_str = "conflict" if conflicts else "valid"
        if status_str == "valid":
            valid_count += 1
        else:
            conflict_count += 1

        items.append(ImportPreviewItem(
            row_number=1,
            status=status_str,
            data={
                **eq_data,
                "parsed_interfaces_count": len(parsed_cli["interfaces"]),
                "parsed_segments_count": len(parsed_cli.get("network_segments", [])),
                "parsed_configs_count": len(parsed_cli["configurations"]),
                "details": parsed_cli
            },
            conflicts=conflicts,
            errors=[]
        ))

    # Save preview state
    job.status = "previewed"
    job.target_type = target_type
    job.mappings = mapping
    job.preview_data = {
        "items": [item.model_dump() for item in items],
        "total_items": len(items),
        "valid_count": valid_count,
        "conflict_count": conflict_count,
        "error_count": error_count
    }
    await db.commit()

    return ImportPreviewResponse(
        job_id=job.id,
        target_type=target_type,
        total_items=len(items),
        valid_count=valid_count,
        conflict_count=conflict_count,
        error_count=error_count,
        items=items
    )


@router.post("/{job_id}/apply", response_model=ImportApplyResponse)
async def apply_import_job(
    job_id: str,
    payload: ImportApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Step 3: Non-destructive import execution.
    Applies validated items to the database according to chosen conflict resolution strategy.
    """
    res = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Tâche d'import non trouvée")

    # Check project lock
    p_res = await db.execute(select(Project).where(Project.id == job.project_id))
    project = p_res.scalars().first()
    if project:
        verify_project_not_locked(project)
        await invalidate_approvals_if_in_review(project, db, user_id=current_user.id)

    if not job.preview_data or "items" not in job.preview_data:
        raise HTTPException(status_code=400, detail="Veuillez d'abord exécuter l'étape de prévisualisation.")

    items_data = job.preview_data["items"]
    resolution = payload.conflict_resolution  # 'skip', 'overwrite', 'create_new'

    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    if job.file_type in ["cisco_ios", "fortinet_cli"]:
        item = items_data[0]
        data = item["data"]
        parsed_cli = data.get("details", {})
        eq_dict = parsed_cli.get("equipment", {})

        # Check existing
        eq_res = await db.execute(
            select(Equipment).where(
                and_(
                    Equipment.project_id == job.project_id,
                    Equipment.name.ilike(eq_dict.get("name", ""))
                )
            )
        )
        existing_eq = eq_res.scalars().first()

        target_eq = None
        if existing_eq:
            if resolution == "skip":
                skipped_count += 1
            elif resolution == "overwrite":
                existing_eq.category = EquipmentCategory(eq_dict.get("category", "generic"))
                existing_eq.manufacturer = eq_dict.get("manufacturer")
                existing_eq.model = eq_dict.get("model")
                existing_eq.role = eq_dict.get("role")
                existing_eq.management_ip = eq_dict.get("management_ip")
                existing_eq.verification_status = VerificationStatus.UNVERIFIED
                target_eq = existing_eq
                updated_count += 1
            elif resolution == "create_new":
                new_eq = Equipment(
                    project_id=job.project_id,
                    name=f"{eq_dict.get('name')}_imported",
                    category=EquipmentCategory(eq_dict.get("category", "generic")),
                    manufacturer=eq_dict.get("manufacturer"),
                    model=eq_dict.get("model"),
                    role=eq_dict.get("role"),
                    management_ip=eq_dict.get("management_ip"),
                    installation_status=InstallationStatus.IN_SERVICE,
                    verification_status=VerificationStatus.UNVERIFIED,
                    data_source=f"{job.file_type}_import"
                )
                db.add(new_eq)
                await db.flush()
                target_eq = new_eq
                created_count += 1
        else:
            new_eq = Equipment(
                project_id=job.project_id,
                name=eq_dict.get("name", "Imported-Device"),
                category=EquipmentCategory(eq_dict.get("category", "generic")),
                manufacturer=eq_dict.get("manufacturer"),
                model=eq_dict.get("model"),
                role=eq_dict.get("role"),
                management_ip=eq_dict.get("management_ip"),
                installation_status=InstallationStatus.IN_SERVICE,
                verification_status=VerificationStatus.UNVERIFIED,
                data_source=f"{job.file_type}_import"
            )
            db.add(new_eq)
            await db.flush()
            target_eq = new_eq
            created_count += 1

        # If target equipment created/updated, create interfaces, segments, and configs
        if target_eq:
            for iface in parsed_cli.get("interfaces", []):
                new_if = Interface(
                    equipment_id=target_eq.id,
                    name=iface["name"],
                    interface_type=InterfaceType(iface.get("interface_type", "physical")),
                    mode=InterfaceMode(iface.get("mode", "unconfigured")),
                    ip_address=iface.get("ip_address"),
                    access_vlan=iface.get("vlan_tag"),
                    allowed_vlans=iface.get("allowed_vlans"),
                    description=iface.get("description"),
                    admin_status="up" if iface.get("is_enabled", True) else "down",
                    verification_status=VerificationStatus.UNVERIFIED
                )
                db.add(new_if)

            for seg in parsed_cli.get("network_segments", []):
                # Only add if segment doesn't exist
                seg_check = await db.execute(
                    select(NetworkSegment).where(
                        and_(
                            NetworkSegment.project_id == job.project_id,
                            NetworkSegment.vlan_id == seg["vlan_id"]
                        )
                    )
                )
                if not seg_check.scalars().first():
                    new_seg = NetworkSegment(
                        project_id=job.project_id,
                        vlan_id=seg["vlan_id"],
                        name=seg["name"],
                        cidr=seg.get("cidr"),
                        gateway=seg.get("gateway")
                    )
                    db.add(new_seg)

            for cfg in parsed_cli.get("configurations", []):
                new_cfg = ConfigurationParam(
                    project_id=job.project_id,
                    equipment_id=target_eq.id,
                    category=cfg["category"],
                    key=cfg["key"],
                    value=cfg["value"],
                    is_secret=cfg.get("is_secret", False)
                )
                db.add(new_cfg)

    elif job.target_type == "equipment":
        # Process tabular equipment items
        for item in items_data:
            if item["status"] == "error":
                error_count += 1
                continue

            data = item["data"]
            name = data.get("name")
            if not name:
                error_count += 1
                continue

            eq_check = await db.execute(
                select(Equipment).where(
                    and_(Equipment.project_id == job.project_id, Equipment.name.ilike(name))
                )
            )
            existing_eq = eq_check.scalars().first()

            if existing_eq:
                if resolution == "skip":
                    skipped_count += 1
                    continue
                elif resolution == "overwrite":
                    existing_eq.category = EquipmentCategory(data.get("category", "generic"))
                    existing_eq.manufacturer = data.get("manufacturer")
                    existing_eq.model = data.get("model")
                    existing_eq.serial_number = data.get("serial_number")
                    existing_eq.management_ip = data.get("management_ip")
                    existing_eq.role = data.get("role")
                    existing_eq.firmware_version = data.get("firmware_version")
                    existing_eq.verification_status = VerificationStatus.UNVERIFIED
                    updated_count += 1
                    continue
                elif resolution == "create_new":
                    name = f"{name}_imported"

            new_eq = Equipment(
                project_id=job.project_id,
                name=name,
                category=EquipmentCategory(data.get("category", "generic")),
                manufacturer=data.get("manufacturer"),
                model=data.get("model"),
                serial_number=data.get("serial_number"),
                management_ip=data.get("management_ip"),
                role=data.get("role"),
                firmware_version=data.get("firmware_version"),
                installation_status=InstallationStatus.PLANNED,
                verification_status=VerificationStatus.UNVERIFIED,
                data_source=f"{job.file_type}_import"
            )
            db.add(new_eq)
            created_count += 1

    else:  # network_segments
        for item in items_data:
            if item["status"] == "error":
                error_count += 1
                continue

            data = item["data"]
            vlan_id = data.get("vlan_id")
            if not vlan_id:
                error_count += 1
                continue

            seg_check = await db.execute(
                select(NetworkSegment).where(
                    and_(NetworkSegment.project_id == job.project_id, NetworkSegment.vlan_id == int(vlan_id))
                )
            )
            existing_seg = seg_check.scalars().first()

            if existing_seg:
                if resolution == "skip":
                    skipped_count += 1
                    continue
                elif resolution == "overwrite":
                    existing_seg.name = data.get("name", existing_seg.name)
                    existing_seg.cidr = data.get("cidr")
                    existing_seg.gateway = data.get("gateway")
                    existing_seg.dhcp_range = data.get("dhcp_range")
                    existing_seg.zone = data.get("zone")
                    existing_seg.description = data.get("description")
                    updated_count += 1
                    continue

            new_seg = NetworkSegment(
                project_id=job.project_id,
                vlan_id=int(vlan_id),
                name=data.get("name", f"VLAN_{vlan_id}"),
                cidr=data.get("cidr"),
                gateway=data.get("gateway"),
                dhcp_range=data.get("dhcp_range"),
                zone=data.get("zone"),
                description=data.get("description")
            )
            db.add(new_seg)
            created_count += 1

    job.status = "applied"
    job.applied_at = datetime.now(timezone.utc)
    job.created_count = created_count
    job.updated_count = updated_count
    job.skipped_count = skipped_count
    job.error_count = error_count

    await db.commit()

    return ImportApplyResponse(
        job_id=job.id,
        status="applied",
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        error_count=error_count,
        message=f"Import appliqué avec succès : {created_count} créés, {updated_count} mis à jour, {skipped_count} ignorés, {error_count} erreurs."
    )


@router.get("", response_model=list[ImportJobResponse])
async def list_import_jobs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List historical import jobs for a project."""
    res = await db.execute(
        select(ImportJob)
        .where(ImportJob.project_id == project_id)
        .order_by(ImportJob.created_at.desc())
    )
    jobs = res.scalars().all()
    return jobs


@router.get("/{job_id}", response_model=dict[str, Any])
async def get_import_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve full details of an import job, including preview data and counts."""
    res = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Tâche d'import non trouvée")

    return {
        "id": job.id,
        "project_id": job.project_id,
        "filename": job.filename,
        "file_type": job.file_type,
        "target_type": job.target_type,
        "status": job.status,
        "total_rows": job.total_rows,
        "created_count": job.created_count,
        "updated_count": job.updated_count,
        "skipped_count": job.skipped_count,
        "error_count": job.error_count,
        "mappings": job.mappings,
        "preview_data": job.preview_data,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "applied_at": job.applied_at.isoformat() if job.applied_at else None
    }
