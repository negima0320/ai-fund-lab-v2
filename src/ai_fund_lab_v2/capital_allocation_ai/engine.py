from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.policy import (
    calculate_available_cash,
    calculate_buy_amount,
    calculate_cash_buffer,
    calculate_target_position_value,
    calculate_weight,
    float_or_default,
    int_or_none,
    is_primary_buy_candidate,
    is_risk_guard_bad,
    is_watch_candidate,
    round_float,
    should_defensive_review,
    should_emergency_exit,
    should_replace,
)
from ai_fund_lab_v2.capital_allocation_ai.schema import (
    DECISION_COLUMNS,
    CapitalAllocationAction,
    DecisionRecord,
    Phase7AConfig,
    PortfolioSnapshot,
)

PHASE = "Phase7-A"
MODEL_VERSION = "capital_allocation_policy_phase7a_v1"
READY_FOR_PHASE7A_VALIDATION = "READY_FOR_PHASE7A_VALIDATION"

DEFAULT_OUTPUT_DIR = Path("reports/capital_allocation_ai/phase7a")
DECISION_CSV_FILENAME = "capital_allocation_decisions.csv"
DECISION_PARQUET_FILENAME = "capital_allocation_decisions.parquet"
SUMMARY_FILENAME = "capital_allocation_summary.json"
AUDIT_FILENAME = "capital_allocation_audit.json"


class Phase7AInputError(ValueError):
    pass


def run_capital_allocation_engine(
    *,
    portfolio: PortfolioSnapshot,
    opportunity_frame: pd.DataFrame,
    holdings_frame: pd.DataFrame,
    position_signal_frame: pd.DataFrame,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    config: Phase7AConfig | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    config = config or Phase7AConfig()
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)

    decisions = build_capital_allocation_decisions(
        portfolio=portfolio,
        opportunity_frame=opportunity_frame,
        holdings_frame=holdings_frame,
        position_signal_frame=position_signal_frame,
        config=config,
    )
    decision_frame = pd.DataFrame([decision.to_dict() for decision in decisions], columns=DECISION_COLUMNS)
    audit = build_runtime_audit(decision_frame, config=config, created_at=created_at)
    summary = build_summary(decision_frame, audit=audit, output_dir=output_dir, config=config, created_at=created_at)

    csv_path = output_dir / DECISION_CSV_FILENAME
    parquet_path = output_dir / DECISION_PARQUET_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME
    audit_path = output_dir / AUDIT_FILENAME
    decision_frame.to_csv(csv_path, index=False)
    decision_frame.to_parquet(parquet_path, index=False)
    summary["artifact_paths"] = {
        "decisions_csv": str(csv_path),
        "decisions_parquet": str(parquet_path),
        "summary": str(summary_path),
        "audit": str(audit_path),
    }
    audit["artifact_paths"] = summary["artifact_paths"]
    write_json(summary_path, summary)
    write_json(audit_path, audit)
    return {"decisions": decision_frame, "summary": summary, "audit": audit}


