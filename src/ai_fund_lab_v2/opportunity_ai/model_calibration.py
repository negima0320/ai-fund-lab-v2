from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from ai_fund_lab_v2.opportunity_ai.quality_audit import load_model_payload
from ai_fund_lab_v2.opportunity_ai.training import (
    TARGET_LABEL,
    audit_opportunity_training_dataset,
    fit_preprocessing,
    fit_simple_rule_baseline,
    regression_metric_block,
    selected_metric_block,
    simple_rule_scores,
    target_array,
    to_jsonable,
    transform_features,
)

PHASE = "Phase5-J"
READY_FOR_PHASE5K_POLICY_FINALIZATION = "READY_FOR_PHASE5K_POLICY_FINALIZATION"
NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW = "NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW"
BLOCKED_BY_INPUT = "BLOCKED_BY_INPUT"
BLOCKED_BY_LEAKAGE_AUDIT = "BLOCKED_BY_LEAKAGE_AUDIT"

DEFAULT_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_PHASE5I_METRICS_PATH = Path("reports/opportunity_ai/phase5i/full_history_combined_validation_metrics.json")
DEFAULT_PHASE5I_AUDIT_PATH = Path("reports/opportunity_ai/phase5i/full_history_audit.json")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5j")

METRICS_FILENAME = "calibration_metrics.json"
AUDIT_FILENAME = "calibration_audit.json"
BY_STRATEGY_FILENAME = "calibration_by_strategy.csv"
BY_DATE_FILENAME = "calibration_by_date.csv"
RECOMMENDED_POLICY_FILENAME = "recommended_policy.json"

EVALUATED_SPLITS = ("validation", "test")
TOPN_SELECTIONS = {"top5": 5, "top10": 10, "top20": 20}
POLICY_SELECTIONS = {
    "top5_only": 5,
    "top10_score_threshold": 10,
    "top10_gap_threshold": 10,
    "top10_excluding_weak_tail": 10,
}


@dataclass(frozen=True)
class CalibrationResult:
    metrics: dict[str, Any]
    audit: dict[str, Any]
    by_strategy: pd.DataFrame
    by_date: pd.DataFrame
    recommended_policy: dict[str, Any]


