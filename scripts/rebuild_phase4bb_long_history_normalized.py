#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_quality.normalization import (  # noqa: E402
    ADJUSTED_FIELDS,
    NORMALIZED_SCHEMA_VERSION,
    UNADJUSTED_FIELDS,
    normalize_daily_quotes,
)
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-BB"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bb_long_history_normalized_summary.json")
PHASE4BA_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ba_long_history_raw_coverage_summary.json")

READY_INPUT = "READY_FOR_LONG_HISTORY_NORMALIZED_REBUILD"
READY = "READY_FOR_LONG_HISTORY_FEATURE_REGENERATION"
BLOCKED_RAW_SCHEMA = "BLOCKED_BY_RAW_SCHEMA"
BLOCKED_NORMALIZATION = "BLOCKED_BY_NORMALIZATION_ERROR"
BLOCKED_OUTPUT_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"
BLOCKED_MOCK_PATH = "BLOCKED_BY_MOCK_PATH_MODIFIED"
BLOCKED_PROMOTION = "BLOCKED_BY_PROMOTION_RULE"
BLOCKED_COVERAGE = "BLOCKED_BY_NORMALIZED_COVERAGE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild long-history isolated real_runtime normalized daily quotes.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--output-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4ba-summary", default=str(PHASE4BA_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = rebuild_phase4bb_long_history_normalized(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        output_format=args.output_format,
        phase4ba_summary_path=Path(args.phase4ba_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def rebuild_phase4bb_long_history_normalized(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    output_format: str = "parquet",
    phase4ba_summary_path: Path = PHASE4BA_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    raw_root = paths.raw_data / "jquants" / "equities_bars_daily"
    response_dir = raw_root / "responses"
    raw_manifest_path = raw_root / "manifest.json"
    isolated_output_path = _isolated_output_path(paths, output_format)
    isolated_manifest_path = _isolated_manifest_path(paths)
    mock_path = paths.raw_normalized_data / "jquants" / "equities_bars_daily"
    mock_hash_before = _tree_hash(mock_path)
    phase4ba_summary = _read_json_optional(phase4ba_summary_path)

    if phase4ba_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_RAW_SCHEMA,
            reason="Phase4-BA summary is missing or not ready for long-history normalized rebuild.",
            paths=paths,
            report_dir=report_dir,
            response_dir=response_dir,
            raw_manifest_path=raw_manifest_path,
            isolated_output_path=isolated_output_path,
            isolated_manifest_path=isolated_manifest_path,
            mock_path=mock_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _is_safe_isolated_output(paths.runtime_dir, isolated_output_path):
        summary = _blocked_summary(
            readiness_status=BLOCKED_OUTPUT_PATH,
            reason="Isolated output path is not under raw_normalized_real_runtime or collides with mock raw_normalized.",
            paths=paths,
            report_dir=report_dir,
            response_dir=response_dir,
            raw_manifest_path=raw_manifest_path,
            isolated_output_path=isolated_output_path,
            isolated_manifest_path=isolated_manifest_path,
            mock_path=mock_path,
        )
        _write_json(summary_path, summary)
        return summary

    raw_records, response_files = _read_raw_response_records(response_dir)
    if not raw_records:
        summary = _blocked_summary(
            readiness_status=BLOCKED_RAW_SCHEMA,
            reason="No raw daily quote records were found in long-history response files.",
            paths=paths,
            report_dir=report_dir,
            response_dir=response_dir,
            raw_manifest_path=raw_manifest_path,
            isolated_output_path=isolated_output_path,
            isolated_manifest_path=isolated_manifest_path,
            mock_path=mock_path,
        )
        _write_json(summary_path, summary)
        return summary

    normalizable_records, missing_price_records, invalid_key_records = _split_raw_records(raw_records)
    if invalid_key_records:
        summary = _blocked_summary(
            readiness_status=BLOCKED_RAW_SCHEMA,
            reason="Raw daily quote records contain missing Date or Code keys.",
            paths=paths,
            report_dir=report_dir,
            response_dir=response_dir,
            raw_manifest_path=raw_manifest_path,
            isolated_output_path=isolated_output_path,
            isolated_manifest_path=isolated_manifest_path,
            mock_path=mock_path,
        )
        summary.update(
            {
                "raw_row_count": len(raw_records),
                "invalid_key_record_count": len(invalid_key_records),
                "price_missing_excluded_count": len(missing_price_records),
            }
        )
        _write_json(summary_path, summary)
        return summary

    normalized_records, normalization_report = normalize_daily_quotes(normalizable_records)
    if normalization_report.error_count > 0 or normalization_report.status == "ERROR":
        summary = _blocked_summary(
            readiness_status=BLOCKED_NORMALIZATION,
            reason="Daily quote normalization produced errors.",
            paths=paths,
            report_dir=report_dir,
            response_dir=response_dir,
            raw_manifest_path=raw_manifest_path,
            isolated_output_path=isolated_output_path,
            isolated_manifest_path=isolated_manifest_path,
            mock_path=mock_path,
        )
        summary.update(
            {
                "raw_row_count": len(raw_records),
                "normalized_row_count": len(normalized_records),
                "normalization_error_count": normalization_report.error_count,
                "price_missing_excluded_count": len(missing_price_records),
                "normalization_report": _compact_normalization_report(normalization_report.to_dict()),
            }
        )
        _write_json(summary_path, summary)
        return summary

    backend = create_storage_backend(output_format)
    backend.write_records(isolated_output_path, normalized_records)
    output_hash = _file_hash(isolated_output_path)
    mock_hash_after = _tree_hash(mock_path)
    mock_path_unchanged = mock_hash_before == mock_hash_after

    stats = _coverage_stats(normalized_records)
    duplicate_count = _duplicate_date_code_count(normalized_records)
    schema_mapping_status = "OK" if normalization_report.validation_status in {"OK", "WARNING"} else "ERROR"
    formal_training_coverage_sufficient = _formal_training_coverage_sufficient(
        stats=stats,
        phase4ba_summary=phase4ba_summary,
        duplicate_count=duplicate_count,
    )

    promotion_status = "not_promoted"
    promotion_performed = False
    reader_switch_performed = False
    readiness_status = _resolve_readiness(
        schema_mapping_status=schema_mapping_status,
        normalization_error_count=normalization_report.error_count,
        duplicate_date_code_count=duplicate_count,
        mock_path_unchanged=mock_path_unchanged,
        promotion_status=promotion_status,
        promotion_performed=promotion_performed,
        reader_switch_performed=reader_switch_performed,
        formal_training_coverage_sufficient=formal_training_coverage_sufficient,
    )

    manifest = _build_manifest(
        raw_records=raw_records,
        normalized_records=normalized_records,
        response_files=response_files,
        raw_manifest_path=raw_manifest_path,
        phase4ba_summary_path=phase4ba_summary_path,
        isolated_output_path=isolated_output_path,
        output_hash=output_hash,
        stats=stats,
        duplicate_count=duplicate_count,
        normalization_report=normalization_report.to_dict(),
        schema_mapping_status=schema_mapping_status,
        mock_path_unchanged=mock_path_unchanged,
        output_format=output_format,
        price_missing_excluded_count=len(missing_price_records),
        formal_training_coverage_sufficient=formal_training_coverage_sufficient,
        phase4ba_summary=phase4ba_summary,
    )
    _write_json(isolated_manifest_path, manifest)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "normalized_rebuild_executed": True,
        "raw_row_count": len(raw_records),
        "normalized_row_count": len(normalized_records),
        "price_missing_excluded_count": len(missing_price_records),
        "normalization_error_count": normalization_report.error_count,
        "invalid_key_record_count": 0,
        "code_count": stats["code_count"],
        "date_min": stats["date_min"],
        "date_max": stats["date_max"],
        "business_day_count": stats["business_day_count"],
        "duplicate_date_code_count": duplicate_count,
        "schema_mapping_status": schema_mapping_status,
        "mock_path_unchanged": mock_path_unchanged,
        "isolated_output_path": str(isolated_output_path),
        "manifest_path": str(isolated_manifest_path),
        "raw_response_dir": str(response_dir),
        "raw_response_file_count": len(response_files),
        "raw_manifest_path": str(raw_manifest_path),
        "phase4ba_summary_path": str(phase4ba_summary_path),
        "data_source_type": "real_runtime",
        "output_format": output_format,
        "normalized_schema_version": NORMALIZED_SCHEMA_VERSION,
        "normalizer_version": "normalize_daily_quotes_v1",
        "promotion_status": promotion_status,
        "promotion_performed": promotion_performed,
        "reader_switch_performed": reader_switch_performed,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "portfolio_auto_update_executed": False,
        "formal_training_coverage_sufficient_after_normalization": formal_training_coverage_sufficient,
        "first_trainable_target_date": phase4ba_summary.get("first_trainable_target_date"),
        "last_label_target_date": phase4ba_summary.get("last_label_target_date"),
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def _resolve_readiness(
    *,
    schema_mapping_status: str,
    normalization_error_count: int,
    duplicate_date_code_count: int,
    mock_path_unchanged: bool,
    promotion_status: str,
    promotion_performed: bool,
    reader_switch_performed: bool,
    formal_training_coverage_sufficient: bool,
) -> str:
    if schema_mapping_status != "OK":
        return BLOCKED_RAW_SCHEMA
    if normalization_error_count:
        return BLOCKED_NORMALIZATION
    if duplicate_date_code_count:
        return BLOCKED_NORMALIZATION
    if not formal_training_coverage_sufficient:
        return BLOCKED_COVERAGE
    if not mock_path_unchanged:
        return BLOCKED_MOCK_PATH
    if promotion_status != "not_promoted" or promotion_performed or reader_switch_performed:
        return BLOCKED_PROMOTION
    return READY


def _read_raw_response_records(response_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    response_files: list[str] = []
    if not response_dir.is_dir():
        return records, response_files
    for response_path in sorted(response_dir.glob("*.json")):
        response_files.append(str(response_path))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        payload = response.get("payload", response)
        rows = _extract_payload_rows(payload)
        for row in rows:
            if isinstance(row, dict):
                record = dict(row)
                record.setdefault("target_date", response.get("date") or record.get("Date"))
                record.setdefault("endpoint", "daily_quotes")
                records.append(record)
    return records, response_files


def _split_raw_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    normalizable: list[dict[str, Any]] = []
    missing_price: list[dict[str, Any]] = []
    invalid_key: list[dict[str, Any]] = []
    for record in records:
        if not (record.get("Date") or record.get("target_date")) or not (record.get("Code") or record.get("code")):
            invalid_key.append(record)
        elif _has_all(record, ADJUSTED_FIELDS) or _has_all(record, UNADJUSTED_FIELDS):
            normalizable.append(record)
        else:
            missing_price.append(record)
    return normalizable, missing_price, invalid_key


def _has_all(record: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(record.get(field) not in (None, "") for field in fields)


def _extract_payload_rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "daily_quotes", "quotes", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _isolated_output_path(paths: RuntimePaths, output_format: str) -> Path:
    return create_storage_backend(output_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _isolated_manifest_path(paths: RuntimePaths) -> Path:
    return paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "manifest.json"


def _is_safe_isolated_output(runtime_dir: Path, output_path: Path) -> bool:
    runtime_root = runtime_dir.resolve()
    isolated_root = (runtime_root / "data" / "raw_normalized_real_runtime").resolve()
    mock_root = (runtime_root / "data" / "raw_normalized").resolve()
    resolved_output = output_path.resolve()
    return _is_relative_to(resolved_output, isolated_root) and not _is_relative_to(resolved_output, mock_root)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _build_manifest(
    *,
    raw_records: list[dict[str, Any]],
    normalized_records: list[dict[str, Any]],
    response_files: list[str],
    raw_manifest_path: Path,
    phase4ba_summary_path: Path,
    isolated_output_path: Path,
    output_hash: str | None,
    stats: dict[str, Any],
    duplicate_count: int,
    normalization_report: dict[str, Any],
    schema_mapping_status: str,
    mock_path_unchanged: bool,
    output_format: str,
    price_missing_excluded_count: int,
    formal_training_coverage_sufficient: bool,
    phase4ba_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "data_source_type": "real_runtime",
        "source_provider": "jquants",
        "source_endpoint": "/v2/equities/bars/daily",
        "source_raw_response_files": response_files,
        "source_raw_response_file_count": len(response_files),
        "source_raw_manifest_path": str(raw_manifest_path),
        "phase4ba_summary_path": str(phase4ba_summary_path),
        "isolated_output_path": str(isolated_output_path),
        "output_format": output_format,
        "output_hash_optional": output_hash,
        "input_hash_optional": _hash_records(raw_records),
        "normalizer_version": "normalize_daily_quotes_v1",
        "schema_version": NORMALIZED_SCHEMA_VERSION,
        "raw_row_count": len(raw_records),
        "normalized_row_count": len(normalized_records),
        "code_count": stats["code_count"],
        "date_min": stats["date_min"],
        "date_max": stats["date_max"],
        "business_day_count": stats["business_day_count"],
        "duplicate_date_code_count": duplicate_count,
        "schema_mapping_status": schema_mapping_status,
        "normalization_error_count": int(normalization_report.get("error_count") or 0),
        "price_missing_excluded_count": price_missing_excluded_count,
        "normalization_report": _compact_normalization_report(normalization_report),
        "formal_training_coverage_sufficient_after_normalization": formal_training_coverage_sufficient,
        "first_trainable_target_date": phase4ba_summary.get("first_trainable_target_date"),
        "last_label_target_date": phase4ba_summary.get("last_label_target_date"),
        "promotion_status": "not_promoted",
        "promotion_performed": False,
        "reader_switch_performed": False,
        "mock_path_unchanged": mock_path_unchanged,
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }


def _coverage_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(record.get("Date") or "") for record in records if record.get("Date")})
    codes = sorted({str(record.get("Code") or "") for record in records if record.get("Code")})
    return {
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "business_day_count": len(dates),
        "code_count": len(codes),
    }


def _duplicate_date_code_count(records: list[dict[str, Any]]) -> int:
    keys = [(str(record.get("Date")), str(record.get("Code"))) for record in records if record.get("Date") and record.get("Code")]
    return sum(count - 1 for count in Counter(keys).values() if count > 1)


def _formal_training_coverage_sufficient(*, stats: dict[str, Any], phase4ba_summary: dict[str, Any], duplicate_count: int) -> bool:
    return (
        phase4ba_summary.get("formal_training_coverage_sufficient") is True
        and stats["business_day_count"] >= int(phase4ba_summary.get("fetched_business_day_count") or 0)
        and stats["date_min"] == phase4ba_summary.get("fetched_date_min")
        and stats["date_max"] == phase4ba_summary.get("fetched_date_max")
        and duplicate_count == 0
    )


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    paths: RuntimePaths,
    report_dir: Path,
    response_dir: Path,
    raw_manifest_path: Path,
    isolated_output_path: Path,
    isolated_manifest_path: Path,
    mock_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "normalized_rebuild_executed": False,
        "raw_row_count": 0,
        "normalized_row_count": 0,
        "price_missing_excluded_count": 0,
        "normalization_error_count": 0,
        "code_count": 0,
        "date_min": None,
        "date_max": None,
        "business_day_count": 0,
        "duplicate_date_code_count": 0,
        "schema_mapping_status": "SKIPPED",
        "promotion_status": "not_promoted",
        "promotion_performed": False,
        "reader_switch_performed": False,
        "mock_path_unchanged": True,
        "isolated_output_path": str(isolated_output_path),
        "manifest_path": str(isolated_manifest_path),
        "raw_response_dir": str(response_dir),
        "raw_manifest_path": str(raw_manifest_path),
        "mock_normalized_path": str(mock_path),
        "data_source_type": "real_runtime",
        "feature_generation_executed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "portfolio_auto_update_executed": False,
        "formal_training_coverage_sufficient_after_normalization": False,
        "first_trainable_target_date": None,
        "last_label_target_date": None,
        "recommended_next_action": "Fix the blocking condition, then rerun Phase4-BB normalized rebuild.",
        "summary_path": str(report_dir / SUMMARY_PATH.name),
        "runtime_dir": str(paths.runtime_dir),
    }


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-BC Long History Feature Regeneration on isolated real_runtime normalized history; do not train yet."
    return "Fix the normalized rebuild blocker before Phase4-BC."


def _compact_normalization_report(report: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "endpoint_name",
        "input_record_count",
        "output_record_count",
        "adjusted_count",
        "unadjusted_count",
        "error_count",
        "warning_count",
        "duplicate_key_count",
        "status",
        "sample_errors",
        "sample_warnings",
        "field_mapping",
        "validation_status",
    )
    compact = {key: report.get(key) for key in keys}
    compact["affected_date_count"] = len(report.get("affected_dates") or [])
    compact["affected_code_count"] = len(report.get("affected_codes") or [])
    return compact


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_records(records: list[dict[str, Any]]) -> str | None:
    if not records:
        return None
    payload = json.dumps(records, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.is_file():
        return _file_hash(path)
    digest = hashlib.sha256()
    files = sorted(child for child in path.rglob("*") if child.is_file())
    if not files:
        return None
    for file_path in files:
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update((_file_hash(file_path) or "").encode("utf-8"))
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
