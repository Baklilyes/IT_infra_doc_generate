"""Tests for Lot 6 - Architecture Diagrams (SVG Physical, Logical Topology & Application Flows)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_physical_diagram_generation(client: AsyncClient, auth_tokens):
    """Test generating physical infrastructure diagram grouped by sites, locations, and cabling links."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    # 1. Create project
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DIAG-01",
        "name": "Diagram Test Project",
        "client_name": "Diagram Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # 2. Create Site & Location
    site_resp = await client.post(f"/api/projects/{project_id}/sites", headers=headers, json={
        "name": "DC-PARIS-NORD",
        "city": "Paris"
    })
    site_id = site_resp.json()["id"]

    loc_resp = await client.post(f"/api/sites/{site_id}/locations", headers=headers, json={
        "name": "Baie B01 - Salle Blanche",
        "rack": "42U-01"
    })
    loc_id = loc_resp.json()["id"]

    # 3. Create 2 connected switches
    sw1_resp = await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-CORE-PARIS",
        "category": "switch",
        "model": "Catalyst 9500",
        "management_ip": "10.100.0.1",
        "site_id": site_id,
        "location_id": loc_id
    })
    sw1_id = sw1_resp.json()["id"]

    sw2_resp = await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "SW-ACCESS-PARIS",
        "category": "switch",
        "model": "Catalyst 9300",
        "management_ip": "10.100.0.2",
        "site_id": site_id,
        "location_id": loc_id
    })
    sw2_id = sw2_resp.json()["id"]

    # Create link on interface
    await client.post(f"/api/equipment/{sw2_id}/interfaces", headers=headers, json={
        "name": "TenGigabitEthernet1/1/1",
        "interface_type": "physical",
        "connected_equipment_id": sw1_id,
        "link_type": "Fibre OM4 10G"
    })

    # 4. Fetch Physical Diagram JSON
    res = await client.get(f"/api/projects/{project_id}/diagrams/physical", headers=headers)
    assert res.status_code == 200
    diag = res.json()
    assert diag["diagram_type"] == "physical"
    assert "<svg" in diag["svg"]
    assert "SW-CORE-PARIS" in diag["svg"]
    assert "SW-ACCESS-PARIS" in diag["svg"]
    assert "DC-PARIS-NORD" in diag["svg"]
    assert "Fibre OM4 10G" in diag["svg"]

    # 5. Fetch Raw SVG image
    raw_res = await client.get(f"/api/projects/{project_id}/diagrams/physical/raw", headers=headers)
    assert raw_res.status_code == 200
    assert "image/svg+xml" in raw_res.headers["content-type"]
    assert raw_res.text.startswith("<svg")


@pytest.mark.asyncio
async def test_logical_topology_generation(client: AsyncClient, auth_tokens):
    """Test generating logical topology diagram with VLAN segmentation and routing."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DIAG-VLAN",
        "name": "VLAN Topology Project",
        "client_name": "Diagram Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    # Create Core Router
    r_resp = await client.post(f"/api/projects/{project_id}/equipment", headers=headers, json={
        "name": "RTR-CORE-01",
        "category": "router",
        "management_ip": "10.0.0.254"
    })
    r_id = r_resp.json()["id"]

    # Create VLAN Segments
    await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 10,
        "name": "USERS_LAN",
        "cidr": "192.168.10.0/24",
        "gateway": "192.168.10.254",
        "zone": "LAN"
    })
    await client.post(f"/api/projects/{project_id}/segments", headers=headers, json={
        "vlan_id": 20,
        "name": "SERVERS_FARM",
        "cidr": "10.0.20.0/24",
        "gateway": "10.0.20.254",
        "zone": "DMZ"
    })

    # Fetch Logical Diagram
    res = await client.get(f"/api/projects/{project_id}/diagrams/logical", headers=headers)
    assert res.status_code == 200
    diag = res.json()
    assert diag["diagram_type"] == "logical"
    assert "VLAN 10 : USERS_LAN" in diag["svg"]
    assert "VLAN 20 : SERVERS_FARM" in diag["svg"]
    assert "192.168.10.0/24" in diag["svg"]
    assert "RTR-CORE-01" in diag["svg"]

    # Raw SVG
    raw_res = await client.get(f"/api/projects/{project_id}/diagrams/logical/raw", headers=headers)
    assert raw_res.status_code == 200
    assert "image/svg+xml" in raw_res.headers["content-type"]


@pytest.mark.asyncio
async def test_flow_matrix_generation(client: AsyncClient, auth_tokens):
    """Test generating flow matrix diagram detailing ports and security directions."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DIAG-FLOW",
        "name": "Flow Matrix Project",
        "client_name": "Diagram Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    res = await client.get(f"/api/projects/{project_id}/diagrams/flows", headers=headers)
    assert res.status_code == 200
    diag = res.json()
    assert diag["diagram_type"] == "flows"
    assert "Zone Utilisateurs (LAN)" in diag["svg"]
    assert "TCP 443" in diag["svg"]
    assert "Zone Serveurs" in diag["svg"]


@pytest.mark.asyncio
async def test_all_diagrams_endpoint(client: AsyncClient, auth_tokens):
    """Test retrieving all three architectural diagrams in a single call."""
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}

    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DIAG-ALL",
        "name": "All Diagrams Project",
        "client_name": "Diagram Client",
        "lead_name": "Tech Lead"
    })
    project_id = p_resp.json()["id"]

    res = await client.get(f"/api/projects/{project_id}/diagrams/all", headers=headers)
    assert res.status_code == 200
    diagrams = res.json()
    assert len(diagrams) == 3
    types = [d["diagram_type"] for d in diagrams]
    assert "physical" in types
    assert "logical" in types
    assert "flows" in types
