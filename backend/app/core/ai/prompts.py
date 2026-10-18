"""Versioned prompts for local LLM inference and secret sanitization."""
import re
from typing import Any
from app.core.network_validator import SECRET_KEYWORDS, mask_secret

PROMPT_VERSION = "1.0.0"

HLD_EXECUTIVE_SUMMARY_PROMPT = """Tu es un Architecte Infrastructure Réseau et Système Sénior certifié.
Rédige une synthèse générale d'architecture (High Level Design) pour le projet suivant :
- Référence Projet : {reference}
- Nom du Projet : {name}
- Client : {client_name}
- Objectifs et périmètre : {scope}
- Description technique : {description}
- Nombre d'équipements : {equipment_count}
- Nombre de sous-réseaux / VLANs : {segments_count}

Règles impératives :
1. Reste factuel, professionnel, et structuré.
2. Explique la stratégie de haute disponibilité, de segmentation de sécurité et d'évolutivité.
3. Rédige en français sous forme de 2 à 3 paragraphes clairs.
"""

LLD_ROUTING_SECURITY_PROMPT = """Tu es un Ingénieur Réseau et Sécurité Sénior.
Rédige la section 'Principes d'interconnexion, routage et sécurité' pour le dossier technique détaillé (Low Level Design) :
- Projet : {reference} ({name})
- Sous-réseaux et VLANs : {segments_summary}
- Équipements de sécurité et de routage : {routing_devices}

Règles impératives :
1. Détaille les choix de segmentation 802.1Q, l'isolation inter-VLAN et le filtrage pare-feu.
2. Explique la politique de passerelle par défaut (SVI / VRRP / HSRP) et le cloisonnement de la DMZ.
3. Rédige en français avec rigueur technique.
"""

COMMISSIONING_GUIDE_PROMPT = """Tu es un Responsable de Recette et Déploiement Infrastructure.
Rédige les prérequis et consignes de validation opérationnelle pour le dossier de recette du projet :
- Projet : {reference} ({name})
- Client : {client_name}
- Total équipements à tester : {equipment_count}

Règles impératives :
1. Définis les critères de validation des tests d'interconnexion (ping, MTU, trunking, redondance).
2. Précise les conditions d'acceptation sans réserve pour le procès-verbal de recette.
"""


def sanitize_prompt_context(text: str | None) -> str:
    """
    Strictly sanitize any text before sending to LLM (Section 9.2).
    Ensures no passwords, secrets, tokens, or private community strings leak into prompt.
    """
    if not text:
        return ""

    sanitized = text
    # Mask common sensitive key-value pairs
    for kw in SECRET_KEYWORDS:
        pattern = rf"({kw}\s*[:=]\s*)([^\s,;\n]+)"
        sanitized = re.sub(pattern, r"\1<SECRET_MASQUÉ>", sanitized, flags=re.IGNORECASE)

    return sanitized
