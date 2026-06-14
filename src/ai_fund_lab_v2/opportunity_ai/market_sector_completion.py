from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.combined_validation import validate_candidate_opportunity_combined
from ai_fund_lab_v2.opportunity_ai.model_calibration import run_model_improvement_calibration
from ai_fund_lab_v2.opportunity_ai.quality_audit import audit_opportunity_quality
from ai_fund_lab_v2.opportunity_ai.random_date_outcome_check import run_random_date_outcome_check
from ai_fund_lab_v2.opportunity_ai.training import audit_opportunity_training_dataset, to_jsonable, train_opportunity_model

PHASE = "Phase5-P"

DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5p")
DEFAULT_BASELINE_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_BASELINE_CANDIDATE_PATH = Path("reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet")
DEFAULT_BASELINE_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_BASELINE_COMBINED_PATH = Path("reports/opportunity_ai/phase5i/full_history_combined_validation_metrics.json")
DEFAULT_BASELINE_RANDOM_PATH = Path("reports/opportunity_ai/phase5o/random_date_outcome_check.json")
DEFAULT_FEATURE_SOURCE_PATH = Path(".runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet")
DEFAULT_LISTED_ISSUES_PATH = Path(".runtime/data/raw/jquants/listed_issues/data.parquet")
DEFAULT_LATEST_INFERENCE_PATH = Path("reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet")
DEFAULT_LATEST_INFERENCE_SUMMARY_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_summary.json")
DEFAULT_LATEST_INFERENCE_AUDIT_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_audit.json")

MARKET_SECTOR_FEATURE_FILENAME = "market_sector_features.parquet"
DATASET_FILENAME = "opportunity_dataset_with_market_sector.parquet"
TRAINING_METRICS_FILENAME = "training_metrics.json"
QUALITY_METRICS_FILENAME = "quality_metrics.json"
COMBINED_METRICS_FILENAME = "combined_validation_metrics.json"
CALIBRATION_METRICS_FILENAME = "calibration_metrics.json"
RANDOM_OUTCOME_FILENAME = "random_date_outcome_check.json"
COMPARISON_FILENAME = "phase5p_vs_phase5_baseline_comparison.json"
AUDIT_FILENAME = "market_sector_completion_audit.json"
SUMMARY_FILENAME = "market_sector_completion_summary.json"
DOC_PATH = Path("docs/phase_reports/phase5p_market_sector_feature_completion.md")

MARKET_FEATURE_COLUMNS = (
    "feature__market_return_5d",
    "feature__market_return_20d",
    "feature__market_ma_5_20_ratio",
    "feature__market_volatility_20d",
    "feature__market_breadth_5d",
    "feature__market_breadth_20d",
    "feature__market_downtrend_flag",
    "feature__market_risk_flag",
)
SECTOR_FEATURE_COLUMNS = (
    "feature__sector_return_5d",
    "feature__sector_return_20d",
    "feature__sector_rank_20d",
    "feature__sector_breadth_20d",
    "feature__stock_vs_sector_return_20d",
    "feature__sector_momentum_flag",
    "feature__sector_weak_flag",
    "feature__market_downtrend_context",
)
FORBIDDEN_TERMS = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "downside_bad_",
    "top_decile_",
    "trade_result",
    "trade_profit",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "backtest",
    "paper_trading",
    "pm_multiplier",
)

PHASE5P_MARKET_SECTOR_IMPROVED = "PHASE5P_MARKET_SECTOR_IMPROVED"
PHASE5P_NO_CLEAR_IMPROVEMENT = "PHASE5P_NO_CLEAR_IMPROVEMENT"
PHASE5P_NEEDS_REWORK = "PHASE5P_NEEDS_REWORK"


@dataclass(frozen=True)
class MarketSectorCompletionResult:
    summary: dict[str, Any]
    audit: dict[str, Any]


