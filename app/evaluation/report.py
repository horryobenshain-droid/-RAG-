import json
from pathlib import Path

from app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationRun,
    EvaluationSummary,
    ProfileEvaluationResult,
)


def write_json_report(run: EvaluationRun, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = run.model_dump(mode="json")
    path.write_text(
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )


def write_markdown_report(run: EvaluationRun, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(run), encoding="utf-8")


def _render_markdown(run: EvaluationRun) -> str:
    top_k_line = (
        f"- 全局 Top K：`{run.top_k_override}`"
        if run.top_k_override
        else "- 全局 Top K：按用例配置"
    )
    lines = [
        "# RAG 评估报告",
        "",
        f"- 数据集：`{run.dataset_name}`",
        f"- 数据集文件：`{run.dataset_path}`",
        f"- 生成时间：`{run.generated_at}`",
        top_k_line,
        "",
        "## 模型对比",
        "",
        "| Profile | Provider / Model | 通过率 | Recall@K | 引用命中率 | "
        "答案关键词召回率 | 平均延迟 | P95 延迟 | 错误 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for profile in run.profiles:
        summary = profile.summary
        lines.append(
            "| "
            f"{_table_cell(profile.profile_name)} | "
            f"{_table_cell(f'{profile.llm_provider} / {profile.llm_model}')} | "
            f"{_percent(summary.pass_rate)} | "
            f"{_percent(summary.recall_at_k)} | "
            f"{_percent(summary.citation_hit_rate)} | "
            f"{_percent(summary.answer_keyword_recall)} | "
            f"{_milliseconds(summary.average_latency_ms)} | "
            f"{_milliseconds(summary.p95_latency_ms)} | "
            f"{summary.error_cases} |"
        )

    for profile in run.profiles:
        lines.extend(_render_profile(profile))
    return "\n".join(lines).rstrip() + "\n"


def _render_profile(profile: ProfileEvaluationResult) -> list[str]:
    summary = profile.summary
    lines = [
        "",
        f"## {_heading(profile.profile_name)}",
        "",
        f"模型：`{profile.llm_provider} / {profile.llm_model}`  ",
        f"开始时间：`{profile.started_at}`  ",
        f"总耗时：`{profile.duration_ms:.2f} ms`",
        "",
        _summary_line(summary),
        "",
        "| 用例 | 状态 | Recall@K | 引用命中 | 关键词召回 | 延迟 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for case in profile.cases:
        lines.append(
            "| "
            f"{_table_cell(case.case_id)} | "
            f"{case.status} | "
            f"{_percent(case.recall_at_k)} | "
            f"{_boolean(case.citation_hit)} | "
            f"{_percent(case.answer_keyword_recall)} | "
            f"{_milliseconds(case.elapsed_ms)} |"
        )

    for case in profile.cases:
        lines.extend(_render_case(case))
    return lines


def _render_case(case: EvaluationCaseResult) -> list[str]:
    lines = [
        "",
        f"### {_heading(case.case_id)}",
        "",
        f"**问题：** {case.question}",
        "",
        f"**状态：** `{case.status}`",
    ]
    if case.error:
        lines.extend(["", f"**错误：** `{case.error}`"])
        return lines

    if case.missing_answer_keywords:
        missing = ", ".join(f"`{keyword}`" for keyword in case.missing_answer_keywords)
        lines.extend(["", f"**缺失关键词：** {missing}"])
    if case.matched_forbidden_keywords:
        forbidden = ", ".join(
            f"`{keyword}`" for keyword in case.matched_forbidden_keywords
        )
        lines.extend(["", f"**命中禁用词：** {forbidden}"])

    lines.extend(
        [
            "",
            "**检索来源：**",
            "",
            "| # | 文件 | Chunk | Symbol | Score | 命中词 |",
            "| ---: | --- | --- | --- | ---: | --- |",
        ]
    )
    if case.sources:
        for source in case.sources:
            keywords = ", ".join(source.matched_keywords) or "-"
            lines.append(
                "| "
                f"{source.source_id} | "
                f"{_table_cell(source.file_name)} | "
                f"{_table_cell(source.chunk_id)} | "
                f"{_table_cell(source.symbol_name)} | "
                f"{_decimal(source.score)} | "
                f"{_table_cell(keywords)} |"
            )
    else:
        lines.append("| - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "<details>",
            "<summary>查看模型答案</summary>",
            "",
            "~~~~markdown",
            case.answer,
            "~~~~",
            "",
            "</details>",
        ]
    )
    return lines


def _summary_line(summary: EvaluationSummary) -> str:
    return (
        f"通过 `{summary.passed_cases}/{summary.total_cases}`，"
        f"失败 `{summary.failed_cases}`，错误 `{summary.error_cases}`；"
        f"Recall@K `{_percent(summary.recall_at_k)}`，"
        f"引用命中率 `{_percent(summary.citation_hit_rate)}`。"
    )


def _percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def _milliseconds(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f} ms"


def _decimal(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def _boolean(value: bool | None) -> str:
    if value is None:
        return "-"
    return "是" if value else "否"


def _table_cell(value: object) -> str:
    if value is None:
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _heading(value: str) -> str:
    return value.replace("\n", " ").strip()
