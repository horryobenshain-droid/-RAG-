from pathlib import Path
from time import perf_counter
from uuid import uuid4

from langchain_core.documents import Document

from app.core.config import Settings
from app.core.files import calculate_sha256
from app.core.registry import DocumentRecord, DocumentRegistry, utc_now
from app.loaders.local_loader import load_local_file
from app.rag.hybrid_retriever import HybridScore, rerank_with_keywords
from app.rag.llm import AnswerMode, generate_answer
from app.rag.splitter import split_documents
from app.rag.vectorstore import (
    add_documents,
    count_vectors,
    delete_document_vectors,
    reset_vectorstore,
    similarity_search_with_scores,
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


class RetrievedSource:
    def __init__(self, document: Document, score: float | None, hybrid_score: HybridScore) -> None:
        self.document = document
        self.score = score
        self.hybrid_score = hybrid_score


class AnswerResult:
    def __init__(
        self,
        answer: str,
        sources: list[RetrievedSource],
        elapsed_ms: float,
        llm_provider: str,
        llm_model: str,
        embedding_provider: str,
        embedding_model: str,
        answer_mode: AnswerMode,
        answer_basis: str,
    ) -> None:
        self.answer = answer
        self.sources = sources
        self.elapsed_ms = elapsed_ms
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.answer_mode = answer_mode
        self.answer_basis = answer_basis


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


def answer_question(
    question: str,
    top_k: int,
    settings: Settings,
    answer_mode: AnswerMode = "strict",
) -> AnswerResult:
    started_at = perf_counter()
    search_results = similarity_search_with_scores(question, top_k, settings)
    reranked_results = rerank_with_keywords(question, search_results, top_k)
    sources = [
        RetrievedSource(
            document=document,
            score=hybrid_score.final_score,
            hybrid_score=hybrid_score,
        )
        for document, hybrid_score in reranked_results
    ]
    documents = [source.document for source in sources]
    answer = generate_answer(question, documents, settings, answer_mode)
    elapsed_ms = (perf_counter() - started_at) * 1000
    return AnswerResult(
        answer=answer,
        sources=sources,
        elapsed_ms=elapsed_ms,
        llm_provider=settings.llm_provider,
        llm_model=_llm_model_name(settings),
        embedding_provider=settings.embedding_provider,
        embedding_model=_embedding_model_name(settings),
        answer_mode=answer_mode,
        answer_basis=_answer_basis(answer_mode, sources),
    )


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
    if settings.embedding_provider == "local":
        return settings.local_embedding_model
    if settings.embedding_provider == "openai":
        return settings.openai_embedding_model
    return "hash-embeddings"


def _llm_model_name(settings: Settings) -> str:
    if settings.llm_provider == "openai":
        return settings.openai_chat_model
    return "demo-snippet-answer"


def _answer_basis(answer_mode: AnswerMode, sources: list[RetrievedSource]) -> str:
    if answer_mode == "strict":
        return "knowledge_base"
    if sources:
        return "mixed"
    return "model_prior"