def run_market_sector_feature_completion(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    baseline_dataset_path: Path = DEFAULT_BASELINE_DATASET_PATH,
    baseline_candidate_path: Path = DEFAULT_BASELINE_CANDIDATE_PATH,
    baseline_model_path: Path = DEFAULT_BASELINE_MODEL_PATH,
    baseline_combined_path: Path = DEFAULT_BASELINE_COMBINED_PATH,
    baseline_random_path: Path = DEFAULT_BASELINE_RANDOM_PATH,
    feature_source_path: Path = DEFAULT_FEATURE_SOURCE_PATH,
    listed_issues_path: Path = DEFAULT_LISTED_ISSUES_PATH,
    latest_inference_path: Path = DEFAULT_LATEST_INFERENCE_PATH,
    latest_inference_summary_path: Path = DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    latest_inference_audit_path: Path = DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    random_seed: int = 42,
    years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025),
    samples_per_year: int = 1,
    top_n: int = 5,
    created_at: str | None = None,
) -> MarketSectorCompletionResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir)
    missing_inputs = [
        str(path)
        for path in (
            baseline_dataset_path,
            baseline_candidate_path,
            baseline_model_path,
            baseline_combined_path,
            feature_source_path,
            listed_issues_path,
            latest_inference_path,
            latest_inference_summary_path,
            latest_inference_audit_path,
        )
        if not path.is_file()
    ]
    if missing_inputs:
        audit = blocked_audit(created_at, missing_inputs)
        summary = summary_shell(created_at, output_dir, paths, audit, readiness_status=PHASE5P_NEEDS_REWORK)
        write_json(paths["summary"], summary)
        write_json(paths["audit"], audit)
        return MarketSectorCompletionResult(summary, audit)

    baseline_dataset = pd.read_parquet(baseline_dataset_path)
    source_features = pd.read_parquet(feature_source_path)
    listed_issues = pd.read_parquet(listed_issues_path)
    market_sector_features = build_market_sector_features(
        source_features,
        listed_issues,
        target_dates=sorted(baseline_dataset["target_date"].astype(str).unique()),
        created_at=created_at,
    )
    market_sector_features.to_parquet(paths["market_sector_features"], index=False)
    dataset = attach_market_sector_features(baseline_dataset, market_sector_features, created_at=created_at)
    dataset.to_parquet(paths["dataset"], index=False)

    training_result = train_opportunity_model(
        dataset_path=paths["dataset"],
        model_dir=output_dir / "models",
        report_dir=output_dir / "training",
        created_at=created_at,
    )
    copy_json(Path(training_result.metrics["metrics_path"]), paths["training_metrics"])
    model_path = Path(training_result.metrics["model_artifact_path"])

    quality_result = audit_opportunity_quality(
        dataset_path=paths["dataset"],
        model_path=model_path,
        latest_inference_path=latest_inference_path,
        latest_inference_summary_path=latest_inference_summary_path,
        latest_inference_audit_path=latest_inference_audit_path,
        output_dir=output_dir / "quality",
        created_at=created_at,
    )
    copy_json(Path(quality_result.metrics["metrics_path"]), paths["quality_metrics"])

    combined_result = validate_candidate_opportunity_combined(
        dataset_path=paths["dataset"],
        model_path=model_path,
        latest_inference_path=latest_inference_path,
        latest_inference_summary_path=latest_inference_summary_path,
        latest_inference_audit_path=latest_inference_audit_path,
        output_dir=output_dir / "combined",
        created_at=created_at,
    )
    copy_json(Path(combined_result.metrics["metrics_path"]), paths["combined_metrics"])

    phase5p_audit_seed = build_intermediate_audit(
        created_at=created_at,
        baseline_dataset=baseline_dataset,
        dataset=dataset,
        market_sector_features=market_sector_features,
        training_audit=training_result.audit,
        combined_metrics=combined_result.metrics,
    )
    write_json(output_dir / "phase5p_intermediate_audit.json", phase5p_audit_seed)
    calibration_result = run_model_improvement_calibration(
        dataset_path=paths["dataset"],
        model_path=model_path,
        phase5i_metrics_path=paths["combined_metrics"],
        phase5i_audit_path=output_dir / "phase5p_intermediate_audit.json",
        output_dir=output_dir / "calibration",
        created_at=created_at,
    )
    copy_json(Path(calibration_result.metrics["metrics_path"]), paths["calibration_metrics"])

    random_result = run_random_date_outcome_check(
        candidate_path=baseline_candidate_path,
        dataset_path=paths["dataset"],
        model_path=model_path,
        output_dir=output_dir / "random_date",
        doc_path=output_dir / "random_date_outcome_check.md",
        years=list(years),
        samples_per_year=samples_per_year,
        top_n=top_n,
        seed=random_seed,
        created_at=created_at,
    )
    copy_json(output_dir / "random_date" / "random_date_outcome_check.json", paths["random_outcome"])
    shutil.copy2(output_dir / "random_date" / "random_date_outcome_by_date.csv", output_dir / "random_date_outcome_by_date.csv")
    shutil.copy2(output_dir / "random_date" / "random_date_outcome_by_stock.csv", output_dir / "random_date_outcome_by_stock.csv")

    baseline_combined = read_json(baseline_combined_path)
    baseline_random = read_json_optional(baseline_random_path)
    comparison = build_baseline_comparison(
        baseline_combined=baseline_combined,
        new_combined=combined_result.metrics,
        baseline_random=baseline_random,
        new_random=random_result.summary,
    )
    write_json(paths["comparison"], comparison)

    audit = build_final_audit(
        created_at=created_at,
        baseline_dataset=baseline_dataset,
        dataset=dataset,
        market_sector_features=market_sector_features,
        training_audit=training_result.audit,
        combined_metrics=combined_result.metrics,
        calibration_metrics=calibration_result.metrics,
        random_summary=random_result.summary,
        comparison=comparison,
        listed_issues=listed_issues,
    )
    readiness_status = resolve_readiness(audit, comparison)
    audit["readiness_status"] = readiness_status
    summary = build_summary(
        created_at=created_at,
        output_dir=output_dir,
        paths=paths,
        audit=audit,
        comparison=comparison,
        training_metrics=training_result.metrics,
        quality_metrics=quality_result.metrics,
        combined_metrics=combined_result.metrics,
        calibration_metrics=calibration_result.metrics,
        random_summary=random_result.summary,
    )
    write_json(paths["audit"], audit)
    write_json(paths["summary"], summary)
    write_markdown_report(DOC_PATH, summary)
    return MarketSectorCompletionResult(summary, audit)


