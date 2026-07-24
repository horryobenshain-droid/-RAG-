import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_allowed_origins: str = "http://127.0.0.1:8501,http://localhost:8501"

    llm_provider: str = Field(default="demo", pattern="^(demo|openai|ollama)$")
    embedding_provider: str = Field(default="demo", pattern="^(demo|openai|local)$")

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_chat_model: str = "gpt-5.5"
    openai_embedding_model: str = "text-embedding-3-large"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    ollama_temperature: float = Field(default=0.2, ge=0)
    ollama_num_ctx: int = Field(default=8192, gt=0)
    ollama_num_predict: int = Field(default=512, gt=0)
    ollama_top_p: float = Field(default=0.9, gt=0, le=1)
    ollama_repeat_penalty: float = Field(default=1.1, ge=1)
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)

    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"

    chroma_collection: str = "local_rag_knowledge"
    chunk_size: int = Field(default=900, ge=100, le=10000)
    chunk_overlap: int = Field(default=150, ge=0, le=5000)
    default_top_k: int = Field(default=4, ge=1, le=10)

    retrieval_strategy: Literal["similarity", "mmr"] = "similarity"
    retrieval_fetch_k: int = Field(default=40, ge=1, le=200)
    mmr_lambda_mult: float = Field(default=0.5, ge=0, le=1)

    hybrid_vector_weight: float = Field(default=0.45, ge=0, le=1)
    hybrid_keyword_weight: float = Field(default=0.4, ge=0, le=1)
    hybrid_filename_weight: float = Field(default=0.1, ge=0, le=1)
    hybrid_symbol_weight: float = Field(default=0.05, ge=0, le=1)

    reranker_provider: Literal["none", "cross_encoder"] = "none"
    reranker_model: str = Field(default="BAAI/bge-reranker-base", min_length=1)
    reranker_device: str = Field(default="cpu", min_length=1)
    reranker_candidate_k: int = Field(default=12, ge=1, le=100)
    reranker_batch_size: int = Field(default=16, ge=1, le=256)
    reranker_weight: float = Field(default=0.6, ge=0, le=1)

    repository_max_archive_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    repository_max_files: int = Field(default=2000, ge=1, le=20000)
    repository_max_file_bytes: int = Field(default=2 * 1024 * 1024, ge=1024)
    repository_max_total_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)

    project_root: Path = Path(__file__).resolve().parents[2]

    @model_validator(mode="after")
    def validate_retrieval_settings(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            msg = "CHUNK_OVERLAP must be smaller than CHUNK_SIZE."
            raise ValueError(msg)
        if self.retrieval_fetch_k < self.default_top_k:
            msg = "RETRIEVAL_FETCH_K must be greater than or equal to DEFAULT_TOP_K."
            raise ValueError(msg)

        weight_total = sum(
            (
                self.hybrid_vector_weight,
                self.hybrid_keyword_weight,
                self.hybrid_filename_weight,
                self.hybrid_symbol_weight,
            )
        )
        if abs(weight_total - 1.0) > 1e-6:
            msg = "HYBRID_*_WEIGHT values must add up to 1.0."
            raise ValueError(msg)
        return self

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def repository_dir(self) -> Path:
        return self.data_dir / "repositories"

    @property
    def registry_path(self) -> Path:
        return self.data_dir / "registry.json"

    @property
    def repository_registry_path(self) -> Path:
        return self.data_dir / "repositories.json"

    @property
    def runtime_config_path(self) -> Path:
        return self.data_dir / "runtime_config.json"

    @property
    def api_base_url(self) -> str:
        return f"http://{self.api_host}:{self.api_port}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.repository_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.runtime_config_path.exists():
        try:
            payload = json.loads(settings.runtime_config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            overrides = {
                key: value
                for key, value in payload.items()
                if key in RUNTIME_CONFIG_FIELDS
            }
            if overrides:
                settings = Settings(**overrides)
    settings.ensure_directories()
    return settings


RUNTIME_CONFIG_FIELDS = frozenset(
    {
        "llm_provider",
        "embedding_provider",
        "openai_api_key",
        "openai_base_url",
        "openai_chat_model",
        "openai_embedding_model",
        "ollama_base_url",
        "ollama_chat_model",
        "ollama_temperature",
        "ollama_num_ctx",
        "ollama_num_predict",
        "ollama_top_p",
        "ollama_repeat_penalty",
        "ollama_timeout_seconds",
        "local_embedding_model",
        "chunk_size",
        "chunk_overlap",
        "default_top_k",
        "retrieval_strategy",
        "retrieval_fetch_k",
        "mmr_lambda_mult",
        "hybrid_vector_weight",
        "hybrid_keyword_weight",
        "hybrid_filename_weight",
        "hybrid_symbol_weight",
        "reranker_provider",
        "reranker_model",
        "reranker_device",
        "reranker_candidate_k",
        "reranker_batch_size",
        "reranker_weight",
    }
)


def update_runtime_settings(settings: Settings, updates: dict[str, Any]) -> Settings:
    """Validate, persist and activate a supported runtime configuration update."""

    unsupported = set(updates) - RUNTIME_CONFIG_FIELDS
    if unsupported:
        fields = ", ".join(sorted(unsupported))
        raise ValueError(f"不支持动态修改以下配置：{fields}")

    merged = settings.model_dump()
    merged.update(updates)
    candidate = Settings(**merged)
    candidate.ensure_directories()
    payload = {
        field: getattr(candidate, field)
        for field in sorted(RUNTIME_CONFIG_FIELDS)
        if getattr(candidate, field) is not None
    }

    target = candidate.runtime_config_path
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(target)

    for field in RUNTIME_CONFIG_FIELDS:
        setattr(settings, field, getattr(candidate, field))
    get_settings.cache_clear()
    return candidate
