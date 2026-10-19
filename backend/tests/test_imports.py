"""Tests for Lot 4 - Data Ingestion, Tabular Parsers, and CLI Adapters."""
import io
import pytest
import openpyxl
from httpx import AsyncClient
from app.models.equipment import VerificationStatus


@pytest.mark.asyncio
async def test_csv_equipment_import_workflow(client: AsyncClient, auth_tokens):
    """Test full CSV equipment import: upload, auto-mapping, preview, and apply."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    # Create project
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-IMP-01",
        "name": "Import Test Project",
        "client_name": "Import Client",
        "lead_name": "Tech Lead"
    })
    assert p_resp.status_code == 201
    project_id = p_resp.json()["id"]

    csv_content = """Nom,Catégorie,Modèle,Fabricant,Numéro de série,IP Management
SW-ACC-01,switch,Catalyst 9200L,Cisco,FOC12345678,192.168.10.10
FW-EDGE-01,firewall,FortiGate 60F,Fortinet,FGT98765432,192.168.1.1
"""
    files = {
        "file": ("inventaire_equipements.csv", csv_content.encode("utf-8"), "text/csv")
    }
    data = {
        "project_id": project_id,
        "target_type": "equipment"
    }

    # 1. Upload
    res = await client.post(
        "/api/imports/upload",
        files=files,
        data=data,
        headers=headers
    )
    assert res.status_code == 201, res.text
    upload_data = res.json()
    job_id = upload_data["job_id"]
    assert upload_data["file_type"] == "csv"
    assert upload_data["total_raw_rows"] == 2
    assert upload_data["suggested_mapping"]["Nom"] == "name"
    assert upload_data["suggested_mapping"]["Catégorie"] == "category"

    # 2. Preview
    res_prev = await client.post(
        f"/api/imports/{job_id}/preview",
        json={"mappings": upload_data["suggested_mapping"], "target_type": "equipment"},
        headers=headers
    )
    assert res_prev.status_code == 200, res_prev.text
    prev_data = res_prev.json()
    assert prev_data["valid_count"] == 2
    assert prev_data["conflict_count"] == 0
    assert prev_data["error_count"] == 0

    # 3. Apply
    res_apply = await client.post(
        f"/api/imports/{job_id}/apply",
        json={"conflict_resolution": "skip"},
        headers=headers
    )
    assert res_apply.status_code == 200, res_apply.text
    apply_data = res_apply.json()
    assert apply_data["status"] == "applied"
    assert apply_data["created_count"] == 2

    # Verify equipment in DB
    res_eq = await client.get(
        f"/api/projects/{project_id}/equipment",
        headers=headers
    )
    assert res_eq.status_code == 200
    items = res_eq.json()
    names = [i["name"] for i in items]
    assert "SW-ACC-01" in names
    assert "FW-EDGE-01" in names
    # Verification status must be unverified for imported items
    for item in items:
        if item["name"] in ["SW-ACC-01", "FW-EDGE-01"]:
            assert item["verification_status"] == VerificationStatus.UNVERIFIED.value


@pytest.mark.asyncio
async def test_csv_network_segments_import_workflow(client: AsyncClient, auth_tokens):
    """Test importing network segments from CSV with auto-detection."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    # Create project
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-IMP-VLAN",
        "name": "Import VLAN Test Project",
        "client_name": "Import Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    csv_content = """VLAN ID,Nom VLAN,Sous-réseau,Passerelle,Zone
10,DATA_USERS,192.168.10.0/24,192.168.10.254,LAN
20,VOIP,192.168.20.0/24,192.168.20.254,VOICE
30,SERVERS,10.0.30.0/24,10.0.30.254,DMZ
"""
    files = {
        "file": ("plan_adressage.csv", csv_content.encode("utf-8"), "text/csv")
    }
    data = {
        "project_id": project_id,
        "target_type": "network_segments"
    }

    res_up = await client.post(
        "/api/imports/upload",
        files=files,
        data=data,
        headers=headers
    )
    assert res_up.status_code == 201
    upload_data = res_up.json()
    job_id = upload_data["job_id"]

    res_prev = await client.post(
        f"/api/imports/{job_id}/preview",
        json={"mappings": upload_data["suggested_mapping"], "target_type": "network_segments"},
        headers=headers
    )
    assert res_prev.status_code == 200
    prev_data = res_prev.json()
    assert prev_data["valid_count"] == 3

    res_apply = await client.post(
        f"/api/imports/{job_id}/apply",
        json={"conflict_resolution": "skip"},
        headers=headers
    )
    assert res_apply.status_code == 200
    assert res_apply.json()["created_count"] == 3

    # Check network segments in DB
    res_list = await client.get(
        f"/api/projects/{project_id}/segments",
        headers=headers
    )
    assert res_list.status_code == 200
    vlans = [s["vlan_id"] for s in res_list.json()]
    assert 10 in vlans and 20 in vlans and 30 in vlans


@pytest.mark.asyncio
async def test_import_validation_errors(client: AsyncClient, auth_tokens):
    """Test rejection of malformed IPs and VLAN IDs during import preview."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-IMP-ERR",
        "name": "Import Errors Project",
        "client_name": "Import Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    csv_content = """Nom,Catégorie,IP Management
