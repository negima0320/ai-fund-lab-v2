#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-AU"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4au_training_lookback_coverage_summary.json")
REPORT_PATH = Path("docs/phase_reports/phase4au_training_lookback_coverage.md")
PHASE4AO_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json")
PHASE4AN_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4an_historical_feature_coverage_summary.json")
PHASE4AL_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4al_label_generation_summary.json")
PHASE4AT_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4at_candidate_feature_quality_summary.json")

READY_FILTER = "READY_FOR_DATASET_LOOKBACK_FILTER_PLAN"
READY_LONG_HISTORY = "READY_FOR_LONG_HISTORY_FETCH_PLAN"
BLOCKED_MISSING_DATASET = "BLOCKED_BY_MISSING_DATASET"
BLOCKED_MISSING_FEATURE_TABLE = "BLOCKED_BY_MISSING_FEATURE_TABLE"
BLOCKED_MISSING_NORMALIZED_HISTORY = "BLOCKED_BY_MISSING_NORMALIZED_HISTORY"
BLOCKED_AUDIT_FAILURE = "BLOCKED_BY_AUDIT_FAILURE"

LOOKBACK_WINDOWS = (5, 20, 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-AU training lookback coverage.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--phase4ao-summary", default=str(PHASE4AO_SUMMARY_PATH))
    parser.add_argument("--phase4an-summary", default=str(PHASE4AN_SUMMARY_PATH))
    parser.add_argument("--phase4al-summary", default=str(PHASE4AL_SUMMARY_PATH))
    parser.add_argument("--phase4at-summary", default=str(PHASE4AT_SUMMARY_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    summary = audit_phase4au_training_lookback_coverage(
        runtime_dir=args.runtime_dir,
        phase4ao_summary_path=Path(args.phase4ao_summary),
        phase4an_summary_path=Path(args.phase4an_summary),
        phase4al_summary_path=Path(args.phase4al_summary),
        phase4at_summary_path=Path(args.phase4at_summary),
        summary_path=Path(args.summary_path),
        report_path=Path(args.report_path),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def audit_phase4au_training_lookback_coverage(
    *,
    runtime_dir: Path | str = ".runtime",
    phase4ao_summary_path: Path = PHASE4AO_SUMMARY_PATH,
    phase4an_summary_path: Path = PHASE4AN_SUMMARY_PATH,
    phase4al_summary_path: Path = PHASE4AL_SUMMARY_PATH,
    phase4at_summary_path: Path = PHASE4AT_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    ao_summary = _read_json_optional(phase4ao_summary_path)
    an_summary = _read_json_optional(phase4an_summary_path)
    al_summary = _read_json_optional(phase4al_summary_path)
    at_summary = _read_json_optional(phase4at_summary_path)

    dataset_path = Path(str(ao_summary.get("dataset_output_path") or ""))
    feature_path = Path(str(an_summary.get("historical_feature_output_path") or ""))
    label_path = Path(str(al_summary.get("label_output_path") or ""))
    normalized_path = Path(str(al_summary.get("normalized_input_path") or _default_normalized_path(paths)))

    dataset_rows = _read_rows(dataset_path)
    if not dataset_rows:
        summary = _blocked_summary(
            readiness_status=BLOCKED_MISSING_DATASET,
            reason="Phase4-AO dataset is missing or empty.",
            paths=paths,
            summary_path=summary_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, report_path, summary)
        return summary

    feature_rows = _read_rows(feature_path)
    if not feature_rows:
        summary = _blocked_summary(
            readiness_status=BLOCKED_MISSING_FEATURE_TABLE,
            reason="Phase4-AN historical feature table is missing or empty.",
            paths=paths,
            summary_path=summary_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, report_path, summary)
        return summary

    normalized_records = _read_normalized_records(normalized_path)
    current_normalized_dates = _extract_sorted_dates(normalized_records)
    if not current_normalized_dates:
        summary = _blocked_summary(
            readiness_status=BLOCKED_MISSING_NORMALIZED_HISTORY,
            reason="real_runtime normalized history is missing or empty.",
            paths=paths,
            summary_path=summary_path,
            report_path=report_path,
        )
        _write_outputs(summary_path, report_path, summary)
        return summary

    dataset_dates = _extract_sorted_dates(dataset_rows)
    feature_dates = _extract_sorted_dates(feature_rows)
    normalized_dates, normalized_history_source = _resolve_normalized_dates_for_audit(
        current_normalized_dates=current_normalized_dates,
        feature_dates=feature_dates,
        dataset_dates=dataset_dates,
    )
    label_rows = _read_rows(label_path)
    label_dates = _extract_sorted_dates(label_rows)
    feature_columns = _dataset_feature_columns(dataset_rows)
    lookback_report = build_lookback_report(dataset_dates=dataset_dates, normalized_dates=normalized_dates)
    feature_non_null_rate_by_window = build_feature_non_null_rate_by_window(
        rows=dataset_rows,
        feature_columns=feature_columns,
        lookback_report=lookback_report,
    )
    target_date_non_null_rate_report = build_target_date_non_null_rate_report(
        rows=dataset_rows,
        feature_columns=feature_columns,
        lookback_report=lookback_report,
    )
    trainable_dates = [
        date for date in dataset_dates if lookback_report["by_target_date"][date]["has_60d_lookback"]
    ]
    trainable_date_set = set(trainable_dates)
    trainable_row_count = sum(1 for row in dataset_rows if str(row.get("target_date")) in trainable_date_set)
    excluded_row_count = len(dataset_rows) - trainable_row_count

    target_dates_with_60d = lookback_report["target_dates_with_60d_lookback_count"]
    readiness_status = READY_FILTER if target_dates_with_60d > 0 else READY_LONG_HISTORY
    root_cause = _root_cause(readiness_status, lookback_report)
    summary = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "audit_executed": True,
        "dataset_target_date_min": _first_or_none(dataset_dates),
        "dataset_target_date_max": _last_or_none(dataset_dates),
        "dataset_target_date_count": len(dataset_dates),
        "feature_target_date_min": _first_or_none(feature_dates),
        "feature_target_date_max": _last_or_none(feature_dates),
        "feature_target_date_count": len(feature_dates),
        "label_target_date_min": _first_or_none(label_dates),
        "label_target_date_max": _last_or_none(label_dates),
        "label_target_date_count": len(label_dates),
        "normalized_date_min": _first_or_none(normalized_dates),
        "normalized_date_max": _last_or_none(normalized_dates),
        "normalized_business_day_count": len(normalized_dates),
        "current_normalized_file_date_min": _first_or_none(current_normalized_dates),
        "current_normalized_file_date_max": _last_or_none(current_normalized_dates),
        "current_normalized_file_business_day_count": len(current_normalized_dates),
        "normalized_history_source": normalized_history_source,
        "first_target_date_with_5d_lookback": lookback_report["first_target_date_with_5d_lookback"],
        "first_target_date_with_20d_lookback": lookback_report["first_target_date_with_20d_lookback"],
        "first_target_date_with_60d_lookback": lookback_report["first_target_date_with_60d_lookback"],
        "target_dates_with_5d_lookback_count": lookback_report["target_dates_with_5d_lookback_count"],
        "target_dates_with_20d_lookback_count": lookback_report["target_dates_with_20d_lookback_count"],
        "target_dates_with_60d_lookback_count": lookback_report["target_dates_with_60d_lookback_count"],
        "lookback_5d_coverage_rate": lookback_report["lookback_5d_coverage_rate"],
        "lookback_20d_coverage_rate": lookback_report["lookback_20d_coverage_rate"],
        "lookback_60d_coverage_rate": lookback_report["lookback_60d_coverage_rate"],
        "trainable_target_date_min": _first_or_none(trainable_dates),
        "trainable_target_date_max": _last_or_none(trainable_dates),
        "trainable_target_date_count": len(trainable_dates),
        "trainable_row_count": trainable_row_count,
        "excluded_by_lookback_target_date_count": len(dataset_dates) - len(trainable_dates),
        "excluded_by_lookback_row_count": excluded_row_count,
        "feature_non_null_rate_by_window": feature_non_null_rate_by_window,
        "target_date_non_null_rate_report": target_date_non_null_rate_report,
        "root_cause_confirmed": root_cause,
        "blocking_issue": _blocking_issue(readiness_status),
        "recommended_fix_plan": _recommended_fix_plan(readiness_status),
        "more_history_required": readiness_status == READY_LONG_HISTORY,
        "dataset_filter_required": True,
        "feature_expansion_required": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "dataset_row_count": len(dataset_rows),
        "feature_row_count": len(feature_rows),
        "label_row_count": len(label_rows),
        "dataset_output_path": str(dataset_path),
        "historical_feature_output_path": str(feature_path),
        "label_output_path": str(label_path),
        "normalized_input_path": str(normalized_path),
        "phase4at_readiness_status": at_summary.get("readiness_status"),
        "lookback_count_basis": "normalized business-day rows with date <= target_date",
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }
    _write_outputs(summary_path, report_path, summary)
    return summary


def build_lookback_report(*, dataset_dates: list[str], normalized_dates: list[str]) -> dict[str, Any]:
    by_target_date: dict[str, dict[str, Any]] = {}
    for date in dataset_dates:
        available_count = bisect.bisect_right(normalized_dates, date)
        by_target_date[date] = {
            "target_date": date,
            "available_history_row_count": available_count,
            "available_past_business_day_count": bisect.bisect_left(normalized_dates, date),
            "has_5d_lookback": available_count >= 5,
            "has_20d_lookback": available_count >= 20,
            "has_60d_lookback": available_count >= 60,
            "insufficient_history_rate": 1.0 if available_count < 60 else 0.0,
        }
    report: dict[str, Any] = {"by_target_date": by_target_date}
    for window in LOOKBACK_WINDOWS:
        dates = [date for date in dataset_dates if by_target_date[date][f"has_{window}d_lookback"]]
        report[f"first_target_date_with_{window}d_lookback"] = _first_or_none(dates)
        report[f"target_dates_with_{window}d_lookback_count"] = len(dates)
        report[f"lookback_{window}d_coverage_rate"] = _safe_divide(len(dates), len(dataset_dates))
    return report


def build_feature_non_null_rate_by_window(
    *,
    rows: list[dict[str, Any]],
    feature_columns: list[str],
    lookback_report: dict[str, Any],
) -> dict[str, Any]:
    windows = {
        "all_dataset": lambda date: True,
        "lookback_5d": lambda date: bool(lookback_report["by_target_date"][date]["has_5d_lookback"]),
        "lookback_20d": lambda date: bool(lookback_report["by_target_date"][date]["has_20d_lookback"]),
        "lookback_60d": lambda date: bool(lookback_report["by_target_date"][date]["has_60d_lookback"]),
    }
    report: dict[str, Any] = {}
    for window_name, predicate in windows.items():
        scoped_rows = [row for row in rows if predicate(str(row.get("target_date")))]
        per_feature = {
            column: _safe_divide(
                sum(1 for row in scoped_rows if _is_non_null(row.get(column))),
                len(scoped_rows),
            )
            for column in feature_columns
        }
        report[window_name] = {
            "row_count": len(scoped_rows),
            "feature_count": len(feature_columns),
            "average_non_null_rate": _safe_divide(sum(per_feature.values()), len(per_feature)),
            "per_feature_non_null_rate": per_feature,
        }
    return report


def build_target_date_non_null_rate_report(
    *,
    rows: list[dict[str, Any]],
    feature_columns: list[str],
    lookback_report: dict[str, Any],
) -> list[dict[str, Any]]:
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_date[str(row.get("target_date"))].append(row)
    report: list[dict[str, Any]] = []
    for date in sorted(rows_by_date):
        date_rows = rows_by_date[date]
        non_null_total = sum(
            1 for row in date_rows for column in feature_columns if _is_non_null(row.get(column))
        )
        denominator = len(date_rows) * len(feature_columns)
        insufficient_column = "feature__missing_flags_insufficient_history"
        insufficient_count = sum(1 for row in date_rows if bool(row.get(insufficient_column)))
        lookback = lookback_report["by_target_date"].get(date, {})
        report.append(
            {
                "target_date": date,
                "row_count": len(date_rows),
                "available_history_row_count": lookback.get("available_history_row_count", 0),
                "average_feature_non_null_rate": _safe_divide(non_null_total, denominator),
                "insufficient_history_rate": _safe_divide(insufficient_count, len(date_rows)),
                "has_5d_lookback": bool(lookback.get("has_5d_lookback")),
                "has_20d_lookback": bool(lookback.get("has_20d_lookback")),
                "has_60d_lookback": bool(lookback.get("has_60d_lookback")),
            }
        )
    return report


def _resolve_normalized_dates_for_audit(
    *,
    current_normalized_dates: list[str],
    feature_dates: list[str],
    dataset_dates: list[str],
) -> tuple[list[str], str]:
    if _covers_any_dataset_date(current_normalized_dates, dataset_dates):
        return current_normalized_dates, "real_runtime_normalized_file"
    if feature_dates:
        return feature_dates, "phase4an_historical_feature_table_fallback"
    return current_normalized_dates, "real_runtime_normalized_file"


def _covers_any_dataset_date(normalized_dates: list[str], dataset_dates: list[str]) -> bool:
    normalized_set = set(normalized_dates)
    return any(date in normalized_set for date in dataset_dates)


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
        "audit_executed": False,
        "block_reason": reason,
        "dataset_target_date_count": 0,
        "feature_target_date_count": 0,
        "label_target_date_count": 0,
        "normalized_business_day_count": 0,
        "target_dates_with_5d_lookback_count": 0,
        "target_dates_with_20d_lookback_count": 0,
        "target_dates_with_60d_lookback_count": 0,
        "lookback_5d_coverage_rate": 0.0,
        "lookback_20d_coverage_rate": 0.0,
        "lookback_60d_coverage_rate": 0.0,
        "trainable_target_date_count": 0,
        "trainable_row_count": 0,
        "excluded_by_lookback_target_date_count": 0,
        "excluded_by_lookback_row_count": 0,
        "root_cause_confirmed": reason,
        "blocking_issue": reason,
        "recommended_fix_plan": ["Restore the missing input, then rerun Phase4-AU."],
        "more_history_required": False,
        "dataset_filter_required": False,
        "feature_expansion_required": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "runtime_dir": str(paths.runtime_dir),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
    }


def _root_cause(readiness_status: str, lookback_report: dict[str, Any]) -> str:
    if readiness_status == READY_LONG_HISTORY:
        return (
            "No Phase4-AO dataset target_date satisfies the 60-business-day lookback window. "
            "Training-period features are null/constant because label target_dates are too early "
            "relative to the current real_runtime normalized history."
        )
    return (
        "Some dataset target_dates satisfy the 60-business-day lookback window; formal training should "
        "filter out earlier insufficient-history rows before any model training."
    )


def _blocking_issue(readiness_status: str) -> str:
    if readiness_status == READY_LONG_HISTORY:
        return "training_label_target_dates_precede_required_60d_lookback_window"
    return "dataset_contains_rows_that_should_be_filtered_by_lookback_quality_gate"


def _recommended_fix_plan(readiness_status: str) -> list[str]:
    if readiness_status == READY_LONG_HISTORY:
        return [
            "Plan a longer real_runtime normalized history fetch before formal Candidate training.",
            "Require at least 60 target_date<=normalized business-day rows before including rows in training.",
            "Keep feature expansion separate; the current root cause is lookback coverage, not model quality.",
        ]
    return [
        "Add a dataset lookback quality gate that excludes target_dates before 60d history is available.",
        "Rebuild the training dataset after filtering insufficient-history target_dates.",
        "Only then rerun the Candidate training smoke or formal training step.",
    ]


def _write_outputs(summary_path: Path, report_path: Path, summary: dict[str, Any]) -> None:
    _write_json(summary_path, summary)
    _write_markdown_report(report_path, summary)


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AU Training Lookback Coverage Audit",
        "",
        "## Purpose",
        "",
        "Phase4-AU audits whether Phase4-AO training dataset target dates have enough normalized "
        "business-day history for 5d, 20d, and 60d lookback features. This phase performs audit only.",
        "",
        "## Explicitly Not Executed",
        "",
        "- Feature expansion",
        "- Label changes",
        "- Dataset rebuild",
        "- Training",
        "- Inference",
        "- Backtest",
        "- Trading",
        "- Promotion or reader switch",
        "",
        "## Summary",
        "",
        f"- status: `{summary.get('status')}`",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- normalized date range: `{summary.get('normalized_date_min')}` to `{summary.get('normalized_date_max')}`",
        f"- normalized_business_day_count: `{summary.get('normalized_business_day_count')}`",
        f"- dataset target_date range: `{summary.get('dataset_target_date_min')}` to `{summary.get('dataset_target_date_max')}`",
        f"- dataset_target_date_count: `{summary.get('dataset_target_date_count')}`",
        f"- label target_date range: `{summary.get('label_target_date_min')}` to `{summary.get('label_target_date_max')}`",
        f"- feature target_date range: `{summary.get('feature_target_date_min')}` to `{summary.get('feature_target_date_max')}`",
        "",
        "## Lookback Coverage",
        "",
        f"- first_target_date_with_5d_lookback: `{summary.get('first_target_date_with_5d_lookback')}`",
        f"- first_target_date_with_20d_lookback: `{summary.get('first_target_date_with_20d_lookback')}`",
        f"- first_target_date_with_60d_lookback: `{summary.get('first_target_date_with_60d_lookback')}`",
        f"- lookback_5d_coverage_rate: `{summary.get('lookback_5d_coverage_rate')}`",
        f"- lookback_20d_coverage_rate: `{summary.get('lookback_20d_coverage_rate')}`",
        f"- lookback_60d_coverage_rate: `{summary.get('lookback_60d_coverage_rate')}`",
        "",
        "## Training Gate Impact",
        "",
        f"- trainable_target_date_range: `{summary.get('trainable_target_date_min')}` to `{summary.get('trainable_target_date_max')}`",
        f"- trainable_target_date_count: `{summary.get('trainable_target_date_count')}`",
        f"- trainable_row_count: `{summary.get('trainable_row_count')}`",
        f"- excluded_by_lookback_target_date_count: `{summary.get('excluded_by_lookback_target_date_count')}`",
        f"- excluded_by_lookback_row_count: `{summary.get('excluded_by_lookback_row_count')}`",
        "",
        "## Root Cause",
        "",
        str(summary.get("root_cause_confirmed") or ""),
        "",
        "## Blocking Issue",
        "",
        str(summary.get("blocking_issue") or ""),
        "",
        "## Recommended Fix Plan",
        "",
    ]
    for item in summary.get("recommended_fix_plan", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Quality Gate Proposal",
            "",
            "Before formal Candidate training, dataset rows should pass a lookback gate that requires "
            "the longest active feature window, currently 60 business days, to be available using only "
            "target_date-or-earlier normalized history.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    payload = _read_json_optional(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return [dict(row) for row in rows]


def _read_normalized_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    if path.suffix == ".json":
        return _read_rows(path)
    if path.suffix == ".jsonl":
        return create_storage_backend("jsonl").read_records(path)
    if path.suffix == ".parquet":
        return create_storage_backend("parquet").read_records(path)
    return []


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _extract_sorted_dates(rows: list[dict[str, Any]]) -> list[str]:
    dates = {
        str(row.get("target_date") or row.get("Date") or row.get("date") or "")
        for row in rows
        if row.get("target_date") or row.get("Date") or row.get("date")
    }
    return sorted(date for date in dates if date)


def _dataset_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns = sorted({column for row in rows for column in row.keys()})
    return [column for column in columns if column.startswith("feature__")]


def _default_normalized_path(paths: RuntimePaths) -> Path:
    return paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data.parquet"


def _is_non_null(value: Any) -> bool:
    return value is not None and value == value


def _safe_divide(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def _last_or_none(values: list[str]) -> str | None:
    return values[-1] if values else None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