def build_capital_allocation_decisions(
    *,
    portfolio: PortfolioSnapshot,
    opportunity_frame: pd.DataFrame,
    holdings_frame: pd.DataFrame,
    position_signal_frame: pd.DataFrame,
    config: Phase7AConfig | None = None,
) -> list[DecisionRecord]:
    config = config or Phase7AConfig()
    opportunities = normalize_opportunity_frame(opportunity_frame)
    holdings = normalize_holdings_frame(holdings_frame)
    signals = normalize_position_signal_frame(position_signal_frame)
    target_position_value = calculate_target_position_value(portfolio.total_assets, config)
    target_weight = calculate_weight(target_position_value, portfolio.total_assets)
    available_cash = calculate_available_cash(portfolio.cash, portfolio.total_assets, config)
    cash_cursor = portfolio.cash

    opportunity_by_code = {str(row.code): row for row in opportunities.itertuples(index=False)}
    signal_by_code = {str(row.code): row for row in signals.itertuples(index=False)}
    holding_codes = set(holdings["code"].astype(str).tolist())
    top3 = opportunities[opportunities["buy_rank"] <= config.primary_buy_rank_cutoff].sort_values(["buy_rank", "code"])
    replace_buy_codes: set[str] = set()

    decisions: list[DecisionRecord] = []
    for row in holdings.sort_values(["code"]).itertuples(index=False):
        code = str(row.code)
        opportunity = opportunity_by_code.get(code)
        signal = signal_by_code.get(code)
        position_signal = str(getattr(signal, "position_signal", "") or "")
        current_value = float_or_default(getattr(row, "current_position_value", 0.0), 0.0)
        unrealized_return = float_or_default(getattr(row, "unrealized_return", 0.0), 0.0)
        holding_days = int(float_or_default(getattr(row, "holding_days", 0), 0.0))
        opportunity_rank = int_or_none(getattr(opportunity, "buy_rank", None)) if opportunity is not None else None
        expected_edge = float_or_default(getattr(opportunity, "expected_edge_score", 0.0), 0.0) if opportunity is not None else 0.0
        downside = float_or_default(getattr(opportunity, "downside_risk_score", 0.0), 0.0) if opportunity is not None else 0.0
        risk_guard = str(getattr(opportunity, "risk_guard_status", "") or "") if opportunity is not None else ""
        replacement_confirmation_days = int(float_or_default(getattr(signal, "replacement_confirmation_days", 0), 0.0)) if signal is not None else 0
        cash_before = cash_cursor
        best_new_top3 = first_unheld_top3(top3, holding_codes | replace_buy_codes)
        best_new_top3_score = float_or_default(getattr(best_new_top3, "expected_edge_score", 0.0), 0.0) if best_new_top3 is not None else 0.0

        if should_emergency_exit(unrealized_return, config):
            sell_amount = current_value
            cash_cursor = round_float(cash_cursor + sell_amount)
            decisions.append(
                base_decision(
                    portfolio=portfolio,
                    code=code,
                    action=CapitalAllocationAction.EMERGENCY_EXIT,
                    current_position_value=current_value,
                    target_position_value=0.0,
                    current_weight=calculate_weight(current_value, portfolio.total_assets),
                    target_weight=0.0,
                    sell_amount=sell_amount,
                    cash_before_action=cash_before,
                    cash_after_action=cash_cursor,
                    expected_edge_score=expected_edge,
                    buy_rank=opportunity_rank,
                    opportunity_rank=opportunity_rank,
                    downside_risk_score=downside,
                    risk_guard_status=risk_guard,
                    position_signal=position_signal,
                    holding_days=holding_days,
                    unrealized_return=unrealized_return,
                    emergency_reason=f"unrealized_return_at_or_below_{config.emergency_exit_pct}",
                    validation_notes="mechanical_full_exit_candidate_no_order_executed",
                )
            )
            continue

        defensive, defensive_reason = should_defensive_review(position_signal, risk_guard, downside, config)
        if defensive:
            decisions.append(
                base_decision(
                    portfolio=portfolio,
                    code=code,
                    action=CapitalAllocationAction.DEFENSIVE_REVIEW,
                    current_position_value=current_value,
                    target_position_value=target_position_value,
                    current_weight=calculate_weight(current_value, portfolio.total_assets),
                    target_weight=target_weight,
                    cash_before_action=cash_before,
                    cash_after_action=cash_cursor,
                    expected_edge_score=expected_edge,
                    buy_rank=opportunity_rank,
                    opportunity_rank=opportunity_rank,
                    downside_risk_score=downside,
                    risk_guard_status=risk_guard,
                    position_signal=position_signal,
                    holding_days=holding_days,
                    unrealized_return=unrealized_return,
                    defensive_reason=defensive_reason,
                    validation_notes="sell_amount_zero_phase6_signal_is_review_only",
                )
            )
            continue

        replace, replacement_reason = should_replace(
            holding_days=holding_days,
            opportunity_rank=opportunity_rank,
            holding_expected_edge_score=expected_edge,
            replacement_candidate_expected_edge_score=best_new_top3_score,
            replacement_confirmation_days=replacement_confirmation_days,
            position_signal=position_signal,
            risk_guard_status=risk_guard,
            downside_risk_score=downside,
            config=config,
        )
        if replace and best_new_top3 is not None:
            sell_amount = min(current_value, current_value)
            cash_cursor = round_float(cash_cursor + sell_amount)
            decisions.append(
                base_decision(
                    portfolio=portfolio,
                    code=code,
                    action=CapitalAllocationAction.REPLACE_SELL,
                    current_position_value=current_value,
                    target_position_value=0.0,
                    current_weight=calculate_weight(current_value, portfolio.total_assets),
                    target_weight=0.0,
                    sell_amount=sell_amount,
                    cash_before_action=cash_before,
                    cash_after_action=cash_cursor,
                    expected_edge_score=expected_edge,
                    buy_rank=opportunity_rank,
                    opportunity_rank=opportunity_rank,
                    downside_risk_score=downside,
                    risk_guard_status=risk_guard,
                    position_signal=position_signal,
                    holding_days=holding_days,
                    unrealized_return=unrealized_return,
                    replacement_reason=replacement_reason,
                    validation_notes="replacement_sell_candidate_no_order_executed",
                )
            )
            buy_cash_before = cash_cursor
            replacement_buy_amount = calculate_buy_amount(
                target_position_value=target_position_value,
                current_position_value=0.0,
                available_cash=min(cash_cursor - calculate_cash_buffer(portfolio.total_assets, config), target_position_value),
                config=config,
            )
            cash_cursor = round_float(cash_cursor - replacement_buy_amount)
            replace_buy_codes.add(str(best_new_top3.code))
            decisions.append(
                base_decision(
                    portfolio=portfolio,
                    code=str(best_new_top3.code),
                    action=CapitalAllocationAction.REPLACE_BUY,
                    current_position_value=0.0,
                    target_position_value=target_position_value,
                    current_weight=0.0,
                    target_weight=target_weight,
                    buy_amount=replacement_buy_amount,
                    cash_before_action=buy_cash_before,
                    cash_after_action=cash_cursor,
                    expected_edge_score=float_or_default(best_new_top3.expected_edge_score, 0.0),
                    buy_rank=int_or_none(best_new_top3.buy_rank),
                    opportunity_rank=int_or_none(best_new_top3.buy_rank),
                    downside_risk_score=float_or_default(best_new_top3.downside_risk_score, 0.0),
                    risk_guard_status=str(best_new_top3.risk_guard_status or ""),
                    position_signal="",
                    holding_days=0,
                    unrealized_return=0.0,
                    replacement_reason=f"paired_with_replace_sell_{code}",
                    validation_notes="replacement_buy_candidate_no_order_executed",
                )
            )
            continue

        decisions.append(
            base_decision(
                portfolio=portfolio,
                code=code,
                action=CapitalAllocationAction.HOLD,
                current_position_value=current_value,
                target_position_value=target_position_value,
                current_weight=calculate_weight(current_value, portfolio.total_assets),
                target_weight=target_weight,
                cash_before_action=cash_before,
                cash_after_action=cash_cursor,
                expected_edge_score=expected_edge,
                buy_rank=opportunity_rank,
                opportunity_rank=opportunity_rank,
                downside_risk_score=downside,
                risk_guard_status=risk_guard,
                position_signal=position_signal,
                holding_days=holding_days,
                unrealized_return=unrealized_return,
                replacement_reason=replacement_reason if replacement_reason else "",
                validation_notes="hold_centered_policy_no_daily_top3_sync_replace",
            )
        )

    held_or_replace_buy_codes = holding_codes | replace_buy_codes
    for row in opportunities.sort_values(["buy_rank", "code"]).itertuples(index=False):
        code = str(row.code)
        if code in held_or_replace_buy_codes:
            continue
        cash_before = cash_cursor
        if is_primary_buy_candidate(pd.Series(row._asdict()), config) and not is_risk_guard_bad(getattr(row, "risk_guard_status", "")):
            buy_amount = calculate_buy_amount(
                target_position_value=target_position_value,
                current_position_value=0.0,
                available_cash=calculate_available_cash(cash_cursor, portfolio.total_assets, config),
                config=config,
            )
            action = CapitalAllocationAction.BUY if buy_amount > 0 else CapitalAllocationAction.NO_ACTION
            cash_cursor = round_float(cash_cursor - buy_amount)
            note = "primary_top3_buy_candidate" if buy_amount > 0 else "insufficient_available_cash_or_below_min_position_value"
        elif is_watch_candidate(pd.Series(row._asdict()), config):
            buy_amount = 0.0
            action = CapitalAllocationAction.NO_ACTION
            note = "top4_5_watch_backup_no_buy"
        else:
            buy_amount = 0.0
            action = CapitalAllocationAction.NO_ACTION
            note = "top6_or_lower_no_buy"
        decisions.append(
            base_decision(
                portfolio=portfolio,
                code=code,
                action=action,
                current_position_value=0.0,
                target_position_value=target_position_value if action == CapitalAllocationAction.BUY else 0.0,
                current_weight=0.0,
                target_weight=target_weight if action == CapitalAllocationAction.BUY else 0.0,
                buy_amount=buy_amount,
                cash_before_action=cash_before,
                cash_after_action=cash_cursor,
                expected_edge_score=float_or_default(row.expected_edge_score, 0.0),
                buy_rank=int_or_none(row.buy_rank),
                opportunity_rank=int_or_none(row.buy_rank),
                downside_risk_score=float_or_default(row.downside_risk_score, 0.0),
                risk_guard_status=str(row.risk_guard_status or ""),
                position_signal="",
                holding_days=0,
                unrealized_return=0.0,
                validation_notes=note,
            )
        )
    return decisions


