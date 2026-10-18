"""Fortinet FortiOS CLI configuration parser."""
import re
from typing import Any
from app.models.equipment import EquipmentCategory, InstallationStatus
from app.models.network import InterfaceType, InterfaceMode


def parse_fortinet_cli(config_text: str) -> dict[str, Any]:
    """
    Parse a Fortinet FortiOS CLI configuration into structured firewall equipment,
    interfaces, and configurations.
    """
    lines = [line.strip() for line in config_text.splitlines() if line.strip() and not line.strip().startswith("#")]

    hostname = "FortiGate-Firewall"
    interfaces: list[dict[str, Any]] = []
    configurations: list[dict[str, Any]] = []

    current_section = None
    current_interface: dict[str, Any] | None = None

    for line in lines:
        if line.startswith("config system global"):
            current_section = "global"
            continue
        elif line.startswith("config system interface"):
            current_section = "interfaces"
            continue
        elif line == "end":
            if current_section == "interfaces" and current_interface:
                interfaces.append(current_interface)
                current_interface = None
            current_section = None
            continue

        if current_section == "global":
            m_host = re.match(r"^set\s+hostname\s+[\"']?([^\"']+)[\"']?", line, re.IGNORECASE)
            if m_host:
                hostname = m_host.group(1)
                configurations.append({
                    "category": "system",
                    "key": "hostname",
                    "value": hostname,
                    "is_secret": False
                })

        elif current_section == "interfaces":
            m_edit = re.match(r"^edit\s+[\"']?([^\"']+)[\"']?", line, re.IGNORECASE)
            if m_edit:
                if current_interface:
                    interfaces.append(current_interface)
                port_name = m_edit.group(1)
                current_interface = {
                    "name": port_name,
                    "interface_type": InterfaceType.PHYSICAL.value,
                    "mode": InterfaceMode.ROUTED.value,
                    "ip_address": None,
                    "vlan_tag": None,
                    "description": None,
                    "is_enabled": True
                }
                continue

            if current_interface:
                m_ip = re.match(r"^set\s+ip\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)", line, re.IGNORECASE)
                if m_ip:
                    from app.core.parsers.cisco import netmask_to_cidr
                    ip_str = m_ip.group(1)
                    mask_str = m_ip.group(2)
                    cidr = netmask_to_cidr(mask_str)
                    current_interface["ip_address"] = f"{ip_str}/{cidr}"
                    continue

                m_alias = re.match(r"^set\s+alias\s+[\"']?([^\"']+)[\"']?", line, re.IGNORECASE)
                if m_alias:
                    current_interface["description"] = m_alias.group(1)
                    continue

                m_vlan = re.match(r"^set\s+vlanid\s+(\d+)", line, re.IGNORECASE)
                if m_vlan:
                    current_interface["vlan_tag"] = int(m_vlan.group(1))
                    current_interface["interface_type"] = InterfaceType.VLAN_INTERFACE.value
                    continue

                if line.startswith("set status down"):
                    current_interface["is_enabled"] = False
                    continue

    if current_interface:
        interfaces.append(current_interface)

    # Management IP
    management_ip = None
    for iface in interfaces:
        if iface.get("ip_address"):
            management_ip = iface["ip_address"].split("/")[0]
            break

    equipment = {
        "name": hostname,
        "category": EquipmentCategory.FIREWALL.value,
        "manufacturer": "Fortinet",
        "model": "FortiGate",
        "role": "Pare-feu de sécurité périmétrique",
        "management_ip": management_ip,
        "status": InstallationStatus.IN_SERVICE.value,
        "specific_attributes": {
            "ports_count": len(interfaces)
        }
    }

    return {
        "equipment": equipment,
        "interfaces": interfaces,
        "network_segments": [],
        "configurations": configurations
    }
