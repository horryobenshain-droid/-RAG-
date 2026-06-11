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
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {exc}") from exc
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
        answer, documents = answer_question(request.question, top_k, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {exc}") from exc

    sources = [
        Source(
            source_id=index,
            file_name=str(document.metadata.get("file_name", "unknown")),
            page=_human_page(document.metadata.get("page")),
            chunk_id=document.metadata.get("chunk_id"),
            preview=document.page_content.strip()[:300],
        )
        for index, document in enumerate(documents, start=1)
    ]
    return ChatResponse(answer=answer, sources=sources)


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
