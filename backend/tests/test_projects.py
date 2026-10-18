import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project_success(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    payload = {
        "reference": "PRJ-2026-TEST01",
        "name": "Datacenter Migration Alpha",
        "client_name": "Acme Corp",
        "description": "Migration d'infrastructure vers nouveau site",
        "scope": "Switches, Firewalls, Hyperviseurs",
        "lead_name": "Jean Dupont",
        "contributors": "Alice, Bob",
        "status": "draft",
        "document_language": "fr",
        "initial_site_name": "Siège Principal Paris"
    }
    resp = await client.post("/api/projects", headers=headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["reference"] == "PRJ-2026-TEST01"
    assert data["name"] == "Datacenter Migration Alpha"
    assert data["client_name"] == "Acme Corp"
    assert data["status"] == "draft"
    assert len(data["sites"]) == 1
    assert data["sites"][0]["name"] == "Siège Principal Paris"
    assert data["sites_count"] == 1

@pytest.mark.asyncio
async def test_create_project_duplicate_reference(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    payload = {
        "reference": "PRJ-DUP-REF",
        "name": "Projet A",
        "client_name": "Client 1",
        "lead_name": "Tech Lead"
    }
    resp1 = await client.post("/api/projects", headers=headers, json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/projects", headers=headers, json=payload)
    assert resp2.status_code == 400
    assert "existe déjà" in resp2.json()["detail"]

@pytest.mark.asyncio
async def test_list_and_filter_projects(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    # Create two projects
    await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-LIST-01",
        "name": "Network Redesign",
        "client_name": "Global Bank",
        "lead_name": "Alex"
    })
    await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-LIST-02",
        "name": "Cloud Interconnect",
        "client_name": "Global Tech",
        "lead_name": "Sophie"
    })

    # Search by client
    resp = await client.get("/api/projects?search=Bank", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(p["client_name"] == "Global Bank" for p in data)

@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    create_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-UPDATE-01",
        "name": "Initial Name",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = create_resp.json()["id"]

    update_resp = await client.put(f"/api/projects/{proj_id}", headers=headers, json={
        "name": "Updated Name",
        "status": "in_preparation",
        "scope": "LAN + WAN Redundancy"
    })
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Updated Name"
    assert data["status"] == "in_preparation"
    assert data["scope"] == "LAN + WAN Redundancy"

@pytest.mark.asyncio
async def test_duplicate_project_isolation(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    # 1. Create project with site and location
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-ORIG-01",
        "name": "Projet Usine Lyon",
        "client_name": "Groupe Industriel",
        "lead_name": "Ingénieur A",
        "initial_site_name": "Site Usine"
    })
    p_data = p_resp.json()
    orig_proj_id = p_data["id"]
    orig_site_id = p_data["sites"][0]["id"]

    # Add location to site
    loc_resp = await client.post(f"/api/sites/{orig_site_id}/locations", headers=headers, json={
        "name": "Local Informatique Bâtiment B",
        "room": "B104",
        "rack": "Baie 42U"
    })
    assert loc_resp.status_code == 201

    # 2. Duplicate project
    dup_resp = await client.post(f"/api/projects/{orig_proj_id}/duplicate", headers=headers, json={
        "new_reference": "PRJ-CLONE-01",
        "new_name": "Projet Usine Lyon - Copie Test"
    })
    assert dup_resp.status_code == 201
    dup_data = dup_resp.json()

    # Verify new UUIDs and isolated structure
    assert dup_data["id"] != orig_proj_id
    assert dup_data["reference"] == "PRJ-CLONE-01"
    assert dup_data["status"] == "draft"  # Reset to draft
    assert len(dup_data["sites"]) == 1
    assert dup_data["sites"][0]["id"] != orig_site_id
    assert dup_data["sites"][0]["name"] == "Site Usine"
    assert len(dup_data["sites"][0]["locations"]) == 1
    assert dup_data["sites"][0]["locations"][0]["name"] == "Local Informatique Bâtiment B"

@pytest.mark.asyncio
async def test_archive_toggle_project(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-ARCH-01",
        "name": "Projet à Archiver",
        "client_name": "Client",
        "lead_name": "Lead"
    })
    proj_id = p_resp.json()["id"]

    # Toggle archive -> True
    arch_resp = await client.post(f"/api/projects/{proj_id}/archive", headers=headers)
    assert arch_resp.status_code == 200
    assert arch_resp.json()["is_archived"] is True

    # Not in active list
    active_list = (await client.get("/api/projects", headers=headers)).json()
    assert not any(p["id"] == proj_id for p in active_list)

    # In archived list
    arch_list = (await client.get("/api/projects?is_archived=true", headers=headers)).json()
    assert any(p["id"] == proj_id for p in arch_list)

@pytest.mark.asyncio
async def test_sites_and_locations_crud(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-SITES-01",
        "name": "Multi-sites Project",
        "client_name": "Enterprise",
        "lead_name": "Engineer Lead"
    })
    proj_id = p_resp.json()["id"]

    # Add site 1
    s1_resp = await client.post(f"/api/projects/{proj_id}/sites", headers=headers, json={
        "name": "Site Marseille",
        "code": "MRS-01",
        "city": "Marseille"
    })
    assert s1_resp.status_code == 201
    s1_id = s1_resp.json()["id"]

    # Add location to site 1
    loc_resp = await client.post(f"/api/sites/{s1_id}/locations", headers=headers, json={
        "name": "Salle Serveurs RDC",
        "room": "RDC-01"
    })
    assert loc_resp.status_code == 201
    loc_id = loc_resp.json()["id"]

    # Update location
    up_loc_resp = await client.put(f"/api/locations/{loc_id}", headers=headers, json={
        "rack": "Baie Schneider 42U"
    })
    assert up_loc_resp.status_code == 200
    assert up_loc_resp.json()["rack"] == "Baie Schneider 42U"

    # Delete location
    del_loc = await client.delete(f"/api/locations/{loc_id}", headers=headers)
    assert del_loc.status_code == 204

    # Delete site
    del_site = await client.delete(f"/api/sites/{s1_id}", headers=headers)
    assert del_site.status_code == 204

@pytest.mark.asyncio
async def test_delete_project_cascades(client: AsyncClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
    p_resp = await client.post("/api/projects", headers=headers, json={
        "reference": "PRJ-CASCADE-01",
        "name": "To be deleted",
        "client_name": "Client",
        "lead_name": "Lead",
        "initial_site_name": "Site Cascadé"
    })
    proj_id = p_resp.json()["id"]

    del_resp = await client.delete(f"/api/projects/{proj_id}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/projects/{proj_id}", headers=headers)
    assert get_resp.status_code == 404
