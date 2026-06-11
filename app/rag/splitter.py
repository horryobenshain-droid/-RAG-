from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings
from app.rag.code_splitter import split_code_document


def split_documents(documents: list[Document], settings: Settings) -> list[Document]:
    chunks: list[Document] = []
    text_documents = []

    for document in documents:
        if document.metadata.get("document_type") == "code":
            chunks.extend(split_code_document(document, settings.chunk_size))
        else:
            text_documents.append(document)

    if text_documents:
        chunks.extend(_split_text_documents(text_documents, settings))

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = index
    return chunks


def _split_text_documents(documents: list[Document], settings: Settings) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=[
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            "。",
            "，",
            " ",
            "",
        ],
    )
    return splitter.split_documents(documents)
