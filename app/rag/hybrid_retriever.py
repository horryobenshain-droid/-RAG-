import re
from dataclasses import dataclass

from langchain_core.documents import Document


@dataclass
class HybridScore:
    vector_score: float | None
    keyword_score: float
    filename_score: float
    symbol_score: float
    final_score: float
    matched_keywords: list[str]


TOKEN_PATTERN = re.compile(r"[A-Za-z_]\w*|\d+|[\u4e00-\u9fff]{2,}")


def rerank_with_keywords(
    question: str,
    results: list[tuple[Document, float | None]],
    top_k: int,
) -> list[tuple[Document, HybridScore]]:
    question_tokens = _tokens(question)
    scored = []

    for document, vector_score in results:
        keyword_score, matched_keywords = _keyword_score(question_tokens, document.page_content)
        filename_score = _metadata_score(
            question_tokens,
            document.metadata.get("original_file_name"),
        )
        symbol_score = _metadata_score(question_tokens, document.metadata.get("symbol_name"))
        normalized_vector = vector_score if vector_score is not None else 0.0
        final_score = (
            normalized_vector * 0.65
            + keyword_score * 0.2
            + filename_score * 0.1
            + symbol_score * 0.05
        )
        scored.append(
            (
                document,
                HybridScore(
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    filename_score=filename_score,
                    symbol_score=symbol_score,
                    final_score=round(final_score, 4),
                    matched_keywords=matched_keywords,
                ),
            )
        )

    scored.sort(key=lambda item: item[1].final_score, reverse=True)
    return scored[:top_k]


def _keyword_score(question_tokens: set[str], content: str) -> tuple[float, list[str]]:
    if not question_tokens:
        return 0.0, []
    content_tokens = _tokens(content)
    matched = sorted(question_tokens & content_tokens)
    return len(matched) / max(len(question_tokens), 1), matched


def _metadata_score(question_tokens: set[str], value: object) -> float:
    if not question_tokens or value is None:
        return 0.0
    metadata_tokens = _tokens(str(value))
    if not metadata_tokens:
        return 0.0
    return len(question_tokens & metadata_tokens) / max(len(question_tokens), 1)


def _tokens(text: str) -> set[str]:
    normalized = text.lower().replace("-", "_")
    return {match.group(0) for match in TOKEN_PATTERN.finditer(normalized)}
