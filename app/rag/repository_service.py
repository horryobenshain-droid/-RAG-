import shutil
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.core.registry import (
    DocumentRecord,
    DocumentRegistry,
    RepositoryRecord,
    RepositoryRegistry,
    utc_now,
)
from app.core.repositories import ExtractedRepository, scan_repository
from app.rag.service import prepare_ingest_file
from app.rag.vectorstore import add_documents, delete_document_vectors


@dataclass(frozen=True)
class RepositoryResult:
    repository_id: str
    name: str
    source_archive_name: str
    files_indexed: int
    chunks_indexed: int
    ignored_files: int
    created_at: str
    updated_at: str


def ingest_repository(
    extracted: ExtractedRepository,
    settings: Settings,
) -> RepositoryResult:
    records, chunks_indexed = _index_files(
        files=extracted.files,
        repository_id=extracted.repository_id,
        repository_name=extracted.name,
        root_path=extracted.root_path,
        settings=settings,
    )
    now = utc_now()
    repository_record = RepositoryRecord(
        repository_id=extracted.repository_id,
        name=extracted.name,
        source_archive_name=extracted.source_archive_name,
        root_path=str(extracted.root_path),
        archive_path=str(extracted.archive_path),
        files_indexed=len(records),
        chunks_indexed=chunks_indexed,
        ignored_files=extracted.ignored_files,
        status="active",
        created_at=now,
        updated_at=now,
    )
    try:
        DocumentRegistry(settings.registry_path).add_many(records)
        RepositoryRegistry(settings.repository_registry_path).add(repository_record)
    except Exception:
        _delete_vectors(records, settings)
        DocumentRegistry(settings.registry_path).mark_repository_deleted(
            extracted.repository_id
        )
        raise
    return _result_from_record(repository_record)


def list_repositories(settings: Settings) -> list[dict[str, object]]:
    return RepositoryRegistry(settings.repository_registry_path).list_repositories()


def delete_repository(repository_id: str, settings: Settings) -> tuple[bool, int, int]:
    repository_registry = RepositoryRegistry(settings.repository_registry_path)
    repository = repository_registry.get(repository_id)
    if repository is None:
        return False, 0, 0

    document_registry = DocumentRegistry(settings.registry_path)
    records = document_registry.list_by_repository(repository_id)
    chunks_deleted = _delete_vectors(records, settings)
    documents_deleted = document_registry.mark_repository_deleted(repository_id)
    repository_registry.mark_deleted(repository_id)
    _remove_repository_files(repository, settings)
    return True, documents_deleted, chunks_deleted


def reindex_repository(repository_id: str, settings: Settings) -> RepositoryResult | None:
    repository_registry = RepositoryRegistry(settings.repository_registry_path)
    repository = repository_registry.get(repository_id)
    if repository is None:
        return None

    root_path = _validated_repository_root(repository, settings)
    if not root_path.is_dir():
        raise ValueError("代码库源文件不存在，无法重建索引。")
    files, newly_ignored = scan_repository(
        root_path,
        max_files=settings.repository_max_files,
        max_file_bytes=settings.repository_max_file_bytes,
        max_total_bytes=settings.repository_max_total_bytes,
    )
    if not files:
        raise ValueError("代码库中没有可重建索引的文件。")

    new_records, chunks_indexed = _index_files(
        files=files,
        repository_id=repository_id,
        repository_name=str(repository["name"]),
        root_path=root_path,
        settings=settings,
    )
    document_registry = DocumentRegistry(settings.registry_path)
    old_records = document_registry.list_by_repository(repository_id)
    try:
        _delete_vectors(old_records, settings)
        document_registry.mark_repository_deleted(repository_id)
        document_registry.add_many(new_records)
        ignored_files = max(int(repository.get("ignored_files", 0)), newly_ignored)
        repository_registry.update_index(
            repository_id,
            files_indexed=len(new_records),
            chunks_indexed=chunks_indexed,
            ignored_files=ignored_files,
        )
    except Exception:
        _delete_vectors(new_records, settings)
        raise

    updated = repository_registry.get(repository_id)
    if updated is None:
        raise ValueError("代码库记录在重建索引后丢失。")
    return _result_from_mapping(updated)


def clear_repository_files(settings: Settings) -> None:
    registry = RepositoryRegistry(settings.repository_registry_path)
    for repository in registry.list_repositories(include_deleted=True):
        try:
            _remove_repository_files(repository, settings)
        except ValueError:
            continue


def discard_repository_upload(
    extracted: ExtractedRepository | None,
    archive_path: Path | None,
) -> None:
    if extracted is not None and extracted.root_path.is_dir():
        shutil.rmtree(extracted.root_path)
    if archive_path is not None and archive_path.is_file():
        archive_path.unlink()


def _index_files(
    files: list[Path],
    repository_id: str,
    repository_name: str,
    root_path: Path,
    settings: Settings,
) -> tuple[list[DocumentRecord], int]:
    records: list[DocumentRecord] = []
    try:
        for path in files:
            prepared = prepare_ingest_file(
                path,
                settings,
                repository_id=repository_id,
                repository_name=repository_name,
                repository_root=root_path,
            )
            add_documents(prepared.chunks, settings)
            records.append(prepared.record)
    except Exception:
        _delete_vectors(records, settings)
        raise
    return records, sum(record.chunks_indexed for record in records)


def _delete_vectors(
    records: list[dict[str, object]] | list[DocumentRecord],
    settings: Settings,
) -> int:
    chunks_deleted = 0
    for record in records:
        document_id = (
            record.document_id if isinstance(record, DocumentRecord) else str(record["document_id"])
        )
        chunks_deleted += delete_document_vectors(document_id, settings)
    return chunks_deleted


def _validated_repository_root(repository: dict[str, object], settings: Settings) -> Path:
    root_path = Path(str(repository["root_path"])).resolve()
    repository_dir = settings.repository_dir.resolve()
    if root_path.parent != repository_dir:
        raise ValueError("代码库存储路径无效。")
    if root_path.name != str(repository["repository_id"]):
        raise ValueError("代码库存储路径与代码库 ID 不匹配。")
    return root_path


def _remove_repository_files(repository: dict[str, object], settings: Settings) -> None:
    root_path = _validated_repository_root(repository, settings)
    if root_path.is_dir():
        shutil.rmtree(root_path)

    archive_path = Path(str(repository.get("archive_path", ""))).resolve()
    if archive_path.parent == settings.upload_dir.resolve() and archive_path.is_file():
        archive_path.unlink()


def _result_from_record(record: RepositoryRecord) -> RepositoryResult:
    return RepositoryResult(
        repository_id=record.repository_id,
        name=record.name,
        source_archive_name=record.source_archive_name,
        files_indexed=record.files_indexed,
        chunks_indexed=record.chunks_indexed,
        ignored_files=record.ignored_files,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _result_from_mapping(record: dict[str, object]) -> RepositoryResult:
    return RepositoryResult(
        repository_id=str(record["repository_id"]),
        name=str(record["name"]),
        source_archive_name=str(record["source_archive_name"]),
        files_indexed=int(record["files_indexed"]),
        chunks_indexed=int(record["chunks_indexed"]),
        ignored_files=int(record["ignored_files"]),
        created_at=str(record["created_at"]),
        updated_at=str(record["updated_at"]),
    )
