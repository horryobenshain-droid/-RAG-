import json
from pathlib import Path

from pydantic import ValidationError

from app.evaluation.models import EvaluationDataset, ModelProfile, ModelProfiles


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    payload = _load_json_object(path, "evaluation dataset")
    try:
        return EvaluationDataset.model_validate(payload)
    except ValidationError as exc:
        msg = f"Invalid evaluation dataset '{path}': {exc}"
        raise ValueError(msg) from exc


def load_model_profiles(path: Path) -> list[ModelProfile]:
    payload = _load_json_object(path, "model profiles")
    try:
        return ModelProfiles.model_validate(payload).profiles
    except ValidationError as exc:
        msg = f"Invalid model profiles '{path}': {exc}"
        raise ValueError(msg) from exc


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    if not path.is_file():
        msg = f"The {label} file does not exist: {path}"
        raise ValueError(msg)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"The {label} is not valid JSON: {path}: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"The {label} root must be a JSON object: {path}"
        raise ValueError(msg)
    return payload
