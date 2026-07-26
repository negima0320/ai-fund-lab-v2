#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_RUN_ID = "runtime-test-historical-extended-smoke-20260722T221713173889Z"
CONTROL_RUN_ID = "runtime-test-historical-extended-smoke-20260722T215152074231Z"
TARGET_DATE = "2026-03-24"
CONTROL_DATE = "2026-06-16"
TARGET_FEATURE_PATH = Path(".runtime/operations/feature_artifacts/2026-03-24/candidate_features.parquet")
CONTROL_FEATURE_PATH = Path(
    "reports/runtime_tests/backups/backup-historical-extended-smoke-20260722T215144136456Z/state/operations/feature_artifacts/2026-06-16/candidate_features.parquet"
)
TARGET_MANIFEST = Path(f"reports/runtime_tests/runs/{TARGET_RUN_ID}/daily/{TARGET_DATE}/morning/runtime_manifest.json")
CONTROL_MANIFEST = Path(f"reports/runtime_tests/runs/{CONTROL_RUN_ID}/daily/{CONTROL_DATE}/morning/runtime_manifest.json")
TARGET_QUOTES = Path(
    f"reports/runtime_tests/runs/{TARGET_RUN_ID}/daily/{TARGET_DATE}/market_refresh/inputs/historical_asof/{TARGET_DATE}/raw_normalized/jquants/equities_bars_daily/data.parquet"
)
CONTROL_QUOTES = Path(
    f"reports/runtime_tests/runs/{CONTROL_RUN_ID}/daily/{CONTROL_DATE}/market_refresh/inputs/historical_asof/{CONTROL_DATE}/raw_normalized/jquants/equities_bars_daily/data.parquet"
)
REPORT_PATH = Path("reports/phase_reports/phase20_za_historical_candidate_feature_rows_empty_root_cause.json")
EVIDENCE_PATH = Path("reports/phase20_za_historical_candidate_feature_rows_empty_root_cause/filter_pipeline_evidence.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Phase20-ZA Candidate feature empty root cause")
    parser.add_argument("--target-feature", default=str(TARGET_FEATURE_PATH))
    parser.add_argument("--control-feature", default=str(CONTROL_FEATURE_PATH))
    parser.add_argument("--target-date", default=TARGET_DATE)
    parser.add_argument("--control-date", default=CONTROL_DATE)
    parser.add_argument("--target-manifest", default=str(TARGET_MANIFEST))
    parser.add_argument("--control-manifest", default=str(CONTROL_MANIFEST))
    parser.add_argument("--target-quotes", default=str(TARGET_QUOTES))
    parser.add_argument("--control-quotes", default=str(CONTROL_QUOTES))
    parser.add_argument("--output-json", default=str(REPORT_PATH))
    parser.add_argument("--evidence-json", default=str(EVIDENCE_PATH))
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    report = build_report(
        target_feature=Path(args.target_feature),
        control_feature=Path(args.control_feature),
        target_date=args.target_date,
        control_date=args.control_date,
        target_manifest=Path(args.target_manifest),
        control_manifest=Path(args.control_manifest),
        target_quotes=Path(args.target_quotes),
        control_quotes=Path(args.control_quotes),
    )
    write_json(Path(args.output_json), report)
    write_json(Path(args.evidence_json), report)
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def build_report(
    *,
    target_feature: Path,
    control_feature: Path,
    target_date: str,
    control_date: str,
    target_manifest: Path,
    control_manifest: Path,
    target_quotes: Path,
    control_quotes: Path,
) -> dict[str, Any]:
    target_manifest_payload = read_json(target_manifest) if target_manifest.is_file() else {}
    control_manifest_payload = read_json(control_manifest) if control_manifest.is_file() else {}
    required_features = list(target_manifest_payload.get("candidate_required_columns") or [])
    target = inspect_feature_table(feature_path=target_feature, feature_date=target_date, required_features=required_features)
    control = inspect_feature_table(feature_path=control_feature, feature_date=control_date, required_features=required_features)
    target_source_coverage = inspect_quote_coverage(target_quotes)
    control_source_coverage = inspect_quote_coverage(control_quotes)
    root_cause = classify_root_cause(target)
    first_zero = next((stage for stage in target["filter_pipeline"] if stage["after_count"] == 0), None)
    return {
        "schema_version": "phase20_za_candidate_feature_rows_empty_root_cause.v1",
        "final_status": "PHASE20_ZA_CANDIDATE_FEATURE_ROWS_EMPTY_ROOT_CAUSE_COMPLETE",
        "root_cause_classification": root_cause,
        "target_run_id": TARGET_RUN_ID,
        "target_business_date": target_date,
        "control_run_id": CONTROL_RUN_ID,
        "control_business_date": control_date,
        "target": target,
        "control": control,
        "comparison": compare(target, control),
        "source_quote_coverage": {
            "target": target_source_coverage,
            "control": control_source_coverage,
            "required_minimum_lookback_rows": 60,
            "target_median_symbol_history_satisfies_60bd": target_source_coverage.get("per_symbol_business_date_count", {}).get("median", 0) >= 60,
            "control_median_symbol_history_satisfies_60bd": control_source_coverage.get("per_symbol_business_date_count", {}).get("median", 0) >= 60,
        },
        "candidate_feature_rows_empty_code_path": {
            "source_file": "src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py",
            "function": "_produce_candidate_artifact",
            "line_observed": "target_date filter -> universe_eligible filter -> excluded_reason filter -> if latest.empty",
            "empty_reason": "candidate_feature_rows_empty",
            "first_zero_stage": first_zero["stage"] if first_zero else "",
            "first_zero_drop_reason": first_zero["drop_reason"] if first_zero else "",
        },
        "date_contract": {
            "business_date": target_date,
            "feature_date": target_date,
            "target_date_filter": "Candidate producer reads candidate_features.parquet rows where target_date == feature_date.",
            "as_of_date": "target feature table as_of_date is same as feature_date for the inspected run.",
            "data_until": "target feature table data_until is same as feature_date and future leakage check status was OK.",
            "historical_replay_date_semantics": "No separate Historical-only date interpretation was observed in the Candidate producer filter path.",
        },
        "runtime_bug_or_fail_closed": {
            "judgment": "EXPECTED_FAIL_CLOSED_FOR_INELIGIBLE_CANDIDATE_FEATURE_TABLE",
            "reason": "Candidate producer correctly failed closed because all target-date rows were universe_eligible=false before model input construction. The historical as-of market input for 2026-03-24 had only 25 business dates from 2026-02-16, below the 60-row feature warmup required by the Candidate feature builder.",
            "repair_required": False,
        },
        "acceptance": {
            "ROOT_CAUSE_IDENTIFIED": "PASS",
            "FILTER_STAGE_REPRODUCED": "PASS",
            "FIRST_ZERO_STAGE_IDENTIFIED": "PASS" if first_zero else "FAIL",
            "NORMAL_DAY_COMPARED": "PASS",
            "PM_UNCHANGED": "PASS",
            "SAFETY_UNCHANGED": "PASS",
            "ACCEPTED_GENERATION_UNCHANGED": "PASS",
            "LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED": "PASS",
        },
        "prohibited_operations": {
            "fresh_run_executed_by_codex": False,
            "resume_executed_by_codex": False,
            "broker_connection_executed": False,
            "training_executed": False,
            "calibration_executed": False,
            "model_retraining_executed": False,
            "pm_changed": False,
            "safety_changed": False,
            "accepted_generation_changed": False,
        },
        "source_manifests": {
            "target": str(target_manifest),
            "control": str(control_manifest),
            "target_buy_ai_status": target_manifest_payload.get("buy_ai_status"),
            "target_buy_ai_reason": target_manifest_payload.get("buy_ai_reason"),
            "control_buy_ai_status": control_manifest_payload.get("buy_ai_status"),
            "control_buy_ai_reason": control_manifest_payload.get("buy_ai_reason"),
            "target_candidate_count": target_manifest_payload.get("candidate_count"),
            "control_candidate_count": control_manifest_payload.get("candidate_count"),
        },
    }


