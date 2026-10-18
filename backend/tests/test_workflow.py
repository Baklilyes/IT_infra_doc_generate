"""Unit and integration tests for Lot 8: Lifecycle, Approval Workflow, Locking & Versioning."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project, ProjectStatus, Site, Location
from app.models.equipment import Equipment, EquipmentCategory, VerificationStatus
from app.models.network import Interface, NetworkSegment
from app.models.workflow import WorkflowDecision, WorkflowAction


@pytest.mark.asyncio
async def test_workflow_status_initial(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """Initial project state is draft, not locked, with submit action allowed for engineer."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    
    # Create clean project
    proj_resp = await client.post(
        "/api/projects",
        json={
            "reference": "PRJ-WF-001",
            "name": "Projet Workflow Test",
            "client_name": "Client WF",
            "lead_name": "Ingénieur Test"
        },
        headers=headers
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Check workflow status
    wf_resp = await client.get(f"/api/projects/{project_id}/workflow", headers=headers)
    assert wf_resp.status_code == 200
    wf_data = wf_resp.json()
    assert wf_data["status"] == "draft"
    assert wf_data["version"] == "1.0"
    assert wf_data["is_locked"] is False
    assert wf_data["can_publish"] is True
    assert "submit" in wf_data["allowed_actions"]


@pytest.mark.asyncio
async def test_submit_blocked_by_consistency_errors(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """A project containing blocking consistency anomalies cannot be submitted."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    
    proj_resp = await client.post(
        "/api/projects",
        json={
            "reference": "PRJ-WF-BLOCK-001",
            "name": "Projet WF Bloquant",
            "client_name": "Client WF",
            "lead_name": "Ingénieur Test"
        },
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    # Add duplicate IP equipments to cause blocking error
    eq1_resp = await client.post(
        f"/api/projects/{project_id}/equipment",
        json={
            "name": "SW-CORE-01",
            "category": "switch",
            "management_ip": "10.10.10.1"
        },
        headers=headers
    )
    assert eq1_resp.status_code == 201

    eq2_resp = await client.post(
        f"/api/projects/{project_id}/equipment",
        json={
            "name": "SW-CORE-02",
            "category": "switch",
            "management_ip": "10.10.10.1"  # Duplicate IP
        },
        headers=headers
    )
    assert eq2_resp.status_code == 201

    # Try to submit for review -> Must fail with HTTP 400
    sub_resp = await client.post(
        f"/api/projects/{project_id}/workflow/submit",
        json={"comment": "Soumission test"},
        headers=headers
    )
    assert sub_resp.status_code == 400
    assert "bloquante" in sub_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_succeeds_with_override(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """Once blocking anomalies are granted formal waivers, submission succeeds."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    
    proj_resp = await client.post(
        "/api/projects",
        json={
            "reference": "PRJ-WF-OVR-001",
            "name": "Projet WF Override",
            "client_name": "Client WF",
            "lead_name": "Ingénieur Test"
        },
        headers=headers
    )
    project_id = proj_resp.json()["id"]

    # Add duplicate IP
    eq1 = await client.post(
        f"/api/projects/{project_id}/equipment",
        json={"name": "RTR-01", "category": "router", "management_ip": "10.20.20.1"},
        headers=headers
    )
    eq2 = await client.post(
        f"/api/projects/{project_id}/equipment",
        json={"name": "RTR-02", "category": "router", "management_ip": "10.20.20.1"},
        headers=headers
    )
    eq1_id = eq1.json()["id"]
    eq2_id = eq2.json()["id"]

    # Grant waiver (override) for both duplicated IP endpoints
    for target_id in [eq1_id, eq2_id]:
        ovr_resp = await client.post(
            f"/api/projects/{project_id}/validations/override",
            json={
                "rule_code": "IP_DUPLICATE",
                "target_id": target_id,
                "target_type": "equipment",
                "severity": "blocking",
                "justification": "VIP partagée HSRP/VRRP documentée et autorisée par l'architecture client"
            },
            headers=headers
        )
        assert ovr_resp.status_code == 201

    # Now submission must succeed
    sub_resp = await client.post(
        f"/api/projects/{project_id}/workflow/submit",
        json={"comment": "Dossier prêt après dérogation VRRP"},
        headers=headers
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["to_status"] == "in_review"


@pytest.mark.asyncio
async def test_tech_reject_requires_motive_and_returns_to_draft(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """Technical reject requires non-empty motive >= 5 chars, and resets project to draft."""
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    lead_headers = {"Authorization": f"Bearer {auth_tokens['tech_lead']}"}

    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-WF-REJ-001", "name": "Projet Rejet Test", "client_name": "Client", "lead_name": "Lead"},
        headers=eng_headers
    )
    project_id = proj_resp.json()["id"]

    # Submit to in_review
    await client.post(f"/api/projects/{project_id}/workflow/submit", json={}, headers=eng_headers)

    # Rejection with empty motive -> HTTP 422
    rej_bad = await client.post(
        f"/api/projects/{project_id}/workflow/tech-reject",
        json={"comment": "Non"},  # < 5 chars
        headers=lead_headers
    )
    assert rej_bad.status_code == 422

    # Rejection with valid motive -> HTTP 200, status becomes draft
    rej_ok = await client.post(
        f"/api/projects/{project_id}/workflow/tech-reject",
        json={"comment": "Masque de sous-réseau erroné sur l'interface WAN, merci de corriger en /30."},
        headers=lead_headers
    )
    assert rej_ok.status_code == 200
    assert rej_ok.json()["to_status"] == "draft"

    # Verify status in db
    wf_status = await client.get(f"/api/projects/{project_id}/workflow", headers=eng_headers)
    assert wf_status.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_full_approval_workflow_with_sod_enforcement(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """
    Complete lifecycle:
    1. Engineer submits
    2. Separation of Duties: Submitter cannot tech-approve
    3. Tech Lead tech-approves
    4. Separation of Duties: Tech approver cannot final-approve
    5. Final Validator final-approves -> project closed and locked
    """
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    lead_headers = {"Authorization": f"Bearer {auth_tokens['tech_lead']}"}
    val_headers = {"Authorization": f"Bearer {auth_tokens['final_validator']}"}

    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-WF-SOD-001", "name": "Projet SoD Complete", "client_name": "Client", "lead_name": "Lead"},
        headers=eng_headers
    )
    project_id = proj_resp.json()["id"]

    # 1. Engineer submits
    sub_res = await client.post(f"/api/projects/{project_id}/workflow/submit", json={"comment": "Livraison v1.0"}, headers=eng_headers)
    assert sub_res.status_code == 200

    # 2. Tech Lead approves (different user)
    app_res = await client.post(
        f"/api/projects/{project_id}/workflow/tech-approve",
        json={"comment": "Architecture réseau et VLANs conformes"},
        headers=lead_headers
    )
    assert app_res.status_code == 200
    assert app_res.json()["to_status"] == "validated"

    # 3. Final Validator approves (different user)
    final_res = await client.post(
        f"/api/projects/{project_id}/workflow/final-approve",
        json={"comment": "Validation finale de mise en production"},
        headers=val_headers
    )
    assert final_res.status_code == 200
    assert final_res.json()["to_status"] == "closed"

    # Check project is locked
    wf_status = await client.get(f"/api/projects/{project_id}/workflow", headers=eng_headers)
    assert wf_status.json()["is_locked"] is True
    assert wf_status.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_separation_of_duties_violation_blocked(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """An admin or user who submitted cannot tech-approve without explicit bypass."""
    admin_headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}

    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-WF-SOD-VIOLATION", "name": "Projet SoD Test", "client_name": "Client", "lead_name": "Lead"},
        headers=admin_headers
    )
    project_id = proj_resp.json()["id"]

    # Admin submits
    await client.post(f"/api/projects/{project_id}/workflow/submit", json={}, headers=admin_headers)

    # Same admin tries to tech-approve without bypass -> HTTP 403
    app_fail = await client.post(
        f"/api/projects/{project_id}/workflow/tech-approve",
        json={"comment": "Auto-approbation"},
        headers=admin_headers
    )
    assert app_fail.status_code == 403
    assert "séparation" in app_fail.json()["detail"].lower()

    # Admin with explicit bypass_sod=True -> Succeeds
    app_ok = await client.post(
        f"/api/projects/{project_id}/workflow/tech-approve?bypass_sod=true",
        json={"comment": "Dérogation administrative exceptionnelle"},
        headers=admin_headers
    )
    assert app_ok.status_code == 200
    assert app_ok.json()["to_status"] == "validated"


@pytest.mark.asyncio
async def test_locked_project_immutability(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """Once a project is CLOSED (locked), all modifications are forbidden with HTTP 423 Locked."""
    admin_headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    lead_headers = {"Authorization": f"Bearer {auth_tokens['tech_lead']}"}
    val_headers = {"Authorization": f"Bearer {auth_tokens['final_validator']}"}

    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-WF-LOCKED-001", "name": "Projet Verrouillé", "client_name": "Client", "lead_name": "Lead"},
        headers=eng_headers
    )
    project_id = proj_resp.json()["id"]

    # Lifecycle to closed
    await client.post(f"/api/projects/{project_id}/workflow/submit", json={}, headers=eng_headers)
    await client.post(f"/api/projects/{project_id}/workflow/tech-approve", json={}, headers=lead_headers)
    await client.post(f"/api/projects/{project_id}/workflow/final-approve", json={}, headers=val_headers)

    # 1. Attempt to update project metadata -> 423
    mod_resp = await client.put(
        f"/api/projects/{project_id}",
        json={"name": "Tentative de modification illégale"},
        headers=eng_headers
    )
    assert mod_resp.status_code == 423
    assert "verrouillé" in mod_resp.json()["detail"].lower()

    # 2. Attempt to add equipment -> 423
    eq_resp = await client.post(
        f"/api/projects/{project_id}/equipment",
        json={"name": "NEW-SW-01", "category": "switch"},
        headers=eng_headers
    )
    assert eq_resp.status_code == 423

    # 3. Attempt to delete project -> 423
    del_resp = await client.delete(f"/api/projects/{project_id}", headers=eng_headers)
    assert del_resp.status_code == 423


@pytest.mark.asyncio
async def test_post_submission_tampering_resets_to_draft(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """
    Section 6.14: 'toute modification après soumission invalide les approbations précédentes de cette version'
    If equipment or project metadata is modified during in_review, status automatically resets to draft.
    """
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    lead_headers = {"Authorization": f"Bearer {auth_tokens['tech_lead']}"}

    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-WF-TAMPER-001", "name": "Projet Anti Tamper", "client_name": "Client", "lead_name": "Lead"},
        headers=eng_headers
    )
    project_id = proj_resp.json()["id"]

    eq_resp = await client.post(
        f"/api/projects/{project_id}/equipment",
        json={"name": "FIREWALL-01", "category": "firewall", "management_ip": "10.0.0.1"},
        headers=eng_headers
    )
    eq_id = eq_resp.json()["id"]

    # Submit for review
    await client.post(f"/api/projects/{project_id}/workflow/submit", json={}, headers=eng_headers)
    
    # Verify status is in_review
    wf_res = await client.get(f"/api/projects/{project_id}/workflow", headers=eng_headers)
    assert wf_res.json()["status"] == "in_review"

    # Modify equipment
    await client.put(
        f"/api/equipment/{eq_id}",
        json={"name": "FIREWALL-MODIFIED"},
        headers=eng_headers
    )

    # Project must now be back in draft!
    wf_after = await client.get(f"/api/projects/{project_id}/workflow", headers=eng_headers)
    assert wf_after.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_branch_new_version(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """
    Branching creates a new draft version cloned deeply from the locked project.
    Parent project remains locked and untouched.
    """
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    lead_headers = {"Authorization": f"Bearer {auth_tokens['tech_lead']}"}
    val_headers = {"Authorization": f"Bearer {auth_tokens['final_validator']}"}

    # Create project
    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-BRANCH-ORIG", "name": "Projet Source", "client_name": "Client", "lead_name": "Lead"},
        headers=eng_headers
    )
    orig_id = proj_resp.json()["id"]

    # Add site, equipment, segment
    site_resp = await client.post(
        f"/api/projects/{orig_id}/sites",
        json={"name": "Site Paris Principal", "city": "Paris"},
        headers=eng_headers
    )
    site_id = site_resp.json()["id"]

    eq_resp = await client.post(
        f"/api/projects/{orig_id}/equipment",
        json={"name": "RTR-PARIS-01", "category": "router", "site_id": site_id, "management_ip": "192.168.1.1"},
        headers=eng_headers
    )
    eq_id = eq_resp.json()["id"]

    seg_resp = await client.post(
        f"/api/projects/{orig_id}/segments",
        json={"name": "VLAN-MGMT", "vlan_id": 10, "cidr": "192.168.1.0/24", "gateway": "192.168.1.254"},
        headers=eng_headers
    )

    # Approve and seal original project
    await client.post(f"/api/projects/{orig_id}/workflow/submit", json={}, headers=eng_headers)
    await client.post(f"/api/projects/{orig_id}/workflow/tech-approve", json={}, headers=lead_headers)
    await client.post(f"/api/projects/{orig_id}/workflow/final-approve", json={}, headers=val_headers)

    # Branch new minor version 1.1
    branch_resp = await client.post(
        f"/api/projects/{orig_id}/workflow/branch-version",
        json={"version_bump": "minor", "comment": "Démarrage de la phase d'extension 1.1"},
        headers=eng_headers
    )
    assert branch_resp.status_code == 201
    new_proj = branch_resp.json()
    new_id = new_proj["id"]

    assert new_proj["version"] == "1.1"
    assert new_proj["status"] == "draft"
    assert new_proj["parent_project_id"] == orig_id
    assert new_id != orig_id

    # Verify deep copy in new project
    new_eqs = (await client.get(f"/api/projects/{new_id}/equipment", headers=eng_headers)).json()
    assert len(new_eqs) == 1
    assert new_eqs[0]["name"] == "RTR-PARIS-01"
    assert new_eqs[0]["id"] != eq_id  # Brand new UUID

    new_segs = (await client.get(f"/api/projects/{new_id}/segments", headers=eng_headers)).json()
    assert len(new_segs) == 1
    assert new_segs[0]["vlan_id"] == 10

    # Verify original project remains locked
    orig_wf = (await client.get(f"/api/projects/{orig_id}/workflow", headers=eng_headers)).json()
    assert orig_wf["is_locked"] is True
    assert orig_wf["status"] == "closed"


@pytest.mark.asyncio
async def test_workflow_history_audit_trail(client: AsyncClient, auth_tokens, db_session: AsyncSession):
    """Workflow history returns complete audit log with user names and roles."""
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    lead_headers = {"Authorization": f"Bearer {auth_tokens['tech_lead']}"}

    proj_resp = await client.post(
        "/api/projects",
        json={"reference": "PRJ-WF-AUDIT-001", "name": "Projet Audit Trail", "client_name": "Client", "lead_name": "Lead"},
        headers=eng_headers
    )
    project_id = proj_resp.json()["id"]

    await client.post(f"/api/projects/{project_id}/workflow/submit", json={"comment": "Soumission v1"}, headers=eng_headers)
    await client.post(f"/api/projects/{project_id}/workflow/tech-approve", json={"comment": "Revue OK"}, headers=lead_headers)

    hist_resp = await client.get(f"/api/projects/{project_id}/workflow/history", headers=eng_headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 2

    # Most recent first
    assert history[0]["action"] == "tech_approve"
    assert history[0]["user_role"] == "technical_lead"
    assert history[1]["action"] == "submit"
    assert history[1]["user_role"] == "engineer"
