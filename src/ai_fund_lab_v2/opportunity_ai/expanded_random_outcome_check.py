from __future__ import annotations

import json
import math
import pickle
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.random_date_outcome_check import OUTCOME_COLUMNS, eligible_target_dates, sample_target_dates
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable, transform_features

PHASE = "Phase5-O2"

DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5o2")
DEFAULT_CANDIDATE_PATH = Path("reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet")
DEFAULT_LABEL_PATH = Path(".runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet")
DEFAULT_BASELINE_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_BASELINE_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_MARKET_ONLY_DATASET_PATH = Path("reports/opportunity_ai/phase5p2/market_only/opportunity_dataset.parquet")
DEFAULT_MARKET_ONLY_MODEL_PATH = Path("reports/opportunity_ai/phase5p2/market_only/models/opportunity_model.pkl")
DEFAULT_MARKET_SECTOR_DATASET_PATH = Path("reports/opportunity_ai/phase5p2/market_sector/opportunity_dataset.parquet")
DEFAULT_MARKET_SECTOR_MODEL_PATH = Path("reports/opportunity_ai/phase5p2/market_sector/models/opportunity_model.pkl")
DEFAULT_DOC_PATH = Path("docs/phase_reports/phase5o2_expanded_random_date_outcome_check.md")

JSON_FILENAME = "random_date_outcome_check_50days.json"
BY_DATE_FILENAME = "random_date_outcome_by_date.csv"
BY_YEAR_FILENAME = "random_date_outcome_by_year.csv"
STRATEGY_COMPARISON_FILENAME = "random_date_strategy_comparison.csv"

DEFAULT_YEARS = (2021, 2022, 2023, 2024, 2025)
MODEL_STRATEGIES = {
    "OpportunityBaselineTop5": (DEFAULT_BASELINE_DATASET_PATH, DEFAULT_BASELINE_MODEL_PATH),
    "MarketOnlyTop5": (DEFAULT_MARKET_ONLY_DATASET_PATH, DEFAULT_MARKET_ONLY_MODEL_PATH),
    "MarketSectorTop5": (DEFAULT_MARKET_SECTOR_DATASET_PATH, DEFAULT_MARKET_SECTOR_MODEL_PATH),
}
FORBIDDEN_FEATURE_TERMS = (
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
)


@dataclass(frozen=True)
class ExpandedRandomOutcomeResult:
    summary: dict[str, Any]
    by_date: pd.DataFrame
    by_year: pd.DataFrame
    strategy_comparison: pd.DataFrame


def run_expanded_random_date_outcome_check(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    baseline_dataset_path: Path = DEFAULT_BASELINE_DATASET_PATH,
    baseline_model_path: Path = DEFAULT_BASELINE_MODEL_PATH,
    market_only_dataset_path: Path = DEFAULT_MARKET_ONLY_DATASET_PATH,
    market_only_model_path: Path = DEFAULT_MARKET_ONLY_MODEL_PATH,
    market_sector_dataset_path: Path = DEFAULT_MARKET_SECTOR_DATASET_PATH,
    market_sector_model_path: Path = DEFAULT_MARKET_SECTOR_MODEL_PATH,
    doc_path: Path = DEFAULT_DOC_PATH,
    years: tuple[int, ...] | list[int] = DEFAULT_YEARS,
    samples_per_year: int = 10,
    top_n: int = 5,
    seed: int = 42,
    created_at: str | None = None,
) -> ExpandedRandomOutcomeResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_dir / JSON_FILENAME,
        "by_date": output_dir / BY_DATE_FILENAME,
        "by_year": output_dir / BY_YEAR_FILENAME,
        "strategy_comparison": output_dir / STRATEGY_COMPARISON_FILENAME,
        "doc": doc_path,
    }
    strategy_specs = {
        "OpportunityBaselineTop5": (baseline_dataset_path, baseline_model_path),
        "MarketOnlyTop5": (market_only_dataset_path, market_only_model_path),
        "MarketSectorTop5": (market_sector_dataset_path, market_sector_model_path),
    }
    missing_inputs = [
        str(path)
        for path in (candidate_path, label_path, *[item for pair in strategy_specs.values() for item in pair])
        if not path.is_file()
    ]
    if missing_inputs:
        summary = blocked_summary(created_at, paths, missing_inputs)
        empty = pd.DataFrame()
        write_outputs(paths, summary, empty, empty, empty)
        return ExpandedRandomOutcomeResult(summary, empty, empty, empty)

    candidate = pd.read_parquet(candidate_path)
    labels = pd.read_parquet(label_path)
    eligible = eligible_target_dates(candidate, labels, years=years)
    sampled_dates = sample_target_dates(eligible, years=years, samples_per_year=samples_per_year, seed=seed)
    baseline_dataset = pd.read_parquet(baseline_dataset_path)
    common_outcome = build_common_outcomes(
        baseline_dataset,
        labels,
        sampled_dates=sampled_dates,
        top_n=top_n,
    )
    strategy_frames = [common_outcome]
    feature_audits: dict[str, Any] = {}
    for strategy_name, (dataset_path, model_path) in strategy_specs.items():
        dataset = pd.read_parquet(dataset_path)
        model_payload = load_model_payload(model_path)
        feature_columns = list(model_payload.get("feature_columns") or sorted(c for c in dataset.columns if str(c).startswith("feature__")))
        feature_audits[strategy_name] = leakage_audit(feature_columns)
        strategy_frames.append(build_model_strategy_outcomes(strategy_name, dataset, labels, model_payload, sampled_dates=sampled_dates, top_n=top_n))
    by_stock = pd.concat(strategy_frames, ignore_index=True)
    by_date = build_by_date(by_stock)
    by_year = build_by_year(by_date)
    strategy_comparison = build_strategy_comparison(by_date)
    summary = build_summary(
        created_at=created_at,
        seed=seed,
        years=list(years),
        samples_per_year=samples_per_year,
        top_n=top_n,
        sampled_dates=sampled_dates,
        eligible=eligible,
        paths=paths,
        feature_audits=feature_audits,
        by_date=by_date,
        by_year=by_year,
        strategy_comparison=strategy_comparison,
    )
    write_outputs(paths, summary, by_date, by_year, strategy_comparison)
    write_markdown_report(doc_path, summary, by_date, by_year, strategy_comparison)
    return ExpandedRandomOutcomeResult(summary, by_date, by_year, strategy_comparison)


