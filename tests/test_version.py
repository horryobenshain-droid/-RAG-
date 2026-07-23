from fastapi.testclient import TestClient

from app import __version__
from app.main import app


def test_application_exposes_release_version() -> None:
    client = TestClient(app)

    assert __version__ == "0.6.0"
    assert app.version == __version__
    assert client.get("/health").json()["version"] == __version__
