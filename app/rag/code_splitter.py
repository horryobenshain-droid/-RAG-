import re

from langchain_core.documents import Document

CODE_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
}

FUNCTION_PATTERNS = [
    re.compile(
        r"^\s*(?:template\s*<[^>]+>\s*)?"
        r"(?:(?:inline|static|constexpr|const|virtual|friend|extern)\s+)*"
        r"(?:[\w:<>,~*&]+\s+)+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?\{?"
    ),
    re.compile(r"^\s*(?:def|async\s+def)\s+(?P<name>[A-Za-z_]\w*)\s*\("),
    re.compile(r"^\s*class\s+(?P<name>[A-Za-z_]\w*)\b"),
    re.compile(r"^\s*func\s+(?P<name>[A-Za-z_]\w*)\s*\("),
    re.compile(r"^\s*function\s+(?P<name>[A-Za-z_]\w*)\s*\("),
]


def split_code_document(document: Document, chunk_size: int) -> list[Document]:
    lines = document.page_content.splitlines()
    if not lines:
        return []

    starts = _find_symbol_starts(lines)
    if not starts:
        return _split_by_line_window(document, lines, chunk_size)

    chunks: list[Document] = []
    for index, (start_index, symbol_name) in enumerate(starts):
        end_index = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines) - 1
        content_lines = lines[start_index : end_index + 1]
        content = "\n".join(content_lines).strip()
        if not content:
            continue
        chunks.extend(
            _split_long_code_block(
                document=document,
                content_lines=content_lines,
                start_line=start_index + 1,
                symbol_name=symbol_name,
                chunk_size=chunk_size,
            )
        )
    return chunks


def _find_symbol_starts(lines: list[str]) -> list[tuple[int, str]]:
    starts = []
    for index, line in enumerate(lines):
        for pattern in FUNCTION_PATTERNS:
            match = pattern.match(line)
            if match:
                starts.append((index, match.group("name")))
                break
    return starts


def _split_long_code_block(
    document: Document,
    content_lines: list[str],
    start_line: int,
    symbol_name: str,
    chunk_size: int,
) -> list[Document]:
    max_lines = max(20, chunk_size // 60)
    chunks = []
    for offset in range(0, len(content_lines), max_lines):
        window = content_lines[offset : offset + max_lines]
        metadata = _code_metadata(
            document,
            start_line=start_line + offset,
            end_line=start_line + offset + len(window) - 1,
            symbol_name=symbol_name,
        )
        chunks.append(Document(page_content="\n".join(window), metadata=metadata))
    return chunks


def _split_by_line_window(document: Document, lines: list[str], chunk_size: int) -> list[Document]:
    max_lines = max(20, chunk_size // 60)
    chunks = []
    for offset in range(0, len(lines), max_lines):
        window = lines[offset : offset + max_lines]
        content = "\n".join(window).strip()
        if not content:
            continue
        metadata = _code_metadata(
            document,
            start_line=offset + 1,
            end_line=offset + len(window),
            symbol_name=None,
        )
        chunks.append(Document(page_content=content, metadata=metadata))
    return chunks


def _code_metadata(
    document: Document,
    start_line: int,
    end_line: int,
    symbol_name: str | None,
) -> dict[str, object]:
    metadata = dict(document.metadata)
    extension = str(metadata.get("extension", "")).lower()
    metadata.update(
        {
            "document_type": "code",
            "language": CODE_LANGUAGE_BY_SUFFIX.get(extension, extension.lstrip(".") or "code"),
            "start_line": start_line,
            "end_line": end_line,
        }
    )
    if symbol_name:
        metadata["symbol_name"] = symbol_name
    return metadata
