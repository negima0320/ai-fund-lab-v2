#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai.schemas import (  # noqa: E402
    ALLOWED_FEATURE_PREFIXES,
    OPTIONAL_FEATURE_METADATA_COLUMNS,
    REQUIRED_FEATURE_COLUMNS,
)
from ai_fund_lab_v2.candidate_ai.validation import is_forbidden_column  # noqa: E402
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_phase4ak_real_runtime_features import (  # noqa: E402
    FEATURE_SET_NAME,
    FEATURE_VERSION,
    REQUIRED_AK_FEATURE_COLUMNS,
    SCHEMA_VERSION,
)

PHASE = "Phase4-BC"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json")
PHASE4BB_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bb_long_history_normalized_summary.json")

READY_INPUT = "READY_FOR_LONG_HISTORY_FEATURE_REGENERATION"
READY = "READY_FOR_LONG_HISTORY_LABEL_REGENERATION"
BLOCKED_GENERATION = "BLOCKED_BY_FEATURE_GENERATION"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA_VALIDATION"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_QUALITY = "BLOCKED_BY_FEATURE_QUALITY_GATE"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

TRAIN_START = "2021-09-09"
TRAIN_END = "2024-12-31"
VALIDATION_START = "2025-01-01"
VALIDATION_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-15"

