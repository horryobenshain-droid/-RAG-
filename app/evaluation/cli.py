import argparse
import sys
from pathlib import Path

from app.core.config import Settings
from app.core.files import SUPPORTED_SUFFIXES, calculate_sha256
from app.evaluation.io import load_evaluation_dataset, load_model_profiles
from app.evaluation.models import ModelProfile
from app.evaluation.report import write_json_report, write_markdown_report
from app.evaluation.runner import evaluate_dataset
from app.rag.service import ingest_file, list_documents

DEFAULT_DATASET_PATH = Path("eval/eval_cases.json")
DEFAULT_MARKDOWN_REPORT_PATH = Path("eval/eval_report.md")
DEFAULT_JSON_REPORT_PATH = Path("eval/eval_results.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run repeatable RAG retrieval and answer evaluations.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_MARKDOWN_REPORT_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--top-k", type=int, choices=range(1, 51))
    parser.add_argument(
        "--ingest",
        type=Path,
        action="append",
        default=[],
        help="Ingest a supported file or directory before evaluation; repeat as needed.",
    )
    parser.add_argument(
        "--fail-on-failure",
        action="store_true",
        help="Exit with status 1 when any case fails or errors.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = Settings()
        settings.ensure_directories()
        dataset = load_evaluation_dataset(args.dataset)
        profiles = (
            load_model_profiles(args.profiles)
            if args.profiles
            else [ModelProfile(name="current")]
        )
        ingested, skipped = _ingest_inputs(args.ingest, settings)
        run = evaluate_dataset(
            dataset=dataset,
            dataset_path=str(args.dataset),
            profiles=profiles,
            base_settings=settings,
            top_k_override=args.top_k,
        )
        write_markdown_report(run, args.output)
        write_json_report(run, args.json_output)
    except ValueError as exc:
        print(f"Evaluation configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"Evaluation dataset: {run.dataset_name}")
    print(f"Profiles: {len(run.profiles)}")
    print(f"Corpus files ingested: {ingested}; skipped: {skipped}")
    for profile in run.profiles:
        summary = profile.summary
        print(
            f"- {profile.profile_name}: passed {summary.passed_cases}/{summary.total_cases}, "
            f"errors {summary.error_cases}, avg {summary.average_latency_ms or 0:.2f} ms"
        )
    print(f"Markdown report: {args.output}")
    print(f"JSON report: {args.json_output}")

    has_failures = any(
        case.status != "passed"
        for profile in run.profiles
        for case in profile.cases
    )
    return 1 if args.fail_on_failure and has_failures else 0


def _ingest_inputs(inputs: list[Path], settings: Settings) -> tuple[int, int]:
    paths = _expand_ingest_paths(inputs)
    if not paths:
        return 0, 0

    active_hashes = {
        str(document.get("file_hash"))
        for document in list_documents(settings)
        if document.get("file_hash")
    }
    ingested = 0
    skipped = 0
    for path in paths:
        file_hash = calculate_sha256(path)
        if file_hash in active_hashes:
            skipped += 1
            continue
        ingest_file(path, settings, original_file_name=path.name)
        active_hashes.add(file_hash)
        ingested += 1
    return ingested, skipped


def _expand_ingest_paths(inputs: list[Path]) -> list[Path]:
    paths: set[Path] = set()
    for input_path in inputs:
        if input_path.is_file():
            if input_path.suffix.lower() not in SUPPORTED_SUFFIXES:
                msg = f"Unsupported evaluation corpus file: {input_path}"
                raise ValueError(msg)
            paths.add(input_path.resolve())
            continue
        if input_path.is_dir():
            paths.update(
                path.resolve()
                for path in input_path.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
            )
            continue
        msg = f"Evaluation corpus path does not exist: {input_path}"
        raise ValueError(msg)
    return sorted(paths, key=str)


if __name__ == "__main__":
    raise SystemExit(main())
