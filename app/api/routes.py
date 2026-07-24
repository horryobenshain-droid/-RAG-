from pathlib import Path
from uuid import uuid4

import requests
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError

from app import __version__
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ClearKnowledgeBaseResponse,
    DeleteDocumentResponse,
    DeleteRepositoryResponse,
    DocumentListResponse,
    DocumentRecordResponse,
    KnowledgeBaseStats,
    ProviderStatus,
    ReindexRepositoryResponse,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUploadResponse,
    RuntimeConfigResponse,
    RuntimeConfigUpdate,
    Source,
    SystemStatusResponse,
    UploadResponse,
)
from app.core.config import Settings, get_settings, update_runtime_settings
from app.core.files import (
    sanitize_filename,
    save_repository_archive,
    save_upload_file,
)
from app.core.repositories import ExtractedRepository, extract_repository_archive
from app.rag.repository_service import (
    delete_repository,
    discard_repository_upload,
    ingest_repository,
    list_repositories,
    reindex_repository,
)
from app.rag.service import (
    answer_question,
    clear_knowledge_base,
    delete_document,
    ingest_file,
    list_documents,
)

router = APIRouter(prefix="/api", tags=["rag"])


@router.post("/upload", response_model=UploadResponse)
def upload_document(
    file: UploadFile = File(...),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UploadResponse:
    original_file_name = sanitize_filename(file.filename or "uploaded-file")
    try:
        saved_path = save_upload_file(file, settings.upload_dir)
        ingest_result = ingest_file(saved_path, settings, original_file_name=original_file_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件入库失败：{exc}") from exc
    finally:
        file.file.close()

    return UploadResponse(
        document_id=ingest_result.document_id,
        original_file_name=ingest_result.original_file_name,
        file_name=saved_path.name,
        saved_path=str(saved_path),
        file_hash=ingest_result.file_hash,
        chunks_indexed=ingest_result.chunks_indexed,
        message="文件上传并入库成功。",
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ChatResponse:
    top_k = request.top_k or settings.default_top_k
    try:
        result = answer_question(
            request.question,
            top_k,
            settings,
            request.answer_mode,
            request.retrieval_strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"问答生成失败：{exc}") from exc

    sources = [
        Source(
            source_id=index,
            file_name=str(source.document.metadata.get("original_file_name", "unknown")),
            page=_human_page(source.document.metadata.get("page")),
            chunk_id=source.document.metadata.get("chunk_id"),
            document_id=_optional_str(source.document.metadata.get("document_id")),
            score=source.score,
            vector_score=source.hybrid_score.vector_score,
            keyword_score=source.hybrid_score.keyword_score,
            filename_score=source.hybrid_score.filename_score,
            symbol_score=source.hybrid_score.symbol_score,
            reranker_score=source.hybrid_score.reranker_score,
            retrieval_rank=source.hybrid_score.retrieval_rank,
            matched_keywords=source.hybrid_score.matched_keywords,
            reasons=source.hybrid_score.reasons,
            language=_optional_str(source.document.metadata.get("language")),
            symbol_name=_optional_str(source.document.metadata.get("symbol_name")),
            start_line=_optional_int(source.document.metadata.get("start_line")),
            end_line=_optional_int(source.document.metadata.get("end_line")),
            repository_id=_optional_str(source.document.metadata.get("repository_id")),
            repository_name=_optional_str(source.document.metadata.get("repository_name")),
            relative_path=_optional_str(source.document.metadata.get("relative_path")),
            module_path=_optional_str(source.document.metadata.get("module_path")),
            preview=source.document.page_content.strip()[:300],
            content=source.document.page_content.strip(),
        )
        for index, source in enumerate(result.sources, start=1)
    ]
    return ChatResponse(
        answer=result.answer,
        sources=sources,
        elapsed_ms=round(result.elapsed_ms, 2),
        retrieved_chunks=len(result.sources),
        llm_provider=result.llm_provider,
        llm_model=result.llm_model,
        embedding_provider=result.embedding_provider,
        embedding_model=result.embedding_model,
        answer_mode=result.answer_mode,
        answer_basis=result.answer_basis,
        retrieval_strategy=result.retrieval_strategy,
        candidate_count=result.candidate_count,
        retrieval_ms=round(result.retrieval_ms, 2),
        reranking_ms=round(result.reranking_ms, 2),
        generation_ms=round(result.generation_ms, 2),
        reranker_provider=result.reranker_provider,
        reranker_model=result.reranker_model,
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_indexed_documents(
    include_deleted: bool = False,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> DocumentListResponse:
    documents = [
        DocumentRecordResponse(**record)
        for record in list_documents(settings, include_deleted=include_deleted)
    ]
    return DocumentListResponse(documents=documents, total=len(documents))


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
def delete_indexed_document(
    document_id: str,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> DeleteDocumentResponse:
    deleted, chunks_deleted = delete_document(document_id, settings)
    if not deleted:
        raise HTTPException(status_code=404, detail="未找到对应文档。")

    return DeleteDocumentResponse(
        document_id=document_id,
        deleted=True,
        chunks_deleted=chunks_deleted,
        message="文档及其向量索引已删除。",
    )


@router.delete("/documents", response_model=ClearKnowledgeBaseResponse)
def clear_indexed_documents(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ClearKnowledgeBaseResponse:
    documents_deleted, chunks_deleted = clear_knowledge_base(settings)
    return ClearKnowledgeBaseResponse(
        documents_deleted=documents_deleted,
        chunks_deleted=chunks_deleted,
        message="知识库已清空。",
    )


@router.post("/repositories/upload", response_model=RepositoryUploadResponse)
def upload_repository(
    file: UploadFile = File(...),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RepositoryUploadResponse:
    original_name = sanitize_filename(file.filename or "repository.zip")
    saved_path: Path | None = None
    extracted: ExtractedRepository | None = None
    try:
        saved_path = save_repository_archive(
            file,
            settings.upload_dir,
            settings.repository_max_archive_bytes,
        )
        extracted = extract_repository_archive(
            archive_path=saved_path,
            repository_dir=settings.repository_dir,
            repository_id=uuid4().hex,
            source_archive_name=original_name,
            max_files=settings.repository_max_files,
            max_file_bytes=settings.repository_max_file_bytes,
            max_total_bytes=settings.repository_max_total_bytes,
        )
        result = ingest_repository(extracted, settings)
    except ValueError as exc:
        discard_repository_upload(extracted, saved_path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        discard_repository_upload(extracted, saved_path)
        raise HTTPException(status_code=500, detail=f"代码库入库失败：{exc}") from exc
    finally:
        file.file.close()

    return RepositoryUploadResponse(
        **result.__dict__,
        message="代码库上传并入库成功。",
    )


@router.get("/repositories", response_model=RepositoryListResponse)
def list_indexed_repositories(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RepositoryListResponse:
    repositories = [RepositoryResponse(**record) for record in list_repositories(settings)]
    return RepositoryListResponse(repositories=repositories, total=len(repositories))


@router.delete("/repositories/{repository_id}", response_model=DeleteRepositoryResponse)
def delete_indexed_repository(
    repository_id: str,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> DeleteRepositoryResponse:
    deleted, documents_deleted, chunks_deleted = delete_repository(repository_id, settings)
    if not deleted:
        raise HTTPException(status_code=404, detail="未找到对应代码库。")
    return DeleteRepositoryResponse(
        repository_id=repository_id,
        deleted=True,
        documents_deleted=documents_deleted,
        chunks_deleted=chunks_deleted,
        message="代码库、源文件及向量索引已删除。",
    )


@router.post(
    "/repositories/{repository_id}/reindex",
    response_model=ReindexRepositoryResponse,
)
def rebuild_repository_index(
    repository_id: str,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ReindexRepositoryResponse:
    try:
        result = reindex_repository(repository_id, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"代码库重建索引失败：{exc}") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="未找到对应代码库。")
    return ReindexRepositoryResponse(
        **result.__dict__,
        message="代码库索引重建成功。",
    )


@router.get("/config", response_model=RuntimeConfigResponse)
def get_runtime_config(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RuntimeConfigResponse:
    return _runtime_config_response(settings)


@router.patch("/config", response_model=RuntimeConfigResponse)
def patch_runtime_config(
    request: RuntimeConfigUpdate,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RuntimeConfigResponse:
    updates = request.model_dump(exclude_unset=True)
    if "openai_api_key" in updates and isinstance(updates["openai_api_key"], str):
        updates["openai_api_key"] = updates["openai_api_key"].strip()
    if "openai_base_url" in updates and updates["openai_base_url"] == "":
        updates["openai_base_url"] = None
    try:
        updated = update_runtime_settings(settings, updates)
    except (OSError, ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _runtime_config_response(updated)


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> SystemStatusResponse:
    documents = list_documents(settings)
    repositories = list_repositories(settings)
    ollama = _probe_ollama(settings.ollama_base_url)
    return SystemStatusResponse(
        version=__version__,
        llm_provider=settings.llm_provider,
        llm_model=_active_llm_model(settings),
        embedding_provider=settings.embedding_provider,
        embedding_model=_active_embedding_model(settings),
        ollama=ollama,
        openai_configured=bool(settings.openai_api_key),
        knowledge_base=KnowledgeBaseStats(
            documents=len(documents),
            repositories=len(repositories),
            chunks=sum(int(document.get("chunks_indexed", 0)) for document in documents),
        ),
    )


def _human_page(page: object) -> int | None:
    if page is None:
        return None
    try:
        return int(page) + 1
    except (TypeError, ValueError):
        return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _runtime_config_response(settings: Settings) -> RuntimeConfigResponse:
    return RuntimeConfigResponse(
        llm_provider=settings.llm_provider,
        active_llm_model=_active_llm_model(settings),
        embedding_provider=settings.embedding_provider,
        active_embedding_model=_active_embedding_model(settings),
        openai_api_key_configured=bool(settings.openai_api_key),
        openai_base_url=settings.openai_base_url,
        openai_chat_model=settings.openai_chat_model,
        openai_embedding_model=settings.openai_embedding_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_chat_model=settings.ollama_chat_model,
        ollama_temperature=settings.ollama_temperature,
        ollama_num_ctx=settings.ollama_num_ctx,
        ollama_num_predict=settings.ollama_num_predict,
        ollama_top_p=settings.ollama_top_p,
        ollama_repeat_penalty=settings.ollama_repeat_penalty,
        ollama_timeout_seconds=settings.ollama_timeout_seconds,
        local_embedding_model=settings.local_embedding_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        default_top_k=settings.default_top_k,
        retrieval_strategy=settings.retrieval_strategy,
        retrieval_fetch_k=settings.retrieval_fetch_k,
        mmr_lambda_mult=settings.mmr_lambda_mult,
        hybrid_vector_weight=settings.hybrid_vector_weight,
        hybrid_keyword_weight=settings.hybrid_keyword_weight,
        hybrid_filename_weight=settings.hybrid_filename_weight,
        hybrid_symbol_weight=settings.hybrid_symbol_weight,
        reranker_provider=settings.reranker_provider,
        reranker_model=settings.reranker_model,
        reranker_device=settings.reranker_device,
        reranker_candidate_k=settings.reranker_candidate_k,
        reranker_batch_size=settings.reranker_batch_size,
        reranker_weight=settings.reranker_weight,
        runtime_configured=settings.runtime_config_path.exists(),
        requires_reindex=_embedding_requires_reindex(settings),
    )


def _active_llm_model(settings: Settings) -> str:
    if settings.llm_provider == "openai":
        return settings.openai_chat_model
    if settings.llm_provider == "ollama":
        return settings.ollama_chat_model
    return "demo-snippet-answer"


def _active_embedding_model(settings: Settings) -> str:
    if settings.embedding_provider == "local":
        return settings.local_embedding_model
    if settings.embedding_provider == "openai":
        return settings.openai_embedding_model
    return "hash-embeddings"


def _embedding_requires_reindex(settings: Settings) -> bool:
    documents = list_documents(settings)
    provider = settings.embedding_provider
    model = _active_embedding_model(settings)
    return any(
        document.get("embedding_provider") != provider
        or document.get("embedding_model") != model
        for document in documents
    )


def _probe_ollama(base_url: str) -> ProviderStatus:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
        response.raise_for_status()
        payload = response.json()
        models = [
            str(item["name"])
            for item in payload.get("models", [])
            if isinstance(item, dict) and item.get("name")
        ]
    except (requests.RequestException, ValueError, TypeError) as exc:
        return ProviderStatus(connected=False, message=f"Ollama 未连接：{exc}")
    message = f"Ollama 已连接，发现 {len(models)} 个模型"
    return ProviderStatus(connected=True, message=message, models=models)
