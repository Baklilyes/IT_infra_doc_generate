"""Cisco IOS configuration parser for network devices."""
import ipaddress
import re
from typing import Any
from app.models.equipment import EquipmentCategory, InstallationStatus
from app.models.network import InterfaceType, InterfaceMode


def netmask_to_cidr(netmask_str: str) -> int:
    """Convert IPv4 netmask string to CIDR prefix length."""
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{netmask_str}").prefixlen
    except Exception:
        return 24


def detect_interface_type(if_name: str) -> InterfaceType:
    """Map Cisco interface naming conventions to InterfaceType enum."""
    name_low = if_name.lower()
    if name_low.startswith("vlan"):
        return InterfaceType.VLAN_INTERFACE
    elif name_low.startswith("port-channel") or name_low.startswith("po"):
        return InterfaceType.PORT_CHANNEL
    elif name_low.startswith("loopback") or name_low.startswith("lo"):
        return InterfaceType.LOOPBACK
    elif "." in name_low:
        return InterfaceType.SUBINTERFACE
    elif "mgmt" in name_low or "management" in name_low:
        return InterfaceType.MANAGEMENT
    elif "tunnel" in name_low:
        return InterfaceType.TUNNEL
    else:
        return InterfaceType.PHYSICAL


def parse_cisco_ios(config_text: str) -> dict[str, Any]:
    """
    Parse a Cisco IOS / IOS-XE running-config into structured equipment,
    interfaces, VLAN segments, and configuration parameters.
    """
    lines = [line.rstrip() for line in config_text.splitlines()]
    
    hostname = "Cisco-Device"
    domain_name = None
    management_ip = None
    vlan_segments: list[dict[str, Any]] = []
    interfaces: list[dict[str, Any]] = []
    configurations: list[dict[str, Any]] = []

    current_interface: dict[str, Any] | None = None
    current_vlan: dict[str, Any] | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("!"):
            continue

        # Hostname
        m_host = re.match(r"^hostname\s+(\S+)", stripped, re.IGNORECASE)
        if m_host:
            hostname = m_host.group(1)
            configurations.append({
                "category": "system",
                "key": "hostname",
                "value": hostname,
                "is_secret": False
            })
            continue

        # Domain name
        m_domain = re.match(r"^ip\s+domain-name\s+(\S+)", stripped, re.IGNORECASE)
        if m_domain:
            domain_name = m_domain.group(1)
            configurations.append({
                "category": "dns",
                "key": "domain_name",
                "value": domain_name,
                "is_secret": False
            })
            continue

        # NTP server
        m_ntp = re.match(r"^ntp\s+server\s+(\S+)", stripped, re.IGNORECASE)
        if m_ntp:
            configurations.append({
                "category": "ntp",
                "key": f"ntp_server_{len([c for c in configurations if c['category'] == 'ntp']) + 1}",
                "value": m_ntp.group(1),
                "is_secret": False
            })
            continue

        # DNS name server
        m_dns = re.match(r"^ip\s+name-server\s+(.+)", stripped, re.IGNORECASE)
        if m_dns:
            configurations.append({
                "category": "dns",
                "key": "name_servers",
                "value": m_dns.group(1).strip(),
                "is_secret": False
            })
            continue

        # Default Gateway
        m_gw = re.match(r"^ip\s+default-gateway\s+(\S+)", stripped, re.IGNORECASE)
        if m_gw:
            configurations.append({
                "category": "routing",
                "key": "default_gateway",
                "value": m_gw.group(1),
                "is_secret": False
            })
            continue

        # SNMP community (classified as secret)
        m_snmp = re.match(r"^snmp-server\s+community\s+(\S+)", stripped, re.IGNORECASE)
        if m_snmp:
            configurations.append({
                "category": "snmp",
                "key": "snmp_community",
                "value": m_snmp.group(1),
                "is_secret": True
            })
            continue

        # Enable secret
        m_secret = re.match(r"^enable\s+secret\s+(\S+)", stripped, re.IGNORECASE)
        if m_secret:
            configurations.append({
                "category": "security",
                "key": "enable_secret",
                "value": m_secret.group(1),
                "is_secret": True
            })
            continue

        # VLAN block detection
        m_vlan = re.match(r"^vlan\s+(\d+)$", stripped, re.IGNORECASE)
        if m_vlan:
            vlan_id = int(m_vlan.group(1))
            current_vlan = {"vlan_id": vlan_id, "name": f"VLAN_{vlan_id}", "cidr": None, "gateway": None}
            vlan_segments.append(current_vlan)
            current_interface = None
            continue

        if current_vlan and line.startswith(" "):
            m_vlan_name = re.match(r"^\s*name\s+(.+)", stripped, re.IGNORECASE)
            if m_vlan_name:
                current_vlan["name"] = m_vlan_name.group(1).strip()
            continue
        elif not line.startswith(" "):
            current_vlan = None

        # Interface block detection
        m_if = re.match(r"^interface\s+(\S+)", stripped, re.IGNORECASE)
        if m_if:
            if_name = m_if.group(1)
            if_type = detect_interface_type(if_name)
            current_interface = {
                "name": if_name,
                "interface_type": if_type.value,
                "mode": InterfaceMode.UNCONFIGURED.value,
                "ip_address": None,
                "vlan_tag": None,
                "allowed_vlans": None,
                "description": None,
                "is_enabled": True
            }
            interfaces.append(current_interface)
            continue

        if current_interface and line.startswith(" "):
            # Description
            m_desc = re.match(r"^\s*description\s+(.+)", stripped, re.IGNORECASE)
            if m_desc:
                current_interface["description"] = m_desc.group(1).strip()
                continue

            # IP Address
            m_ip = re.match(r"^\s*ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)", stripped, re.IGNORECASE)
            if m_ip:
                ip_str = m_ip.group(1)
                mask_str = m_ip.group(2)
                cidr_prefix = netmask_to_cidr(mask_str)
                full_ip = f"{ip_str}/{cidr_prefix}"
                current_interface["ip_address"] = full_ip
                if not management_ip and (current_interface["interface_type"] in ["management", "vlan_interface"] or "mgmt" in current_interface["name"].lower()):
                    management_ip = ip_str
                continue

            # Switchport mode
            m_mode = re.match(r"^\s*switchport\s+mode\s+(access|trunk)", stripped, re.IGNORECASE)
            if m_mode:
                mode_str = m_mode.group(1).lower()
                current_interface["mode"] = InterfaceMode.ACCESS.value if mode_str == "access" else InterfaceMode.TRUNK.value
                continue

            # Switchport access vlan
            m_acc_vlan = re.match(r"^\s*switchport\s+access\s+vlan\s+(\d+)", stripped, re.IGNORECASE)
            if m_acc_vlan:
                current_interface["vlan_tag"] = int(m_acc_vlan.group(1))
                current_interface["mode"] = InterfaceMode.ACCESS.value
                continue

            # Switchport trunk allowed vlan
            m_trk_vlan = re.match(r"^\s*switchport\s+trunk\s+allowed\s+vlan\s+(.+)", stripped, re.IGNORECASE)
            if m_trk_vlan:
                current_interface["allowed_vlans"] = m_trk_vlan.group(1).strip()
                current_interface["mode"] = InterfaceMode.TRUNK.value
                continue

            # Shutdown
            if stripped.lower() == "shutdown":
                current_interface["is_enabled"] = False
                continue
            elif stripped.lower() == "no shutdown":
                current_interface["is_enabled"] = True
                continue

    # If no specific management IP was found, look for first configured IP
    if not management_ip:
        for iface in interfaces:
            if iface.get("ip_address"):
                management_ip = iface["ip_address"].split("/")[0]
                break

    category = EquipmentCategory.SWITCH.value
    if "router" in hostname.lower() or any(i.get("mode") == "routed" for i in interfaces):
        category = EquipmentCategory.ROUTER.value

    equipment = {
        "name": hostname,
        "category": category,
        "manufacturer": "Cisco",
        "model": "Catalyst / IOS",
        "role": "Commutateur de distribution" if category == EquipmentCategory.SWITCH.value else "Routeur d'accès",
        "management_ip": management_ip,
        "status": InstallationStatus.IN_SERVICE.value,
        "specific_attributes": {
            "domain_name": domain_name,
            "interfaces_count": len(interfaces),
            "vlans_count": len(vlan_segments)
        }
    }

    return {
        "equipment": equipment,
        "interfaces": interfaces,
        "network_segments": vlan_segments,
        "configurations": configurations
    }
