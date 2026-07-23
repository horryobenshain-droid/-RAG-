from fastapi.testclient import TestClient

from app import __version__
from app.main import app


def test_application_exposes_release_version() -> None:
    client = TestClient(app)

    assert __version__ == "0.7.0"
    assert app.version == __version__
    health = client.get("/health").json()
    assert health["version"] == __version__
    assert health["default_top_k"] >= 1
    assert health["retrieval_strategy"] in {"similarity", "mmr"}
