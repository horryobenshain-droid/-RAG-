from typing import Any

import pytest
import requests
from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.llm import _clean_model_answer, _ollama_chat_url, generate_answer


def test_ollama_llm_uses_chat_api(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"message": {"content": "本地模型回答"}}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.rag.llm.requests.post", fake_post)
    settings = Settings(
        llm_provider="ollama",
        embedding_provider="demo",
        ollama_base_url="http://127.0.0.1:11434/",
        ollama_chat_model="llama3.1:8b",
        ollama_temperature=0.1,
        ollama_num_ctx=4096,
        ollama_num_predict=512,
        ollama_top_p=0.85,
        ollama_repeat_penalty=1.15,
        ollama_timeout_seconds=30,
    )

    answer = generate_answer(
        "问题",
        [Document(page_content="资料", metadata={})],
        settings,
        "strict",
    )

    assert answer == "本地模型回答"
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["timeout"] == 30
    assert captured["json"]["model"] == "llama3.1:8b"
    assert captured["json"]["stream"] is False
    assert captured["json"]["options"] == {
        "temperature": 0.1,
        "num_ctx": 4096,
        "num_predict": 512,
        "top_p": 0.85,
        "repeat_penalty": 1.15,
    }
    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][1]["role"] == "user"
    assert "用户问题：问题" in captured["json"]["messages"][1]["content"]


def test_ollama_augmented_mode_adds_guidance(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"message": {"content": "增强回答"}}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.rag.llm.requests.post", fake_post)
    settings = Settings(llm_provider="ollama", embedding_provider="demo")

    answer = generate_answer("快速幂怎么写？", [], settings, "augmented")

    assert answer == "增强回答"
    user_message = captured["json"]["messages"][1]["content"]
    assert "当前回答模式：知识库增强" in user_message
    assert "来源声明最多出现一次" in user_message
    assert "当前没有检索到可用知识库片段" in user_message


def test_ollama_missing_model_returns_actionable_error(monkeypatch: Any) -> None:
    response = requests.Response()
    response.status_code = 404
    response.url = "http://127.0.0.1:11434/api/chat"
    response._content = b'{"error":"model \'qwen3:8b\' not found"}'

    monkeypatch.setattr("app.rag.llm.requests.post", lambda *args, **kwargs: response)
    settings = Settings(
        llm_provider="ollama",
        embedding_provider="demo",
        ollama_chat_model="qwen3:8b",
    )

    with pytest.raises(ValueError, match="未安装模型.*qwen3:8b"):
        generate_answer(
            "问题",
            [Document(page_content="检索片段", metadata={})],
            settings,
            "strict",
        )


def test_ollama_chat_url_accepts_base_or_api_url() -> None:
    assert _ollama_chat_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434/api/chat"
    assert _ollama_chat_url("http://127.0.0.1:11434/") == "http://127.0.0.1:11434/api/chat"
    assert _ollama_chat_url("http://127.0.0.1:11434/api") == "http://127.0.0.1:11434/api/chat"


def test_clean_model_answer_collapses_repeated_augmented_notices() -> None:
    answer = """[知识库资料不足，以下为模型通用知识补充]

先给结论。

知识库资料不足，以下为模型通用知识补充

再给说明。
"""

    assert _clean_model_answer(answer) == (
        "> 以下补充基于模型通用知识。\n\n先给结论。\n\n再给说明。"
    )
