import math
import re
from datetime import UTC, datetime
from statistics import fmean
from time import perf_counter

from app.core.config import Settings
from app.evaluation.models import (
    EvaluatedSource,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationDataset,
    EvaluationRun,
    EvaluationSummary,
    ExpectedSource,
    ModelProfile,
    ProfileEvaluationResult,
)
from app.rag.service import RetrievedSource, answer_question

CITATION_PATTERN = re.compile(r"\bsource\s*(\d+)\b", re.IGNORECASE)


def evaluate_dataset(
    dataset: EvaluationDataset,
    dataset_path: str,
    profiles: list[ModelProfile],
    base_settings: Settings,
    top_k_override: int | None = None,
) -> EvaluationRun:
    if top_k_override is not None and not 1 <= top_k_override <= 50:
        msg = "top_k_override must be between 1 and 50."
        raise ValueError(msg)
    if not profiles:
        msg = "At least one model profile is required."
        raise ValueError(msg)

    profile_results = [
        _evaluate_profile(dataset, profile, base_settings, top_k_override) for profile in profiles
    ]
    return EvaluationRun(
        dataset_name=dataset.name,
        dataset_path=dataset_path,
        generated_at=_utc_now(),
        top_k_override=top_k_override,
        profiles=profile_results,
    )


def _evaluate_profile(
    dataset: EvaluationDataset,
    profile: ModelProfile,
    base_settings: Settings,
    top_k_override: int | None,
) -> ProfileEvaluationResult:
    settings = _profile_settings(base_settings, profile)
    started_at = _utc_now()
    started = perf_counter()
    results = [_evaluate_case(case, settings, top_k_override) for case in dataset.cases]
    duration_ms = (perf_counter() - started) * 1000
    return ProfileEvaluationResult(
        profile_name=profile.name,
        llm_provider=settings.llm_provider,
        llm_model=_llm_model_name(settings),
        started_at=started_at,
        duration_ms=round(duration_ms, 2),
        summary=_summarize(results),
        cases=results,
        retrieval_strategy=settings.retrieval_strategy,
        retrieval_fetch_k=settings.retrieval_fetch_k,
        reranker_provider=settings.reranker_provider,
        reranker_model=(
            settings.reranker_model if settings.reranker_provider == "cross_encoder" else None
        ),
    )


def _evaluate_case(
    case: EvaluationCase,
    settings: Settings,
    top_k_override: int | None,
) -> EvaluationCaseResult:
    started = perf_counter()
    try:
        result = answer_question(
            case.question,
            top_k_override or case.top_k,
            settings,
            case.answer_mode,
        )
    except Exception as exc:
        return EvaluationCaseResult(
            case_id=case.id,
            question=case.question,
            status="error",
            elapsed_ms=round((perf_counter() - started) * 1000, 2),
            recall_at_k=0.0 if case.expected_sources else None,
            citation_hit=False if case.require_citation else None,
            answer_keyword_recall=0.0 if case.expected_answer_keywords else None,
            missing_answer_keywords=case.expected_answer_keywords,
            error=str(exc),
        )

    sources = [
        _evaluated_source(index, source) for index, source in enumerate(result.sources, start=1)
    ]
    recall_at_k = _recall_at_k(case.expected_sources, sources)
    citation_hit = _citation_hit(
        result.answer,
        sources,
        case.expected_sources,
        case.require_citation,
    )
    keyword_recall, missing_keywords = _answer_keyword_recall(
        result.answer,
        case.expected_answer_keywords,
    )
    forbidden_keywords = _matched_keywords(result.answer, case.forbidden_answer_keywords)

    passed = not forbidden_keywords
    if recall_at_k is not None:
        passed = passed and recall_at_k == 1.0
    if citation_hit is not None:
        passed = passed and citation_hit
    if keyword_recall is not None:
        passed = passed and keyword_recall == 1.0

    return EvaluationCaseResult(
        case_id=case.id,
        question=case.question,
        status="passed" if passed else "failed",
        answer=result.answer,
        sources=sources,
        elapsed_ms=round(result.elapsed_ms, 2),
        recall_at_k=recall_at_k,
        citation_hit=citation_hit,
        answer_keyword_recall=keyword_recall,
        missing_answer_keywords=missing_keywords,
        matched_forbidden_keywords=forbidden_keywords,
        retrieval_strategy=result.retrieval_strategy,
        candidate_count=result.candidate_count,
        retrieval_ms=round(result.retrieval_ms, 2),
        reranking_ms=round(result.reranking_ms, 2),
        generation_ms=round(result.generation_ms, 2),
    )


def _profile_settings(base_settings: Settings, profile: ModelProfile) -> Settings:
    values = base_settings.model_dump()
    values.update(profile.overrides)
    settings = Settings(**values)
    settings.ensure_directories()
    return settings


