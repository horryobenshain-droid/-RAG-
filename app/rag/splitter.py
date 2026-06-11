from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings


def split_documents(documents: list[Document], settings: Settings) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=[
            "\nclass ",
            "\ndef ",
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
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = index
    return chunks
