#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PHASE = "Phase4-AT"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4at_candidate_feature_quality_summary.json")
PHASE4AO_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json")
PHASE4AN_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4an_historical_feature_coverage_summary.json")
CATALOG_PATH = Path("docs/03_ai_design/candidate_feature_catalog.md")
BUILDER_DESIGN_PATH = Path("docs/03_ai_design/candidate_feature_builder_design.md")
REPORT_PATH = Path("docs/phase_reports/phase4at_candidate_feature_quality.md")

READY = "READY_FOR_FEATURE_EXPANSION_PLAN"
BLOCKED_BUILDER = "BLOCKED_BY_FEATURE_BUILDER"
BLOCKED_QUALITY = "BLOCKED_BY_FEATURE_DATA_QUALITY"

HIGH_NULL_THRESHOLD = 0.5
NEAR_CONSTANT_DOMINANCE_THRESHOLD = 0.99


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-AT Candidate feature quality.")
    parser.add_argument("--phase4ao-summary", default=str(PHASE4AO_SUMMARY_PATH))
    parser.add_argument("--phase4an-summary", default=str(PHASE4AN_SUMMARY_PATH))
    parser.add_argument("--summary-path", default=str(SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = audit_phase4at_candidate_feature_quality(
        phase4ao_summary_path=Path(args.phase4ao_summary),
        phase4an_summary_path=Path(args.phase4an_summary),
        summary_path=Path(args.summary_path),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def audit_phase4at_candidate_feature_quality(
    *,
    phase4ao_summary_path: Path = PHASE4AO_SUMMARY_PATH,
    phase4an_summary_path: Path = PHASE4AN_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    ao_summary = _read_json_optional(phase4ao_summary_path)
    an_summary = _read_json_optional(phase4an_summary_path)
    dataset_path = Path(str(ao_summary.get("dataset_output_path") or ""))
    historical_feature_path = Path(str(an_summary.get("historical_feature_output_path") or ""))
    if not dataset_path.is_file() or not historical_feature_path.is_file():
        summary = _blocked_summary(BLOCKED_BUILDER, "Required Phase4-AO dataset or Phase4-AN feature table is missing.", summary_path)
        _write_json(summary_path, summary)
        return summary

    dataset_rows = _rows(_read_json_optional(dataset_path))
    historical_rows = _rows(_read_json_optional(historical_feature_path))
    feature_columns = sorted({column for row in dataset_rows for column in row if column.startswith("feature__")})
    implemented_features = [column.replace("feature__", "", 1) for column in feature_columns]
    training_feature_report = analyze_feature_quality(dataset_rows, feature_columns)
    latest_target_date = max(str(row.get("target_date")) for row in historical_rows if row.get("target_date"))
    latest_rows = [row for row in historical_rows if str(row.get("target_date")) == latest_target_date]
    latest_feature_columns = sorted({column for column in latest_rows[0].keys() if _is_feature_name(column)}) if latest_rows else []
    latest_feature_report = analyze_feature_quality(latest_rows, latest_feature_columns)
    target_date_distribution = analyze_target_date_distribution(dataset_rows, feature_columns)
    design_features = extract_builder_design_features(BUILDER_DESIGN_PATH)
    catalog_features = extract_catalog_features(CATALOG_PATH)
    implemented_design_mapped = set(implemented_features)
    design_missing = sorted(feature for feature in design_features if feature not in implemented_design_mapped)
    catalog_missing = sorted(feature for feature in catalog_features if not _catalog_feature_implemented(feature, implemented_features))
    builder_gap = build_feature_builder_gap(
        implemented_features=implemented_features,
        design_features=design_features,
        catalog_features=catalog_features,
        training_report=training_feature_report,
    )
    readiness_status = READY if training_feature_report["high_null_feature_count"] or design_missing else BLOCKED_QUALITY
    likely_root_cause = (
        "Training-period features are mostly missing or constant because Phase4-AO labels cover early target_dates "
        "where 60-day lookback features cannot be calculated from the current 60-business-day real_runtime history."
    )
    recommended_fix_plan = [
        "Plan Phase4-AU Candidate Feature Expansion before retraining.",
        "Extend normalized history so each label target_date has enough prior lookback rows.",
        "Generate historical features only for target_dates with sufficient lookback, or mark early dates out of training.",
        "Add catalog-defined missing features such as high-breakout, liquidity turnover, market regime, sector relative, and quality features.",
        "Add feature quality gates before training: non-null rate, unique value count, variance, and target_date coverage.",
        "Keep label, training, inference, backtest, and trading unchanged until feature quality is fixed.",
    ]
    summary = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "feature_quality_audit_executed": True,
        "feature_count": len(feature_columns),
        "constant_feature_count": training_feature_report["constant_feature_count"],
        "near_constant_feature_count": training_feature_report["near_constant_feature_count"],
        "high_null_feature_count": training_feature_report["high_null_feature_count"],
        "all_null_feature_count": training_feature_report["all_null_feature_count"],
        "constant_features": training_feature_report["constant_features"],
        "near_constant_features": training_feature_report["near_constant_features"],
        "high_null_features": training_feature_report["high_null_features"],
        "all_null_features": training_feature_report["all_null_features"],
        "feature_variance_report": training_feature_report["variance_report"],
        "feature_distribution_report": {
            "training_dataset": training_feature_report["distribution_report"],
            "latest_inference_date": latest_feature_report["distribution_report"],
            "target_date_distribution": target_date_distribution,
        },
        "implemented_feature_count": len(implemented_features),
        "implemented_features": implemented_features,
        "missing_feature_count": len(design_missing),
        "missing_features": design_missing,
        "catalog_missing_feature_count": len(catalog_missing),
        "catalog_missing_features": catalog_missing,
        "feature_builder_design_gap": builder_gap,
        "likely_root_cause": likely_root_cause,
        "recommended_fix_plan": recommended_fix_plan,
        "latest_target_date": latest_target_date,
        "latest_feature_constant_count": latest_feature_report["constant_feature_count"],
        "latest_feature_high_null_count": latest_feature_report["high_null_feature_count"],
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    _write_markdown_report(REPORT_PATH, summary)
    return summary


def analyze_feature_quality(rows: list[dict[str, Any]], feature_columns: list[str]) -> dict[str, Any]:
    per_feature: dict[str, dict[str, Any]] = {}
    constant_features: list[str] = []
    near_constant_features: list[str] = []
    high_null_features: list[str] = []
    all_null_features: list[str] = []
    variance_report: dict[str, float | None] = {}
    distribution_report: dict[str, dict[str, Any]] = {}
    for column in feature_columns:
        values = [_numeric_value(row.get(column)) for row in rows]
        stats = summarize_values(values)
        per_feature[column] = stats
        variance_report[column] = stats["variance"]
        distribution_report[column] = {
            key: stats[key]
            for key in ("null_rate", "unique_count", "std", "min", "p25", "median", "p75", "max", "dominance_ratio")
        }
        if stats["constant"]:
            constant_features.append(column)
        if stats["near_constant"]:
            near_constant_features.append(column)
        if stats["high_null"]:
            high_null_features.append(column)
        if stats["all_null"]:
            all_null_features.append(column)
    return {
        "constant_feature_count": len(constant_features),
        "near_constant_feature_count": len(near_constant_features),
        "high_null_feature_count": len(high_null_features),
        "all_null_feature_count": len(all_null_features),
        "constant_features": constant_features,
        "near_constant_features": near_constant_features,
        "high_null_features": high_null_features,
        "all_null_features": all_null_features,
        "variance_report": variance_report,
        "distribution_report": distribution_report,
        "per_feature": per_feature,
    }


def summarize_values(values: list[float]) -> dict[str, Any]:
    normalized_values = [_numeric_value(value) for value in values]
    non_null = [value for value in normalized_values if not math.isnan(value)]
    null_rate = 1.0 - (len(non_null) / len(normalized_values)) if normalized_values else 1.0
    unique_count = len({round(value, 12) for value in non_null})
    all_null = len(non_null) == 0
    constant = unique_count <= 1
    dominance = dominance_ratio(non_null)
    near_constant = constant or dominance >= NEAR_CONSTANT_DOMINANCE_THRESHOLD
    high_null = null_rate >= HIGH_NULL_THRESHOLD
    quantiles = value_quantiles(non_null)
    variance = statistics.pvariance(non_null) if len(non_null) > 1 else 0.0 if non_null else None
    return {
        "null_rate": round(null_rate, 6),
        "unique_count": unique_count,
        "variance": round(float(variance), 12) if variance is not None else None,
        "std": round(float(math.sqrt(variance)), 12) if variance is not None else None,
        "min": round(min(non_null), 12) if non_null else None,
        "p25": quantiles["p25"],
        "median": quantiles["median"],
        "p75": quantiles["p75"],
        "max": round(max(non_null), 12) if non_null else None,
        "dominance_ratio": round(dominance, 6),
        "constant": constant,
        "near_constant": near_constant,
        "high_null": high_null,
        "all_null": all_null,
    }


def analyze_target_date_distribution(rows: list[dict[str, Any]], feature_columns: list[str]) -> dict[str, Any]:
    by_date: dict[str, dict[str, Any]] = {}
    dates = sorted({str(row.get("target_date")) for row in rows if row.get("target_date")})
    for target_date in dates:
        subset = [row for row in rows if str(row.get("target_date")) == target_date]
        non_null_values = 0
        total_values = len(subset) * len(feature_columns)
        for row in subset:
            non_null_values += sum(row.get(column) is not None for column in feature_columns)
        by_date[target_date] = {
            "row_count": len(subset),
            "feature_non_null_rate": round(non_null_values / total_values, 6) if total_values else 0.0,
        }
    return {
        "target_date_count": len(dates),
        "target_date_min": dates[0] if dates else None,
        "target_date_max": dates[-1] if dates else None,
        "by_date": by_date,
    }


def extract_builder_design_features(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    names = sorted(set(re.findall(r"^(?:price|volume|volatility|trend|relative|market|sector|fundamental|liquidity|universe|missing)_[a-zA-Z0-9_]+$", text, re.MULTILINE)))
    # Remove prefixes that are category examples rather than concrete output columns.
    excluded = {"missing_flag_counts", "universe_eligible", "universe_eligible_count"}
    return [name for name in names if not name.endswith("_features") and name not in excluded]


def extract_catalog_features(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    names = sorted(set(re.findall(r"\|\s*([a-zA-Z][a-zA-Z0-9_]+)\s*\|", text)))
    excluded = {"feature_name", "category", "daily_quotes_normalized"}
    return [name for name in names if name not in excluded and "_" in name]


def build_feature_builder_gap(
    *,
    implemented_features: list[str],
    design_features: list[str],
    catalog_features: list[str],
    training_report: dict[str, Any],
) -> dict[str, Any]:
    implemented = set(implemented_features)
    return {
        "implemented_but_all_null": [feature.replace("feature__", "", 1) for feature in training_report["all_null_features"]],
        "implemented_but_constant": [feature.replace("feature__", "", 1) for feature in training_report["constant_features"]],
        "design_features_not_implemented": [feature for feature in design_features if feature not in implemented],
        "catalog_features_not_implemented_or_not_mapped": [
            feature for feature in catalog_features if not _catalog_feature_implemented(feature, implemented_features)
        ],
        "gap_summary": (
            "Only a small price/volume subset is implemented, and during label target_dates most implemented "
            "features are null or constant. Market, sector, quality, high-breakout, turnover, and risk filters "
            "from the design/catalog are not yet implemented."
        ),
    }


def _catalog_feature_implemented(catalog_feature: str, implemented_features: list[str]) -> bool:
    direct = set(implemented_features)
    mapping = {
        "return_5d": "price_momentum_return_5d",
        "return_20d": "price_momentum_return_20d",
        "return_60d": "price_momentum_return_60d",
        "ma_5_20_ratio": "trend_ma_5_20_ratio",
        "ma_20_60_ratio": "trend_ma_20_60_ratio",
        "volatility_20d": "volatility_return_std_20d",
        "volume_ratio_5d_20d": "volume_momentum_ratio_5d",
        "volume_ratio_1d_20d": "volume_momentum_ratio_1d_20d",
        "avg_volume_20d": "liquidity_avg_volume_20d",
        "insufficient_history_flag": "missing_flags_insufficient_history",
    }
    return catalog_feature in direct or mapping.get(catalog_feature) in direct


def value_quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p25": None, "median": None, "p75": None}
    ordered = sorted(values)
    return {
        "p25": round(percentile(ordered, 0.25), 12),
        "median": round(percentile(ordered, 0.5), 12),
        "p75": round(percentile(ordered, 0.75), 12),
    }


def percentile(ordered: list[float], q: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - pos) + ordered[upper] * (pos - lower)


def dominance_ratio(values: list[float]) -> float:
    if not values:
        return 1.0
    counts: dict[float, int] = {}
    for value in values:
        key = round(value, 12)
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values()) / len(values)


def _numeric_value(value: Any) -> float:
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _is_feature_name(column: str) -> bool:
    return column.startswith(
        (
            "price_",
            "volume_",
            "volatility_",
            "trend_",
            "liquidity_",
            "missing_",
            "relative_",
            "market_",
            "sector_",
            "fundamental_",
            "universe_",
        )
    )


def _blocked_summary(readiness_status: str, reason: str, summary_path: Path) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "feature_count": 0,
        "constant_feature_count": 0,
        "near_constant_feature_count": 0,
        "high_null_feature_count": 0,
        "all_null_feature_count": 0,
        "feature_variance_report": {},
        "feature_distribution_report": {},
        "implemented_feature_count": 0,
        "missing_feature_count": 0,
        "feature_builder_design_gap": {},
        "likely_root_cause": reason,
        "recommended_fix_plan": [],
        "summary_path": str(summary_path),
    }


def _write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AT Candidate Feature Quality Audit",
        "",
        "## Result",
        "",
        f"- status: {summary['status']}",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- feature_count: {summary['feature_count']}",
        f"- constant_feature_count: {summary['constant_feature_count']}",
        f"- near_constant_feature_count: {summary['near_constant_feature_count']}",
        f"- high_null_feature_count: {summary['high_null_feature_count']}",
        f"- all_null_feature_count: {summary['all_null_feature_count']}",
        "",
        "## Likely Root Cause",
        "",
        summary["likely_root_cause"],
        "",
        "## Constant Features",
        "",
    ]
    for feature in summary["constant_features"]:
        lines.append(f"- {feature}")
    lines.extend(["", "## High Null Features", ""])
    for feature in summary["high_null_features"]:
        lines.append(f"- {feature}")
    lines.extend(["", "## Missing Design Features", ""])
    for feature in summary["missing_features"]:
        lines.append(f"- {feature}")
    lines.extend(["", "## Recommended Fix Plan", ""])
    for item in summary["recommended_fix_plan"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This phase audits feature quality only.",
            "- It does not add features, change labels, retrain, run inference, backtest, or trade.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return [dict(row) for row in rows]


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
