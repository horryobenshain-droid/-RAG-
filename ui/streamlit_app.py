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
            page = f"第 {source['page']} 页" if source.get("page") else "无页码"
            score = source.get("score")
            score_text = f"相关度 {score:.2f}" if isinstance(score, int | float) else "相关度未知"
            st.markdown(
                f"**[{source['source_id']}] {source['file_name']} · {page} · {score_text}**"
            )
            st.caption(source["preview"])


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
                json={"question": question, "top_k": top_k},
            )
        if ok and isinstance(payload, dict):
            st.markdown(payload["answer"])
            st.caption(
                f"耗时 {payload['elapsed_ms']} ms · "
                f"召回 {payload['retrieved_chunks']} 个片段 · "
                f"模型 {payload['llm_provider']} / {payload['llm_model']}"
            )
            render_sources(payload["sources"])
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": payload["answer"],
                    "sources": payload["sources"],
                }
            )
        else:
            st.error(payload)
            st.session_state.messages.append({"role": "assistant", "content": str(payload)})
