from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import Base, async_engine
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.sites import router as sites_router
from app.api.inventory import router as inventory_router
from app.api.network import router as network_router
from app.api.configurations import router as configurations_router
from app.api.imports import router as imports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist in dev/test if not using migrations
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await async_engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API pour la constitution, validation et génération documentaire d'infrastructure IT.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler to avoid exposing stack traces or secrets
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Une erreur interne est survenue. Veuillez contacter un administrateur."}
    )

# Include Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix=settings.API_PREFIX)
app.include_router(projects_router, prefix=settings.API_PREFIX)
app.include_router(sites_router, prefix=settings.API_PREFIX)
app.include_router(inventory_router, prefix=settings.API_PREFIX)
app.include_router(network_router, prefix=settings.API_PREFIX)
app.include_router(configurations_router, prefix=settings.API_PREFIX)
app.include_router(imports_router, prefix=settings.API_PREFIX)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "documentation": "/api/docs",
        "health": "/api/health"
    }
