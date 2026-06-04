import os
from pydantic_settings import BaseSettings
from functools import lru_cache

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")


class Settings(BaseSettings):
    PROJECT_NAME: str = "BizPlot Agent"
    VERSION: str = "0.1.0"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "finpilot"
    POSTGRES_USER: str = "finpilot"
    POSTGRES_PASSWORD: str = "finpilot2026"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM (Ollama OpenAI-compatible)
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "finpilot"
    LLM_API_KEY: str = "ollama"
    LLM_MAX_TOKENS: int = 900
    LLM_TEMPERATURE: float = 0.2

    # Ollama native API (임베딩용 — torch 비의존)
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Fallback LLM (external API)
    FALLBACK_LLM_PROVIDER: str = "openai"  # openai | anthropic
    FALLBACK_LLM_API_KEY: str = ""
    FALLBACK_LLM_MODEL: str = "gpt-4o-mini"

    # Public Data APIs
    DATA_GO_KR_KEY: str = ""
    KOSIS_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""
    TOUR_API_KEY: str = ""

    # OAuth Login
    FRONTEND_URL: str = "http://localhost:3000"
    KAKAO_REST_API_KEY: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:8000/api/auth/kakao/callback"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # Security
    SECRET_KEY: str = "finpilot-dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "finpilot"
    MINIO_SECRET_KEY: str = "finpilot2026"
    UPLOAD_DIR: str = "/SSD/guest/chojoonghui/FinPilot/data/uploads"

    # Embedding model (ollama — bge-m3, 한국어 멀티링궐 1024차원)
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIM: int = 1024

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
