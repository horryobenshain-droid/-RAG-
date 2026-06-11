from typing import Any

from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.embeddings import get_embeddings
from app.rag.llm import generate_answer


def test_openai_llm_uses_configured_base_url(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeResponses:
        def create(self, **kwargs: Any) -> Any:
            captured["create"] = kwargs
            return type("Response", (), {"output_text": "ok"})

    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured["client"] = kwargs
            self.responses = FakeResponses()

    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    settings = Settings(
        llm_provider="openai",
        embedding_provider="demo",
        openai_api_key="test-key",
        openai_base_url="https://gateway.example.com/v1",
        openai_chat_model="gpt-5.5",
    )

    answer = generate_answer(
        "问题",
        [Document(page_content="资料", metadata={})],
        settings,
        "strict",
    )

    assert answer == "ok"
    assert captured["client"]["base_url"] == "https://gateway.example.com/v1"
    assert captured["create"]["model"] == "gpt-5.5"


def test_openai_embeddings_accept_configured_base_url() -> None:
    settings = Settings(
        llm_provider="demo",
        embedding_provider="openai",
        openai_api_key="test-key",
        openai_base_url="https://gateway.example.com/v1",
        openai_embedding_model="text-embedding-3-large",
    )

    embeddings = get_embeddings(settings)

    assert str(embeddings.openai_api_base).rstrip("/") == "https://gateway.example.com/v1"