def run_model_improvement_calibration(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    phase5i_metrics_path: Path = DEFAULT_PHASE5I_METRICS_PATH,
    phase5i_audit_path: Path = DEFAULT_PHASE5I_AUDIT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> CalibrationResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / METRICS_FILENAME
    audit_path = output_dir / AUDIT_FILENAME
    by_strategy_path = output_dir / BY_STRATEGY_FILENAME
    by_date_path = output_dir / BY_DATE_FILENAME
    recommended_policy_path = output_dir / RECOMMENDED_POLICY_FILENAME

    missing_inputs = [
        str(path)
        for path in (dataset_path, model_path, phase5i_metrics_path, phase5i_audit_path)
        if not path.is_file()
    ]
    if missing_inputs:
        audit = blocked_audit(created_at=created_at, readiness_status=BLOCKED_BY_INPUT, missing_inputs=missing_inputs)
        metrics = metrics_shell(
            status="BLOCKED",
            readiness_status=BLOCKED_BY_INPUT,
            created_at=created_at,
            dataset_path=dataset_path,
            model_path=model_path,
            phase5i_metrics_path=phase5i_metrics_path,
            phase5i_audit_path=phase5i_audit_path,
            output_dir=output_dir,
            audit=audit,
        )
        by_strategy = pd.DataFrame()
        by_date = pd.DataFrame()
        recommended_policy = build_blocked_policy(BLOCKED_BY_INPUT, "Required Phase5-I inputs are missing.")
        write_outputs(metrics_path, audit_path, by_strategy_path, by_date_path, recommended_policy_path, metrics, audit, by_strategy, by_date, recommended_policy)
        return CalibrationResult(metrics, audit, by_strategy, by_date, recommended_policy)

    dataset = pd.read_parquet(dataset_path)
    model_payload = load_model_payload(model_path)
    phase5i_metrics = read_json(phase5i_metrics_path)
    phase5i_audit = read_json(phase5i_audit_path)
    feature_columns = list(model_payload.get("feature_columns") or sorted(column for column in dataset.columns if str(column).startswith("feature__")))
    label_columns = sorted(column for column in dataset.columns if str(column).startswith("label__"))
    training_audit = audit_opportunity_training_dataset(
        dataset,
        feature_columns=feature_columns,
        label_columns=label_columns,
        created_at=created_at,
    )
    if training_audit.get("leakage_audit_status") != "OK":
        audit = {
            **blocked_audit(created_at=created_at, readiness_status=BLOCKED_BY_LEAKAGE_AUDIT, missing_inputs=[]),
            **leakage_audit_counts(training_audit),
        }
        metrics = metrics_shell(
            status="BLOCKED",
            readiness_status=BLOCKED_BY_LEAKAGE_AUDIT,
            created_at=created_at,
            dataset_path=dataset_path,
            model_path=model_path,
            phase5i_metrics_path=phase5i_metrics_path,
            phase5i_audit_path=phase5i_audit_path,
            output_dir=output_dir,
            audit=audit,
        )
        by_strategy = pd.DataFrame()
        by_date = pd.DataFrame()
        recommended_policy = build_blocked_policy(BLOCKED_BY_LEAKAGE_AUDIT, "Training feature leakage audit failed.")
        write_outputs(metrics_path, audit_path, by_strategy_path, by_date_path, recommended_policy_path, metrics, audit, by_strategy, by_date, recommended_policy)
        return CalibrationResult(metrics, audit, by_strategy, by_date, recommended_policy)

    split_frames = {split: dataset[dataset["split"] == split].copy() for split in ("train", *EVALUATED_SPLITS)}
    scored_splits = score_all_strategies(split_frames, feature_columns, model_payload)
    thresholds = fit_policy_thresholds(scored_splits["validation"])
    by_strategy = build_by_strategy_table(scored_splits, thresholds)
    by_date = build_by_date_table(scored_splits, thresholds)
    strategy_summary = build_strategy_summary(by_strategy)
    top6_10_analysis = analyze_top6_10_tail(by_date)
    validation_test_gap = calculate_strategy_validation_test_gap(by_strategy)
    score_distribution = build_score_distribution(scored_splits)
    recommended_policy = choose_recommended_policy(by_strategy, top6_10_analysis)
    readiness_status = resolve_readiness(
        training_audit=training_audit,
        by_strategy=by_strategy,
        score_distribution=score_distribution,
        recommended_policy=recommended_policy,
        validation_test_gap=validation_test_gap,
    )
    audit = {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_rows": int(len(dataset)),
        "target_date_count": int(dataset["target_date"].nunique()),
        "train_rows": int((dataset["split"] == "train").sum()),
        "validation_rows": int((dataset["split"] == "validation").sum()),
        "test_rows": int((dataset["split"] == "test").sum()),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        **leakage_audit_counts(training_audit),
        "leakage_status": training_audit.get("leakage_audit_status", "ERROR"),
        "strategy_count": int(by_strategy["strategy"].nunique()) if not by_strategy.empty else 0,
        "multiple_strategies_compared": bool(by_strategy["strategy"].nunique() >= 10) if not by_strategy.empty else False,
        "model_unique_score_count": score_distribution["model_unique_score_count"],
        "all_same_score": score_distribution["model_all_same_score"],
        "top5_policy_available": strategy_exists(by_strategy, "current_model_top5"),
        "top10_threshold_policy_available": strategy_exists(by_strategy, "top10_score_threshold_policy"),
        "top10_gap_policy_available": strategy_exists(by_strategy, "top10_gap_threshold_policy"),
        "top6_10_tail_investigated": top6_10_analysis["investigated"],
        "simple_rule_baseline_available": strategy_exists(by_strategy, "simple_rule_top10"),
        "candidate_score_blend_available": strategy_exists(by_strategy, "blend_candidate_score_model_top10"),
        "recommended_policy_available": bool(recommended_policy.get("policy_name")),
        "validation_test_gap_status": validation_test_gap["status"],
        "promotion_ready": False,
        "readiness_status": readiness_status,
    }
    metrics = {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "phase5i_metrics_path": str(phase5i_metrics_path),
        "phase5i_audit_path": str(phase5i_audit_path),
        "metrics_path": str(metrics_path),
        "audit_path": str(audit_path),
        "by_strategy_path": str(by_strategy_path),
        "by_date_path": str(by_date_path),
        "recommended_policy_path": str(recommended_policy_path),
        "promotion_ready": False,
        "phase5i_readiness_status": phase5i_audit.get("readiness_status", phase5i_metrics.get("readiness_status")),
        "phase5i_top5_lift_status": phase5i_audit.get("top5_lift_status"),
        "phase5i_top10_lift_status": phase5i_audit.get("top10_lift_status"),
        "phase5i_top20_lift_status": phase5i_audit.get("top20_lift_status"),
        "phase5i_top10_underperformance_status": phase5i_audit.get("top10_underperformance_status"),
        "strategy_summary": strategy_summary,
        "top6_10_tail_analysis": top6_10_analysis,
        "validation_test_gap": validation_test_gap,
        "score_distribution": score_distribution,
        "policy_thresholds": thresholds,
        "recommended_policy": recommended_policy,
        "training_executed": False,
        "model_parameter_adjustment_evaluated": True,
        "label_weight_adjustment_evaluated": True,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": (
            "Proceed to Phase5-K Policy Finalization without promotion."
            if readiness_status == READY_FOR_PHASE5K_POLICY_FINALIZATION
            else "Return to Phase5 label or feature review before policy finalization."
        ),
    }
    write_outputs(metrics_path, audit_path, by_strategy_path, by_date_path, recommended_policy_path, metrics, audit, by_strategy, by_date, recommended_policy)
    return CalibrationResult(metrics, audit, by_strategy, by_date, recommended_policy)


