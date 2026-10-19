"""API Router for Document Generation (HLD, LLD, Annexes, Commissioning) in DOCX & PDF."""
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, require_engineer
from app.models.user import User
from app.models.project import Project
from app.models.equipment import Equipment
from app.models.network import NetworkSegment, ConfigurationParam
from app.models.document import Document
from app.schemas.document import DocumentGenerateRequest, DocumentResponse, DocumentStatusResponse
from app.core.ai.client import generate_narrative_section, check_ollama_status
from app.core.documents.docx_generator import build_docx_document
from app.core.documents.pdf_generator import build_pdf_document

router = APIRouter(tags=["Document Generation & AI Copilot"])

DOCS_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated_docs")


@router.get("/documents/ai-status", response_model=DocumentStatusResponse)
async def get_ai_and_doc_status(current_user: User = Depends(get_current_user)):
    """Check availability of local Ollama AI model and document generation engine."""
    ai_status = await check_ollama_status()
    return DocumentStatusResponse(
        ai_status=ai_status,
        total_generated=0,
        allowed_types=["hld", "lld", "config_annexes", "commissioning"]
    )


@router.post("/projects/{project_id}/documents/generate", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def generate_project_document(
    project_id: str,
    payload: DocumentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """
    Generate an official HLD, LLD, Configuration Annexes or Commissioning deliverable
    in Microsoft Word (.docx) or PDF (.pdf) format with optional local AI enrichment.
    """
    # 1. Fetch project with all relationships
    p_res = await db.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    doc_type = payload.document_type.lower()
    if doc_type not in ["hld", "lld", "config_annexes", "commissioning"]:
        raise HTTPException(status_code=400, detail="Type de document invalide. Choix : hld, lld, config_annexes, commissioning")

    file_format = payload.file_format.lower()
    if file_format not in ["docx", "pdf"]:
        raise HTTPException(status_code=400, detail="Format invalide. Choix : docx, pdf")

    # Fetch equipment
    eq_res = await db.execute(
        select(Equipment)
        .options(selectinload(Equipment.site), selectinload(Equipment.location), selectinload(Equipment.interfaces))
        .where(Equipment.project_id == project_id)
        .order_by(Equipment.name)
    )
    equipment_list = eq_res.scalars().all()

    # Fetch segments
    seg_res = await db.execute(
        select(NetworkSegment)
        .where(NetworkSegment.project_id == project_id)
        .order_by(NetworkSegment.vlan_id)
    )
    segments = seg_res.scalars().all()

    # Fetch configs
    cfg_res = await db.execute(
        select(ConfigurationParam)
        .where(ConfigurationParam.project_id == project_id)
        .order_by(ConfigurationParam.category, ConfigurationParam.key)
    )
    configs = cfg_res.scalars().all()

    # 2. Local AI Narrative Generation / Fallback
    ai_section_key = "hld_summary" if doc_type == "hld" else ("lld_routing" if doc_type == "lld" else "commissioning")
    ai_context = {
        "reference": project.reference,
        "name": project.name,
        "client_name": project.client_name,
        "scope": project.scope or "",
        "description": project.description or "",
        "equipment_count": len(equipment_list),
        "segments_count": len(segments),
        "segments_summary": ", ".join([f"VLAN {s.vlan_id} ({s.cidr})" for s in segments[:5]]),
        "routing_devices": ", ".join([e.name for e in equipment_list if e.category.value in ["router", "firewall", "switch"]][:4])
    }

    narrative, is_ai = await generate_narrative_section(
        section_type=ai_section_key,
        context=ai_context,
        use_ai=payload.use_ai
    )

    # 3. File naming and storage
    os.makedirs(DOCS_STORAGE_DIR, exist_ok=True)
    clean_ref = "".join(c for c in project.reference if c.isalnum() or c in "-_")
    filename = f"{clean_ref}_{doc_type.upper()}_v{payload.version}_{int(datetime.now().timestamp())}.{file_format}"
    file_path = os.path.join(DOCS_STORAGE_DIR, filename)

    # Title mapping
    type_titles = {
        "hld": "Dossier d'Architecture Générale (HLD)",
        "lld": "Dossier d'Architecture Technique Détaillée (LLD)",
        "config_annexes": "Annexes de Configuration Matérielle",
        "commissioning": "Dossier de Recette & Mise en Service"
    }
    doc_title = f"{type_titles[doc_type]} - {project.name}"

    # 4. Generate Document Binary
    if file_format == "docx":
        build_docx_document(
            output_path=file_path,
            doc_type=doc_type,
            project=project,
            equipment_list=equipment_list,
            segments=segments,
            configs=configs,
            narrative_text=narrative
        )
    else:  # pdf
        build_pdf_document(
            output_path=file_path,
            doc_type=doc_type,
            project=project,
            equipment_list=equipment_list,
            segments=segments,
            configs=configs,
            narrative_text=narrative
        )

    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

    # 5. Persist Document Record
    doc_record = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        generated_by_id=current_user.id,
        document_type=doc_type,
        title=doc_title,
        version=payload.version,
        file_format=file_format,
        file_path=file_path,
        file_size=file_size,
        ai_enhanced=is_ai,
        is_locked=False
    )
    db.add(doc_record)
    await db.commit()
    await db.refresh(doc_record)

    return DocumentResponse(
        id=doc_record.id,
        project_id=project_id,
        document_type=doc_record.document_type,
        title=doc_record.title,
        version=doc_record.version,
        file_format=doc_record.file_format,
        file_size=doc_record.file_size,
        ai_enhanced=doc_record.ai_enhanced,
        is_locked=doc_record.is_locked,
        created_at=doc_record.created_at,
        download_url=f"/api/documents/{doc_record.id}/download"
    )


@router.get("/projects/{project_id}/documents", response_model=List[DocumentResponse])
async def list_project_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all generated architecture deliverables for a project."""
    res = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(desc(Document.created_at))
    )
    docs = res.scalars().all()
    out = []
    for d in docs:
        resp = DocumentResponse.model_validate(d)
        resp.download_url = f"/api/documents/{d.id}/download"
        out.append(resp)
    return out


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Download a generated DOCX or PDF document."""
    # Authenticate via Header or Query parameter
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ", 1)[1].strip()
    elif token:
        auth_token = token.strip()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise pour télécharger ce document",
            headers={"WWW-Authenticate": "Bearer"}
        )

    from app.core.security import decode_access_token
    payload = decode_access_token(auth_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou token invalide",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_res = await db.execute(select(User).where(User.id == payload.get("sub")))
    user = user_res.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte inactif ou non autorisé"
        )

    res = await db.execute(select(Document).where(Document.id == document_id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Fichier physique manquant sur le serveur")

    filename = os.path.basename(doc.file_path)
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if doc.file_format == "docx" else "application/pdf"

    return FileResponse(
        path=doc.file_path,
        filename=filename,
        media_type=media_type
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer)
):
    """Delete a document and remove its file on disk."""
    res = await db.execute(select(Document).where(Document.id == document_id))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    if doc.is_locked:
        raise HTTPException(status_code=403, detail="Impossible de supprimer un document verrouillé/publié.")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()
    return None
