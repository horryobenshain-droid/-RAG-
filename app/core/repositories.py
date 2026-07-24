import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.core.files import SUPPORTED_SUFFIXES

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".idea",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "env",
    "node_modules",
    "target",
    "venv",
}
MODULE_SUFFIXES = {
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}


@dataclass(frozen=True)
class ExtractedRepository:
    repository_id: str
    name: str
    source_archive_name: str
    archive_path: Path
    root_path: Path
    files: list[Path]
    ignored_files: int


def extract_repository_archive(
    archive_path: Path,
    repository_dir: Path,
    repository_id: str,
    source_archive_name: str,
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> ExtractedRepository:
    if not zipfile.is_zipfile(archive_path):
        raise ValueError("上传的文件不是有效的 ZIP 压缩包。")

    root_path = repository_dir / repository_id
    root_path.mkdir(parents=True, exist_ok=False)
    extracted_files: list[Path] = []
    extracted_paths: set[str] = set()
    ignored_files = 0
    total_bytes = 0

    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            prefix = _common_root_prefix(members)
            for member in members:
                relative_path = _safe_relative_path(member.filename, prefix)
                if relative_path is None:
                    ignored_files += 1
                    continue
                if _is_symlink(member):
                    ignored_files += 1
                    continue
                if _is_ignored_path(relative_path):
                    ignored_files += 1
                    continue
                if relative_path.suffix.lower() not in SUPPORTED_SUFFIXES:
                    ignored_files += 1
                    continue
                normalized_path = relative_path.as_posix().casefold()
                if normalized_path in extracted_paths:
                    raise ValueError(f"ZIP 包含重复文件路径：{relative_path.as_posix()}")
                if member.flag_bits & 0x1:
                    raise ValueError(f"代码库包含加密文件：{relative_path.as_posix()}")
                if member.file_size > max_file_bytes:
                    raise ValueError(
                        f"文件超过单文件大小限制：{relative_path.as_posix()} "
                        f"({member.file_size} bytes)。"
                    )
                if len(extracted_files) >= max_files:
                    raise ValueError(f"代码库可入库文件数不能超过 {max_files}。")
                total_bytes += member.file_size
                if total_bytes > max_total_bytes:
                    raise ValueError(
                        f"代码库可入库文件总大小不能超过 {max_total_bytes} bytes。"
                    )

                with archive.open(member) as source:
                    content = source.read(max_file_bytes + 1)
                if len(content) > max_file_bytes:
                    raise ValueError(f"文件超过单文件大小限制：{relative_path.as_posix()}。")
                if _looks_binary(content):
                    ignored_files += 1
                    continue

                target_path = root_path.joinpath(*relative_path.parts)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(content)
                extracted_files.append(target_path)
                extracted_paths.add(normalized_path)
    except Exception:
        _remove_tree(root_path)
        raise

    if not extracted_files:
        _remove_tree(root_path)
        raise ValueError("ZIP 中没有可入库的文本或代码文件。")

    return ExtractedRepository(
        repository_id=repository_id,
        name=_repository_name(source_archive_name),
        source_archive_name=source_archive_name,
        archive_path=archive_path,
        root_path=root_path,
        files=sorted(extracted_files, key=lambda path: path.as_posix().casefold()),
        ignored_files=ignored_files,
    )


def scan_repository(
    root_path: Path,
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> tuple[list[Path], int]:
    files: list[Path] = []
    ignored = 0
    total_bytes = 0
    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root_path)
        if _is_ignored_path(PurePosixPath(relative_path.as_posix())):
            ignored += 1
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            ignored += 1
            continue
        try:
            file_size = path.stat().st_size
            if file_size > max_file_bytes:
                raise ValueError(
                    f"文件超过单文件大小限制：{relative_path.as_posix()} ({file_size} bytes)。"
                )
            if len(files) >= max_files:
                raise ValueError(f"代码库可入库文件数不能超过 {max_files}。")
            total_bytes += file_size
            if total_bytes > max_total_bytes:
                raise ValueError(
                    f"代码库可入库文件总大小不能超过 {max_total_bytes} bytes。"
                )
            with path.open("rb") as file:
                sample = file.read(8192)
        except OSError:
            ignored += 1
            continue
        if _looks_binary(sample):
            ignored += 1
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.as_posix().casefold()), ignored


def repository_relative_path(path: Path, root_path: Path) -> str:
    return path.relative_to(root_path).as_posix()


def module_path_for(relative_path: str) -> str | None:
    path = PurePosixPath(relative_path)
    if path.suffix.lower() not in MODULE_SUFFIXES:
        return None
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] in {"__init__", "index"}:
        parts.pop()
    return ".".join(parts) or None


def _safe_relative_path(filename: str, prefix: str | None) -> PurePosixPath | None:
    normalized = filename.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"ZIP 包含不安全路径：{filename}")
    if re.match(r"^[A-Za-z]:", path.parts[0]):
        raise ValueError(f"ZIP 包含不安全路径：{filename}")
    parts = path.parts[1:] if prefix and path.parts[0] == prefix else path.parts
    if not parts:
        return None
    return PurePosixPath(*parts)


def _common_root_prefix(members: list[zipfile.ZipInfo]) -> str | None:
    paths = [PurePosixPath(member.filename.replace("\\", "/")) for member in members]
    if paths and all(len(path.parts) > 1 for path in paths):
        first = paths[0].parts[0]
        if all(path.parts[0] == first for path in paths):
            return first
    return None


def _is_ignored_path(path: PurePosixPath) -> bool:
    return any(part.casefold() in IGNORED_DIRECTORY_NAMES for part in path.parts[:-1])


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    mode = member.external_attr >> 16
    return stat.S_ISLNK(mode)


def _looks_binary(content: bytes) -> bool:
    return b"\x00" in content[:8192]


def _repository_name(source_archive_name: str) -> str:
    stem = Path(source_archive_name).stem.strip() or "repository"
    return re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", stem)


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()
