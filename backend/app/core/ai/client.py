"""Local Ollama AI Client with Graceful Fallback and Explicit AI Tagging."""
import httpx
from typing import Any
from app.core.config import settings
from app.core.ai.prompts import (
    HLD_EXECUTIVE_SUMMARY_PROMPT,
    LLD_ROUTING_SECURITY_PROMPT,
    COMMISSIONING_GUIDE_PROMPT,
    sanitize_prompt_context
)

AI_DISCLAIMER_TAG = "[Généré par IA locale (Ollama) — À vérifier par un ingénieur]"
TEMPLATE_FALLBACK_TAG = "[Généré par template déterministe (Mode secours — IA locale hors-ligne)]"


async def check_ollama_status() -> dict[str, Any]:
    """Check if the local Ollama instance is online and what models are present."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                models = [m.get("name") for m in res.json().get("models", [])]
                return {"online": True, "models": models}
    except Exception:
        pass
    return {"online": False, "models": []}


async def get_active_model(client: httpx.AsyncClient) -> str:
    """Return configured model or best matching available model in Ollama."""
    target = getattr(settings, "OLLAMA_MODEL", getattr(settings, "AI_MODEL_NAME", "qwen2.5-coder:7b"))
    try:
        res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        if res.status_code == 200:
            models = [m.get("name") for m in res.json().get("models", [])]
            if target in models:
                return target
            prefix = target.split(":")[0]
            matching = [m for m in models if prefix in m or m.startswith(prefix)]
            if matching:
                return matching[0]
            if models:
                return models[0]
    except Exception:
        pass
    return target


async def generate_narrative_section(
    section_type: str,  # 'hld_summary', 'lld_routing', 'commissioning'
    context: dict[str, Any],
    use_ai: bool = True
) -> tuple[str, bool]:
    """
    Generate technical narrative. If Ollama is available and use_ai is True,
    calls local LLM with sanitized context. Otherwise gracefully falls back to
    deterministic technical template.
    Returns (content_text, is_ai_generated).
    """
    # 1. Deterministic Fallback Templates
    fallback_texts = {
        "hld_summary": (
            f"Le présent dossier d'architecture générale (High Level Design) définit l'infrastructure cible du projet "
            f"« {context.get('name', 'Infrastructure')} » pour le compte de {context.get('client_name', 'Client')}. "
            f"L'architecture s'articule autour d'un socle matériel éprouvé comprenant {context.get('equipment_count', 0)} équipements "
            f"et {context.get('segments_count', 0)} sous-réseaux logiques cloisonnés. "
            f"Les principes directeurs garantissent la résilience des interconnexions, la séparation stricte des flux "
            f"et l'évolutivité des capacités d'accueil."
        ),
        "lld_routing": (
            f"La politique de segmentation et d'adressage IP repose sur le standard IEEE 802.1Q. "
            f"L'ensemble des passerelles par défaut est hébergé sur les commutateurs de distribution de niveau 3 et le pare-feu de périmètre. "
            f"Les flux inter-VLAN sont soumis à un filtrage d'état (Stateful Firewall) interdisant par défaut "
            f"toute communication non expressément déclarée dans la matrice des flux applicatifs."
        ),
        "commissioning": (
            f"La recette de mise en service a pour objet de valider la conformité matérielle, logicielle et fonctionnelle de l'infrastructure. "
            f"Tous les équipements ({context.get('equipment_count', 0)} matériels répertoriés) doivent satisfaire aux tests de connectivité L2/L3, "
            f"de redondance et de conformité des configurations avant signature du procès-verbal de recette définitive."
        )
    }

    if not use_ai:
        return f"{TEMPLATE_FALLBACK_TAG}\n\n{fallback_texts.get(section_type, '')}", False

    # 2. Select Prompt Template
    if section_type == "hld_summary":
        prompt = HLD_EXECUTIVE_SUMMARY_PROMPT.format(
            reference=sanitize_prompt_context(context.get("reference", "")),
            name=sanitize_prompt_context(context.get("name", "")),
            client_name=sanitize_prompt_context(context.get("client_name", "")),
            scope=sanitize_prompt_context(context.get("scope", "Non spécifié")),
            description=sanitize_prompt_context(context.get("description", "Non spécifiée")),
            equipment_count=context.get("equipment_count", 0),
            segments_count=context.get("segments_count", 0)
        )
    elif section_type == "lld_routing":
        prompt = LLD_ROUTING_SECURITY_PROMPT.format(
            reference=sanitize_prompt_context(context.get("reference", "")),
            name=sanitize_prompt_context(context.get("name", "")),
            segments_summary=sanitize_prompt_context(context.get("segments_summary", "Non défini")),
            routing_devices=sanitize_prompt_context(context.get("routing_devices", "Non défini"))
        )
    else:
        prompt = COMMISSIONING_GUIDE_PROMPT.format(
            reference=sanitize_prompt_context(context.get("reference", "")),
            name=sanitize_prompt_context(context.get("name", "")),
            client_name=sanitize_prompt_context(context.get("client_name", "")),
            equipment_count=context.get("equipment_count", 0)
        )

    # 3. Attempt Ollama Query
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            active_model = await get_active_model(client)
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": active_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 400
                    }
                }
            )
            if resp.status_code == 200:
                ai_text = resp.json().get("response", "").strip()
                if ai_text:
                    return f"{AI_DISCLAIMER_TAG}\n\n{ai_text}", True
    except Exception:
        # Fallback gracefully
        pass

    # 4. Graceful Fallback
    return f"{TEMPLATE_FALLBACK_TAG}\n\n{fallback_texts.get(section_type, '')}", False
