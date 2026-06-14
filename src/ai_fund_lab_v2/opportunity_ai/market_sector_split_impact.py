from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.combined_validation import validate_candidate_opportunity_combined
from ai_fund_lab_v2.opportunity_ai.market_sector_completion import (
    MARKET_FEATURE_COLUMNS,
    SECTOR_FEATURE_COLUMNS,
    read_json,
    read_json_optional,
    round_float,
)
from ai_fund_lab_v2.opportunity_ai.random_date_outcome_check import run_random_date_outcome_check
from ai_fund_lab_v2.opportunity_ai.training import audit_opportunity_training_dataset, to_jsonable, train_opportunity_model

PHASE = "Phase5-P2"

DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5p2")
DEFAULT_BASELINE_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_BASELINE_CANDIDATE_PATH = Path("reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet")
DEFAULT_BASELINE_COMBINED_PATH = Path("reports/opportunity_ai/phase5i/full_history_combined_validation_metrics.json")
DEFAULT_BASELINE_RANDOM_PATH = Path("reports/opportunity_ai/phase5o/random_date_outcome_check.json")
DEFAULT_PHASE5P_DATASET_PATH = Path("reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet")
DEFAULT_PHASE5P_AUDIT_PATH = Path("reports/opportunity_ai/phase5p/market_sector_completion_audit.json")
DEFAULT_LATEST_INFERENCE_PATH = Path("reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet")
DEFAULT_LATEST_INFERENCE_SUMMARY_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_summary.json")
DEFAULT_LATEST_INFERENCE_AUDIT_PATH = Path("reports/opportunity_ai/phase5f/opportunity_inference_audit.json")

METRICS_FILENAME = "split_impact_metrics.json"
AUDIT_FILENAME = "split_impact_audit.json"
BY_STRATEGY_FILENAME = "split_impact_by_strategy.csv"
RANDOM_COMPARISON_FILENAME = "random_date_comparison.csv"
DOC_PATH = Path("docs/phase_reports/phase5p2_market_sector_split_impact_audit.md")

MARKET_ONLY_IMPROVES = "MARKET_ONLY_IMPROVES"
SECTOR_ONLY_IMPROVES = "SECTOR_ONLY_IMPROVES"
MARKET_AND_SECTOR_IMPROVES = "MARKET_AND_SECTOR_IMPROVES"
MARKET_SECTOR_NO_CLEAR_IMPROVEMENT = "MARKET_SECTOR_NO_CLEAR_IMPROVEMENT"
NEEDS_REWORK = "NEEDS_REWORK"

STRATEGY_FEATURES = {
    "market_only": set(MARKET_FEATURE_COLUMNS),
    "sector_only": set(SECTOR_FEATURE_COLUMNS),
    "market_sector": set(MARKET_FEATURE_COLUMNS) | set(SECTOR_FEATURE_COLUMNS),
}


@dataclass(frozen=True)
class SplitImpactResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]
    by_strategy: pd.DataFrame
    random_comparison: pd.DataFrame


