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
