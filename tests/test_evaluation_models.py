import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.io import load_evaluation_dataset, load_model_profiles
from app.evaluation.models import EvaluationDataset, ExpectedSource, ModelProfile


def test_expected_source_requires_a_selector() -> None:
    with pytest.raises(ValidationError, match="at least one selector"):
        ExpectedSource()


def test_dataset_requires_unique_case_ids() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        EvaluationDataset.model_validate(
            {
                "name": "duplicate cases",
                "cases": [
                    {"id": "same", "question": "one"},
                    {"id": "same", "question": "two"},
                ],
            }
        )


def test_model_profile_rejects_secrets_and_embedding_changes() -> None:
    with pytest.raises(ValidationError, match="Unsupported model profile settings"):
        ModelProfile(
            name="unsafe",
            overrides={
                "openai_api_key": "secret",
                "embedding_provider": "openai",
            },
        )


def test_model_profile_allows_retrieval_and_reranker_comparison() -> None:
    profile = ModelProfile(
        name="mmr-reranker",
        overrides={
            "retrieval_strategy": "mmr",
            "retrieval_fetch_k": 30,
            "reranker_provider": "cross_encoder",
            "reranker_weight": 0.7,
        },
    )

    assert profile.overrides["retrieval_strategy"] == "mmr"


def test_load_evaluation_files(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "sample",
                "cases": [{"id": "case-1", "question": "What is RAG?"}],
            }
        ),
        encoding="utf-8",
    )
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "name": "qwen",
                        "overrides": {
                            "llm_provider": "ollama",
                            "ollama_chat_model": "qwen2.5:3b",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    dataset = load_evaluation_dataset(dataset_path)
    profiles = load_model_profiles(profiles_path)

    assert dataset.cases[0].id == "case-1"
    assert profiles[0].overrides["ollama_chat_model"] == "qwen2.5:3b"