def run_market_sector_split_impact_audit(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    baseline_dataset_path: Path = DEFAULT_BASELINE_DATASET_PATH,
    baseline_candidate_path: Path = DEFAULT_BASELINE_CANDIDATE_PATH,
    baseline_combined_path: Path = DEFAULT_BASELINE_COMBINED_PATH,
    baseline_random_path: Path = DEFAULT_BASELINE_RANDOM_PATH,
    phase5p_dataset_path: Path = DEFAULT_PHASE5P_DATASET_PATH,
    phase5p_audit_path: Path = DEFAULT_PHASE5P_AUDIT_PATH,
    latest_inference_path: Path = DEFAULT_LATEST_INFERENCE_PATH,
    latest_inference_summary_path: Path = DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    latest_inference_audit_path: Path = DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    random_seed: int = 42,
    years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025),
    samples_per_year: int = 1,
    top_n: int = 5,
    created_at: str | None = None,
) -> SplitImpactResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir)
    missing_inputs = [
        str(path)
        for path in (
            baseline_dataset_path,
            baseline_candidate_path,
            baseline_combined_path,
            baseline_random_path,
            phase5p_dataset_path,
            phase5p_audit_path,
            latest_inference_path,
            latest_inference_summary_path,
            latest_inference_audit_path,
        )
        if not path.is_file()
    ]
    if missing_inputs:
        audit = blocked_audit(created_at, missing_inputs)
        metrics = metrics_shell(created_at, paths, audit)
        by_strategy = pd.DataFrame()
        random_comparison = pd.DataFrame()
        write_outputs(paths, metrics, audit, by_strategy, random_comparison)
        return SplitImpactResult(metrics, audit, by_strategy, random_comparison)

    baseline_dataset = pd.read_parquet(baseline_dataset_path)
    phase5p_dataset = pd.read_parquet(phase5p_dataset_path)
    baseline_combined = read_json(baseline_combined_path)
    baseline_random = read_json(baseline_random_path)
    phase5p_audit = read_json_optional(phase5p_audit_path)
    baseline_feature_columns = sorted(column for column in baseline_dataset.columns if str(column).startswith("feature__"))

    strategy_results: dict[str, dict[str, Any]] = {}
    strategy_datasets: dict[str, Path] = {}
    for strategy_name, added_columns in STRATEGY_FEATURES.items():
        strategy_dir = output_dir / strategy_name
        strategy_dir.mkdir(parents=True, exist_ok=True)
        dataset = select_strategy_dataset(
            phase5p_dataset,
            feature_columns=baseline_feature_columns + sorted(added_columns),
            created_at=created_at,
            strategy_name=strategy_name,
        )
        dataset_path = strategy_dir / "opportunity_dataset.parquet"
        dataset.to_parquet(dataset_path, index=False)
        strategy_datasets[strategy_name] = dataset_path

        training = train_opportunity_model(
            dataset_path=dataset_path,
            model_dir=strategy_dir / "models",
            report_dir=strategy_dir / "training",
            created_at=created_at,
        )
        model_path = Path(training.metrics["model_artifact_path"])
        combined = validate_candidate_opportunity_combined(
            dataset_path=dataset_path,
            model_path=model_path,
            latest_inference_path=latest_inference_path,
            latest_inference_summary_path=latest_inference_summary_path,
            latest_inference_audit_path=latest_inference_audit_path,
            output_dir=strategy_dir / "combined",
            created_at=created_at,
        )
        random_result = run_random_date_outcome_check(
            candidate_path=baseline_candidate_path,
            dataset_path=dataset_path,
            model_path=model_path,
            output_dir=strategy_dir / "random_date",
            doc_path=strategy_dir / "random_date_outcome_check.md",
            years=list(years),
            samples_per_year=samples_per_year,
            top_n=top_n,
            seed=random_seed,
            created_at=created_at,
        )
        strategy_results[strategy_name] = {
            "dataset_path": str(dataset_path),
            "model_path": str(model_path),
            "training_metrics": training.metrics,
            "training_audit": training.audit,
            "combined_metrics": combined.metrics,
            "combined_audit": combined.audit,
            "random_summary": random_result.summary,
        }

    by_strategy = build_by_strategy_table(
        baseline_combined=baseline_combined,
        strategy_results=strategy_results,
    )
    random_comparison = build_random_comparison_table(
        baseline_random=baseline_random,
        strategy_results=strategy_results,
    )
    conclusion = build_conclusion(by_strategy, random_comparison)
    audit = build_audit(
        created_at=created_at,
        baseline_dataset=baseline_dataset,
        phase5p_dataset=phase5p_dataset,
        phase5p_audit=phase5p_audit,
        strategy_results=strategy_results,
        by_strategy=by_strategy,
        random_comparison=random_comparison,
        conclusion=conclusion,
    )
    metrics = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": conclusion["readiness_status"],
        "created_at": created_at,
        "promotion_ready": False,
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "strategy_dataset_paths": {key: str(path) for key, path in strategy_datasets.items()},
        "baseline_dataset_path": str(baseline_dataset_path),
        "phase5p_dataset_path": str(phase5p_dataset_path),
        "conclusion": conclusion,
        "sector_master_snapshot_proxy_warning": bool(phase5p_audit.get("sector_master_snapshot_proxy_warning", False)),
        "sector_master_source_note": phase5p_audit.get("sector_mapping_source_note"),
        "training_executed": True,
        "evaluation_executed": True,
        "random_date_outcome_executed": True,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "summary_by_strategy": by_strategy.to_dict("records"),
        "random_date_comparison": random_comparison.to_dict("records"),
    }
    write_outputs(paths, metrics, audit, by_strategy, random_comparison)
    write_markdown_report(DOC_PATH, metrics)
    return SplitImpactResult(metrics, audit, by_strategy, random_comparison)


