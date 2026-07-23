from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.hybrid_retriever import HybridScore
from app.rag.reranker import rerank_with_cross_encoder


class FakeCrossEncoder:
    def predict(self, pairs: list[tuple[str, str]], **kwargs: Any) -> list[float]:
        assert pairs == [("query", "first"), ("query", "second")]
        assert kwargs == {"batch_size": 8, "show_progress_bar": False}
        return [-2.0, 2.0]


def _hybrid_score(final_score: float) -> HybridScore:
    return HybridScore(
        vector_score=final_score,
        keyword_score=0.0,
        filename_score=0.0,
        symbol_score=0.0,
        final_score=final_score,
        matched_keywords=[],
        reasons=["向量检索候选"],
    )


def test_cross_encoder_can_change_hybrid_order(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    first = Document(page_content="first")
    second = Document(page_content="second")
    monkeypatch.setattr(
        "app.rag.reranker._load_cross_encoder",
        lambda model, device: FakeCrossEncoder(),
    )
    settings = Settings(
        project_root=tmp_path,
        reranker_provider="cross_encoder",
        reranker_batch_size=8,
        reranker_candidate_k=2,
        reranker_weight=0.8,
    )

    results = rerank_with_cross_encoder(
        "query",
        [(first, _hybrid_score(0.9)), (second, _hybrid_score(0.4))],
        2,
        settings,
    )

    assert results[0][0] is second
    assert results[0][1].reranker_score is not None
    assert any("CrossEncoder" in reason for reason in results[0][1].reasons)
