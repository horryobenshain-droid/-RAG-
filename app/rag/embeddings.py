import hashlib
import math
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.core.config import Settings


class HashEmbeddings(Embeddings):
    """Small deterministic embedding model for local demos and tests."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def get_embeddings(settings: Settings) -> Embeddings:
    return _get_embeddings_cached(
        settings.embedding_provider,
        settings.local_embedding_model,
        settings.openai_embedding_model,
        settings.openai_api_key,
        settings.openai_base_url,
    )


@lru_cache(maxsize=8)
def _get_embeddings_cached(
    provider: str,
    local_model: str,
    openai_model: str,
    openai_api_key: str | None,
    openai_base_url: str | None,
) -> Embeddings:
    if provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings

        try:
            return HuggingFaceEmbeddings(
                model_name=local_model,
                model_kwargs={"local_files_only": True},
                encode_kwargs={"normalize_embeddings": True},
            )
        except OSError:
            return HuggingFaceEmbeddings(
                model_name=local_model,
                encode_kwargs={"normalize_embeddings": True},
            )

    if provider == "openai":
        if not openai_api_key:
            msg = "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai."
            raise ValueError(msg)

        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=openai_model,
            api_key=openai_api_key,
            base_url=openai_base_url,
        )

    return HashEmbeddings()


def _tokenize(text: str) -> list[str]:
    normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
    tokens = normalized.split()
    return tokens or [text.strip().lower()]
