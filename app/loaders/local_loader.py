from pathlib import Path

import docx2txt
from langchain_core.documents import Document
from pypdf import PdfReader

from app.core.files import assert_supported_file

TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
CODE_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".sql",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
}


def load_local_file(path: Path) -> list[Document]:
    assert_supported_file(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        docs = _load_pdf_documents(path, suffix)
    elif suffix == ".docx":
        docs = _load_docx_document(path, suffix)
    elif suffix in TEXT_SUFFIXES | CODE_SUFFIXES:
        docs = [_load_text_document(path, suffix)]
    else:
        msg = f"No loader configured for file type: {suffix}"
        raise ValueError(msg)

    for doc in docs:
        doc.metadata.update(_base_metadata(path, suffix))

    return [doc for doc in docs if doc.page_content.strip()]


def _load_pdf_documents(path: Path, suffix: str) -> list[Document]:
    reader = PdfReader(str(path))
    documents = []
    for page_number, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        metadata = _base_metadata(path, suffix)
        metadata["page"] = page_number
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


def _load_docx_document(path: Path, suffix: str) -> list[Document]:
    content = docx2txt.process(str(path)) or ""
    return [Document(page_content=content, metadata=_base_metadata(path, suffix))]


def _load_text_document(path: Path, suffix: str) -> Document:
    content = path.read_text(encoding="utf-8", errors="ignore")
    metadata = _base_metadata(path, suffix)
    metadata["document_type"] = "code" if suffix in CODE_SUFFIXES else "text"
    return Document(page_content=content, metadata=metadata)


def _base_metadata(path: Path, suffix: str) -> dict[str, str]:
    return {
        "source": str(path),
        "file_name": path.name,
        "extension": suffix,
        "document_type": "document",
    }
