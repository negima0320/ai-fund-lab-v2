from __future__ import annotations

import json
import math
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.market_sector_completion import MARKET_FEATURE_COLUMNS, SECTOR_FEATURE_COLUMNS
from ai_fund_lab_v2.opportunity_ai.training import (
    audit_opportunity_training_dataset,
    simple_rule_scores,
    to_jsonable,
    transform_features,
)

PHASE = "Phase5-R"

DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5r")
DEFAULT_BASELINE_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_BASELINE_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_MARKET_ONLY_DATASET_PATH = Path("reports/opportunity_ai/phase5p2/market_only/opportunity_dataset.parquet")
DEFAULT_MARKET_ONLY_MODEL_PATH = Path("reports/opportunity_ai/phase5p2/market_only/models/opportunity_model.pkl")
DEFAULT_SECTOR_ONLY_DATASET_PATH = Path("reports/opportunity_ai/phase5p2/sector_only/opportunity_dataset.parquet")
DEFAULT_SECTOR_ONLY_MODEL_PATH = Path("reports/opportunity_ai/phase5p2/sector_only/models/opportunity_model.pkl")
DEFAULT_MARKET_SECTOR_DATASET_PATH = Path("reports/opportunity_ai/phase5p2/market_sector/opportunity_dataset.parquet")
DEFAULT_MARKET_SECTOR_MODEL_PATH = Path("reports/opportunity_ai/phase5p2/market_sector/models/opportunity_model.pkl")
DEFAULT_LABEL_PATH = Path(".runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet")
DEFAULT_PHASE5P_AUDIT_PATH = Path("reports/opportunity_ai/phase5p/market_sector_completion_audit.json")

METRICS_FILENAME = "ranking_quality_metrics.json"
AUDIT_FILENAME = "ranking_quality_audit.json"
BY_STRATEGY_FILENAME = "ranking_quality_by_strategy.csv"
BY_YEAR_FILENAME = "ranking_quality_by_year.csv"
BY_DATE_FILENAME = "ranking_quality_by_date.csv"
BUCKET_FILENAME = "rank_bucket_analysis.csv"
DOC_PATH = Path("docs/phase_reports/phase5r_opportunity_ranking_quality_audit.md")

RANKING_QUALITY_CONFIRMED = "RANKING_QUALITY_CONFIRMED"
RANKING_QUALITY_MIXED = "RANKING_QUALITY_MIXED"
RANKING_QUALITY_NOT_CONFIRMED = "RANKING_QUALITY_NOT_CONFIRMED"
NEEDS_REWORK = "NEEDS_REWORK"

LABEL_METRICS = {
    "future_return_20d": "label__future_return_20d",
    "future_max_return_20d": "label__future_max_return_20d",
    "risk_adjusted_future_return_20d": "label__risk_adjusted_future_return_20d",
}
TOP_KS = (5, 10, 20)
BUCKETS = [
    ("rank_1_5", 1, 5),
    ("rank_6_10", 6, 10),
    ("rank_11_20", 11, 20),
    ("rank_21_50", 21, 50),
]
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


@dataclass(frozen=True)
class RankingQualityAuditResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]
    by_strategy: pd.DataFrame
    by_year: pd.DataFrame
    by_date: pd.DataFrame
    bucket: pd.DataFrame


