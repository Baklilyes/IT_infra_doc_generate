import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings

router = APIRouter(tags=["Health & Diagnostics"])

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check distinguishing:
    - Backend API status
    - PostgreSQL database connectivity
    - Local Ollama AI runtime accessibility
    - Local AI model availability
    """
    health = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "backend": {"status": "operational"},
            "database": {"status": "unknown"},
            "ai_runtime": {"status": "disabled", "model": settings.AI_MODEL_NAME}
        }
    }

    # 1. Database Check
    try:
        await db.execute(text("SELECT 1"))
        health["components"]["database"]["status"] = "operational"
    except Exception as e:
        health["components"]["database"]["status"] = "degraded"
        health["components"]["database"]["error"] = "Database connection error"
        health["status"] = "degraded"

    # 2. Local Ollama AI Runtime & Model Check
    if settings.AI_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    # Check if configured model or model:tag exists
                    configured_model = settings.AI_MODEL_NAME
                    model_found = any(
                        configured_model in m or m.startswith(configured_model.split(":")[0])
                        for m in models
                    )
                    if model_found:
                        health["components"]["ai_runtime"] = {
                            "status": "operational",
                            "model": settings.AI_MODEL_NAME,
                            "available_models": models
                        }
                    else:
                        health["components"]["ai_runtime"] = {
                            "status": "model_missing",
                            "model": settings.AI_MODEL_NAME,
                            "detail": f"Modèle '{settings.AI_MODEL_NAME}' non téléchargé dans Ollama.",
                            "available_models": models
                        }
                else:
                    health["components"]["ai_runtime"] = {
                        "status": "unavailable",
                        "model": settings.AI_MODEL_NAME,
                        "detail": f"Ollama HTTP status {resp.status_code}"
                    }
        except Exception:
            health["components"]["ai_runtime"] = {
                "status": "unavailable",
                "model": settings.AI_MODEL_NAME,
                "detail": "Runtime Ollama local non joignable (fonctions non IA pleinement opérationnelles)"
            }

    return health