BAD-DEVICE-1,switch,999.999.999.999
BAD-DEVICE-2,router,not-an-ip
GOOD-DEVICE,switch,10.10.10.10
"""
    files = {"file": ("bad_inventory.csv", csv_content.encode("utf-8"), "text/csv")}
    res_up = await client.post(
        "/api/imports/upload",
        files=files,
        data={"project_id": project_id, "target_type": "equipment"},
        headers=headers
    )
    job_id = res_up.json()["job_id"]

    res_prev = await client.post(
        f"/api/imports/{job_id}/preview",
        json={"mappings": res_up.json()["suggested_mapping"], "target_type": "equipment"},
        headers=headers
    )
    assert res_prev.status_code == 200
    prev = res_prev.json()
    assert prev["error_count"] == 2
    assert prev["valid_count"] == 1


@pytest.mark.asyncio
async def test_import_conflict_detection_and_resolution(client: AsyncClient, auth_tokens):
    """Test duplicate detection (same hostname & IP) and resolution strategies."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-IMP-CONF",
        "name": "Import Conflict Project",
        "client_name": "Import Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # Pre-create equipment
    await client.post(
        f"/api/projects/{project_id}/equipment",
        json={
            "name": "SW-CORE-PRIMARY",
            "category": "switch",
            "model": "Catalyst 9500",
            "management_ip": "10.0.0.1"
        },
        headers=headers
    )

    # Now upload CSV with conflicting device
    csv_content = """Nom,Catégorie,Modèle,IP Management
SW-CORE-PRIMARY,switch,Catalyst 9500-Updated,10.0.0.1
SW-BRANCH-01,switch,Catalyst 9200,10.0.1.1
"""
    files = {"file": ("conflict_inventory.csv", csv_content.encode("utf-8"), "text/csv")}
    res_up = await client.post(
        "/api/imports/upload",
        files=files,
        data={"project_id": project_id, "target_type": "equipment"},
        headers=headers
    )
    job_id = res_up.json()["job_id"]

    res_prev = await client.post(
        f"/api/imports/{job_id}/preview",
        json={"mappings": res_up.json()["suggested_mapping"], "target_type": "equipment"},
        headers=headers
    )
    prev = res_prev.json()
    assert prev["conflict_count"] == 1
    assert prev["valid_count"] == 1
    conflict_item = [i for i in prev["items"] if i["status"] == "conflict"][0]
    assert any("existe déjà" in c for c in conflict_item["conflicts"])

    # Apply with skip
    res_apply = await client.post(
        f"/api/imports/{job_id}/apply",
        json={"conflict_resolution": "skip"},
        headers=headers
    )
    assert res_apply.json()["skipped_count"] == 1
    assert res_apply.json()["created_count"] == 1


@pytest.mark.asyncio
async def test_excel_import(client: AsyncClient, auth_tokens):
    """Test importing an Excel (.xlsx) file created in memory."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-IMP-XLSX",
        "name": "Import Excel Project",
        "client_name": "Import Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Equipements"
    ws.append(["Nom", "Catégorie", "Modèle", "Fabricant", "IP Management"])
    ws.append(["SRV-EXCEL-01", "serveur", "PowerEdge R750", "Dell", "172.16.1.10"])
    ws.append(["SRV-EXCEL-02", "serveur", "PowerEdge R750", "Dell", "172.16.1.11"])

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_bytes = excel_buffer.getvalue()

    files = {"file": ("serveurs.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res_up = await client.post(
        "/api/imports/upload",
        files=files,
        data={"project_id": project_id, "target_type": "equipment"},
        headers=headers
    )
    assert res_up.status_code == 201
    job_id = res_up.json()["job_id"]

    res_prev = await client.post(
        f"/api/imports/{job_id}/preview",
        json={"mappings": res_up.json()["suggested_mapping"], "target_type": "equipment"},
        headers=headers
    )
    assert res_prev.status_code == 200
    assert res_prev.json()["valid_count"] == 2

    res_apply = await client.post(
        f"/api/imports/{job_id}/apply",
        json={"conflict_resolution": "skip"},
        headers=headers
    )
    assert res_apply.status_code == 200
    assert res_apply.json()["created_count"] == 2


@pytest.mark.asyncio
async def test_cisco_ios_config_import(client: AsyncClient, auth_tokens):
    """Test importing a Cisco IOS running-config into equipment, interfaces, and configs."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-IMP-CISCO",
        "name": "Import Cisco Project",
        "client_name": "Import Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    cisco_config = """!
