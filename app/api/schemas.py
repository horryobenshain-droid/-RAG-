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
    top_k: int | None = Field(default=None, ge=1, le=10)
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
    repository_id: str | None = None
    repository_name: str | None = None
    relative_path: str | None = None
    module_path: str | None = None
    preview: str
    content: str


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
    repository_id: str | None = None
    repository_name: str | None = None
    relative_path: str | None = None
    module_path: str | None = None


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


class RepositoryResponse(BaseModel):
    repository_id: str
    name: str
    source_archive_name: str
    files_indexed: int
    chunks_indexed: int
    ignored_files: int
    created_at: str
    updated_at: str


class RepositoryUploadResponse(RepositoryResponse):
    message: str


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryResponse]
    total: int


class DeleteRepositoryResponse(BaseModel):
    repository_id: str
    deleted: bool
    documents_deleted: int
    chunks_deleted: int
    message: str


class ReindexRepositoryResponse(RepositoryResponse):
    message: str


class RuntimeConfigUpdate(BaseModel):
    llm_provider: Literal["demo", "openai", "ollama"] | None = None
    embedding_provider: Literal["demo", "openai", "local"] | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_chat_model: str | None = Field(default=None, min_length=1, max_length=200)
    openai_embedding_model: str | None = Field(default=None, min_length=1, max_length=200)
    ollama_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    ollama_chat_model: str | None = Field(default=None, min_length=1, max_length=200)
    ollama_temperature: float | None = Field(default=None, ge=0, le=2)
    ollama_num_ctx: int | None = Field(default=None, ge=512, le=131072)
    ollama_num_predict: int | None = Field(default=None, ge=1, le=32768)
    ollama_top_p: float | None = Field(default=None, gt=0, le=1)
    ollama_repeat_penalty: float | None = Field(default=None, ge=1, le=2)
    ollama_timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    local_embedding_model: str | None = Field(default=None, min_length=1, max_length=300)
    chunk_size: int | None = Field(default=None, ge=100, le=10000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=5000)
    default_top_k: int | None = Field(default=None, ge=1, le=10)
    retrieval_strategy: Literal["similarity", "mmr"] | None = None
    retrieval_fetch_k: int | None = Field(default=None, ge=1, le=200)
    mmr_lambda_mult: float | None = Field(default=None, ge=0, le=1)
    hybrid_vector_weight: float | None = Field(default=None, ge=0, le=1)
    hybrid_keyword_weight: float | None = Field(default=None, ge=0, le=1)
    hybrid_filename_weight: float | None = Field(default=None, ge=0, le=1)
    hybrid_symbol_weight: float | None = Field(default=None, ge=0, le=1)
    reranker_provider: Literal["none", "cross_encoder"] | None = None
    reranker_model: str | None = Field(default=None, min_length=1, max_length=300)
    reranker_device: str | None = Field(default=None, min_length=1, max_length=50)
    reranker_candidate_k: int | None = Field(default=None, ge=1, le=100)
    reranker_batch_size: int | None = Field(default=None, ge=1, le=256)
    reranker_weight: float | None = Field(default=None, ge=0, le=1)


class RuntimeConfigResponse(BaseModel):
    llm_provider: str
    active_llm_model: str
    embedding_provider: str
    active_embedding_model: str
    openai_api_key_configured: bool
    openai_base_url: str | None
    openai_chat_model: str
    openai_embedding_model: str
    ollama_base_url: str
    ollama_chat_model: str
    ollama_temperature: float
    ollama_num_ctx: int
    ollama_num_predict: int
    ollama_top_p: float
    ollama_repeat_penalty: float
    ollama_timeout_seconds: float
    local_embedding_model: str
    chunk_size: int
    chunk_overlap: int
    default_top_k: int
    retrieval_strategy: str
    retrieval_fetch_k: int
    mmr_lambda_mult: float
    hybrid_vector_weight: float
    hybrid_keyword_weight: float
    hybrid_filename_weight: float
    hybrid_symbol_weight: float
    reranker_provider: str
    reranker_model: str
    reranker_device: str
    reranker_candidate_k: int
    reranker_batch_size: int
    reranker_weight: float
    runtime_configured: bool
    requires_reindex: bool


class ProviderStatus(BaseModel):
    connected: bool
    message: str
    models: list[str] = Field(default_factory=list)


class KnowledgeBaseStats(BaseModel):
    documents: int
    repositories: int
    chunks: int


class SystemStatusResponse(BaseModel):
    version: str
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    ollama: ProviderStatus
    openai_configured: bool
    knowledge_base: KnowledgeBaseStats
