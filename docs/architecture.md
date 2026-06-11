# Architecture

## Overview

The project follows a small RAG pipeline:

1. Upload local files through FastAPI or Streamlit.
2. Load the file into LangChain `Document` objects.
3. Split documents into chunks.
4. Convert chunks into embeddings.
5. Persist vectors in Chroma.
6. Retrieve top-k chunks for each user question.
7. Generate an answer from retrieved context.
8. Return the answer with source metadata.

## Components

- `app/api`: HTTP routes and Pydantic schemas.
- `app/loaders`: file loaders for PDF, Word, text and code files.
- `app/rag/embeddings.py`: demo hash embeddings and OpenAI embeddings adapter.
- `app/rag/vectorstore.py`: Chroma collection setup and retrieval.
- `app/rag/llm.py`: prompt construction and LLM provider adapter.
- `ui/streamlit_app.py`: lightweight frontend for upload and chat.

## Provider Modes

`demo` mode is designed for local development without API keys. It uses deterministic hash embeddings and returns retrieved snippets instead of calling a real LLM.

`openai` mode uses OpenAI embeddings and the Responses API. Configure it through `.env`:

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
```

When changing embedding providers or embedding models, rebuild the Chroma index because vector dimensions may change.
