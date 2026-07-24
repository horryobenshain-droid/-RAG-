import os
from datetime import datetime
from html import escape
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_CHAT_TIMEOUT_SECONDS = float(os.getenv("API_CHAT_TIMEOUT_SECONDS", "150"))
API_INGEST_TIMEOUT_SECONDS = float(os.getenv("API_INGEST_TIMEOUT_SECONDS", "600"))
SUPPORTED_TYPES = [
    "zip",
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
ANSWER_MODES = {"严格知识库": "strict", "知识库增强": "augmented"}
ANSWER_BASIS_LABELS = {
    "knowledge_base": "知识库",
    "model_prior": "模型通用知识",
    "mixed": "知识库 + 模型补充",
}
RETRIEVAL_STRATEGIES = {"相似度": "similarity", "MMR 多样性": "mmr"}
RETRIEVAL_STRATEGY_LABELS = {
    value: label for label, value in RETRIEVAL_STRATEGIES.items()
}
PAGES = {
    "对话工作台": ":material/forum:",
    "知识库": ":material/folder_open:",
    "配置中心": ":material/tune:",
}
OLLAMA_LABEL = "O\u2060llama"
PROVIDER_LABELS = {
    "demo": "演示模式",
    "openai": "OpenAI",
    "ollama": OLLAMA_LABEL,
    "local": "本地模型",
}


def protect_technical_terms(value: object) -> str:
    return str(value).replace("Ollama", OLLAMA_LABEL).replace("ollama", "o\u2060llama")


def api_request(
    method: str,
    path: str,
    timeout: float = 30,
    **kwargs: Any,
) -> tuple[bool, dict[str, Any] | str]:
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=timeout,
            **kwargs,
        )
    except requests.Timeout:
        return False, f"请求超时：后端在 {timeout:.0f} 秒内未完成处理。"
    except requests.RequestException as exc:
        return False, f"无法连接后端服务：{exc}"
    if response.ok:
        try:
            return True, response.json()
        except ValueError:
            return True, {}
    try:
        payload = response.json()
        detail = payload.get("detail", response.text)
    except ValueError:
        detail = response.text
    return False, protect_technical_terms(detail)


def api_get(path: str, timeout: float = 30) -> tuple[bool, dict[str, Any] | str]:
    return api_request("GET", path, timeout=timeout)


def api_post(path: str, **kwargs: Any) -> tuple[bool, dict[str, Any] | str]:
    timeout = 120.0
    if path == "/api/chat":
        timeout = API_CHAT_TIMEOUT_SECONDS
    elif path == "/api/repositories/upload" or path.endswith("/reindex"):
        timeout = API_INGEST_TIMEOUT_SECONDS
    return api_request("POST", path, timeout=timeout, **kwargs)


def api_patch(path: str, **kwargs: Any) -> tuple[bool, dict[str, Any] | str]:
    return api_request("PATCH", path, timeout=30, **kwargs)


def api_delete(path: str) -> tuple[bool, dict[str, Any] | str]:
    return api_request("DELETE", path, timeout=60)


