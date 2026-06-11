import os
from html import escape
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
        :root {
            --sky-25: #f8fcff;
            --sky-50: #eff8ff;
            --sky-100: #dff1ff;
            --sky-200: #bfe3fb;
            --sky-500: #238fe2;
            --sky-700: #0e5d9d;
            --cyan-500: #16b4c9;
            --mint-500: #24a978;
            --coral-500: #ef6a6a;
            --ink: #17344d;
            --muted: #5d7487;
            --line: #d8eafa;
            --surface: #ffffff;
        }
        .stApp {
            background: linear-gradient(180deg, #f6fbff 0%, #eef8ff 44%, #f9fcff 100%);
            color: var(--ink);
        }
        .block-container {
            max-width: 1180px;
            padding-top: 1.35rem;
            padding-bottom: 5.5rem;
        }
        [data-testid="stHeader"] {
            background: rgba(246, 251, 255, 0.84);
            backdrop-filter: blur(10px);
        }
        [data-testid="stSidebar"] {
            background: #f2f9ff;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] * {
            color: var(--ink);
        }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] {
            background: rgba(255, 255, 255, 0.68);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.45rem;
        }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
            background: #f8fcff !important;
            border: 1px dashed var(--sky-200) !important;
            border-radius: 8px !important;
            color: var(--muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section * {
            color: var(--muted) !important;
        }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
            background: #eff8ff !important;
            border: 1px solid var(--sky-200) !important;
            color: var(--sky-700) !important;
        }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
            color: var(--muted) !important;
        }
        h1 {
            color: #0b4f84;
            letter-spacing: 0;
        }
        h2, h3 {
            color: #145c94;
            letter-spacing: 0;
        }
        .app-heading {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            border-bottom: 1px solid var(--line);
            padding-bottom: 0.85rem;
            margin-bottom: 1rem;
        }
        .app-heading h1 {
            margin: 0;
            font-size: 2rem;
            line-height: 1.15;
        }
        .app-badge {
            display: inline-flex;
            align-items: center;
            border: 1px solid var(--sky-200);
            border-left: 3px solid var(--sky-500);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.72);
            color: var(--sky-700);
            font-size: 0.86rem;
            font-weight: 700;
            padding: 0.34rem 0.58rem;
            white-space: nowrap;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.72rem 0.8rem;
            box-shadow: 0 8px 20px rgba(35, 143, 226, 0.06);
        }
        [data-testid="stMetricValue"] {
            color: var(--sky-700);
            font-size: 1rem;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        [data-testid="stMetricLabel"] {
            color: var(--muted);
        }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            font-size: 1rem;
            line-height: 1.35;
            margin-top: 0.35rem;
        }
        [data-testid="stSidebar"] hr {
            margin: 1rem 0;
            border-color: var(--line);
        }
        .stButton > button {
            border-radius: 8px;
            border-color: var(--sky-200);
            color: var(--sky-700);
            min-height: 2.35rem;
            font-weight: 650;
            background: rgba(255, 255, 255, 0.76);
        }
        .stButton > button:hover {
            border-color: var(--sky-500);
            color: var(--sky-700);
            background: #f3faff;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--sky-500) 0%, var(--cyan-500) 100%);
            border: none;
            color: white;
            box-shadow: 0 8px 18px rgba(35, 143, 226, 0.16);
        }
        .stButton > button[kind="primary"]:hover {
            color: white;
        }
        div[role="radiogroup"] {
            background: rgba(255, 255, 255, 0.58);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.35rem 0.45rem;
        }
        .stSlider [data-baseweb="slider"] > div {
            color: var(--sky-500);
        }
        [data-testid="stChatMessage"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: 0 8px 20px rgba(35, 143, 226, 0.045);
            margin-bottom: 0.85rem;
        }
        [data-testid="stChatMessage"] *,
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div {
            color: var(--ink) !important;
        }
        [data-testid="stChatMessage"] [data-testid="stCaptionContainer"] *,
        [data-testid="stChatMessage"] small {
            color: var(--muted) !important;
        }
        [data-testid="stChatMessage"] svg {
            color: var(--sky-700) !important;
            fill: currentColor !important;
        }
        [data-testid="stSpinner"] *,
        [data-testid="stStatusWidget"] * {
            color: var(--ink) !important;
        }
        [data-testid="stExpander"] {
            border-color: var(--line);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.76);
        }
        [data-testid="stExpander"] *,
        [data-testid="stExpander"] summary {
            color: var(--ink) !important;
        }
        [data-testid="stChatInput"] {
            background: rgba(248, 252, 255, 0.92);
            border-top: 1px solid var(--line);
        }
        [data-testid="stBottom"] {
            background: #f2f9ff !important;
            border-top: 1px solid var(--line);
        }
        [data-testid="stBottom"] > div {
            background: #f2f9ff !important;
        }
        [data-testid="stChatInput"] > div {
            background: #f8fcff !important;
            border: 1px solid var(--sky-200) !important;
            border-radius: 8px !important;
            box-shadow: 0 10px 24px rgba(35, 143, 226, 0.08);
        }
        [data-testid="stChatInput"] textarea {
            background: var(--surface) !important;
            border: 1px solid var(--line) !important;
            border-radius: 8px;
            color: var(--ink) !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: #7f9aae !important;
            opacity: 1 !important;
        }
        [data-testid="stChatInput"] button {
            background: #e6f5ff !important;
            border: 1px solid var(--sky-200) !important;
            color: var(--sky-700) !important;
            border-radius: 8px !important;
        }
        .doc-title {
            color: var(--ink);
            font-weight: 750;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .doc-meta {
            color: var(--muted);
            font-size: 0.84rem;
            line-height: 1.45;
            margin-top: 0.12rem;
            overflow-wrap: anywhere;
        }
        .file-chip {
            width: 2.35rem;
            height: 2.35rem;
            border-radius: 8px;
            display: grid;
            place-items: center;
            border: 1px solid var(--line);
            background: linear-gradient(135deg, var(--sky-50) 0%, #ffffff 100%);
            color: var(--sky-700);
            font-size: 0.72rem;
            font-weight: 800;
            margin-top: 0.05rem;
        }
        .doc-divider {
            height: 1px;
            background: var(--line);
            margin: 0.58rem 0;
            opacity: 0.72;
        }
        [data-testid="stCodeBlock"] {
            border: 1px solid var(--line);
            border-radius: 8px;
        }
        [data-testid="stCodeBlock"],
        [data-testid="stCodeBlock"] pre,
        [data-testid="stCodeBlock"] code {
            background: #f6fbff !important;
            color: #17344d !important;
        }
        [data-testid="stCodeBlock"] pre {
            border-radius: 8px !important;
        }
        [data-testid="stCodeBlock"] span {
            color: #17344d !important;
            background: transparent !important;
        }
        [data-testid="stMarkdownContainer"] pre,
        [data-testid="stMarkdownContainer"] pre code {
            background: #f6fbff !important;
            color: #17344d !important;
            border: 1px solid var(--line);
            border-radius: 8px;
        }
        [data-testid="stMarkdownContainer"] pre span {
            color: #17344d !important;
            background: transparent !important;
        }
        [data-testid="stMarkdownContainer"] :not(pre) > code {
            background: #e8f5ff !important;
            color: #0e5d9d !important;
            border: 1px solid var(--sky-200);
            border-radius: 5px;
            padding: 0.08rem 0.28rem;
            font-weight: 650;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .app-heading {
                align-items: flex-start;
                flex-direction: column;
            }
            .app-heading h1 {
                font-size: 1.65rem;
            }
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
    model_pair = f"{health.get('llm_provider', '-')}/{health.get('embedding_provider', '-')}"

    status_label = "服务在线" if health else "等待后端"
    st.markdown(
        f"""
        <div class="app-heading">
            <h1>本地 RAG 知识库</h1>
            <div class="app-badge">{status_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("服务状态", "在线" if health else "未连接")
    col2.metric("文档数量", len(active_documents))
    col3.metric("知识片段", chunk_total)
    col4.metric("模型组合", model_pair)


def render_sidebar() -> tuple[int, str]:
    with st.sidebar:
        st.subheader("文档入库")
        uploaded_file = st.file_uploader("选择文件", type=SUPPORTED_TYPES)
        if st.button(
            "上传并入库",
            type="primary",
            icon=":material/upload_file:",
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
            horizontal=True,
        )
        answer_mode = ANSWER_MODES[answer_mode_label]
        top_k = st.slider("召回片段数", min_value=1, max_value=10, value=4)

        st.divider()
        st.subheader("知识库操作")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("刷新", icon=":material/refresh:", use_container_width=True):
                refresh_documents()
                refresh_health()
                st.rerun()
        with col2:
            if st.button("清空", icon=":material/delete_sweep:", use_container_width=True):
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
    with st.expander("知识库文档", expanded=False, icon=":material/folder_open:"):
        if not documents:
            st.info("暂无已入库文档")
            return

        for document in documents:
            with st.container():
                col_icon, col_info, col_action = st.columns([0.55, 5.2, 1])
                file_name = document["original_file_name"]
                extension = file_name.rsplit(".", 1)[-1].upper() if "." in file_name else "DOC"
                extension = extension[:4]
                col_icon.markdown(
                    f'<div class="file-chip">{escape(extension)}</div>',
                    unsafe_allow_html=True,
                )
                col_info.markdown(
                    (
                        f'<div class="doc-title">{escape(file_name)}</div>'
                        f'<div class="doc-meta">{document["chunks_indexed"]} 片段 · '
                        f'{escape(str(document["embedding_provider"]))} / '
                        f'{escape(str(document["embedding_model"]))}</div>'
                    ),
                    unsafe_allow_html=True,
                )
                if col_action.button(
                    "删除",
                    key=f"delete_{document['document_id']}",
                    icon=":material/delete:",
                    use_container_width=True,
                ):
                    ok, payload = api_delete(f"/api/documents/{document['document_id']}")
                    if ok:
                        refresh_documents()
                        st.rerun()
                    else:
                        st.error(payload)
                st.markdown('<div class="doc-divider"></div>', unsafe_allow_html=True)


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
    with st.expander("来源诊断", expanded=False, icon=":material/troubleshoot:"):
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


st.set_page_config(
    page_title="本地 RAG 知识库",
    page_icon=":material/database:",
    layout="wide",
)
inject_styles()
init_state()
top_k_value, answer_mode_value = render_sidebar()
render_header()
render_knowledge_base()
render_chat_history()

question_text = st.chat_input("例如：请总结这篇论文的核心方法，或解释代码库中的检索流程")
if question_text:
    handle_question(question_text, top_k_value, answer_mode_value)
