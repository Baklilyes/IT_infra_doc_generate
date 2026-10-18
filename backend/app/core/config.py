from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "IT Infrastructure Documentation Generator"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production-min-32-chars-long!", min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Initial Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@infra-doc.local"
    ADMIN_PASSWORD: str = "AdminStrongPassword123!"

    # Database
    POSTGRES_USER: str = "infradoc"
    POSTGRES_PASSWORD: str = "infradoc_secure_pass"
    POSTGRES_DB: str = "infradoc_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://infradoc:infradoc_secure_pass@localhost:5432/infradoc_db"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://infradoc:infradoc_secure_pass@localhost:5432/infradoc_db"
    )

    # Local Ollama AI Runtime (Internal Network Only)
    AI_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AI_MODEL_NAME: str = "qwen2.5-coder:7b"
    AI_TIMEOUT_SECONDS: int = 120
    AI_MAX_CONTEXT_TOKENS: int = 8192
    AI_MAX_OUTPUT_TOKENS: int = 4096

    # Storage Paths
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage"))
    TEMPLATES_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates"))

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
