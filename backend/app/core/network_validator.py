import re
import ipaddress
from typing import Optional, Any

SECRET_KEYWORDS = [
    "password", "pass", "secret", "key", "token", "credential",
    "community", "private", "cert", "auth_key", "preshared"
]

def is_valid_ipv4(ip: str) -> bool:
    """Validate if string is a valid IPv4 address."""
    if not ip or not isinstance(ip, str):
        return False
    try:
        ipaddress.IPv4Address(ip.strip())
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False

def is_valid_cidr(cidr: str) -> bool:
    """Validate if string is a valid IPv4 network CIDR (e.g. 192.168.1.0/24)."""
    if not cidr or not isinstance(cidr, str):
        return False
    try:
        ipaddress.IPv4Network(cidr.strip(), strict=False)
        return True
    except (ValueError, ipaddress.NetmaskValueError):
        return False

def is_valid_vlan(vlan_id: Optional[int]) -> bool:
    """Validate standard IEEE 802.1Q VLAN range (1 to 4094)."""
    if vlan_id is None:
        return True
    return isinstance(vlan_id, int) and 1 <= vlan_id <= 4094

def validate_ipv4_address(ip: str) -> tuple[bool, Optional[str]]:
    """Validate IPv4 address and return boolean and error message if invalid."""
    if not ip or not isinstance(ip, str):
        return False, "Adresse IP vide ou invalide"
    try:
        ipaddress.IPv4Address(ip.strip())
        return True, None
    except Exception as e:
        return False, str(e)

def validate_cidr(cidr: str) -> tuple[bool, Optional[str]]:
    """Validate CIDR network notation and return boolean and error message if invalid."""
    if not cidr or not isinstance(cidr, str):
        return False, "Format CIDR vide ou invalide"
    try:
        ipaddress.IPv4Network(cidr.strip(), strict=False)
        return True, None
    except Exception as e:
        return False, str(e)

def validate_vlan_id(vlan: Any) -> tuple[bool, Optional[int]]:
    """Validate and convert VLAN ID into integer between 1 and 4094."""
    try:
        val = int(str(vlan).strip())
        if 1 <= val <= 4094:
            return True, val
        return False, None
    except Exception:
        return False, None

def is_secret_field(key_or_name: str) -> bool:
    """Check if field name suggests a confidential or secret value."""
    if not key_or_name:
        return False
    lower = key_or_name.lower()
    return any(keyword in lower for keyword in SECRET_KEYWORDS)

def mask_secret(value: Optional[str]) -> str:
    """Mask a secret value according to section 8 of MASTER_PROMPT.md."""
    if not value:
        return ""
    return "<SECRET_MASQUÉ>"