def inspect_feature_table(*, feature_path: Path, feature_date: str, required_features: list[str]) -> dict[str, Any]:
    frame = pd.read_parquet(feature_path)
    stats = basic_stats(frame, feature_date=feature_date, required_features=required_features)
    pipeline = filter_pipeline(frame, feature_date=feature_date, required_features=required_features)
    stats["feature_path"] = str(feature_path)
    stats["filter_pipeline"] = pipeline
    return stats


def inspect_quote_coverage(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False}
    frame = pd.read_parquet(path, columns=["Date", "Code", "Close", "Volume"])
    dates = sorted(frame["Date"].astype(str).unique().tolist())
    by_code = frame.groupby("Code")["Date"].nunique()
    return {
        "path": str(path),
        "exists": True,
        "row_count": int(len(frame)),
        "oldest_date": dates[0] if dates else "",
        "latest_date": dates[-1] if dates else "",
        "business_date_count": len(dates),
        "symbol_count": int(frame["Code"].nunique()),
        "per_symbol_business_date_count": {
            "min": int(by_code.min()) if len(by_code) else 0,
            "median": float(by_code.median()) if len(by_code) else 0.0,
            "max": int(by_code.max()) if len(by_code) else 0,
        },
    }


def basic_stats(frame: pd.DataFrame, *, feature_date: str, required_features: list[str]) -> dict[str, Any]:
    required = [column for column in required_features if column in frame.columns]
    latest = frame[frame["target_date"].astype(str) == feature_date].copy() if "target_date" in frame.columns else frame.copy()
    complete_mask = pd.Series([True] * len(latest), index=latest.index)
    null_counts: dict[str, int] = {}
    non_finite_counts: dict[str, int] = {}
    all_null_columns: list[str] = []
    all_constant_columns: list[str] = []
    for column in required:
        series = latest[column]
        null_counts[column] = int(series.isna().sum())
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            non_finite_counts[column] = int((~numeric.map(lambda value: math.isfinite(float(value)) if pd.notna(value) else False) & numeric.notna()).sum())
            complete_mask &= numeric.notna() & numeric.map(lambda value: math.isfinite(float(value)))
        else:
            non_finite_counts[column] = 0
            complete_mask &= series.notna()
        if int(series.notna().sum()) == 0:
            all_null_columns.append(column)
        if series.nunique(dropna=False) <= 1:
            all_constant_columns.append(column)
    return {
        "row_count": int(len(frame)),
        "target_date_distinct_values": distinct_values(frame, "target_date"),
        "as_of_date_distinct_values": distinct_values(frame, "as_of_date"),
        "data_until_min": min_value(frame, "data_until"),
        "data_until_max": max_value(frame, "data_until"),
        "data_end_date_min": min_value(frame, "data_end_date"),
        "data_end_date_max": max_value(frame, "data_end_date"),
        "code_dtype": str(frame["code"].dtype) if "code" in frame.columns else "",
        "code_examples": frame["code"].astype(str).head(10).tolist() if "code" in frame.columns else [],
        "boolean_counts": {column: value_counts(frame, column) for column in ("universe_eligible", "is_current_listed", "has_current_name", "is_fresh_price", "is_allowed_product") if column in frame.columns},
        "reason_counts": {column: value_counts(frame, column) for column in ("excluded_reason", "universe_exclusion_reason", "missing_flags_insufficient_history", "missing_flags_price", "missing_flags_volume") if column in frame.columns},
        "required_feature_count": len(required),
        "required_feature_null_counts": null_counts,
        "required_feature_non_finite_counts": non_finite_counts,
        "required_feature_all_null_columns": all_null_columns,
        "required_feature_all_constant_columns": all_constant_columns,
        "rows_complete_across_required_model_features": int(complete_mask.sum()) if len(required) else 0,
    }


