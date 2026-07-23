import json
from pathlib import Path
from typing import Any

from app.evaluation.cli import main
from app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationRun,
    EvaluationSummary,
    ProfileEvaluationResult,
)


def test_evaluation_cli_writes_both_report_formats(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "cli sample",
                "cases": [{"id": "case-1", "question": "What is RAG?"}],
            }
        ),
        encoding="utf-8",
    )
    run = EvaluationRun(
        dataset_name="cli sample",
        dataset_path=str(dataset_path),
        generated_at="2026-07-23T00:00:00+00:00",
        profiles=[
            ProfileEvaluationResult(
                profile_name="current",
                llm_provider="demo",
                llm_model="demo-snippet-answer",
                started_at="2026-07-23T00:00:00+00:00",
                duration_ms=1.0,
                summary=EvaluationSummary(
                    total_cases=1,
                    passed_cases=1,
                    failed_cases=0,
                    error_cases=0,
                    pass_rate=1.0,
                ),
                cases=[
                    EvaluationCaseResult(
                        case_id="case-1",
                        question="What is RAG?",
                        status="passed",
                    )
                ],
            )
        ],
    )
    monkeypatch.setattr("app.evaluation.cli.evaluate_dataset", lambda **kwargs: run)
    markdown_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--dataset",
            str(dataset_path),
            "--output",
            str(markdown_path),
            "--json-output",
            str(json_path),
        ]
    )

    assert exit_code == 0
    assert markdown_path.is_file()
    assert json_path.is_file()
