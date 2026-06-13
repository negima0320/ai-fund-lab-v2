#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-AV"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4av_long_history_fetch_plan_summary.json")
REPORT_PATH = Path("docs/phase_reports/phase4av_long_history_fetch_plan.md")
PHASE4AU_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4au_training_lookback_coverage_summary.json")

READY = "READY_FOR_LONG_HISTORY_FETCH_DRY_RUN"
BLOCKED_INCONSISTENCY = "BLOCKED_BY_PLAN_INCONSISTENCY"
BLOCKED_STORAGE = "BLOCKED_BY_STORAGE_ESTIMATE"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

ENDPOINT = "/v2/equities/bars/daily"
LOOKBACK_BUSINESS_DAYS = 60
LABEL_HORIZON_BUSINESS_DAYS = 20
TRAIN_SPLIT_START = "2021-06-01"
TRAIN_SPLIT_END = "2024-12-31"
VALIDATION_SPLIT_START = "2025-01-01"
VALIDATION_SPLIT_END = "2025-12-31"
TEST_SPLIT_START = "2026-01-01"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Phase4-AV long history fetch plan.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--phase4au-summary", default=str(PHASE4AU_SUMMARY_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    parser.add_argument("--current-date", default=None, help="Override current date for deterministic audits.")
    args = parser.parse_args(argv)
    current_date = date.fromisoformat(args.current_date) if args.current_date else None
    summary = audit_phase4av_long_history_fetch_plan(
        runtime_dir=args.runtime_dir,
        phase4au_summary_path=Path(args.phase4au_summary),
        summary_path=Path(args.summary_path),
        report_path=Path(args.report_path),
        current_date=current_date,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def audit_phase4av_long_history_fetch_plan(
    *,
    runtime_dir: Path | str = ".runtime",
    phase4au_summary_path: Path = PHASE4AU_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
    current_date: date | None = None,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    au_summary = _read_json_optional(phase4au_summary_path)
    raw_output_path = paths.runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily"
    normalized_output_path = (
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily"
    )
    if not _safe_runtime_path(paths.runtime_dir, raw_output_path) or not _safe_runtime_path(
        paths.runtime_dir, normalized_output_path
    ):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Planned raw or normalized output path is outside runtime dir.",
            paths=paths,
            summary_path=summary_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, report_path, summary)
        return summary

    if au_summary.get("readiness_status") != "READY_FOR_LONG_HISTORY_FETCH_PLAN":
        summary = _blocked_summary(
            readiness_status=BLOCKED_INCONSISTENCY,
            reason="Phase4-AU summary is missing or does not require a long history fetch plan.",
            paths=paths,
            summary_path=summary_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, report_path, summary)
        return summary

    today = current_date or date.today()
    preferred_fetch_end = _latest_weekday(today)
    required_training_start = date.fromisoformat(TRAIN_SPLIT_START)
    preferred_fetch_start = subtract_business_days(required_training_start, LOOKBACK_BUSINESS_DAYS)
    required_training_end = subtract_business_days(preferred_fetch_end, LABEL_HORIZON_BUSINESS_DAYS)
    estimated_fetch_business_day_count = count_business_days(preferred_fetch_start, preferred_fetch_end)
    estimated_request_count = estimated_fetch_business_day_count
    storage_estimate_mb = estimate_storage_mb(
        raw_output_path=raw_output_path,
        estimated_request_count=estimated_request_count,
        fallback_mb_per_request=0.42,
    )
    readiness_status = _resolve_readiness(
        preferred_fetch_start=preferred_fetch_start,
        required_training_start=required_training_start,
        required_training_end=required_training_end,
        storage_estimate_mb=storage_estimate_mb,
    )
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "plan_created": True,
        "api_call_performed": False,
        "fetch_executed": False,
        "normalized_rebuild_executed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "current_history_start_date": au_summary.get("normalized_date_min"),
        "current_history_end_date": au_summary.get("normalized_date_max"),
        "current_business_day_count": au_summary.get("normalized_business_day_count"),
        "required_training_start_date": required_training_start.isoformat(),
        "required_training_end_date": required_training_end.isoformat(),
        "preferred_fetch_start_date": preferred_fetch_start.isoformat(),
        "preferred_fetch_end_date": preferred_fetch_end.isoformat(),
        "lookback_business_days": LOOKBACK_BUSINESS_DAYS,
        "label_horizon_business_days": LABEL_HORIZON_BUSINESS_DAYS,
        "train_split_start": TRAIN_SPLIT_START,
        "train_split_end": TRAIN_SPLIT_END,
        "validation_split_start": VALIDATION_SPLIT_START,
        "validation_split_end": VALIDATION_SPLIT_END,
        "test_split_start": TEST_SPLIT_START,
        "test_split_end": required_training_end.isoformat(),
        "estimated_fetch_business_day_count": estimated_fetch_business_day_count,
        "estimated_request_count": estimated_request_count,
        "endpoint": ENDPOINT,
        "rate_limit_policy": "Use configured J-Quants Light plan limit of 60 req/min; schedule at most one daily quote request per trading date and retain retry/backoff on 429 without logging secrets.",
        "resume_policy": "Generate one request manifest per target_date, skip succeeded manifests, rerun failed/missing manifests, keep partial responses isolated, and never overwrite mock normalized paths.",
        "manifest_policy": "Store request, response, normalization, feature, label, dataset, and training manifests under .runtime and reports with source_snapshot_id links.",
        "raw_output_path": str(raw_output_path),
        "normalized_output_path": str(normalized_output_path),
        "storage_estimate_mb": storage_estimate_mb,
        "formal_training_possible_after_fetch": readiness_status == READY,
        "phase4_completion_criteria_restored": readiness_status == READY,
        "reexecution_plan": [
            "Phase4-AW Long History Fetch Dry-run: generate request sequence without API calls.",
            "Controlled raw fetch after dry-run approval: fetch daily quotes only into .runtime/data/raw/jquants/equities_bars_daily.",
            "Rebuild isolated real_runtime normalized history; do not promote and do not switch readers.",
            "Rebuild historical Candidate features with 60d lookback quality gate.",
            "Regenerate labels using a 20d future horizon and keep labels physically separated from features.",
            "Rebuild dataset with time-series split and exclude target_dates without full lookback/horizon coverage.",
            "Run formal Candidate training only after leakage, schema, and coverage audits pass.",
        ],
        "recommended_next_action": _recommended_next_action(readiness_status),
        "phase4au_root_cause": au_summary.get("root_cause_confirmed"),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }
    _write_outputs(summary_path, report_path, summary)
    return summary


