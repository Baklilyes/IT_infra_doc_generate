"""Tabular parser for CSV and Excel (.xlsx) file ingestion."""
import csv
import io
import re
from typing import Any
import openpyxl
from app.core.network_validator import validate_ipv4_address, validate_cidr, validate_vlan_id
from app.models.equipment import EquipmentCategory

# Mapping synonyms for auto-detection
EQUIPMENT_FIELD_SYNONYMS = {
    "name": ["nom", "hostname", "name", "nom équipement", "nom equipement", "device", "device name", "machine"],
    "category": ["catégorie", "categorie", "type", "category", "famille", "device type", "type équipement"],
    "manufacturer": ["constructeur", "fabricant", "marque", "vendor", "manufacturer", "brand"],
    "model": ["modèle", "modele", "model", "référence", "reference"],
    "serial_number": ["numéro de série", "numero de serie", "serial", "s/n", "sn", "serial number", "serie"],
    "management_ip": ["ip", "ip management", "ip gestion", "ip admin", "adresse ip", "management ip", "ip_address"],
    "role": ["rôle", "role", "fonction", "function"],
    "firmware_version": ["firmware", "os", "version", "ios", "version firmware"],
    "site_name": ["site", "nom site", "site name", "agence", "lieu"],
    "location_name": ["emplacement", "baie", "salle", "rack", "room", "location"]
}

SEGMENT_FIELD_SYNONYMS = {
    "vlan_id": ["vlan", "vlan id", "vid", "numéro vlan", "numero vlan", "id vlan", "vlan_id"],
    "name": ["nom", "nom vlan", "vlan name", "name", "libellé", "libelle", "description vlan"],
    "cidr": ["cidr", "sous-réseau", "sous reseau", "subnet", "réseau", "reseau", "network", "plage ip"],
    "gateway": ["passerelle", "gateway", "gw", "ip passerelle", "router ip"],
    "dhcp_range": ["dhcp", "plage dhcp", "dhcp range", "étendue dhcp", "pool dhcp"],
    "zone": ["zone", "sécurité", "securite", "security zone", "zone sécurité", "type réseau"],
    "description": ["description", "notes", "commentaire", "commentaires", "remarques"]
}

CATEGORY_NORMALIZATION_MAP = {
    "switch": EquipmentCategory.SWITCH,
    "commutateur": EquipmentCategory.SWITCH,
    "cœur": EquipmentCategory.SWITCH,
    "coeur": EquipmentCategory.SWITCH,
    "distribution": EquipmentCategory.SWITCH,
    "accès": EquipmentCategory.SWITCH,
    "acces": EquipmentCategory.SWITCH,
    "router": EquipmentCategory.ROUTER,
    "routeur": EquipmentCategory.ROUTER,
    "firewall": EquipmentCategory.FIREWALL,
    "pare-feu": EquipmentCategory.FIREWALL,
    "pare feu": EquipmentCategory.FIREWALL,
    "server": EquipmentCategory.PHYSICAL_SERVER,
    "serveur": EquipmentCategory.PHYSICAL_SERVER,
    "physical_server": EquipmentCategory.PHYSICAL_SERVER,
    "hypervisor": EquipmentCategory.HYPERVISOR,
    "hyperviseur": EquipmentCategory.HYPERVISOR,
    "esxi": EquipmentCategory.HYPERVISOR,
    "vm": EquipmentCategory.VIRTUAL_MACHINE,
    "virtual_machine": EquipmentCategory.VIRTUAL_MACHINE,
    "machine virtuelle": EquipmentCategory.VIRTUAL_MACHINE,
    "storage": EquipmentCategory.STORAGE,
    "stockage": EquipmentCategory.STORAGE,
    "nas": EquipmentCategory.STORAGE,
    "san": EquipmentCategory.STORAGE,
    "wifi": EquipmentCategory.WIFI,
    "ap": EquipmentCategory.WIFI,
    "borne": EquipmentCategory.WIFI,
    "borne wifi": EquipmentCategory.WIFI,
    "generic": EquipmentCategory.GENERIC
}


