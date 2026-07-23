import warnings
from typing import Literal

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.core.config import Settings
from app.rag.embeddings import get_embeddings

RetrievalStrategy = Literal["similarity", "mmr"]


def get_vectorstore(settings: Settings, embeddings: Embeddings | None = None) -> Chroma:
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings or get_embeddings(settings),
        persist_directory=str(settings.chroma_dir),
    )


def add_documents(documents: list[Document], settings: Settings) -> int:
    if not documents:
        return 0

    vectorstore = get_vectorstore(settings)
    vectorstore.add_documents(documents)
    return len(documents)


def similarity_search(question: str, top_k: int, settings: Settings) -> list[Document]:
    vectorstore = get_vectorstore(settings)
    return vectorstore.similarity_search(question, k=top_k)


def similarity_search_with_scores(
    question: str,
    top_k: int,
    settings: Settings,
) -> list[tuple[Document, float | None]]:
    return retrieve_with_scores(question, top_k, settings, strategy="similarity")


def retrieve_with_scores(
    question: str,
    top_k: int,
    settings: Settings,
    strategy: RetrievalStrategy | None = None,
) -> list[tuple[Document, float | None]]:
    active_strategy = strategy or settings.retrieval_strategy
    fetch_k = max(top_k, settings.retrieval_fetch_k)
    embeddings = get_embeddings(settings)
    vectorstore = get_vectorstore(settings, embeddings)
    query_embedding = embeddings.embed_query(question)
    similarity_results = _similarity_by_vector(
        vectorstore,
        query_embedding,
        question,
        fetch_k,
    )
    if active_strategy == "similarity":
        return similarity_results

    selected_k = min(fetch_k, max(top_k, settings.reranker_candidate_k))
    try:
        documents = vectorstore.max_marginal_relevance_search_by_vector(
            query_embedding,
            k=selected_k,
            fetch_k=fetch_k,
            lambda_mult=settings.mmr_lambda_mult,
        )
    except NotImplementedError:
        documents = vectorstore.max_marginal_relevance_search(
            question,
            k=selected_k,
            fetch_k=fetch_k,
            lambda_mult=settings.mmr_lambda_mult,
        )

    scores = {_document_key(document): score for document, score in similarity_results}
    return [(document, scores.get(_document_key(document))) for document in documents]


def _similarity_by_vector(
    vectorstore: Chroma,
    query_embedding: list[float],
    question: str,
    fetch_k: int,
) -> list[tuple[Document, float | None]]:
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Relevance scores must be between 0 and 1")
            results = vectorstore.similarity_search_by_vector_with_relevance_scores(
                query_embedding,
                k=fetch_k,
            )
        return [(document, _normalize_score(score)) for document, score in results]
    except NotImplementedError:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Relevance scores must be between 0 and 1",
                )
                results = vectorstore.similarity_search_with_relevance_scores(
                    question,
                    k=fetch_k,
                )
            return [(document, _normalize_score(score)) for document, score in results]
        except NotImplementedError:
            documents = vectorstore.similarity_search_by_vector(query_embedding, k=fetch_k)
            return [(document, None) for document in documents]


def delete_document_vectors(document_id: str, settings: Settings) -> int:
    vectorstore = get_vectorstore(settings)
    results = vectorstore.get(where={"document_id": document_id}, include=[])
    ids = results.get("ids", [])
    if not ids:
        return 0
    vectorstore.delete(ids=ids)
    return len(ids)


def reset_vectorstore(settings: Settings) -> None:
    vectorstore = get_vectorstore(settings)
    vectorstore.reset_collection()


def count_vectors(settings: Settings) -> int:
    vectorstore = get_vectorstore(settings)
    results = vectorstore.get(include=[])
    return len(results.get("ids", []))


def _normalize_score(score: float | None) -> float | None:
    if score is None:
        return None
    return max(0.0, min(1.0, float(score)))


def _document_key(document: Document) -> tuple[object, ...]:
    if document.id:
        return ("id", document.id)
    metadata = tuple(sorted((str(key), str(value)) for key, value in document.metadata.items()))
    return ("content", document.page_content, metadata)
