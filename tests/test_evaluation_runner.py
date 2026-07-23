from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.core.config import Settings
from app.evaluation.models import EvaluationDataset, ModelProfile
from app.evaluation.report import write_json_report, write_markdown_report
from app.evaluation.runner import evaluate_dataset
from app.rag.hybrid_retriever import HybridScore
from app.rag.service import AnswerResult, RetrievedSource


def test_evaluator_computes_metrics_and_writes_reports(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    source = RetrievedSource(
        document=Document(
            page_content="qpow computes modular powers in O(log exponent).",
            metadata={
                "original_file_name": "quick_power.cpp",
                "chunk_id": 0,
                "document_id": "doc-1",
                "symbol_name": "qpow",
            },
        ),
        score=0.91,
        hybrid_score=HybridScore(
            vector_score=0.85,
            keyword_score=1.0,
            filename_score=0.0,
            symbol_score=1.0,
            final_score=0.91,
            matched_keywords=["qpow"],
        ),
    )

    def fake_answer_question(*args: Any, **kwargs: Any) -> AnswerResult:
        return AnswerResult(
            answer="qpow 使用二进制拆分，复杂度为 O(log exponent)。引用：source 1",
            sources=[source],
            elapsed_ms=25.0,
            llm_provider="demo",
            llm_model="demo-snippet-answer",
            embedding_provider="demo",
            embedding_model="hash-embeddings",
            answer_mode="strict",
            answer_basis="knowledge_base",
        )

    monkeypatch.setattr("app.evaluation.runner.answer_question", fake_answer_question)
    dataset = EvaluationDataset.model_validate(
        {
            "name": "quick power",
            "cases": [
                {
                    "id": "qpow",
                    "question": "qpow complexity?",
                    "expected_sources": [
                        {"file_name": "quick_power.cpp", "symbol_name": "qpow"}
                    ],
                    "expected_answer_keywords": ["qpow", "O(log"],
                    "forbidden_answer_keywords": ["矩阵快速幂"],
                    "require_citation": True,
                }
            ],
        }
    )
    settings = Settings(
        llm_provider="demo",
        embedding_provider="demo",
        project_root=tmp_path,
    )

    run = evaluate_dataset(
        dataset=dataset,
        dataset_path="dataset.json",
        profiles=[ModelProfile(name="demo")],
        base_settings=settings,
    )

    summary = run.profiles[0].summary
    result = run.profiles[0].cases[0]
    assert result.status == "passed"
    assert result.recall_at_k == 1.0
    assert result.citation_hit is True
    assert result.answer_keyword_recall == 1.0
    assert summary.pass_rate == 1.0
    assert summary.recall_at_k == 1.0
    assert summary.citation_hit_rate == 1.0
    assert summary.average_latency_ms == 25.0

    markdown_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    write_markdown_report(run, markdown_path)
    write_json_report(run, json_path)

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "RAG 评估报告" in markdown
    assert "100.0%" in markdown
    assert "quick_power.cpp" in markdown
    assert '"citation_hit": true' in json_path.read_text(encoding="utf-8")


def test_evaluator_isolates_case_errors(monkeypatch: Any, tmp_path: Path) -> None:
    def failing_answer_question(*args: Any, **kwargs: Any) -> AnswerResult:
        raise ValueError("model unavailable")

    monkeypatch.setattr("app.evaluation.runner.answer_question", failing_answer_question)
    dataset = EvaluationDataset.model_validate(
        {
            "name": "error handling",
            "cases": [
                {
                    "id": "failure",
                    "question": "question",
                    "expected_sources": [{"file_name": "notes.md"}],
                    "expected_answer_keywords": ["answer"],
                    "require_citation": True,
                }
            ],
        }
    )
    settings = Settings(
        llm_provider="demo",
        embedding_provider="demo",
        project_root=tmp_path,
    )

    run = evaluate_dataset(
        dataset=dataset,
        dataset_path="dataset.json",
        profiles=[ModelProfile(name="demo")],
        base_settings=settings,
    )

    result = run.profiles[0].cases[0]
    assert result.status == "error"
    assert result.error == "model unavailable"
    assert result.recall_at_k == 0.0
    assert result.citation_hit is False
    assert result.answer_keyword_recall == 0.0
    assert run.profiles[0].summary.error_cases == 1
    assert run.profiles[0].summary.pass_rate == 0.0
    assert run.profiles[0].summary.average_latency_ms is None
