"""Styles, color palettes, and SVG graphic definitions for architecture diagrams."""
import html

CATEGORY_COLORS = {
    "switch": {"fill": "#eff6ff", "stroke": "#3b82f6", "header": "#1d4ed8", "text": "#1e3a8a", "badge": "Switch"},
    "router": {"fill": "#faf5ff", "stroke": "#a855f7", "header": "#7e22ce", "text": "#581c87", "badge": "Routeur"},
    "firewall": {"fill": "#fff7ed", "stroke": "#f97316", "header": "#c2410c", "text": "#7c2d12", "badge": "Pare-feu"},
    "physical_server": {"fill": "#f0fdf4", "stroke": "#22c55e", "header": "#15803d", "text": "#14532d", "badge": "Serveur"},
    "hypervisor": {"fill": "#f0fdfa", "stroke": "#14b8a6", "header": "#0f766e", "text": "#134e4a", "badge": "Hyperviseur"},
    "virtual_machine": {"fill": "#f5f3ff", "stroke": "#8b5cf6", "header": "#6d28d9", "text": "#4c1d95", "badge": "VM"},
    "storage": {"fill": "#fffbeb", "stroke": "#f59e0b", "header": "#b45309", "text": "#78350f", "badge": "Stockage"},
    "wifi": {"fill": "#fdf2f8", "stroke": "#ec4899", "header": "#be185d", "text": "#831843", "badge": "WiFi AP"},
    "generic": {"fill": "#f8fafc", "stroke": "#94a3b8", "header": "#475569", "text": "#1e293b", "badge": "Équipement"}
}

ZONE_COLORS = {
    "lan": {"fill": "#f0fdf4", "stroke": "#16a34a", "badge": "#15803d", "title": "Zone Utilisateurs & Bureautique (LAN)"},
    "voice": {"fill": "#fdf2f8", "stroke": "#db2777", "badge": "#be185d", "title": "Zone Téléphonie & VoIP"},
    "dmz": {"fill": "#fff7ed", "stroke": "#ea580c", "badge": "#c2410c", "title": "Zone Démilitarisée (DMZ)"},
    "servers": {"fill": "#eff6ff", "stroke": "#2563eb", "badge": "#1d4ed8", "title": "Zone Serveurs & Applications"},
    "mgmt": {"fill": "#faf5ff", "stroke": "#9333ea", "badge": "#7e22ce", "title": "Zone Administration & Management (OOB)"},
    "wifi": {"fill": "#ecfeff", "stroke": "#0891b2", "badge": "#0e7490", "title": "Zone Accès Sans Fil (WiFi)"},
    "wan": {"fill": "#fef2f2", "stroke": "#dc2626", "badge": "#b91c1c", "title": "Zone Opérateur & Internet (WAN)"},
    "default": {"fill": "#f8fafc", "stroke": "#64748b", "badge": "#475569", "title": "Zone Réseau"}
}

SVG_DEFS = """
  <defs>
    <!-- Arrow Marker for Link Direction -->
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#475569" />
    </marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#2563eb" />
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#16a34a" />
    </marker>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#ea580c" />
    </marker>
    
    <!-- Drop Shadow Filter -->
    <filter id="shadow" x="-5%" y="-5%" width="115%" height="115%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.07" />
    </filter>
    <filter id="shadow-md" x="-8%" y="-8%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#0f172a" flood-opacity="0.12" />
    </filter>

    <!-- Linear Gradients -->
    <linearGradient id="header-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <linearGradient id="site-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#f8fafc" />
    </linearGradient>
  </defs>
"""


def escape(text: str | None) -> str:
    """Escape XML characters for SVG text attributes."""
    if text is None:
        return ""
    return html.escape(str(text))


def get_zone_style(zone_name: str | None) -> dict:
    """Retrieve color palette based on zone name keywords."""
    if not zone_name:
        return ZONE_COLORS["default"]
    low = zone_name.lower()
    for key in ["dmz", "lan", "voice", "voip", "server", "mgmt", "admin", "wifi", "wan"]:
        if key in low:
            if key in ["voice", "voip"]:
                return ZONE_COLORS["voice"]
            if key in ["mgmt", "admin"]:
                return ZONE_COLORS["mgmt"]
            if key == "server":
                return ZONE_COLORS["servers"]
            return ZONE_COLORS.get(key, ZONE_COLORS["default"])
    return ZONE_COLORS["default"]