def base_decision(
    *,
    portfolio: PortfolioSnapshot,
    code: str,
    action: CapitalAllocationAction,
    current_position_value: float,
    target_position_value: float,
    current_weight: float,
    target_weight: float,
    cash_before_action: float,
    cash_after_action: float,
    expected_edge_score: float,
    buy_rank: int | None,
    opportunity_rank: int | None,
    downside_risk_score: float,
    risk_guard_status: str,
    position_signal: str,
    holding_days: int,
    unrealized_return: float,
    buy_amount: float = 0.0,
    sell_amount: float = 0.0,
    replacement_reason: str = "",
    defensive_reason: str = "",
    emergency_reason: str = "",
    validation_notes: str = "",
) -> DecisionRecord:
    return DecisionRecord(
        target_date=portfolio.target_date,
        code=str(code),
        action=action.value,
        current_position_value=round_float(current_position_value),
        target_position_value=round_float(target_position_value),
        current_weight=round_float(current_weight),
        target_weight=round_float(target_weight),
        buy_amount=round_float(buy_amount),
        sell_amount=round_float(sell_amount),
        cash_before_action=round_float(cash_before_action),
        cash_after_action=round_float(cash_after_action),
        expected_edge_score=round_float(expected_edge_score),
        buy_rank=buy_rank,
        opportunity_rank=opportunity_rank,
        downside_risk_score=round_float(downside_risk_score),
        risk_guard_status=str(risk_guard_status or ""),
        position_signal=str(position_signal or ""),
        holding_days=int(holding_days),
        unrealized_return=round_float(unrealized_return),
        replacement_reason=replacement_reason,
        defensive_reason=defensive_reason,
        emergency_reason=emergency_reason,
        validation_notes=validation_notes,
    )


