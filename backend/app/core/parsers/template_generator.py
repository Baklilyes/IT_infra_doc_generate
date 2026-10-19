"""Excel Template Generator for Tabular Imports (Equipment, VLANs/Segments)."""
import io
from typing import Literal
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

# Styling definitions
HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Dark Slate Blue
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
GUIDE_HEADER_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
ROW_ALT_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
BORDER_THIN = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)
CELL_FONT = Font(name="Calibri", size=10, color="0F172A")
CODE_FONT = Font(name="Consolas", size=10, color="0F172A")


def _apply_sheet_formatting(ws, headers: list[str], rows: list[list[any]], comments: dict[str, str] = None):
    """Apply styling, borders, comments, and column auto-sizing to a worksheet."""
    ws.views.sheetView[0].showGridLines = True
    ws.freeze_panes = "A2"

    # Header Row
    ws.row_dimensions[1].height = 28
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_THIN

        if comments and header in comments:
            cell.comment = Comment(comments[header], "InfraDoc Generator")
            cell.comment.width = 250
            cell.comment.height = 80

    # Data Rows
    for row_idx, row_data in enumerate(rows, start=2):
        ws.row_dimensions[row_idx].height = 20
        fill = ROW_ALT_FILL if row_idx % 2 == 1 else PatternFill(fill_type=None)
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            # Use monospaced font for IPs, VLANs, CIDRs, Serials
            if any(key in headers[col_idx - 1].lower() for key in ["ip", "vlan", "cidr", "série", "serie"]):
                cell.font = CODE_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.font = CELL_FONT
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if fill.fill_type:
                cell.fill = fill
            cell.border = BORDER_THIN

    # Auto-adjust column widths
    for col_idx, header in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(str(header or ""))
        for row_data in rows:
            if col_idx - 1 < len(row_data):
                val_len = len(str(row_data[col_idx - 1] or ""))
                if val_len > max_len:
                    max_len = val_len
        ws.column_dimensions[col_letter].width = max(max_len + 5, 16)


def _add_instructions_sheet(wb, target_type: str = "all"):
    """Add a documentation worksheet explaining fields, rules, and valid categories."""
    ws = wb.create_sheet(title="Guide & Instructions")
    ws.views.sheetView[0].showGridLines = True
    ws.freeze_panes = "A2"

    headers = ["Type de Donnée", "Champ / Colonne", "Obligatoire", "Format / Valeurs Admises", "Description & Exemple"]
    ws.row_dimensions[1].height = 28
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = GUIDE_HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER_THIN

    guide_rows = [
        # Equipment
        ["Équipement", "Nom / Hostname", "OUI", "Texte unique (ex: SW-CORE-01)", "Identifiant d'équipement dans l'infrastructure"],
        ["Équipement", "Catégorie", "Non (Défaut: generic)", "switch, router, firewall, physical_server, hypervisor, virtual_machine, storage, wifi, generic", "Famille technique pour le dimensionnement et les schémas"],
        ["Équipement", "Constructeur", "Non", "Texte (ex: Cisco, Dell, Fortinet)", "Marque du constructeur matériel"],
        ["Équipement", "Modèle", "Non", "Texte (ex: Catalyst 9300-48P)", "Référence modèle constructeur"],
        ["Équipement", "Numéro de série", "Non", "Alphanumérique (ex: FCW2145L0AB)", "Numéro de série pour inventaire physique"],
        ["Équipement", "Adresse IP de gestion", "Non", "IPv4 valide (ex: 192.168.1.10)", "Adresse IP d'administration"],
        ["Équipement", "Rôle / Fonction", "Non", "Texte (ex: Cœur de réseau)", "Rôle fonctionnel dans la topologie"],
        ["Équipement", "Version Firmware", "Non", "Texte (ex: IOS-XE 17.6.4)", "Version du système d'exploitation"],
        ["Équipement", "Nom du Site", "Non", "Texte (ex: Siège Social)", "Site géographique d'installation"],
        ["Équipement", "Emplacement / Baie", "Non", "Texte (ex: Salle Serveurs - Baie B01)", "Emplacement physique précis"],
        # Network Segments
        ["VLAN / Réseau", "Numéro VLAN", "OUI", "Entier 1 à 4094 (ex: 10, 20)", "Identifiant 802.1Q de segmentation"],
        ["VLAN / Réseau", "Nom du VLAN", "OUI", "Texte (ex: MGMT_INFRA, DATA_CORP)", "Nom explicite du sous-réseau"],
        ["VLAN / Réseau", "CIDR", "Non", "IPv4 CIDR (ex: 192.168.10.0/24)", "Sous-réseau IP et masque de sous-réseau"],
        ["VLAN / Réseau", "Passerelle IP", "Non", "IPv4 valide (ex: 192.168.10.254)", "Passerelle par défaut L3"],
        ["VLAN / Réseau", "Plage DHCP", "Non", "Plage IP (ex: 192.168.10.50-192.168.10.200)", "Étendue dynamique DHCP optionnelle"],
        ["VLAN / Réseau", "Zone de sécurité", "Non", "Texte (ex: LAN, DMZ, MGMT, WAN)", "Zone de filtrage pare-feu"],
        ["VLAN / Réseau", "Description", "Non", "Texte explicatif", "Finalité métier du segment réseau"],
    ]

    for row_idx, r in enumerate(guide_rows, start=2):
        ws.row_dimensions[row_idx].height = 22
        fill = ROW_ALT_FILL if row_idx % 2 == 1 else PatternFill(fill_type=None)
        for col_idx, val in enumerate(r, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = CELL_FONT
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if fill.fill_type:
                cell.fill = fill
            cell.border = BORDER_THIN

    # Auto width for guide
    for col_idx, h in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = max(len(h), max(len(str(r[col_idx - 1])) for r in guide_rows))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)


