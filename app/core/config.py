from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    llm_provider: str = Field(default="demo", pattern="^(demo|openai)$")
    embedding_provider: str = Field(default="demo", pattern="^(demo|openai)$")

    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5.5"
    openai_embedding_model: str = "text-embedding-3-large"

    chroma_collection: str = "local_rag_knowledge"
    chunk_size: int = 900
    chunk_overlap: int = 150
    default_top_k: int = 4

    project_root: Path = Path(__file__).resolve().parents[2]

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
