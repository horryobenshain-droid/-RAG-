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
from app.rag.reranker import rerank_with_cross_encoder
from app.rag.splitter import split_documents
from app.rag.vectorstore import (
    RetrievalStrategy,
    add_documents,
    count_vectors,
    delete_document_vectors,
    reset_vectorstore,
    retrieve_with_scores,
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
        retrieval_strategy: RetrievalStrategy = "similarity",
        candidate_count: int = 0,
        retrieval_ms: float = 0.0,
        reranking_ms: float = 0.0,
        generation_ms: float = 0.0,
        reranker_provider: str = "none",
        reranker_model: str | None = None,
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
        self.retrieval_strategy = retrieval_strategy
        self.candidate_count = candidate_count
        self.retrieval_ms = retrieval_ms
        self.reranking_ms = reranking_ms
        self.generation_ms = generation_ms
        self.reranker_provider = reranker_provider
        self.reranker_model = reranker_model


def ingest_file(
    path: Path,
    settings: Settings,
    original_file_name: str | None = None,
) -> IngestResult:
    _ensure_embedding_config_matches_active_documents(settings)
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
    retrieval_strategy: RetrievalStrategy | None = None,
) -> AnswerResult:
    started_at = perf_counter()
    _ensure_embedding_config_matches_active_documents(settings)
    active_strategy = retrieval_strategy or settings.retrieval_strategy

    retrieval_started = perf_counter()
    search_results = retrieve_with_scores(
        question,
        top_k,
        settings,
        strategy=active_strategy,
    )
    retrieval_ms = (perf_counter() - retrieval_started) * 1000

    reranking_started = perf_counter()
    hybrid_limit = (
        max(top_k, settings.reranker_candidate_k)
        if settings.reranker_provider == "cross_encoder"
        else top_k
    )
    hybrid_results = rerank_with_keywords(
        question,
        search_results,
        hybrid_limit,
        vector_weight=settings.hybrid_vector_weight,
        keyword_weight=settings.hybrid_keyword_weight,
        filename_weight=settings.hybrid_filename_weight,
        symbol_weight=settings.hybrid_symbol_weight,
        retrieval_strategy=active_strategy,
    )
    reranked_results = rerank_with_cross_encoder(
        question,
        hybrid_results,
        top_k,
        settings,
    )
    reranking_ms = (perf_counter() - reranking_started) * 1000
    sources = [
        RetrievedSource(
            document=document,
            score=hybrid_score.final_score,
            hybrid_score=hybrid_score,
        )
        for document, hybrid_score in reranked_results
    ]
    documents = [source.document for source in sources]

    generation_started = perf_counter()
    answer = generate_answer(question, documents, settings, answer_mode)
    generation_ms = (perf_counter() - generation_started) * 1000
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
        retrieval_strategy=active_strategy,
        candidate_count=len(search_results),
        retrieval_ms=retrieval_ms,
        reranking_ms=reranking_ms,
        generation_ms=generation_ms,
        reranker_provider=settings.reranker_provider,
        reranker_model=(
            settings.reranker_model if settings.reranker_provider == "cross_encoder" else None
        ),
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
    if settings.llm_provider == "ollama":
        return settings.ollama_chat_model
    return "demo-snippet-answer"


def _ensure_embedding_config_matches_active_documents(settings: Settings) -> None:
    registry = DocumentRegistry(settings.registry_path)
    active_documents = registry.list_documents(include_deleted=False)
    if not active_documents:
        return

    current_provider = settings.embedding_provider
    current_model = _embedding_model_name(settings)
    mismatched_documents = [
        document
        for document in active_documents
        if document.get("embedding_provider") != current_provider
        or document.get("embedding_model") != current_model
    ]
    if not mismatched_documents:
        return

    examples = "、".join(
        str(document.get("original_file_name", "未知文档")) for document in mismatched_documents[:3]
    )
    if len(mismatched_documents) > 3:
        examples += f" 等 {len(mismatched_documents)} 个文档"

    first = mismatched_documents[0]
    indexed_provider = first.get("embedding_provider", "unknown")
    indexed_model = first.get("embedding_model", "unknown")
    msg = (
        "当前知识库索引的 Embedding 配置与当前系统配置不一致，检索结果不可靠。\n"
        f"当前配置：{current_provider}/{current_model}。\n"
        f"知识库索引：{indexed_provider}/{indexed_model}。\n"
        f"不匹配文档：{examples}。\n"
        "请先清空知识库，并在当前配置下重新上传文档。"
    )
    raise ValueError(msg)


def _answer_basis(answer_mode: AnswerMode, sources: list[RetrievedSource]) -> str:
    if answer_mode == "strict":
        return "knowledge_base"
    if sources:
        return "mixed"
    return "model_prior"
