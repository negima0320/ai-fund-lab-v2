#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai.leakage_audit import audit_feature_table  # noqa: E402
from ai_fund_lab_v2.candidate_ai.paths import CandidateAIRuntimePaths  # noqa: E402
from ai_fund_lab_v2.candidate_ai.validation import validate_feature_table  # noqa: E402
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-AK"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ak_real_runtime_feature_generation_summary.json")
PHASE4AJ_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aj_real_runtime_normalized_summary.json")

READY_INPUT = "READY_FOR_REAL_RUNTIME_FEATURE_GENERATION"
READY = "READY_FOR_LABEL_GENERATION"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA_VALIDATION"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_GENERATION = "BLOCKED_BY_FEATURE_GENERATION"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

FEATURE_VERSION = "candidate_features_real_runtime_v1"
FEATURE_SET_NAME = "candidate_real_runtime_price_volume_v1"
SCHEMA_VERSION = "candidate_feature_schema_v1"
MIN_LOOKBACK_ROWS = 60

REQUIRED_AK_FEATURE_COLUMNS = (
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "price_momentum_return_60d",
    "volume_momentum_ratio_5d",
    "volume_momentum_ratio_1d_20d",
    "volatility_return_std_20d",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "trend_ma_20_60_ratio",
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_history",
    "missing_flags_price",
    "missing_flags_volume",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-AK real_runtime Candidate features from isolated normalized data.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4aj-summary", default=str(PHASE4AJ_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4ak_real_runtime_features(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        phase4aj_summary_path=Path(args.phase4aj_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4ak_real_runtime_features(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "parquet",
    phase4aj_summary_path: Path = PHASE4AJ_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    candidate_paths = CandidateAIRuntimePaths(paths)
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    phase4aj_summary = _read_json_optional(phase4aj_summary_path)
    source_path = _real_runtime_normalized_path(paths, input_format)

    if phase4aj_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Phase4-AJ summary is missing or not ready for real_runtime feature generation.",
            paths=paths,
            source_path=source_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    if not _is_safe_output_root(paths.runtime_dir, candidate_paths):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Candidate AI output paths are not under .runtime/candidate_ai.",
            paths=paths,
            source_path=source_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    if not source_path.is_file():
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Isolated real_runtime normalized input file is missing.",
            paths=paths,
            source_path=source_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    normalized_records = create_storage_backend(input_format).read_records(source_path)
    if not _input_matches_phase4aj_summary(normalized_records, phase4aj_summary):
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Isolated real_runtime normalized input does not match the Phase4-AJ summary. Re-run the intended normalized rebuild explicitly before feature generation.",
            paths=paths,
            source_path=source_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not normalized_records:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Isolated real_runtime normalized input is empty.",
            paths=paths,
            source_path=source_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_rows = build_real_runtime_feature_rows(
        normalized_records,
        source_snapshot_id=f"phase4aj:{phase4aj_summary.get('isolated_manifest_path') or source_path}",
    )
    validation = validate_feature_table(feature_rows)
    audit = audit_feature_table(feature_rows)
    feature_stats = _feature_statistics(feature_rows)

    forbidden_feature_detected = audit.forbidden_feature_detected
    future_column_detected = audit.future_column_detected
    label_column_detected = audit.label_column_detected
    schema_validation_status = "OK" if validation.is_valid and _required_features_present(feature_rows) else "ERROR"
    leakage_audit_status = "OK" if audit.status == "OK" and not forbidden_feature_detected else "ERROR"
    readiness_status = _resolve_readiness(
        schema_validation_status=schema_validation_status,
        leakage_audit_status=leakage_audit_status,
        forbidden_feature_detected=forbidden_feature_detected,
        future_column_detected=future_column_detected,
        label_column_detected=label_column_detected,
    )

    candidate_paths.ensure_dirs()
    as_of_date = _latest_date(feature_rows)
    feature_path = candidate_paths.features / f"phase4ak_real_runtime_features_{as_of_date}.json"
    manifest_path = candidate_paths.manifests / f"phase4ak_real_runtime_features_manifest_{as_of_date}.json"
    audit_path = candidate_paths.audit / f"phase4ak_real_runtime_features_audit_{as_of_date}.json"

    audit_payload = {
        **audit.to_dict(),
        "schema_validation_status": schema_validation_status,
        "leakage_audit_status": leakage_audit_status,
        "validation_messages": list(validation.messages),
        "required_ak_feature_columns": list(REQUIRED_AK_FEATURE_COLUMNS),
        "feature_statistics": feature_stats,
    }
    manifest_payload = _build_manifest(
        feature_rows=feature_rows,
        normalized_records=normalized_records,
        source_path=source_path,
        phase4aj_summary_path=phase4aj_summary_path,
        feature_path=feature_path,
        manifest_path=manifest_path,
        audit_path=audit_path,
        audit_payload=audit_payload,
        phase4aj_summary=phase4aj_summary,
    )
    _write_json(feature_path, {"rows": feature_rows})
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)

    date_min, date_max, business_day_count, code_count = _normalized_coverage(normalized_records)
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "feature_generation_executed": True,
        "schema_validation_status": schema_validation_status,
        "leakage_audit_status": leakage_audit_status,
        "raw_row_count": int(phase4aj_summary.get("raw_row_count") or 0),
        "normalized_row_count": len(normalized_records),
        "feature_row_count": len(feature_rows),
        "eligible_count": audit.eligible_count,
        "excluded_count": audit.excluded_count,
        "business_day_count": business_day_count,
        "code_count": code_count,
        "date_min": date_min,
        "date_max": date_max,
        "feature_column_count": feature_stats["feature_column_count"],
        "null_count": feature_stats["null_count"],
        "forbidden_feature_detected": forbidden_feature_detected,
        "future_column_detected": future_column_detected,
        "label_column_detected": label_column_detected,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "label_generation_executed": False,
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "feature_output_path": str(feature_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "input_path": str(source_path),
        "feature_version": FEATURE_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "excluded_reason_counts": audit.excluded_reason_counts,
        "recommended_next_action": "Phase4-AL Label Generation: create future labels in a physically separate label table; do not mix labels into features.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_real_runtime_feature_rows(
    normalized_records: list[dict[str, Any]],
    *,
    source_snapshot_id: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in normalized_records:
        date_value = str(record.get("Date") or record.get("target_date") or "")
        code = str(record.get("Code") or record.get("code") or "").strip()
        if not date_value or not code:
            continue
        grouped.setdefault(code, []).append(dict(record))
    latest_date = max(str(record.get("Date") or record.get("target_date")) for record in normalized_records)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    feature_rows: list[dict[str, Any]] = []
    for code, rows in sorted(grouped.items()):
        visible_rows = sorted(
            [row for row in rows if str(row.get("Date") or row.get("target_date")) <= latest_date],
            key=lambda row: str(row.get("Date") or row.get("target_date")),
        )
        feature_rows.append(
            _build_feature_row(
                code=code,
                rows=visible_rows,
                as_of_date=latest_date,
                source_snapshot_id=source_snapshot_id,
                created_at=created_at,
            )
        )
    return feature_rows


def _build_feature_row(
    *,
    code: str,
    rows: list[dict[str, Any]],
    as_of_date: str,
    source_snapshot_id: str,
    created_at: str,
) -> dict[str, Any]:
    data_start_date = str(rows[0].get("Date")) if rows else None
    data_end_date = str(rows[-1].get("Date")) if rows else None
    has_enough_history = len(rows) >= MIN_LOOKBACK_ROWS
    has_price = all(_is_number(row.get("Close")) for row in rows[-MIN_LOOKBACK_ROWS:])
    has_volume = all(_is_number(row.get("Volume")) for row in rows[-MIN_LOOKBACK_ROWS:])
    universe_eligible = has_enough_history and has_price and has_volume and data_end_date == as_of_date
    excluded_reason = _excluded_reason(
        has_enough_history=has_enough_history,
        has_price=has_price,
        has_volume=has_volume,
        data_end_date=data_end_date,
        as_of_date=as_of_date,
    )
    base = {
        "as_of_date": as_of_date,
        "target_date": as_of_date,
        "code": code,
        "feature_version": FEATURE_VERSION,
        "source_snapshot_id": source_snapshot_id,
        "feature_set_name": FEATURE_SET_NAME,
        "created_at": created_at,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        "universe_eligible": universe_eligible,
        "excluded_reason": excluded_reason,
        "missing_flags_insufficient_history": not has_enough_history,
        "missing_flags_price": not has_price,
        "missing_flags_volume": not has_volume,
    }
    if not universe_eligible:
        base.update({feature: None for feature in REQUIRED_AK_FEATURE_COLUMNS if not feature.startswith("missing_flags_")})
        return base

    window = rows[-MIN_LOOKBACK_ROWS:]
    closes = [_to_float(row.get("Close")) for row in window]
    volumes = [_to_float(row.get("Volume")) for row in window]
    daily_returns = [_safe_ratio(closes[index], closes[index - 1]) for index in range(1, len(closes))]
    ma_5 = mean(closes[-5:])
    ma_20 = mean(closes[-20:])
    ma_60 = mean(closes[-60:])
    base.update(
        {
            "price_momentum_return_5d": _round(_safe_ratio(closes[-1], closes[-6])),
            "price_momentum_return_20d": _round(_safe_ratio(closes[-1], closes[-21])),
            "price_momentum_return_60d": _round(_safe_ratio(closes[-1], closes[0])),
            "volume_momentum_ratio_5d": _round(_safe_divide(mean(volumes[-5:]), mean(volumes[-20:]))),
            "volume_momentum_ratio_1d_20d": _round(_safe_divide(volumes[-1], mean(volumes[-20:]))),
            "volatility_return_std_20d": _round(pstdev(daily_returns[-20:])),
            "trend_close_over_ma_20d": _round(_safe_ratio(closes[-1], ma_20)),
            "trend_ma_5_20_ratio": _round(_safe_ratio(ma_5, ma_20)),
            "trend_ma_20_60_ratio": _round(_safe_ratio(ma_20, ma_60)),
            "liquidity_avg_volume_20d": _round(mean(volumes[-20:])),
        }
    )
    return base


def _excluded_reason(
    *,
    has_enough_history: bool,
    has_price: bool,
    has_volume: bool,
    data_end_date: str | None,
    as_of_date: str,
) -> str:
    reasons = []
    if not has_enough_history:
        reasons.append("insufficient_history")
    if not has_price:
        reasons.append("price_data_missing")
    if not has_volume:
        reasons.append("volume_data_missing")
    if data_end_date != as_of_date:
        reasons.append("latest_date_missing")
    return "|".join(reasons)


def _feature_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({column for row in rows for column in row.keys()})
    metadata = {
        "as_of_date",
        "target_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "feature_set_name",
        "created_at",
        "data_start_date",
        "data_end_date",
        "universe_eligible",
        "excluded_reason",
    }
    feature_columns = [column for column in columns if column not in metadata]
    null_count = sum(1 for row in rows for column in columns if row.get(column) is None)
    numeric_stats: dict[str, dict[str, float | int | None]] = {}
    for column in feature_columns:
        values = [_to_float(row.get(column)) for row in rows if _is_number(row.get(column))]
        if values:
            numeric_stats[column] = {
                "count": len(values),
                "min": _round(min(values)),
                "max": _round(max(values)),
                "mean": _round(mean(values)),
            }
        else:
            numeric_stats[column] = {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "feature_column_count": len(feature_columns),
        "columns": columns,
        "feature_columns": feature_columns,
        "null_count": null_count,
        "numeric_stats": numeric_stats,
    }


def _build_manifest(
    *,
    feature_rows: list[dict[str, Any]],
    normalized_records: list[dict[str, Any]],
    source_path: Path,
    phase4aj_summary_path: Path,
    feature_path: Path,
    manifest_path: Path,
    audit_path: Path,
    audit_payload: dict[str, Any],
    phase4aj_summary: dict[str, Any],
) -> dict[str, Any]:
    date_min, date_max, business_day_count, code_count = _normalized_coverage(normalized_records)
    return {
        "phase": PHASE,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "feature_version": FEATURE_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "schema_version": SCHEMA_VERSION,
        "data_source_type": "real_runtime",
        "input_sources": ["daily_quotes_normalized_real_runtime"],
        "input_path": str(source_path),
        "phase4aj_summary_path": str(phase4aj_summary_path),
        "phase4aj_readiness_status": phase4aj_summary.get("readiness_status"),
        "source_snapshot_id": feature_rows[0].get("source_snapshot_id") if feature_rows else None,
        "as_of_date": date_max,
        "target_date": date_max,
        "date_min": date_min,
        "date_max": date_max,
        "business_day_count": business_day_count,
        "code_count": code_count,
        "row_count": len(feature_rows),
        "eligible_count": audit_payload.get("eligible_count"),
        "excluded_count": audit_payload.get("excluded_count"),
        "output_path": str(feature_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "schema_validation_status": audit_payload.get("schema_validation_status"),
        "leakage_audit_status": audit_payload.get("leakage_audit_status"),
        "promotion_performed": False,
        "reader_switch_performed": False,
        "label_generation_executed": False,
        "training_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }


def _resolve_readiness(
    *,
    schema_validation_status: str,
    leakage_audit_status: str,
    forbidden_feature_detected: bool,
    future_column_detected: bool,
    label_column_detected: bool,
) -> str:
    if schema_validation_status != "OK":
        return BLOCKED_SCHEMA
    if leakage_audit_status != "OK" or forbidden_feature_detected or future_column_detected or label_column_detected:
        return BLOCKED_LEAKAGE
    return READY


def _required_features_present(rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return False
    columns = set(rows[0].keys())
    return all(column in columns for column in REQUIRED_AK_FEATURE_COLUMNS) and "universe_eligible" in columns and "excluded_reason" in columns


def _normalized_coverage(records: list[dict[str, Any]]) -> tuple[str | None, str | None, int, int]:
    dates = sorted({str(record.get("Date") or record.get("target_date") or "") for record in records if record.get("Date") or record.get("target_date")})
    codes = {str(record.get("Code") or record.get("code") or "") for record in records if record.get("Code") or record.get("code")}
    return (dates[0] if dates else None, dates[-1] if dates else None, len(dates), len(codes))


def _input_matches_phase4aj_summary(records: list[dict[str, Any]], phase4aj_summary: dict[str, Any]) -> bool:
    if not records:
        return False
    date_min, date_max, business_day_count, code_count = _normalized_coverage(records)
    expected_rows = int(phase4aj_summary.get("normalized_row_count") or 0)
    expected_business_days = int(phase4aj_summary.get("business_day_count") or 0)
    expected_date_min = phase4aj_summary.get("date_min")
    expected_date_max = phase4aj_summary.get("date_max")
    return (
        len(records) == expected_rows
        and business_day_count == expected_business_days
        and date_min == expected_date_min
        and date_max == expected_date_max
        and code_count > 0
    )


def _latest_date(rows: list[dict[str, Any]]) -> str:
    dates = [str(row.get("as_of_date") or "") for row in rows if row.get("as_of_date")]
    return max(dates) if dates else "unknown"


def _real_runtime_normalized_path(paths: RuntimePaths, input_format: str) -> Path:
    return create_storage_backend(input_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _is_safe_output_root(runtime_dir: Path, candidate_paths: CandidateAIRuntimePaths) -> bool:
    root = runtime_dir.resolve()
    expected = (root / "candidate_ai").resolve()
    for path in (candidate_paths.features, candidate_paths.manifests, candidate_paths.audit):
        try:
            path.resolve().relative_to(expected)
        except ValueError:
            return False
    return True


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    paths: RuntimePaths,
    source_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "feature_generation_executed": False,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "raw_row_count": 0,
        "normalized_row_count": 0,
        "feature_row_count": 0,
        "eligible_count": 0,
        "excluded_count": 0,
        "business_day_count": 0,
        "code_count": 0,
        "date_min": None,
        "date_max": None,
        "feature_column_count": 0,
        "null_count": 0,
        "forbidden_feature_detected": False,
        "future_column_detected": False,
        "label_column_detected": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "label_generation_executed": False,
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "input_path": str(source_path),
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the blocking condition, then rerun Phase4-AK.",
        "summary_path": str(summary_path),
    }


def _is_number(value: Any) -> bool:
    if value is None or value == "":
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return not math.isnan(number)


def _to_float(value: Any) -> float:
    return float(value)


def _safe_ratio(current: float, previous: float) -> float:
    return _safe_divide(current, previous) - 1.0


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _round(value: float) -> float:
    return round(value, 6)


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