def subtract_business_days(start: date, business_days: int) -> date:
    current = start
    remaining = business_days
    while remaining:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def count_business_days(start: date, end: date) -> int:
    if end < start:
        return 0
    current = start
    count = 0
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def estimate_storage_mb(
    *,
    raw_output_path: Path,
    estimated_request_count: int,
    fallback_mb_per_request: float,
) -> float:
    response_dir = raw_output_path / "responses"
    response_files = sorted(response_dir.glob("*.json")) if response_dir.is_dir() else []
    if response_files:
        total_bytes = sum(path.stat().st_size for path in response_files)
        mb_per_request = total_bytes / len(response_files) / (1024 * 1024)
    else:
        mb_per_request = fallback_mb_per_request
    raw_mb = mb_per_request * estimated_request_count
    normalized_mb = raw_mb * 0.55
    manifest_and_reports_mb = max(25.0, estimated_request_count * 0.02)
    return round(raw_mb + normalized_mb + manifest_and_reports_mb, 2)


def _latest_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def _resolve_readiness(
    *,
    preferred_fetch_start: date,
    required_training_start: date,
    required_training_end: date,
    storage_estimate_mb: float,
) -> str:
    if preferred_fetch_start >= required_training_start or required_training_end <= required_training_start:
        return BLOCKED_INCONSISTENCY
    if storage_estimate_mb > 20_000:
        return BLOCKED_STORAGE
    return READY


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-AW Long History Fetch Dry-run: generate the request sequence without calling J-Quants API."
    if readiness_status == BLOCKED_STORAGE:
        return "Review storage budget and chunking before planning long history fetch dry-run."
    return "Fix the plan inconsistency, then rerun Phase4-AV."


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    paths: RuntimePaths,
    summary_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "plan_created": False,
        "block_reason": reason,
        "api_call_performed": False,
        "fetch_executed": False,
        "normalized_rebuild_executed": False,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "runtime_dir": str(paths.runtime_dir),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "recommended_next_action": "Fix the blocking condition, then rerun Phase4-AV.",
    }


