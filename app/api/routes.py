from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.schemas import ChatRequest, ChatResponse, Source, UploadResponse
from app.core.config import Settings, get_settings
from app.core.files import save_upload_file
from app.rag.service import answer_question, ingest_file

router = APIRouter(prefix="/api", tags=["rag"])


@router.post("/upload", response_model=UploadResponse)
def upload_document(
    file: UploadFile = File(...),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> UploadResponse:
    try:
        saved_path = save_upload_file(file, settings.upload_dir)
        chunks_indexed = ingest_file(saved_path, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {exc}") from exc
    finally:
        file.file.close()

    return UploadResponse(
        file_name=saved_path.name,
        saved_path=str(saved_path),
        chunks_indexed=chunks_indexed,
        message="File uploaded and indexed successfully.",
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


def _human_page(page: object) -> int | None:
    if page is None:
        return None
    try:
        return int(page) + 1
    except (TypeError, ValueError):
        return None
