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


ASCII_TOKEN_PATTERN = re.compile(r"[A-Za-z_]\w*|\d+")
CJK_SEQUENCE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")
QUERY_NOISE_PHRASES = (
    "请给出",
    "请解释",
    "只讲",
    "并说明",
    "怎么写",
    "如何实现",
    "适用场景",
    "时间复杂度",
    "空间复杂度",
    "复杂度",
    "边界条件",
    "代码模板",
    "模板",
    "模意义",
    "取模",
    "模运算",
)


def rerank_with_keywords(
    question: str,
    results: list[tuple[Document, float | None]],
    top_k: int,
) -> list[tuple[Document, HybridScore]]:
    question_tokens = _question_tokens(question)
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
            normalized_vector * 0.45
            + keyword_score * 0.4
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
    normalized = text.lower().replace("c++", " cpp ").replace("-", "_")
    tokens = {match.group(0) for match in ASCII_TOKEN_PATTERN.finditer(normalized)}
    for match in CJK_SEQUENCE_PATTERN.finditer(normalized):
        sequence = match.group(0)
        if 2 <= len(sequence) <= 4:
            tokens.add(sequence)
        for size in range(2, min(4, len(sequence)) + 1):
            tokens.update(
                sequence[index : index + size]
                for index in range(len(sequence) - size + 1)
            )
    return tokens


def _question_tokens(question: str) -> set[str]:
    focused_question = question
    for phrase in QUERY_NOISE_PHRASES:
        focused_question = focused_question.replace(phrase, " ")

    tokens = _tokens(focused_question)
    if "快速幂" in question and "矩阵快速幂" not in question:
        tokens.add("qpow")
    if any(phrase in question for phrase in ("模意义", "取模", "模运算")):
        tokens.add("mod")
    return tokens
