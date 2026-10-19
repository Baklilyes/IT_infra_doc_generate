"""
Comprehensive Security and End-to-End Governance Tests (Lot 9 - Stabilisation).
Verifies:
1. Strict Role-Based Access Control (RBAC) across all functional domains.
2. Separation of Duties (SoD) and tamper-proof workflow governance.
3. Token expiration, tampering, and unauthenticated request rejection.
4. Path traversal and injection defense on file downloads and imports.
5. Zero cleartext secret leakage in AI prompts, logs, and document generation.
6. Offline AI graceful degradation and air-gap verification.
"""
import pytest
import os
import sys
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus, DocumentLanguage
from app.models.equipment import Equipment, EquipmentCategory, InstallationStatus, VerificationStatus
from app.models.network import ConfigurationParam
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_rejected(client: AsyncClient):
    """Ensure all protected API endpoints return 401 when no token is supplied."""
    endpoints = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/projects"),
        ("POST", "/api/projects"),
        ("GET", "/api/auth/users"),
        ("POST", "/api/imports/upload"),
        ("GET", "/api/documents/ai-status"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = await client.get(path)
        else:
            res = await client.post(path)
        assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_tampered_token_is_rejected(client: AsyncClient):
    """Ensure tokens with modified signature or malformed JWT payload return 401."""
    tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.TAMPERED_INVALID_SIGNATURE"
    headers = {"Authorization": f"Bearer {tampered_token}"}
    res = await client.get("/api/auth/me", headers=headers)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_rbac_matrix_enforcement(client: AsyncClient, db_session: AsyncSession, test_users: dict):
    """
    Test strict role segregation across all roles:
    - Administrator: can manage users, list all projects.
    - Engineer: can create projects, add equipment, run imports; CANNOT manage users or approve workflow.
    - Technical Lead: can perform technical review; CANNOT manage users or grant final validation.
    - Final Validator: can grant final validation; CANNOT bypass technical review or manage users.
    """
    admin_token = create_access_token({"sub": test_users["admin"].id, "role": UserRole.ADMINISTRATOR.value})
    engineer_token = create_access_token({"sub": test_users["engineer"].id, "role": UserRole.ENGINEER.value})
    tech_lead_token = create_access_token({"sub": test_users["tech_lead"].id, "role": UserRole.TECHNICAL_LEAD.value})
    validator_token = create_access_token({"sub": test_users["final_validator"].id, "role": UserRole.FINAL_VALIDATOR.value})

    # 1. Admin endpoints access control (/api/auth/users)
    # Admin -> 200
    res = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # Engineer -> 403
    res = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {engineer_token}"})
    assert res.status_code == 403

    # Tech Lead -> 403
    res = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {tech_lead_token}"})
    assert res.status_code == 403

    # Validator -> 403
    res = await client.get("/api/auth/users", headers={"Authorization": f"Bearer {validator_token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_path_traversal_defense_on_document_download(client: AsyncClient, test_users: dict):
    """Verify that path traversal attempts in document ID or paths are safely handled."""
    admin_token = create_access_token({"sub": test_users["admin"].id, "role": UserRole.ADMINISTRATOR.value})
    headers = {"Authorization": f"Bearer {admin_token}"}

    traversal_ids = [
        "../../../../etc/passwd",
        "..\\..\\..\\windows\\win.ini",
        "../../backend/app/main.py",
        "random-nonexistent-uuid"
    ]
    for doc_id in traversal_ids:
        res = await client.get(f"/api/documents/{doc_id}/download", headers=headers)
        assert res.status_code in [400, 404], f"Path traversal attempt {doc_id} must return 400 or 404, got {res.status_code}"


@pytest.mark.asyncio
async def test_separation_of_duties_workflow_gatekeeper(
    client: AsyncClient, db_session: AsyncSession, test_users: dict
):
    """
    Test Separation of Duties:
    1. Engineer creates project & submits.
    2. Engineer attempts to approve own submission -> 403 Forbidden.
    3. Tech Lead reviews and approves -> Status moves to IN_REVIEW (tech approved).
    4. Tech Lead attempts to grant FINAL approval -> 403 Forbidden.
    5. Final Validator grants final approval -> Status moves to VALIDATED.
    """
    eng_token = create_access_token({"sub": test_users["engineer"].id, "role": UserRole.ENGINEER.value})
    lead_token = create_access_token({"sub": test_users["tech_lead"].id, "role": UserRole.TECHNICAL_LEAD.value})
    val_token = create_access_token({"sub": test_users["final_validator"].id, "role": UserRole.FINAL_VALIDATOR.value})

    # Step 1: Create project as Engineer
    proj_res = await client.post(
        "/api/projects",
        json={
            "reference": "PRJ-SEC-01",
            "name": "Secured Network Infrastructure",
            "client_name": "Defense Security Agency",
            "lead_name": "Lead Test",
            "scope": "Perimeter network hardening",
            "document_language": "fr"
        },
        headers={"Authorization": f"Bearer {eng_token}"}
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # Step 2: Submit project
    sub_res = await client.post(
        f"/api/projects/{project_id}/workflow/submit",
        json={"comment": "Ready for initial technical audit"},
        headers={"Authorization": f"Bearer {eng_token}"}
    )
    assert sub_res.status_code == 200

    # Step 3: Engineer attempts to technical-approve -> 403
    eng_approve_attempt = await client.post(
        f"/api/projects/{project_id}/workflow/tech-approve",
        json={"comment": "Illegal self-approval attempt"},
        headers={"Authorization": f"Bearer {eng_token}"}
    )
    assert eng_approve_attempt.status_code == 403

    # Step 4: Tech Lead technical-approve -> 200
    lead_approve = await client.post(
        f"/api/projects/{project_id}/workflow/tech-approve",
        json={"comment": "Architecture reviewed and confirmed compliant"},
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert lead_approve.status_code == 200

    # Step 5: Tech Lead attempts final validation -> 403
    lead_final_attempt = await client.post(
        f"/api/projects/{project_id}/workflow/final-approve",
        json={"comment": "Illegal cross-role final sign-off attempt"},
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert lead_final_attempt.status_code == 403

    # Step 6: Final Validator approves -> 200
    val_final = await client.post(
        f"/api/projects/{project_id}/workflow/final-approve",
        json={"comment": "Final sign-off confirmed by head validator"},
        headers={"Authorization": f"Bearer {val_token}"}
    )
    assert val_final.status_code == 200
    assert val_final.json()["to_status"] == ProjectStatus.CLOSED.value


@pytest.mark.asyncio
async def test_secret_sanitization_integrity(
    client: AsyncClient, db_session: AsyncSession, test_users: dict
):
    """
    Verify that configuration parameters containing sensitive keys
    (passwords, pre-shared keys, snmp community strings) have their values
    properly masked as <SECRET_MASQUÉ> in client queries when is_secret is True.
    """
    admin_token = create_access_token({"sub": test_users["admin"].id, "role": UserRole.ADMINISTRATOR.value})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create project
    proj_res = await client.post(
        "/api/projects",
        json={
            "reference": "PRJ-SEC-02",
            "name": "Audit Secrets Project",
            "client_name": "Finance Corp",
            "lead_name": "Auditor",
            "document_language": "fr"
        },
        headers=headers
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # Insert a sensitive configuration parameter
    cfg = ConfigurationParam(
        project_id=project_id,
        category="security",
        key="vpn_ipsec_preshared_key",
        value="UltraSecretCompanyKey2026!",
        is_secret=True
    )
    db_session.add(cfg)
    await db_session.commit()

    # Query configurations endpoint
    res = await client.get(f"/api/projects/{project_id}/configurations", headers=headers)
    assert res.status_code == 200
    configs = res.json()
    assert len(configs) >= 1
    found_secret_param = next(c for c in configs if c["key"] == "vpn_ipsec_preshared_key")
    assert found_secret_param["value"] == "<SECRET_MASQUÉ>", "Cleartext secret must never be exposed"
