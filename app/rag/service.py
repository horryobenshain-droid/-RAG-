from pathlib import Path

from langchain_core.documents import Document

from app.core.config import Settings
from app.loaders.local_loader import load_local_file
from app.rag.llm import generate_answer
from app.rag.splitter import split_documents
from app.rag.vectorstore import add_documents, similarity_search


def ingest_file(path: Path, settings: Settings) -> int:
    documents = load_local_file(path)
    chunks = split_documents(documents, settings)
    return add_documents(chunks, settings)


def answer_question(question: str, top_k: int, settings: Settings) -> tuple[str, list[Document]]:
    documents = similarity_search(question, top_k, settings)
    answer = generate_answer(question, documents, settings)
    return answer, documents
