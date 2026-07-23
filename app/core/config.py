from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

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
    ollama_num_predict: int = Field(default=1024, gt=0)
    ollama_top_p: float = Field(default=0.9, gt=0, le=1)
    ollama_repeat_penalty: float = Field(default=1.1, ge=1)
    ollama_timeout_seconds: float = Field(default=120.0, gt=0)

    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"

    chroma_collection: str = "local_rag_knowledge"
    chunk_size: int = Field(default=900, ge=100, le=10000)
    chunk_overlap: int = Field(default=150, ge=0, le=5000)
    default_top_k: int = Field(default=4, ge=1, le=50)

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
    def registry_path(self) -> Path:
        return self.data_dir / "registry.json"

    @property
    def api_base_url(self) -> str:
        return f"http://{self.api_host}:{self.api_port}"

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