def build_market_sector_features(
    source: pd.DataFrame,
    listed_issues: pd.DataFrame,
    *,
    target_dates: list[str],
    created_at: str,
) -> pd.DataFrame:
    required = {
        "target_date",
        "code",
        "price_momentum_return_5d",
        "price_momentum_return_20d",
        "trend_ma_5_20_ratio",
        "volatility_return_std_20d",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"source feature table missing required columns: {', '.join(missing)}")
    frame = source[source["target_date"].astype(str).isin(set(target_dates))].copy()
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    for column in required - {"target_date", "code"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    sector_map = build_sector_map(listed_issues)
    frame = frame.merge(sector_map, on="code", how="left")
    frame["sector_key"] = frame["sector_key"].fillna("UNKNOWN")

    usable = frame.dropna(subset=["price_momentum_return_20d"]).copy()
    market = (
        usable.groupby("target_date", as_index=False)
        .agg(
            market_return_5d=("price_momentum_return_5d", "mean"),
            market_return_20d=("price_momentum_return_20d", "mean"),
            market_ma_5_20_ratio=("trend_ma_5_20_ratio", "mean"),
            market_volatility_20d=("volatility_return_std_20d", "mean"),
            market_breadth_5d=("price_momentum_return_5d", positive_rate),
            market_breadth_20d=("price_momentum_return_20d", positive_rate),
        )
    )
    market["market_downtrend_flag"] = (market["market_return_20d"] < 0) | (market["market_breadth_20d"] < 0.45)
    market["market_risk_flag"] = market["market_downtrend_flag"] | (market["market_volatility_20d"] > market["market_volatility_20d"].quantile(0.75))

    sector = (
        usable.groupby(["target_date", "sector_key"], as_index=False)
        .agg(
            sector_return_5d=("price_momentum_return_5d", "mean"),
            sector_return_20d=("price_momentum_return_20d", "mean"),
            sector_breadth_20d=("price_momentum_return_20d", positive_rate),
            sector_member_count=("code", "count"),
        )
    )
    sector["sector_rank_20d"] = sector.groupby("target_date")["sector_return_20d"].rank(method="dense", ascending=False)
    sector["sector_count_on_date"] = sector.groupby("target_date")["sector_key"].transform("count")
    sector["sector_rank_20d"] = sector["sector_rank_20d"] / sector["sector_count_on_date"].replace(0, np.nan)
    sector["sector_momentum_flag"] = (sector["sector_rank_20d"] <= 0.30) & (sector["sector_return_20d"] > 0)
    sector["sector_weak_flag"] = (sector["sector_rank_20d"] >= 0.70) | (sector["sector_return_20d"] < 0)

    out = frame[["target_date", "code", "sector_key", "price_momentum_return_20d"]].merge(market, on="target_date", how="left")
    out = out.merge(
        sector[
            [
                "target_date",
                "sector_key",
                "sector_return_5d",
                "sector_return_20d",
                "sector_rank_20d",
                "sector_breadth_20d",
                "sector_momentum_flag",
                "sector_weak_flag",
            ]
        ],
        on=["target_date", "sector_key"],
        how="left",
    )
    out["stock_vs_sector_return_20d"] = out["price_momentum_return_20d"] - out["sector_return_20d"]
    out["market_downtrend_context"] = out["market_downtrend_flag"]
    out["as_of_date"] = out["target_date"]
    out["feature_version"] = "opportunity_feature_v1_1_market_sector"
    out["feature_set_name"] = "opportunity_market_sector_jquants_proxy_v1"
    out["created_at"] = created_at
    out = out.drop(columns=["price_momentum_return_20d"])
    return out.drop_duplicates(["target_date", "code"], keep="first")


def build_sector_map(listed_issues: pd.DataFrame) -> pd.DataFrame:
    frame = listed_issues.copy()
    frame["code"] = frame.get("code", frame.get("Code")).astype(str)
    sector = frame.get("S33Nm", frame.get("S17Nm", pd.Series(["UNKNOWN"] * len(frame))))
    frame["sector_key"] = sector.fillna("UNKNOWN").astype(str)
    return frame[["code", "sector_key"]].drop_duplicates("code", keep="last")


def attach_market_sector_features(dataset: pd.DataFrame, features: pd.DataFrame, *, created_at: str) -> pd.DataFrame:
    dataset = dataset.copy()
    features = features.copy()
    dataset["target_date"] = dataset["target_date"].astype(str)
    dataset["code"] = dataset["code"].astype(str)
    features["target_date"] = features["target_date"].astype(str)
    features["code"] = features["code"].astype(str)
    rename = {
        column: f"feature__{column}"
        for column in (
            "market_return_5d",
            "market_return_20d",
            "market_ma_5_20_ratio",
            "market_volatility_20d",
            "market_breadth_5d",
            "market_breadth_20d",
            "market_downtrend_flag",
            "market_risk_flag",
            "sector_return_5d",
            "sector_return_20d",
            "sector_rank_20d",
            "sector_breadth_20d",
            "stock_vs_sector_return_20d",
            "sector_momentum_flag",
            "sector_weak_flag",
            "market_downtrend_context",
        )
    }
    part = features[["target_date", "code", *rename.keys()]].rename(columns=rename)
    out = dataset.merge(part, on=["target_date", "code"], how="left", validate="one_to_one")
    bool_cols = [
        "feature__market_downtrend_flag",
        "feature__market_risk_flag",
        "feature__sector_momentum_flag",
        "feature__sector_weak_flag",
        "feature__market_downtrend_context",
    ]
    for column in bool_cols:
        out[column] = out[column].fillna(False).astype(bool)
    out["feature_version"] = "opportunity_feature_v1_1_market_sector"
    out["dataset_version"] = "opportunity_dataset_v1_1_market_sector"
    out["created_at"] = created_at
    return out


def positive_rate(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float((numeric > 0).mean()) if len(numeric) else 0.0


def build_baseline_comparison(
    *,
    baseline_combined: dict[str, Any],
    new_combined: dict[str, Any],
    baseline_random: dict[str, Any],
    new_random: dict[str, Any],
) -> dict[str, Any]:
    combined = {}
    for split in ("validation", "test"):
        combined[split] = {}
        for topn in ("top5", "top10", "top20"):
            old_value = metric_from_combined(baseline_combined, split, topn)
            new_value = metric_from_combined(new_combined, split, topn)
            combined[split][topn] = {
                "baseline_mean_future_return_20d": old_value,
                "phase5p_mean_future_return_20d": new_value,
                "delta": round_float(new_value - old_value),
                "improved": new_value > old_value,
            }
    old_2022 = random_date_metric(baseline_random, "2022-01-13")
    new_2022 = random_date_metric(new_random, "2022-01-13")
    random_dates = {
        "baseline_effective_dates": baseline_random.get("opportunity_effective_dates_20bd_vs_candidate_top50", []),
        "phase5p_effective_dates": new_random.get("opportunity_effective_dates_20bd_vs_candidate_top50", []),
        "baseline_2022_01_13_opportunity_top5_mean_return_20bd": old_2022,
        "phase5p_2022_01_13_opportunity_top5_mean_return_20bd": new_2022,
        "phase5p_minus_baseline_2022_01_13": round_float(new_2022 - old_2022),
        "date_2022_01_13_improved": new_2022 > old_2022,
    }
    return {
        "phase": PHASE,
        "combined_validation": combined,
        "random_date_outcome": random_dates,
        "any_topn_improved": any(block[topn]["improved"] for block in combined.values() for topn in block),
        "failure_date_2022_01_13_improved": random_dates["date_2022_01_13_improved"],
    }


def metric_from_combined(metrics: dict[str, Any], split: str, topn: str) -> float:
    try:
        return float(metrics["quality_metrics"][split]["rankers"]["model"][topn]["selected_mean_future_return"])
    except Exception:
        return 0.0


def random_date_metric(summary: dict[str, Any], target_date: str) -> float:
    for row in summary.get("by_date_records", []):
        if row.get("target_date") == target_date and row.get("selection_group") == "OpportunityTop5":
            return float(row.get("mean_return_20bd", 0.0))
    return 0.0


def build_intermediate_audit(
    *,
    created_at: str,
    baseline_dataset: pd.DataFrame,
    dataset: pd.DataFrame,
    market_sector_features: pd.DataFrame,
    training_audit: dict[str, Any],
    combined_metrics: dict[str, Any],
) -> dict[str, Any]:
    return build_final_audit(
        created_at=created_at,
        baseline_dataset=baseline_dataset,
        dataset=dataset,
        market_sector_features=market_sector_features,
        training_audit=training_audit,
        combined_metrics=combined_metrics,
        calibration_metrics={},
        random_summary={},
        comparison={},
    )


def build_final_audit(
    *,
    created_at: str,
    baseline_dataset: pd.DataFrame,
    dataset: pd.DataFrame,
    market_sector_features: pd.DataFrame,
    training_audit: dict[str, Any],
    combined_metrics: dict[str, Any],
    calibration_metrics: dict[str, Any],
    random_summary: dict[str, Any],
    comparison: dict[str, Any],
    listed_issues: pd.DataFrame | None = None,
) -> dict[str, Any]:
    feature_columns = sorted(column for column in dataset.columns if str(column).startswith("feature__"))
    label_columns = sorted(column for column in dataset.columns if str(column).startswith("label__"))
    audit = audit_opportunity_training_dataset(dataset, feature_columns=feature_columns, label_columns=label_columns, created_at=created_at)
    added_market = [column for column in feature_columns if column in MARKET_FEATURE_COLUMNS]
    added_sector = [column for column in feature_columns if column in SECTOR_FEATURE_COLUMNS]
    forbidden = [column for column in feature_columns if any(term in column.lower() for term in FORBIDDEN_TERMS)]
    sector_master_audit = audit_sector_master_snapshot(listed_issues, dataset)
    return {
        "phase": PHASE,
        "created_at": created_at,
        "feature_count_before": int(len([c for c in baseline_dataset.columns if str(c).startswith("feature__")])),
        "feature_count_after": int(len(feature_columns)),
        "added_market_feature_count": int(len(added_market)),
        "added_sector_feature_count": int(len(added_sector)),
        "added_market_features": added_market,
        "added_sector_features": added_sector,
        "forbidden_feature_count": int(len(forbidden)),
        "future_feature_count": int(audit.get("future_feature_column_count", 0)),
        "trade_backtest_portfolio_feature_count": int(
            audit.get("trade_result_feature_column_count", 0)
            + audit.get("backtest_feature_column_count", 0)
            + audit.get("portfolio_feature_column_count", 0)
        ),
        "as_of_date_violation_count": int(count_as_of_violations(dataset)),
        "sector_master_historical_as_of_available": sector_master_audit["historical_as_of_available"],
        "sector_master_snapshot_proxy_warning": sector_master_audit["snapshot_proxy_warning"],
        "sector_master_snapshot_date_min": sector_master_audit["snapshot_date_min"],
        "sector_master_snapshot_date_max": sector_master_audit["snapshot_date_max"],
        "sector_master_rows_with_date_after_dataset_min_target_date": sector_master_audit["rows_with_date_after_dataset_min_target_date"],
        "leakage_status": "OK" if not forbidden and audit.get("leakage_audit_status") == "OK" else "ERROR",
        "full_history_target_date_count": int(dataset["target_date"].nunique()),
        "dataset_rows": int(len(dataset)),
        "train_rows": int((dataset["split"] == "train").sum()),
        "validation_rows": int((dataset["split"] == "validation").sum()),
        "test_rows": int((dataset["split"] == "test").sum()),
        "market_sector_feature_rows": int(len(market_sector_features)),
        "market_sector_join_coverage": round_float(dataset[list(MARKET_FEATURE_COLUMNS) + list(SECTOR_FEATURE_COLUMNS)].notna().all(axis=1).mean()),
        "model_unique_score_count": int(combined_metrics.get("score_distribution", {}).get("model_unique_score_count", 0)),
        "score_collapse": bool(combined_metrics.get("score_distribution", {}).get("model_all_same_score", True)),
        "old_vs_new_top5_test_delta": comparison.get("combined_validation", {}).get("test", {}).get("top5", {}).get("delta", 0.0),
        "old_vs_new_top10_test_delta": comparison.get("combined_validation", {}).get("test", {}).get("top10", {}).get("delta", 0.0),
        "old_vs_new_top20_test_delta": comparison.get("combined_validation", {}).get("test", {}).get("top20", {}).get("delta", 0.0),
        "old_vs_new_random_date_2022_01_13_delta": comparison.get("random_date_outcome", {}).get("phase5p_minus_baseline_2022_01_13", 0.0),
        "calibration_readiness_status": calibration_metrics.get("readiness_status"),
        "random_date_status": random_summary.get("status"),
        "promotion_ready": False,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "sector_mapping_source_note": "J-Quants listed issue master snapshot currently available in local artifacts; daily market features are J-Quants-derived full-history features.",
    }


def audit_sector_master_snapshot(listed_issues: pd.DataFrame | None, dataset: pd.DataFrame) -> dict[str, Any]:
    if listed_issues is None or listed_issues.empty or "Date" not in listed_issues.columns:
        return {
            "historical_as_of_available": False,
            "snapshot_proxy_warning": True,
            "snapshot_date_min": None,
            "snapshot_date_max": None,
            "rows_with_date_after_dataset_min_target_date": 0,
        }
    dates = pd.to_datetime(listed_issues["Date"], errors="coerce")
    min_target = pd.to_datetime(dataset["target_date"], errors="coerce").min()
    unique_dates = dates.dropna().dt.strftime("%Y-%m-%d").unique().tolist()
    historical_available = bool(len(unique_dates) > 1 or (dates.dropna().min() <= min_target))
    return {
        "historical_as_of_available": historical_available,
        "snapshot_proxy_warning": not historical_available,
        "snapshot_date_min": str(dates.dropna().min().date()) if len(dates.dropna()) else None,
        "snapshot_date_max": str(dates.dropna().max().date()) if len(dates.dropna()) else None,
        "rows_with_date_after_dataset_min_target_date": int((dates > min_target).sum()) if pd.notna(min_target) else 0,
    }


def resolve_readiness(audit: dict[str, Any], comparison: dict[str, Any]) -> str:
    if audit["leakage_status"] != "OK" or audit["as_of_date_violation_count"] or audit["score_collapse"]:
        return PHASE5P_NEEDS_REWORK
    if comparison.get("any_topn_improved") or comparison.get("failure_date_2022_01_13_improved"):
        return PHASE5P_MARKET_SECTOR_IMPROVED
    return PHASE5P_NO_CLEAR_IMPROVEMENT


def build_summary(
    *,
    created_at: str,
    output_dir: Path,
    paths: dict[str, Path],
    audit: dict[str, Any],
    comparison: dict[str, Any],
    training_metrics: dict[str, Any],
    quality_metrics: dict[str, Any],
    combined_metrics: dict[str, Any],
    calibration_metrics: dict[str, Any],
    random_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": audit["readiness_status"],
        "created_at": created_at,
        "output_dir": str(output_dir),
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "audit": audit,
        "comparison": comparison,
        "training_readiness_status": training_metrics.get("readiness_status"),
        "quality_readiness_status": quality_metrics.get("readiness_status"),
        "combined_readiness_status": combined_metrics.get("readiness_status"),
        "calibration_readiness_status": calibration_metrics.get("readiness_status"),
        "random_date_initial_conclusion": random_summary.get("initial_conclusion"),
        "promotion_ready": False,
        "recommended_next_action": (
            "Market/Sector design deviation is connected; review metrics before any future promotion."
            if audit["readiness_status"] != PHASE5P_NEEDS_REWORK
            else "Review Phase5-P leakage, join, or score collapse blocker."
        ),
    }


def write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    audit = summary["audit"]
    comparison = summary["comparison"]
    lines = [
        "# Phase5-P Market / Sector Feature Completion",
        "",
        "## Summary",
        "",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- promotion_ready: `{summary['promotion_ready']}`",
        f"- feature count before / after: `{audit['feature_count_before']}` / `{audit['feature_count_after']}`",
        f"- added market / sector feature count: `{audit['added_market_feature_count']}` / `{audit['added_sector_feature_count']}`",
        f"- leakage_status: `{audit['leakage_status']}`",
        f"- full history rows: `{audit['dataset_rows']}`",
        f"- sector master snapshot proxy warning: `{audit.get('sector_master_snapshot_proxy_warning')}`",
        "",
        "## Added Features",
        "",
        "- market: `" + "`, `".join(audit["added_market_features"]) + "`",
        "- sector: `" + "`, `".join(audit["added_sector_features"]) + "`",
        "",
        "## Baseline Comparison",
        "",
        json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True),
        "",
        "## Safety",
        "",
        "- No Broker API, Paper Trading, order placement, capital allocation, promotion, or reader switch was performed.",
        "- Future outcomes remain evaluation-only and are not feature columns.",
        "- Fundamental features remain outside Phase5-P scope.",
        "- Sector strength uses the local J-Quants listed issue master snapshot available in artifacts; historical listed-master snapshots were not present, so this is recorded as a source limitation.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "market_sector_features": output_dir / MARKET_SECTOR_FEATURE_FILENAME,
        "dataset": output_dir / DATASET_FILENAME,
        "training_metrics": output_dir / TRAINING_METRICS_FILENAME,
        "quality_metrics": output_dir / QUALITY_METRICS_FILENAME,
        "combined_metrics": output_dir / COMBINED_METRICS_FILENAME,
        "calibration_metrics": output_dir / CALIBRATION_METRICS_FILENAME,
        "random_outcome": output_dir / RANDOM_OUTCOME_FILENAME,
        "comparison": output_dir / COMPARISON_FILENAME,
        "audit": output_dir / AUDIT_FILENAME,
        "summary": output_dir / SUMMARY_FILENAME,
        "doc": DOC_PATH,
    }


def blocked_audit(created_at: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "missing_inputs": missing_inputs,
        "leakage_status": "NOT_RUN",
        "promotion_ready": False,
        "readiness_status": PHASE5P_NEEDS_REWORK,
    }


def summary_shell(created_at: str, output_dir: Path, paths: dict[str, Path], audit: dict[str, Any], *, readiness_status: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "output_dir": str(output_dir),
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "audit": audit,
        "promotion_ready": False,
    }


def count_as_of_violations(dataset: pd.DataFrame) -> int:
    if "as_of_date" not in dataset.columns or "target_date" not in dataset.columns:
        return 0
    as_of = pd.to_datetime(dataset["as_of_date"], errors="coerce")
    target = pd.to_datetime(dataset["target_date"], errors="coerce")
    return int(((as_of > target) | as_of.isna() | target.isna()).sum())


def copy_json(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_optional(path: Path) -> dict[str, Any]:
    return read_json(path) if path.is_file() else {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def round_float(value: Any, digits: int = 6) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