def _evaluated_source(source_id: int, source: RetrievedSource) -> EvaluatedSource:
    metadata = source.document.metadata
    return EvaluatedSource(
        source_id=source_id,
        file_name=str(metadata.get("original_file_name", "unknown")),
        chunk_id=metadata.get("chunk_id"),
        document_id=_optional_str(metadata.get("document_id")),
        symbol_name=_optional_str(metadata.get("symbol_name")),
        score=source.score,
        vector_score=source.hybrid_score.vector_score,
        keyword_score=source.hybrid_score.keyword_score,
        filename_score=source.hybrid_score.filename_score,
        symbol_score=source.hybrid_score.symbol_score,
        reranker_score=source.hybrid_score.reranker_score,
        retrieval_rank=source.hybrid_score.retrieval_rank,
        matched_keywords=source.hybrid_score.matched_keywords,
        reasons=source.hybrid_score.reasons,
        preview=source.document.page_content.strip()[:300],
    )


def _recall_at_k(
    expected_sources: list[ExpectedSource],
    sources: list[EvaluatedSource],
) -> float | None:
    if not expected_sources:
        return None
    hits = sum(
        any(_source_matches(expected, source) for source in sources)
        for expected in expected_sources
    )
    return round(hits / len(expected_sources), 4)


def _citation_hit(
    answer: str,
    sources: list[EvaluatedSource],
    expected_sources: list[ExpectedSource],
    require_citation: bool,
) -> bool | None:
    if not require_citation:
        return None
    cited_source_ids = {int(match) for match in CITATION_PATTERN.findall(answer)}
    cited_sources = [source for source in sources if source.source_id in cited_source_ids]
    if not expected_sources:
        return bool(cited_sources)
    return any(
        _source_matches(expected, source)
        for expected in expected_sources
        for source in cited_sources
    )


def _source_matches(expected: ExpectedSource, source: EvaluatedSource) -> bool:
    comparisons = (
        (expected.file_name, source.file_name, True),
        (expected.chunk_id, source.chunk_id, False),
        (expected.document_id, source.document_id, False),
        (expected.symbol_name, source.symbol_name, True),
    )
    for expected_value, actual_value, case_insensitive in comparisons:
        if expected_value is None:
            continue
        if actual_value is None:
            return False
        if case_insensitive:
            if str(expected_value).casefold() != str(actual_value).casefold():
                return False
        elif str(expected_value) != str(actual_value):
            return False
    return True


def _answer_keyword_recall(answer: str, keywords: list[str]) -> tuple[float | None, list[str]]:
    if not keywords:
        return None, []
    normalized_answer = answer.casefold()
    missing = [keyword for keyword in keywords if keyword.casefold() not in normalized_answer]
    return round((len(keywords) - len(missing)) / len(keywords), 4), missing


def _matched_keywords(answer: str, keywords: list[str]) -> list[str]:
    normalized_answer = answer.casefold()
    return [keyword for keyword in keywords if keyword.casefold() in normalized_answer]


def _summarize(results: list[EvaluationCaseResult]) -> EvaluationSummary:
    passed_cases = sum(result.status == "passed" for result in results)
    failed_cases = sum(result.status == "failed" for result in results)
    error_cases = sum(result.status == "error" for result in results)
    recalls = [result.recall_at_k for result in results if result.recall_at_k is not None]
    citations = [result.citation_hit for result in results if result.citation_hit is not None]
    keyword_recalls = [
        result.answer_keyword_recall
        for result in results
        if result.answer_keyword_recall is not None
    ]
    latencies = [
        result.elapsed_ms
        for result in results
        if result.status != "error" and result.elapsed_ms is not None
    ]
    return EvaluationSummary(
        total_cases=len(results),
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        error_cases=error_cases,
        pass_rate=_rounded_mean([1.0 if result.status == "passed" else 0.0 for result in results])
        or 0.0,
        recall_at_k=_rounded_mean(recalls),
        citation_hit_rate=_rounded_mean([1.0 if value else 0.0 for value in citations]),
        answer_keyword_recall=_rounded_mean(keyword_recalls),
        average_latency_ms=_rounded_mean(latencies, digits=2),
        p95_latency_ms=_percentile_95(latencies),
    )


def _rounded_mean(values: list[float], digits: int = 4) -> float | None:
    if not values:
        return None
    return round(fmean(values), digits)


def _percentile_95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return round(ordered[index], 2)


def _llm_model_name(settings: Settings) -> str:
    if settings.llm_provider == "openai":
        return settings.openai_chat_model
    if settings.llm_provider == "ollama":
        return settings.ollama_chat_model
    return "demo-snippet-answer"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
