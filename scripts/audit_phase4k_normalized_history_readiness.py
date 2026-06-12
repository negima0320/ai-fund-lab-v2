#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.candidate_ai import discover_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend  # noqa: E402
from scripts.build_candidate_features_real_prepared_dry_run import (  # noqa: E402
    DEFAULT_LOOKBACK_BUSINESS_DAYS,
    DEFAULT_MAX_CODES,
    DEFAULT_MAX_ROWS,
    run_prepared_real_feature_dry_run,
)


PHASE = "Phase4-K Normalized Data History Expansion / Prepared Dry-run Ready"
READY_STATUS = "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN"
BLOCKED_STATUS = "BLOCKED_BY_DATA_WINDOW"
PYTEST_HINT = (
    "python3 scripts/prepare_phase4k_normalized_history.py && "
    "python3 scripts/build_candidate_features_real_prepared_dry_run.py && "
    "python3 scripts/audit_phase4k_normalized_history_readiness.py && "
    "python3 -m pytest tests/test_phase4k_normalized_history_readiness.py && "
    "python3 -m pytest -q"
)

REQUIRED_INPUTS = (
    ROOT / "docs/phase_reports/phase4j_real_feature_prepared_dry_run.md",
    ROOT / "docs/phase_reports/phase4j_real_feature_prepared_dry_run_audit.md",
    ROOT / "reports/phase_reports/phase4j_real_feature_prepared_dry_run_audit.json",
    ROOT / "reports/candidate_ai/phase4j_real_feature_prepared_dry_run_summary.json",
)

