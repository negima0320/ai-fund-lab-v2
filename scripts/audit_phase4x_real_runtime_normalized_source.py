#!/usr/bin/env python3
from __future__ import annotations

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

from ai_fund_lab_v2.data_quality.normalization import (  # noqa: E402
    DAILY_QUOTES_ENDPOINT,
    DAILY_QUOTES_NORMALIZED_ENDPOINT,
    normalize_daily_quotes,
    normalized_output_path,
)
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.data_store.manifest import manifest_path, read_manifest  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4x_real_runtime_normalized_source_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4x_real_runtime_normalized_source_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4x_real_runtime_normalized_source_audit.md")

READY_REBUILD = "READY_TO_REBUILD_REAL_RUNTIME_NORMALIZED_FROM_RAW"
READY_EXISTING = "READY_TO_USE_EXISTING_REAL_RUNTIME_NORMALIZED"
BLOCKED_RAW = "BLOCKED_BY_MISSING_RAW_DATA"
BLOCKED_MANIFEST = "BLOCKED_BY_MISSING_MANIFEST"
BLOCKED_MOCK_ONLY = "BLOCKED_BY_MOCK_ONLY"
BLOCKED_PROVENANCE = "BLOCKED_BY_UNKNOWN_PROVENANCE"
SKIPPED_NO_RUNTIME = "SKIPPED_NO_RUNTIME_DATA"


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_real_runtime_normalized_source_summary(runtime_dir=runtime_dir)
    _write_json(summary_path, summary)
    checks = {
        "runtime_inventory_produced": "inventory" in summary
        and all(key in summary for key in ("raw_daily_quotes_detected", "normalized_daily_quotes_detected")),
        "provenance_classification_produced": bool(summary.get("selected_data_source_type"))
        and isinstance(summary.get("provenance"), dict),
        "mock_history_not_misclassified": not (
            summary.get("mock_normalized_history_detected") is True
            and summary.get("real_runtime_normalized_detected") is True
            and summary.get("selected_data_source_type") == "real_runtime"
        ),
        "api_call_not_performed": summary.get("api_call_performed") is False,
        "rebuild_feasibility_assessed": "safe_rebuild_possible" in summary
        and "would_overwrite_mock_history" in summary
        and "normalizer_available" in summary,
        "readiness_status_produced": summary.get("readiness_status")
        in {
            READY_REBUILD,
            READY_EXISTING,
            BLOCKED_RAW,
            BLOCKED_MANIFEST,
            BLOCKED_MOCK_ONLY,
            BLOCKED_PROVENANCE,
            SKIPPED_NO_RUNTIME,
        },
        "ready_or_clear_blocked_or_skipped_status_produced": summary.get("status") in {"READY", "BLOCKED", "SKIPPED"},
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_terms_not_emitted": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-X",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4x_real_runtime_normalized_source.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_real_runtime_normalized_source_summary(*, runtime_dir: Path | str = ".runtime") -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    raw_manifest_path = manifest_path(paths.raw_data)
    manifest_entries = read_manifest(raw_manifest_path)
    raw_path, raw_format, raw_records = _read_first_existing(paths.raw_data / "jquants" / "equities_bars_daily" / "data")
    normalized_path, normalized_format, normalized_records = _read_first_existing(
        paths.raw_normalized_data / "jquants" / "equities_bars_daily" / "data"
    )
    mock_manifest = _read_mock_manifest(paths)
    mock_detected = bool(mock_manifest)
    fixture_detected = _fixture_detected(paths.runtime_dir, manifest_entries)
    raw_entries = _matching_entries(
        manifest_entries,
        endpoints={DAILY_QUOTES_ENDPOINT},
        storage_path=raw_path,
        exclude_mock=True,
    )
    normalized_entries = _matching_entries(
        manifest_entries,
        endpoints={DAILY_QUOTES_NORMALIZED_ENDPOINT, "daily_quotes_normalized"},
        storage_path=normalized_path,
        exclude_mock=False,
    )
    raw_real = bool(raw_path and raw_entries and not fixture_detected)
    latest_normalized = normalized_entries[-1] if normalized_entries else {}
    normalized_latest_is_mock = str(latest_normalized.get("data_source_type") or "").lower() == "mock" or str(
        latest_normalized.get("source_endpoint") or ""
    ).startswith("mock")
    real_normalized = bool(
        normalized_path
        and latest_normalized
        and not normalized_latest_is_mock
        and not mock_detected
        and not fixture_detected
        and str(latest_normalized.get("source_endpoint") or latest_normalized.get("endpoint") or "").lower()
        in {DAILY_QUOTES_ENDPOINT.lower(), "jquants", "daily_quotes_normalized"}
    )
    raw_stats = _record_stats(raw_records)
    normalized_stats = _record_stats(normalized_records)
    normalizer_available = callable(normalize_daily_quotes)
    default_normalized_path = normalized_output_path(paths, normalized_format or "parquet")
    would_overwrite_mock = bool(mock_detected and normalized_path and normalized_path == default_normalized_path)
    raw_manifest_exists = bool(raw_entries)
    safe_rebuild_possible = bool(raw_real and raw_manifest_exists and normalizer_available and raw_records)
    if real_normalized:
        readiness_status = READY_EXISTING
        status = "READY"
        selected_type = "real_runtime"
        selected_input = str(normalized_path)
    elif safe_rebuild_possible:
        readiness_status = READY_REBUILD
        status = "READY"
        selected_type = "real_raw_jquants"
        selected_input = str(raw_path)
    elif raw_path and not raw_manifest_exists:
        readiness_status = BLOCKED_MANIFEST
        status = "BLOCKED"
        selected_type = "unknown"
        selected_input = str(raw_path)
    elif mock_detected and normalized_path and not raw_path:
        readiness_status = BLOCKED_MOCK_ONLY
        status = "BLOCKED"
        selected_type = "mock"
        selected_input = str(normalized_path)
    elif not raw_path and not normalized_path:
        readiness_status = SKIPPED_NO_RUNTIME
        status = "SKIPPED"
        selected_type = "missing"
        selected_input = None
    elif not raw_path:
        readiness_status = BLOCKED_RAW
        status = "BLOCKED"
        selected_type = "mock" if mock_detected else "unknown"
        selected_input = str(normalized_path) if normalized_path else None
    else:
        readiness_status = BLOCKED_PROVENANCE
        status = "BLOCKED"
        selected_type = "unknown"
        selected_input = str(raw_path)
    inventory = {
        "raw_daily_quotes_path": str(raw_path) if raw_path else None,
        "normalized_daily_quotes_path": str(normalized_path) if normalized_path else None,
        "trading_calendar_detected": _data_file_exists(paths.raw_data / "jquants" / "trading_calendar" / "data"),
        "listed_issues_detected": _data_file_exists(paths.raw_data / "jquants" / "listed_issues" / "data"),
        "fins_summary_detected": _data_file_exists(paths.raw_data / "jquants" / "fins_summary" / "data"),
        "manifest_path": str(raw_manifest_path) if raw_manifest_path.exists() else None,
        "mock_manifest_path": str(_mock_manifest_path(paths)) if mock_detected else None,
    }
    provenance = {
        "raw_daily_quotes": "real_runtime" if raw_real else ("unknown" if raw_path else "missing"),
        "normalized_daily_quotes": "real_runtime" if real_normalized else ("mock" if mock_detected and normalized_path else ("unknown" if normalized_path else "missing")),
        "manifest_entry_count": len(manifest_entries),
        "raw_manifest_entry_count": len(raw_entries),
        "normalized_manifest_entry_count": len(normalized_entries),
        "latest_normalized_source_endpoint": latest_normalized.get("source_endpoint") if latest_normalized else None,
        "latest_normalized_data_source_type": latest_normalized.get("data_source_type") if latest_normalized else None,
    }
    summary = {
        "status": status,
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "raw_daily_quotes_detected": bool(raw_path),
        "normalized_daily_quotes_detected": bool(normalized_path),
        "mock_normalized_history_detected": mock_detected,
        "real_runtime_normalized_detected": real_normalized,
        "manifest_detected": raw_manifest_path.exists(),
        "fixture_detected": fixture_detected,
        "selected_data_source_type": selected_type,
        "selected_input_path": selected_input,
        "raw_date_min": raw_stats["date_min"],
        "raw_date_max": raw_stats["date_max"],
        "raw_row_count": raw_stats["row_count"],
        "raw_code_count": raw_stats["code_count"],
        "normalized_date_min": normalized_stats["date_min"],
        "normalized_date_max": normalized_stats["date_max"],
        "normalized_row_count": normalized_stats["row_count"],
        "normalized_code_count": normalized_stats["code_count"],
        "safe_rebuild_possible": safe_rebuild_possible,
        "would_overwrite_mock_history": would_overwrite_mock,
        "normalizer_available": normalizer_available,
        "raw_manifest_exists": raw_manifest_exists,
        "output_path_design_exists": bool(default_normalized_path),
        "inventory": inventory,
        "provenance": provenance,
        "recommended_next_action": _recommended_action(
            readiness_status,
            would_overwrite_mock=would_overwrite_mock,
        ),
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }
    return summary


def _read_first_existing(base_path: Path) -> tuple[Path | None, str | None, list[dict[str, Any]]]:
    for storage_format in ("parquet", "jsonl"):
        backend = create_storage_backend(storage_format)
        path = backend.path_for(base_path)
        if not path.exists():
            continue
        try:
            return path, storage_format, backend.read_records(path)
        except Exception:
            return path, storage_format, []
    return None, None, []


def _matching_entries(
    entries: list[dict[str, Any]],
    *,
    endpoints: set[str],
    storage_path: Path | None,
    exclude_mock: bool,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    storage_text = str(storage_path) if storage_path else None
    for entry in entries:
        endpoint_values = {
            str(entry.get("endpoint") or ""),
            str(entry.get("source_endpoint") or ""),
            str(entry.get("normalized_endpoint") or ""),
        }
        if not endpoint_values.intersection(endpoints):
            continue
        if storage_text and entry.get("storage_path") and str(entry.get("storage_path")) != storage_text:
            continue
        if exclude_mock and str(entry.get("data_source_type") or "").lower() == "mock":
            continue
        output.append(entry)
    return output


def _record_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(record.get("Date") or record.get("target_date") or "") for record in records if record.get("Date") or record.get("target_date")})
    codes = sorted({str(record.get("Code") or record.get("code") or "") for record in records if record.get("Code") or record.get("code")})
    return {
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "row_count": len(records),
        "code_count": len(codes),
    }


