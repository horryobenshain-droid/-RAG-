from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def test_augmented_mode_can_answer_without_sources_in_demo(tmp_path: Path) -> None:
    settings = Settings(
        llm_provider="demo",
        embedding_provider="demo",
        chroma_collection=f"test_{uuid4().hex}",
        project_root=tmp_path,
    )
    settings.ensure_directories()
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={
                "question": "快速幂怎么写？",
                "top_k": 2,
                "answer_mode": "augmented",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["answer_mode"] == "augmented"
        assert payload["answer_basis"] == "model_prior"
        assert payload["retrieved_chunks"] == 0
    finally:
        app.dependency_overrides.clear()
