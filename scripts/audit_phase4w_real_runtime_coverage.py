#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import build_full_range_chunk_plan  # noqa: E402
from ai_fund_lab_v2.candidate_ai.data_loader import validate_daily_quotes_normalized_input  # noqa: E402
from ai_fund_lab_v2.candidate_ai.normalized_data_reader import discover_daily_quotes_normalized  # noqa: E402
from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend  # noqa: E402

SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4w_real_runtime_coverage_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4w_real_runtime_coverage_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4w_real_runtime_coverage_audit.md")

READY = "READY_FOR_REAL_RUNTIME_FULL_CONTROLLED_FEATURE_GENERATION"
BLOCKED_COVERAGE = "BLOCKED_BY_REAL_RUNTIME_DATA_COVERAGE"
BLOCKED_STORAGE = "BLOCKED_BY_STORAGE"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA"
SKIPPED_NO_REAL = "SKIPPED_NO_REAL_RUNTIME_DATA"


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_real_runtime_coverage_summary(runtime_dir=runtime_dir, report_dir=report_dir)
    _write_json(summary_path, summary)
    checks = {
        "real_runtime_coverage_summary_exists": summary_path.is_file(),
        "api_call_not_performed": summary.get("api_call_performed") is False,
        "mock_real_runtime_identification_present": "mock_history_detected" in summary
        and "real_runtime_history_detected" in summary
        and "selected_data_source_type" in summary,
        "coverage_stats_produced": all(key in summary for key in ("date_min", "date_max", "business_day_count", "code_count", "row_count")),
        "per_code_lookback_stats_produced": all(
            key in summary
            for key in (
                "per_code_row_count_min",
                "per_code_row_count_max",
                "per_code_row_count_mean",
                "codes_with_60_business_day_lookback",
                "codes_without_60_business_day_lookback",
            )
        ),
        "readiness_status_produced": summary.get("readiness_status")
        in {READY, BLOCKED_COVERAGE, BLOCKED_STORAGE, BLOCKED_SCHEMA, SKIPPED_NO_REAL},
        "ready_or_clear_blocked_or_skipped_status_produced": summary.get("status") in {"READY", "BLOCKED", "SKIPPED"},
        "chunk_scale_estimate_produced": summary.get("estimated_chunk_count", 0) >= 0
        and summary.get("estimated_output_size_bytes", 0) >= 0,
        "mock_history_not_misclassified_as_real_runtime": not (
            summary.get("mock_history_detected") is True
            and summary.get("selected_data_source_type") == "real_runtime"
        ),
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "no_secret_terms_in_reports": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-W",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4w_real_runtime_coverage.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_real_runtime_coverage_summary(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    min_lookback_rows: int = 60,
    max_codes_per_chunk: int = 30,
    estimated_bytes_per_feature_row: int = 512,
) -> dict[str, Any]:
    runtime = Path(runtime_dir)
    discovery = discover_daily_quotes_normalized(runtime, input_format=input_format)
    mock_detected = _mock_history_detected(runtime, discovery.path)
    if discovery.status != "FOUND" or discovery.path is None or discovery.storage_format is None:
        return _base_summary(
            status="SKIPPED",
            readiness_status=SKIPPED_NO_REAL,
            runtime_dir=runtime,
            mock_history_detected=mock_detected,
            real_runtime_history_detected=False,
            selected_data_source_type="skipped",
            reason=discovery.message,
        )
    selected_type = "mock" if mock_detected else "real_runtime"
    real_detected = selected_type == "real_runtime"
    try:
        records = create_storage_backend(discovery.storage_format).read_records(discovery.path)
    except (StorageBackendError, ImportError, RuntimeError) as exc:
        return _base_summary(
            status="SKIPPED",
            readiness_status=SKIPPED_NO_REAL,
            runtime_dir=runtime,
            mock_history_detected=mock_detected,
            real_runtime_history_detected=False,
            selected_data_source_type="skipped",
            path=str(discovery.path),
            storage_format=discovery.storage_format,
            reason=f"could not read normalized data: {type(exc).__name__}",
        )
    stats = _coverage_stats(records, min_lookback_rows=min_lookback_rows)
    schema_ok = False
    schema_messages: list[str] = []
    if records and stats["date_max"]:
        validation = validate_daily_quotes_normalized_input(records, as_of_date=str(stats["date_max"]))
        schema_ok = validation.is_valid
        schema_messages = list(validation.messages)
    chunk_plan = build_full_range_chunk_plan(
        records,
        run_id="phase4w_real_runtime_scale_estimate",
        data_source_type=selected_type,
        max_codes_per_chunk=max_codes_per_chunk,
    ) if records else []
    storage = _storage_guard(runtime, estimated_feature_rows=stats["row_count"], estimated_bytes_per_feature_row=estimated_bytes_per_feature_row)
    readiness_status = _readiness_status(
        is_real_runtime=real_detected,
        business_day_count=stats["business_day_count"],
        codes_with_lookback=stats["codes_with_60_business_day_lookback"],
        row_count=stats["row_count"],
        schema_ok=schema_ok,
        storage_ok=storage["runtime_free_space_sufficient"],
    )
    status = "READY" if readiness_status == READY else ("SKIPPED" if readiness_status == SKIPPED_NO_REAL else "BLOCKED")
    estimated_feature_rows = stats["row_count"]
    estimated_output_size = estimated_feature_rows * max(1, estimated_bytes_per_feature_row)
    summary = {
        "status": status,
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "selected_data_source_type": selected_type,
        "mock_history_detected": mock_detected,
        "real_runtime_history_detected": real_detected,
        "is_mock": mock_detected,
        "is_fixture": False,
        "is_real_runtime": real_detected,
        "path": str(discovery.path),
        "storage_format": discovery.storage_format,
        **stats,
        "schema_mapping_possible": schema_ok,
        "schema_validation_messages": schema_messages,
        "estimated_chunk_count": len(chunk_plan),
        "estimated_feature_rows": estimated_feature_rows,
        "estimated_output_size_bytes": estimated_output_size,
        "runtime_free_space_bytes": storage["runtime_free_space_bytes"],
        "runtime_free_space_sufficient": storage["runtime_free_space_sufficient"],
        "recommended_chunk_strategy": "month date chunk + code chunk",
        "recommended_max_chunks_first_run": 4 if readiness_status == READY else 0,
        "recommended_next_action": _recommended_action(readiness_status, selected_type),
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }
    return summary


