import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Local RAG Knowledge Base", layout="wide")

st.title("Local RAG Knowledge Base")

with st.sidebar:
    st.subheader("Knowledge Base")
    uploaded_file = st.file_uploader(
        "Upload document",
        type=[
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
        ],
    )
    if st.button(
        "Index file",
        type="primary",
        use_container_width=True,
        disabled=uploaded_file is None,
    ):
        with st.spinner("Indexing document..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            response = requests.post(f"{API_BASE_URL}/api/upload", files=files, timeout=120)
        if response.ok:
            result = response.json()
            st.success(f"Indexed {result['chunks_indexed']} chunks.")
        else:
            st.error(response.text)

    st.divider()
    top_k = st.slider("Retrieved chunks", min_value=1, max_value=10, value=4)

question = st.chat_input("Ask a question about your local documents")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    page = f", page {source['page']}" if source.get("page") else ""
                    st.markdown(f"**[{source['source_id']}] {source['file_name']}{page}**")
                    st.caption(source["preview"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving and answering..."):
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                json={"question": question, "top_k": top_k},
                timeout=120,
            )
        if response.ok:
            result = response.json()
            st.markdown(result["answer"])
            with st.expander("Sources"):
                for source in result["sources"]:
                    page = f", page {source['page']}" if source.get("page") else ""
                    st.markdown(f"**[{source['source_id']}] {source['file_name']}{page}**")
                    st.caption(source["preview"])
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                }
            )
        else:
            error_text = response.text
            st.error(error_text)
            st.session_state.messages.append({"role": "assistant", "content": error_text})
