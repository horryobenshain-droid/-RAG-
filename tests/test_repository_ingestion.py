import io
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        llm_provider="demo",
        embedding_provider="demo",
        chroma_collection=f"test_{uuid4().hex}",
        project_root=tmp_path,
    )
    settings.ensure_directories()
    return settings


def test_repository_upload_preserves_paths_and_ignores_generated_files(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    archive = _zip_bytes(
        {
            "sample-main/src/search.py": b"def find_answer(query):\n    return query\n",
            "sample-main/README.md": b"# Search repository\n",
            "sample-main/.git/config": b"secret=false\n",
            "sample-main/node_modules/package/index.js": b"export default 1\n",
            "sample-main/dist/bundle.js": b"compiled output\n",
            "sample-main/assets/logo.png": b"\x89PNG\x00binary",
        }
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/repositories/upload",
            files={"file": ("sample.zip", archive, "application/zip")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "sample"
        assert payload["files_indexed"] == 2
        assert payload["chunks_indexed"] == 2
        assert payload["ignored_files"] == 4

        repositories = client.get("/api/repositories").json()
        assert repositories["total"] == 1
        assert repositories["repositories"][0]["repository_id"] == payload["repository_id"]

        documents = client.get("/api/documents").json()["documents"]
        code_document = next(doc for doc in documents if doc["relative_path"] == "src/search.py")
        assert code_document["repository_id"] == payload["repository_id"]
        assert code_document["repository_name"] == "sample"
        assert code_document["module_path"] == "src.search"
        assert code_document["original_file_name"] == "src/search.py"

        cleared = client.delete("/api/documents")
        assert cleared.status_code == 200
        assert client.get("/api/repositories").json()["total"] == 0
        assert not (settings.repository_dir / payload["repository_id"]).exists()
    finally:
        app.dependency_overrides.clear()


def test_repository_reindex_replaces_documents_and_delete_removes_repository(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    archive = _zip_bytes({"project/src/main.py": b"def main():\n    return 'v1'\n"})

    try:
        client = TestClient(app)
        uploaded = client.post(
            "/api/repositories/upload",
            files={"file": ("project.zip", archive, "application/zip")},
        ).json()
        repository_id = uploaded["repository_id"]
        old_document_id = client.get("/api/documents").json()["documents"][0]["document_id"]

        reindexed = client.post(f"/api/repositories/{repository_id}/reindex")

        assert reindexed.status_code == 200
        assert reindexed.json()["files_indexed"] == 1
        documents = client.get("/api/documents").json()["documents"]
        assert len(documents) == 1
        assert documents[0]["document_id"] != old_document_id

        deleted = client.delete(f"/api/repositories/{repository_id}")
        assert deleted.status_code == 200
        assert deleted.json()["documents_deleted"] == 1
        assert deleted.json()["chunks_deleted"] == 1
        assert client.get("/api/repositories").json()["total"] == 0
        assert client.get("/api/documents").json()["total"] == 0
        assert not (settings.repository_dir / repository_id).exists()
    finally:
        app.dependency_overrides.clear()


def test_repository_upload_rejects_path_traversal(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    archive = _zip_bytes({"../outside.py": b"print('unsafe')\n"})

    try:
        response = TestClient(app).post(
            "/api/repositories/upload",
            files={"file": ("unsafe.zip", archive, "application/zip")},
        )

        assert response.status_code == 400
        assert "不安全路径" in response.json()["detail"]
        assert not (tmp_path / "outside.py").exists()
    finally:
        app.dependency_overrides.clear()
