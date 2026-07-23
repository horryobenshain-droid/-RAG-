from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.rag.llm import AnswerMode

ALLOWED_PROFILE_OVERRIDES = {
    "llm_provider",
    "openai_base_url",
    "openai_chat_model",
    "ollama_base_url",
    "ollama_chat_model",
    "ollama_temperature",
    "ollama_num_ctx",
    "ollama_num_predict",
    "ollama_top_p",
    "ollama_repeat_penalty",
    "ollama_timeout_seconds",
    "default_top_k",
    "retrieval_strategy",
    "retrieval_fetch_k",
    "mmr_lambda_mult",
    "hybrid_vector_weight",
    "hybrid_keyword_weight",
    "hybrid_filename_weight",
    "hybrid_symbol_weight",
    "reranker_provider",
    "reranker_model",
    "reranker_device",
    "reranker_candidate_k",
    "reranker_batch_size",
    "reranker_weight",
}


class ExpectedSource(BaseModel):
    file_name: str | None = None
    chunk_id: int | str | None = None
    document_id: str | None = None
    symbol_name: str | None = None

    @model_validator(mode="after")
    def require_selector(self) -> "ExpectedSource":
        if not any(
            value is not None
            for value in (self.file_name, self.chunk_id, self.document_id, self.symbol_name)
        ):
            msg = "Expected sources need at least one selector."
            raise ValueError(msg)
        return self


class EvaluationCase(BaseModel):
    id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    question: str = Field(min_length=1, max_length=2000)
    answer_mode: AnswerMode = "strict"
    top_k: int = Field(default=4, ge=1, le=50)
    expected_sources: list[ExpectedSource] = Field(default_factory=list)
    expected_answer_keywords: list[str] = Field(default_factory=list)
    forbidden_answer_keywords: list[str] = Field(default_factory=list)
    require_citation: bool = False


class EvaluationDataset(BaseModel):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> "EvaluationDataset":
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            msg = "Evaluation case IDs must be unique."
            raise ValueError(msg)
        return self


class ModelProfile(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    overrides: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_overrides(self) -> "ModelProfile":
        unsupported = sorted(set(self.overrides) - ALLOWED_PROFILE_OVERRIDES)
        if unsupported:
            msg = f"Unsupported model profile settings: {', '.join(unsupported)}"
            raise ValueError(msg)
        return self


class ModelProfiles(BaseModel):
    profiles: list[ModelProfile] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_profile_names(self) -> "ModelProfiles":
        names = [profile.name for profile in self.profiles]
        if len(names) != len(set(names)):
            msg = "Model profile names must be unique."
            raise ValueError(msg)
        return self


class EvaluatedSource(BaseModel):
    source_id: int
    file_name: str
    chunk_id: int | str | None = None
    document_id: str | None = None
    symbol_name: str | None = None
    score: float | None = None
    vector_score: float | None = None
    keyword_score: float | None = None
    filename_score: float | None = None
    symbol_score: float | None = None
    reranker_score: float | None = None
    retrieval_rank: int | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    preview: str


class EvaluationCaseResult(BaseModel):
    case_id: str
    question: str
    status: Literal["passed", "failed", "error"]
    answer: str = ""
    sources: list[EvaluatedSource] = Field(default_factory=list)
    elapsed_ms: float | None = None
    recall_at_k: float | None = None
    citation_hit: bool | None = None
    answer_keyword_recall: float | None = None
    missing_answer_keywords: list[str] = Field(default_factory=list)
    matched_forbidden_keywords: list[str] = Field(default_factory=list)
    error: str | None = None
    retrieval_strategy: str | None = None
    candidate_count: int | None = None
    retrieval_ms: float | None = None
    reranking_ms: float | None = None
    generation_ms: float | None = None


class EvaluationSummary(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    pass_rate: float
    recall_at_k: float | None = None
    citation_hit_rate: float | None = None
    answer_keyword_recall: float | None = None
    average_latency_ms: float | None = None
    p95_latency_ms: float | None = None


class ProfileEvaluationResult(BaseModel):
    profile_name: str
    llm_provider: str
    llm_model: str
    started_at: str
    duration_ms: float
    summary: EvaluationSummary
    cases: list[EvaluationCaseResult]
    retrieval_strategy: str = "similarity"
    retrieval_fetch_k: int = 40
    reranker_provider: str = "none"
    reranker_model: str | None = None


class EvaluationRun(BaseModel):
    schema_version: Literal[1] = 1
    dataset_name: str
    dataset_path: str
    generated_at: str
    top_k_override: int | None = None
    profiles: list[ProfileEvaluationResult]