HIGH_NULL_THRESHOLD = 0.5
NEAR_CONSTANT_THRESHOLD = 0.995
MIN_LOOKBACK_ROWS = 60


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-BC long-history Candidate features.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--output-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4bb-summary", default=str(PHASE4BB_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4bc_long_history_features(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        output_format=args.output_format,
        phase4bb_summary_path=Path(args.phase4bb_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4bc_long_history_features(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "parquet",
    output_format: str = "parquet",
    phase4bb_summary_path: Path = PHASE4BB_SUMMARY_PATH,
) -> dict[str, Any]:
    import pandas as pd

    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    bb_summary = _read_json_optional(phase4bb_summary_path)
    normalized_path = _real_runtime_normalized_path(paths, input_format)
    feature_root = paths.runtime_dir / "candidate_ai" / "features"
    manifest_root = paths.runtime_dir / "candidate_ai" / "manifests"
    audit_root = paths.runtime_dir / "candidate_ai" / "audit"

    if bb_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Phase4-BB summary is missing or not ready for long-history feature regeneration.",
            paths=paths,
            summary_path=summary_path,
            normalized_path=normalized_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _safe_candidate_output_paths(paths.runtime_dir, feature_root, manifest_root, audit_root):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Candidate AI output paths are not under .runtime/candidate_ai.",
            paths=paths,
            summary_path=summary_path,
            normalized_path=normalized_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not normalized_path.is_file():
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Long-history real_runtime normalized input is missing.",
            paths=paths,
            summary_path=summary_path,
            normalized_path=normalized_path,
        )
        _write_json(summary_path, summary)
        return summary

    normalized = _read_normalized_frame(normalized_path, input_format)
    if normalized.empty:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Long-history real_runtime normalized input is empty.",
            paths=paths,
            summary_path=summary_path,
            normalized_path=normalized_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_frame = build_long_history_feature_frame(
        normalized,
        source_snapshot_id=f"phase4bb:{bb_summary.get('manifest_path') or normalized_path}",
    )
    schema_validation = validate_long_history_feature_schema(feature_frame)
    leakage_audit = audit_long_history_feature_leakage(feature_frame)
    feature_quality = compute_feature_quality_gate(feature_frame)
    readiness_status = _resolve_readiness(
        schema_validation_status=schema_validation["status"],
        leakage_audit_status=leakage_audit["status"],
        feature_quality_status=feature_quality["status"],
        future_column_detected=leakage_audit["future_column_detected"],
        label_column_detected=leakage_audit["label_column_detected"],
        forbidden_feature_detected=leakage_audit["forbidden_feature_detected"],
    )

    target_dates = sorted(feature_frame["target_date"].dropna().astype(str).unique().tolist())
    target_date_min = target_dates[0] if target_dates else None
    target_date_max = target_dates[-1] if target_dates else None
    suffix = f"{target_date_min or 'none'}_{target_date_max or 'none'}"
    feature_path = _feature_output_path(feature_root, output_format, suffix)
    manifest_path = manifest_root / f"phase4bc_long_history_features_manifest_{suffix}.json"
    audit_path = audit_root / f"phase4bc_long_history_features_audit_{suffix}.json"

    feature_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    audit_root.mkdir(parents=True, exist_ok=True)
    _write_feature_frame(feature_path, feature_frame, output_format)

    audit_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "schema_validation": schema_validation,
        "leakage_audit": leakage_audit,
        "feature_quality_gate": feature_quality,
        "split_ranges": _split_ranges(),
    }
    manifest_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "feature_version": FEATURE_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "schema_version": SCHEMA_VERSION,
        "data_source_type": "real_runtime",
        "input_sources": ["daily_quotes_normalized_real_runtime_long_history"],
        "normalized_input_path": str(normalized_path),
        "phase4bb_summary_path": str(phase4bb_summary_path),
        "phase4bb_readiness_status": bb_summary.get("readiness_status"),
        "source_snapshot_id": f"phase4bb:{bb_summary.get('manifest_path') or normalized_path}",
        "target_date_min": target_date_min,
        "target_date_max": target_date_max,
        "target_date_count": len(target_dates),
        "row_count": int(len(feature_frame)),
        "eligible_count": int(feature_frame["universe_eligible"].sum()),
        "excluded_count": int((~feature_frame["universe_eligible"]).sum()),
        "output_path": str(feature_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "schema_validation_status": schema_validation["status"],
        "leakage_audit_status": leakage_audit["status"],
        "feature_quality_gate_status": feature_quality["status"],
        "promotion_performed": False,
        "reader_switch_performed": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)

    quality_train = feature_quality["splits"]["train"]
    quality_validation = feature_quality["splits"]["validation"]
    quality_test = feature_quality["splits"]["test"]
    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "feature_generation_executed": True,
        "normalized_row_count": int(len(normalized)),
        "feature_row_count": int(len(feature_frame)),
        "eligible_count": int(feature_frame["universe_eligible"].sum()),
        "excluded_count": int((~feature_frame["universe_eligible"]).sum()),
        "code_count": int(feature_frame["code"].nunique()),
        "target_date_min": target_date_min,
        "target_date_max": target_date_max,
        "target_date_count": len(target_dates),
        "feature_column_count": len(_feature_columns(feature_frame)),
        "schema_validation_status": schema_validation["status"],
        "leakage_audit_status": leakage_audit["status"],
        "forbidden_feature_detected": leakage_audit["forbidden_feature_detected"],
        "future_column_detected": leakage_audit["future_column_detected"],
        "label_column_detected": leakage_audit["label_column_detected"],
        "all_null_feature_count_train": quality_train["all_null_feature_count"],
        "constant_feature_count_train": quality_train["constant_feature_count"],
        "near_constant_feature_count_train": quality_train["near_constant_feature_count"],
        "high_null_feature_count_train": quality_train["high_null_feature_count"],
        "feature_non_null_rate_train": quality_train["feature_non_null_rate"],
        "feature_variance_available_train": quality_train["feature_variance_available"],
        "all_null_feature_count_validation": quality_validation["all_null_feature_count"],
        "constant_feature_count_validation": quality_validation["constant_feature_count"],
        "high_null_feature_count_validation": quality_validation["high_null_feature_count"],
        "all_null_feature_count_test": quality_test["all_null_feature_count"],
        "constant_feature_count_test": quality_test["constant_feature_count"],
        "high_null_feature_count_test": quality_test["high_null_feature_count"],
        "at_null_constant_problem_resolved": feature_quality["at_null_constant_problem_resolved"],
        "feature_quality_gate_status": feature_quality["status"],
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_output_path": str(feature_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "input_path": str(normalized_path),
        "feature_version": FEATURE_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "recommended_next_action": "Phase4-BD Long History Label Regeneration: regenerate labels in a physically separate label table.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_long_history_feature_frame(normalized: Any, *, source_snapshot_id: str) -> Any:
    import numpy as np
    import pandas as pd

    frame = normalized.copy()
    frame["target_date"] = frame.get("Date", frame.get("target_date")).astype(str)
    frame["as_of_date"] = frame["target_date"]
    frame["code"] = frame.get("Code", frame.get("code")).astype(str).str.strip()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame["Volume"] = pd.to_numeric(frame["Volume"], errors="coerce")
    frame = frame.dropna(subset=["target_date", "code"]).sort_values(["code", "target_date"]).reset_index(drop=True)
    grouped = frame.groupby("code", sort=False, group_keys=False)
    history_count = grouped.cumcount() + 1
    price_valid_60 = grouped["Close"].transform(lambda values: values.notna().rolling(MIN_LOOKBACK_ROWS, min_periods=MIN_LOOKBACK_ROWS).sum())
    volume_valid_60 = grouped["Volume"].transform(lambda values: values.notna().rolling(MIN_LOOKBACK_ROWS, min_periods=MIN_LOOKBACK_ROWS).sum())
    close = frame["Close"]
    volume = frame["Volume"]
    ma_5 = grouped["Close"].transform(lambda values: values.rolling(5, min_periods=5).mean())
    ma_20 = grouped["Close"].transform(lambda values: values.rolling(20, min_periods=20).mean())
    ma_60 = grouped["Close"].transform(lambda values: values.rolling(60, min_periods=60).mean())
    volume_ma_5 = grouped["Volume"].transform(lambda values: values.rolling(5, min_periods=5).mean())
    volume_ma_20 = grouped["Volume"].transform(lambda values: values.rolling(20, min_periods=20).mean())
    daily_return = grouped["Close"].pct_change()
    volatility_20 = daily_return.groupby(frame["code"], sort=False).transform(lambda values: values.rolling(20, min_periods=20).std(ddof=0))
    has_history = history_count >= MIN_LOOKBACK_ROWS
    has_price = price_valid_60 == MIN_LOOKBACK_ROWS
    has_volume = volume_valid_60 == MIN_LOOKBACK_ROWS
    eligible = has_history & has_price & has_volume

    feature = pd.DataFrame(
        {
            "as_of_date": frame["as_of_date"],
            "target_date": frame["target_date"],
            "code": frame["code"],
            "feature_version": FEATURE_VERSION,
            "source_snapshot_id": source_snapshot_id,
            "feature_set_name": FEATURE_SET_NAME,
            "created_at": _now(),
            "data_start_date": grouped["target_date"].transform("first"),
            "data_end_date": frame["target_date"],
            "universe_eligible": eligible.astype(bool),
            "missing_flags_insufficient_history": (~has_history).astype(bool),
            "missing_flags_price": (~has_price).astype(bool),
            "missing_flags_volume": (~has_volume).astype(bool),
            "price_momentum_return_1d": close / grouped["Close"].shift(1) - 1.0,
            "price_momentum_return_3d": close / grouped["Close"].shift(3) - 1.0,
            "price_momentum_return_5d": close / grouped["Close"].shift(5) - 1.0,
            "price_momentum_return_10d": close / grouped["Close"].shift(10) - 1.0,
            "price_momentum_return_20d": close / grouped["Close"].shift(20) - 1.0,
            "price_momentum_return_60d": close / grouped["Close"].shift(59) - 1.0,
            "recent_move_volatility_z_1d": (close / grouped["Close"].shift(1) - 1.0) / volatility_20,
            "recent_move_volatility_z_3d": (close / grouped["Close"].shift(3) - 1.0) / (volatility_20 * (3.0**0.5)),
            "momentum_5d_vs_20d_delta": (close / grouped["Close"].shift(5) - 1.0) - (close / grouped["Close"].shift(20) - 1.0),
            "momentum_1d_vs_5d_delta": (close / grouped["Close"].shift(1) - 1.0) - (close / grouped["Close"].shift(5) - 1.0),
            "volume_momentum_ratio_5d": volume_ma_5 / volume_ma_20,
            "volume_momentum_ratio_1d_20d": volume / volume_ma_20,
            "volatility_return_std_20d": volatility_20,
            "trend_close_over_ma_20d": close / ma_20 - 1.0,
            "trend_ma_5_20_ratio": ma_5 / ma_20 - 1.0,
            "trend_ma_20_60_ratio": ma_20 / ma_60 - 1.0,
            "liquidity_avg_volume_20d": volume_ma_20,
        }
    )
    feature["excluded_reason"] = np.select(
        [
            feature["missing_flags_insufficient_history"],
            feature["missing_flags_price"],
            feature["missing_flags_volume"],
        ],
        ["insufficient_history", "price_data_missing", "volume_data_missing"],
        default="",
    )
    numeric_feature_columns = [column for column in REQUIRED_AK_FEATURE_COLUMNS if not column.startswith("missing_flags_")]
    feature.loc[~feature["universe_eligible"], numeric_feature_columns] = np.nan
    for column in numeric_feature_columns:
        feature[column] = feature[column].replace([np.inf, -np.inf], np.nan).round(6)
    return feature


