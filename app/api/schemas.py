from typing import Literal

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    document_id: str
    original_file_name: str
    file_name: str
    saved_path: str
    file_hash: str
    chunks_indexed: int
    message: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    answer_mode: str = Field(default="strict", pattern="^(strict|augmented)$")
    retrieval_strategy: Literal["similarity", "mmr"] | None = None


class Source(BaseModel):
    source_id: int
    file_name: str
    page: int | None = None
    chunk_id: int | str | None = None
    document_id: str | None = None
    score: float | None = None
    vector_score: float | None = None
    keyword_score: float | None = None
    filename_score: float | None = None
    symbol_score: float | None = None
    reranker_score: float | None = None
    retrieval_rank: int | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    language: str | None = None
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    preview: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    elapsed_ms: float
    retrieved_chunks: int
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    answer_mode: str
    answer_basis: str
    retrieval_strategy: str
    candidate_count: int
    retrieval_ms: float
    reranking_ms: float
    generation_ms: float
    reranker_provider: str
    reranker_model: str | None = None


class DocumentRecordResponse(BaseModel):
    document_id: str
    original_file_name: str
    stored_file_name: str
    extension: str
    file_hash: str
    chunks_indexed: int
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    status: str
    created_at: str
    deleted_at: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecordResponse]
    total: int


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: bool
    chunks_deleted: int
    message: str


class ClearKnowledgeBaseResponse(BaseModel):
    documents_deleted: int
    chunks_deleted: int
    message: str
