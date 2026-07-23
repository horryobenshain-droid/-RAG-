import math
from dataclasses import replace
from functools import lru_cache
from typing import Any

from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.hybrid_retriever import HybridScore


def rerank_with_cross_encoder(
    question: str,
    results: list[tuple[Document, HybridScore]],
    top_k: int,
    settings: Settings,
) -> list[tuple[Document, HybridScore]]:
    if settings.reranker_provider == "none" or not results:
        return results[:top_k]

    candidates = results[: max(top_k, settings.reranker_candidate_k)]
    model = _load_cross_encoder(settings.reranker_model, settings.reranker_device)
    raw_scores = model.predict(
        [(question, document.page_content) for document, _ in candidates],
        batch_size=settings.reranker_batch_size,
        show_progress_bar=False,
    )

    reranked = []
    for (document, hybrid_score), raw_score in zip(candidates, raw_scores, strict=True):
        reranker_score = _sigmoid(_as_float(raw_score))
        final_score = (
            hybrid_score.final_score * (1 - settings.reranker_weight)
            + reranker_score * settings.reranker_weight
        )
        score = replace(
            hybrid_score,
            reranker_score=round(reranker_score, 4),
            final_score=round(final_score, 4),
            reasons=[
                *hybrid_score.reasons,
                f"CrossEncoder 相关度 {reranker_score:.2f}",
            ],
        )
        reranked.append((document, score))

    reranked.sort(key=lambda item: item[1].final_score, reverse=True)
    return reranked[:top_k]


@lru_cache
def _load_cross_encoder(model_name: str, device: str) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device)


def _as_float(value: Any) -> float:
    if hasattr(value, "item"):
        value = value.item()
    while isinstance(value, list | tuple):
        value = value[0]
    return float(value)


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponent = math.exp(value)
    return exponent / (1 + exponent)