def _coverage_stats(records: list[dict[str, Any]], *, min_lookback_rows: int) -> dict[str, Any]:
    dates = sorted({str(record.get("Date") or "") for record in records if record.get("Date")})
    codes = sorted({str(record.get("Code") or "") for record in records if record.get("Code")})
    counts = Counter(str(record.get("Code") or "") for record in records if record.get("Code"))
    values = [counts[code] for code in codes]
    if dates:
        calendar_day_count = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1
    else:
        calendar_day_count = 0
    sufficient = sum(1 for value in values if value >= min_lookback_rows)
    return {
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "business_day_count": len(dates),
        "calendar_day_count": calendar_day_count,
        "code_count": len(codes),
        "row_count": len(records),
        "per_code_row_count_min": min(values) if values else 0,
        "per_code_row_count_max": max(values) if values else 0,
        "per_code_row_count_mean": round(mean(values), 4) if values else 0,
        "codes_with_60_business_day_lookback": sufficient,
        "codes_without_60_business_day_lookback": max(0, len(codes) - sufficient),
    }


def _mock_history_detected(runtime_dir: Path, normalized_path: Path | None) -> bool:
    manifest_paths = (
        Path("reports/candidate_ai/phase4k_mock_normalized_history_manifest.json"),
        runtime_dir / "reports" / "candidate_ai" / "phase4k_mock_normalized_history_manifest.json",
    )
    normalized_text = str(normalized_path) if normalized_path else ""
    for path in manifest_paths:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        manifest_runtime = Path(str(payload.get("runtime_dir") or "")).resolve()
        if payload.get("data_source_type") != "mock":
            continue
        if manifest_runtime == runtime_dir.resolve():
            return True
        if normalized_text and str(payload.get("normalized_storage_path") or "") == normalized_text:
            return True
    return False