def _read_mock_manifest(paths: RuntimePaths) -> dict[str, Any]:
    path = _mock_manifest_path(paths)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if payload.get("data_source_type") == "mock" else {}


def _mock_manifest_path(paths: RuntimePaths) -> Path:
    return paths.reports / "candidate_ai" / "phase4k_mock_normalized_history_manifest.json"


def _fixture_detected(runtime_dir: Path, entries: list[dict[str, Any]]) -> bool:
    if (runtime_dir / "fixture.marker").exists() or (runtime_dir / ".fixture").exists():
        return True
    serialized = json.dumps(entries, ensure_ascii=True).lower()
    return "fixture" in serialized


def _data_file_exists(base_path: Path) -> bool:
    return any(create_storage_backend(fmt).path_for(base_path).exists() for fmt in ("parquet", "jsonl"))


def _recommended_action(readiness_status: str, *, would_overwrite_mock: bool) -> str:
    if readiness_status == READY_EXISTING:
        return "existing real_runtime normalized history can be used for the next coverage audit"
    if readiness_status == READY_REBUILD:
        if would_overwrite_mock:
            return "raw J-Quants data can rebuild real_runtime normalized history, but write to an isolated path or clear mock history first"
        return "raw J-Quants data can rebuild real_runtime normalized history without overwriting mock history"
    if readiness_status == BLOCKED_MANIFEST:
        return "raw daily quotes exist, but provenance manifest is missing or insufficient"
    if readiness_status == BLOCKED_MOCK_ONLY:
        return "only mock normalized history is available; do not proceed as real_runtime"
    if readiness_status == BLOCKED_RAW:
        return "real raw daily quotes are missing; prepare raw data before rebuilding normalized history"
    if readiness_status == SKIPPED_NO_RUNTIME:
        return "no runtime data found for real_runtime source audit"
    return "provenance is unknown; inspect manifest entries before using or rebuilding normalized history"


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "raw_daily_quotes_detected",
        "normalized_daily_quotes_detected",
        "mock_normalized_history_detected",
        "real_runtime_normalized_detected",
        "manifest_detected",
        "fixture_detected",
        "selected_data_source_type",
        "raw_date_min",
        "raw_date_max",
        "raw_row_count",
        "raw_code_count",
        "normalized_date_min",
        "normalized_date_max",
        "normalized_row_count",
        "normalized_code_count",
        "safe_rebuild_possible",
        "would_overwrite_mock_history",
    )
    return {key: summary.get(key) for key in keys}


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-X Real Runtime Normalized Source Audit",
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
            "- This audit performs no J-Quants API call and does not request credentials.",
            "- It does not execute normalized rebuilds or overwrite mock history.",
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