def validate_long_history_feature_schema(frame: Any) -> dict[str, Any]:
    columns = [str(column) for column in frame.columns]
    missing_required = sorted(REQUIRED_FEATURE_COLUMNS - set(columns))
    invalid_prefix_columns = [
        column
        for column in columns
        if column not in REQUIRED_FEATURE_COLUMNS
        and column not in OPTIONAL_FEATURE_METADATA_COLUMNS
        and not column.startswith(ALLOWED_FEATURE_PREFIXES)
    ]
    forbidden_columns = [column for column in columns if is_forbidden_column(column)]
    invalid_date_count = int((frame["as_of_date"].astype(str) > frame["target_date"].astype(str)).sum()) if {"as_of_date", "target_date"} <= set(columns) else 0
    invalid_universe_count = 0 if "universe_eligible" in columns and frame["universe_eligible"].dropna().isin([True, False, 0, 1]).all() else 1
    status = "OK" if not (missing_required or invalid_prefix_columns or forbidden_columns or invalid_date_count or invalid_universe_count) else "ERROR"
    return {
        "status": status,
        "missing_required_columns": missing_required,
        "invalid_prefix_columns": invalid_prefix_columns,
        "forbidden_columns": forbidden_columns,
        "invalid_date_row_count": invalid_date_count,
        "invalid_universe_eligible_row_count": invalid_universe_count,
    }


