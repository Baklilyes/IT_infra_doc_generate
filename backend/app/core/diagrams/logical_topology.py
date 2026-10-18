"""SVG Generator for Logical Network Topology (VLANs, Subnets, Routing & Security Zones)."""
import math
from datetime import datetime
from app.models.project import Project
from app.models.equipment import Equipment, EquipmentCategory
from app.models.network import NetworkSegment
from app.core.diagrams.styles import ZONE_COLORS, CATEGORY_COLORS, SVG_DEFS, escape, get_zone_style


def generate_logical_svg(
    project: Project,
    equipment_list: list[Equipment],
    segments: list[NetworkSegment]
) -> str:
    """
    Generate a professional SVG diagram of the logical network topology,
    showing routing layer, security firewalls, VLAN segments, and host assignments.
    """
    # 1. Identify Core / Router / Firewall devices
    routers_and_firewalls = [
        e for e in equipment_list if e.category in [EquipmentCategory.ROUTER, EquipmentCategory.FIREWALL, EquipmentCategory.SWITCH]
    ]
    core_devices = routers_and_firewalls[:3] if routers_and_firewalls else equipment_list[:1]

    # Map VLAN to equipment connected
    vlan_members: dict[int, list[tuple[Equipment, str]]] = {}
    for eq in equipment_list:
        for iface in eq.interfaces:
            if iface.access_vlan:
                vlan_members.setdefault(iface.access_vlan, []).append((eq, iface.name))

    # Dimensions
    TOTAL_W = 1200
    HEADER_H = 80
    ROUTER_Y = 120
    ROUTER_BOX_W = 220
    ROUTER_BOX_H = 75

    # Layout Core Devices at top
    core_positions: list[tuple[Equipment, float, float]] = []
    num_cores = max(len(core_devices), 1)
    spacing = TOTAL_W / (num_cores + 1)
    for idx, dev in enumerate(core_devices):
        x = spacing * (idx + 1) - (ROUTER_BOX_W / 2)
        y = ROUTER_Y
        core_positions.append((dev, x, y))

    # Layout VLAN Segment Cards in a grid below
    SEG_START_Y = ROUTER_Y + ROUTER_BOX_H + 80
    SEG_W = 340
    SEG_H = 160
    COLS = 3
    GAP_X = 35
    GAP_Y = 30

    num_segs = len(segments)
    rows = math.ceil(max(num_segs, 1) / COLS)
    TOTAL_H = SEG_START_Y + (rows * (SEG_H + GAP_Y)) + 120

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TOTAL_W} {TOTAL_H}" width="100%" height="100%" style="background-color: #f8fafc; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;">')
    svg.append(SVG_DEFS)

    # 1. Header Banner
    svg.append(f'''
    <!-- Header -->
    <rect x="20" y="20" width="{TOTAL_W - 40}" height="75" rx="12" fill="url(#header-grad)" filter="url(#shadow-md)" />
    <text x="45" y="52" fill="#ffffff" font-size="20" font-weight="700">Topologie Réseau Logique &amp; Segmentation VLAN</text>
    <text x="45" y="74" fill="#94a3b8" font-size="12">Projet : <tspan fill="#38bdf8" font-weight="600">{escape(project.reference)} - {escape(project.name)}</tspan> | {len(segments)} Segments / VLANs déclarés</text>
    <rect x="{TOTAL_W - 200}" y="38" width="160" height="36" rx="6" fill="#1e293b" stroke="#334155" />
    <text x="{TOTAL_W - 120}" y="61" fill="#38bdf8" font-size="12" font-weight="600" text-anchor="middle">Routage &amp; Sécurité</text>
    ''')

    # 2. Render Core / Routing Nodes
    core_bottom_centers = []
    for dev, cx, cy in core_positions:
        cat_style = CATEGORY_COLORS.get(dev.category.value, CATEGORY_COLORS["router"])
        svg.append(f'''
        <!-- Core Node -->
        <g class="core-node" id="core-{dev.id}">
          <rect x="{cx}" y="{cy}" width="{ROUTER_BOX_W}" height="{ROUTER_BOX_H}" rx="10" fill="{cat_style['fill']}" stroke="{cat_style['stroke']}" stroke-width="2" filter="url(#shadow-md)" />
          <rect x="{cx}" y="{cy}" width="{ROUTER_BOX_W}" height="24" rx="10" fill="{cat_style['stroke']}" />
          <rect x="{cx}" y="{cy + 16}" width="{ROUTER_BOX_W}" height="8" fill="{cat_style['stroke']}" />
          <text x="{cx + 10}" y="{cy + 16}" fill="#ffffff" font-size="11" font-weight="700">{escape(dev.name)}</text>
          <text x="{cx + ROUTER_BOX_W - 10}" y="{cy + 16}" fill="#ffffff" font-size="9" font-weight="600" text-anchor="end">Cœur / Routage</text>
          <text x="{cx + 10}" y="{cy + 42}" fill="#334155" font-size="10">{escape(dev.model or dev.role or 'Niveau L3 / Sécurité')}</text>
          <rect x="{cx + 10}" y="{cy + 50}" width="120" height="16" rx="3" fill="#ffffff" stroke="#cbd5e1" />
          <text x="{cx + 18}" y="{cy + 62}" fill="#0f172a" font-size="9" font-family="monospace">IP: {escape(dev.management_ip or 'Passerelle L3')}</text>
        </g>
        ''')
        core_bottom_centers.append((cx + ROUTER_BOX_W / 2, cy + ROUTER_BOX_H))

    # 3. Render VLAN Segments & Connecting Trunks
    svg.append('<g class="segments-grid">')
    for idx, seg in enumerate(segments):
        col = idx % COLS
        row = idx // COLS
        sx = 45 + col * (SEG_W + GAP_X)
        sy = SEG_START_Y + row * (SEG_H + GAP_Y)

        zone_style = get_zone_style(seg.zone or seg.name)
        members = vlan_members.get(seg.vlan_id, [])

        # Draw Trunk Link from primary core node down to this segment
        if core_bottom_centers:
            # Pick closest core router
            closest_core = min(core_bottom_centers, key=lambda c: abs(c[0] - (sx + SEG_W / 2)))
            link_x1 = closest_core[0]
            link_y1 = closest_core[1]
            link_x2 = sx + SEG_W / 2
            link_y2 = sy

            svg.append(f'''
            <!-- Trunk Line -->
            <path d="M {link_x1} {link_y1} C {link_x1} {link_y1 + 35}, {link_x2} {link_y2 - 35}, {link_x2} {link_y2}" fill="none" stroke="{zone_style['stroke']}" stroke-width="2" stroke-dasharray="3,2" marker-end="url(#arrow)" />
            ''')

        svg.append(f'''
        <!-- VLAN Segment Box -->
        <g class="vlan-segment" id="vlan-{seg.vlan_id}">
          <rect x="{sx}" y="{sy}" width="{SEG_W}" height="{SEG_H}" rx="10" fill="{zone_style['fill']}" stroke="{zone_style['stroke']}" stroke-width="2" filter="url(#shadow)" />
          
          <!-- Segment Header -->
          <rect x="{sx}" y="{sy}" width="{SEG_W}" height="28" rx="10" fill="{zone_style['badge']}" />
          <rect x="{sx}" y="{sy + 20}" width="{SEG_W}" height="8" fill="{zone_style['badge']}" />
          
          <text x="{sx + 10}" y="{sy + 18}" fill="#ffffff" font-size="11" font-weight="700">VLAN {seg.vlan_id} : {escape(seg.name)}</text>
          <text x="{sx + SEG_W - 10}" y="{sy + 18}" fill="#ffffff" font-size="9" font-weight="600" text-anchor="end">{escape(seg.zone or 'LAN')}</text>

          <!-- Subnet & Gateway Meta -->
          <rect x="{sx + 10}" y="{sy + 36}" width="{SEG_W - 20}" height="32" rx="6" fill="#ffffff" stroke="#e2e8f0" />
          <text x="{sx + 18}" y="{sy + 50}" fill="#475569" font-size="9">Sous-réseau : <tspan fill="#0f172a" font-weight="700" font-family="monospace">{escape(seg.cidr or 'Non défini')}</tspan></text>
          <text x="{sx + 18}" y="{sy + 63}" fill="#475569" font-size="9">Passerelle : <tspan fill="#16a34a" font-weight="700" font-family="monospace">{escape(seg.gateway or 'SVI non renseigné')}</tspan></text>

          <!-- Members List -->
          <text x="{sx + 12}" y="{sy + 84}" fill="#334155" font-size="10" font-weight="700">Équipements &amp; Hôtes rattachés ({len(members)}) :</text>
          <g transform="translate({sx + 10}, {sy + 92})">
        ''')

        if not members:
            svg.append('<text x="5" y="20" fill="#94a3b8" font-size="9" font-style="italic">Aucun équipement actuellement assigné</text>')
        else:
            for m_idx, (m_eq, m_if_name) in enumerate(members[:3]):
                my = m_idx * 18 + 12
                svg.append(f'''
                <circle cx="6" cy="{my - 3}" r="3" fill="{zone_style['stroke']}" />
                <text x="15" y="{my}" fill="#1e293b" font-size="9" font-weight="600">{escape(m_eq.name)} <tspan fill="#64748b" font-weight="normal">({escape(m_if_name)})</tspan></text>
                ''')
            if len(members) > 3:
                svg.append(f'<text x="15" y="62" fill="#64748b" font-size="8" font-style="italic">+ {len(members) - 3} autres hôtes...</text>')

        svg.append('</g></g>')

    svg.append('</g>')

    # 4. Legend
    legend_y = TOTAL_H - 45
    svg.append(f'''
    <!-- Legend -->
    <g class="diagram-legend">
      <rect x="25" y="{legend_y}" width="{TOTAL_W - 50}" height="32" rx="6" fill="#ffffff" stroke="#e2e8f0" />
      <text x="40" y="{legend_y + 20}" fill="#475569" font-size="10" font-weight="700">Zones de Sécurité :</text>
      <rect x="180" y="{legend_y + 8}" width="14" height="14" rx="3" fill="#16a34a" />
      <text x="200" y="{legend_y + 19}" fill="#334155" font-size="9">Zone LAN</text>
      <rect x="300" y="{legend_y + 8}" width="14" height="14" rx="3" fill="#ea580c" />
      <text x="320" y="{legend_y + 19}" fill="#334155" font-size="9">Zone DMZ</text>
      <rect x="420" y="{legend_y + 8}" width="14" height="14" rx="3" fill="#db2777" />
      <text x="440" y="{legend_y + 19}" fill="#334155" font-size="9">Zone Voix / VoIP</text>
      <rect x="560" y="{legend_y + 8}" width="14" height="14" rx="3" fill="#9333ea" />
      <text x="580" y="{legend_y + 19}" fill="#334155" font-size="9">Zone Management</text>
      <rect x="720" y="{legend_y + 8}" width="14" height="14" rx="3" fill="#2563eb" />
      <text x="740" y="{legend_y + 19}" fill="#334155" font-size="9">Zone Serveurs</text>
    </g>
    ''')

    svg.append('</svg>')
    return "\n".join(svg)