def normalize_opportunity_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"target_date", "code", "expected_edge_score", "buy_rank"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise Phase7AInputError(f"opportunity frame missing columns: {missing}")
    out = frame.copy()
    out["code"] = out["code"].astype(str)
    out["target_date"] = out["target_date"].astype(str)
    if "downside_risk_score" not in out.columns:
        out["downside_risk_score"] = 0.0
    if "risk_guard_status" not in out.columns:
        out["risk_guard_status"] = ""
    out["buy_rank"] = pd.to_numeric(out["buy_rank"], errors="coerce").fillna(999).astype(int)
    out["expected_edge_score"] = pd.to_numeric(out["expected_edge_score"], errors="coerce").fillna(0.0)
    out["downside_risk_score"] = pd.to_numeric(out["downside_risk_score"], errors="coerce").fillna(0.0)
    return out.drop_duplicates(["target_date", "code"], keep="first")


def normalize_holdings_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"target_date", "code", "current_position_value"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise Phase7AInputError(f"holdings frame missing columns: {missing}")
    out = frame.copy()
    out["code"] = out["code"].astype(str)
    out["target_date"] = out["target_date"].astype(str)
    if "holding_days" not in out.columns:
        out["holding_days"] = 0
    if "unrealized_return" not in out.columns:
        out["unrealized_return"] = 0.0
    out["current_position_value"] = pd.to_numeric(out["current_position_value"], errors="coerce").fillna(0.0)
    out["holding_days"] = pd.to_numeric(out["holding_days"], errors="coerce").fillna(0).astype(int)
    out["unrealized_return"] = pd.to_numeric(out["unrealized_return"], errors="coerce").fillna(0.0)
    return out.drop_duplicates(["target_date", "code"], keep="first")