def run_opportunity_ranking_quality_audit(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    baseline_dataset_path: Path = DEFAULT_BASELINE_DATASET_PATH,
    baseline_model_path: Path = DEFAULT_BASELINE_MODEL_PATH,
    market_only_dataset_path: Path = DEFAULT_MARKET_ONLY_DATASET_PATH,
    market_only_model_path: Path = DEFAULT_MARKET_ONLY_MODEL_PATH,
    sector_only_dataset_path: Path = DEFAULT_SECTOR_ONLY_DATASET_PATH,
    sector_only_model_path: Path = DEFAULT_SECTOR_ONLY_MODEL_PATH,
    market_sector_dataset_path: Path = DEFAULT_MARKET_SECTOR_DATASET_PATH,
    market_sector_model_path: Path = DEFAULT_MARKET_SECTOR_MODEL_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    phase5p_audit_path: Path = DEFAULT_PHASE5P_AUDIT_PATH,
    created_at: str | None = None,
) -> RankingQualityAuditResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_paths(output_dir)
    strategy_specs = {
        "baseline": (baseline_dataset_path, baseline_model_path),
        "market_only": (market_only_dataset_path, market_only_model_path),
        "sector_only": (sector_only_dataset_path, sector_only_model_path),
        "market_sector": (market_sector_dataset_path, market_sector_model_path),
    }
    missing_inputs = [
        str(path)
        for pair in strategy_specs.values()
        for path in pair
        if not path.is_file()
    ]
    if not label_path.is_file():
        missing_inputs.append(str(label_path))
    if missing_inputs:
        audit = blocked_audit(created_at, missing_inputs)
        metrics = metrics_shell(created_at, paths, audit)
        empty = pd.DataFrame()
        write_outputs(paths, metrics, audit, empty, empty, empty, empty)
        return RankingQualityAuditResult(metrics, audit, empty, empty, empty, empty)

    labels = pd.read_parquet(label_path)
    scored_frames: list[pd.DataFrame] = []
    strategy_audits: dict[str, Any] = {}
    for strategy_name, (dataset_path, model_path) in strategy_specs.items():
        dataset = attach_auxiliary_labels(pd.read_parquet(dataset_path), labels)
        model_payload = load_model_payload(model_path)
        scored = score_model_strategy(dataset, model_payload, strategy_name)
        scored_frames.append(scored)
        feature_columns = list(model_payload.get("feature_columns") or sorted(c for c in dataset.columns if str(c).startswith("feature__")))
        label_columns = sorted(c for c in dataset.columns if str(c).startswith("label__"))
        strategy_audits[strategy_name] = audit_opportunity_training_dataset(
            dataset,
            feature_columns=feature_columns,
            label_columns=label_columns,
            created_at=created_at,
        )
    baseline_dataset = attach_auxiliary_labels(pd.read_parquet(baseline_dataset_path), labels)
    scored_frames.append(score_candidate_score_baseline(baseline_dataset))
    scored_frames.append(score_simple_rule_baseline(baseline_dataset, load_model_payload(baseline_model_path)))
    scored = pd.concat(scored_frames, ignore_index=True)
    scored = scored[scored["split"].isin(["validation", "test"])].copy()
    scored["year"] = scored["target_date"].astype(str).str.slice(0, 4)

    by_date = build_by_date(scored)
    by_strategy = aggregate_quality(by_date, ["strategy", "split"])
    by_year = aggregate_quality(by_date, ["strategy", "split", "year"])
    bucket = build_bucket_analysis(scored)
    phase5p_audit = read_json_optional(phase5p_audit_path)
    audit = build_audit(
        created_at=created_at,
        strategy_audits=strategy_audits,
        scored=scored,
        by_strategy=by_strategy,
        by_date=by_date,
        phase5p_audit=phase5p_audit,
    )
    readiness_status = resolve_readiness(audit, by_strategy)
    audit["readiness_status"] = readiness_status
    metrics = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "promotion_ready": False,
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "strategy_count": int(scored["strategy"].nunique()),
        "strategies": sorted(scored["strategy"].unique().tolist()),
        "target_date_count": int(scored["target_date"].nunique()),
        "validation_rows": int((scored["split"] == "validation").sum()),
        "test_rows": int((scored["split"] == "test").sum()),
        "best_strategy_by_test_ndcg20_risk_adjusted": best_strategy(by_strategy, "test", "ndcg@20_risk_adjusted_future_return_20d"),
        "best_strategy_by_test_spearman_risk_adjusted": best_strategy(by_strategy, "test", "spearman_risk_adjusted_future_return_20d"),
        "candidate_score_comparison": compare_to_candidate_score(by_strategy),
        "ranking_audit_executed": True,
        "future_outcome_used_for_evaluation_only": True,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "sector_master_snapshot_proxy_warning": bool(phase5p_audit.get("sector_master_snapshot_proxy_warning", False)),
        "summary_by_strategy": by_strategy.to_dict("records"),
    }
    write_outputs(paths, metrics, audit, by_strategy, by_year, by_date, bucket)
    write_markdown_report(DOC_PATH, metrics, by_strategy, bucket)
    return RankingQualityAuditResult(metrics, audit, by_strategy, by_year, by_date, bucket)


