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


class Source(BaseModel):
    source_id: int
    file_name: str
    page: int | None = None
    chunk_id: int | str | None = None
    preview: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


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
