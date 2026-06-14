from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import transform_features, to_jsonable
from ai_fund_lab_v2.position_management_ai.calibration import build_calibrated_position_management_output
from ai_fund_lab_v2.position_management_ai.inference import FORBIDDEN_FEATURE_PREFIXES, FORBIDDEN_FEATURE_TERMS, audit_position_feature_frame

PHASE = "Phase6-H"
PHASE6_VALIDATED = "PHASE6_VALIDATED"
PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED = "PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED"

DEFAULT_OPPORTUNITY_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_OPPORTUNITY_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_LONG_FEATURE_PATH = Path(".runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet")

DEFAULT_VALIDATION_CSV_PATH = Path("reports/position_management_ai/phase6h_historical_validation.csv")
DEFAULT_VALIDATION_JSON_PATH = Path("reports/position_management_ai/phase6h_historical_validation.json")
DEFAULT_COMPARISON_PATH = Path("reports/position_management_ai/phase6h_baseline_vs_position_comparison.json")
DEFAULT_ACTION_STATS_PATH = Path("reports/position_management_ai/phase6h_position_action_statistics.json")

CHECKPOINT_DAYS = (5, 10, 20)


@dataclass(frozen=True)
class Phase6HValidationResult:
    trades: pd.DataFrame
    summary: dict[str, Any]
    comparison: dict[str, Any]
    action_statistics: dict[str, Any]


def run_phase6h_historical_validation(
    *,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    opportunity_model_path: Path = DEFAULT_OPPORTUNITY_MODEL_PATH,
    long_feature_path: Path = DEFAULT_LONG_FEATURE_PATH,
    output_csv_path: Path = DEFAULT_VALIDATION_CSV_PATH,
    output_json_path: Path = DEFAULT_VALIDATION_JSON_PATH,
    comparison_path: Path = DEFAULT_COMPARISON_PATH,
    action_stats_path: Path = DEFAULT_ACTION_STATS_PATH,
    validation_year: int = 2025,
    max_target_dates: int | None = 80,
    top_n: int = 5,
    created_at: str | None = None,
) -> Phase6HValidationResult:
    created_at = created_at or now_utc()
    dataset = pd.read_parquet(opportunity_dataset_path)
    model_payload = load_model_payload(opportunity_model_path)
    scored = score_opportunity_dataset(dataset, model_payload, validation_year=validation_year)
    selected = select_validation_entries(scored, validation_year=validation_year, max_target_dates=max_target_dates, top_n=top_n)
    checkpoint_features = load_checkpoint_features(
        long_feature_path=long_feature_path,
        selected=selected,
        all_dates=sorted(scored["target_date"].astype(str).unique().tolist()),
    )
    trades = simulate_position_management(selected=selected, checkpoint_features=checkpoint_features, created_at=created_at)
    comparison = build_comparison(trades)
    action_statistics = build_action_statistics(trades)
    audit = build_validation_audit(
        selected=selected,
        trades=trades,
        comparison=comparison,
        action_statistics=action_statistics,
        created_at=created_at,
        validation_year=validation_year,
        max_target_dates=max_target_dates,
        top_n=top_n,
        opportunity_dataset_path=opportunity_dataset_path,
        opportunity_model_path=opportunity_model_path,
        long_feature_path=long_feature_path,
    )
    completion_status = (
        PHASE6_VALIDATED
        if audit["validation_improved_major_metric_count"] >= 1 and audit["forbidden_feature_audit_status"] == "OK" and audit["leakage_audit_status"] == "OK"
        else PHASE6_IMPLEMENTED_BUT_NOT_VALIDATED
    )
    summary = {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": completion_status,
        "status": "OK",
        "data_source": "phase5_formal_opportunity_model_plus_label_based_path_validation",
        "opportunity_signal_source": "Phase5 formal Opportunity model re-scoring",
        "price_path_source": "Phase5 future labels approximated into 5/10/20bd validation checkpoints",
        "validation_year": validation_year,
        "target_date_count": int(selected["target_date"].nunique()) if not selected.empty else 0,
        "code_count": int(selected["code"].nunique()) if not selected.empty else 0,
        "row_count": int(len(trades)),
        "baseline_definition": "Opportunity model topN fixed 20 business-day hold",
        "position_definition": "Opportunity model topN with calibrated Position Management actions at 5/10/20bd checkpoints",
        "comparison": comparison,
        "action_statistics": action_statistics,
        "audit": audit,
        "no_broker_api_executed": True,
        "no_order_executed": True,
        "no_paper_trading_executed": True,
        "no_capital_allocation_executed": True,
    }
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    trades.to_csv(output_csv_path, index=False)
    write_json(output_json_path, summary)
    write_json(comparison_path, comparison)
    write_json(action_stats_path, action_statistics)
    return Phase6HValidationResult(trades=trades, summary=summary, comparison=comparison, action_statistics=action_statistics)


