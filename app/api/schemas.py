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