version 15.2
hostname SW-DIST-BUILDING-A
!
ip domain-name enterprise.local
ip name-server 1.1.1.1 8.8.8.8
ntp server 192.168.1.50
snmp-server community PrivateCommunityRO RO
!
vlan 10
 name USERS_DATA
!
vlan 20
 name SERVERS_FARM
!
interface GigabitEthernet0/1
 description Uplink to Core
 switchport mode trunk
 switchport trunk allowed vlan 10,20
!
interface GigabitEthernet0/2
 description User workstation
 switchport mode access
 switchport access vlan 10
!
interface Vlan1
 description Management SVI
 ip address 10.100.1.5 255.255.255.0
 no shutdown
!
end
"""
    files = {"file": ("cisco_switch.cfg", cisco_config.encode("utf-8"), "text/plain")}
    res_up = await client.post(
        "/api/imports/upload",
        files=files,
        data={"project_id": project_id, "target_type": "cli"},
        headers=headers
    )
    assert res_up.status_code == 201
    job_id = res_up.json()["job_id"]

    res_prev = await client.post(
        f"/api/imports/{job_id}/preview",
        json={},
        headers=headers
    )
    assert res_prev.status_code == 200
    prev = res_prev.json()
    assert prev["valid_count"] == 1
    item = prev["items"][0]
    assert item["data"]["name"] == "SW-DIST-BUILDING-A"
    assert item["data"]["parsed_interfaces_count"] >= 3

    # Apply
    res_apply = await client.post(
        f"/api/imports/{job_id}/apply",
        json={"conflict_resolution": "skip"},
        headers=headers
    )
    assert res_apply.status_code == 200
    assert res_apply.json()["created_count"] == 1

    # Verify equipment was created
    res_eq = await client.get(
        f"/api/projects/{project_id}/equipment",
        headers=headers
    )
    eq_list = res_eq.json()
    eq_item = [i for i in eq_list if i["name"] == "SW-DIST-BUILDING-A"][0]
    assert eq_item["management_ip"] == "10.100.1.5"

    # Verify interfaces created
    res_if = await client.get(
        f"/api/equipment/{eq_item['id']}/interfaces",
        headers=headers
    )
    assert res_if.status_code == 200
    if_names = [i["name"] for i in res_if.json()]
    assert "GigabitEthernet0/1" in if_names
    assert "Vlan1" in if_names

    # Verify secrets masked in configurations
    res_cfg = await client.get(
        f"/api/projects/{project_id}/configurations",
        headers=headers
    )
    assert res_cfg.status_code == 200
    cfgs = res_cfg.json()
    snmp_cfg = [c for c in cfgs if c["key"] == "snmp_community"][0]
    assert snmp_cfg["value"] == "<SECRET_MASQUÉ>"


@pytest.mark.asyncio
async def test_download_import_templates(client: AsyncClient, auth_tokens):
    """Test downloading formatted Excel templates for equipment, segments, and complete."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    # 1. Equipment template
    res_eq = await client.get("/api/imports/templates?type=equipment", headers=headers)
    assert res_eq.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_eq.headers["content-type"]
    assert "template_inventaire_equipements.xlsx" in res_eq.headers["content-disposition"]
    eq_content = res_eq.content
    assert len(eq_content) > 1000

    # 2. Segments template
    res_seg = await client.get("/api/imports/templates?type=segments", headers=headers)
    assert res_seg.status_code == 200
    assert "template_vlans_reseaux.xlsx" in res_seg.headers["content-disposition"]
    assert len(res_seg.content) > 1000

    # 3. Complete workbook template
    res_comp = await client.get("/api/imports/templates?type=complete", headers=headers)
    assert res_comp.status_code == 200
    assert "template_import_inventaire_complet.xlsx" in res_comp.headers["content-disposition"]
    assert len(res_comp.content) > 1000

    # 4. Unauthorized without token
    res_unauth = await client.get("/api/imports/templates?type=equipment")
    assert res_unauth.status_code == 401
