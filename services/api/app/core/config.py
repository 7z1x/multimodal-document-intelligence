from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://mdi:mdi@localhost:5432/mdi"
    storage_dir: Path = REPOSITORY_ROOT / "storage" / "documents"
    max_upload_bytes: int = Field(default=15 * 1024 * 1024, gt=0)
    max_document_pages: int = Field(default=10, gt=0)
    max_image_pixels: int = Field(default=40_000_000, gt=0)
    native_text_min_characters: int = Field(default=40, ge=0)
    extraction_backend: str = "heuristic"
    opencode_base_url: str = "http://127.0.0.1:4096"
    opencode_provider: str = "opencode"
    opencode_model: str = "muse-spark-1.3-contributor-free"
    opencode_timeout_seconds: float = Field(default=120, gt=0)
    opencode_directory: Path = REPOSITORY_ROOT
    max_extraction_characters: int = Field(default=30_000, gt=0)
    rag_chunk_size: int = Field(default=900, ge=100)
    rag_chunk_overlap: int = Field(default=120, ge=0)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_min_relevance: float = Field(default=0.15, ge=0, le=1)
    rag_rerank_model_weight: float = Field(default=0.65, ge=0, le=1)
    agent_max_retrieval_attempts: int = Field(default=2, ge=1, le=5)
    audit_log_dir: Path = REPOSITORY_ROOT / "storage" / "audit-logs"
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "http://localhost:3001"
    langfuse_timeout_seconds: int = Field(default=5, ge=1, le=30)
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("storage_dir", "audit_log_dir", mode="after")
    @classmethod
    def resolve_repository_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else REPOSITORY_ROOT / value


@lru_cache
def get_settings() -> Settings:
    return Settings()
