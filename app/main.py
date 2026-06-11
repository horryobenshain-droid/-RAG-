from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Local RAG Knowledge Base",
    description="A local RAG knowledge base system built with FastAPI, LangChain and Chroma.",
    version="0.1.0",
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
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
    }
