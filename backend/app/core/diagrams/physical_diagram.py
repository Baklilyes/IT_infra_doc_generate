"""SVG Generator for Physical Infrastructure Architecture Diagram (Sites, Racks, Equipment)."""
import math
from datetime import datetime
from typing import Any
from app.models.project import Project, Site, Location
from app.models.equipment import Equipment
from app.core.diagrams.styles import CATEGORY_COLORS, SVG_DEFS, escape


def generate_physical_svg(project: Project, equipment_list: list[Equipment]) -> str:
    """
    Generate a professional SVG diagram of physical equipment layout grouped by site & location,
    including inter-device physical cabling links.
    """
    # 1. Group equipment by site and location
    site_groups: dict[str, dict[str, list[Equipment]]] = {}
    site_names: dict[str, str] = {}
    location_names: dict[str, str] = {}

    for eq in equipment_list:
        site_id = eq.site_id or "unassigned_site"
        site_name = eq.site.name if eq.site else "Équipements Hors Site"
        site_names[site_id] = site_name

        loc_id = eq.location_id or "unassigned_location"
        loc_name = eq.location.name if eq.location else "Emplacement Général"
        location_names[loc_id] = loc_name

        if site_id not in site_groups:
            site_groups[site_id] = {}
        if loc_id not in site_groups[site_id]:
            site_groups[site_id][loc_id] = []
        site_groups[site_id][loc_id].append(eq)

    # 2. Dimensions and coordinate calculations
    CARD_W = 220
    CARD_H = 80
    CARD_PAD_X = 20
    CARD_PAD_Y = 15

    LOC_PAD = 15
    LOC_HEADER_H = 30
    SITE_PAD = 25
    SITE_HEADER_H = 45

    current_y = 120  # Below title banner
    max_total_w = 1200
    equipment_positions: dict[str, tuple[float, float, float, float]] = {}  # id -> (x, y, w, h)

    site_blocks = []

    for site_id, loc_dict in site_groups.items():
        site_name = site_names[site_id]
        site_start_y = current_y

        loc_blocks = []
        current_loc_y = site_start_y + SITE_HEADER_H + 10
        max_site_w = 0

        for loc_id, eq_items in loc_dict.items():
            loc_name = location_names[loc_id]
            # Layout equipment in 2 columns if more than 3 items
            cols = 2 if len(eq_items) > 3 else 1
            rows = math.ceil(len(eq_items) / cols)

            loc_w = cols * (CARD_W + CARD_PAD_X) + (LOC_PAD * 2) - CARD_PAD_X
            loc_h = LOC_HEADER_H + (rows * (CARD_H + CARD_PAD_Y)) + LOC_PAD

            if loc_w > max_site_w:
                max_site_w = loc_w

            eq_cards = []
            for idx, eq in enumerate(eq_items):
                col_idx = idx % cols
                row_idx = idx // cols
                eq_x = 40 + (col_idx * (CARD_W + CARD_PAD_X))
                eq_y = current_loc_y + LOC_HEADER_H + (row_idx * (CARD_H + CARD_PAD_Y))

                equipment_positions[eq.id] = (eq_x, eq_y, CARD_W, CARD_H)
                eq_cards.append((eq, eq_x, eq_y))

            loc_blocks.append({
                "name": loc_name,
                "y": current_loc_y,
                "w": loc_w,
                "h": loc_h,
                "cards": eq_cards
            })

            current_loc_y += loc_h + 15

        site_h = (current_loc_y - site_start_y) + 10
        site_w = max(max_site_w + 50, 600)
        if site_w > max_total_w:
            max_total_w = site_w

        site_blocks.append({
            "name": site_name,
            "y": site_start_y,
            "w": site_w,
            "h": site_h,
            "locations": loc_blocks
        })

        current_y = current_loc_y + 25

    TOTAL_SVG_W = max(max_total_w + 80, 1100)
    TOTAL_SVG_H = current_y + 100

    # 3. Assemble SVG Output
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TOTAL_SVG_W} {TOTAL_SVG_H}" width="100%" height="100%" style="background-color: #f8fafc; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;">')
    svg.append(SVG_DEFS)

    # Header Banner
    svg.append(f'''
    <!-- Diagram Header -->
    <rect x="20" y="20" width="{TOTAL_SVG_W - 40}" height="75" rx="12" fill="url(#header-grad)" filter="url(#shadow-md)" />
    <text x="45" y="52" fill="#ffffff" font-size="20" font-weight="700">Schéma d\'Infrastructure Physique &amp; Implantation</text>
    <text x="45" y="74" fill="#94a3b8" font-size="12">Projet : <tspan fill="#38bdf8" font-weight="600">{escape(project.reference)} - {escape(project.name)}</tspan> | Client : <tspan fill="#cbd5e1">{escape(project.client_name)}</tspan> | Date : {datetime.now().strftime("%d/%m/%Y")}</text>
    <rect x="{TOTAL_SVG_W - 200}" y="38" width="155" height="36" rx="6" fill="#1e293b" stroke="#334155" />
    <text x="{TOTAL_SVG_W - 122}" y="61" fill="#38bdf8" font-size="12" font-weight="600" text-anchor="middle">{len(equipment_list)} Équipements</text>
    ''')

    # Sites and Location Containers
    for s_block in site_blocks:
        svg.append(f'''
        <!-- Site Container -->
        <g class="site-group">
          <rect x="25" y="{s_block['y']}" width="{s_block['w']}" height="{s_block['h']}" rx="14" fill="url(#site-grad)" stroke="#cbd5e1" stroke-width="2" filter="url(#shadow)" />
          <path d="M 25 {s_block['y'] + SITE_HEADER_H} L {25 + s_block['w']} {s_block['y'] + SITE_HEADER_H}" stroke="#e2e8f0" stroke-width="1.5" />
          <circle cx="50" cy="{s_block['y'] + 22}" r="10" fill="#2563eb" />
          <text x="50" y="{s_block['y'] + 26}" fill="#ffffff" font-size="10" font-weight="700" text-anchor="middle">S</text>
          <text x="70" y="{s_block['y'] + 27}" fill="#0f172a" font-size="14" font-weight="700">Site : {escape(s_block['name'])}</text>
        ''')

        for l_block in s_block["locations"]:
            svg.append(f'''
            <!-- Location Container -->
            <rect x="35" y="{l_block['y']}" width="{l_block['w']}" height="{l_block['h']}" rx="10" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" />
            <text x="50" y="{l_block['y'] + 20}" fill="#475569" font-size="12" font-weight="600">Baie / Emplacement : {escape(l_block['name'])}</text>
            ''')

            for eq, eq_x, eq_y in l_block["cards"]:
                cat_info = CATEGORY_COLORS.get(eq.category.value, CATEGORY_COLORS["generic"])
                ip_label = eq.management_ip if eq.management_ip else "IP Non assignée"

                svg.append(f'''
                <!-- Equipment Card -->
                <g class="equipment-card" id="card-{eq.id}">
                  <rect x="{eq_x}" y="{eq_y}" width="{CARD_W}" height="{CARD_H}" rx="8" fill="{cat_info['fill']}" stroke="{cat_info['stroke']}" stroke-width="1.5" filter="url(#shadow)" />
                  <!-- Header bar -->
                  <rect x="{eq_x}" y="{eq_y}" width="{CARD_W}" height="24" rx="8" fill="{cat_info['stroke']}" />
                  <rect x="{eq_x}" y="{eq_y + 16}" width="{CARD_W}" height="8" fill="{cat_info['stroke']}" />
                  
                  <!-- Device Name -->
                  <text x="{eq_x + 10}" y="{eq_y + 16}" fill="#ffffff" font-size="11" font-weight="700">{escape(eq.name)}</text>
                  <text x="{eq_x + CARD_W - 10}" y="{eq_y + 16}" fill="#ffffff" font-size="9" font-weight="600" text-anchor="end">{escape(cat_info['badge'])}</text>

                  <!-- Details -->
                  <text x="{eq_x + 10}" y="{eq_y + 42}" fill="#334155" font-size="10" font-weight="500">{escape(eq.model or eq.manufacturer or 'Modèle standard')}</text>
                  
                  <!-- Management IP pill -->
                  <rect x="{eq_x + 10}" y="{eq_y + 53}" width="120" height="18" rx="4" fill="#ffffff" stroke="#cbd5e1" />
                  <circle cx="{eq_x + 18}" cy="{eq_y + 62}" r="3" fill="#16a34a" />
                  <text x="{eq_x + 26}" y="{eq_y + 66}" fill="#0f172a" font-size="9" font-family="monospace">{escape(ip_label)}</text>
                  
                  {f'<text x="{eq_x + CARD_W - 10}" y="{eq_y + 66}" fill="#64748b" font-size="8" text-anchor="end">S/N: {escape(eq.serial_number[:10])}</text>' if eq.serial_number else ''}
                </g>
                ''')

        svg.append('</g>')

    # 4. Inter-Equipment Cabling Links
    drawn_links = set()
    svg.append('<g class="cabling-links">')
    for eq in equipment_list:
        for iface in eq.interfaces:
            if iface.connected_equipment_id and iface.connected_equipment_id in equipment_positions:
                target_id = iface.connected_equipment_id
                pair_key = tuple(sorted([eq.id, target_id]))
                if pair_key in drawn_links:
                    continue
                drawn_links.add(pair_key)

                src_x, src_y, src_w, src_h = equipment_positions[eq.id]
                dst_x, dst_y, dst_w, dst_h = equipment_positions[target_id]

                # Center points
                x1 = src_x + src_w
                y1 = src_y + (src_h / 2)
                x2 = dst_x
                y2 = dst_y + (dst_h / 2)

                # Curved bezier path
                cx1 = x1 + 40
                cy1 = y1
                cx2 = x2 - 40
                cy2 = y2

                link_desc = iface.link_type or iface.name

                svg.append(f'''
                <!-- Cabling Link -->
                <path d="M {x1} {y1} C {cx1} {cy1}, {cx2} {cy2}, {x2} {y2}" fill="none" stroke="#2563eb" stroke-width="2" stroke-dasharray="4,2" marker-end="url(#arrow-blue)" />
                <rect x="{(x1 + x2)/2 - 35}" y="{(y1 + y2)/2 - 10}" width="70" height="18" rx="4" fill="#ffffff" stroke="#93c5fd" />
                <text x="{(x1 + x2)/2}" y="{(y1 + y2)/2 + 3}" fill="#1e40af" font-size="8" font-weight="600" text-anchor="middle">{escape(link_desc)}</text>
                ''')

    svg.append('</g>')

    # 5. Legend at the bottom
    legend_y = TOTAL_SVG_H - 45
    svg.append(f'''
    <!-- Legend -->
    <g class="diagram-legend">
      <rect x="25" y="{legend_y}" width="{TOTAL_SVG_W - 50}" height="32" rx="6" fill="#ffffff" stroke="#e2e8f0" />
      <text x="40" y="{legend_y + 20}" fill="#475569" font-size="10" font-weight="700">Légende :</text>
    ''')

    lx = 110
    for cat_name, cat_style in [("Switch", CATEGORY_COLORS["switch"]), ("Routeur", CATEGORY_COLORS["router"]), ("Pare-feu", CATEGORY_COLORS["firewall"]), ("Serveur", CATEGORY_COLORS["physical_server"]), ("Stockage", CATEGORY_COLORS["storage"])]:
        svg.append(f'''
        <rect x="{lx}" y="{legend_y + 8}" width="14" height="14" rx="3" fill="{cat_style['stroke']}" />
        <text x="{lx + 20}" y="{legend_y + 19}" fill="#334155" font-size="9" font-weight="500">{cat_name}</text>
        ''')
        lx += 110

    svg.append('</g>')
    svg.append('</svg>')

    return "\n".join(svg)
