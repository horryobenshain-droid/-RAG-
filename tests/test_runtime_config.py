import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings, update_runtime_settings
from app.main import app


def test_runtime_config_update_is_persisted_and_masks_secret(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path)
    settings.ensure_directories()

    updated = update_runtime_settings(
        settings,
        {
            "llm_provider": "ollama",
            "ollama_chat_model": "llama3.1:8b",
            "openai_api_key": "secret-key",
            "default_top_k": 6,
        },
    )

    assert updated.llm_provider == "ollama"
    assert settings.ollama_chat_model == "llama3.1:8b"
    payload = json.loads(settings.runtime_config_path.read_text(encoding="utf-8"))
    assert payload["default_top_k"] == 6
    assert payload["openai_api_key"] == "secret-key"
    assert "project_root" not in payload

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).get("/api/config")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["openai_api_key_configured"] is True
    assert "openai_api_key" not in response.json()


def test_invalid_runtime_config_does_not_replace_persisted_file(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path)
    settings.ensure_directories()
    update_runtime_settings(settings, {"default_top_k": 5})
    original = settings.runtime_config_path.read_text(encoding="utf-8")

    with pytest.raises(ValidationError, match="HYBRID_.*_WEIGHT"):
        update_runtime_settings(settings, {"hybrid_vector_weight": 0.8})

    assert settings.runtime_config_path.read_text(encoding="utf-8") == original


def test_config_api_updates_active_settings(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path)
    settings.ensure_directories()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).patch(
            "/api/config",
            json={
                "llm_provider": "ollama",
                "ollama_chat_model": "qwen2.5:7b",
                "ollama_temperature": 0.4,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_llm_model"] == "qwen2.5:7b"
    assert payload["ollama_temperature"] == 0.4
    assert settings.llm_provider == "ollama"
