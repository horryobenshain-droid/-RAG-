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
        upload_payload = upload_response.json()
        assert upload_payload["chunks_indexed"] == 1
        document_id = upload_payload["document_id"]

        documents_response = client.get("/api/documents")
        assert documents_response.status_code == 200
        documents_payload = documents_response.json()
        assert documents_payload["total"] == 1
        assert documents_payload["documents"][0]["document_id"] == document_id

        chat_response = client.post(
            "/api/chat",
            json={"question": "What does RAG combine?", "top_k": 2},
        )
        assert chat_response.status_code == 200
        payload = chat_response.json()
        assert "demo" in payload["answer"]
        assert payload["sources"]
        assert payload["retrieved_chunks"] == 1
        assert payload["elapsed_ms"] >= 0
        assert payload["llm_provider"] == "demo"
        assert payload["embedding_provider"] == "demo"
        assert payload["answer_mode"] == "strict"
        assert payload["answer_basis"] == "knowledge_base"
        assert payload["sources"][0]["score"] is not None
        assert 0 <= payload["sources"][0]["score"] <= 1

        delete_response = client.delete(f"/api/documents/{document_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["chunks_deleted"] == 1

        documents_response = client.get("/api/documents")
        assert documents_response.status_code == 200
        assert documents_response.json()["total"] == 0
    finally:
        app.dependency_overrides.clear()


def test_clear_knowledge_base_demo_flow(tmp_path: Path) -> None:
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
        client.post(
            "/api/upload",
            files={"file": ("rag_notes.txt", b"Chroma stores vectors.", "text/plain")},
        )

        clear_response = client.delete("/api/documents")
        assert clear_response.status_code == 200
        payload = clear_response.json()
        assert payload["documents_deleted"] == 1
        assert payload["chunks_deleted"] == 1
    finally:
        app.dependency_overrides.clear()