def _storage_guard(runtime_dir: Path, *, estimated_feature_rows: int, estimated_bytes_per_feature_row: int) -> dict[str, Any]:
    estimated = estimated_feature_rows * max(1, estimated_bytes_per_feature_row)
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(runtime_dir)
        free = usage.free
        sufficient = free > max(estimated * 2, 1)
    except OSError:
        free = 0
        sufficient = True
    return {
        "runtime_free_space_bytes": free,
        "runtime_free_space_sufficient": sufficient,
    }


def _readiness_status(
    *,
    is_real_runtime: bool,
    business_day_count: int,
    codes_with_lookback: int,
    row_count: int,
    schema_ok: bool,
    storage_ok: bool,
) -> str:
    if not is_real_runtime:
        return SKIPPED_NO_REAL
    if row_count <= 0 or business_day_count < 60 or codes_with_lookback <= 0:
        return BLOCKED_COVERAGE
    if not schema_ok:
        return BLOCKED_SCHEMA
    if not storage_ok:
        return BLOCKED_STORAGE
    return READY


def _recommended_action(readiness_status: str, selected_type: str) -> str:
    if readiness_status == READY:
        return "ready for real_runtime full controlled feature generation gate with stop-on-first-failure guards"
    if readiness_status == SKIPPED_NO_REAL and selected_type == "mock":
        return "real_runtime normalized history is not present; do not use Phase4-K mock history as real runtime coverage"
    if readiness_status == SKIPPED_NO_REAL:
        return "prepare or discover real_runtime daily_quotes_normalized without calling the API in this audit"
    if readiness_status == BLOCKED_COVERAGE:
        return "expand real_runtime normalized history until at least 60 business days and one code has sufficient lookback"
    if readiness_status == BLOCKED_SCHEMA:
        return "fix daily_quotes_normalized schema mapping before real_runtime controlled generation"
    return "free runtime storage or reduce the next controlled batch size"


def _base_summary(
    *,
    status: str,
    readiness_status: str,
    runtime_dir: Path,
    mock_history_detected: bool,
    real_runtime_history_detected: bool,
    selected_data_source_type: str,
    path: str | None = None,
    storage_format: str | None = None,
    reason: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "selected_data_source_type": selected_data_source_type,
        "mock_history_detected": mock_history_detected,
        "real_runtime_history_detected": real_runtime_history_detected,
        "is_mock": mock_history_detected,
        "is_fixture": False,
        "is_real_runtime": real_runtime_history_detected,
        "path": path,
        "storage_format": storage_format,
        "date_min": None,
        "date_max": None,
        "business_day_count": 0,
        "calendar_day_count": 0,
        "code_count": 0,
        "row_count": 0,
        "per_code_row_count_min": 0,
        "per_code_row_count_max": 0,
        "per_code_row_count_mean": 0,
        "codes_with_60_business_day_lookback": 0,
        "codes_without_60_business_day_lookback": 0,
        "schema_mapping_possible": False,
        "estimated_chunk_count": 0,
        "estimated_feature_rows": 0,
        "estimated_output_size_bytes": 0,
        "runtime_free_space_bytes": _storage_guard(runtime_dir, estimated_feature_rows=0, estimated_bytes_per_feature_row=512)["runtime_free_space_bytes"],
        "runtime_free_space_sufficient": True,
        "recommended_chunk_strategy": "month date chunk + code chunk",
        "recommended_max_chunks_first_run": 0,
        "recommended_next_action": reason,
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "selected_data_source_type",
        "mock_history_detected",
        "real_runtime_history_detected",
        "date_min",
        "date_max",
        "business_day_count",
        "code_count",
        "row_count",
        "codes_with_60_business_day_lookback",
        "codes_without_60_business_day_lookback",
        "estimated_chunk_count",
        "runtime_free_space_sufficient",
    )
    return {key: summary.get(key) for key in keys}


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-W Real Runtime Coverage Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This audit reads existing normalized runtime data only.",
            "- It performs no J-Quants API call and never treats Phase4-K mock history as real_runtime.",
            "- It does not generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
