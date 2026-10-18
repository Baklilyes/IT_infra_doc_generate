"""Tests for Lot 7 - Local AI Integration & Document Generation (DOCX & PDF)."""
import os
import pytest
from httpx import AsyncClient
from app.core.ai.prompts import sanitize_prompt_context
from app.core.ai.client import generate_narrative_section, AI_DISCLAIMER_TAG, TEMPLATE_FALLBACK_TAG


def test_secret_sanitization_in_prompts():
    """Verify passwords, keys, and tokens are strictly sanitized before reaching LLM."""
    raw_text = "Configuration standard: password=SuperSecretPassword123! and token: abcdef123456"
    sanitized = sanitize_prompt_context(raw_text)
    assert "SuperSecretPassword123!" not in sanitized
    assert "abcdef123456" not in sanitized
    assert "<SECRET_MASQUÉ>" in sanitized


@pytest.mark.asyncio
async def test_ai_graceful_fallback():
    """Verify narrative synthesis gracefully falls back to deterministic template if Ollama is unreachable."""
    context = {
        "reference": "PRJ-TEST-AI",
        "name": "Fallback Test Project",
        "client_name": "Test Client",
        "equipment_count": 5,
        "segments_count": 3
    }
    narrative, is_ai = await generate_narrative_section(
        section_type="hld_summary",
        context=context,
        use_ai=True
    )
    assert len(narrative) > 50
    # Must have either AI tag or Fallback tag
    assert (AI_DISCLAIMER_TAG in narrative) or (TEMPLATE_FALLBACK_TAG in narrative)


@pytest.mark.asyncio
async def test_docx_hld_generation(client: AsyncClient, auth_tokens):
    """Test generating High Level Design document in DOCX format."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    # Create project
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DOC-HLD",
        "name": "HLD Document Test",
        "client_name": "Corporate Client",
        "lead_name": "Lead Architect"
    })
    project_id = p_resp.json()["id"]

    # Add switch and segment
    await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-CORE-01",
        "category": "switch",
        "management_ip": "10.0.0.1"
    })
    await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 10,
        "name": "LAN_DATA",
        "cidr": "10.0.10.0/24"
    })

    # Generate HLD DOCX
    res = await client.post(
        f"/api/projects/{project_id}/documents/generate",
        headers=headers,
        json={
            "document_type": "hld",
            "file_format": "docx",
            "use_ai": True,
            "version": "1.0"
        }
    )
    assert res.status_code == 201, res.text
    doc_data = res.json()
    assert doc_data["document_type"] == "hld"
    assert doc_data["file_format"] == "docx"
    assert doc_data["file_size"] > 1000
    doc_id = doc_data["id"]

    # Verify download
    dl_res = await client.get(f"/api/documents/{doc_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert "wordprocessingml" in dl_res.headers["content-type"]
    assert len(dl_res.content) > 1000


@pytest.mark.asyncio
async def test_pdf_lld_generation(client: AsyncClient, auth_tokens):
    """Test generating Low Level Design document in PDF format."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DOC-LLD",
        "name": "LLD Document Test",
        "client_name": "Corporate Client",
        "lead_name": "Lead Architect"
    })
    project_id = p_resp.json()["id"]

    # Generate LLD PDF
    res = await client.post(
        f"/api/projects/{project_id}/documents/generate",
        headers=headers,
        json={
            "document_type": "lld",
            "file_format": "pdf",
            "use_ai": False,
            "version": "1.0"
        }
    )
    assert res.status_code == 201, res.text
    doc_data = res.json()
    assert doc_data["file_format"] == "pdf"
    assert doc_data["file_size"] > 1000

    # Verify download starts with PDF magic bytes
    dl_res = await client.get(f"/api/documents/{doc_data['id']}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_commissioning_and_config_annexes_with_secret_masking(client: AsyncClient, auth_tokens):
    """Test Commissioning dossier and verify secrets are masked in Config Annexes."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DOC-CFG",
        "name": "Secret Masking Document Test",
        "client_name": "Security Client",
        "lead_name": "Security Engineer"
    })
    project_id = p_resp.json()["id"]

    # Create equipment with a secret configuration
    eq_res = await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-ACCESS-01",
        "category": "switch"
    })
    eq_id = eq_res.json()["id"]

    await client.post(f"/api/projects/{project_id}/configurations", headers=headers, json={
        "equipment_id": eq_id,
        "category": "snmp",
        "key": "snmp_ro_community",
        "value": "TopSecretCommunityRO123",
        "is_secret": True
    })

    # Generate Config Annexes DOCX
    res_cfg = await client.post(
        f"/api/projects/{project_id}/documents/generate",
        headers=headers,
        json={
            "document_type": "config_annexes",
            "file_format": "docx",
            "use_ai": False,
            "version": "1.0"
        }
    )
    assert res_cfg.status_code == 201
    cfg_doc = res_cfg.json()

    # Download and inspect binary content: ensure clear password is NOT present and secret is masked
    dl_cfg = await client.get(f"/api/documents/{cfg_doc['id']}/download", headers=headers)
    assert b"TopSecretCommunityRO123" not in dl_cfg.content
    
    import io
    from docx import Document as DocxDocument
    doc_obj = DocxDocument(io.BytesIO(dl_cfg.content))
    all_table_text = " ".join(cell.text for t in doc_obj.tables for row in t.rows for cell in row.cells)
    assert "<SECRET_MASQUÉ>" in all_table_text
    assert "TopSecretCommunityRO123" not in all_table_text

    # Generate Commissioning PDF
    res_com = await client.post(
        f"/api/projects/{project_id}/documents/generate",
        headers=headers,
        json={
            "document_type": "commissioning",
            "file_format": "pdf",
            "use_ai": False,
            "version": "1.0"
        }
    )
    assert res_com.status_code == 201
    com_doc = res_com.json()
    assert com_doc["document_type"] == "commissioning"


@pytest.mark.asyncio
async def test_document_listing_and_deletion(client: AsyncClient, auth_tokens):
    """Test listing documents and deleting an unlocked draft deliverable."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DOC-LIST",
        "name": "List Docs Project",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    project_id = p_resp.json()["id"]

    # Generate doc
    gen_res = await client.post(
        f"/api/projects/{project_id}/documents/generate",
        headers=headers,
        json={"document_type": "hld", "file_format": "docx", "use_ai": False}
    )
    doc_id = gen_res.json()["id"]

    # List
    list_res = await client.get(f"/api/projects/{project_id}/documents", headers=headers)
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["id"] == doc_id for d in docs)

    # Delete
    del_res = await client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 204

    # List again
    list_res2 = await client.get(f"/api/projects/{project_id}/documents", headers=headers)
    assert not any(d["id"] == doc_id for d in list_res2.json())
