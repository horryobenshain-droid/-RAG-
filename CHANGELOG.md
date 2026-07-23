# Changelog

## Unreleased

- No unreleased changes yet.

## 0.6.0 - 2026-07-23

- Add validated JSON evaluation datasets and model comparison profiles.
- Add batch evaluation for retrieval, citations, answer keywords and latency.
- Report macro Recall@K, citation hit rate, answer keyword recall, pass rate and P95 latency.
- Generate detailed Markdown and machine-readable JSON evaluation reports.
- Add reproducible evaluation corpus fixtures and a CLI with optional corpus ingestion.
- Isolate per-case model failures so unavailable providers do not abort a comparison run.
- Improve Chinese hybrid retrieval and structured code-answer prompting.
- Add configurable Ollama output length, top-p and repetition penalty settings.

## 0.5.0 - 2026-06-13

- Add Ollama LLM provider using the local `/api/chat` endpoint.
- Support Qwen and Llama local chat models through `OLLAMA_CHAT_MODEL`.
- Add Ollama runtime settings for base URL, temperature, context length and timeout.
- Return the active Ollama model in chat responses and health metadata.
- Document local Ollama setup with Qwen and Llama examples.

## 0.4.1 - 2026-06-11

- Add `OPENAI_BASE_URL` support for OpenAI-compatible gateway providers.

## 0.4.0 - 2026-06-11

- Add code-aware chunking with language, symbol and line-range metadata.
- Add hybrid reranking with vector, keyword, filename and symbol signals.
- Return retrieval diagnostics including matched keywords and score breakdowns.
- Show retrieval diagnostics in the Streamlit source panel.
- Improve algorithm-template prompting for code answers.

## 0.3.0 - 2026-06-11

- Add strict and augmented answer modes.
- Return answer basis metadata: knowledge base, model prior or mixed.
- Add local HuggingFace embedding provider with `BAAI/bge-small-zh-v1.5`.
- Add Streamlit answer mode controls.
- Add tests for answer modes and local embedding provider.

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
