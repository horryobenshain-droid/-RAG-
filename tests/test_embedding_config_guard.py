from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def test_chat_rejects_active_documents_indexed_with_different_embedding(tmp_path: Path) -> None:
    collection = f"test_{uuid4().hex}"
    initial_settings = Settings(
        llm_provider="demo",
        embedding_provider="demo",
        chroma_collection=collection,
        project_root=tmp_path,
    )
    initial_settings.ensure_directories()
    app.dependency_overrides[get_settings] = lambda: initial_settings

    try:
        client = TestClient(app)
        upload_response = client.post(
            "/api/upload",
            files={"file": ("notes.txt", b"Dijkstra finds shortest paths.", "text/plain")},
        )
        assert upload_response.status_code == 200

        changed_settings = Settings(
            llm_provider="demo",
            embedding_provider="local",
            local_embedding_model="BAAI/bge-small-zh-v1.5",
            chroma_collection=collection,
            project_root=tmp_path,
        )
        changed_settings.ensure_directories()
        app.dependency_overrides[get_settings] = lambda: changed_settings

        chat_response = client.post(
            "/api/chat",
            json={
                "question": "解释一下 Dijkstra",
                "top_k": 2,
                "answer_mode": "augmented",
            },
        )

        assert chat_response.status_code == 400
        assert "Embedding 配置与当前系统配置不一致" in chat_response.json()["detail"]
        assert "请先清空知识库" in chat_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
