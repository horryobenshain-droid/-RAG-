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


def refresh_health() -> None:
    ok, payload = api_get("/health")
    st.session_state.health = payload if ok and isinstance(payload, dict) else None


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            max-width: 1280px;
        }
        .stChatMessage {
            border-radius: 8px;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.05rem;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "documents" not in st.session_state:
        refresh_documents()
    if "health" not in st.session_state:
        refresh_health()


def render_header() -> None:
    health = st.session_state.get("health") or {}
    documents = st.session_state.get("documents", [])
    active_documents = [doc for doc in documents if doc.get("status") != "deleted"]
    chunk_total = sum(int(doc.get("chunks_indexed", 0)) for doc in active_documents)

    st.title("本地 RAG 知识库")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("后端", "在线" if health else "未连接")
    col2.metric("文档", len(active_documents))
    col3.metric("片段", chunk_total)
    col4.metric(
        "模型",
        f"{health.get('llm_provider', '-')}/{health.get('embedding_provider', '-')}",
    )


def render_sidebar() -> tuple[int, str]:
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
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                }
                ok, payload = api_post("/api/upload", files=files)
            if ok and isinstance(payload, dict):
                st.success(f"入库成功：{payload['chunks_indexed']} 个片段")
                refresh_documents()
                refresh_health()
                st.rerun()
            else:
                st.error(payload)

        st.divider()
        st.subheader("回答设置")
        answer_mode_label = st.radio(
            "回答模式",
            options=list(ANSWER_MODES.keys()),
            index=0,
        )
        answer_mode = ANSWER_MODES[answer_mode_label]
        top_k = st.slider("召回片段数", min_value=1, max_value=10, value=4)

        st.divider()
        st.subheader("知识库操作")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("刷新", use_container_width=True):
                refresh_documents()
                refresh_health()
                st.rerun()
        with col2:
            if st.button("清空", use_container_width=True):
                ok, payload = api_delete("/api/documents")
                if ok:
                    st.success("知识库已清空")
                    refresh_documents()
                    st.rerun()
                else:
                    st.error(payload)

        if st.session_state.get("document_error"):
            st.error(st.session_state.document_error)

    return top_k, answer_mode


def render_knowledge_base() -> None:
    documents = st.session_state.get("documents", [])
    with st.expander("知识库文档", expanded=False):
        if not documents:
            st.info("暂无已入库文档")
            return

        for document in documents:
            col_name, col_meta, col_action = st.columns([4, 3, 1])
            col_name.markdown(f"**{document['original_file_name']}**")
            col_meta.caption(
                f"{document['chunks_indexed']} 片段 · "
                f"{document['embedding_provider']} / {document['embedding_model']}"
            )
            if col_action.button("删除", key=f"delete_{document['document_id']}"):
                ok, payload = api_delete(f"/api/documents/{document['document_id']}")
                if ok:
                    refresh_documents()
                    st.rerun()
                else:
                    st.error(payload)


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            render_answer_metadata(message.get("metadata", {}))
            render_sources(message.get("sources", []))


def handle_question(question: str, top_k: int, answer_mode: str) -> None:
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


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander("来源诊断", expanded=False):
        for source in sources:
            source_id = source.get("source_id", "?")
            file_name = source.get("file_name", "未知文件")
            symbol = source.get("symbol_name")
            page_or_line = _location_text(source)
            score_text = _score_text(
                source.get("score"),
                source.get("vector_score"),
                source.get("keyword_score"),
            )
            title_parts = [file_name, symbol, page_or_line, score_text]
            st.markdown(f"**[{source_id}] {' · '.join(part for part in title_parts if part)}**")

            matched_keywords = source.get("matched_keywords", [])
            if matched_keywords:
                st.caption(f"命中词：{', '.join(matched_keywords)}")
            st.code(source.get("preview", ""), language=source.get("language") or None)


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


def _location_text(source: dict[str, Any]) -> str | None:
    start_line = source.get("start_line")
    end_line = source.get("end_line")
    if start_line and end_line:
        return f"行 {start_line}-{end_line}"
    if source.get("page"):
        return f"第 {source['page']} 页"
    return None


def _score_text(score: object, vector_score: object, keyword_score: object) -> str:
    parts = []
    if isinstance(score, int | float):
        parts.append(f"综合 {score:.2f}")
    if isinstance(vector_score, int | float):
        parts.append(f"向量 {vector_score:.2f}")
    if isinstance(keyword_score, int | float):
        parts.append(f"关键词 {keyword_score:.2f}")
    return " / ".join(parts) if parts else "相关度未知"


st.set_page_config(page_title="本地 RAG 知识库", layout="wide")
inject_styles()
init_state()
top_k_value, answer_mode_value = render_sidebar()
render_header()
render_knowledge_base()
render_chat_history()

question_text = st.chat_input("输入问题，按 Enter 发送")
if question_text:
    handle_question(question_text, top_k_value, answer_mode_value)
