from __future__ import annotations

import math
from typing import Any

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.schema import Phase7AConfig

BAD_RISK_GUARD_STATUSES = {"bad", "ng", "blocked", "risk_bad", "high_risk"}
DEFENSIVE_SIGNALS = {"EXIT", "REDUCE"}
HOLD_SUPPORT_SIGNALS = {"HOLD", "ADD"}


def calculate_cash_buffer(total_assets: float, config: Phase7AConfig) -> float:
    return round_float(max(total_assets, 0.0) * config.cash_buffer_ratio)


def calculate_available_cash(cash: float, total_assets: float, config: Phase7AConfig) -> float:
    return round_float(max(cash - calculate_cash_buffer(total_assets, config), 0.0))


def calculate_target_position_value(total_assets: float, config: Phase7AConfig) -> float:
    cap = max(total_assets, 0.0) * config.max_position_weight
    if config.max_position_value is not None:
        cap = min(cap, config.max_position_value)
    return round_float(max(cap, 0.0))


def calculate_weight(position_value: float, total_assets: float) -> float:
    return round_float(position_value / total_assets) if total_assets else 0.0


def calculate_buy_amount(*, target_position_value: float, current_position_value: float, available_cash: float, config: Phase7AConfig) -> float:
    desired = max(target_position_value - current_position_value, 0.0)
    amount = min(desired, max(available_cash, 0.0))
    if amount < config.min_position_value:
        return 0.0
    return round_float(amount)


def is_primary_buy_candidate(opportunity: pd.Series, config: Phase7AConfig) -> bool:
    return int_or_none(opportunity.get("buy_rank")) is not None and int(opportunity["buy_rank"]) <= config.primary_buy_rank_cutoff


def is_watch_candidate(opportunity: pd.Series, config: Phase7AConfig) -> bool:
    rank = int_or_none(opportunity.get("buy_rank"))
    return rank is not None and config.primary_buy_rank_cutoff < rank <= config.watch_rank_cutoff


def is_risk_guard_bad(status: Any) -> bool:
    return str(status or "").strip().lower() in BAD_RISK_GUARD_STATUSES


def is_defensive_signal(position_signal: Any) -> bool:
    return str(position_signal or "").strip().upper() in DEFENSIVE_SIGNALS


def has_strong_hold_support(*, position_signal: str, risk_guard_status: str, downside_risk_score: float, opportunity_rank: int | None) -> bool:
    signal = str(position_signal or "").strip().upper()
    if signal not in HOLD_SUPPORT_SIGNALS:
        return False
    if is_risk_guard_bad(risk_guard_status):
        return False
    if downside_risk_score >= 0.35:
        return False
    return opportunity_rank is not None and opportunity_rank <= 10


def should_emergency_exit(unrealized_return: float, config: Phase7AConfig) -> bool:
    return unrealized_return <= config.emergency_exit_pct


def should_defensive_review(position_signal: str, risk_guard_status: str, downside_risk_score: float, config: Phase7AConfig) -> tuple[bool, str]:
    reasons: list[str] = []
    if is_defensive_signal(position_signal):
        reasons.append(f"phase6_{str(position_signal).strip().upper()}_signal")
    if is_risk_guard_bad(risk_guard_status):
        reasons.append("risk_guard_status_bad")
    if downside_risk_score >= config.high_downside_risk_threshold:
        reasons.append("downside_risk_score_high")
    return bool(reasons), "|".join(reasons)


def should_replace(
    *,
    holding_days: int,
    opportunity_rank: int | None,
    holding_expected_edge_score: float,
    replacement_candidate_expected_edge_score: float,
    replacement_confirmation_days: int,
    position_signal: str,
    risk_guard_status: str,
    downside_risk_score: float,
    config: Phase7AConfig,
) -> tuple[bool, str]:
    reasons: list[str] = []
    if holding_days < config.minimum_holding_days:
        return False, "blocked_by_minimum_holding_days"
    reasons.append("minimum_holding_days_met")

    degraded = opportunity_rank is None or opportunity_rank > config.replacement_rank_degradation_threshold
    if not degraded:
        return False, "rank_degradation_not_met"
    reasons.append("rank_degradation_met")

    edge_gap = replacement_candidate_expected_edge_score - holding_expected_edge_score
    if edge_gap < config.replacement_edge_margin:
        return False, "edge_margin_not_met"
    reasons.append("edge_margin_met")

    if replacement_confirmation_days < config.confirmation_days:
        return False, "confirmation_days_not_met"
    reasons.append("confirmation_days_met")

    if has_strong_hold_support(
        position_signal=position_signal,
        risk_guard_status=risk_guard_status,
        downside_risk_score=downside_risk_score,
        opportunity_rank=opportunity_rank,
    ):
        return False, "blocked_by_strong_hold_support"
    reasons.append("no_strong_hold_support")
    return True, "|".join(reasons)


def int_or_none(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_default(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(numeric) or math.isinf(numeric):
        return default
    return numeric


def round_float(value: Any, digits: int = 8) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)
