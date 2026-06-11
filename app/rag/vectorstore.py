import warnings

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import Settings
from app.rag.embeddings import get_embeddings


def get_vectorstore(settings: Settings) -> Chroma:
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(settings),
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
    vectorstore = get_vectorstore(settings)
    fetch_k = max(top_k * 4, top_k)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Relevance scores must be between 0 and 1")
            results = vectorstore.similarity_search_with_relevance_scores(question, k=fetch_k)
        return [(document, _normalize_score(score)) for document, score in results]
    except NotImplementedError:
        documents = vectorstore.similarity_search(question, k=fetch_k)
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