def select_strategy_dataset(dataset: pd.DataFrame, *, feature_columns: list[str], created_at: str, strategy_name: str) -> pd.DataFrame:
    meta_columns = [column for column in dataset.columns if not str(column).startswith("feature__") and not str(column).startswith("label__")]
    label_columns = sorted(column for column in dataset.columns if str(column).startswith("label__"))
    available_features = [column for column in feature_columns if column in dataset.columns]
    out = dataset[meta_columns + available_features + label_columns].copy()
    out["dataset_version"] = f"opportunity_dataset_v1_1_{strategy_name}"
    out["feature_version"] = f"opportunity_feature_v1_1_{strategy_name}"
    out["created_at"] = created_at
    return out


def build_by_strategy_table(*, baseline_combined: dict[str, Any], strategy_results: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for strategy in ("baseline", *strategy_results.keys()):
        metrics = baseline_combined if strategy == "baseline" else strategy_results[strategy]["combined_metrics"]
        for split in ("validation", "test"):
            for topn in ("top5", "top10", "top20"):
                block = combined_metric_block(metrics, split, topn)
                baseline_block = combined_metric_block(baseline_combined, split, topn)
                rows.append(
                    {
                        "strategy": strategy,
                        "split": split,
                        "selection": topn,
                        "mean_return_20d": block["selected_mean_future_return"],
                        "future_max_return_20d": block["selected_mean_future_max_return"],
                        "downside_bad_rate": block["selected_downside_bad_rate"],
                        "max_drawdown_20d": block["selected_mean_future_max_drawdown"],
                        "win_rate_20d": block["win_rate_20d"],
                        "delta_mean_return_20d_vs_baseline": round_float(block["selected_mean_future_return"] - baseline_block["selected_mean_future_return"]),
                    }
                )
    return pd.DataFrame(rows)


def build_random_comparison_table(*, baseline_random: dict[str, Any], strategy_results: dict[str, dict[str, Any]]) -> pd.DataFrame:
    baseline_effective = set(baseline_random.get("opportunity_effective_dates_20bd_vs_candidate_top50", []))
    rows = [
        random_row("baseline", baseline_random, baseline_effective, baseline_random),
    ]
    for strategy_name, result in strategy_results.items():
        rows.append(random_row(strategy_name, result["random_summary"], baseline_effective, baseline_random))
    return pd.DataFrame(rows)


def random_row(strategy: str, summary: dict[str, Any], baseline_effective: set[str], baseline_random: dict[str, Any]) -> dict[str, Any]:
    effective = set(summary.get("opportunity_effective_dates_20bd_vs_candidate_top50", []))
    target = "2022-01-13"
    value_2022 = random_date_metric(summary, target)
    baseline_2022 = random_date_metric(baseline_random, target)
    return {
        "strategy": strategy,
        "sampled_target_dates": "|".join(summary.get("sampled_target_dates", [])),
        "effective_date_count": len(effective),
        "effective_dates": "|".join(sorted(effective)),
        "newly_effective_dates_vs_baseline": "|".join(sorted(effective - baseline_effective)),
        "opportunity_top5_2022_01_13_mean_return_20bd": value_2022,
        "delta_2022_01_13_vs_baseline": round_float(value_2022 - baseline_2022),
        "date_2022_01_13_improved": value_2022 > baseline_2022,
    }


def build_conclusion(by_strategy: pd.DataFrame, random_comparison: pd.DataFrame) -> dict[str, Any]:
    test_topn = by_strategy[(by_strategy["split"] == "test") & (by_strategy["selection"].isin(["top5", "top10", "top20"]))]
    improvements = {
        strategy: bool((frame["delta_mean_return_20d_vs_baseline"] > 0).any())
        for strategy, frame in test_topn.groupby("strategy")
        if strategy != "baseline"
    }
    random_improvements = {
        row["strategy"]: bool(row["date_2022_01_13_improved"] or row["effective_date_count"] > random_comparison.loc[random_comparison["strategy"] == "baseline", "effective_date_count"].iloc[0])
        for row in random_comparison.to_dict("records")
        if row["strategy"] != "baseline"
    }
    combined_signal = {strategy: improvements.get(strategy, False) or random_improvements.get(strategy, False) for strategy in improvements}
    if combined_signal.get("market_only") and not combined_signal.get("sector_only"):
        readiness = MARKET_ONLY_IMPROVES
    elif combined_signal.get("sector_only") and not combined_signal.get("market_only"):
        readiness = SECTOR_ONLY_IMPROVES
    elif combined_signal.get("market_sector"):
        readiness = MARKET_AND_SECTOR_IMPROVES
    elif any(combined_signal.values()):
        readiness = MARKET_AND_SECTOR_IMPROVES
    else:
        readiness = MARKET_SECTOR_NO_CLEAR_IMPROVEMENT
    likely_cause = infer_likely_cause(by_strategy, random_comparison)
    return {
        "readiness_status": readiness,
        "test_topn_mean_return_improvement_by_strategy": improvements,
        "random_date_improvement_by_strategy": random_improvements,
        "combined_improvement_signal": combined_signal,
        "likely_full_history_degradation_cause": likely_cause,
        "promotion_ready": False,
    }


def infer_likely_cause(by_strategy: pd.DataFrame, random_comparison: pd.DataFrame) -> str:
    test = by_strategy[(by_strategy["split"] == "test") & (by_strategy["strategy"] != "baseline")]
    avg_delta = test.groupby("strategy")["delta_mean_return_20d_vs_baseline"].mean().to_dict()
    random_2022 = {
        row["strategy"]: row["delta_2022_01_13_vs_baseline"]
        for row in random_comparison.to_dict("records")
        if row["strategy"] != "baseline"
    }
    worst = min(avg_delta, key=avg_delta.get) if avg_delta else "unknown"
    best_random = max(random_2022, key=random_2022.get) if random_2022 else "unknown"
    return (
        f"Full-history test degradation is strongest in `{worst}` by average TopN return delta, "
        f"while random-date failure-day improvement is strongest in `{best_random}`. "
        "This suggests market/sector context helps specific adverse dates but may dilute broad test ranking."
    )


def build_audit(
    *,
    created_at: str,
    baseline_dataset: pd.DataFrame,
    phase5p_dataset: pd.DataFrame,
    phase5p_audit: dict[str, Any],
    strategy_results: dict[str, dict[str, Any]],
    by_strategy: pd.DataFrame,
    random_comparison: pd.DataFrame,
    conclusion: dict[str, Any],
) -> dict[str, Any]:
    strategy_audits = {name: result["training_audit"] for name, result in strategy_results.items()}
    feature_columns = sorted(column for column in phase5p_dataset.columns if str(column).startswith("feature__"))
    label_columns = sorted(column for column in phase5p_dataset.columns if str(column).startswith("label__"))
    aggregate_audit = audit_opportunity_training_dataset(phase5p_dataset, feature_columns=feature_columns, label_columns=label_columns, created_at=created_at)
    leakage_ok = aggregate_audit.get("leakage_audit_status") == "OK" and all(audit.get("leakage_audit_status") == "OK" for audit in strategy_audits.values())
    return {
        "phase": PHASE,
        "created_at": created_at,
        "baseline_feature_count": int(len([c for c in baseline_dataset.columns if str(c).startswith("feature__")])),
        "phase5p_feature_count": int(len([c for c in phase5p_dataset.columns if str(c).startswith("feature__")])),
        "market_feature_count": len(MARKET_FEATURE_COLUMNS),
        "sector_feature_count": len(SECTOR_FEATURE_COLUMNS),
        "strategies_evaluated": sorted(strategy_results.keys()),
        "strategy_count": len(strategy_results),
        "full_history_rows": int(len(phase5p_dataset)),
        "target_date_count": int(phase5p_dataset["target_date"].nunique()),
        "train_rows": int((phase5p_dataset["split"] == "train").sum()),
        "validation_rows": int((phase5p_dataset["split"] == "validation").sum()),
        "test_rows": int((phase5p_dataset["split"] == "test").sum()),
        "leakage_status": "OK" if leakage_ok else "ERROR",
        "forbidden_feature_count": int(aggregate_audit.get("forbidden_feature_column_count", 0)),
        "future_feature_count": int(aggregate_audit.get("future_feature_column_count", 0)),
        "sector_master_snapshot_proxy_warning": bool(phase5p_audit.get("sector_master_snapshot_proxy_warning", False)),
        "sector_master_historical_as_of_available": bool(phase5p_audit.get("sector_master_historical_as_of_available", False)),
        "sector_master_snapshot_date_min": phase5p_audit.get("sector_master_snapshot_date_min"),
        "sector_master_snapshot_date_max": phase5p_audit.get("sector_master_snapshot_date_max"),
        "random_date_effective_counts": random_comparison.set_index("strategy")["effective_date_count"].to_dict() if not random_comparison.empty else {},
        "readiness_status": NEEDS_REWORK if not leakage_ok else conclusion["readiness_status"],
        "promotion_ready": False,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def combined_metric_block(metrics: dict[str, Any], split: str, topn: str) -> dict[str, float]:
    try:
        block = metrics["quality_metrics"][split]["rankers"]["model"][topn]
    except Exception:
        block = {}
    return {
        "selected_mean_future_return": float(block.get("selected_mean_future_return", 0.0)),
        "selected_mean_future_max_return": float(block.get("selected_mean_future_max_return", 0.0)),
        "selected_downside_bad_rate": float(block.get("selected_downside_bad_rate", 0.0)),
        "selected_mean_future_max_drawdown": float(block.get("selected_mean_future_max_drawdown", 0.0)),
        "win_rate_20d": float(block.get("win_rate_20d", 0.0)),
    }


def random_date_metric(summary: dict[str, Any], target_date: str) -> float:
    for row in summary.get("by_date_records", []):
        if row.get("target_date") == target_date and row.get("selection_group") == "OpportunityTop5":
            return float(row.get("mean_return_20bd", 0.0))
    return 0.0


def write_markdown_report(path: Path, metrics: dict[str, Any]) -> None:
    conclusion = metrics["conclusion"]
    lines = [
        "# Phase5-P2 Market / Sector Split Impact Audit",
        "",
        "## Summary",
        "",
        f"- readiness_status: `{metrics['readiness_status']}`",
        f"- promotion_ready: `{metrics['promotion_ready']}`",
        f"- sector_master_snapshot_proxy_warning: `{metrics['sector_master_snapshot_proxy_warning']}`",
        f"- likely cause: {conclusion['likely_full_history_degradation_cause']}",
        "",
        "## Strategy Summary",
        "",
        markdown_table(pd.DataFrame(metrics["summary_by_strategy"])),
        "",
        "## Random Date Comparison",
        "",
        markdown_table(pd.DataFrame(metrics["random_date_comparison"])),
        "",
        "## Safety",
        "",
        "- No Broker API, Paper Trading, order placement, capital allocation, promotion, or reader switch was performed.",
        "- Future outcomes remain evaluation-only and are not feature columns.",
        "- Sector strength uses the local J-Quants listed issue master snapshot proxy, so sector-only results should be treated cautiously.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(markdown_value(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def markdown_value(value: Any) -> str:
    return str(value).replace("|", "\\|")


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "metrics": output_dir / METRICS_FILENAME,
        "audit": output_dir / AUDIT_FILENAME,
        "by_strategy": output_dir / BY_STRATEGY_FILENAME,
        "random_comparison": output_dir / RANDOM_COMPARISON_FILENAME,
        "doc": DOC_PATH,
    }


def write_outputs(paths: dict[str, Path], metrics: dict[str, Any], audit: dict[str, Any], by_strategy: pd.DataFrame, random_comparison: pd.DataFrame) -> None:
    write_json(paths["metrics"], metrics)
    write_json(paths["audit"], audit)
    by_strategy.to_csv(paths["by_strategy"], index=False)
    random_comparison.to_csv(paths["random_comparison"], index=False)


def blocked_audit(created_at: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "missing_inputs": missing_inputs,
        "leakage_status": "NOT_RUN",
        "readiness_status": NEEDS_REWORK,
        "promotion_ready": False,
    }


def metrics_shell(created_at: str, paths: dict[str, Path], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": NEEDS_REWORK,
        "created_at": created_at,
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "audit": audit,
        "promotion_ready": False,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