def audit_long_history_feature_leakage(frame: Any) -> dict[str, Any]:
    columns = [str(column) for column in frame.columns]
    forbidden_columns = [column for column in columns if is_forbidden_column(column)]
    future_columns = [column for column in columns if column.startswith(("future_return_", "future_max_return_", "future_max_drawdown_"))]
    label_columns = [column for column in columns if "label" in column.lower()]
    post_as_of_count = int((frame["as_of_date"].astype(str) > frame["target_date"].astype(str)).sum())
    status = "OK" if not (forbidden_columns or future_columns or label_columns or post_as_of_count) else "ERROR"
    return {
        "status": status,
        "forbidden_feature_detected": bool(forbidden_columns),
        "forbidden_columns": forbidden_columns,
        "future_column_detected": bool(future_columns),
        "future_columns": future_columns,
        "label_column_detected": bool(label_columns),
        "label_columns": label_columns,
        "post_as_of_data_detected": bool(post_as_of_count),
        "post_as_of_row_count": post_as_of_count,
        "target_date_leakage_detected": bool(post_as_of_count),
    }


def compute_feature_quality_gate(frame: Any) -> dict[str, Any]:
    splits = {
        "train": _split_quality(frame, TRAIN_START, TRAIN_END),
        "validation": _split_quality(frame, VALIDATION_START, VALIDATION_END),
        "test": _split_quality(frame, TEST_START, TEST_END),
    }
    train = splits["train"]
    status = "OK" if train["all_null_feature_count"] == 0 and train["feature_variance_available"] else "ERROR"
    return {
        "status": status,
        "splits": splits,
        "at_null_constant_problem_resolved": status == "OK"
        and train["all_null_feature_count"] == 0
        and train["high_null_feature_count"] == 0
        and train["feature_variance_available"] is True,
    }


def _split_quality(frame: Any, start: str, end: str) -> dict[str, Any]:
    split = frame[(frame["target_date"].astype(str) >= start) & (frame["target_date"].astype(str) <= end)]
    feature_columns = _feature_columns(frame)
    numeric_columns = [column for column in feature_columns if not column.startswith("missing_flags_")]
    if split.empty:
        return {
            "row_count": 0,
            "target_date_min": None,
            "target_date_max": None,
            "target_date_count": 0,
            "all_null_feature_count": len(numeric_columns),
            "constant_feature_count": len(numeric_columns),
            "near_constant_feature_count": len(numeric_columns),
            "high_null_feature_count": len(numeric_columns),
            "feature_non_null_rate": {},
            "feature_unique_count": {},
            "feature_variance": {},
            "feature_variance_available": False,
        }
    non_null_rate = {column: round(float(split[column].notna().mean()), 6) for column in numeric_columns}
    unique_count = {column: int(split[column].nunique(dropna=True)) for column in numeric_columns}
    variance = {column: _safe_float(split[column].var(skipna=True)) for column in numeric_columns}
    all_null = [column for column in numeric_columns if non_null_rate[column] == 0.0]
    constant = [column for column in numeric_columns if unique_count[column] <= 1]
    near_constant = [column for column in numeric_columns if _near_constant(split[column])]
    high_null = [column for column in numeric_columns if non_null_rate[column] < (1.0 - HIGH_NULL_THRESHOLD)]
    dates = sorted(split["target_date"].astype(str).unique().tolist())
    return {
        "row_count": int(len(split)),
        "target_date_min": dates[0] if dates else None,
        "target_date_max": dates[-1] if dates else None,
        "target_date_count": len(dates),
        "all_null_feature_count": len(all_null),
        "all_null_features": all_null,
        "constant_feature_count": len(constant),
        "constant_features": constant,
        "near_constant_feature_count": len(near_constant),
        "near_constant_features": near_constant,
        "high_null_feature_count": len(high_null),
        "high_null_features": high_null,
        "feature_non_null_rate": non_null_rate,
        "feature_unique_count": unique_count,
        "feature_variance": variance,
        "feature_variance_available": any(value is not None and value > 0 for value in variance.values()),
    }


