from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_retrieval_config_rejects_overlapping_chunks(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(project_root=tmp_path, chunk_size=200, chunk_overlap=200)


def test_retrieval_config_requires_normalized_hybrid_weights(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="HYBRID_.*_WEIGHT"):
        Settings(project_root=tmp_path, hybrid_vector_weight=0.5)


def test_retrieval_config_requires_enough_candidates(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="RETRIEVAL_FETCH_K"):
        Settings(project_root=tmp_path, default_top_k=8, retrieval_fetch_k=4)
