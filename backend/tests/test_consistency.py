"""Tests for Lot 5 - Deterministic Consistency Engine and Formal Overrides."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_duplicate_ip_and_hostname_detection(client: AsyncClient, auth_tokens):
    """Test detection of duplicated hostnames and IP addresses within a project."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    # 1. Create project
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-CONST-01",
        "name": "Consistency Test Project",
        "client_name": "Audit Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # 2. Create two switches with identical name and identical IP
    await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-IDENTICAL-01",
        "category": "switch",
        "management_ip": "10.10.10.1"
    })
    await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-IDENTICAL-01",
        "category": "switch",
        "management_ip": "10.10.10.1"
    })

    # 3. Run validation
    v_resp = await client.post(f"/api/projects/{project_id}/validations/run", headers=headers)
    assert v_resp.status_code == 201
    rep = v_resp.json()
    assert rep["status"] == "failed"
    assert rep["blocking_count"] >= 2

    rule_codes = [f["rule_code"] for f in rep["findings"]]
    assert "HOSTNAME_DUPLICATE" in rule_codes
    assert "IP_DUPLICATE" in rule_codes


@pytest.mark.asyncio
async def test_cidr_overlap_and_gateway_out_of_range(client: AsyncClient, auth_tokens):
    """Test detection of overlapping subnets and gateway IPs outside the CIDR range."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-CONST-CIDR",
        "name": "CIDR Test Project",
        "client_name": "Audit Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # Create parent subnet /16
    await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 100,
        "name": "GLOBAL_CORP",
        "cidr": "172.16.0.0/16",
        "gateway": "172.16.0.1"
    })

    # Create overlapping /24 with out-of-range gateway
    await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 101,
        "name": "BRANCH_OVERLAP",
        "cidr": "172.16.50.0/24",
        "gateway": "192.168.99.1"  # Invalid: not in 172.16.50.0/24!
    })

    # Run validation
    v_resp = await client.post(f"/api/projects/{project_id}/validations/run", headers=headers)
    assert v_resp.status_code == 201
    rep = v_resp.json()

    rule_codes = [f["rule_code"] for f in rep["findings"]]
    assert "CIDR_OVERLAP" in rule_codes
    assert "GATEWAY_OUT_OF_SUBNET" in rule_codes


@pytest.mark.asyncio
async def test_undefined_vlan_on_interface(client: AsyncClient, auth_tokens):
    """Test warning when an interface is assigned a VLAN not declared in the project segments."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-CONST-VLAN",
        "name": "Undefined VLAN Project",
        "client_name": "Audit Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    eq_resp = await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-ACCESS-TEST",
        "category": "switch"
    })
    eq_id = eq_resp.json()["id"]

    # Create interface with access_vlan=444 without declaring VLAN 444
    await client.post(f"/api/equipment/{eq_id}/interfaces", headers=headers, json={
        "name": "GigabitEthernet0/5",
        "interface_type": "physical",
        "mode": "access",
        "access_vlan": 444
    })

    # Run validation
    v_resp = await client.post(f"/api/projects/{project_id}/validations/run", headers=headers)
    assert v_resp.status_code == 201
    rep = v_resp.json()

    vlan_undef = [f for f in rep["findings"] if f["rule_code"] == "VLAN_UNDEFINED"]
    assert len(vlan_undef) >= 1
    assert vlan_undef[0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_cleartext_secret_detection(client: AsyncClient, auth_tokens):
    """Test blocking alert when cleartext passwords or credentials are found in description fields."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-CONST-SEC",
        "name": "Security Audit Project",
        "client_name": "Audit Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # Equipment with password in notes
    await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "FW-PERIMETRE-LEAK",
        "category": "firewall",
        "notes": "ATTENTION: admin access password=AdminPasswordSuperSecret! a changer apres mise en service"
    })

    # Run validation
    v_resp = await client.post(f"/api/projects/{project_id}/validations/run", headers=headers)
    assert v_resp.status_code == 201
    rep = v_resp.json()

    secret_findings = [f for f in rep["findings"] if f["rule_code"] == "CLEAR_TEXT_SECRET"]
    assert len(secret_findings) >= 1
    assert secret_findings[0]["severity"] == "blocking"


@pytest.mark.asyncio
async def test_waiver_override_workflow(client: AsyncClient, auth_tokens):
    """Test formal override / justification of a finding to waive blocking status."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-CONST-OVR",
        "name": "Override Waiver Project",
        "client_name": "Audit Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # Create 2 overlapping segments
    s1 = await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 200,
        "name": "MAIN_DC",
        "cidr": "10.0.0.0/16"
    })
    s2 = await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 201,
        "name": "OOB_MGMT",
        "cidr": "10.0.10.0/24"
    })
    s1_id = s1.json()["id"]

    # Check can-publish (must be blocked)
    pub_res1 = await client.get(f"/api/projects/{project_id}/validations/can-publish", headers=headers)
    assert pub_res1.status_code == 200
    assert pub_res1.json()["can_publish"] is False

    # Short justification rejected
    bad_ovr = await client.post(
        f"/api/projects/{project_id}/validations/override",
        headers=headers,
        json={
            "rule_code": "CIDR_OVERLAP",
            "target_id": s1_id,
            "target_type": "segment",
            "severity": "blocking",
            "justification": "short"
        }
    )
    assert bad_ovr.status_code == 422

    # Detailed valid justification accepted
    good_ovr = await client.post(
        f"/api/projects/{project_id}/validations/override",
        headers=headers,
        json={
            "rule_code": "CIDR_OVERLAP",
            "target_id": s1_id,
            "target_type": "segment",
            "severity": "blocking",
            "justification": "Dérogation technique : sous-réseau OOB physiquement isolé sur commutateurs dédiés."
        }
    )
    assert good_ovr.status_code == 201
    ovr_id = good_ovr.json()["id"]

    # Re-run validations
    v_resp = await client.post(f"/api/projects/{project_id}/validations/run", headers=headers)
    assert v_resp.status_code == 201
    rep = v_resp.json()
    assert rep["resolved_count"] >= 1

    # Check can-publish is now true
    pub_res2 = await client.get(f"/api/projects/{project_id}/validations/can-publish", headers=headers)
    assert pub_res2.status_code == 200
    assert pub_res2.json()["can_publish"] is True

    # Delete override and check it blocks again
    del_res = await client.delete(f"/api/projects/{project_id}/validations/override/{ovr_id}", headers=headers)
    assert del_res.status_code == 204

    pub_res3 = await client.get(f"/api/projects/{project_id}/validations/can-publish", headers=headers)
    assert pub_res3.json()["can_publish"] is False
