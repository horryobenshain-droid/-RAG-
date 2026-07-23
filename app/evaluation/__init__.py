"""RAG evaluation and model comparison utilities."""

from app.evaluation.models import EvaluationDataset, EvaluationRun, ModelProfile
from app.evaluation.runner import evaluate_dataset

__all__ = ["EvaluationDataset", "EvaluationRun", "ModelProfile", "evaluate_dataset"]
