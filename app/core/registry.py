import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    original_file_name: str
    stored_file_name: str
    saved_path: str
    extension: str
    file_hash: str
    chunks_indexed: int
    embedding_provider: str
    embedding_model: str
    llm_provider: str
    status: str
    created_at: str
    deleted_at: str | None = None
    repository_id: str | None = None
    repository_name: str | None = None
    relative_path: str | None = None
    module_path: str | None = None


@dataclass(frozen=True)
class RepositoryRecord:
    repository_id: str
    name: str
    source_archive_name: str
    root_path: str
    archive_path: str
    files_indexed: int
    chunks_indexed: int
    ignored_files: int
    status: str
    created_at: str
    updated_at: str
    deleted_at: str | None = None


class DocumentRegistry:
    """Tiny JSON registry for local document lifecycle metadata."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_documents(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        records = self._load()
        if not include_deleted:
            records = [record for record in records if record.get("status") != "deleted"]
        return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def add(self, record: DocumentRecord) -> None:
        records = self._load()
        records.append(asdict(record))
        self._save(records)

    def add_many(self, new_records: list[DocumentRecord]) -> None:
        if not new_records:
            return
        records = self._load()
        records.extend(asdict(record) for record in new_records)
        self._save(records)

    def list_by_repository(
        self,
        repository_id: str,
        include_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        records = [
            record
            for record in self._load()
            if record.get("repository_id") == repository_id
        ]
        if not include_deleted:
            records = [record for record in records if record.get("status") != "deleted"]
        return records

    def mark_deleted(self, document_id: str) -> bool:
        records = self._load()
        changed = False
        deleted_at = utc_now()
        for record in records:
            if record.get("document_id") == document_id and record.get("status") != "deleted":
                record["status"] = "deleted"
                record["deleted_at"] = deleted_at
                changed = True
        if changed:
            self._save(records)
        return changed

    def clear(self) -> int:
        records = self._load()
        active_count = sum(1 for record in records if record.get("status") != "deleted")
        if active_count:
            deleted_at = utc_now()
            for record in records:
                if record.get("status") != "deleted":
                    record["status"] = "deleted"
                    record["deleted_at"] = deleted_at
            self._save(records)
        return active_count

    def mark_repository_deleted(self, repository_id: str) -> int:
        records = self._load()
        deleted_at = utc_now()
        changed = 0
        for record in records:
            if (
                record.get("repository_id") == repository_id
                and record.get("status") != "deleted"
            ):
                record["status"] = "deleted"
                record["deleted_at"] = deleted_at
                changed += 1
        if changed:
            self._save(records)
        return changed

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _save(self, records: list[dict[str, Any]]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        payload = json.dumps(records, ensure_ascii=False, indent=2)
        temp_path.write_text(f"{payload}\n", encoding="utf-8")
        temp_path.replace(self.path)


class RepositoryRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_repositories(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        records = self._load()
        if not include_deleted:
            records = [record for record in records if record.get("status") != "deleted"]
        return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def get(self, repository_id: str, include_deleted: bool = False) -> dict[str, Any] | None:
        for record in self._load():
            if record.get("repository_id") != repository_id:
                continue
            if not include_deleted and record.get("status") == "deleted":
                return None
            return record
        return None

    def add(self, record: RepositoryRecord) -> None:
        records = self._load()
        records.append(asdict(record))
        self._save(records)

    def update_index(
        self,
        repository_id: str,
        files_indexed: int,
        chunks_indexed: int,
        ignored_files: int,
    ) -> bool:
        records = self._load()
        changed = False
        for record in records:
            if record.get("repository_id") == repository_id and record.get("status") != "deleted":
                record.update(
                    {
                        "files_indexed": files_indexed,
                        "chunks_indexed": chunks_indexed,
                        "ignored_files": ignored_files,
                        "updated_at": utc_now(),
                    }
                )
                changed = True
                break
        if changed:
            self._save(records)
        return changed

    def mark_deleted(self, repository_id: str) -> bool:
        records = self._load()
        changed = False
        deleted_at = utc_now()
        for record in records:
            if record.get("repository_id") == repository_id and record.get("status") != "deleted":
                record["status"] = "deleted"
                record["deleted_at"] = deleted_at
                record["updated_at"] = deleted_at
                changed = True
                break
        if changed:
            self._save(records)
        return changed

    def clear(self) -> int:
        records = self._load()
        changed = 0
        deleted_at = utc_now()
        for record in records:
            if record.get("status") != "deleted":
                record["status"] = "deleted"
                record["deleted_at"] = deleted_at
                record["updated_at"] = deleted_at
                changed += 1
        if changed:
            self._save(records)
        return changed

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _save(self, records: list[dict[str, Any]]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        payload = json.dumps(records, ensure_ascii=False, indent=2)
        temp_path.write_text(f"{payload}\n", encoding="utf-8")
        temp_path.replace(self.path)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
