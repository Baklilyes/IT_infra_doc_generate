"""SVG Generator for Application and Inter-Zone Flow Matrix Diagrams (Ports, Protocols, Traffic Direction)."""
from datetime import datetime
from app.models.project import Project
from app.models.network import NetworkSegment
from app.core.diagrams.styles import SVG_DEFS, escape

STANDARD_FLOWS = [
    {"src": "Zone Utilisateurs (LAN)", "dst": "Zone Serveurs (Apps)", "proto": "TCP 443 (HTTPS) / 80", "direction": "Uni-directionnel", "action": "Autorisé"},
    {"src": "Zone Utilisateurs (LAN)", "dst": "Zone Serveurs (Apps)", "proto": "TCP 3389 (RDP)", "direction": "Uni-directionnel", "action": "Filtré / MFA"},
    {"src": "Zone Utilisateurs (LAN)", "dst": "Zone Voix (VoIP)", "proto": "UDP 5060 (SIP) / RTP 10000-20000", "direction": "Bi-directionnel", "action": "Autorisé"},
    {"src": "Zone DMZ Publique", "dst": "Zone Serveurs (Apps)", "proto": "TCP 1433 / 5432 (Bases de données)", "direction": "Uni-directionnel", "action": "Filtré strict"},
    {"src": "Zone Management (OOB)", "dst": "Toutes Zones", "proto": "TCP 22 (SSH) / HTTPS", "direction": "Supervision / Admin", "action": "Autorisé OOB"},
    {"src": "Zone Serveurs (Apps)", "dst": "Zone WAN / Internet", "proto": "TCP 443 (Mises à jour API/OS)", "direction": "Sortant exclusif", "action": "Proxy / Filtré"},
]


def generate_flow_svg(project: Project, segments: list[NetworkSegment]) -> str:
    """
    Generate an Application & Security Flow SVG matrix diagram detailing inter-zone protocols and ports.
    """
    TOTAL_W = 1100
    HEADER_H = 80
    ROW_H = 45
    TABLE_Y = 120
    NUM_ROWS = len(STANDARD_FLOWS)
    TOTAL_H = TABLE_Y + (NUM_ROWS * ROW_H) + 120

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TOTAL_W} {TOTAL_H}" width="100%" height="100%" style="background-color: #f8fafc; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;">')
    svg.append(SVG_DEFS)

    # Header
    svg.append(f'''
    <!-- Header -->
    <rect x="20" y="20" width="{TOTAL_W - 40}" height="75" rx="12" fill="url(#header-grad)" filter="url(#shadow-md)" />
    <text x="45" y="52" fill="#ffffff" font-size="20" font-weight="700">Matrice des Flux Applicatifs &amp; Règles Inter-Zones</text>
    <text x="45" y="74" fill="#94a3b8" font-size="12">Projet : <tspan fill="#38bdf8" font-weight="600">{escape(project.reference)} - {escape(project.name)}</tspan> | Politiques de sécurité et d\'ouverture de ports</text>
    ''')

    # Table Header
    cols = [
        ("Zone Source", 40, 220),
        ("Sens", 260, 100),
        ("Zone Destination", 360, 220),
        ("Protocole & Ports", 580, 260),
        ("Politique de Sécurité", 840, 210)
    ]

    svg.append(f'''
    <!-- Flow Table Container -->
    <g class="flow-table">
      <rect x="30" y="{TABLE_Y}" width="{TOTAL_W - 60}" height="35" rx="8" fill="#1e293b" />
    ''')

    for title, x, _ in cols:
        svg.append(f'<text x="{x + 10}" y="{TABLE_Y + 22}" fill="#f1f5f9" font-size="11" font-weight="700">{title}</text>')

    svg.append('</g>')

    # Table Rows
    current_y = TABLE_Y + 45
    for idx, flow in enumerate(STANDARD_FLOWS):
        bg_color = "#ffffff" if idx % 2 == 0 else "#f8fafc"
        action_color = "#16a34a" if "Autorisé" in flow["action"] else ("#ea580c" if "Filtré" in flow["action"] else "#2563eb")
        
        svg.append(f'''
        <g class="flow-row" transform="translate(30, {current_y})">
          <rect x="0" y="0" width="{TOTAL_W - 60}" height="{ROW_H - 5}" rx="6" fill="{bg_color}" stroke="#e2e8f0" />
          <text x="20" y="25" fill="#0f172a" font-size="11" font-weight="600">{escape(flow["src"])}</text>
          <g transform="translate(240, 12)">
            <path d="M 0 8 L 60 8" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />
          </g>
          <text x="340" y="25" fill="#0f172a" font-size="11" font-weight="600">{escape(flow["dst"])}</text>
          <rect x="560" y="8" width="240" height="24" rx="4" fill="#f1f5f9" stroke="#cbd5e1" />
          <text x="570" y="24" fill="#334155" font-size="10" font-family="monospace" font-weight="600">{escape(flow["proto"])}</text>
          <rect x="820" y="8" width="180" height="24" rx="4" fill="{action_color}15" stroke="{action_color}" />
          <text x="830" y="24" fill="{action_color}" font-size="10" font-weight="700">{escape(flow["action"])}</text>
        </g>
        ''')
        current_y += ROW_H

    # Footer Notice
    svg.append(f'''
    <g class="flow-footer">
      <rect x="30" y="{current_y + 10}" width="{TOTAL_W - 60}" height="35" rx="6" fill="#eff6ff" stroke="#bfdbfe" />
      <text x="50" y="{current_y + 32}" fill="#1e40af" font-size="10" font-weight="500">Note de sécurité : Tout flux non explicitement autorisé ci-dessus est interdit par défaut (Règle implicite "Deny All" sur les pare-feux de périmètre).</text>
    </g>
    ''')

    svg.append('</svg>')
    return "\n".join(svg)
