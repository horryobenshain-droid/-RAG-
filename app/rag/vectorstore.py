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
