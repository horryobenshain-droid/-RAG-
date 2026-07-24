# Changelog

## Unreleased

- No unreleased changes yet.

## 1.0.0 - 2026-07-24

- Add a non-root Python application image for FastAPI and Streamlit.
- Add Docker Compose services for Nginx, Streamlit, FastAPI, Ollama and model initialization.
- Persist application data, HuggingFace caches and Ollama models in separate named volumes.
- Protect the public entry point with file-backed Nginx Basic Auth and keep internal services private.
- Add CPU and NVIDIA GPU deployment modes with health checks and restart policies.
- Restrict FastAPI CORS to configurable origins instead of allowing every origin.
- Add Windows and Linux deployment helpers, production environment templates and backup guidance.
- Validate deployment configuration in CI and document upgrade, rollback and release workflows.

## 0.9.0 - 2026-07-24

- Reorganize Streamlit into chat, knowledge base and configuration workspaces.
- Add validated, persistent runtime configuration APIs for model and retrieval settings.
- Add OpenAI, Ollama Qwen/Llama and Embedding selection without restarting the backend.
- Report provider connectivity, discovered Ollama models and knowledge base statistics.
- Add visual controls for generation, chunking, retrieval, hybrid ranking and reranking.
- Export chat history as Markdown and expose complete, copyable source chunks.
- Warn when the active Embedding configuration no longer matches the stored index.

## 0.8.0 - 2026-07-24

- Add safe ZIP repository upload and batch indexing with configurable file and size limits.
- Ignore VCS metadata, dependencies, virtual environments, build output and binary files.
- Preserve repository, relative path, module path, language, symbol and line metadata.
- Add repository listing, deletion and staged index rebuilding APIs and UI actions.
- Add a repository-focused evaluation case and reproducible code corpus fixture.
- Cache Embedding model instances instead of reloading local model weights for every query.
- Cap interactive Top K at 10 and reduce the default Ollama output limit to avoid oversized requests.
- Let the Streamlit chat timeout outlast the backend model timeout and show a clearer error.

## 0.7.0 - 2026-07-23

- Add similarity and MMR retrieval strategies with request-level switching.
- Make candidate counts, MMR diversity, chunking and hybrid ranking weights configurable.
- Add an optional lazy-loaded CrossEncoder reranker with bounded candidate scoring.
- Return per-source score breakdowns, retrieval ranks and human-readable hit reasons.
- Report retrieval, reranking and generation latency separately in the API and UI.
- Extend evaluation profiles and reports to compare retrieval and reranker configurations.

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
