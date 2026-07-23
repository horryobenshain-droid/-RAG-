import re
from dataclasses import dataclass, field

from langchain_core.documents import Document


@dataclass
class HybridScore:
    vector_score: float | None
    keyword_score: float
    filename_score: float
    symbol_score: float
    final_score: float
    matched_keywords: list[str]
    retrieval_rank: int = 0
    reranker_score: float | None = None
    reasons: list[str] = field(default_factory=list)


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
    *,
    vector_weight: float = 0.45,
    keyword_weight: float = 0.4,
    filename_weight: float = 0.1,
    symbol_weight: float = 0.05,
    retrieval_strategy: str = "similarity",
) -> list[tuple[Document, HybridScore]]:
    question_tokens = _question_tokens(question)
    scored = []

    for retrieval_rank, (document, vector_score) in enumerate(results, start=1):
        keyword_score, matched_keywords = _keyword_score(question_tokens, document.page_content)
        filename_score = _metadata_score(
            question_tokens,
            document.metadata.get("original_file_name"),
        )
        symbol_score = _metadata_score(question_tokens, document.metadata.get("symbol_name"))
        normalized_vector = vector_score if vector_score is not None else 0.0
        final_score = (
            normalized_vector * vector_weight
            + keyword_score * keyword_weight
            + filename_score * filename_weight
            + symbol_score * symbol_weight
        )
        reasons = _hit_reasons(
            vector_score,
            matched_keywords,
            filename_score,
            symbol_score,
            retrieval_strategy,
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
                    retrieval_rank=retrieval_rank,
                    reasons=reasons,
                ),
            )
        )

    scored.sort(key=lambda item: item[1].final_score, reverse=True)
    return scored[:top_k]


def _hit_reasons(
    vector_score: float | None,
    matched_keywords: list[str],
    filename_score: float,
    symbol_score: float,
    retrieval_strategy: str,
) -> list[str]:
    reasons = []
    if vector_score is not None:
        reasons.append(f"向量相关度 {vector_score:.2f}")
    if matched_keywords:
        reasons.append(f"关键词命中：{', '.join(matched_keywords)}")
    if filename_score > 0:
        reasons.append("文件名与问题匹配")
    if symbol_score > 0:
        reasons.append("代码符号与问题匹配")
    if retrieval_strategy == "mmr":
        reasons.append("MMR 多样性候选")
    return reasons or ["向量检索候选"]


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
                sequence[index : index + size] for index in range(len(sequence) - size + 1)
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