def _near_constant(series: Any) -> bool:
    values = series.dropna()
    if values.empty:
        return True
    top_rate = float(values.value_counts(normalize=True, dropna=True).iloc[0])
    return top_rate >= NEAR_CONSTANT_THRESHOLD


def _feature_columns(frame: Any) -> list[str]:
    metadata = set(REQUIRED_FEATURE_COLUMNS) | set(OPTIONAL_FEATURE_METADATA_COLUMNS)
    return [column for column in frame.columns if column not in metadata]


def _safe_float(value: Any) -> float | None:
    try:
        if value != value:
            return None
        return round(float(value), 10)
    except (TypeError, ValueError):
        return None


def _resolve_readiness(
    *,
    schema_validation_status: str,
    leakage_audit_status: str,
    feature_quality_status: str,
    forbidden_feature_detected: bool,
    future_column_detected: bool,
    label_column_detected: bool,
) -> str:
    if schema_validation_status != "OK":
        return BLOCKED_SCHEMA
    if leakage_audit_status != "OK" or forbidden_feature_detected or future_column_detected or label_column_detected:
        return BLOCKED_LEAKAGE
    if feature_quality_status != "OK":
        return BLOCKED_QUALITY
    return READY


def _read_normalized_frame(path: Path, input_format: str) -> Any:
    import pandas as pd

    if input_format == "parquet":
        return pd.read_parquet(path)
    return pd.DataFrame(create_storage_backend(input_format).read_records(path))


def _write_feature_frame(path: Path, frame: Any, output_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "parquet":
        frame.to_parquet(path, index=False, engine="pyarrow")
        return
    create_storage_backend(output_format).write_records(path, frame.astype(object).where(frame.notna(), None).to_dict("records"))


def _feature_output_path(feature_root: Path, output_format: str, suffix: str) -> Path:
    return create_storage_backend(output_format).path_for(feature_root / f"phase4bc_long_history_features_{suffix}")


def _real_runtime_normalized_path(paths: RuntimePaths, input_format: str) -> Path:
    return create_storage_backend(input_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _safe_candidate_output_paths(runtime_dir: Path, *paths: Path) -> bool:
    root = (runtime_dir.resolve() / "candidate_ai").resolve()
    for path in paths:
        try:
            path.resolve().relative_to(root)
        except ValueError:
            return False
    return True


def _blocked_summary(*, readiness_status: str, reason: str, paths: RuntimePaths, summary_path: Path, normalized_path: Path) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "feature_generation_executed": False,
        "normalized_row_count": 0,
        "feature_row_count": 0,
        "eligible_count": 0,
        "excluded_count": 0,
        "code_count": 0,
        "target_date_min": None,
        "target_date_max": None,
        "target_date_count": 0,
        "feature_column_count": 0,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "forbidden_feature_detected": False,
        "future_column_detected": False,
        "label_column_detected": False,
        "at_null_constant_problem_resolved": False,
        "label_generation_executed": False,
        "dataset_rebuild_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "input_path": str(normalized_path),
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the feature regeneration blocker, then rerun Phase4-BC.",
        "summary_path": str(summary_path),
    }


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _split_ranges() -> dict[str, dict[str, str]]:
    return {
        "train": {"start": TRAIN_START, "end": TRAIN_END},
        "validation": {"start": VALIDATION_START, "end": VALIDATION_END},
        "test": {"start": TEST_START, "end": TEST_END},
    }


if __name__ == "__main__":
    raise SystemExit(main())
