import hashlib
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


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_upload_file(upload_file: UploadFile, upload_dir: Path) -> Path:
    original_name = sanitize_filename(upload_file.filename or "uploaded-file")
    target_path = upload_dir / f"{uuid4().hex}_{original_name}"
    assert_supported_file(target_path)

    with target_path.open("wb") as target:
        shutil.copyfileobj(upload_file.file, target)

    return target_path


def save_repository_archive(
    upload_file: UploadFile,
    upload_dir: Path,
    max_bytes: int,
) -> Path:
    original_name = sanitize_filename(upload_file.filename or "repository.zip")
    if Path(original_name).suffix.lower() != ".zip":
        raise ValueError("代码库必须使用 ZIP 格式上传。")

    target_path = upload_dir / f"{uuid4().hex}_{original_name}"
    written = 0
    try:
        with target_path.open("wb") as target:
            while block := upload_file.file.read(1024 * 1024):
                written += len(block)
                if written > max_bytes:
                    raise ValueError(f"ZIP 文件大小不能超过 {max_bytes} bytes。")
                target.write(block)
    except Exception:
        if target_path.exists():
            target_path.unlink()
        raise
    return target_path
