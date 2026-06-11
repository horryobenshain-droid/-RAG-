from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document

from app.core.config import Settings
from app.core.files import calculate_sha256
from app.core.registry import DocumentRecord, DocumentRegistry, utc_now
from app.loaders.local_loader import load_local_file
from app.rag.llm import generate_answer
from app.rag.splitter import split_documents
from app.rag.vectorstore import (
    add_documents,
    count_vectors,
    delete_document_vectors,
    reset_vectorstore,
    similarity_search,
)


class IngestResult:
    def __init__(
        self,
        document_id: str,
        file_hash: str,
        chunks_indexed: int,
        original_file_name: str,
    ) -> None:
        self.document_id = document_id
        self.file_hash = file_hash
        self.chunks_indexed = chunks_indexed
        self.original_file_name = original_file_name


def ingest_file(
    path: Path,
    settings: Settings,
    original_file_name: str | None = None,
) -> IngestResult:
    documents = load_local_file(path)
    document_id = uuid4().hex
    file_hash = calculate_sha256(path)
    ingested_at = utc_now()
    display_name = original_file_name or path.name

    for document in documents:
        document.metadata.update(
            {
                "document_id": document_id,
                "file_hash": file_hash,
                "original_file_name": display_name,
                "stored_file_name": path.name,
                "ingested_at": ingested_at,
            }
        )

    chunks = split_documents(documents, settings)
    for chunk in chunks:
        chunk.metadata["chunk_count"] = len(chunks)

    chunks_indexed = add_documents(chunks, settings)
    registry = DocumentRegistry(settings.registry_path)
    registry.add(
        DocumentRecord(
            document_id=document_id,
            original_file_name=display_name,
            stored_file_name=path.name,
            saved_path=str(path),
            extension=path.suffix.lower(),
            file_hash=file_hash,
            chunks_indexed=chunks_indexed,
            embedding_provider=settings.embedding_provider,
            embedding_model=_embedding_model_name(settings),
            llm_provider=settings.llm_provider,
            status="active",
            created_at=ingested_at,
        )
    )
    return IngestResult(
        document_id=document_id,
        file_hash=file_hash,
        chunks_indexed=chunks_indexed,
        original_file_name=display_name,
    )


def answer_question(question: str, top_k: int, settings: Settings) -> tuple[str, list[Document]]:
    documents = similarity_search(question, top_k, settings)
    answer = generate_answer(question, documents, settings)
    return answer, documents


def list_documents(settings: Settings, include_deleted: bool = False) -> list[dict[str, object]]:
    registry = DocumentRegistry(settings.registry_path)
    return registry.list_documents(include_deleted=include_deleted)


def delete_document(document_id: str, settings: Settings) -> tuple[bool, int]:
    deleted_vectors = delete_document_vectors(document_id, settings)
    registry = DocumentRegistry(settings.registry_path)
    registry_changed = registry.mark_deleted(document_id)
    return registry_changed or deleted_vectors > 0, deleted_vectors


def clear_knowledge_base(settings: Settings) -> tuple[int, int]:
    registry = DocumentRegistry(settings.registry_path)
    active_documents = registry.clear()
    chunks_deleted = count_vectors(settings)
    reset_vectorstore(settings)
    return active_documents, chunks_deleted


def _embedding_model_name(settings: Settings) -> str:
    if settings.embedding_provider == "openai":
        return settings.openai_embedding_model
    return "hash-embeddings"
