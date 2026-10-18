"""Deterministic Consistency Engine for IT Infrastructure Validation.

Evaluates strict network, topology, VLAN, IP, and security rules without AI dependency.
Complies with Section 8 of MASTER_PROMPT.md.
"""
import hashlib
import ipaddress
import re
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.project import Project, Site
from app.models.equipment import Equipment, VerificationStatus
from app.models.network import Interface, NetworkSegment, ConfigurationParam
from app.models.validation import ConsistencyOverride, ConsistencyReport
from app.core.network_validator import is_valid_ipv4, is_valid_cidr, SECRET_KEYWORDS


class Finding:
    def __init__(
        self,
        rule_code: str,
        rule_title: str,
        category: str,
        severity: str,
        target_type: str,
        target_id: str,
        target_name: str,
        message: str,
        recommendation: str
    ):
        self.id = hashlib.md5(f"{rule_code}:{target_id}:{target_type}".encode()).hexdigest()[:12]
        self.rule_code = rule_code
        self.rule_title = rule_title
        self.category = category  # 'ip', 'vlan', 'topology', 'security'
        self.severity = severity  # 'blocking', 'warning', 'info'
        self.target_type = target_type  # 'equipment', 'interface', 'segment', 'configuration'
        self.target_id = str(target_id)
        self.target_name = target_name
        self.message = message
        self.recommendation = recommendation
        self.is_overridden = False
        self.override_id = None
        self.override_justification = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule_code": self.rule_code,
            "rule_title": self.rule_title,
            "category": self.category,
            "severity": self.severity,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "message": self.message,
            "recommendation": self.recommendation,
            "is_overridden": self.is_overridden,
            "override_id": self.override_id,
            "override_justification": self.override_justification
        }


def extract_ip_clean(ip_str: Optional[str]) -> Optional[str]:
    """Extract clean IP without /CIDR prefix if present."""
    if not ip_str:
        return None
    return ip_str.split("/")[0].strip()


