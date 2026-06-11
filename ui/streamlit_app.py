import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
SUPPORTED_TYPES = [
    "pdf",
    "docx",
    "txt",
    "md",
    "markdown",
    "py",
    "js",
    "ts",
    "tsx",
    "jsx",
    "java",
    "go",
    "rs",
    "cpp",
    "c",
    "h",
    "hpp",
    "cs",
    "php",
    "rb",
    "swift",
    "kt",
    "sql",
    "yaml",
    "yml",
    "json",
    "toml",
]
ANSWER_MODES = {
    "严格知识库": "strict",
    "知识库增强": "augmented",
}
ANSWER_BASIS_LABELS = {
    "knowledge_base": "知识库",
    "model_prior": "模型通用知识",
    "mixed": "知识库 + 模型补充",
}


def api_get(path: str) -> tuple[bool, dict[str, Any] | str]:
    try:
        response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    except requests.RequestException as exc:
        return False, f"无法连接后端服务：{exc}"
    return _parse_response(response)


def api_post(path: str, **kwargs: Any) -> tuple[bool, dict[str, Any] | str]:
    try:
        response = requests.post(f"{API_BASE_URL}{path}", timeout=120, **kwargs)
    except requests.RequestException as exc:
        return False, f"请求失败：{exc}"
    return _parse_response(response)


def api_delete(path: str) -> tuple[bool, dict[str, Any] | str]:
    try:
        response = requests.delete(f"{API_BASE_URL}{path}", timeout=60)
    except requests.RequestException as exc:
        return False, f"请求失败：{exc}"
    return _parse_response(response)


def _parse_response(response: requests.Response) -> tuple[bool, dict[str, Any] | str]:
    if response.ok:
        return True, response.json()
    try:
        payload = response.json()
        detail = payload.get("detail", response.text)
    except ValueError:
        detail = response.text
    return False, str(detail)


def refresh_documents() -> None:
    ok, payload = api_get("/api/documents")
    if ok and isinstance(payload, dict):
        st.session_state.documents = payload.get("documents", [])
        st.session_state.document_error = None
    else:
        st.session_state.documents = []
        st.session_state.document_error = payload


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander("来源片段", expanded=False):
        for source in sources:
            source_id = source.get("source_id", "?")
            file_name = source.get("file_name", "未知文件")
            page = f"第 {source['page']} 页" if source.get("page") else "无页码"
            line_range = _line_range(source)
            symbol = source.get("symbol_name")
            score = source.get("score")
            vector_score = source.get("vector_score")
            keyword_score = source.get("keyword_score")
            score_text = _score_text(score, vector_score, keyword_score)
            location = " · ".join(item for item in [file_name, symbol, page, line_range] if item)
            st.markdown(f"**[{source_id}] {location} · {score_text}**")
            matched_keywords = source.get("matched_keywords", [])
            if matched_keywords:
                st.caption(f"命中词：{', '.join(matched_keywords)}")
            st.caption(source.get("preview", ""))


def render_answer_metadata(payload: dict[str, Any]) -> None:
    metadata = []
    basis = payload.get("answer_basis")
    if basis:
        metadata.append(f"依据 {ANSWER_BASIS_LABELS.get(basis, basis)}")
    if payload.get("elapsed_ms") is not None:
        metadata.append(f"耗时 {payload['elapsed_ms']} ms")
    if payload.get("retrieved_chunks") is not None:
        metadata.append(f"召回 {payload['retrieved_chunks']} 个片段")

    llm_provider = payload.get("llm_provider")
    llm_model = payload.get("llm_model")
    if llm_provider or llm_model:
        model_name = " / ".join(value for value in [llm_provider, llm_model] if value)
        metadata.append(f"模型 {model_name}")

    if metadata:
        st.caption(" · ".join(metadata))


def _line_range(source: dict[str, Any]) -> str | None:
    start_line = source.get("start_line")
    end_line = source.get("end_line")
    if start_line and end_line:
        return f"行 {start_line}-{end_line}"
    return None


def _score_text(
    score: object,
    vector_score: object,
    keyword_score: object,
) -> str:
    parts = []
    if isinstance(score, int | float):
        parts.append(f"综合 {score:.2f}")
    if isinstance(vector_score, int | float):
        parts.append(f"向量 {vector_score:.2f}")
    if isinstance(keyword_score, int | float):
        parts.append(f"关键词 {keyword_score:.2f}")
    return " / ".join(parts) if parts else "相关度未知"


st.set_page_config(page_title="本地 RAG 知识库", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    refresh_documents()

st.title("本地 RAG 知识库")

with st.sidebar:
    st.subheader("文档入库")
    uploaded_file = st.file_uploader("选择文件", type=SUPPORTED_TYPES)
    if st.button(
        "上传并入库",
        type="primary",
        use_container_width=True,
        disabled=uploaded_file is None,
    ):
        with st.spinner("正在解析、切分并写入向量库..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            ok, payload = api_post("/api/upload", files=files)
        if ok and isinstance(payload, dict):
            st.success(f"入库成功：{payload['chunks_indexed']} 个片段")
            refresh_documents()
        else:
            st.error(payload)

    st.divider()
    st.subheader("回答设置")
    answer_mode_label = st.radio(
        "回答模式",
        options=list(ANSWER_MODES.keys()),
        index=0,
        horizontal=False,
    )
    answer_mode = ANSWER_MODES[answer_mode_label]

    st.divider()
    st.subheader("检索设置")
    top_k = st.slider("召回片段数", min_value=1, max_value=10, value=4)

    st.divider()
    st.subheader("知识库")
    if st.button("刷新列表", use_container_width=True):
        refresh_documents()

    if st.session_state.get("document_error"):
        st.error(st.session_state.document_error)

    documents = st.session_state.get("documents", [])
    if documents:
        for document in documents:
            label = f"{document['original_file_name']} · {document['chunks_indexed']} 片段"
            with st.expander(label):
                st.caption(f"文档 ID：{document['document_id']}")
                st.caption(f"入库时间：{document['created_at']}")
                st.caption(
                    f"向量模型：{document['embedding_provider']} / {document['embedding_model']}"
                )
                if st.button(
                    "删除文档",
                    key=f"delete_{document['document_id']}",
                    use_container_width=True,
                ):
                    ok, payload = api_delete(f"/api/documents/{document['document_id']}")
                    if ok:
                        st.success("已删除")
                        refresh_documents()
                        st.rerun()
                    else:
                        st.error(payload)
    else:
        st.info("暂无已入库文档")

    if st.button("清空知识库", use_container_width=True, disabled=not documents):
        ok, payload = api_delete("/api/documents")
        if ok:
            st.success("知识库已清空")
            refresh_documents()
            st.rerun()
        else:
            st.error(payload)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_answer_metadata(message.get("metadata", {}))
        render_sources(message.get("sources", []))

question = st.chat_input("请输入问题")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("正在检索知识库并生成回答..."):
            ok, payload = api_post(
                "/api/chat",
                json={
                    "question": question,
                    "top_k": top_k,
                    "answer_mode": answer_mode,
                },
            )
        if ok and isinstance(payload, dict):
            answer = payload.get("answer", "后端未返回回答内容。")
            st.markdown(answer)
            render_answer_metadata(payload)
            render_sources(payload.get("sources", []))
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": payload.get("sources", []),
                    "metadata": payload,
                }
            )
        else:
            st.error(payload)
            st.session_state.messages.append({"role": "assistant", "content": str(payload)})