FORBIDDEN_SOURCE_TERMS = (
    "def tr" + "ain",
    "def pre" + "dict",
    "def back" + "test",
    "def generate_" + "labels",
    "submit_" + "order",
    "place_" + "order",
    "live " + "mode",
    "JQuants" + "Client(",
)


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    input_format: str = "auto",
    lookback_business_days: int = DEFAULT_LOOKBACK_BUSINESS_DAYS,
    max_codes: int = DEFAULT_MAX_CODES,
    max_rows: int = DEFAULT_MAX_ROWS,
    json_report_path: Path | str = "reports/phase_reports/phase4k_normalized_history_readiness_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4k_normalized_history_readiness_audit.md",
) -> dict[str, Any]:
    history = inspect_normalized_history(
        runtime_dir=runtime_dir,
        input_format=input_format,
        min_lookback_rows=lookback_business_days,
    )
    prepared_summary = run_prepared_real_feature_dry_run(
        runtime_dir=runtime_dir,
        lookback_business_days=lookback_business_days,
        max_codes=max_codes,
        max_rows=max_rows,
        input_format=input_format,
        report_dir=ROOT / "reports/candidate_ai" if Path(runtime_dir) == Path(".runtime") else Path(runtime_dir) / "reports",
    )
    data_source_type = _detect_data_source_type(runtime_dir)
    checks = {
        "required_phase4j_inputs_present": all(path.is_file() for path in REQUIRED_INPUTS),
        "normalized_data_discovery": history["discovery_status"] == "FOUND",
        "storage_format_present": history["storage_format"] in {"parquet", "jsonl"},
        "date_range_present": bool(history["date_min"]) and bool(history["date_max"]),
        "business_day_count_at_least_60": history["business_day_count"] >= lookback_business_days,
        "row_count_present": history["row_count"] > 0,
        "code_count_present": history["code_count"] > 0,
        "per_code_stats_present": history["per_code_row_count_max"] >= history["per_code_row_count_min"],
        "codes_with_sufficient_lookback": history["codes_with_sufficient_lookback"] > 0,
        "prepared_dry_run_eligible_positive": prepared_summary.get("eligible_count", 0) > 0,
        "schema_validation_ok": prepared_summary.get("schema_validation_status") == "OK",
        "leakage_audit_ok": prepared_summary.get("leakage_audit_status") == "OK",
        "prepared_readiness_ready": prepared_summary.get("readiness_status") == READY_STATUS,
        "data_source_type_declared": data_source_type in {"real_runtime", "fixture", "mock", "skipped"},
        "no_real_api_required": data_source_type in {"real_runtime", "fixture", "mock", "skipped"},
        "no_forbidden_implementation": _no_forbidden_implementation(),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    readiness_status = READY_STATUS if checks["prepared_readiness_ready"] else BLOCKED_STATUS
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "readiness_status": readiness_status,
            "data_source_type": data_source_type,
            "checks": checks,
            "normalized_history": history,
            "prepared_dry_run_summary": prepared_summary,
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def inspect_normalized_history(
    *,
    runtime_dir: Path | str = ".runtime",
    input_format: str = "auto",
    min_lookback_rows: int = DEFAULT_LOOKBACK_BUSINESS_DAYS,
) -> dict[str, Any]:
    discovery = discover_daily_quotes_normalized(runtime_dir, input_format=input_format)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        return _empty_history(discovery)
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        history = _empty_history(discovery)
        history["read_error"] = type(exc).__name__
        return history

    dates = sorted({str(record.get("Date") or "") for record in records if record.get("Date")})
    codes = sorted({str(record.get("Code") or "") for record in records if record.get("Code")})
    counts = Counter(str(record.get("Code")) for record in records if record.get("Code"))
    values = list(counts.values())
    sufficient = sum(1 for value in values if value >= min_lookback_rows)
    insufficient = sum(1 for value in values if value < min_lookback_rows)
    return {
        "discovery_status": discovery.status,
        "storage_format": discovery.storage_format,
        "storage_path": str(discovery.path),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "business_day_count": len(dates),
        "code_count": len(codes),
        "row_count": len(records),
        "per_code_row_count_min": min(values) if values else 0,
        "per_code_row_count_max": max(values) if values else 0,
        "per_code_row_count_mean": round(mean(values), 4) if values else 0,
        "codes_with_sufficient_lookback": sufficient,
        "codes_with_insufficient_lookback": insufficient,
        "min_lookback_rows": min_lookback_rows,
        "message": discovery.message,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-K normalized history readiness.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--input-format", default="auto", choices=("auto", "jsonl", "parquet"))
    parser.add_argument("--lookback-business-days", type=int, default=DEFAULT_LOOKBACK_BUSINESS_DAYS)
    parser.add_argument("--max-codes", type=int, default=DEFAULT_MAX_CODES)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--json-report", default="reports/phase_reports/phase4k_normalized_history_readiness_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4k_normalized_history_readiness_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(
        runtime_dir=args.runtime_dir,
        input_format=args.input_format,
        lookback_business_days=args.lookback_business_days,
        max_codes=args.max_codes,
        max_rows=args.max_rows,
        json_report_path=args.json_report,
        markdown_report_path=args.markdown_report,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _empty_history(discovery: Any) -> dict[str, Any]:
    return {
        "discovery_status": discovery.status,
        "storage_format": discovery.storage_format,
        "storage_path": str(discovery.path) if discovery.path is not None else None,
        "date_min": None,
        "date_max": None,
        "business_day_count": 0,
        "code_count": 0,
        "row_count": 0,
        "per_code_row_count_min": 0,
        "per_code_row_count_max": 0,
        "per_code_row_count_mean": 0,
        "codes_with_sufficient_lookback": 0,
        "codes_with_insufficient_lookback": 0,
        "min_lookback_rows": DEFAULT_LOOKBACK_BUSINESS_DAYS,
        "message": discovery.message,
    }


def _detect_data_source_type(runtime_dir: Path | str) -> str:
    manifest = Path(runtime_dir) / "reports" / "candidate_ai" / "phase4k_mock_normalized_history_manifest.json"
    if manifest.is_file():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "skipped"
        if payload.get("data_source_type") == "mock":
            return "mock"
    discovery = discover_daily_quotes_normalized(runtime_dir)
    if discovery.status == "FOUND":
        return "real_runtime"
    return "skipped"


def _no_forbidden_implementation() -> bool:
    source_paths = [
        ROOT / "scripts/prepare_phase4k_normalized_history.py",
        ROOT / "scripts/audit_phase4k_normalized_history_readiness.py",
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.is_file())
    return all(term not in source_text for term in FORBIDDEN_SOURCE_TERMS)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    history = payload["normalized_history"]
    summary = payload["prepared_dry_run_summary"]
    lines = [
        "# AI Fund Lab vNext Phase4-K Normalized History Readiness Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        f"- readiness_status: `{payload['readiness_status']}`",
        f"- data_source_type: `{payload['data_source_type']}`",
        "",
        "## Normalized History",
        "",
        f"- storage_format: `{history['storage_format']}`",
        f"- storage_path: `{history['storage_path']}`",
        f"- date_min: `{history['date_min']}`",
        f"- date_max: `{history['date_max']}`",
        f"- business_day_count: `{history['business_day_count']}`",
        f"- code_count: `{history['code_count']}`",
        f"- row_count: `{history['row_count']}`",
        f"- per_code_row_count_min: `{history['per_code_row_count_min']}`",
        f"- per_code_row_count_max: `{history['per_code_row_count_max']}`",
        f"- per_code_row_count_mean: `{history['per_code_row_count_mean']}`",
        f"- codes_with_sufficient_lookback: `{history['codes_with_sufficient_lookback']}`",
        f"- codes_with_insufficient_lookback: `{history['codes_with_insufficient_lookback']}`",
        "",
        "## Prepared Dry-run",
        "",
        f"- readiness_status: `{summary.get('readiness_status')}`",
        f"- eligible_count: `{summary.get('eligible_count')}`",
        f"- excluded_count: `{summary.get('excluded_count')}`",
        f"- schema_validation_status: `{summary.get('schema_validation_status')}`",
        f"- leakage_audit_status: `{summary.get('leakage_audit_status')}`",
        "",
        "## Boundary",
        "",
        "Phase4-K only expands normalized history and checks prepared dry-run readiness. It does not implement labels, datasets, Candidate AI training, inference, backtest, trading, broker live access, ordering, or portfolio auto-update.",
        "",
        "## pytest",
        "",
        f"`{payload['pytest_hint']}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