def normalize_position_signal_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["target_date", "code", "position_signal", "replacement_confirmation_days"])
    required = {"target_date", "code"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise Phase7AInputError(f"position signal frame missing columns: {missing}")
    out = frame.copy()
    out["code"] = out["code"].astype(str)
    out["target_date"] = out["target_date"].astype(str)
    if "position_signal" not in out.columns:
        out["position_signal"] = ""
    if "replacement_confirmation_days" not in out.columns:
        out["replacement_confirmation_days"] = 0
    out["replacement_confirmation_days"] = pd.to_numeric(out["replacement_confirmation_days"], errors="coerce").fillna(0).astype(int)
    return out.drop_duplicates(["target_date", "code"], keep="first")


def first_unheld_top3(top3: pd.DataFrame, holding_codes: set[str]) -> Any | None:
    for row in top3.itertuples(index=False):
        if str(row.code) not in holding_codes:
            return row
    return None


def build_runtime_audit(decision_frame: pd.DataFrame, *, config: Phase7AConfig, created_at: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "created_at": created_at,
        "readiness_status": READY_FOR_PHASE7A_VALIDATION,
        "decision_count": int(len(decision_frame)),
        "buy_count": int((decision_frame["action"] == "BUY").sum()) if not decision_frame.empty else 0,
        "hold_count": int((decision_frame["action"] == "HOLD").sum()) if not decision_frame.empty else 0,
        "replace_sell_count": int((decision_frame["action"] == "REPLACE_SELL").sum()) if not decision_frame.empty else 0,
        "replace_buy_count": int((decision_frame["action"] == "REPLACE_BUY").sum()) if not decision_frame.empty else 0,
        "emergency_exit_count": int((decision_frame["action"] == "EMERGENCY_EXIT").sum()) if not decision_frame.empty else 0,
        "defensive_review_count": int((decision_frame["action"] == "DEFENSIVE_REVIEW").sum()) if not decision_frame.empty else 0,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "fixed_take_profit_enabled": False,
        "phase6_single_exit_auto_sell_enabled": False,
        "simple_top3_drop_replacement_enabled": False,
        "kelly_criterion_enabled": False,
        "leverage_enabled": False,
        "margin_trading_enabled": False,
        "loss_averaging_enabled": False,
        "emergency_exit_enabled": True,
        "replacement_requires_minimum_holding_days": config.minimum_holding_days > 0,
        "replacement_requires_edge_margin": config.replacement_edge_margin > 0,
        "replacement_requires_confirmation_days": config.confirmation_days > 1,
        "replacement_same_time_live_execution_enabled": False,
        "replacement_requires_sell_fill_before_buy": True,
        "cash_buffer_applied": config.cash_buffer_ratio > 0,
        "max_position_weight_applied": config.max_position_weight > 0,
        "config": asdict(config),
    }


def build_summary(
    decision_frame: pd.DataFrame,
    *,
    audit: dict[str, Any],
    output_dir: Path,
    config: Phase7AConfig,
    created_at: str,
) -> dict[str, Any]:
    max_buy = float(decision_frame["buy_amount"].max()) if not decision_frame.empty else 0.0
    max_sell_over_position = bool((decision_frame["sell_amount"] > decision_frame["current_position_value"]).any()) if not decision_frame.empty else False
    return {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": READY_FOR_PHASE7A_VALIDATION,
        "created_at": created_at,
        "model_version": MODEL_VERSION,
        "output_dir": str(output_dir),
        "decision_count": int(len(decision_frame)),
        "action_counts": decision_frame["action"].value_counts().to_dict() if not decision_frame.empty else {},
        "max_buy_amount": round_float(max_buy),
        "sell_amount_exceeds_current_position_value": max_sell_over_position,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "fixed_take_profit_enabled": False,
        "phase6_single_exit_auto_sell_enabled": False,
        "simple_top3_drop_replacement_enabled": False,
        "capital_allocation_policy_executed": True,
        "capital_allocation_order_executed": False,
        "config": asdict(config),
        "audit": audit,
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    return value
