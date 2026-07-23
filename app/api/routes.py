from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ClearKnowledgeBaseResponse,
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentRecordResponse,
    Source,
    UploadResponse,
)
from app.core.config import Settings, get_settings
from app.core.files import sanitize_filename, save_upload_file
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
            preview=source.document.page_content.strip()[:300],
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
