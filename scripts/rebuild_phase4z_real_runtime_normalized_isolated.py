#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
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
    NORMALIZED_SCHEMA_VERSION,
    normalize_daily_quotes,
)
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.data_store.manifest import manifest_path  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4z_real_runtime_normalized_isolated_summary.json")
READY = "ISOLATED_REAL_RUNTIME_NORMALIZED_READY"
BLOCKED_RAW = "BLOCKED_BY_MISSING_RAW"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA_MAPPING"
BLOCKED_WRITE = "BLOCKED_BY_WRITE_FAILURE"
BLOCKED_MANIFEST = "BLOCKED_BY_MANIFEST"
BLOCKED_OVERWRITE = "BLOCKED_BY_MOCK_OVERWRITE_RISK"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild real_runtime normalized daily quotes into an isolated no-promotion path.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("auto", "jsonl", "parquet"), default="auto")
    parser.add_argument("--output-format", choices=("parquet", "jsonl"), default="parquet")
    args = parser.parse_args(argv)
    summary = rebuild_isolated_real_runtime_normalized(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        output_format=args.output_format,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"OK", "BLOCKED"} else 1


def rebuild_isolated_real_runtime_normalized(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "auto",
    output_format: str = "parquet",
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    raw_path, raw_format = _resolve_raw_path(paths, input_format)
    default_mock_path = create_storage_backend(output_format).path_for(
        paths.raw_normalized_data / "jquants" / "equities_bars_daily" / "data"
    )
    before_hash = _file_hash(default_mock_path)
    summary_path = Path(report_dir) / SUMMARY_PATH.name
    if raw_path is None or raw_format is None or not raw_path.exists():
        summary = _base_summary(
            status="BLOCKED",
            coverage_status=BLOCKED_RAW,
            runtime_dir=paths.runtime_dir,
            report_dir=report_dir,
            raw_path=None,
            isolated_output_path=_isolated_output_path(paths, output_format),
            isolated_manifest_path=_isolated_manifest_path(paths),
            default_mock_path=default_mock_path,
        )
        _write_json(summary_path, summary)
        return summary
    source_manifest_path = manifest_path(paths.raw_data)
    if not source_manifest_path.exists():
        summary = _base_summary(
            status="BLOCKED",
            coverage_status=BLOCKED_MANIFEST,
            runtime_dir=paths.runtime_dir,
            report_dir=report_dir,
            raw_path=raw_path,
            isolated_output_path=_isolated_output_path(paths, output_format),
            isolated_manifest_path=_isolated_manifest_path(paths),
            default_mock_path=default_mock_path,
        )
        _write_json(summary_path, summary)
        return summary
    try:
        raw_records = create_storage_backend(raw_format).read_records(raw_path)
        normalized_records, normalization_report = normalize_daily_quotes(raw_records)
    except Exception as exc:  # pragma: no cover - defensive execution path
        summary = _base_summary(
            status="BLOCKED",
            coverage_status=BLOCKED_SCHEMA,
            runtime_dir=paths.runtime_dir,
            report_dir=report_dir,
            raw_path=raw_path,
            isolated_output_path=_isolated_output_path(paths, output_format),
            isolated_manifest_path=_isolated_manifest_path(paths),
            default_mock_path=default_mock_path,
        )
        summary["error_message"] = f"normalization failed: {type(exc).__name__}"
        _write_json(summary_path, summary)
        return summary
    isolated_output = _isolated_output_path(paths, output_format)
    isolated_manifest = _isolated_manifest_path(paths)
    if isolated_output == default_mock_path:
        summary = _base_summary(
            status="BLOCKED",
            coverage_status=BLOCKED_OVERWRITE,
            runtime_dir=paths.runtime_dir,
            report_dir=report_dir,
            raw_path=raw_path,
            isolated_output_path=isolated_output,
            isolated_manifest_path=isolated_manifest,
            default_mock_path=default_mock_path,
        )
        _write_json(summary_path, summary)
        return summary
    try:
        create_storage_backend(output_format).write_records(isolated_output, normalized_records)
        output_hash = _file_hash(isolated_output)
        manifest = _build_manifest(
            raw_path=raw_path,
            source_manifest_path=source_manifest_path,
            normalized_records=normalized_records,
            input_hash=_hash_records(raw_records),
            output_hash=output_hash,
        )
        _write_json(isolated_manifest, manifest)
    except Exception as exc:  # pragma: no cover - defensive execution path
        summary = _base_summary(
            status="BLOCKED",
            coverage_status=BLOCKED_WRITE,
            runtime_dir=paths.runtime_dir,
            report_dir=report_dir,
            raw_path=raw_path,
            isolated_output_path=isolated_output,
            isolated_manifest_path=isolated_manifest,
            default_mock_path=default_mock_path,
        )
        summary["error_message"] = f"isolated write failed: {type(exc).__name__}"
        _write_json(summary_path, summary)
        return summary
    after_hash = _file_hash(default_mock_path)
    mock_unchanged = before_hash == after_hash
    stats = _coverage_stats(normalized_records)
    coverage_status = (
        READY
        if mock_unchanged and normalized_records
        else BLOCKED_OVERWRITE
    )
    summary = {
        "status": "OK" if coverage_status == READY else "BLOCKED",
        "coverage_status": coverage_status,
        "data_source_type": "real_runtime",
        "api_call_performed": False,
        "isolated_output_path": str(isolated_output),
        "isolated_manifest_path": str(isolated_manifest),
        "default_mock_path": str(default_mock_path),
        "default_mock_path_unchanged": mock_unchanged,
        "mock_history_overwritten": not mock_unchanged,
        "promotion_performed": False,
        "promotion_status": "not_promoted",
        "reader_switch_performed": False,
        "row_count": len(normalized_records),
        "code_count": stats["code_count"],
        "date_min": stats["date_min"],
        "date_max": stats["date_max"],
        "business_day_count": stats["business_day_count"],
        "per_code_row_count_min": stats["per_code_row_count_min"],
        "per_code_row_count_max": stats["per_code_row_count_max"],
        "per_code_row_count_mean": stats["per_code_row_count_mean"],
        "schema_mapping_status": "OK" if normalization_report.validation_status in {"OK", "WARNING"} else "ERROR",
        "normalization_status": normalization_report.status,
        "normalization_error_count": normalization_report.error_count,
        "coverage_status_detail": _coverage_detail(stats["business_day_count"]),
        "manifest": manifest,
        "recommended_next_action": "run Phase4-Z audit, then coverage audit; do not promote until 60-day coverage is sufficient",
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def _resolve_raw_path(paths: RuntimePaths, input_format: str) -> tuple[Path | None, str | None]:
    formats = ("parquet", "jsonl") if input_format == "auto" else (input_format,)
    base = paths.raw_data / "jquants" / "equities_bars_daily" / "data"
    for fmt in formats:
        path = create_storage_backend(fmt).path_for(base)
        if path.exists():
            return path, fmt
    return None, None


def _isolated_output_path(paths: RuntimePaths, output_format: str) -> Path:
    return create_storage_backend(output_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _isolated_manifest_path(paths: RuntimePaths) -> Path:
    return paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "manifest.json"


def _build_manifest(
    *,
    raw_path: Path,
    source_manifest_path: Path,
    normalized_records: list[dict[str, Any]],
    input_hash: str | None,
    output_hash: str | None,
) -> dict[str, Any]:
    stats = _coverage_stats(normalized_records)
    return {
        "data_source_type": "real_runtime",
        "source_provider": "jquants",
        "api_call_performed": False,
        "source_raw_path": str(raw_path),
        "source_raw_manifest_path": str(source_manifest_path),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "normalizer_version": "normalize_daily_quotes_v1",
        "schema_version": NORMALIZED_SCHEMA_VERSION,
        "row_count": len(normalized_records),
        "code_count": stats["code_count"],
        "date_min": stats["date_min"],
        "date_max": stats["date_max"],
        "input_hash_optional": input_hash,
        "output_hash_optional": output_hash,
        "promotion_status": "not_promoted",
        "mock_history_overwritten": False,
    }


def _coverage_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(record.get("Date") or "") for record in records if record.get("Date")})
    codes = sorted({str(record.get("Code") or "") for record in records if record.get("Code")})
    counts = Counter(str(record.get("Code") or "") for record in records if record.get("Code"))
    values = [counts[code] for code in codes]
    return {
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "business_day_count": len(dates),
        "code_count": len(codes),
        "per_code_row_count_min": min(values) if values else 0,
        "per_code_row_count_max": max(values) if values else 0,
        "per_code_row_count_mean": round(mean(values), 4) if values else 0,
    }


def _coverage_detail(business_day_count: int) -> str:
    if business_day_count >= 60:
        return "sufficient_for_60_day_candidate_feature_generation"
    return "isolated rebuild success but insufficient for 60-day Candidate feature generation"


def _base_summary(
    *,
    status: str,
    coverage_status: str,
    runtime_dir: Path,
    report_dir: Path | str,
    raw_path: Path | None,
    isolated_output_path: Path,
    isolated_manifest_path: Path,
    default_mock_path: Path,
) -> dict[str, Any]:
    summary_path = Path(report_dir) / SUMMARY_PATH.name
    return {
        "status": status,
        "coverage_status": coverage_status,
        "data_source_type": "real_runtime",
        "api_call_performed": False,
        "isolated_output_path": str(isolated_output_path),
        "isolated_manifest_path": str(isolated_manifest_path),
        "default_mock_path": str(default_mock_path),
        "default_mock_path_unchanged": True,
        "mock_history_overwritten": False,
        "promotion_performed": False,
        "promotion_status": "not_promoted",
        "reader_switch_performed": False,
        "raw_input_path": str(raw_path) if raw_path else None,
        "row_count": 0,
        "code_count": 0,
        "date_min": None,
        "date_max": None,
        "business_day_count": 0,
        "per_code_row_count_min": 0,
        "per_code_row_count_max": 0,
        "per_code_row_count_mean": 0,
        "schema_mapping_status": "SKIPPED",
        "coverage_status_detail": "not rebuilt",
        "recommended_next_action": "fix isolated rebuild blocker before retrying",
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
