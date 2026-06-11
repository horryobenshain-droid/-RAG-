from typing import Any

from app.core.config import Settings
from app.rag.embeddings import get_embeddings
from app.rag.service import _embedding_model_name


def test_local_embedding_provider_uses_configured_model(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeHuggingFaceEmbeddings:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    import langchain_huggingface

    monkeypatch.setattr(
        langchain_huggingface,
        "HuggingFaceEmbeddings",
        FakeHuggingFaceEmbeddings,
    )
    settings = Settings(
        embedding_provider="local",
        local_embedding_model="BAAI/bge-small-zh-v1.5",
    )

    embeddings = get_embeddings(settings)

    assert isinstance(embeddings, FakeHuggingFaceEmbeddings)
    assert captured["model_name"] == "BAAI/bge-small-zh-v1.5"
    assert captured["encode_kwargs"] == {"normalize_embeddings": True}
    assert _embedding_model_name(settings) == "BAAI/bge-small-zh-v1.5"