def build_common_outcomes(dataset: pd.DataFrame, labels: pd.DataFrame, *, sampled_dates: list[str], top_n: int) -> pd.DataFrame:
    frame = dataset[dataset["target_date"].astype(str).isin(set(sampled_dates))].copy()
    frame["candidate_score"] = pd.to_numeric(frame.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
    frame["candidate_rank"] = pd.to_numeric(frame.get("feature__candidate_rank", 999999), errors="coerce").fillna(999999).astype(int)
    frame["candidate_score_rank"] = (
        frame.sort_values(["target_date", "candidate_score", "code"], ascending=[True, False, True])
        .groupby("target_date")
        .cumcount()
        + 1
    )
    merged = attach_outcomes(frame, labels)
    candidate = merged.copy()
    candidate["selection_group"] = "CandidateTop50"
    score = merged[merged["candidate_score_rank"] <= top_n].copy()
    score["selection_group"] = "CandidateScoreTop5"
    return format_stock_rows(pd.concat([candidate, score], ignore_index=True))


def build_model_strategy_outcomes(
    strategy_name: str,
    dataset: pd.DataFrame,
    labels: pd.DataFrame,
    model_payload: dict[str, Any],
    *,
    sampled_dates: list[str],
    top_n: int,
) -> pd.DataFrame:
    frame = dataset[dataset["target_date"].astype(str).isin(set(sampled_dates))].copy()
    feature_columns = list(model_payload.get("feature_columns") or sorted(c for c in frame.columns if str(c).startswith("feature__")))
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    matrix = transform_features(frame, feature_columns, model_payload.get("preprocessing", {}))
    frame["expected_edge_score"] = np.asarray(model_payload["model"].predict(matrix), dtype=float)
    frame["buy_rank"] = (
        frame.sort_values(["target_date", "expected_edge_score", "code"], ascending=[True, False, True])
        .groupby("target_date")
        .cumcount()
        + 1
    )
    frame["candidate_score"] = pd.to_numeric(frame.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
    frame["candidate_rank"] = pd.to_numeric(frame.get("feature__candidate_rank", 999999), errors="coerce").fillna(999999).astype(int)
    top = attach_outcomes(frame[frame["buy_rank"] <= top_n], labels)
    top["selection_group"] = strategy_name
    return format_stock_rows(top)


def attach_outcomes(scored: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    label_columns = ["target_date", "code", *OUTCOME_COLUMNS]
    label_part = labels[label_columns].copy()
    label_part["target_date"] = label_part["target_date"].astype(str)
    label_part["code"] = label_part["code"].astype(str)
    scored = scored.copy()
    scored["target_date"] = scored["target_date"].astype(str)
    scored["code"] = scored["code"].astype(str)
    merged = scored.merge(label_part, on=["target_date", "code"], how="inner", validate="one_to_one")
    merged["return_5bd"] = pd.to_numeric(merged["future_return_5d"], errors="coerce")
    merged["return_10bd"] = pd.to_numeric(merged["future_return_10d"], errors="coerce")
    merged["return_20bd"] = pd.to_numeric(merged["future_return_20d"], errors="coerce")
    merged["positive_5bd"] = merged["return_5bd"] > 0
    merged["positive_10bd"] = merged["return_10bd"] > 0
    merged["positive_20bd"] = merged["return_20bd"] > 0
    merged["max_return_20bd"] = pd.to_numeric(merged["future_max_return_20d"], errors="coerce")
    merged["max_drawdown_20bd"] = pd.to_numeric(merged["future_max_drawdown_20d"], errors="coerce")
    return merged


def format_stock_rows(frame: pd.DataFrame) -> pd.DataFrame:
    for column, default in (("buy_rank", 999999), ("expected_edge_score", 0.0), ("candidate_rank", 999999), ("candidate_score", 0.0)):
        if column not in frame.columns:
            frame[column] = default
    columns = [
        "target_date",
        "selection_group",
        "code",
        "buy_rank",
        "candidate_rank",
        "expected_edge_score",
        "candidate_score",
        "return_5bd",
        "return_10bd",
        "return_20bd",
        "positive_5bd",
        "positive_10bd",
        "positive_20bd",
        "max_return_20bd",
        "max_drawdown_20bd",
    ]
    return frame[columns]


def build_by_date(by_stock: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (target_date, group), frame in by_stock.groupby(["target_date", "selection_group"], sort=True):
        rows.append(
            {
                "target_date": str(target_date),
                "year": str(target_date)[:4],
                "selection_group": str(group),
                "selected_count": int(len(frame)),
                "mean_return_5bd": round_float(frame["return_5bd"].mean()),
                "median_return_5bd": round_float(frame["return_5bd"].median()),
                "mean_return_10bd": round_float(frame["return_10bd"].mean()),
                "median_return_10bd": round_float(frame["return_10bd"].median()),
                "mean_return_20bd": round_float(frame["return_20bd"].mean()),
                "median_return_20bd": round_float(frame["return_20bd"].median()),
                "win_rate_5bd": round_float(frame["positive_5bd"].mean()),
                "win_rate_10bd": round_float(frame["positive_10bd"].mean()),
                "win_rate_20bd": round_float(frame["positive_20bd"].mean()),
                "positive_date_5bd": int(frame["return_5bd"].mean() > 0),
                "positive_date_10bd": int(frame["return_10bd"].mean() > 0),
                "positive_date_20bd": int(frame["return_20bd"].mean() > 0),
                "positive_stock_count_5bd": int(frame["positive_5bd"].sum()),
                "positive_stock_count_10bd": int(frame["positive_10bd"].sum()),
                "positive_stock_count_20bd": int(frame["positive_20bd"].sum()),
                "avg_max_return_20bd": round_float(frame["max_return_20bd"].mean()),
                "avg_max_drawdown_20bd": round_float(frame["max_drawdown_20bd"].mean()),
            }
        )
    return pd.DataFrame(rows)


def build_by_year(by_date: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, group), frame in by_date.groupby(["year", "selection_group"], sort=True):
        rows.append(
            {
                "year": str(year),
                "selection_group": str(group),
                "target_date_count": int(frame["target_date"].nunique()),
                "mean_return_5bd": round_float(frame["mean_return_5bd"].mean()),
                "mean_return_10bd": round_float(frame["mean_return_10bd"].mean()),
                "mean_return_20bd": round_float(frame["mean_return_20bd"].mean()),
                "median_return_20bd": round_float(frame["median_return_20bd"].median()),
                "positive_date_count_5bd": int(frame["positive_date_5bd"].sum()),
                "positive_date_count_10bd": int(frame["positive_date_10bd"].sum()),
                "positive_date_count_20bd": int((frame["mean_return_20bd"] > 0).sum()),
                "date_win_rate_5bd": round_float(frame["positive_date_5bd"].mean()),
                "date_win_rate_10bd": round_float(frame["positive_date_10bd"].mean()),
                "date_win_rate_20bd": round_float((frame["mean_return_20bd"] > 0).mean()),
                "avg_win_rate_20bd": round_float(frame["win_rate_20bd"].mean()),
                "avg_max_return_20bd": round_float(frame["avg_max_return_20bd"].mean()),
                "avg_max_drawdown_20bd": round_float(frame["avg_max_drawdown_20bd"].mean()),
            }
        )
    return pd.DataFrame(rows)


def build_strategy_comparison(by_date: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target_date, frame in by_date.groupby("target_date", sort=True):
        lookup = frame.set_index("selection_group").to_dict("index")
        baseline = lookup.get("OpportunityBaselineTop5", {})
        candidate = lookup.get("CandidateTop50", {})
        score = lookup.get("CandidateScoreTop5", {})
        market_only = lookup.get("MarketOnlyTop5", {})
        market_sector = lookup.get("MarketSectorTop5", {})
        rows.append(
            {
                "target_date": str(target_date),
                "year": str(target_date)[:4],
                "baseline_minus_candidate_top50_20bd": round_float(baseline.get("mean_return_20bd", 0.0) - candidate.get("mean_return_20bd", 0.0)),
                "baseline_minus_candidate_score_top5_20bd": round_float(baseline.get("mean_return_20bd", 0.0) - score.get("mean_return_20bd", 0.0)),
                "market_only_minus_baseline_20bd": round_float(market_only.get("mean_return_20bd", 0.0) - baseline.get("mean_return_20bd", 0.0)),
                "market_sector_minus_baseline_20bd": round_float(market_sector.get("mean_return_20bd", 0.0) - baseline.get("mean_return_20bd", 0.0)),
                "baseline_beats_candidate_top50_20bd": bool(baseline.get("mean_return_20bd", 0.0) > candidate.get("mean_return_20bd", 0.0)),
                "baseline_beats_candidate_score_top5_20bd": bool(baseline.get("mean_return_20bd", 0.0) > score.get("mean_return_20bd", 0.0)),
                "market_only_beats_baseline_20bd": bool(market_only.get("mean_return_20bd", 0.0) > baseline.get("mean_return_20bd", 0.0)),
                "market_sector_beats_baseline_20bd": bool(market_sector.get("mean_return_20bd", 0.0) > baseline.get("mean_return_20bd", 0.0)),
                "candidate_top50_mean_return_20bd": candidate.get("mean_return_20bd", 0.0),
                "opportunity_baseline_mean_return_20bd": baseline.get("mean_return_20bd", 0.0),
                "market_only_mean_return_20bd": market_only.get("mean_return_20bd", 0.0),
                "market_sector_mean_return_20bd": market_sector.get("mean_return_20bd", 0.0),
            }
        )
    return pd.DataFrame(rows)


def build_summary(
    *,
    created_at: str,
    seed: int,
    years: list[int],
    samples_per_year: int,
    top_n: int,
    sampled_dates: list[str],
    eligible: dict[int, list[str]],
    paths: dict[str, Path],
    feature_audits: dict[str, Any],
    by_date: pd.DataFrame,
    by_year: pd.DataFrame,
    strategy_comparison: pd.DataFrame,
) -> dict[str, Any]:
    win_counts = {
        "opportunity_baseline_beats_candidate_top50_20bd": int(strategy_comparison["baseline_beats_candidate_top50_20bd"].sum()),
        "opportunity_baseline_beats_candidate_score_top5_20bd": int(strategy_comparison["baseline_beats_candidate_score_top5_20bd"].sum()),
        "market_only_beats_baseline_20bd": int(strategy_comparison["market_only_beats_baseline_20bd"].sum()),
        "market_sector_beats_baseline_20bd": int(strategy_comparison["market_sector_beats_baseline_20bd"].sum()),
    }
    losing = strategy_comparison.sort_values("baseline_minus_candidate_top50_20bd", ascending=True).head(10)
    winning = strategy_comparison.sort_values("baseline_minus_candidate_top50_20bd", ascending=False).head(10)
    down_proxy = identify_down_regime_dates(by_date)
    failure_2022_like = strategy_comparison[
        (strategy_comparison["baseline_beats_candidate_top50_20bd"] == False)
        & (strategy_comparison["candidate_top50_mean_return_20bd"] < 0)
    ]
    return {
        "phase": PHASE,
        "status": "OK",
        "created_at": created_at,
        "random_seed": int(seed),
        "years": years,
        "samples_per_year": int(samples_per_year),
        "top_n": int(top_n),
        "sampled_target_dates": sampled_dates,
        "sampled_target_date_count": len(sampled_dates),
        "eligible_target_date_count_by_year": {str(year): len(dates) for year, dates in eligible.items()},
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "feature_audits": feature_audits,
        "leakage_status": "OK" if all(audit["leakage_status"] == "OK" for audit in feature_audits.values()) else "ERROR",
        "future_outcome_used_for_evaluation_only": True,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "win_counts_20bd": win_counts,
        "win_rates_20bd": {key: round_float(value / len(sampled_dates)) for key, value in win_counts.items()},
        "top10_losing_dates_vs_candidate_top50_20bd": losing.to_dict("records"),
        "top10_winning_dates_vs_candidate_top50_20bd": winning.to_dict("records"),
        "failure_2022_like_count": int(len(failure_2022_like)),
        "failure_2022_like_dates": failure_2022_like["target_date"].tolist(),
        "down_regime_proxy_dates": down_proxy,
        "down_regime_proxy_failure_overlap_count": int(len(set(down_proxy) & set(failure_2022_like["target_date"].tolist()))),
        "by_year_records": by_year.to_dict("records"),
        "strategy_comparison_records": strategy_comparison.to_dict("records"),
        "promotion_ready": False,
    }


def identify_down_regime_dates(by_date: pd.DataFrame) -> list[str]:
    candidate = by_date[by_date["selection_group"] == "CandidateTop50"].copy()
    down = candidate[(candidate["mean_return_20bd"] < 0) | (candidate["win_rate_20bd"] < 0.40)]
    return sorted(down["target_date"].astype(str).unique().tolist())


def leakage_audit(feature_columns: list[str]) -> dict[str, Any]:
    forbidden = [column for column in feature_columns if any(term in column.lower() for term in FORBIDDEN_FEATURE_TERMS)]
    future = [column for column in forbidden if "future_" in column.lower() or "downside_bad_" in column.lower() or "top_decile_" in column.lower()]
    return {
        "feature_column_count": len(feature_columns),
        "forbidden_feature_column_count": len(forbidden),
        "future_feature_column_count": len(future),
        "forbidden_feature_columns": forbidden,
        "leakage_status": "OK" if not forbidden else "ERROR",
    }


def blocked_summary(created_at: str, paths: dict[str, Path], missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "created_at": created_at,
        "missing_inputs": missing_inputs,
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "promotion_ready": False,
    }


def write_outputs(paths: dict[str, Path], summary: dict[str, Any], by_date: pd.DataFrame, by_year: pd.DataFrame, strategy_comparison: pd.DataFrame) -> None:
    write_json(paths["json"], summary)
    by_date.to_csv(paths["by_date"], index=False)
    by_year.to_csv(paths["by_year"], index=False)
    strategy_comparison.to_csv(paths["strategy_comparison"], index=False)


def write_markdown_report(path: Path, summary: dict[str, Any], by_date: pd.DataFrame, by_year: pd.DataFrame, strategy_comparison: pd.DataFrame) -> None:
    lines = [
        "# Phase5-O2 Expanded Random Date Opportunity Outcome Check",
        "",
        "## Summary",
        "",
        f"- seed: `{summary['random_seed']}`",
        f"- sampled target date count: `{summary['sampled_target_date_count']}`",
        f"- sampled target dates: `{summary['sampled_target_dates']}`",
        f"- leakage_status: `{summary['leakage_status']}`",
        f"- win counts 20bd: `{summary['win_counts_20bd']}`",
        f"- win rates 20bd: `{summary['win_rates_20bd']}`",
        f"- failure_2022_like_count: `{summary['failure_2022_like_count']}`",
        f"- down_regime_proxy_failure_overlap_count: `{summary['down_regime_proxy_failure_overlap_count']}`",
        "",
        "## Strategy Comparison",
        "",
        markdown_table(strategy_comparison),
        "",
        "## By Year",
        "",
        markdown_table(by_year),
        "",
        "## Top Losing Dates Vs CandidateTop50",
        "",
        markdown_table(pd.DataFrame(summary["top10_losing_dates_vs_candidate_top50_20bd"])),
        "",
        "## Top Winning Dates Vs CandidateTop50",
        "",
        markdown_table(pd.DataFrame(summary["top10_winning_dates_vs_candidate_top50_20bd"])),
        "",
        "## Safety",
        "",
        "- This is offline outcome checking, not real trading or Paper Trading.",
        "- Future outcomes are evaluation-only and are not used as features.",
        "- No Broker API, order placement, capital allocation, promotion, or reader switch was performed.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("|", "\\|") for column in columns) + " |")
    return "\n".join(lines)


def load_model_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return pickle.load(handle)


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
