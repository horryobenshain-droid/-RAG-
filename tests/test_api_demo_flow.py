from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def test_upload_and_chat_demo_flow(tmp_path: Path) -> None:
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

        upload_response = client.post(
            "/api/upload",
            files={
                "file": (
                    "rag_notes.txt",
                    b"RAG combines retrieval with generation. Chroma stores local vectors.",
                    "text/plain",
                )
            },
        )
        assert upload_response.status_code == 200
        assert upload_response.json()["chunks_indexed"] == 1

        chat_response = client.post(
            "/api/chat",
            json={"question": "What does RAG combine?", "top_k": 2},
        )
        assert chat_response.status_code == 200
        payload = chat_response.json()
        assert "demo" in payload["answer"]
        assert payload["sources"]
    finally:
        app.dependency_overrides.clear()
