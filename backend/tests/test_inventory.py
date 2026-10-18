import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_equipment_crud(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    # 1. Create project
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-INV-01",
        "name": "Datacenter Equipment Test",
        "client_name": "Test Client",
        "lead_name": "Tech Lead"
    })
    proj_id = p_resp.json()["id"]

    # 2. Create Switch
    switch_resp = await client.post(f"/api/projects/{proj_id}/equipment", headers=headers, json={
        "name": "SW-CORE-01",
        "category": "switch",
        "manufacturer": "Cisco",
        "model": "Catalyst 9300-48P",
        "serial_number": "FCW2219B001",
        "management_ip": "10.0.0.1",
        "role": "Core Switch",
        "specific_attributes": {"poe_budget": 740, "stacking": True}
    })
    assert switch_resp.status_code == 201
    sw_data = switch_resp.json()
    assert sw_data["name"] == "SW-CORE-01"
    assert sw_data["category"] == "switch"
    assert sw_data["specific_attributes"]["poe_budget"] == 740
    eq_id = sw_data["id"]

    # 3. Create Server
    srv_resp = await client.post(f"/api/projects/{proj_id}/equipment", headers=headers, json={
        "name": "SRV-ESXI-01",
        "category": "physical_server",
        "manufacturer": "Dell",
        "model": "PowerEdge R750",
        "serial_number": "DELL-R750-01",
        "management_ip": "10.0.0.10",
        "role": "Hyperviseur ESXi",
        "specific_attributes": {"cpu_cores": 32, "ram_gb": 256, "storage_tb": 8.0}
    })
    assert srv_resp.status_code == 201

    # 4. List equipment
    list_resp = await client.get(f"/api/projects/{proj_id}/equipment", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # 5. Filter by category
    filter_resp = await client.get(f"/api/projects/{proj_id}/equipment?category=switch", headers=headers)
    assert filter_resp.status_code == 200
    assert len(filter_resp.json()) == 1
    assert filter_resp.json()[0]["name"] == "SW-CORE-01"

    # 6. Update equipment
    up_resp = await client.put(f"/api/equipment/{eq_id}", headers=headers, json={
        "role": "Core Switch Agrégé",
        "firmware_version": "17.9.4"
    })
    assert up_resp.status_code == 200
    assert up_resp.json()["role"] == "Core Switch Agrégé"
    assert up_resp.json()["firmware_version"] == "17.9.4"

@pytest.mark.asyncio
async def test_invalid_ip_rejection(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-INV-IP",
        "name": "Test IP Validation",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = p_resp.json()["id"]

    bad_ip_resp = await client.post(f"/api/projects/{proj_id}/equipment", headers=headers, json={
        "name": "BAD-IP-EQ",
        "category": "router",
        "management_ip": "999.999.999.999"
    })
    assert bad_ip_resp.status_code == 400
    assert "pas une adresse IPv4 valide" in bad_ip_resp.json()["detail"]

@pytest.mark.asyncio
async def test_duplicate_detection(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-DUP-01",
        "name": "Duplicate Check Test",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = p_resp.json()["id"]

    # Create two equipments with same IP and serial
    await client.post(f"/api/projects/{proj_id}/equipment", headers=headers, json={
        "name": "FW-CLUSTER-01",
        "category": "firewall",
        "serial_number": "FG100F-DUPLICATE",
        "management_ip": "192.168.1.1"
    })
    await client.post(f"/api/projects/{proj_id}/equipment", headers=headers, json={
        "name": "FW-CLUSTER-02",
        "category": "firewall",
        "serial_number": "FG100F-DUPLICATE",
        "management_ip": "192.168.1.1"
    })

    dup_resp = await client.get(f"/api/projects/{proj_id}/equipment/duplicates", headers=headers)
    assert dup_resp.status_code == 200
    dups = dup_resp.json()
    assert len(dups) >= 2
    fields_found = [d["field"] for d in dups]
    assert "serial_number" in fields_found
    assert "management_ip" in fields_found

@pytest.mark.asyncio
async def test_interface_crud_and_validations(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-INTF-01",
        "name": "Interface Test Project",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = p_resp.json()["id"]

    eq_resp = await client.post(f"/api/projects/{proj_id}/equipment", headers=headers, json={
        "name": "SWITCH-ACCESS-01",
        "category": "switch"
    })
    eq_id = eq_resp.json()["id"]

    # 1. Add valid interface
    intf_resp = await client.post(f"/api/equipment/{eq_id}/interfaces", headers=headers, json={
        "name": "GigabitEthernet1/0/1",
        "interface_type": "physical",
        "ip_address": "192.168.10.1",
        "access_vlan": 10,
        "speed_duplex": "1000/Full",
        "description": "Lien vers Firewall"
    })
    assert intf_resp.status_code == 201
    intf_data = intf_resp.json()
    assert intf_data["name"] == "GigabitEthernet1/0/1"
    assert intf_data["access_vlan"] == 10

    # 2. Invalid VLAN (> 4094)
    bad_vlan = await client.post(f"/api/equipment/{eq_id}/interfaces", headers=headers, json={
        "name": "Gi1/0/2",
        "access_vlan": 5000
    })
    assert bad_vlan.status_code in (400, 422)

    # 3. Invalid IP
    bad_ip = await client.post(f"/api/equipment/{eq_id}/interfaces", headers=headers, json={
        "name": "Gi1/0/3",
        "ip_address": "invalid-ip"
    })
    assert bad_ip.status_code in (400, 422)

@pytest.mark.asyncio
async def test_network_segment_crud(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-SEG-01",
        "name": "Segments Project",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = p_resp.json()["id"]

    # 1. Create valid VLAN
    seg_resp = await client.post(f"/api/projects/{proj_id}/segments", headers=headers, json={
        "vlan_id": 20,
        "name": "VLAN-SERVEURS",
        "cidr": "10.20.0.0/24",
        "gateway": "10.20.0.254",
        "dhcp_range": "10.20.0.100 - 10.20.0.200",
        "zone": "Production"
    })
    assert seg_resp.status_code == 201
    data = seg_resp.json()
    assert data["vlan_id"] == 20
    assert data["cidr"] == "10.20.0.0/24"

    # 2. Invalid CIDR format
    bad_cidr = await client.post(f"/api/projects/{proj_id}/segments", headers=headers, json={
        "vlan_id": 30,
        "name": "VLAN-BAD",
        "cidr": "10.20.0.500/33"
    })
    assert bad_cidr.status_code == 400

@pytest.mark.asyncio
async def test_configuration_secret_masking(client: AsyncClient, auth_tokens):
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    admin_headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}

    p_resp = await client.post("/api/projects", headers=eng_headers, json={
        "reference": "PRJ-CONF-01",
        "name": "Secret Masking Project",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = p_resp.json()["id"]

    # Add secret config (SNMP community & password)
    conf_resp = await client.post(f"/api/projects/{proj_id}/configurations", headers=eng_headers, json={
        "category": "security",
        "key": "snmp_ro_community",
        "value": "MySuperSecretCommunityString123!",
        "description": "SNMP Community for monitoring"
    })
    assert conf_resp.status_code == 201
    created_conf = conf_resp.json()
    # Value masked upon return
    assert created_conf["value"] == "<SECRET_MASQUÉ>"

    # 1. Normal list view (engineer) -> Masked
    list_resp = await client.get(f"/api/projects/{proj_id}/configurations", headers=eng_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["value"] == "<SECRET_MASQUÉ>"

    # 2. Admin unmask requested -> Raw value returned
    admin_unmask_resp = await client.get(f"/api/projects/{proj_id}/configurations?unmask=true", headers=admin_headers)
    assert admin_unmask_resp.status_code == 200
    assert admin_unmask_resp.json()[0]["value"] == "MySuperSecretCommunityString123!"

    # 3. Engineer requesting unmask -> Still masked (RBAC enforced)
    eng_unmask_resp = await client.get(f"/api/projects/{proj_id}/configurations?unmask=true", headers=eng_headers)
    assert eng_unmask_resp.status_code == 200
    assert eng_unmask_resp.json()[0]["value"] == "<SECRET_MASQUÉ>"