def score_all_strategies(
    split_frames: dict[str, pd.DataFrame],
    feature_columns: list[str],
    model_payload: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    train = split_frames["train"].copy()
    for frame in split_frames.values():
        for column in feature_columns:
            if column not in frame.columns:
                frame[column] = np.nan

    simple_rule_state = fit_simple_rule_baseline(train)
    adjusted_preprocessing = fit_preprocessing(train, feature_columns)
    x_train = transform_features(train, feature_columns, adjusted_preprocessing)
    y_train = target_array(train)
    adjusted_model = HistGradientBoostingRegressor(
        max_iter=120,
        learning_rate=0.035,
        max_leaf_nodes=9,
        l2_regularization=0.25,
        random_state=52,
    )
    adjusted_model.fit(x_train, y_train)
    weighted_model = HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.04,
        max_leaf_nodes=11,
        l2_regularization=0.20,
        random_state=53,
    )
    weighted_model.fit(x_train, build_label_weight_adjusted_target(train))

    scored: dict[str, pd.DataFrame] = {}
    for split_name, frame in split_frames.items():
        out = frame.copy()
        model_matrix = transform_features(out, feature_columns, model_payload.get("preprocessing", {}))
        adjusted_matrix = transform_features(out, feature_columns, adjusted_preprocessing)
        out["score__model"] = np.asarray(model_payload["model"].predict(model_matrix), dtype=float)
        out["score__candidate_score_baseline"] = pd.to_numeric(out.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
        out["score__simple_rule_baseline"] = simple_rule_scores(out, simple_rule_state)
        out["score__adjusted_model"] = np.asarray(adjusted_model.predict(adjusted_matrix), dtype=float)
        out["score__label_weight_adjusted_model"] = np.asarray(weighted_model.predict(adjusted_matrix), dtype=float)
        out["risk__downside_proxy"] = downside_risk_proxy(out)
        out["score__blend_candidate_score_model"] = blend_scores(out["score__model"], out["score__candidate_score_baseline"], 0.65, 0.35)
        out["score__risk_adjusted_model"] = zscore(out["score__model"]) - (0.30 * zscore(out["risk__downside_proxy"]))
        out["score__simple_rule_blend_model"] = blend_scores(out["score__model"], out["score__simple_rule_baseline"], 0.55, 0.45)
        scored[split_name] = out
    return {split: scored[split] for split in EVALUATED_SPLITS}


def build_label_weight_adjusted_target(train: pd.DataFrame) -> np.ndarray:
    future_return = numeric(train, "label__future_return_20d")
    future_max_return = numeric(train, "label__future_max_return_20d")
    future_max_drawdown = numeric(train, "label__future_max_drawdown_20d")
    downside_bad = numeric(train, "label__downside_bad_20d")
    top_decile = numeric(train, "label__top_decile_20d")
    target = (
        0.40 * future_return
        + 0.35 * future_max_return
        + 0.15 * top_decile
        - 0.35 * np.abs(future_max_drawdown)
        - 0.12 * downside_bad
    )
    return np.asarray(target, dtype=float)


def fit_policy_thresholds(validation: pd.DataFrame) -> dict[str, Any]:
    ranked = add_dense_rank(validation, score_column="score__model")
    model_top10 = ranked[ranked["policy_rank"] <= 10].copy()
    model_top6_10 = ranked[(ranked["policy_rank"] >= 6) & (ranked["policy_rank"] <= 10)].copy()
    top_scores = ranked.groupby("target_date")["score__model"].transform("max")
    top10_gaps = top_scores[ranked["policy_rank"] == 10] - ranked.loc[ranked["policy_rank"] == 10, "score__model"]
    score_threshold = quantile_or_default(model_top10["score__model"], 0.20, 0.0)
    gap_threshold = quantile_or_default(top10_gaps, 0.50, 0.0)
    weak_tail_score_threshold = quantile_or_default(model_top6_10["score__model"], 0.55, score_threshold)
    weak_tail_risk_threshold = quantile_or_default(model_top6_10["risk__downside_proxy"], 0.60, 1.0)
    return {
        "model_top10_score_floor_validation_p20": round_float(score_threshold),
        "model_top10_gap_ceiling_validation_median": round_float(gap_threshold),
        "top6_10_tail_score_floor_validation_p55": round_float(weak_tail_score_threshold),
        "top6_10_tail_risk_ceiling_validation_p60": round_float(weak_tail_risk_threshold),
    }


def build_by_strategy_table(scored_splits: dict[str, pd.DataFrame], thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    strategy_specs = fixed_strategy_specs()
    policy_specs = threshold_policy_specs(thresholds)
    for split_name, scored in scored_splits.items():
        candidate_metrics = selected_metric_block(scored)
        rows.append(metric_row(split_name, "candidate_top50_average", "candidate_top50", "average", candidate_metrics, candidate_metrics))
        for strategy, score_column, top_n in strategy_specs:
            selected = select_top_n_by_date(scored, score_column=score_column, top_n=top_n)
            rows.append(metric_row(split_name, strategy, score_column, f"top{top_n}", selected_metric_block(selected), candidate_metrics))
        for strategy, selector, selection in policy_specs:
            selected = selector(scored)
            rows.append(metric_row(split_name, strategy, "score__model", selection, selected_metric_block(selected), candidate_metrics))
    return pd.DataFrame(rows)


def build_by_date_table(scored_splits: dict[str, pd.DataFrame], thresholds: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    strategy_specs = fixed_strategy_specs()
    policy_specs = threshold_policy_specs(thresholds)
    for split_name, scored in scored_splits.items():
        for target_date, date_frame in scored.groupby("target_date"):
            candidate_metrics = selected_metric_block(date_frame)
            rows.append(metric_row(split_name, "candidate_top50_average", "candidate_top50", "average", candidate_metrics, candidate_metrics, target_date=str(target_date)))
            for strategy, score_column, top_n in strategy_specs:
                selected = select_top_n_by_date(date_frame, score_column=score_column, top_n=top_n)
                rows.append(metric_row(split_name, strategy, score_column, f"top{top_n}", selected_metric_block(selected), candidate_metrics, target_date=str(target_date)))
            for strategy, selector, selection in policy_specs:
                selected = selector(date_frame)
                rows.append(metric_row(split_name, strategy, "score__model", selection, selected_metric_block(selected), candidate_metrics, target_date=str(target_date)))
            top5 = select_top_n_by_date(date_frame, score_column="score__model", top_n=5)
            top10 = select_top_n_by_date(date_frame, score_column="score__model", top_n=10)
            tail = tail_rows(top10, top5)
            rows.append(metric_row(split_name, "current_model_top6_10_tail", "score__model", "top6_10", selected_metric_block(tail), candidate_metrics, target_date=str(target_date)))
    return pd.DataFrame(rows)


def fixed_strategy_specs() -> list[tuple[str, str, int]]:
    specs: list[tuple[str, str, int]] = []
    for prefix, score_column in (
        ("current_model", "score__model"),
        ("candidate_score", "score__candidate_score_baseline"),
        ("simple_rule", "score__simple_rule_baseline"),
        ("adjusted_model", "score__adjusted_model"),
        ("label_weight_adjusted", "score__label_weight_adjusted_model"),
        ("blend_candidate_score_model", "score__blend_candidate_score_model"),
        ("risk_adjusted_model", "score__risk_adjusted_model"),
        ("simple_rule_blend_model", "score__simple_rule_blend_model"),
    ):
        for selection, top_n in TOPN_SELECTIONS.items():
            specs.append((f"{prefix}_{selection}", score_column, top_n))
    return specs


def threshold_policy_specs(thresholds: dict[str, Any]) -> list[tuple[str, Callable[[pd.DataFrame], pd.DataFrame], str]]:
    score_floor = float(thresholds["model_top10_score_floor_validation_p20"])
    gap_ceiling = float(thresholds["model_top10_gap_ceiling_validation_median"])
    tail_score_floor = float(thresholds["top6_10_tail_score_floor_validation_p55"])
    tail_risk_ceiling = float(thresholds["top6_10_tail_risk_ceiling_validation_p60"])
    return [
        ("top5_only_policy", lambda frame: select_top_n_by_date(frame, score_column="score__model", top_n=5), "top5_only"),
        (
            "top10_score_threshold_policy",
            lambda frame: select_top_n_with_score_floor(frame, score_column="score__model", top_n=10, score_floor=score_floor),
            "top10_score_threshold",
        ),
        (
            "top10_gap_threshold_policy",
            lambda frame: select_top_n_with_gap_ceiling(frame, score_column="score__model", top_n=10, gap_ceiling=gap_ceiling),
            "top10_gap_threshold",
        ),
        (
            "top10_excluding_weak_tail_policy",
            lambda frame: select_top10_excluding_weak_tail(
                frame,
                score_column="score__model",
                tail_score_floor=tail_score_floor,
                tail_risk_ceiling=tail_risk_ceiling,
            ),
            "top10_excluding_weak_tail",
        ),
    ]


def select_top_n_by_date(scored: pd.DataFrame, *, score_column: str, top_n: int) -> pd.DataFrame:
    return (
        scored.sort_values(["target_date", score_column, "code"], ascending=[True, False, True])
        .groupby("target_date", group_keys=False)
        .head(top_n)
        .copy()
    )


def select_top_n_with_score_floor(scored: pd.DataFrame, *, score_column: str, top_n: int, score_floor: float) -> pd.DataFrame:
    selected = select_top_n_by_date(scored, score_column=score_column, top_n=top_n)
    return selected[pd.to_numeric(selected[score_column], errors="coerce") >= score_floor].copy()


def select_top_n_with_gap_ceiling(scored: pd.DataFrame, *, score_column: str, top_n: int, gap_ceiling: float) -> pd.DataFrame:
    ranked = add_dense_rank(scored, score_column=score_column)
    top_score = ranked.groupby("target_date")[score_column].transform("max")
    selected = ranked[(ranked["policy_rank"] <= top_n) & ((top_score - ranked[score_column]) <= gap_ceiling)].copy()
    return selected.drop(columns=["policy_rank"], errors="ignore")


def select_top10_excluding_weak_tail(
    scored: pd.DataFrame,
    *,
    score_column: str,
    tail_score_floor: float,
    tail_risk_ceiling: float,
) -> pd.DataFrame:
    ranked = add_dense_rank(scored, score_column=score_column)
    top5 = ranked[ranked["policy_rank"] <= 5].copy()
    tail = ranked[
        (ranked["policy_rank"] >= 6)
        & (ranked["policy_rank"] <= 10)
        & (pd.to_numeric(ranked[score_column], errors="coerce") >= tail_score_floor)
        & (pd.to_numeric(ranked["risk__downside_proxy"], errors="coerce") <= tail_risk_ceiling)
    ].copy()
    return pd.concat([top5, tail], ignore_index=True).drop(columns=["policy_rank"], errors="ignore")


def add_dense_rank(scored: pd.DataFrame, *, score_column: str) -> pd.DataFrame:
    ranked = scored.sort_values(["target_date", score_column, "code"], ascending=[True, False, True]).copy()
    ranked["policy_rank"] = ranked.groupby("target_date").cumcount() + 1
    return ranked


def tail_rows(top10: pd.DataFrame, top5: pd.DataFrame) -> pd.DataFrame:
    if top10.empty:
        return top10.copy()
    keys = set(zip(top5["target_date"].astype(str), top5["code"].astype(str)))
    mask = [(str(row.target_date), str(row.code)) not in keys for row in top10.itertuples(index=False)]
    return top10.loc[mask].copy()


def metric_row(
    split_name: str,
    strategy: str,
    ranker: str,
    selection: str,
    metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
    *,
    target_date: str | None = None,
) -> dict[str, Any]:
    row = {
        "split": split_name,
        "strategy": strategy,
        "ranker": ranker,
        "selection": selection,
        "selected_row_count": metrics["selected_row_count"],
        "selected_target_date_count": metrics["selected_target_date_count"],
        "mean_future_return_20d": metrics["selected_mean_future_return"],
        "mean_future_max_return_20d": metrics["selected_mean_future_max_return"],
        "top_decile_rate_20d": metrics["selected_top_decile_rate"],
        "downside_bad_rate_20d": metrics["selected_downside_bad_rate"],
        "mean_future_max_drawdown_20d": metrics["selected_mean_future_max_drawdown"],
        "win_rate_20d": metrics["win_rate_20d"],
        "candidate_top50_mean_future_return_20d": candidate_metrics["selected_mean_future_return"],
        "candidate_top50_mean_future_max_return_20d": candidate_metrics["selected_mean_future_max_return"],
        "candidate_top50_downside_bad_rate_20d": candidate_metrics["selected_downside_bad_rate"],
        "lift_vs_candidate_top50_future_return": round_float(
            metrics["selected_mean_future_return"] - candidate_metrics["selected_mean_future_return"]
        ),
        "lift_vs_candidate_top50_future_max_return": round_float(
            metrics["selected_mean_future_max_return"] - candidate_metrics["selected_mean_future_max_return"]
        ),
        "downside_bad_delta_vs_candidate_top50": round_float(
            metrics["selected_downside_bad_rate"] - candidate_metrics["selected_downside_bad_rate"]
        ),
    }
    if target_date is not None:
        row["target_date"] = target_date
    return row


def build_strategy_summary(by_strategy: pd.DataFrame) -> dict[str, Any]:
    if by_strategy.empty:
        return {}
    summary: dict[str, Any] = {}
    for split_name, split_frame in by_strategy.groupby("split"):
        split_summary: dict[str, Any] = {}
        for row in split_frame.to_dict("records"):
            split_summary[str(row["strategy"])] = {
                "selection": row["selection"],
                "selected_row_count": int(row["selected_row_count"]),
                "mean_future_return_20d": round_float(row["mean_future_return_20d"]),
                "mean_future_max_return_20d": round_float(row["mean_future_max_return_20d"]),
                "top_decile_rate_20d": round_float(row["top_decile_rate_20d"]),
                "downside_bad_rate_20d": round_float(row["downside_bad_rate_20d"]),
                "mean_future_max_drawdown_20d": round_float(row["mean_future_max_drawdown_20d"]),
                "win_rate_20d": round_float(row["win_rate_20d"]),
                "lift_vs_candidate_top50_future_return": round_float(row["lift_vs_candidate_top50_future_return"]),
            }
        summary[str(split_name)] = split_summary
    return summary


def analyze_top6_10_tail(by_date: pd.DataFrame) -> dict[str, Any]:
    tail = by_date[by_date["strategy"] == "current_model_top6_10_tail"].copy()
    top5 = by_date[by_date["strategy"] == "current_model_top5"].copy()
    top10 = by_date[by_date["strategy"] == "current_model_top10"].copy()
    result: dict[str, Any] = {"investigated": True, "by_split": {}}
    for split_name in EVALUATED_SPLITS:
        split_tail = tail[tail["split"] == split_name]
        split_top5 = top5[top5["split"] == split_name]
        split_top10 = top10[top10["split"] == split_name]
        result["by_split"][split_name] = {
            "tail_date_count": int(len(split_tail)),
            "tail_mean_future_return_20d": round_float(split_tail["mean_future_return_20d"].mean()),
            "top5_mean_future_return_20d": round_float(split_top5["mean_future_return_20d"].mean()),
            "top10_mean_future_return_20d": round_float(split_top10["mean_future_return_20d"].mean()),
            "tail_minus_top5_mean_future_return": round_float(
                split_tail["mean_future_return_20d"].mean() - split_top5["mean_future_return_20d"].mean()
            ),
            "tail_underperforming_date_count": int((split_tail["lift_vs_candidate_top50_future_return"] < 0).sum()),
            "top10_underperforming_date_count": int((split_top10["lift_vs_candidate_top50_future_return"] < 0).sum()),
            "tail_downside_bad_rate_20d": round_float(split_tail["downside_bad_rate_20d"].mean()),
            "top5_downside_bad_rate_20d": round_float(split_top5["downside_bad_rate_20d"].mean()),
        }
    test_tail = result["by_split"].get("test", {})
    result["status"] = (
        "TAIL_DILUTION_CONFIRMED"
        if test_tail.get("tail_minus_top5_mean_future_return", 0.0) < 0
        else "TAIL_DILUTION_NOT_CONFIRMED"
    )
    return result


def calculate_strategy_validation_test_gap(by_strategy: pd.DataFrame) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    severe = False
    for strategy in sorted(by_strategy["strategy"].unique()):
        validation = by_strategy[(by_strategy["split"] == "validation") & (by_strategy["strategy"] == strategy)]
        test = by_strategy[(by_strategy["split"] == "test") & (by_strategy["strategy"] == strategy)]
        if validation.empty or test.empty:
            continue
        delta = round_float(float(test.iloc[0]["mean_future_return_20d"]) - float(validation.iloc[0]["mean_future_return_20d"]))
        if abs(delta) > 0.10:
            severe = True
        rows.append({"strategy": strategy, "test_minus_validation_mean_future_return_20d": delta})
    return {"status": "WARNING" if severe else "OK", "by_strategy": rows}


def build_score_distribution(scored_splits: dict[str, pd.DataFrame]) -> dict[str, Any]:
    frames = []
    by_split: dict[str, Any] = {}
    for split_name, frame in scored_splits.items():
        scores = pd.to_numeric(frame["score__model"], errors="coerce")
        frames.append(scores)
        by_split[split_name] = {
            "row_count": int(len(scores)),
            "unique_score_count": int(scores.nunique(dropna=False)),
            "all_same_score": bool(scores.nunique(dropna=False) <= 1),
            "score_min": round_float(scores.min()),
            "score_max": round_float(scores.max()),
            "score_mean": round_float(scores.mean()),
            "score_std": round_float(scores.std()),
        }
    all_scores = pd.concat(frames, ignore_index=True) if frames else pd.Series(dtype=float)
    return {
        "model_unique_score_count": int(all_scores.nunique(dropna=False)),
        "model_all_same_score": bool(all_scores.nunique(dropna=False) <= 1),
        "by_split": by_split,
    }


def choose_recommended_policy(by_strategy: pd.DataFrame, top6_10_analysis: dict[str, Any]) -> dict[str, Any]:
    candidates = by_strategy[by_strategy["strategy"] != "candidate_top50_average"].copy()
    if candidates.empty:
        return build_blocked_policy(NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW, "No strategy comparison rows were generated.")
    pivot = {str(row["strategy"]): row for row in candidates.to_dict("records") if row["split"] == "test"}
    validation = {str(row["strategy"]): row for row in candidates.to_dict("records") if row["split"] == "validation"}
    scored: list[dict[str, Any]] = []
    for strategy, test_row in pivot.items():
        validation_row = validation.get(strategy, {})
        test_lift = float(test_row.get("lift_vs_candidate_top50_future_return", 0.0))
        validation_lift = float(validation_row.get("lift_vs_candidate_top50_future_return", 0.0))
        downside_delta = float(test_row.get("downside_bad_delta_vs_candidate_top50", 0.0))
        gap = float(test_row.get("mean_future_return_20d", 0.0)) - float(validation_row.get("mean_future_return_20d", 0.0) or 0.0)
        score = test_lift + (0.45 * validation_lift) - (0.20 * abs(gap)) - (0.04 * max(0.0, downside_delta))
        scored.append(
            {
                "strategy": strategy,
                "selection": test_row.get("selection"),
                "policy_score": round_float(score),
                "test_lift_vs_candidate_top50_future_return": round_float(test_lift),
                "validation_lift_vs_candidate_top50_future_return": round_float(validation_lift),
                "test_mean_future_return_20d": round_float(test_row.get("mean_future_return_20d")),
                "validation_mean_future_return_20d": round_float(validation_row.get("mean_future_return_20d", 0.0)),
                "test_downside_bad_delta_vs_candidate_top50": round_float(downside_delta),
                "test_selected_target_date_count": int(test_row.get("selected_target_date_count", 0)),
            }
        )
    ranked = sorted(scored, key=lambda row: row["policy_score"], reverse=True)
    best = ranked[0]
    return {
        "policy_name": best["strategy"],
        "selection": best["selection"],
        "recommendation_type": "calibration_candidate_not_promoted",
        "promotion_ready": False,
        "reader_switch_ready": False,
        "reason": build_policy_reason(best, top6_10_analysis),
        "best_policy_metrics": best,
        "top_policy_candidates": ranked[:10],
        "notes": [
            "Phase5-J compares candidate policies only.",
            "No production promotion, reader switch, Broker API, Paper Trading, order, or capital allocation was performed.",
            "Future labels were used only for evaluation and label-weighted training target construction, never as inference features.",
        ],
    }


def build_policy_reason(best: dict[str, Any], top6_10_analysis: dict[str, Any]) -> str:
    if "top10" in str(best["strategy"]) and "threshold" in str(best["strategy"]):
        return "Top10 threshold policy is preferred because it directly addresses weak Top6-10 tail dilution while keeping a Top10-style operating envelope."
    if "top5" in str(best["strategy"]):
        return "Top5 policy is preferred because fixed Top10 tail dilution remains visible in the full-history calibration."
    if top6_10_analysis.get("status") == "TAIL_DILUTION_CONFIRMED":
        return "The best policy ranks highest after accounting for persistent Top6-10 tail dilution."
    return "The best policy has the strongest combined validation/test lift score among compared Phase5-J strategies."


def resolve_readiness(
    *,
    training_audit: dict[str, Any],
    by_strategy: pd.DataFrame,
    score_distribution: dict[str, Any],
    recommended_policy: dict[str, Any],
    validation_test_gap: dict[str, Any],
) -> str:
    leakage_ok = training_audit.get("leakage_audit_status") == "OK"
    metrics_available = not by_strategy.empty and {"validation", "test"}.issubset(set(by_strategy["split"]))
    multiple_strategies = bool(by_strategy["strategy"].nunique() >= 10) if not by_strategy.empty else False
    test_rows = by_strategy[(by_strategy["split"] == "test") & (by_strategy["strategy"] != "candidate_top50_average")]
    any_test_lift = bool((test_rows["lift_vs_candidate_top50_future_return"] > 0).any()) if not test_rows.empty else False
    top5_unstable = top5_strategies_unstable(by_strategy)
    severe_issue = (
        not leakage_ok
        or not metrics_available
        or not multiple_strategies
        or score_distribution["model_all_same_score"]
        or validation_test_gap["status"] != "OK"
        or not recommended_policy.get("policy_name")
        or not any_test_lift
        or top5_unstable
    )
    return NEEDS_PHASE5_LABEL_OR_FEATURE_REVIEW if severe_issue else READY_FOR_PHASE5K_POLICY_FINALIZATION


def top5_strategies_unstable(by_strategy: pd.DataFrame) -> bool:
    top5_rows = by_strategy[
        (by_strategy["strategy"].str.contains("top5", regex=False))
        & (by_strategy["split"].isin(EVALUATED_SPLITS))
    ]
    if top5_rows.empty:
        return True
    return bool((top5_rows["lift_vs_candidate_top50_future_return"] < -0.05).all())


def downside_risk_proxy(frame: pd.DataFrame) -> np.ndarray:
    volatility = numeric(frame, "feature__volatility_return_std_20d")
    return_20d = numeric(frame, "feature__price_momentum_return_20d")
    trend = numeric(frame, "feature__trend_close_over_ma_20d")
    volume_ratio = numeric(frame, "feature__volume_momentum_ratio_1d_20d")
    risk = (
        0.45 * np.clip(volatility / 0.08, 0.0, 2.0)
        + 0.25 * np.clip(-return_20d / 0.20, 0.0, 2.0)
        + 0.20 * np.clip(-trend / 0.20, 0.0, 2.0)
        + 0.10 * np.clip((volume_ratio - 3.0) / 3.0, 0.0, 2.0)
    )
    return np.clip(risk / 2.0, 0.0, 1.0)


def blend_scores(left: pd.Series | np.ndarray, right: pd.Series | np.ndarray, left_weight: float, right_weight: float) -> np.ndarray:
    return left_weight * zscore(left) + right_weight * zscore(right)


def zscore(values: pd.Series | np.ndarray) -> np.ndarray:
    series = pd.to_numeric(pd.Series(values), errors="coerce").fillna(0.0)
    std = float(series.std()) if pd.notna(series.std()) and series.std() else 1.0
    mean = float(series.mean()) if pd.notna(series.mean()) else 0.0
    return ((series - mean) / std).to_numpy(dtype=float)


def numeric(frame: pd.DataFrame, column: str) -> np.ndarray:
    if column not in frame.columns:
        return np.zeros(len(frame), dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).to_numpy(dtype=float)


def quantile_or_default(series: pd.Series, quantile: float, default: float) -> float:
    value = pd.to_numeric(series, errors="coerce").dropna().quantile(quantile)
    return float(value) if pd.notna(value) else float(default)


def strategy_exists(by_strategy: pd.DataFrame, strategy: str) -> bool:
    return bool(not by_strategy.empty and (by_strategy["strategy"] == strategy).any())


def leakage_audit_counts(training_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "forbidden_feature_column_count": int(training_audit.get("forbidden_feature_column_count", 0)),
        "future_feature_column_count": int(training_audit.get("future_feature_column_count", 0)),
        "trade_result_feature_column_count": int(training_audit.get("trade_result_feature_column_count", 0)),
        "portfolio_feature_column_count": int(training_audit.get("portfolio_feature_column_count", 0)),
        "backtest_feature_column_count": int(training_audit.get("backtest_feature_column_count", 0)),
        "paper_trading_feature_column_count": int(training_audit.get("paper_trading_feature_column_count", 0)),
        "ai_output_feature_column_count": int(training_audit.get("ai_output_feature_column_count", 0)),
    }


def blocked_audit(*, created_at: str, readiness_status: str, missing_inputs: list[str]) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "dataset_rows": 0,
        "target_date_count": 0,
        "train_rows": 0,
        "validation_rows": 0,
        "test_rows": 0,
        "feature_column_count": 0,
        "label_column_count": 0,
        "leakage_status": "NOT_RUN",
        "forbidden_feature_column_count": 0,
        "future_feature_column_count": 0,
        "trade_result_feature_column_count": 0,
        "portfolio_feature_column_count": 0,
        "backtest_feature_column_count": 0,
        "strategy_count": 0,
        "multiple_strategies_compared": False,
        "top6_10_tail_investigated": False,
        "recommended_policy_available": False,
        "promotion_ready": False,
        "readiness_status": readiness_status,
        "missing_inputs": missing_inputs,
    }


def metrics_shell(
    *,
    status: str,
    readiness_status: str,
    created_at: str,
    dataset_path: Path,
    model_path: Path,
    phase5i_metrics_path: Path,
    phase5i_audit_path: Path,
    output_dir: Path,
    audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": status,
        "readiness_status": readiness_status,
        "created_at": created_at,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "phase5i_metrics_path": str(phase5i_metrics_path),
        "phase5i_audit_path": str(phase5i_audit_path),
        "output_dir": str(output_dir),
        "promotion_ready": False,
        "dataset_rows": int(audit.get("dataset_rows", 0)),
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }


def build_blocked_policy(readiness_status: str, reason: str) -> dict[str, Any]:
    return {
        "policy_name": None,
        "recommendation_type": "blocked",
        "readiness_status": readiness_status,
        "reason": reason,
        "promotion_ready": False,
        "reader_switch_ready": False,
    }


def write_outputs(
    metrics_path: Path,
    audit_path: Path,
    by_strategy_path: Path,
    by_date_path: Path,
    recommended_policy_path: Path,
    metrics: dict[str, Any],
    audit: dict[str, Any],
    by_strategy: pd.DataFrame,
    by_date: pd.DataFrame,
    recommended_policy: dict[str, Any],
) -> None:
    write_json(metrics_path, metrics)
    write_json(audit_path, audit)
    write_json(recommended_policy_path, recommended_policy)
    by_strategy.to_csv(by_strategy_path, index=False)
    by_date.to_csv(by_date_path, index=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def round_float(value: Any, digits: int = 6) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric_value) or math.isinf(numeric_value):
        return 0.0
    return round(numeric_value, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