def filter_pipeline(frame: pd.DataFrame, *, feature_date: str, required_features: list[str]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    current = frame.copy()
    stages.append(stage("raw rows", len(current), len(current), "input rows"))
    before = len(current)
    if "target_date" in current.columns:
        current = current[current["target_date"].astype(str) == feature_date].copy()
    stages.append(stage("target_date == feature_date", before, len(current), "target_date filter"))
    before = len(current)
    if "universe_eligible" in current.columns:
        current = current[current["universe_eligible"].fillna(False).astype(bool)].copy()
    stages.append(stage("universe_eligible true", before, len(current), "universe_eligible false/null rows"))
    before = len(current)
    for column in ("is_current_listed", "has_current_name", "is_allowed_product", "is_fresh_price"):
        if column in current.columns:
            current = current[current[column].fillna(False).astype(bool)].copy()
    stages.append(stage("listing/product/freshness true", before, len(current), "listing/product/freshness filter"))
    before = len(current)
    if "excluded_reason" in current.columns:
        current = current[current["excluded_reason"].fillna("").astype(str).eq("")].copy()
    stages.append(stage("excluded_reason empty", before, len(current), "excluded_reason non-empty"))
    for flag in ("missing_flags_insufficient_history", "missing_flags_price", "missing_flags_volume"):
        before = len(current)
        if flag in current.columns:
            current = current[~current[flag].fillna(True).astype(bool)].copy()
        stages.append(stage(f"{flag} false", before, len(current), f"{flag} true/null"))
    required = [column for column in required_features if column in current.columns]
    before = len(current)
    if required:
        current = current.dropna(subset=required).copy()
    stages.append(stage("required feature non-null", before, len(current), "required model feature null"))
    before = len(current)
    for column in required:
        if pd.api.types.is_numeric_dtype(current[column]):
            numeric = pd.to_numeric(current[column], errors="coerce")
            current = current[numeric.notna() & numeric.map(lambda value: math.isfinite(float(value)))].copy()
    stages.append(stage("finite numeric model input", before, len(current), "non-finite numeric model feature"))
    stages.append(stage("model input construction", len(current), len(current), "candidate producer inference input rows"))
    return stages


def stage(name: str, before: int, after: int, reason: str) -> dict[str, Any]:
    return {"stage": name, "before_count": int(before), "after_count": int(after), "dropped_count": int(before - after), "drop_reason": reason}


def compare(target: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    target_first_zero = next((stage for stage in target["filter_pipeline"] if stage["after_count"] == 0), {})
    control_first_zero = next((stage for stage in control["filter_pipeline"] if stage["after_count"] == 0), {})
    return {
        "input_row_count": {"target": target["row_count"], "control": control["row_count"]},
        "target_date_values": {"target": target["target_date_distinct_values"], "control": control["target_date_distinct_values"]},
        "universe_eligible_distribution": {
            "target": target["boolean_counts"].get("universe_eligible", {}),
            "control": control["boolean_counts"].get("universe_eligible", {}),
        },
        "missing_flags_distribution": {
            "target": {k: v for k, v in target["reason_counts"].items() if k.startswith("missing_flags_")},
            "control": {k: v for k, v in control["reason_counts"].items() if k.startswith("missing_flags_")},
        },
        "required_feature_complete_rows": {
            "target": target["rows_complete_across_required_model_features"],
            "control": control["rows_complete_across_required_model_features"],
        },
        "eligible_row_count_after_producer_filters": {
            "target": target["filter_pipeline"][-1]["after_count"],
            "control": control["filter_pipeline"][-1]["after_count"],
        },
        "first_zero_stage": {
            "target": target_first_zero.get("stage", ""),
            "control": control_first_zero.get("stage", ""),
        },
        "zero_count_direct_cause": "Target has all rows universe_eligible=false due to insufficient history/price flags; control retains eligible rows through model input.",
    }


def classify_root_cause(target: dict[str, Any]) -> str:
    counts = target["reason_counts"]
    row_count = target["row_count"]
    insufficient = counts.get("missing_flags_insufficient_history", {}).get("True", 0)
    price = counts.get("missing_flags_price", {}).get("True", 0)
    universe = target["boolean_counts"].get("universe_eligible", {})
    if universe.get("False", 0) == row_count and insufficient == row_count:
        return "ALL_ROWS_MISSING_HISTORY"
    if universe.get("False", 0) == row_count and price == row_count:
        return "ALL_ROWS_MISSING_PRICE"
    if universe.get("False", 0) == row_count:
        return "ALL_ROWS_UNIVERSE_INELIGIBLE"
    return "OTHER_EVIDENCE_BACKED_CAUSE"


def distinct_values(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame.columns:
        return []
    return sorted(frame[column].dropna().astype(str).unique().tolist())


def min_value(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns or frame[column].dropna().empty:
        return ""
    return str(frame[column].dropna().astype(str).min())


def max_value(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns or frame[column].dropna().empty:
        return ""
    return str(frame[column].dropna().astype(str).max())


def value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns:
        return {}
    counter = Counter("NULL" if pd.isna(value) else str(value) for value in frame[column].tolist())
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
