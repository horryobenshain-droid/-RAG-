import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

SUPPORTED_SUFFIXES = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".markdown",
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


def sanitize_filename(filename: str) -> str:
    clean_name = Path(filename).name.strip() or "uploaded-file"
    return re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", clean_name)


def assert_supported_file(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        msg = f"Unsupported file type '{path.suffix}'. Supported suffixes: {supported}"
        raise ValueError(msg)


def save_upload_file(upload_file: UploadFile, upload_dir: Path) -> Path:
    original_name = sanitize_filename(upload_file.filename or "uploaded-file")
    target_path = upload_dir / f"{uuid4().hex}_{original_name}"
    assert_supported_file(target_path)

    with target_path.open("wb") as target:
        shutil.copyfileobj(upload_file.file, target)

    return target_path
