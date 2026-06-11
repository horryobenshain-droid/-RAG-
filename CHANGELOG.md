# Changelog

## Unreleased

- Add `OPENAI_BASE_URL` support for OpenAI-compatible gateway providers.

## 0.2.0 - 2026-06-11

- Add document registry metadata with document ID, file hash, model config and ingest time.
- Add knowledge base management APIs for listing, deleting and clearing indexed documents.
- Return retrieval scores, elapsed time, retrieved chunk count and provider metadata in chat responses.
- Rewrite the grounding prompt in Simplified Chinese to reduce hallucinations.
- Localize the Streamlit UI to Simplified Chinese and expose document management controls.
- Extend smoke tests to cover upload, chat, list, delete and clear flows.

## 0.1.0 - 2026-06-11

- Initialize FastAPI backend and Streamlit UI.
- Add local upload, parsing, chunking, Chroma persistence and demo retrieval.
- Add OpenAI provider configuration for Responses API and embeddings.
- Add README, architecture notes, roadmap, linting, tests and CI workflow.