def normalize_header(header: str) -> str:
    """Strip and clean header strings for matching."""
    return re.sub(r"\s+", " ", str(header or "")).strip().lower()


def suggest_mapping(headers: list[str], target_type: str = "equipment") -> dict[str, str]:
    """Auto-detect column mapping according to predefined synonyms."""
    synonyms = EQUIPMENT_FIELD_SYNONYMS if target_type == "equipment" else SEGMENT_FIELD_SYNONYMS
    mapping: dict[str, str] = {}
    
    cleaned_headers = {h: normalize_header(h) for h in headers if h}
    
    for target_field, syn_list in synonyms.items():
        matched = False
        for orig_h, clean_h in cleaned_headers.items():
            if clean_h in syn_list or any(syn in clean_h for syn in syn_list):
                mapping[orig_h] = target_field
                matched = True
                break
        if not matched:
            for orig_h, clean_h in cleaned_headers.items():
                if target_field == clean_h:
                    mapping[orig_h] = target_field
                    break

    return mapping


def parse_csv_content(content_str: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse CSV text with dialect auto-detection."""
    if not content_str.strip():
        return [], []
    
    sample = content_str[:4096]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t")
        delimiter = dialect.delimiter
    except Exception:
        if ";" in sample and "," not in sample:
            delimiter = ";"
        elif "\t" in sample:
            delimiter = "\t"

    reader = csv.reader(io.StringIO(content_str), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return [], []
    
    raw_headers = [str(col).strip() for col in rows[0]]
    # Eliminate empty trailing headers
    while raw_headers and not raw_headers[-1]:
        raw_headers.pop()

    parsed_rows: list[dict[str, Any]] = []
    for r in rows[1:]:
        if not any(r):
            continue
        row_dict = {}
        for idx, header in enumerate(raw_headers):
            val = r[idx].strip() if idx < len(r) else ""
            row_dict[header] = val
        parsed_rows.append(row_dict)

    return raw_headers, parsed_rows


def parse_excel_bytes(file_bytes: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse Excel (.xlsx) file bytes using openpyxl."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet = wb.active
    if not sheet:
        return [], []

    rows_iter = sheet.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    if not header_row:
        return [], []

    raw_headers = [str(cell).strip() if cell is not None else f"Column_{idx+1}" for idx, cell in enumerate(header_row)]
    while raw_headers and (not raw_headers[-1] or raw_headers[-1].startswith("Column_")):
        raw_headers.pop()

    parsed_rows: list[dict[str, Any]] = []
    for row in rows_iter:
        if not any(row):
            continue
        row_dict = {}
        has_content = False
        for idx, header in enumerate(raw_headers):
            val = row[idx] if idx < len(row) else None
            str_val = str(val).strip() if val is not None else ""
            if str_val:
                has_content = True
            row_dict[header] = str_val
        if has_content:
            parsed_rows.append(row_dict)

    return raw_headers, parsed_rows


def transform_equipment_row(row_dict: dict[str, Any], mapping: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """Transform and validate a single equipment row against mapping."""
    transformed: dict[str, Any] = {}
    errors: list[str] = []

    # Invert mapping: target_field -> source_col
    target_to_source = {target: src for src, target in mapping.items() if target}

    # Name is required
    name_col = target_to_source.get("name")
    raw_name = row_dict.get(name_col, "").strip() if name_col else ""
    if not raw_name:
        errors.append("Le nom d'équipement (hostname) est obligatoire.")
    else:
        transformed["name"] = raw_name

    # Category normalization
    cat_col = target_to_source.get("category")
    raw_cat = row_dict.get(cat_col, "").strip().lower() if cat_col else ""
    if raw_cat:
        transformed["category"] = CATEGORY_NORMALIZATION_MAP.get(raw_cat, EquipmentCategory.GENERIC).value
    else:
        transformed["category"] = EquipmentCategory.GENERIC.value

    # Manufacturer & Model
    mfg_col = target_to_source.get("manufacturer")
    transformed["manufacturer"] = row_dict.get(mfg_col, "").strip() if mfg_col else None

    mod_col = target_to_source.get("model")
    transformed["model"] = row_dict.get(mod_col, "").strip() if mod_col else None

    # Serial Number
    sn_col = target_to_source.get("serial_number")
    transformed["serial_number"] = row_dict.get(sn_col, "").strip() if sn_col else None

    # Management IP
    ip_col = target_to_source.get("management_ip")
    raw_ip = row_dict.get(ip_col, "").strip() if ip_col else ""
    if raw_ip:
        is_valid_ip, err = validate_ipv4_address(raw_ip)
        if is_valid_ip:
            transformed["management_ip"] = raw_ip
        else:
            errors.append(f"Adresse IP invalide '{raw_ip}': {err}")
            transformed["management_ip"] = raw_ip
    else:
        transformed["management_ip"] = None

    # Role & Firmware
    role_col = target_to_source.get("role")
    transformed["role"] = row_dict.get(role_col, "").strip() if role_col else None

    fw_col = target_to_source.get("firmware_version")
    transformed["firmware_version"] = row_dict.get(fw_col, "").strip() if fw_col else None

    # Site & Location
    site_col = target_to_source.get("site_name")
    transformed["site_name"] = row_dict.get(site_col, "").strip() if site_col else None

    loc_col = target_to_source.get("location_name")
    transformed["location_name"] = row_dict.get(loc_col, "").strip() if loc_col else None

    return transformed, errors


def transform_segment_row(row_dict: dict[str, Any], mapping: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """Transform and validate a single network segment row against mapping."""
    transformed: dict[str, Any] = {}
    errors: list[str] = []

    target_to_source = {target: src for src, target in mapping.items() if target}

    # VLAN ID
    vlan_col = target_to_source.get("vlan_id")
    raw_vlan = row_dict.get(vlan_col, "").strip() if vlan_col else ""
    if not raw_vlan:
        errors.append("Le numéro de VLAN est obligatoire.")
    else:
        is_valid_vlan, vlan_int = validate_vlan_id(raw_vlan)
        if is_valid_vlan:
            transformed["vlan_id"] = vlan_int
        else:
            errors.append(f"VLAN invalide '{raw_vlan}' : doit être un entier entre 1 et 4094.")
            transformed["vlan_id"] = raw_vlan

    # Name
    name_col = target_to_source.get("name")
    raw_name = row_dict.get(name_col, "").strip() if name_col else ""
    if not raw_name:
        errors.append("Le nom du sous-réseau / VLAN est obligatoire.")
    else:
        transformed["name"] = raw_name

    # CIDR
    cidr_col = target_to_source.get("cidr")
    raw_cidr = row_dict.get(cidr_col, "").strip() if cidr_col else ""
    if raw_cidr:
        is_valid_cidr, err = validate_cidr(raw_cidr)
        if is_valid_cidr:
            transformed["cidr"] = raw_cidr
        else:
            errors.append(f"Format CIDR invalide '{raw_cidr}': {err}")
            transformed["cidr"] = raw_cidr
    else:
        transformed["cidr"] = None

    # Gateway
    gw_col = target_to_source.get("gateway")
    raw_gw = row_dict.get(gw_col, "").strip() if gw_col else ""
    if raw_gw:
        is_valid_gw, err = validate_ipv4_address(raw_gw)
        if is_valid_gw:
            transformed["gateway"] = raw_gw
        else:
            errors.append(f"Passerelle IP invalide '{raw_gw}': {err}")
            transformed["gateway"] = raw_gw
    else:
        transformed["gateway"] = None

    # DHCP, Zone, Description
    dhcp_col = target_to_source.get("dhcp_range")
    transformed["dhcp_range"] = row_dict.get(dhcp_col, "").strip() if dhcp_col else None

    zone_col = target_to_source.get("zone")
    transformed["zone"] = row_dict.get(zone_col, "").strip() if zone_col else None

    desc_col = target_to_source.get("description")
    transformed["description"] = row_dict.get(desc_col, "").strip() if desc_col else None

    return transformed, errors
