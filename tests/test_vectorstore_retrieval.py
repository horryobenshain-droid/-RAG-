from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.vectorstore import retrieve_with_scores


class FakeEmbeddings:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.25, 0.75]


class FakeVectorstore:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.similarity_embedding: list[float] | None = None
        self.mmr_embedding: list[float] | None = None

    def similarity_search_by_vector_with_relevance_scores(
        self,
        embedding: list[float],
        k: int,
    ) -> list[tuple[Document, float]]:
        self.similarity_embedding = embedding
        assert k == 3
        return list(zip(self.documents, [0.9, 0.7, 0.5], strict=True))

    def max_marginal_relevance_search_by_vector(
        self,
        embedding: list[float],
        **kwargs: Any,
    ) -> list[Document]:
        self.mmr_embedding = embedding
        assert kwargs == {"k": 2, "fetch_k": 3, "lambda_mult": 0.35}
        return [self.documents[2], self.documents[0]]


def test_mmr_reuses_query_embedding_and_preserves_vector_scores(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    documents = [Document(id=f"doc-{index}", page_content=f"chunk {index}") for index in range(3)]
    embeddings = FakeEmbeddings()
    vectorstore = FakeVectorstore(documents)
    monkeypatch.setattr("app.rag.vectorstore.get_embeddings", lambda settings: embeddings)
    monkeypatch.setattr(
        "app.rag.vectorstore.get_vectorstore",
        lambda settings, active_embeddings=None: vectorstore,
    )
    settings = Settings(
        project_root=tmp_path,
        default_top_k=2,
        retrieval_fetch_k=3,
        reranker_candidate_k=2,
        mmr_lambda_mult=0.35,
    )

    results = retrieve_with_scores("diverse query", 2, settings, strategy="mmr")

    assert embeddings.queries == ["diverse query"]
    assert vectorstore.similarity_embedding is vectorstore.mmr_embedding
    assert [document.id for document, _ in results] == ["doc-2", "doc-0"]
    assert [score for _, score in results] == [0.5, 0.9]