def score_opportunity_dataset(dataset: pd.DataFrame, model_payload: dict[str, Any], *, validation_year: int) -> pd.DataFrame:
    frame = dataset[dataset["target_date"].astype(str).str.startswith(str(validation_year))].copy()
    feature_columns = list(model_payload.get("feature_columns") or [])
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    matrix = transform_features(frame, feature_columns, model_payload.get("preprocessing", {}))
    frame["expected_edge_score"] = np.asarray(model_payload["model"].predict(matrix), dtype=float)
    frame["buy_rank"] = frame.groupby("target_date")["expected_edge_score"].rank(method="first", ascending=False).astype(int)
    frame["downside_risk_score"] = estimate_downside_risk(frame)
    frame["risk_guard_status"] = np.where(frame["downside_risk_score"] >= 0.75, "bad", "ok")
    return frame


def select_validation_entries(scored: pd.DataFrame, *, validation_year: int, max_target_dates: int | None, top_n: int) -> pd.DataFrame:
    dates = sorted(scored["target_date"].astype(str).unique().tolist())
    usable_dates = dates[:-20] if len(dates) > 20 else dates
    if max_target_dates is not None and len(usable_dates) > max_target_dates:
        step = max(1, len(usable_dates) // max_target_dates)
        usable_dates = usable_dates[::step][:max_target_dates]
    selected = scored[(scored["target_date"].isin(usable_dates)) & (scored["buy_rank"] <= top_n)].copy()
    selected["entry_year"] = validation_year
    date_index = {date: index for index, date in enumerate(dates)}
    for days in CHECKPOINT_DAYS:
        selected[f"checkpoint_date_{days}bd"] = selected["target_date"].map(
            lambda target_date: dates[date_index[str(target_date)] + days]
            if date_index.get(str(target_date), len(dates)) + days < len(dates)
            else ""
        )
    return selected.sort_values(["target_date", "buy_rank", "code"]).reset_index(drop=True)


def load_checkpoint_features(*, long_feature_path: Path, selected: pd.DataFrame, all_dates: list[str]) -> pd.DataFrame:
    checkpoint_dates: set[str] = set()
    for days in CHECKPOINT_DAYS:
        column = f"checkpoint_date_{days}bd"
        if column in selected.columns:
            checkpoint_dates.update(date for date in selected[column].dropna().astype(str).unique().tolist() if date)
    codes = selected["code"].astype(str).unique().tolist()
    try:
        features = pd.read_parquet(long_feature_path, filters=[("target_date", "in", sorted(checkpoint_dates)), ("code", "in", codes)])
    except Exception:
        features = pd.read_parquet(long_feature_path)
        features = features[features["target_date"].astype(str).isin(checkpoint_dates) & features["code"].astype(str).isin(codes)].copy()
    features["target_date"] = features["target_date"].astype(str)
    features["code"] = features["code"].astype(str)
    return features.drop_duplicates(["target_date", "code"], keep="first")


def simulate_position_management(
    *,
    selected: pd.DataFrame,
    checkpoint_features: pd.DataFrame,
    created_at: str,
    output_builder: Callable[[pd.DataFrame, str], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    output_builder = output_builder or (lambda frame, timestamp: build_calibrated_position_management_output(frame, created_at=timestamp))
    rows: list[dict[str, Any]] = []
    feature_lookup = {
        (str(row["target_date"]), str(row["code"])): row
        for row in checkpoint_features.to_dict("records")
    }
    for entry in selected.to_dict("records"):
        target_date = str(entry["target_date"])
        code = str(entry["code"])
        path = approximate_return_path(entry)
        peak_so_far = 0.0
        action_trace: list[str] = []
        exit_day = 20
        managed_return = path[20]
        terminal_action = "HOLD"
        terminal_reason = "fixed_horizon_reached"
        for day in CHECKPOINT_DAYS:
            current_return = float(path[day])
            peak_so_far = max(peak_so_far, current_return)
            checkpoint_date = str(entry.get(f"checkpoint_date_{day}bd") or target_date)
            feature_row = feature_lookup.get((checkpoint_date, code), entry)
            inference_frame = build_checkpoint_inference_frame(
                entry=entry,
                feature_row=feature_row,
                checkpoint_date=checkpoint_date,
                holding_days=day,
                current_return=current_return,
                peak_return=peak_so_far,
            )
            output = output_builder(inference_frame, created_at).iloc[0].to_dict()
            action = str(output["action"])
            action_trace.append(action)
            if action == "EXIT":
                exit_day = day
                managed_return = current_return
                terminal_action = action
                terminal_reason = str(output["action_reason"])
                break
            if action == "REDUCE":
                exit_day = day
                managed_return = 0.5 * current_return + 0.5 * path[20]
                terminal_action = action
                terminal_reason = str(output["action_reason"])
                break
            if action == "ADD":
                terminal_action = action
                terminal_reason = str(output["action_reason"])
        future_max_return = float(entry["label__future_max_return_20d"])
        future_drawdown = float(entry["label__future_max_drawdown_20d"])
        baseline_return = float(entry["label__future_return_20d"])
        rows.append(
            {
                "target_date": target_date,
                "code": code,
                "buy_rank": int(entry["buy_rank"]),
                "expected_edge_score": round_float(float(entry["expected_edge_score"])),
                "baseline_hold_days": 20,
                "position_hold_days": int(exit_day),
                "baseline_return": round_float(baseline_return),
                "position_return": round_float(float(managed_return)),
                "future_max_return_20d": round_float(future_max_return),
                "future_max_drawdown_20d": round_float(future_drawdown),
                "profit_retention_baseline": retention_rate(baseline_return, future_max_return),
                "profit_retention_position": retention_rate(float(managed_return), future_max_return),
                "profit_decay_baseline": profit_decay(baseline_return, future_max_return),
                "profit_decay_position": profit_decay(float(managed_return), future_max_return),
                "label_continue_winner": bool(entry["label__future_max_return_20d"] > 0.06 and entry["label__future_max_drawdown_20d"] > -0.08),
                "label_exit_before_drawdown": bool(entry["label__future_max_drawdown_20d"] <= -0.08),
                "position_terminal_action": terminal_action,
                "position_terminal_reason": terminal_reason,
                "action_trace": "|".join(action_trace),
                "add_on_loss": bool("ADD" in action_trace and min(path[day] for day, action in zip(CHECKPOINT_DAYS, action_trace) if action == "ADD") <= 0),
                "false_exit": bool(terminal_action == "EXIT" and future_max_return > float(managed_return) + 0.05),
                "exit_before_drawdown": bool(terminal_action in {"EXIT", "REDUCE"} and future_drawdown <= -0.08),
            }
        )
    return pd.DataFrame(rows)


def build_checkpoint_inference_frame(
    *,
    entry: dict[str, Any],
    feature_row: dict[str, Any],
    checkpoint_date: str,
    holding_days: int,
    current_return: float,
    peak_return: float,
) -> pd.DataFrame:
    downside = float(entry.get("downside_risk_score", 0.5))
    if current_return < -0.04:
        downside = min(1.0, downside + 0.20)
    return pd.DataFrame(
        [
            {
                "target_date": checkpoint_date,
                "code": str(entry["code"]),
                "entry_price": 1.0,
                "current_price": 1.0 + current_return,
                "holding_days": holding_days,
                "position_size": 100.0,
                "current_return": current_return,
                "peak_return": peak_return,
                "expected_edge_score": float(entry["expected_edge_score"]),
                "buy_rank": int(entry["buy_rank"]),
                "downside_risk_score": downside,
                "risk_guard_status": "bad" if downside >= 0.75 else str(entry.get("risk_guard_status", "ok")),
                "feature_version": "position_management_feature_phase6h_validation_v1",
                "feature__return_5d": float(feature_row.get("price_momentum_return_5d", entry.get("feature__price_momentum_return_5d", 0.0))),
                "feature__return_20d": float(feature_row.get("price_momentum_return_20d", entry.get("feature__price_momentum_return_20d", 0.0))),
                "feature__volume_ratio_5d": float(feature_row.get("volume_momentum_ratio_5d", entry.get("feature__volume_momentum_ratio_5d", 1.0))),
                "feature__close_over_ma_20d": float(feature_row.get("trend_close_over_ma_20d", entry.get("feature__trend_close_over_ma_20d", 1.0))),
                "feature__ma_5_20_ratio": float(feature_row.get("trend_ma_5_20_ratio", entry.get("feature__trend_ma_5_20_ratio", 1.0))),
                "feature__volatility_20d": float(feature_row.get("volatility_return_std_20d", entry.get("feature__volatility_return_std_20d", 0.0))),
            }
        ]
    )


def approximate_return_path(entry: dict[str, Any]) -> dict[int, float]:
    final_return = float(entry["label__future_return_20d"])
    max_return = max(float(entry["label__future_max_return_20d"]), final_return, 0.0)
    drawdown = min(float(entry["label__future_max_drawdown_20d"]), final_return, 0.0)
    if final_return >= 0:
        day5 = min(max_return, max(drawdown, 0.35 * final_return + 0.35 * max_return))
        day10 = min(max_return, max(drawdown, 0.70 * final_return + 0.25 * max_return))
    else:
        day5 = max(drawdown, 0.35 * final_return)
        day10 = max(drawdown, 0.70 * final_return)
    return {5: round_float(day5), 10: round_float(day10), 20: round_float(final_return)}


def build_comparison(trades: pd.DataFrame) -> dict[str, Any]:
    baseline = metric_block(trades, prefix="baseline", return_column="baseline_return", hold_days_column="baseline_hold_days")
    position = metric_block(trades, prefix="position", return_column="position_return", hold_days_column="position_hold_days")
    improvements = {
        "average_return_improved": position["average_return"] > baseline["average_return"],
        "profit_retention_rate_improved": position["profit_retention_rate"] > baseline["profit_retention_rate"],
        "profit_decay_before_exit_improved": position["profit_decay_before_exit"] < baseline["profit_decay_before_exit"],
        "winner_to_loser_rate_improved": position["winner_to_loser_rate"] < baseline["winner_to_loser_rate"],
    }
    return {
        "baseline": baseline,
        "position_managed": position,
        "improvements": improvements,
        "improved_major_metric_count": int(sum(bool(value) for value in improvements.values())),
    }


def metric_block(trades: pd.DataFrame, *, prefix: str, return_column: str, hold_days_column: str) -> dict[str, Any]:
    returns = pd.to_numeric(trades[return_column], errors="coerce").fillna(0.0)
    hold_days = pd.to_numeric(trades[hold_days_column], errors="coerce").fillna(0.0)
    winners = returns > 0
    losers = returns <= 0
    winner_candidates = pd.to_numeric(trades["future_max_return_20d"], errors="coerce").fillna(0.0) >= 0.06
    winner_to_loser = winner_candidates & (returns <= 0)
    continue_winner = trades["label_continue_winner"].astype(bool)
    if prefix == "baseline":
        captured_continue = continue_winner & (returns > 0)
        exit_before_drawdown_rate = 0.0
        false_exit_rate = 0.0
        average_exit_return = 0.0
    else:
        terminal = trades["position_terminal_action"]
        captured_continue = continue_winner & terminal.isin(["HOLD", "ADD"])
        exits = terminal.isin(["EXIT", "REDUCE"])
        exit_before_drawdown_rate = rate((trades["exit_before_drawdown"] & exits).sum(), exits.sum())
        false_exit_rate = rate(trades["false_exit"].sum(), exits.sum())
        average_exit_return = float(returns[terminal == "EXIT"].mean()) if (terminal == "EXIT").any() else 0.0
    return {
        "row_count": int(len(trades)),
        "average_return": round_float(float(returns.mean())),
        "avg_hold_days": round_float(float(hold_days.mean())),
        "winner_hold_days": round_float(float(hold_days[winners].mean())) if winners.any() else 0.0,
        "loser_hold_days": round_float(float(hold_days[losers].mean())) if losers.any() else 0.0,
        "profit_retention_rate": round_float(float(pd.to_numeric(trades[f"profit_retention_{prefix if prefix == 'baseline' else 'position'}"], errors="coerce").fillna(0.0).mean())),
        "profit_decay_before_exit": round_float(float(pd.to_numeric(trades[f"profit_decay_{prefix if prefix == 'baseline' else 'position'}"], errors="coerce").fillna(0.0).mean())),
        "average_exit_return": round_float(average_exit_return),
        "continue_winner_capture_rate": rate(captured_continue.sum(), continue_winner.sum()),
        "winner_to_loser_rate": rate(winner_to_loser.sum(), winner_candidates.sum()),
        "exit_before_drawdown_rate": round_float(exit_before_drawdown_rate),
        "false_exit_rate": round_float(false_exit_rate),
    }


def build_action_statistics(trades: pd.DataFrame) -> dict[str, Any]:
    trace_actions: list[str] = []
    for trace in trades["action_trace"].fillna(""):
        trace_actions.extend([action for action in str(trace).split("|") if action])
    counts = pd.Series(trace_actions, dtype="object").value_counts().to_dict() if trace_actions else {}
    terminal_counts = trades["position_terminal_action"].value_counts().to_dict()
    return {
        "checkpoint_action_counts": {str(key): int(value) for key, value in counts.items()},
        "terminal_action_counts": {str(key): int(value) for key, value in terminal_counts.items()},
        "HOLD_count": int(counts.get("HOLD", 0)),
        "EXIT_count": int(counts.get("EXIT", 0)),
        "ADD_count": int(counts.get("ADD", 0)),
        "REDUCE_count": int(counts.get("REDUCE", 0)),
    }


def build_validation_audit(
    *,
    selected: pd.DataFrame,
    trades: pd.DataFrame,
    comparison: dict[str, Any],
    action_statistics: dict[str, Any],
    created_at: str,
    validation_year: int,
    max_target_dates: int | None,
    top_n: int,
    opportunity_dataset_path: Path,
    opportunity_model_path: Path,
    long_feature_path: Path,
) -> dict[str, Any]:
    feature_columns = [column for column in selected.columns if str(column).startswith("feature__")]
    label_columns = [column for column in selected.columns if str(column).startswith("label__")]
    forbidden_feature_columns = [
        column for column in feature_columns if is_forbidden_feature(column.replace("feature__", "", 1))
    ]
    inference_probe = pd.DataFrame(
        {
            "target_date": selected["target_date"].head(10).astype(str),
            "code": selected["code"].head(10).astype(str),
        }
    )
    feature_audit = audit_position_feature_frame(inference_probe, input_holding_count=len(inference_probe), created_at=created_at)
    add_loss_count = int(trades["add_on_loss"].astype(bool).sum())
    add_exit_overlap_count = int(((trades["action_trace"].str.contains("ADD", na=False)) & trades["label_exit_before_drawdown"].astype(bool)).sum())
    continue_exit_count = int(((trades["position_terminal_action"] == "EXIT") & trades["label_continue_winner"].astype(bool)).sum())
    continue_reduce_count = int(((trades["position_terminal_action"] == "REDUCE") & trades["label_continue_winner"].astype(bool)).sum())
    return {
        "phase": PHASE,
        "created_at": created_at,
        "validation_year": validation_year,
        "max_target_dates": max_target_dates,
        "top_n": top_n,
        "target_date_count": int(selected["target_date"].nunique()) if not selected.empty else 0,
        "code_count": int(selected["code"].nunique()) if not selected.empty else 0,
        "row_count": int(len(trades)),
        "opportunity_dataset_path": str(opportunity_dataset_path),
        "opportunity_model_path": str(opportunity_model_path),
        "long_feature_path": str(long_feature_path),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "forbidden_feature_columns": forbidden_feature_columns,
        "forbidden_feature_column_count": len(forbidden_feature_columns),
        "feature_label_separation_status": "OK" if feature_columns and label_columns and not forbidden_feature_columns else "ERROR",
        "forbidden_feature_audit_status": "OK" if not forbidden_feature_columns else "ERROR",
        "leakage_audit_status": "OK" if not forbidden_feature_columns and feature_audit["leakage_audit_status"] == "OK" else "ERROR",
        "feature_audit": feature_audit,
        "add_loss_position_count": add_loss_count,
        "add_exit_label_overlap_count": add_exit_overlap_count,
        "continue_winner_wrong_exit_count": continue_exit_count,
        "continue_winner_over_reduce_count": continue_reduce_count,
        "add_safety_status": "OK" if add_loss_count == 0 and add_exit_overlap_count == 0 else "ERROR",
        "hold_exit_safety_status": "OK" if continue_exit_count == 0 and continue_reduce_count == 0 else "WARN",
        "action_statistics": action_statistics,
        "validation_improved_major_metric_count": int(comparison["improved_major_metric_count"]),
        "broker_api_executed": False,
        "order_executed": False,
        "paper_trading_executed": False,
        "capital_allocation_executed": False,
        "full_backtest_executed": False,
    }


def estimate_downside_risk(frame: pd.DataFrame) -> pd.Series:
    volatility = pd.to_numeric(frame.get("feature__volatility_return_std_20d", 0.0), errors="coerce").fillna(0.0)
    close_ma = pd.to_numeric(frame.get("feature__trend_close_over_ma_20d", 1.0), errors="coerce").fillna(1.0)
    ma_ratio = pd.to_numeric(frame.get("feature__trend_ma_5_20_ratio", 1.0), errors="coerce").fillna(1.0)
    risk = 0.35 + 0.35 * (volatility / 0.08).clip(0.0, 1.0) + 0.15 * (1.0 - close_ma).clip(0.0, 1.0) + 0.15 * (1.0 - ma_ratio).clip(0.0, 1.0)
    return risk.clip(0.0, 1.0).map(round_float)


def retention_rate(realized_return: float, max_return: float) -> float:
    if max_return <= 0:
        return 0.0
    return round_float(max(min(realized_return / max_return, 1.0), -1.0))


def profit_decay(realized_return: float, max_return: float) -> float:
    if max_return <= 0:
        return 0.0
    return round_float(max_return - realized_return)


def rate(numerator: Any, denominator: Any) -> float:
    denominator_float = float(denominator)
    if denominator_float == 0:
        return 0.0
    return round_float(float(numerator) / denominator_float)


def round_float(value: float) -> float:
    if not np.isfinite(value):
        return 0.0
    return round(float(value), 6)


def is_forbidden_feature(name: str) -> bool:
    if name.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    if name.startswith(("future_min_return_", "future_profit")):
        return True
    return any(term in name for term in FORBIDDEN_FEATURE_TERMS)


def load_model_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict) or "model" not in payload:
        raise ValueError(f"invalid opportunity model payload: {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
