from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Local RAG Knowledge Base",
    description="A local RAG knowledge base system built with FastAPI, LangChain and Chroma.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "llm_model": _llm_model_name(),
        "embedding_provider": settings.embedding_provider,
        "embedding_model": _embedding_model_name(),
    }


def _llm_model_name() -> str:
    if settings.llm_provider == "openai":
        return settings.openai_chat_model
    if settings.llm_provider == "ollama":
        return settings.ollama_chat_model
    return "demo-snippet-answer"


def _embedding_model_name() -> str:
    if settings.embedding_provider == "local":
        return settings.local_embedding_model
    if settings.embedding_provider == "openai":
        return settings.openai_embedding_model
    return "hash-embeddings"