def attach_auxiliary_labels(dataset: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    out = dataset.copy()
    needed = ["future_return_5d", "future_return_10d"]
    missing = [f"label__{column}" for column in needed if f"label__{column}" not in out.columns]
    if missing:
        label_part = labels[["target_date", "code", *needed]].copy()
        label_part["target_date"] = label_part["target_date"].astype(str)
        label_part["code"] = label_part["code"].astype(str)
        label_part = label_part.rename(columns={column: f"label__{column}" for column in needed})
        out["target_date"] = out["target_date"].astype(str)
        out["code"] = out["code"].astype(str)
        out = out.merge(label_part, on=["target_date", "code"], how="left")
    return out


def score_model_strategy(dataset: pd.DataFrame, model_payload: dict[str, Any], strategy_name: str) -> pd.DataFrame:
    frame = dataset.copy()
    feature_columns = list(model_payload.get("feature_columns") or sorted(c for c in frame.columns if str(c).startswith("feature__")))
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    matrix = transform_features(frame, feature_columns, model_payload.get("preprocessing", {}))
    frame["ranking_score"] = np.asarray(model_payload["model"].predict(matrix), dtype=float)
    frame["strategy"] = strategy_name
    frame["score_source"] = "opportunity_model"
    return frame


def score_candidate_score_baseline(dataset: pd.DataFrame) -> pd.DataFrame:
    frame = dataset.copy()
    frame["ranking_score"] = pd.to_numeric(frame.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
    frame["strategy"] = "candidate_score_baseline"
    frame["score_source"] = "candidate_score"
    return frame


def score_simple_rule_baseline(dataset: pd.DataFrame, model_payload: dict[str, Any]) -> pd.DataFrame:
    frame = dataset.copy()
    frame["ranking_score"] = simple_rule_scores(frame, model_payload.get("simple_rule_baseline", {}))
    frame["strategy"] = "simple_rule_baseline"
    frame["score_source"] = "simple_rule"
    return frame


def build_by_date(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (strategy, split_name, target_date), frame in scored.groupby(["strategy", "split", "target_date"], sort=True):
        rows.append(date_metric_row(strategy, split_name, str(target_date), frame))
    return pd.DataFrame(rows)


def date_metric_row(strategy: str, split_name: str, target_date: str, frame: pd.DataFrame) -> dict[str, Any]:
    frame = frame.copy()
    frame["score_rank"] = frame["ranking_score"].rank(method="first", ascending=False)
    row: dict[str, Any] = {
        "strategy": strategy,
        "split": split_name,
        "target_date": target_date,
        "year": target_date[:4],
        "candidate_count": int(len(frame)),
        "downside_bad_top5_rate": topk_downside_rate(frame, 5),
        "downside_bad_top10_rate": topk_downside_rate(frame, 10),
        "downside_bad_top20_rate": topk_downside_rate(frame, 20),
    }
    for label_name, column in LABEL_METRICS.items():
        relevance = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        row[f"spearman_{label_name}"] = round_float(frame["ranking_score"].corr(relevance, method="spearman"))
        row[f"kendall_{label_name}"] = round_float(frame["ranking_score"].corr(relevance, method="kendall"))
        for top_k in TOP_KS:
            row[f"ndcg@{top_k}_{label_name}"] = round_float(ndcg_at_k(frame["ranking_score"], relevance, top_k))
            row[f"precision@{top_k}_{label_name}"] = round_float(precision_at_k(frame, column, top_k))
            row[f"recall@{top_k}_{label_name}"] = row[f"precision@{top_k}_{label_name}"]
    if "label__top_decile_20d" in frame.columns:
        for top_k in TOP_KS:
            top = frame.sort_values(["ranking_score", "code"], ascending=[False, True]).head(top_k)
            row[f"top_decile_capture@{top_k}"] = round_float(top["label__top_decile_20d"].astype(bool).mean())
    return row


def ndcg_at_k(scores: pd.Series, relevance: pd.Series, top_k: int) -> float:
    relevance = pd.to_numeric(relevance, errors="coerce").fillna(0.0)
    shifted = relevance - relevance.min()
    if shifted.max() <= 0:
        return 0.0
    order = scores.sort_values(ascending=False).index[:top_k]
    ideal = shifted.sort_values(ascending=False).iloc[:top_k].to_numpy(dtype=float)
    actual = shifted.loc[order].to_numpy(dtype=float)
    ideal_dcg = dcg(ideal)
    return dcg(actual) / ideal_dcg if ideal_dcg else 0.0


def dcg(values: np.ndarray) -> float:
    discounts = np.log2(np.arange(2, len(values) + 2))
    return float(np.sum(values / discounts))


def precision_at_k(frame: pd.DataFrame, label_column: str, top_k: int) -> float:
    top_pred = set(frame.sort_values(["ranking_score", "code"], ascending=[False, True]).head(top_k).index)
    top_true = set(frame.sort_values([label_column, "code"], ascending=[False, True]).head(top_k).index)
    return len(top_pred & top_true) / float(top_k) if top_k else 0.0


def topk_downside_rate(frame: pd.DataFrame, top_k: int) -> float:
    if "label__downside_bad_20d" not in frame.columns:
        return 0.0
    top = frame.sort_values(["ranking_score", "code"], ascending=[False, True]).head(top_k)
    return round_float(top["label__downside_bad_20d"].astype(bool).mean())


def aggregate_quality(by_date: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    metric_columns = [column for column in by_date.columns if any(token in column for token in ("spearman_", "kendall_", "ndcg@", "precision@", "recall@", "top_decile_capture@", "downside_bad_top"))]
    grouped = by_date.groupby(group_columns, as_index=False)[metric_columns].mean()
    for column in metric_columns:
        grouped[column] = grouped[column].map(round_float)
    grouped["target_date_count"] = by_date.groupby(group_columns)["target_date"].nunique().to_numpy()
    return grouped


def build_bucket_analysis(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (strategy, split_name, target_date), frame in scored.groupby(["strategy", "split", "target_date"], sort=True):
        ranked = frame.sort_values(["ranking_score", "code"], ascending=[False, True]).copy()
        ranked["rank"] = np.arange(1, len(ranked) + 1)
        for bucket_name, start, end in BUCKETS:
            bucket = ranked[(ranked["rank"] >= start) & (ranked["rank"] <= end)]
            rows.append(
                {
                    "strategy": strategy,
                    "split": split_name,
                    "target_date": str(target_date),
                    "year": str(target_date)[:4],
                    "bucket": bucket_name,
                    "selected_count": int(len(bucket)),
                    "mean_future_return_5d": round_float(pd.to_numeric(bucket.get("label__future_return_5d", 0.0), errors="coerce").mean()),
                    "mean_future_return_10d": round_float(pd.to_numeric(bucket.get("label__future_return_10d", 0.0), errors="coerce").mean()),
                    "mean_future_return_20d": round_float(pd.to_numeric(bucket["label__future_return_20d"], errors="coerce").mean()),
                    "mean_future_max_return_20d": round_float(pd.to_numeric(bucket["label__future_max_return_20d"], errors="coerce").mean()),
                    "mean_risk_adjusted_future_return_20d": round_float(pd.to_numeric(bucket["label__risk_adjusted_future_return_20d"], errors="coerce").mean()),
                    "downside_bad_rate": round_float(bucket["label__downside_bad_20d"].astype(bool).mean()),
                }
            )
    return pd.DataFrame(rows)


def build_audit(
    *,
    created_at: str,
    strategy_audits: dict[str, Any],
    scored: pd.DataFrame,
    by_strategy: pd.DataFrame,
    by_date: pd.DataFrame,
    phase5p_audit: dict[str, Any],
) -> dict[str, Any]:
    leakage_ok = all(audit.get("leakage_audit_status") == "OK" for audit in strategy_audits.values())
    future_feature_count = sum(int(audit.get("future_feature_column_count", 0)) for audit in strategy_audits.values())
    forbidden_feature_count = sum(int(audit.get("forbidden_feature_column_count", 0)) for audit in strategy_audits.values())
    trade_backtest_portfolio = sum(
        int(audit.get("trade_result_feature_column_count", 0))
        + int(audit.get("backtest_feature_column_count", 0))
        + int(audit.get("portfolio_feature_column_count", 0))
        for audit in strategy_audits.values()
    )
    score_collapse = scored.groupby("strategy")["ranking_score"].nunique().min() <= 1
    return {
        "phase": PHASE,
        "created_at": created_at,
        "leakage_status": "OK" if leakage_ok else "ERROR",
        "future_feature_count": int(future_feature_count),
        "forbidden_feature_count": int(forbidden_feature_count),
        "trade_backtest_portfolio_feature_count": int(trade_backtest_portfolio),
        "label_evaluation_only_status": True,
        "strategy_count": int(scored["strategy"].nunique()),
        "target_date_count": int(scored["target_date"].nunique()),
        "validation_rows": int((scored["split"] == "validation").sum()),
        "test_rows": int((scored["split"] == "test").sum()),
        "metric_availability": bool(not by_strategy.empty and not by_date.empty),
        "score_collapse": bool(score_collapse),
        "promotion_ready": False,
        "sector_master_snapshot_proxy_warning": bool(phase5p_audit.get("sector_master_snapshot_proxy_warning", False)),
        "sector_feature_strategies": ["sector_only", "market_sector"],
        "market_feature_strategies": ["market_only", "market_sector"],
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def resolve_readiness(audit: dict[str, Any], by_strategy: pd.DataFrame) -> str:
    if audit["leakage_status"] != "OK" or audit["future_feature_count"] or audit["forbidden_feature_count"] or audit["score_collapse"]:
        return NEEDS_REWORK
    comparison = compare_to_candidate_score(by_strategy)
    wins = sum(1 for value in comparison.values() if isinstance(value, bool) and value)
    losses = sum(1 for value in comparison.values() if isinstance(value, bool) and not value)
    if wins and not losses:
        return RANKING_QUALITY_CONFIRMED
    if wins:
        return RANKING_QUALITY_MIXED
    return RANKING_QUALITY_NOT_CONFIRMED


def compare_to_candidate_score(by_strategy: pd.DataFrame) -> dict[str, Any]:
    test = by_strategy[by_strategy["split"] == "test"].set_index("strategy")
    if "candidate_score_baseline" not in test.index:
        return {}
    candidate = test.loc["candidate_score_baseline"]
    result: dict[str, Any] = {}
    for strategy in [idx for idx in test.index if idx != "candidate_score_baseline"]:
        row = test.loc[strategy]
        result[f"{strategy}_beats_candidate_ndcg20_risk_adjusted"] = bool(row["ndcg@20_risk_adjusted_future_return_20d"] > candidate["ndcg@20_risk_adjusted_future_return_20d"])
        result[f"{strategy}_beats_candidate_spearman_risk_adjusted"] = bool(row["spearman_risk_adjusted_future_return_20d"] > candidate["spearman_risk_adjusted_future_return_20d"])
        result[f"{strategy}_beats_candidate_precision20_future_return"] = bool(row["precision@20_future_return_20d"] > candidate["precision@20_future_return_20d"])
    return result


def best_strategy(by_strategy: pd.DataFrame, split_name: str, metric: str) -> dict[str, Any]:
    frame = by_strategy[by_strategy["split"] == split_name]
    if frame.empty or metric not in frame.columns:
        return {"strategy": None, "metric": metric, "value": 0.0}
    row = frame.sort_values(metric, ascending=False).iloc[0]
    return {"strategy": row["strategy"], "metric": metric, "value": round_float(row[metric])}


def write_markdown_report(path: Path, metrics: dict[str, Any], by_strategy: pd.DataFrame, bucket: pd.DataFrame) -> None:
    test = by_strategy[by_strategy["split"] == "test"].copy()
    bucket_summary = (
        bucket.groupby(["strategy", "split", "bucket"], as_index=False)[["mean_future_return_20d", "downside_bad_rate"]]
        .mean()
        .round(6)
    )
    lines = [
        "# Phase5-R Opportunity Ranking Quality Audit",
        "",
        "## Summary",
        "",
        f"- readiness_status: `{metrics['readiness_status']}`",
        f"- promotion_ready: `{metrics['promotion_ready']}`",
        f"- best test NDCG@20 risk-adjusted: `{metrics['best_strategy_by_test_ndcg20_risk_adjusted']}`",
        f"- best test Spearman risk-adjusted: `{metrics['best_strategy_by_test_spearman_risk_adjusted']}`",
        f"- sector_master_snapshot_proxy_warning: `{metrics['sector_master_snapshot_proxy_warning']}`",
        "",
        "## Test Strategy Metrics",
        "",
        markdown_table(test[["strategy", "spearman_risk_adjusted_future_return_20d", "kendall_risk_adjusted_future_return_20d", "ndcg@20_risk_adjusted_future_return_20d", "precision@20_future_return_20d", "top_decile_capture@20", "downside_bad_top20_rate"]]),
        "",
        "## Rank Bucket Summary",
        "",
        markdown_table(bucket_summary[bucket_summary["split"] == "test"]),
        "",
        "## Safety",
        "",
        "- No Broker API, Paper Trading, order placement, capital allocation, promotion, or reader switch was performed.",
        "- Future returns, max returns, drawdowns, and downside labels are evaluation-only.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in frame.to_dict("records"):
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "metrics": output_dir / METRICS_FILENAME,
        "audit": output_dir / AUDIT_FILENAME,
        "by_strategy": output_dir / BY_STRATEGY_FILENAME,
        "by_year": output_dir / BY_YEAR_FILENAME,
        "by_date": output_dir / BY_DATE_FILENAME,
        "bucket": output_dir / BUCKET_FILENAME,
        "doc": DOC_PATH,
    }


def write_outputs(
    paths: dict[str, Path],
    metrics: dict[str, Any],
    audit: dict[str, Any],
    by_strategy: pd.DataFrame,
    by_year: pd.DataFrame,
    by_date: pd.DataFrame,
    bucket: pd.DataFrame,
) -> None:
    write_json(paths["metrics"], metrics)
    write_json(paths["audit"], audit)
    by_strategy.to_csv(paths["by_strategy"], index=False)
    by_year.to_csv(paths["by_year"], index=False)
    by_date.to_csv(paths["by_date"], index=False)
    bucket.to_csv(paths["bucket"], index=False)


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


def load_model_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return pickle.load(handle)


def read_json_optional(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


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