def _write_outputs(summary_path: Path, report_path: Path, summary: dict[str, Any]) -> None:
    _write_json(summary_path, summary)
    _write_markdown_report(report_path, summary)


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AV Long History Fetch Plan for Formal Candidate Training",
        "",
        "## Purpose",
        "",
        "Phase4-AV creates a no-live long history fetch plan for formal Candidate AI training. It does not call APIs, fetch data, rebuild normalized data, generate features or labels, rebuild datasets, train, infer, backtest, trade, promote, or switch readers.",
        "",
        "## Plan Summary",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- current history: `{summary.get('current_history_start_date')}` to `{summary.get('current_history_end_date')}` (`{summary.get('current_business_day_count')}` business days)",
        f"- required training range: `{summary.get('required_training_start_date')}` to `{summary.get('required_training_end_date')}`",
        f"- preferred fetch range: `{summary.get('preferred_fetch_start_date')}` to `{summary.get('preferred_fetch_end_date')}`",
        f"- lookback_business_days: `{summary.get('lookback_business_days')}`",
        f"- label_horizon_business_days: `{summary.get('label_horizon_business_days')}`",
        f"- estimated_fetch_business_day_count: `{summary.get('estimated_fetch_business_day_count')}`",
        f"- estimated_request_count: `{summary.get('estimated_request_count')}`",
        f"- storage_estimate_mb: `{summary.get('storage_estimate_mb')}`",
        "",
        "## Split Plan",
        "",
        f"- Train: `{summary.get('train_split_start')}` to `{summary.get('train_split_end')}`",
        f"- Validation: `{summary.get('validation_split_start')}` to `{summary.get('validation_split_end')}`",
        f"- Test: `{summary.get('test_split_start')}` to `{summary.get('test_split_end')}`",
        "",
        "## Endpoint And Storage",
        "",
        f"- endpoint: `{summary.get('endpoint')}`",
        f"- raw_output_path: `{summary.get('raw_output_path')}`",
        f"- normalized_output_path: `{summary.get('normalized_output_path')}`",
        "",
        "## Policies",
        "",
        f"- rate_limit_policy: {summary.get('rate_limit_policy')}",
        f"- resume_policy: {summary.get('resume_policy')}",
        f"- manifest_policy: {summary.get('manifest_policy')}",
        "",
        "## Re-execution Plan After Long History Fetch",
        "",
    ]
    for item in summary.get("reexecution_plan", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            f"- api_call_performed: `{summary.get('api_call_performed')}`",
            f"- fetch_executed: `{summary.get('fetch_executed')}`",
            f"- normalized_rebuild_executed: `{summary.get('normalized_rebuild_executed')}`",
            f"- feature_generation_executed: `{summary.get('feature_generation_executed')}`",
            f"- label_generation_executed: `{summary.get('label_generation_executed')}`",
            f"- dataset_rebuild_executed: `{summary.get('dataset_rebuild_executed')}`",
            f"- training_executed: `{summary.get('training_executed')}`",
            f"- inference_executed: `{summary.get('inference_executed')}`",
            f"- backtest_executed: `{summary.get('backtest_executed')}`",
            f"- trading_executed: `{summary.get('trading_executed')}`",
            "",
            "## Recommended Next Action",
            "",
            str(summary.get("recommended_next_action") or ""),
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _safe_runtime_path(runtime_dir: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(runtime_dir.resolve())
        return True
    except ValueError:
        return False


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