async def run_consistency_checks(project_id: str, db: AsyncSession) -> tuple[list[Finding], dict[str, int]]:
    """
    Run all deterministic verification rules on a project and match findings against active overrides.
    Returns (findings, counters_dict).
    """
    # 1. Fetch project data
    p_res = await db.execute(select(Project).where(Project.id == project_id))
    project = p_res.scalars().first()
    if not project:
        raise ValueError("Projet introuvable")

    # Fetch equipment with interfaces
    eq_res = await db.execute(
        select(Equipment)
        .options(selectinload(Equipment.interfaces), selectinload(Equipment.site), selectinload(Equipment.location))
        .where(Equipment.project_id == project_id)
    )
    equipment_list = eq_res.scalars().all()
    equipment_ids = {e.id for e in equipment_list}

    # Fetch segments
    seg_res = await db.execute(
        select(NetworkSegment).where(NetworkSegment.project_id == project_id)
    )
    segments = seg_res.scalars().all()

    # Fetch configurations
    cfg_res = await db.execute(
        select(ConfigurationParam).where(ConfigurationParam.project_id == project_id)
    )
    configs = cfg_res.scalars().all()

    # Fetch active overrides
    ovr_res = await db.execute(
        select(ConsistencyOverride).where(
            and_(
                ConsistencyOverride.project_id == project_id,
                ConsistencyOverride.is_active == True
            )
        )
    )
    active_overrides = ovr_res.scalars().all()
    override_lookup = {
        f"{o.rule_code}:{o.target_id}": o for o in active_overrides
    }

    raw_findings: list[Finding] = []

    # -------------------------------------------------------------
    # RULE GROUP 1: Hostname Duplicates (Blocking)
    # -------------------------------------------------------------
    hostname_map: dict[str, list[Equipment]] = {}
    for eq in equipment_list:
        clean_name = eq.name.strip().lower()
        hostname_map.setdefault(clean_name, []).append(eq)

    for clean_name, eq_group in hostname_map.items():
        if len(eq_group) > 1:
            for eq in eq_group:
                other_names = [e.name for e in eq_group if e.id != eq.id]
                raw_findings.append(Finding(
                    rule_code="HOSTNAME_DUPLICATE",
                    rule_title="Nom d'hôte (Hostname) en double",
                    category="topology",
                    severity="blocking",
                    target_type="equipment",
                    target_id=eq.id,
                    target_name=eq.name,
                    message=f"Le nom d'équipement '{eq.name}' est dupliqué ({len(eq_group)} occurrences).",
                    recommendation="Renommez l'équipement pour assurer l'unicité des hostnames dans le projet."
                ))

    # -------------------------------------------------------------
    # RULE GROUP 2: IP Address Duplicates & Formatting (Blocking)
    # -------------------------------------------------------------
    ip_usage_map: dict[str, list[tuple[str, str, str]]] = {}  # ip -> [(type, id, name)]

    for eq in equipment_list:
        clean_ip = extract_ip_clean(eq.management_ip)
        if clean_ip:
            if not is_valid_ipv4(clean_ip):
                raw_findings.append(Finding(
                    rule_code="INVALID_IP_FORMAT",
                    rule_title="Format d'adresse IP invalide",
                    category="ip",
                    severity="blocking",
                    target_type="equipment",
                    target_id=eq.id,
                    target_name=eq.name,
                    message=f"L'adresse IP de management '{eq.management_ip}' n'est pas une adresse IPv4 valide.",
                    recommendation="Corrigez l'adresse IP de management (format décimal à point x.x.x.x)."
                ))
            else:
                ip_usage_map.setdefault(clean_ip, []).append(("equipment", eq.id, f"{eq.name} (Management)"))

        for iface in eq.interfaces:
            if iface.ip_address:
                clean_if_ip = extract_ip_clean(iface.ip_address)
                if not is_valid_ipv4(clean_if_ip):
                    raw_findings.append(Finding(
                        rule_code="INVALID_IP_FORMAT",
                        rule_title="Format d'adresse IP invalide sur interface",
                        category="ip",
                        severity="blocking",
                        target_type="interface",
                        target_id=iface.id,
                        target_name=f"{eq.name} -> {iface.name}",
                        message=f"L'adresse IP de l'interface '{iface.ip_address}' est invalide.",
                        recommendation="Renseignez une adresse IPv4 valide ou ajustez le masque CIDR."
                    ))
                else:
                    ip_usage_map.setdefault(clean_if_ip, []).append(("interface", iface.id, f"{eq.name} -> {iface.name}"))

    # Check IP duplicates
    for ip, usages in ip_usage_map.items():
        if len(usages) > 1:
            for target_type, target_id, target_name in usages:
                others = [u[2] for u in usages if u[1] != target_id]
                raw_findings.append(Finding(
                    rule_code="IP_DUPLICATE",
                    rule_title="Adresse IP en double (Conflit)",
                    category="ip",
                    severity="blocking",
                    target_type=target_type,
                    target_id=target_id,
                    target_name=target_name,
                    message=f"L'adresse IP '{ip}' est assignée simultanément à plusieurs éléments : {', '.join(others)}.",
                    recommendation="Attribuez une adresse IP distincte pour éliminer le conflit d'adressage."
                ))

    # -------------------------------------------------------------
    # RULE GROUP 3: CIDR Overlap & Gateway Validation (Blocking)
    # -------------------------------------------------------------
    valid_subnets: list[tuple[NetworkSegment, ipaddress.IPv4Network]] = []
    defined_vlan_ids: set[int] = set()

    for seg in segments:
        defined_vlan_ids.add(seg.vlan_id)
        if seg.vlan_id < 1 or seg.vlan_id > 4094:
            raw_findings.append(Finding(
                rule_code="VLAN_OUT_OF_RANGE",
                rule_title="Numéro de VLAN hors limites (1-4094)",
                category="vlan",
                severity="blocking",
                target_type="segment",
                target_id=seg.id,
                target_name=f"VLAN {seg.vlan_id} ({seg.name})",
                message=f"Le VLAN ID {seg.vlan_id} est hors limites de la norme IEEE 802.1Q (1 à 4094).",
                recommendation="Choisissez un ID de VLAN compris strictement entre 1 et 4094."
            ))

        if seg.cidr:
            if not is_valid_cidr(seg.cidr):
                raw_findings.append(Finding(
                    rule_code="INVALID_CIDR_FORMAT",
                    rule_title="Format CIDR de sous-réseau invalide",
                    category="ip",
                    severity="blocking",
                    target_type="segment",
                    target_id=seg.id,
                    target_name=seg.name,
                    message=f"La notation CIDR '{seg.cidr}' n'est pas un sous-réseau IPv4 valide.",
                    recommendation="Spécifiez un masque CIDR valide (ex. 192.168.1.0/24)."
                ))
            else:
                try:
                    net_obj = ipaddress.IPv4Network(seg.cidr, strict=False)
                    valid_subnets.append((seg, net_obj))

                    # Check Gateway within subnet
                    if seg.gateway:
                        clean_gw = extract_ip_clean(seg.gateway)
                        if is_valid_ipv4(clean_gw):
                            gw_ip = ipaddress.IPv4Address(clean_gw)
                            if gw_ip not in net_obj:
                                raw_findings.append(Finding(
                                    rule_code="GATEWAY_OUT_OF_SUBNET",
                                    rule_title="Passerelle hors de la plage du sous-réseau",
                                    category="ip",
                                    severity="blocking",
                                    target_type="segment",
                                    target_id=seg.id,
                                    target_name=f"{seg.name} (VLAN {seg.vlan_id})",
                                    message=f"La passerelle '{seg.gateway}' n'appartient pas au sous-réseau '{seg.cidr}'.",
                                    recommendation="Configurez une adresse IP de passerelle incluse dans le sous-réseau."
                                ))
                except Exception:
                    pass

    # Check overlap between subnets
    for i in range(len(valid_subnets)):
        for j in range(i + 1, len(valid_subnets)):
            seg_a, net_a = valid_subnets[i]
            seg_b, net_b = valid_subnets[j]
            if net_a.overlaps(net_b):
                raw_findings.append(Finding(
                    rule_code="CIDR_OVERLAP",
                    rule_title="Chevauchement de sous-réseaux (Overlap)",
                    category="ip",
                    severity="blocking",
                    target_type="segment",
                    target_id=seg_a.id,
                    target_name=f"{seg_a.name} ({seg_a.cidr})",
                    message=f"Le sous-réseau '{seg_a.cidr}' chevauche '{seg_b.cidr}' (VLAN {seg_b.vlan_id} - {seg_b.name}).",
                    recommendation="Ajustez les plages d'adressage IP pour éviter tout chevauchement non routé."
                ))

    # -------------------------------------------------------------
    # RULE GROUP 4: VLAN Assignment & Undefined VLANs (Warning)
    # -------------------------------------------------------------
    used_vlans: set[int] = set()
    for eq in equipment_list:
        for iface in eq.interfaces:
            if iface.access_vlan is not None:
                used_vlans.add(iface.access_vlan)
                if iface.access_vlan not in defined_vlan_ids:
                    raw_findings.append(Finding(
                        rule_code="VLAN_UNDEFINED",
                        rule_title="VLAN d'accès non déclaré dans le plan d'adressage",
                        category="vlan",
                        severity="warning",
                        target_type="interface",
                        target_id=iface.id,
                        target_name=f"{eq.name} -> {iface.name}",
                        message=f"L'interface est configurée sur le VLAN {iface.access_vlan}, mais ce VLAN n'est pas défini dans le projet.",
                        recommendation=f"Créez le VLAN {iface.access_vlan} dans le plan d'adressage ou réaffectez l'interface."
                    ))

    # Orphan segments (Info)
    for seg in segments:
        if seg.vlan_id not in used_vlans:
            raw_findings.append(Finding(
                rule_code="ORPHAN_SEGMENT",
                rule_title="VLAN déclaré sans interface associée",
                category="vlan",
                severity="info",
                target_type="segment",
                target_id=seg.id,
                target_name=f"VLAN {seg.vlan_id} ({seg.name})",
                message=f"Le VLAN {seg.vlan_id} est présent dans le plan d'adressage mais aucune interface ne lui est attribuée.",
                recommendation="Associez ce VLAN aux interfaces prévues ou supprimez-le s'il est devenu obsolète."
            ))

    # -------------------------------------------------------------
    # RULE GROUP 5: Topology, Sites & Remote Links (Warning / Blocking)
    # -------------------------------------------------------------
    for eq in equipment_list:
        # Site assignment
        if not eq.site_id:
            raw_findings.append(Finding(
                rule_code="EQUIPMENT_NO_SITE",
                rule_title="Équipement sans site rattaché",
                category="topology",
                severity="warning",
                target_type="equipment",
                target_id=eq.id,
                target_name=eq.name,
                message=f"L'équipement '{eq.name}' n'est associé à aucun site géographique.",
                recommendation="Attribuez un site à l'équipement pour le positionner dans les schémas d'architecture."
            ))
        elif not eq.location_id:
            raw_findings.append(Finding(
                rule_code="EQUIPMENT_NO_LOCATION",
                rule_title="Équipement sans emplacement précis (baie / salle)",
                category="topology",
                severity="info",
                target_type="equipment",
                target_id=eq.id,
                target_name=eq.name,
                message=f"L'équipement '{eq.name}' est sur un site mais sans salle technique ou rack défini.",
                recommendation="Précisez la baie ou la salle technique pour le dossier d'exploitation."
            ))

        # Management IP missing
        if not eq.management_ip and not any(i.ip_address for i in eq.interfaces):
            raw_findings.append(Finding(
                rule_code="EQUIPMENT_NO_MGMT_IP",
                rule_title="Équipement sans adresse IP de gestion",
                category="topology",
                severity="warning",
                target_type="equipment",
                target_id=eq.id,
                target_name=eq.name,
                message=f"L'équipement actif '{eq.name}' ne possède aucune adresse IP de gestion.",
                recommendation="Renseignez l'IP d'administration pour l'inventaire et les annexes de configuration."
            ))

        # Remote link orphan
        for iface in eq.interfaces:
            if iface.connected_equipment_id and iface.connected_equipment_id not in equipment_ids:
                raw_findings.append(Finding(
                    rule_code="REMOTE_LINK_ORPHAN",
                    rule_title="Interconnexion vers un équipement inexistant",
                    category="topology",
                    severity="blocking",
                    target_type="interface",
                    target_id=iface.id,
                    target_name=f"{eq.name} -> {iface.name}",
                    message="L'interface pointe vers un équipement distant qui a été supprimé ou n'existe pas.",
                    recommendation="Mettez à jour le lien distant vers un équipement valide ou retirez la liaison."
                ))

        # Unverified items check (from imports or AI)
        if eq.verification_status == VerificationStatus.UNVERIFIED:
            raw_findings.append(Finding(
                rule_code="UNVERIFIED_EQUIPMENT",
                rule_title="Équipement en attente de vérification technique",
                category="security",
                severity="warning",
                target_type="equipment",
                target_id=eq.id,
                target_name=eq.name,
                message=f"L'équipement '{eq.name}' a été importé ou proposé par l'IA et nécessite validation.",
                recommendation="Passez l'équipement en revue et confirmez son statut 'Vérifié'."
            ))

    # -------------------------------------------------------------
    # RULE GROUP 6: Cleartext Secrets in Descriptions / Configs (Blocking)
    # -------------------------------------------------------------
    for eq in equipment_list:
        for field_text, field_name in [(eq.notes, "Notes"), (eq.role, "Rôle")]:
            if field_text:
                lower_text = field_text.lower()
                for kw in ["password=", "pwd:", "secret:", "pass:", "motdepasse="]:
                    if kw in lower_text:
                        raw_findings.append(Finding(
                            rule_code="CLEAR_TEXT_SECRET",
                            rule_title="Secret ou mot de passe en clair détecté",
                            category="security",
                            severity="blocking",
                            target_type="equipment",
                            target_id=eq.id,
                            target_name=f"{eq.name} ({field_name})",
                            message=f"Un mot de passe ou secret semble présent en clair dans le champ '{field_name}'.",
                            recommendation="Supprimez le secret du champ textuel et déclarez-le dans les Configurations avec masquage automatique."
                        ))
                        break

    for cfg in configs:
        if not cfg.is_secret and cfg.value:
            for kw in SECRET_KEYWORDS:
                if kw in cfg.key.lower() and cfg.value != "<SECRET_MASQUÉ>":
                    raw_findings.append(Finding(
                        rule_code="CLEAR_TEXT_SECRET",
                        rule_title="Paramètre sensible non marqué comme secret",
                        category="security",
                        severity="blocking",
                        target_type="configuration",
                        target_id=cfg.id,
                        target_name=f"{cfg.category}.{cfg.key}",
                        message=f"La clé '{cfg.key}' correspond à un terme confidentiel mais n'est pas protégée par masquage.",
                        recommendation="Activez la case 'Secret masqué' sur ce paramètre de configuration."
                    ))
                    break

    # -------------------------------------------------------------
    # Match findings against active overrides
    # -------------------------------------------------------------
    blocking_count = 0
    warning_count = 0
    info_count = 0
    resolved_count = 0

    for finding in raw_findings:
        lookup_key = f"{finding.rule_code}:{finding.target_id}"
        if lookup_key in override_lookup:
            ovr = override_lookup[lookup_key]
            finding.is_overridden = True
            finding.override_id = ovr.id
            finding.override_justification = ovr.justification
            resolved_count += 1
        else:
            if finding.severity == "blocking":
                blocking_count += 1
            elif finding.severity == "warning":
                warning_count += 1
            elif finding.severity == "info":
                info_count += 1

    return raw_findings, {
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "resolved_count": resolved_count,
        "total_findings": len(raw_findings)
    }