def refresh_workspace(probe_providers: bool = True) -> None:
    requests_to_make = [
        ("documents", "/api/documents"),
        ("repositories", "/api/repositories"),
        ("config", "/api/config"),
    ]
    if probe_providers:
        requests_to_make.append(("system_status", "/api/status"))

    for state_key, path in requests_to_make:
        ok, payload = api_get(path)
        if ok and isinstance(payload, dict):
            if state_key == "documents":
                st.session_state.documents = payload.get("documents", [])
            elif state_key == "repositories":
                st.session_state.repositories = payload.get("repositories", [])
            else:
                st.session_state[state_key] = payload
            st.session_state.pop(f"{state_key}_error", None)
        else:
            if state_key in {"documents", "repositories"}:
                st.session_state[state_key] = []
            else:
                st.session_state[state_key] = None
            st.session_state[f"{state_key}_error"] = payload


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "documents" not in st.session_state:
        refresh_workspace()
    if "confirm_clear" not in st.session_state:
        st.session_state.confirm_clear = False


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --canvas: #f7f8ff;
            --surface: #ffffff;
            --surface-soft: #f8fbff;
            --sky-50: #eff6ff;
            --sky-100: #dbeafe;
            --sky-200: #bfdbfe;
            --sky-300: #93c5fd;
            --sky-500: #3b82f6;
            --sky-600: #2563eb;
            --sky-700: #1d4ed8;
            --violet-50: #f5f3ff;
            --violet-100: #ede9fe;
            --violet-200: #ddd6fe;
            --violet-400: #8b5cf6;
            --violet-500: #7c3aed;
            --indigo-500: #6366f1;
            --indigo-600: #4f46e5;
            --ink: #334155;
            --muted: #64748b;
            --line: #e2e8f0;
            --accent: #6366f1;
            --accent-strong: #4f46e5;
            --success: #279279;
            --success-soft: #ecfdf5;
            --warning: #b7791f;
            --danger: #c2414d;
        }
        .stApp {
            background: linear-gradient(
                135deg,
                #eff6ff 0%,
                #f8fafc 44%,
                #f5f3ff 100%
            );
            background-attachment: fixed;
            color: var(--ink);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei",
                sans-serif;
        }
        .block-container {
            max-width: 1280px;
            padding: 2rem 2.35rem 6rem;
        }
        [data-testid="stHeader"] {
            background: rgba(247, 248, 255, 0.86);
            border-bottom: 1px solid rgba(221, 214, 254, 0.76);
            backdrop-filter: blur(12px);
        }
        [data-testid="stToolbarActions"],
        [data-testid="stHeaderActionElements"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenuButton"],
        [data-testid="stDecoration"],
        footer {
            display: none !important;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 56%, #f7f4ff 100%);
            border-right: 1px solid var(--violet-100);
        }
        [data-testid="stSidebarContent"] {
            padding-top: 1.1rem;
        }
        .brand-lockup {
            align-items: center;
            display: flex;
            gap: 0.72rem;
            margin-bottom: 1.2rem;
        }
        .brand-mark {
            align-items: center;
            background: linear-gradient(135deg, var(--sky-500), var(--violet-500));
            border: 1px solid rgba(99, 102, 241, 0.45);
            border-radius: 12px;
            box-shadow: 0 8px 22px rgba(99, 102, 241, 0.22);
            color: #ffffff;
            display: flex;
            flex: 0 0 auto;
            font-size: 1rem;
            font-weight: 800;
            height: 2.35rem;
            justify-content: center;
            width: 2.35rem;
        }
        .brand-name {
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 700;
            letter-spacing: 0;
        }
        .brand-meta {
            color: var(--muted);
            font-size: 0.72rem;
            margin-top: 0.1rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 0.3rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            align-items: center;
            border: 1px solid transparent;
            border-radius: 12px;
            color: var(--muted);
            min-height: 2.55rem;
            padding: 0.5rem 0.72rem;
            transition: background 120ms ease, border-color 120ms ease;
            width: 100%;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
            display: none;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: var(--sky-50);
            border-color: var(--sky-200);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(90deg, var(--sky-100), var(--violet-100));
            border-color: var(--violet-200);
            box-shadow: inset 3px 0 0 var(--indigo-500),
                0 5px 14px rgba(99, 102, 241, 0.1);
            color: var(--indigo-600);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label p {
            color: inherit;
            font-weight: 650;
        }
        .runtime-panel {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid var(--violet-100);
            border-radius: 14px;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.07);
            margin-top: 0.95rem;
            padding: 1rem;
            transition: border-color 160ms ease, box-shadow 160ms ease;
        }
        .runtime-panel:hover {
            border-color: var(--violet-200);
            box-shadow: 0 10px 24px rgba(99, 102, 241, 0.13);
        }
        .runtime-row + .runtime-row {
            border-top: 1px solid var(--line);
            margin-top: 0.72rem;
            padding-top: 0.72rem;
        }
        .page-heading {
            align-items: center;
            display: flex;
            justify-content: space-between;
            margin: 0 0 1.5rem;
        }
        .page-heading h1 {
            color: var(--ink);
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: 0;
            line-height: 1.25;
            margin: 0;
        }
        .status-inline {
            align-items: center;
            background: var(--success-soft);
            border: 1px solid #bee9dc;
            border-radius: 999px;
            color: #247c69;
            display: inline-flex;
            font-size: 0.76rem;
            gap: 0.4rem;
            padding: 0.3rem 0.62rem;
        }
        .status-dot {
            background: var(--success);
            border-radius: 50%;
            display: inline-block;
            height: 0.48rem;
            width: 0.48rem;
        }
        .status-inline:has(.status-dot.offline) {
            background: #fff0f2;
            border-color: #f4ccd1;
            color: var(--danger);
        }
        .status-dot.offline { background: var(--danger); }
        .section-label {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 650;
            letter-spacing: 0;
            margin: 1.2rem 0 0.5rem;
        }
        .model-line {
            color: var(--ink);
            font-size: 0.86rem;
            font-weight: 650;
            overflow-wrap: anywhere;
        }
        .model-line span {
            color: var(--muted);
            font-weight: 500;
        }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid var(--violet-100);
            border-radius: 14px;
            box-shadow: 0 5px 18px rgba(99, 102, 241, 0.06);
            min-height: 6.25rem;
            padding: 0.8rem 0.9rem;
        }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] {
            color: var(--ink);
            font-size: 1.25rem;
            overflow-wrap: anywhere;
        }
        .metric-grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .metric-item {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(191, 219, 254, 0.9);
            border-radius: 14px;
            box-shadow: 0 5px 18px rgba(99, 102, 241, 0.06);
            min-height: 6.25rem;
            padding: 1.05rem 1.1rem;
            transition: border-color 160ms ease, box-shadow 160ms ease,
                transform 160ms ease;
        }
        .metric-item:hover {
            border-color: var(--violet-200);
            box-shadow: 0 12px 28px rgba(99, 102, 241, 0.15);
            transform: translateY(-1px);
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.82rem;
            line-height: 1.4;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.12rem;
            font-weight: 700;
            line-height: 1.35;
            margin-top: 0.65rem;
            overflow-wrap: anywhere;
        }
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="stFormSubmitButton"] button {
            border-radius: 10px;
            font-weight: 650;
            transition: border-color 160ms ease, box-shadow 160ms ease,
                transform 160ms ease;
        }
        [data-testid="stButton"] button[kind="secondary"],
        [data-testid="stDownloadButton"] button[kind="secondary"] {
            background: #ffffff;
            border-color: var(--sky-200);
            color: var(--sky-700);
        }
        [data-testid="stButton"] button[kind="secondary"]:hover,
        [data-testid="stDownloadButton"] button[kind="secondary"]:hover {
            background: var(--violet-50);
            border-color: var(--violet-200);
            color: var(--indigo-600);
            box-shadow: 0 7px 18px rgba(99, 102, 241, 0.12);
            transform: translateY(-1px);
        }
        [data-testid="stButton"] button:disabled,
        [data-testid="stDownloadButton"] button:disabled,
        [data-testid="stFormSubmitButton"] button:disabled {
            background: #e8f3f8 !important;
            border-color: #d5e7ef !important;
            color: #86a5b5 !important;
            opacity: 1 !important;
        }
        button[kind="primary"] {
            background: linear-gradient(135deg, var(--sky-500), var(--violet-500)) !important;
            border-color: transparent !important;
        }
        button[kind="primary"]:hover {
            background: linear-gradient(135deg, var(--sky-600), var(--indigo-600)) !important;
            border-color: transparent !important;
            box-shadow: 0 10px 22px rgba(99, 102, 241, 0.24);
            transform: translateY(-1px);
        }
        [data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stFileUploaderDropzone"] {
            background: var(--sky-50) !important;
            border-color: var(--sky-200) !important;
            border-radius: 10px !important;
            color: var(--ink) !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stNumberInput"] > div {
            background: rgba(239, 246, 255, 0.82) !important;
            border-color: var(--violet-100) !important;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus {
            border-color: var(--indigo-500) !important;
            box-shadow: 0 0 0 1px var(--indigo-500),
                0 0 0 4px rgba(99, 102, 241, 0.09) !important;
        }
        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.84);
            border-color: var(--violet-100);
            border-radius: 14px;
            box-shadow: 0 8px 26px rgba(99, 102, 241, 0.07);
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(
                120deg,
                rgba(239, 246, 255, 0.82),
                rgba(245, 243, 255, 0.82)
            );
            border-color: var(--violet-200) !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 3px rgba(51, 65, 85, 0.05);
        }
        [data-testid="stFileUploaderDropzoneInstructions"] small {
            display: none;
        }
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            border-bottom: 1px solid var(--line);
            gap: 1.1rem;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            border-radius: 0;
            color: var(--muted);
            padding-left: 0;
            padding-right: 0;
        }
        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.86);
            border-color: var(--violet-100);
            border-radius: 14px;
            transition: border-color 160ms ease, box-shadow 160ms ease;
        }
        [data-testid="stExpander"]:hover {
            border-color: var(--violet-200);
            box-shadow: 0 9px 22px rgba(99, 102, 241, 0.1);
        }
        [data-testid="stChatMessage"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--violet-100);
            border-radius: 14px;
            margin-bottom: 0.65rem;
            padding: 0.65rem 0.85rem;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(120deg, var(--sky-50), var(--violet-50));
        }
        [data-testid="stBottom"] {
            background: rgba(247, 248, 255, 0.92);
            border-top: 1px solid var(--violet-100);
        }
        [data-testid="stChatInput"] > div {
            background: var(--surface);
            border: 1px solid var(--sky-300);
            border-radius: 14px;
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.1);
        }
        [data-testid="stCodeBlock"] {
            border: 1px solid var(--line);
            border-radius: 6px;
        }
        .row-title {
            color: var(--ink);
            font-weight: 700;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .row-meta {
            color: var(--muted);
            font-size: 0.82rem;
            line-height: 1.45;
            margin-top: 0.15rem;
            overflow-wrap: anywhere;
        }
        .row-divider {
            background: var(--line);
            height: 1px;
            margin: 0.65rem 0;
        }
        .empty-state {
            align-items: center;
            background: linear-gradient(
                135deg,
                rgba(255, 255, 255, 0.82),
                rgba(245, 243, 255, 0.72)
            );
            border: 1px dashed var(--violet-200);
            border-radius: 14px;
            color: var(--muted);
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin: 1rem 0;
            min-height: 9.5rem;
            padding: 2rem 1rem;
            text-align: center;
        }
        .empty-state-rule {
            background: linear-gradient(90deg, var(--sky-400), var(--violet-400));
            border-radius: 999px;
            height: 0.28rem;
            margin-bottom: 0.8rem;
            width: 2.5rem;
        }
        .empty-state-title {
            color: var(--ink);
            font-size: 0.95rem;
            font-weight: 700;
        }
        .empty-state-meta {
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 0.24rem;
        }
        @media (max-width: 768px) {
            .block-container { padding: 3rem 1rem 5.5rem; }
            .page-heading { align-items: flex-start; flex-direction: column; gap: 0.45rem; }
            .page-heading h1 { font-size: 1.35rem; }
            [data-testid="stMetric"] { min-height: 5.5rem; }
            .metric-grid { gap: 0.7rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .metric-item { min-height: 5.8rem; padding: 0.85rem 0.9rem; }
            .metric-value { font-size: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    status = st.session_state.get("system_status") or {}
    config = st.session_state.get("config") or {}
    version = escape(str(status.get("version", "-")))
    with st.sidebar:
        st.markdown(
            '<div class="brand-lockup">'
            '<div class="brand-mark">R</div>'
            '<div><div class="brand-name">RAG Studio</div>'
            f'<div class="brand-meta">本地知识工作台 · v{version}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-label">工作区</div>', unsafe_allow_html=True)
        page = st.radio(
            "工作区",
            options=list(PAGES),
            label_visibility="collapsed",
        )
        online = bool(status)
        state_class = "" if online else " offline"
        state_label = "服务在线" if online else "后端未连接"
        runtime_rows = ""
        if config:
            llm_provider = PROVIDER_LABELS.get(
                str(config["llm_provider"]),
                str(config["llm_provider"]),
            )
            embedding_provider = PROVIDER_LABELS.get(
                str(config["embedding_provider"]),
                str(config["embedding_provider"]),
            )
            runtime_rows = (
                '<div class="runtime-row"><div class="section-label">生成模型</div>'
                f'<div class="model-line">{escape(str(config["active_llm_model"]))}'
                f"<br><span>{escape(llm_provider)}</span></div></div>"
                '<div class="runtime-row"><div class="section-label">Embedding</div>'
                f'<div class="model-line">{escape(str(config["active_embedding_model"]))}'
                f"<br><span>{escape(embedding_provider)}</span></div></div>"
            )
        st.markdown(
            '<div class="section-label">运行环境</div><div class="runtime-panel">'
            f'<div class="status-inline"><span class="status-dot{state_class}"></span>'
            f"{state_label}</div>{runtime_rows}</div>",
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("刷新状态", icon=":material/refresh:", use_container_width=True):
            refresh_workspace()
            st.rerun()
    return page


def render_page_header(title: str) -> None:
    online = bool(st.session_state.get("system_status"))
    status_class = "" if online else " offline"
    status_label = "运行正常" if online else "服务不可用"
    st.markdown(
        f'<div class="page-heading"><h1>{escape(title)}</h1>'
        f'<div class="status-inline"><span class="status-dot{status_class}"></span>'
        f"{status_label}</div></div>",
        unsafe_allow_html=True,
    )


def render_workspace_metrics() -> None:
    status = st.session_state.get("system_status") or {}
    stats = status.get("knowledge_base", {})
    config = st.session_state.get("config") or {}
    document_total = stats.get("documents", 0)
    repository_total = stats.get("repositories", 0)
    metrics = [
        ("知识片段", stats.get("chunks", 0)),
        ("文档 / 代码库", f"{document_total} / {repository_total}"),
        ("生成模型", config.get("active_llm_model", "-")),
        ("Embedding", config.get("active_embedding_model", "-")),
    ]
    items = "".join(
        '<div class="metric-item">'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>'
        "</div>"
        for label, value in metrics
    )
    st.markdown(f'<div class="metric-grid">{items}</div>', unsafe_allow_html=True)


def render_chat_page() -> None:
    render_page_header("对话工作台")
    render_workspace_metrics()
    config = st.session_state.get("config") or {}

    with st.container(border=True):
        st.markdown('<div class="section-label">对话参数</div>', unsafe_allow_html=True)
        control_columns = st.columns([1.25, 1.25, 1, 1.15, 0.8])
        answer_mode_label = control_columns[0].selectbox("回答模式", list(ANSWER_MODES))
        strategy_values = list(RETRIEVAL_STRATEGIES)
        strategy_default = RETRIEVAL_STRATEGY_LABELS.get(
            str(config.get("retrieval_strategy", "similarity")),
            strategy_values[0],
        )
        strategy_label = control_columns[1].selectbox(
            "检索策略",
            strategy_values,
            index=strategy_values.index(strategy_default),
        )
        configured_top_k = int(config.get("default_top_k", 4))
        top_k = control_columns[2].number_input(
            "返回片段",
            min_value=1,
            max_value=10,
            value=max(1, min(configured_top_k, 10)),
            step=1,
        )
        export_text = build_chat_export(st.session_state.messages)
        control_columns[3].download_button(
            "导出对话",
            data=export_text,
            file_name=f"rag-chat-{datetime.now():%Y%m%d-%H%M}.md",
            mime="text/markdown",
            icon=":material/download:",
            use_container_width=True,
            disabled=not st.session_state.messages,
        )
        if control_columns[4].button(
            "清空",
            icon=":material/delete_sweep:",
            use_container_width=True,
            disabled=not st.session_state.messages,
        ):
            st.session_state.messages = []
            st.rerun()

    if not st.session_state.messages:
        status = st.session_state.get("system_status") or {}
        chunk_total = status.get("knowledge_base", {}).get("chunks", 0)
        st.markdown(
            '<div class="empty-state"><div class="empty-state-rule"></div>'
            '<div class="empty-state-title">暂无对话记录</div>'
            f'<div class="empty-state-meta">{chunk_total} 个知识片段已就绪</div></div>',
            unsafe_allow_html=True,
        )
    else:
        render_chat_history()

    if st.session_state.messages:
        question = st.chat_input("向当前知识库提问")
    else:
        with st.form("first_question_form", clear_on_submit=True):
            composer_columns = st.columns([6, 1])
            question = composer_columns[0].text_input(
                "问题", placeholder="向当前知识库提问", label_visibility="collapsed"
            )
            submitted = composer_columns[1].form_submit_button(
                "发送",
                type="primary",
                icon=":material/arrow_upward:",
                use_container_width=True,
            )
        if not submitted:
            question = ""
    if question:
        handle_question(
            question,
            int(top_k),
            ANSWER_MODES[answer_mode_label],
            RETRIEVAL_STRATEGIES[strategy_label],
        )


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("is_error"):
                st.error(message["content"])
            else:
                st.markdown(message["content"])
            render_answer_metadata(message.get("metadata", {}))
            render_sources(message.get("sources", []), message.get("message_id", "history"))


def handle_question(
    question: str,
    top_k: int,
    answer_mode: str,
    retrieval_strategy: str,
) -> None:
    user_message = {"role": "user", "content": question}
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("正在检索并生成回答..."):
            ok, payload = api_post(
                "/api/chat",
                json={
                    "question": question,
                    "top_k": top_k,
                    "answer_mode": answer_mode,
                    "retrieval_strategy": retrieval_strategy,
                },
            )
        message_id = str(len(st.session_state.messages) + 1)
        if ok and isinstance(payload, dict):
            answer = payload.get("answer", "后端未返回回答内容。")
            sources = payload.get("sources", [])
            st.markdown(answer)
            render_answer_metadata(payload)
            render_sources(sources, message_id)
            assistant_message = {
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "metadata": payload,
                "message_id": message_id,
            }
        else:
            error = str(payload)
            st.error(error)
            assistant_message = {
                "role": "assistant",
                "content": error,
                "message_id": message_id,
                "is_error": True,
            }
    st.session_state.messages.extend([user_message, assistant_message])


def render_sources(sources: list[dict[str, Any]], message_id: str) -> None:
    if not sources:
        return
    st.markdown('<div class="section-label">引用来源</div>', unsafe_allow_html=True)
    for source in sources:
        source_id = source.get("source_id", "?")
        file_name = source.get("file_name", "未知文件")
        location = _location_text(source)
        title_parts = [f"[{source_id}] {file_name}", source.get("symbol_name"), location]
        title = " · ".join(str(part) for part in title_parts if part)
        with st.expander(title, expanded=False, icon=":material/description:"):
            path = source.get("relative_path") or source.get("module_path")
            if path:
                st.caption(str(path))
            diagnostics = _source_diagnostics(source)
            if diagnostics:
                st.caption(" · ".join(diagnostics))
            content = source.get("content") or source.get("preview", "")
            st.code(content, language=source.get("language") or None)
            st.download_button(
                "下载来源",
                data=content,
                file_name=f"source-{message_id}-{source_id}.txt",
                mime="text/plain",
                icon=":material/download:",
                key=f"source_download_{message_id}_{source_id}",
            )


def _source_diagnostics(source: dict[str, Any]) -> list[str]:
    diagnostics = []
    score = source.get("score")
    if isinstance(score, int | float):
        diagnostics.append(f"综合分 {score:.2f}")
    vector_score = source.get("vector_score")
    if isinstance(vector_score, int | float):
        diagnostics.append(f"向量 {vector_score:.2f}")
    keyword_score = source.get("keyword_score")
    if isinstance(keyword_score, int | float):
        diagnostics.append(f"关键词 {keyword_score:.2f}")
    reranker_score = source.get("reranker_score")
    if isinstance(reranker_score, int | float):
        diagnostics.append(f"重排 {reranker_score:.2f}")
    if source.get("retrieval_rank"):
        diagnostics.append(f"初始召回第 {source['retrieval_rank']} 位")
    matched = source.get("matched_keywords", [])
    if matched:
        diagnostics.append(f"命中词 {', '.join(matched)}")
    return diagnostics


def render_answer_metadata(payload: dict[str, Any]) -> None:
    metadata = []
    basis = payload.get("answer_basis")
    if basis:
        metadata.append(f"依据 {ANSWER_BASIS_LABELS.get(basis, basis)}")
    if payload.get("elapsed_ms") is not None:
        metadata.append(f"总耗时 {payload['elapsed_ms']} ms")
    if payload.get("retrieved_chunks") is not None:
        candidate_count = payload.get("candidate_count", payload["retrieved_chunks"])
        metadata.append(f"候选 {candidate_count} / 返回 {payload['retrieved_chunks']}")
    if payload.get("retrieval_strategy"):
        strategy = RETRIEVAL_STRATEGY_LABELS.get(
            payload["retrieval_strategy"], payload["retrieval_strategy"]
        )
        metadata.append(str(strategy))
    if payload.get("llm_model"):
        metadata.append(str(payload["llm_model"]))
    if metadata:
        st.caption(" · ".join(metadata))


def build_chat_export(messages: list[dict[str, Any]]) -> str:
    lines = ["# RAG Studio 对话导出", "", f"导出时间：{datetime.now():%Y-%m-%d %H:%M}", ""]
    for message in messages:
        heading = "问题" if message.get("role") == "user" else "回答"
        lines.extend([f"## {heading}", "", str(message.get("content", "")), ""])
        sources = message.get("sources", [])
        if sources:
            lines.extend(["### 来源", ""])
            for source in sources:
                location = _location_text(source)
                suffix = f" · {location}" if location else ""
                source_id = source.get("source_id", "?")
                file_name = source.get("file_name", "")
                lines.append(f"- [{source_id}] {file_name}{suffix}")
            lines.append("")
    return "\n".join(lines)


def render_knowledge_page() -> None:
    render_page_header("知识库")
    render_workspace_metrics()
    st.markdown('<div class="section-label">新增内容</div>', unsafe_allow_html=True)
    upload_column, action_column = st.columns([4, 1])
    uploaded_file = upload_column.file_uploader(
        "选择文档或代码库 ZIP",
        type=SUPPORTED_TYPES,
        label_visibility="collapsed",
    )
    if action_column.button(
        "上传并入库",
        type="primary",
        icon=":material/upload_file:",
        use_container_width=True,
        disabled=uploaded_file is None,
    ):
        upload_to_knowledge_base(uploaded_file)

    documents_tab, repositories_tab = st.tabs(["文档", "代码库"])
    with documents_tab:
        render_documents()
    with repositories_tab:
        render_repositories()

    st.markdown('<div class="section-label">数据操作</div>', unsafe_allow_html=True)
    if not st.session_state.confirm_clear:
        if st.button("清空知识库", icon=":material/delete_sweep:"):
            st.session_state.confirm_clear = True
            st.rerun()
    else:
        st.warning("此操作将删除全部文档、代码库和向量索引。")
        confirm_column, cancel_column, _ = st.columns([1, 1, 4])
        if confirm_column.button("确认清空", type="primary", use_container_width=True):
            ok, payload = api_delete("/api/documents")
            if ok:
                st.session_state.confirm_clear = False
                refresh_workspace()
                st.rerun()
            else:
                st.error(payload)
        if cancel_column.button("取消", use_container_width=True):
            st.session_state.confirm_clear = False
            st.rerun()


def upload_to_knowledge_base(uploaded_file: Any) -> None:
    is_repository = uploaded_file.name.lower().endswith(".zip")
    endpoint = "/api/repositories/upload" if is_repository else "/api/upload"
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    with st.spinner("正在解析并建立索引..."):
        ok, payload = api_post(endpoint, files=files)
    if ok and isinstance(payload, dict):
        if is_repository:
            st.success(
                f"已入库 {payload['files_indexed']} 个文件，"
                f"生成 {payload['chunks_indexed']} 个片段。"
            )
        else:
            st.success(f"已生成 {payload['chunks_indexed']} 个片段。")
        refresh_workspace()
        st.rerun()
    else:
        st.error(payload)


def render_documents() -> None:
    documents = st.session_state.get("documents", [])
    if not documents:
        st.markdown('<div class="empty-state">暂无文档</div>', unsafe_allow_html=True)
        return
    for document in documents:
        info_column, action_column = st.columns([6, 1])
        file_name = escape(str(document.get("original_file_name", "未知文档")))
        model = escape(str(document.get("embedding_model", "-")))
        relative_path = document.get("relative_path")
        path_text = f" · {escape(str(relative_path))}" if relative_path else ""
        info_column.markdown(
            f'<div class="row-title">{file_name}</div>'
            f'<div class="row-meta">{document.get("chunks_indexed", 0)} 片段 · '
            f"{model}{path_text}</div>",
            unsafe_allow_html=True,
        )
        document_id = document["document_id"]
        if action_column.button(
            "删除",
            icon=":material/delete:",
            key=f"delete_document_{document_id}",
            use_container_width=True,
        ):
            ok, payload = api_delete(f"/api/documents/{document_id}")
            if ok:
                refresh_workspace()
                st.rerun()
            else:
                st.error(payload)
        st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)


def render_repositories() -> None:
    repositories = st.session_state.get("repositories", [])
    if not repositories:
        st.markdown('<div class="empty-state">暂无代码库</div>', unsafe_allow_html=True)
        return
    for repository in repositories:
        info_column, reindex_column, delete_column = st.columns([5, 1, 1])
        repository_id = repository["repository_id"]
        info_column.markdown(
            f'<div class="row-title">{escape(str(repository["name"]))}</div>'
            f'<div class="row-meta">{repository["files_indexed"]} 文件 · '
            f'{repository["chunks_indexed"]} 片段 · 忽略 {repository["ignored_files"]}</div>',
            unsafe_allow_html=True,
        )
        if reindex_column.button(
            "重建",
            icon=":material/restart_alt:",
            key=f"reindex_repository_{repository_id}",
            use_container_width=True,
        ):
            with st.spinner("正在重建索引..."):
                ok, payload = api_post(f"/api/repositories/{repository_id}/reindex")
            if ok:
                refresh_workspace()
                st.rerun()
            else:
                st.error(payload)
        if delete_column.button(
            "删除",
            icon=":material/delete:",
            key=f"delete_repository_{repository_id}",
            use_container_width=True,
        ):
            ok, payload = api_delete(f"/api/repositories/{repository_id}")
            if ok:
                refresh_workspace()
                st.rerun()
            else:
                st.error(payload)
        st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)


def render_config_page() -> None:
    render_page_header("配置中心")
    config = st.session_state.get("config")
    status = st.session_state.get("system_status") or {}
    if not config:
        st.error(st.session_state.get("config_error", "无法读取运行时配置。"))
        return

    render_provider_status(status, config)
    model_tab, retrieval_tab = st.tabs(["模型服务", "检索与索引"])
    with model_tab:
        render_model_config_form(config, status)
    with retrieval_tab:
        render_retrieval_config_form(config)


def render_provider_status(status: dict[str, Any], config: dict[str, Any]) -> None:
    ollama = status.get("ollama", {})
    columns = st.columns(3)
    llm_provider = str(config["llm_provider"])
    columns[0].metric(
        "当前 LLM",
        f"{PROVIDER_LABELS.get(llm_provider, llm_provider)} / {config['active_llm_model']}",
    )
    columns[1].metric(
        OLLAMA_LABEL,
        "已连接" if ollama.get("connected") else "未连接",
        f"{len(ollama.get('models', []))} 个本地模型" if ollama.get("connected") else None,
    )
    columns[2].metric(
        "OpenAI",
        "已配置" if config.get("openai_api_key_configured") else "未配置",
    )
    if config.get("requires_reindex"):
        st.warning("当前 Embedding 与已有索引不一致，需要清空知识库并重新入库。")
    installed_models = [str(model) for model in ollama.get("models", [])]
    configured_model = str(config.get("ollama_chat_model", ""))
    if (
        config.get("llm_provider") == "ollama"
        and ollama.get("connected")
        and configured_model not in installed_models
    ):
        available = "、".join(installed_models) or "无"
        st.error(f"当前模型 {configured_model} 未安装。已安装模型：{available}。")


def render_model_config_form(config: dict[str, Any], status: dict[str, Any]) -> None:
    with st.form("model_config_form"):
        st.markdown('<div class="section-label">生成模型</div>', unsafe_allow_html=True)
        provider_column, model_column = st.columns(2)
        provider_options = ["demo", "openai", "ollama"]
        llm_provider = provider_column.selectbox(
            "LLM Provider",
            provider_options,
            index=provider_options.index(config["llm_provider"]),
            format_func=lambda value: PROVIDER_LABELS.get(value, value),
        )
        ollama_models = _ollama_model_options(config, status)
        configured_ollama_model = str(config["ollama_chat_model"])
        model_index = (
            ollama_models.index(configured_ollama_model)
            if configured_ollama_model in ollama_models
            else 0
        )
        ollama_chat_model = model_column.selectbox(
            f"{OLLAMA_LABEL} 模型",
            ollama_models,
            index=model_index,
        )
        custom_ollama_model = st.text_input("手动输入已安装模型", value="")

        openai_model_column, openai_url_column = st.columns(2)
        openai_chat_model = openai_model_column.text_input(
            "OpenAI 模型",
            value=config["openai_chat_model"],
        )
        openai_base_url = openai_url_column.text_input(
            "OpenAI Base URL",
            value=config.get("openai_base_url") or "",
        )
        key_column, clear_column = st.columns([3, 1])
        openai_key = key_column.text_input(
            "OpenAI API Key",
            value="",
            type="password",
            placeholder="已配置，留空则保持不变"
            if config.get("openai_api_key_configured")
            else "未配置",
        )
        clear_openai_key = clear_column.checkbox("清除现有 Key", value=False)

        st.markdown(
            f'<div class="section-label">{OLLAMA_LABEL} 参数</div>',
            unsafe_allow_html=True,
        )
        base_url_column, temperature_column, context_column = st.columns(3)
        ollama_base_url = base_url_column.text_input(
            f"{OLLAMA_LABEL} Base URL",
            value=config["ollama_base_url"],
        )
        ollama_temperature = temperature_column.number_input(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(config["ollama_temperature"]),
            step=0.1,
        )
        ollama_num_ctx = context_column.number_input(
            "Context Length",
            min_value=512,
            max_value=131072,
            value=int(config["ollama_num_ctx"]),
            step=512,
        )
        predict_column, top_p_column, penalty_column = st.columns(3)
        ollama_num_predict = predict_column.number_input(
            "Max Output",
            min_value=1,
            max_value=32768,
            value=int(config["ollama_num_predict"]),
        )
        ollama_top_p = top_p_column.number_input(
            "Top P",
            min_value=0.01,
            max_value=1.0,
            value=float(config["ollama_top_p"]),
            step=0.05,
        )
        ollama_repeat_penalty = penalty_column.number_input(
            "Repeat Penalty",
            min_value=1.0,
            max_value=2.0,
            value=float(config["ollama_repeat_penalty"]),
            step=0.05,
        )

        st.markdown('<div class="section-label">Embedding</div>', unsafe_allow_html=True)
        embedding_provider_column, embedding_model_column = st.columns(2)
        embedding_options = ["demo", "local", "openai"]
        embedding_provider = embedding_provider_column.selectbox(
            "Embedding Provider",
            embedding_options,
            index=embedding_options.index(config["embedding_provider"]),
        )
        local_embedding_model = embedding_model_column.text_input(
            "本地 Embedding 模型",
            value=config["local_embedding_model"],
        )
        openai_embedding_model = st.text_input(
            "OpenAI Embedding 模型",
            value=config["openai_embedding_model"],
        )
        submitted = st.form_submit_button(
            "保存模型配置",
            type="primary",
            icon=":material/save:",
        )

    if submitted:
        active_ollama_model = custom_ollama_model.strip() or ollama_chat_model
        installed_models = {
            str(model) for model in status.get("ollama", {}).get("models", [])
        }
        if (
            llm_provider == "ollama"
            and status.get("ollama", {}).get("connected")
            and active_ollama_model not in installed_models
        ):
            st.error(
                f"{OLLAMA_LABEL} 中未安装模型 {active_ollama_model}，配置未保存。"
            )
            return
        payload: dict[str, Any] = {
            "llm_provider": llm_provider,
            "embedding_provider": embedding_provider,
            "openai_base_url": openai_base_url,
            "openai_chat_model": openai_chat_model,
            "openai_embedding_model": openai_embedding_model,
            "ollama_base_url": ollama_base_url,
            "ollama_chat_model": active_ollama_model,
            "ollama_temperature": ollama_temperature,
            "ollama_num_ctx": ollama_num_ctx,
            "ollama_num_predict": ollama_num_predict,
            "ollama_top_p": ollama_top_p,
            "ollama_repeat_penalty": ollama_repeat_penalty,
            "local_embedding_model": local_embedding_model,
        }
        if openai_key or clear_openai_key:
            payload["openai_api_key"] = "" if clear_openai_key else openai_key
        save_runtime_config(payload)


def _ollama_model_options(config: dict[str, Any], status: dict[str, Any]) -> list[str]:
    ollama_status = status.get("ollama", {})
    discovered = [str(model) for model in ollama_status.get("models", []) if model]
    if ollama_status.get("connected") and discovered:
        return list(dict.fromkeys(discovered))
    candidates = [
        config["ollama_chat_model"],
        "qwen2.5:7b",
        "qwen3:8b",
        "llama3.1:8b",
    ]
    return list(dict.fromkeys(str(model) for model in candidates if model))


def render_retrieval_config_form(config: dict[str, Any]) -> None:
    with st.form("retrieval_config_form"):
        st.markdown('<div class="section-label">召回参数</div>', unsafe_allow_html=True)
        strategy_column, top_k_column, fetch_k_column = st.columns(3)
        strategy_options = ["similarity", "mmr"]
        retrieval_strategy = strategy_column.selectbox(
            "默认策略",
            strategy_options,
            index=strategy_options.index(config["retrieval_strategy"]),
        )
        default_top_k = top_k_column.number_input(
            "默认 Top K",
            min_value=1,
            max_value=10,
            value=int(config["default_top_k"]),
        )
        retrieval_fetch_k = fetch_k_column.number_input(
            "候选数量",
            min_value=1,
            max_value=200,
            value=int(config["retrieval_fetch_k"]),
        )
        mmr_lambda_mult = st.slider(
            "MMR 相关性权重",
            min_value=0.0,
            max_value=1.0,
            value=float(config["mmr_lambda_mult"]),
            step=0.05,
        )

        st.markdown('<div class="section-label">混合排序权重</div>', unsafe_allow_html=True)
        vector_column, keyword_column, filename_column, symbol_column = st.columns(4)
        hybrid_vector_weight = vector_column.number_input(
            "向量",
            min_value=0.0,
            max_value=1.0,
            value=float(config["hybrid_vector_weight"]),
            step=0.05,
        )
        hybrid_keyword_weight = keyword_column.number_input(
            "关键词",
            min_value=0.0,
            max_value=1.0,
            value=float(config["hybrid_keyword_weight"]),
            step=0.05,
        )
        hybrid_filename_weight = filename_column.number_input(
            "文件名",
            min_value=0.0,
            max_value=1.0,
            value=float(config["hybrid_filename_weight"]),
            step=0.05,
        )
        hybrid_symbol_weight = symbol_column.number_input(
            "符号",
            min_value=0.0,
            max_value=1.0,
            value=float(config["hybrid_symbol_weight"]),
            step=0.05,
        )
        weight_total = sum(
            (
                hybrid_vector_weight,
                hybrid_keyword_weight,
                hybrid_filename_weight,
                hybrid_symbol_weight,
            )
        )
        st.caption(f"当前总和：{weight_total:.2f}")

        st.markdown('<div class="section-label">切分与重排</div>', unsafe_allow_html=True)
        chunk_column, overlap_column = st.columns(2)
        chunk_size = chunk_column.number_input(
            "Chunk Size",
            min_value=100,
            max_value=10000,
            value=int(config["chunk_size"]),
            step=50,
        )
        chunk_overlap = overlap_column.number_input(
            "Chunk Overlap",
            min_value=0,
            max_value=5000,
            value=int(config["chunk_overlap"]),
            step=25,
        )
        reranker_provider_column, reranker_model_column = st.columns(2)
        reranker_options = ["none", "cross_encoder"]
        reranker_provider = reranker_provider_column.selectbox(
            "Reranker Provider",
            reranker_options,
            index=reranker_options.index(config["reranker_provider"]),
        )
        reranker_model = reranker_model_column.text_input(
            "Reranker 模型",
            value=config["reranker_model"],
        )
        candidate_column, batch_column, weight_column = st.columns(3)
        reranker_candidate_k = candidate_column.number_input(
            "重排候选",
            min_value=1,
            max_value=100,
            value=int(config["reranker_candidate_k"]),
        )
        reranker_batch_size = batch_column.number_input(
            "Batch Size",
            min_value=1,
            max_value=256,
            value=int(config["reranker_batch_size"]),
        )
        reranker_weight = weight_column.slider(
            "重排权重",
            min_value=0.0,
            max_value=1.0,
            value=float(config["reranker_weight"]),
            step=0.05,
        )
        submitted = st.form_submit_button(
            "保存检索配置",
            type="primary",
            icon=":material/save:",
            disabled=abs(weight_total - 1.0) > 1e-6,
        )

    if submitted:
        save_runtime_config(
            {
                "retrieval_strategy": retrieval_strategy,
                "default_top_k": default_top_k,
                "retrieval_fetch_k": retrieval_fetch_k,
                "mmr_lambda_mult": mmr_lambda_mult,
                "hybrid_vector_weight": hybrid_vector_weight,
                "hybrid_keyword_weight": hybrid_keyword_weight,
                "hybrid_filename_weight": hybrid_filename_weight,
                "hybrid_symbol_weight": hybrid_symbol_weight,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "reranker_provider": reranker_provider,
                "reranker_model": reranker_model,
                "reranker_candidate_k": reranker_candidate_k,
                "reranker_batch_size": reranker_batch_size,
                "reranker_weight": reranker_weight,
            }
        )


def save_runtime_config(payload: dict[str, Any]) -> None:
    ok, response = api_patch("/api/config", json=payload)
    if ok and isinstance(response, dict):
        st.session_state.config = response
        refresh_workspace()
        st.success("配置已保存并生效。")
        st.rerun()
    else:
        st.error(response)


def _location_text(source: dict[str, Any]) -> str | None:
    start_line = source.get("start_line")
    end_line = source.get("end_line")
    if start_line and end_line:
        return f"行 {start_line}-{end_line}"
    if source.get("page"):
        return f"第 {source['page']} 页"
    return None


st.set_page_config(
    page_title="RAG Studio",
    page_icon=":material/database:",
    layout="wide",
)
inject_styles()
init_state()
active_page = render_sidebar()

if active_page == "对话工作台":
    render_chat_page()
elif active_page == "知识库":
    render_knowledge_page()
else:
    render_config_page()