def generate_equipment_template() -> io.BytesIO:
    """Generate Excel template workbook for IT equipment inventory."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Équipements"

    headers = [
        "Nom / Hostname",
        "Catégorie",
        "Constructeur",
        "Modèle",
        "Numéro de série",
        "Adresse IP de gestion",
        "Rôle / Fonction",
        "Version Firmware",
        "Nom du Site",
        "Emplacement / Baie"
    ]

    comments = {
        "Nom / Hostname": "Obligatoire. Nom d'hôte ou désignation unique de l'équipement.",
        "Catégorie": "Valeurs admises : switch, router, firewall, physical_server, hypervisor, virtual_machine, storage, wifi, generic.",
        "Constructeur": "Marque constructeur (ex: Cisco, Dell, Fortinet, HPE).",
        "Modèle": "Modèle exact du châssis ou serveur.",
        "Numéro de série": "Numéro de série matériel pour le suivi de garantie/inventaire.",
        "Adresse IP de gestion": "Format IPv4 standard (ex: 192.168.1.10).",
        "Nom du Site": "Site d'affectation (sera créé automatiquement s'il n'existe pas).",
        "Emplacement / Baie": "Localisation physique dans le site."
    }

    sample_rows = [
        [
            "SW-CORE-01",
            "switch",
            "Cisco",
            "Catalyst 9300-48P",
            "FCW2145L0AB",
            "192.168.1.2",
            "Commutateur Cœur de réseau",
            "IOS-XE 17.6.4",
            "Siège Social",
            "Salle Serveurs - Baie B01"
        ],
        [
            "FW-PERIM-01",
            "firewall",
            "Fortinet",
            "FortiGate 100F",
            "FG100FTK21000123",
            "192.168.1.1",
            "Pare-feu périmétrique & VPN",
            "FortiOS 7.2.5",
            "Siège Social",
            "Salle Serveurs - Baie B01"
        ],
        [
            "SRV-PROD-01",
            "physical_server",
            "Dell",
            "PowerEdge R750",
            "7X99Y82",
            "192.168.1.10",
            "Serveur Hyperviseur ESXi",
            "VMware ESXi 8.0",
            "Siège Social",
            "Salle Serveurs - Baie B02"
        ],
        [
            "RTR-WAN-01",
            "router",
            "Cisco",
            "Catalyst 8300-1N1S-4T2X",
            "FOC24302XYZ",
            "192.168.1.254",
            "Routeur d'interconnexion WAN",
            "IOS-XE 17.6.4",
            "Siège Social",
            "Salle Serveurs - Baie B01"
        ],
        [
            "AP-ETAGE-1",
            "wifi",
            "Cisco",
            "Catalyst 9120AXI",
            "FOC23419ABC",
            "192.168.1.50",
            "Borne Wi-Fi Étage 1",
            "17.6.2",
            "Siège Social",
            "Zone Bureaux Est"
        ]
    ]

    _apply_sheet_formatting(ws, headers, sample_rows, comments)
    _add_instructions_sheet(wb, target_type="equipment")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def generate_segments_template() -> io.BytesIO:
    """Generate Excel template workbook for VLANs and network segments."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "VLANs & Réseaux"

    headers = [
        "Numéro VLAN",
        "Nom du VLAN",
        "CIDR",
        "Passerelle IP",
        "Plage DHCP",
        "Zone de sécurité",
        "Description"
    ]

    comments = {
        "Numéro VLAN": "Obligatoire. Entier compris entre 1 et 4094.",
        "Nom du VLAN": "Obligatoire. Libellé sans espaces ou caractères spéciaux (ex: VLAN_MGMT, USERS_LAN).",
        "CIDR": "Format IPv4 avec masque CIDR (ex: 192.168.10.0/24).",
        "Passerelle IP": "Adresse IP de la passerelle par défaut (ex: 192.168.10.254).",
        "Plage DHCP": "Optionnel. Plage d'adresses distribuées (ex: 192.168.10.10-192.168.10.200).",
        "Zone de sécurité": "Zone firewall associée (ex: LAN, DMZ, MGMT, SERVERS)."
    }

    sample_rows = [
        [
            10,
            "MGMT_INFRA",
            "192.168.10.0/24",
            "192.168.10.254",
            "",
            "MGMT",
            "Administration et supervision des équipements réseau et serveurs"
        ],
        [
            20,
            "SERVERS_PROD",
            "10.10.20.0/24",
            "10.10.20.254",
            "",
            "SERVERS",
            "Serveurs applicatifs de production et bases de données"
        ],
        [
            30,
            "USERS_DATA",
            "10.10.30.0/23",
            "10.10.30.254",
            "10.10.30.10-10.10.31.200",
            "LAN_USERS",
            "Postes de travail collaborateurs et imprimantes réseau"
        ],
        [
            40,
            "VOIP_TELEPHONY",
            "10.10.40.0/24",
            "10.10.40.254",
            "10.10.40.10-10.10.40.200",
            "VOIP",
            "Postes téléphoniques IP et passerelle ToIP"
        ],
        [
            50,
            "WIFI_GUEST",
            "172.16.50.0/24",
            "172.16.50.254",
            "172.16.50.10-172.16.50.250",
            "GUEST",
            "Réseau Wi-Fi invités isolé avec portail captif"
        ]
    ]

    _apply_sheet_formatting(ws, headers, sample_rows, comments)
    _add_instructions_sheet(wb, target_type="network_segments")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def generate_complete_template() -> io.BytesIO:
    """Generate multi-sheet workbook containing both Equipment and VLAN templates."""
    wb = openpyxl.Workbook()

    # Sheet 1: Equipment
    ws_eq = wb.active
    ws_eq.title = "Équipements"
    eq_template_wb = openpyxl.load_workbook(generate_equipment_template())
    eq_sheet = eq_template_wb["Équipements"]
    for row in eq_sheet.iter_rows(values_only=True):
        ws_eq.append(row)

    # Sheet 2: Segments
    ws_seg = wb.create_sheet(title="VLANs & Réseaux")
    seg_template_wb = openpyxl.load_workbook(generate_segments_template())
    seg_sheet = seg_template_wb["VLANs & Réseaux"]
    for row in seg_sheet.iter_rows(values_only=True):
        ws_seg.append(row)

    # Format sheets
    _apply_sheet_formatting(ws_eq, [c.value for c in ws_eq[1]], [list(r) for r in ws_eq.iter_rows(min_row=2, values_only=True)])
    _apply_sheet_formatting(ws_seg, [c.value for c in ws_seg[1]], [list(r) for r in ws_seg.iter_rows(min_row=2, values_only=True)])
    _add_instructions_sheet(wb, target_type="all")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
