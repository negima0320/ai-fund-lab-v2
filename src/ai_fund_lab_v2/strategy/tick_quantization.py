from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.strategy.minimum_tick_authority import STATUS_KNOWN


TICK_NORMALIZED_SCHEMA_VERSION = "tick_normalized_trend_momentum.v1"
TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY = "TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY"
QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY = "QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY"

TREND_ROBUST = "ROBUST"
TREND_ACCEPTABLE = "ACCEPTABLE"
TREND_QUANTIZED_CAUTION = "QUANTIZED_CAUTION"
TREND_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

MOMENTUM_HIGH = "HIGH_CONFIDENCE"
MOMENTUM_MODERATE = "MODERATE_CONFIDENCE"
MOMENTUM_LOW_QUANTIZED = "LOW_CONFIDENCE_QUANTIZED"
MOMENTUM_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

RANK_RELIABLE = "RELIABLE"
RANK_QUALIFIED = "QUALIFIED"
RANK_LOW_CONFIDENCE = "LOW_CONFIDENCE"
RANK_INSUFFICIENT = "INSUFFICIENT"


def build_tick_normalized_evidence(
    *,
    close_values: Iterable[Any],
    minimum_tick_authority_status: str,
    minimum_tick: Any,
    single_tick_pct: Any,
    business_date: str,
    symbol: str,
    minimum_tick_authority_hash: str = "",
) -> dict[str, Any]:
    closes = [_finite_float(value) for value in close_values]
    closes = [value for value in closes if value is not None and value > 0.0]
    tick = _finite_float(minimum_tick)
    tick_pct = _finite_float(single_tick_pct)
    reason_codes: list[str] = []
    if str(minimum_tick_authority_status or "").upper() != STATUS_KNOWN or tick is None or tick <= 0 or tick_pct is None or tick_pct <= 0:
        reason_codes.append("tick_normalized_minimum_tick_authority_insufficient")
        return _insufficient_payload(
            business_date=business_date,
            symbol=symbol,
            reason_codes=reason_codes,
            minimum_tick_authority_status=str(minimum_tick_authority_status or ""),
            minimum_tick_authority_hash=minimum_tick_authority_hash,
        )
    if len(closes) < 21:
        reason_codes.append("tick_normalized_price_history_insufficient")
        return _insufficient_payload(
            business_date=business_date,
            symbol=symbol,
            reason_codes=reason_codes,
            minimum_tick_authority_status=str(minimum_tick_authority_status or ""),
            minimum_tick_authority_hash=minimum_tick_authority_hash,
        )

    latest = closes[-1]
    ma5 = _mean(closes[-5:])
    ma20 = _mean(closes[-20:])
    ma60 = _mean(closes[-60:]) if len(closes) >= 60 else None
    close_levels = {
        "5d": _close_level_count(closes, 5, tick),
        "10d": _close_level_count(closes, 10, tick),
        "20d": _close_level_count(closes, 20, tick),
        "60d": _close_level_count(closes, 60, tick),
    }
    ticks_traversed = {
        "5d": _ticks_traversed(closes, 5, tick),
        "20d": _ticks_traversed(closes, 20, tick),
        "60d": _ticks_traversed(closes, 60, tick),
    }
    net_tick_move = {
        "5d": _net_tick_move(closes, 5, tick),
        "20d": _net_tick_move(closes, 20, tick),
        "60d": _net_tick_move(closes, 60, tick),
    }
    directional = {
        "5d": _directional_tick_persistence(closes, 5, tick),
        "20d": _directional_tick_persistence(closes, 20, tick),
        "60d": _directional_tick_persistence(closes, 60, tick),
    }
    close_over_ma20_pct = _ratio_or_none(latest, ma20)
    ma5_over_ma20_pct = _ratio_or_none(ma5, ma20)
    ma20_over_ma60_pct = _ratio_or_none(ma20, ma60)
    ma_separation_ticks = {
        "close_over_ma20": _tick_gap(latest, ma20, tick),
        "ma5_over_ma20": _tick_gap(ma5, ma20, tick),
        "ma20_over_ma60": _tick_gap(ma20, ma60, tick),
    }
    ma_separation_vs_single_tick_pct = {
        "close_over_ma20": _pct_gap_vs_tick(close_over_ma20_pct, tick_pct),
        "ma5_over_ma20": _pct_gap_vs_tick(ma5_over_ma20_pct, tick_pct),
        "ma20_over_ma60": _pct_gap_vs_tick(ma20_over_ma60_pct, tick_pct),
    }
    return_vs_tick_resolution = {
        "5d": _return_vs_tick(closes, 5, tick_pct),
        "20d": _return_vs_tick(closes, 20, tick_pct),
        "60d": _return_vs_tick(closes, 60, tick_pct),
    }
    diversity_state = _close_level_diversity_state(close_levels["20d"])
    volatility_state = _quantized_volatility_state(
        single_tick_pct=tick_pct,
        close_level_count_20d=close_levels["20d"],
        ticks_traversed_20d=ticks_traversed["20d"],
    )
    trend_state = _trend_state(
        single_tick_pct=tick_pct,
        close_level_count_20d=close_levels["20d"],
        ticks_traversed_20d=ticks_traversed["20d"],
        close_over_ma20_ticks=ma_separation_ticks["close_over_ma20"],
        ma5_over_ma20_ticks=ma_separation_ticks["ma5_over_ma20"],
        ma20_over_ma60_ticks=ma_separation_ticks["ma20_over_ma60"],
    )
    momentum_state = _momentum_state(
        trend_state=trend_state,
        single_tick_pct=tick_pct,
        close_level_count_20d=close_levels["20d"],
        net_tick_move_20d=net_tick_move["20d"],
        directional_persistence_20d=directional["20d"],
    )
    rank_reliability = _rank_reliability(trend_state=trend_state, momentum_state=momentum_state)
    if trend_state == TREND_QUANTIZED_CAUTION:
        reason_codes.append("tick_normalized_trend_quantized_caution")
    elif trend_state == TREND_ROBUST:
        reason_codes.append("tick_normalized_trend_robust")
    else:
        reason_codes.append("tick_normalized_trend_acceptable")
    if momentum_state == MOMENTUM_LOW_QUANTIZED:
        reason_codes.append("quantization_aware_momentum_low_confidence")
    elif momentum_state == MOMENTUM_HIGH:
        reason_codes.append("quantization_aware_momentum_high_confidence")
    else:
        reason_codes.append("quantization_aware_momentum_moderate_confidence")
    if tick_pct >= 0.02 and trend_state in {TREND_ROBUST, TREND_ACCEPTABLE}:
        reason_codes.append("low_price_but_tick_persistent_trend")

    return {
        "schema_version": TICK_NORMALIZED_SCHEMA_VERSION,
        "business_date": business_date,
        "symbol": symbol,
        "minimum_tick_authority_status": str(minimum_tick_authority_status or ""),
        "minimum_tick_authority_hash": minimum_tick_authority_hash,
        "minimum_tick": round(tick, 10),
        "single_tick_pct": round(tick_pct, 10),
        "tick_quantization_status": "PASS",
        "tick_normalized_trend_state": trend_state,
        "momentum_confidence_state": momentum_state,
        "close_level_diversity_state": diversity_state,
        "candidate_rank_tick_reliability": rank_reliability,
        "close_level_count_5d": close_levels["5d"],
        "close_level_count_10d": close_levels["10d"],
        "close_level_count_20d": close_levels["20d"],
        "close_level_count_60d": close_levels["60d"],
        "ticks_traversed_5d": ticks_traversed["5d"],
        "ticks_traversed_20d": ticks_traversed["20d"],
        "ticks_traversed_60d": ticks_traversed["60d"],
        "net_tick_move_5d": net_tick_move["5d"],
        "net_tick_move_20d": net_tick_move["20d"],
        "net_tick_move_60d": net_tick_move["60d"],
        "directional_tick_persistence_5d": directional["5d"],
        "directional_tick_persistence_20d": directional["20d"],
        "directional_tick_persistence_60d": directional["60d"],
        "ma_separation_ticks_close_over_ma20": ma_separation_ticks["close_over_ma20"],
        "ma_separation_ticks_ma5_over_ma20": ma_separation_ticks["ma5_over_ma20"],
        "ma_separation_ticks_ma20_over_ma60": ma_separation_ticks["ma20_over_ma60"],
        "ma_separation_vs_single_tick_pct_close_over_ma20": ma_separation_vs_single_tick_pct["close_over_ma20"],
        "ma_separation_vs_single_tick_pct_ma5_over_ma20": ma_separation_vs_single_tick_pct["ma5_over_ma20"],
        "ma_separation_vs_single_tick_pct_ma20_over_ma60": ma_separation_vs_single_tick_pct["ma20_over_ma60"],
        "return_vs_tick_resolution_5d": return_vs_tick_resolution["5d"],
        "return_vs_tick_resolution_20d": return_vs_tick_resolution["20d"],
        "return_vs_tick_resolution_60d": return_vs_tick_resolution["60d"],
        "quantized_volatility_context": volatility_state,
        "trend_robustness_authority": {
            "authority_type": TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY,
            "state": trend_state,
            "business_date": business_date,
            "symbol": symbol,
            "minimum_tick_authority_hash": minimum_tick_authority_hash,
            "PIT_status": "PASS",
        },
        "momentum_confidence_authority": {
            "authority_type": QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY,
            "state": momentum_state,
            "business_date": business_date,
            "symbol": symbol,
            "minimum_tick_authority_hash": minimum_tick_authority_hash,
            "PIT_status": "PASS",
        },
        "reason_codes": sorted(set(reason_codes)),
        "future_information_used": False,
        "historical_result_input_used": False,
        "hard_min_price_filter_used": False,
        "low_price_blacklist_used": False,
    }


def tick_evidence_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    trend_state = str(row.get("tick_normalized_trend_state") or "").upper()
    momentum_state = str(row.get("momentum_confidence_state") or "").upper()
    status = str(row.get("tick_quantization_status") or "").upper()
    reliability = str(row.get("candidate_rank_tick_reliability") or "").upper()
    reason_codes = [str(reason) for reason in row.get("tick_quantization_reason_codes") or row.get("reason_codes") or []]
    if not trend_state and not momentum_state and status != "PASS":
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "trend_state": TREND_INSUFFICIENT,
            "momentum_state": MOMENTUM_INSUFFICIENT,
            "rank_reliability": RANK_INSUFFICIENT,
            "reason_codes": ["tick_normalized_evidence_missing"],
        }
    if trend_state == TREND_INSUFFICIENT or momentum_state == MOMENTUM_INSUFFICIENT or status in {"INSUFFICIENT_EVIDENCE", "REVIEW_REQUIRED"}:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "trend_state": trend_state or TREND_INSUFFICIENT,
            "momentum_state": momentum_state or MOMENTUM_INSUFFICIENT,
            "rank_reliability": reliability or RANK_INSUFFICIENT,
            "reason_codes": reason_codes or ["tick_normalized_evidence_insufficient"],
        }
    return {
        "status": "PASS",
        "trend_state": trend_state,
        "momentum_state": momentum_state,
        "rank_reliability": reliability or _rank_reliability(trend_state=trend_state, momentum_state=momentum_state),
        "reason_codes": reason_codes,
    }


def _insufficient_payload(
    *,
    business_date: str,
    symbol: str,
    reason_codes: list[str],
    minimum_tick_authority_status: str,
    minimum_tick_authority_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": TICK_NORMALIZED_SCHEMA_VERSION,
        "business_date": business_date,
        "symbol": symbol,
        "minimum_tick_authority_status": minimum_tick_authority_status,
        "minimum_tick_authority_hash": minimum_tick_authority_hash,
        "tick_quantization_status": "INSUFFICIENT_EVIDENCE",
        "tick_normalized_trend_state": TREND_INSUFFICIENT,
        "momentum_confidence_state": MOMENTUM_INSUFFICIENT,
        "close_level_diversity_state": "INSUFFICIENT_EVIDENCE",
        "candidate_rank_tick_reliability": RANK_INSUFFICIENT,
        "trend_robustness_authority": {
            "authority_type": TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY,
            "state": TREND_INSUFFICIENT,
            "business_date": business_date,
            "symbol": symbol,
            "minimum_tick_authority_hash": minimum_tick_authority_hash,
            "PIT_status": "REVIEW_REQUIRED",
        },
        "momentum_confidence_authority": {
            "authority_type": QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY,
            "state": MOMENTUM_INSUFFICIENT,
            "business_date": business_date,
            "symbol": symbol,
            "minimum_tick_authority_hash": minimum_tick_authority_hash,
            "PIT_status": "REVIEW_REQUIRED",
        },
        "reason_codes": sorted(set(reason_codes)),
        "future_information_used": False,
        "historical_result_input_used": False,
        "hard_min_price_filter_used": False,
        "low_price_blacklist_used": False,
    }


def _trend_state(
    *,
    single_tick_pct: float,
    close_level_count_20d: int | None,
    ticks_traversed_20d: float | None,
    close_over_ma20_ticks: float | None,
    ma5_over_ma20_ticks: float | None,
    ma20_over_ma60_ticks: float | None,
) -> str:
    if close_level_count_20d is None or ticks_traversed_20d is None:
        return TREND_INSUFFICIENT
    tick_dominated = single_tick_pct >= 0.02
    low_diversity = close_level_count_20d <= 3 or ticks_traversed_20d <= 2.0
    weak_ma_tick_support = (
        close_over_ma20_ticks is not None
        and ma5_over_ma20_ticks is not None
        and abs(close_over_ma20_ticks) <= 1.0
        and abs(ma5_over_ma20_ticks) <= 1.0
    )
    if tick_dominated and (low_diversity or weak_ma_tick_support):
        return TREND_QUANTIZED_CAUTION
    if single_tick_pct <= 0.01 and close_level_count_20d >= 8 and ticks_traversed_20d >= 5.0:
        if close_over_ma20_ticks is None or ma5_over_ma20_ticks is None:
            return TREND_ACCEPTABLE
        if close_over_ma20_ticks >= 2.0 and ma5_over_ma20_ticks >= 1.0:
            return TREND_ROBUST
    if ma20_over_ma60_ticks is not None and ma20_over_ma60_ticks < -2.0:
        return TREND_QUANTIZED_CAUTION if tick_dominated else TREND_ACCEPTABLE
    return TREND_ACCEPTABLE


def _momentum_state(
    *,
    trend_state: str,
    single_tick_pct: float,
    close_level_count_20d: int | None,
    net_tick_move_20d: float | None,
    directional_persistence_20d: float | None,
) -> str:
    if trend_state == TREND_INSUFFICIENT or close_level_count_20d is None:
        return MOMENTUM_INSUFFICIENT
    if trend_state == TREND_QUANTIZED_CAUTION:
        return MOMENTUM_LOW_QUANTIZED
    if (
        single_tick_pct <= 0.01
        and close_level_count_20d >= 8
        and net_tick_move_20d is not None
        and net_tick_move_20d >= 5.0
        and directional_persistence_20d is not None
        and directional_persistence_20d >= 0.55
    ):
        return MOMENTUM_HIGH
    return MOMENTUM_MODERATE


def _rank_reliability(*, trend_state: str, momentum_state: str) -> str:
    if trend_state == TREND_INSUFFICIENT or momentum_state == MOMENTUM_INSUFFICIENT:
        return RANK_INSUFFICIENT
    if trend_state == TREND_QUANTIZED_CAUTION or momentum_state == MOMENTUM_LOW_QUANTIZED:
        return RANK_LOW_CONFIDENCE
    if trend_state == TREND_ROBUST and momentum_state == MOMENTUM_HIGH:
        return RANK_RELIABLE
    return RANK_QUALIFIED


def _close_level_diversity_state(count: int | None) -> str:
    if count is None:
        return "INSUFFICIENT_EVIDENCE"
    if count <= 3:
        return "LOW_DIVERSITY"
    if count >= 8:
        return "ADEQUATE_DIVERSITY"
    return "MODERATE_DIVERSITY"


def _quantized_volatility_state(*, single_tick_pct: float, close_level_count_20d: int | None, ticks_traversed_20d: float | None) -> str:
    if close_level_count_20d is None or ticks_traversed_20d is None:
        return "INSUFFICIENT_EVIDENCE"
    if single_tick_pct >= 0.02 and (close_level_count_20d <= 3 or ticks_traversed_20d <= 2.0):
        return "TICK_DOMINATED_LOW_DIVERSITY"
    if single_tick_pct >= 0.02:
        return "LARGE_TICK_CONTEXT"
    return "CONTINUOUS_ENOUGH"


def _finite_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _close_level_count(values: list[float], window: int, tick: float) -> int | None:
    if len(values) < min(window, len(values)):
        return None
    sample = values[-window:]
    if not sample:
        return None
    return len({round(value / tick) for value in sample})


def _ticks_traversed(values: list[float], window: int, tick: float) -> float | None:
    sample = values[-window:] if len(values) >= window else values
    if not sample:
        return None
    return round((max(sample) - min(sample)) / tick, 6)


def _net_tick_move(values: list[float], periods: int, tick: float) -> float | None:
    if len(values) <= periods:
        return None
    return round((values[-1] - values[-1 - periods]) / tick, 6)


def _directional_tick_persistence(values: list[float], periods: int, tick: float) -> float | None:
    if len(values) <= periods:
        return None
    moves = []
    for prev, curr in zip(values[-periods - 1 : -1], values[-periods:]):
        tick_move = round((curr - prev) / tick)
        if tick_move:
            moves.append(1 if tick_move > 0 else -1)
    if not moves:
        return 0.0
    positive = sum(1 for move in moves if move > 0)
    negative = sum(1 for move in moves if move < 0)
    return round(max(positive, negative) / len(moves), 6)


def _ratio_or_none(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _tick_gap(numerator: float | None, denominator: float | None, tick: float) -> float | None:
    if numerator is None or denominator is None:
        return None
    return round((numerator - denominator) / tick, 6)


def _pct_gap_vs_tick(ratio: float | None, single_tick_pct: float) -> float | None:
    if ratio is None or single_tick_pct <= 0:
        return None
    return round((ratio - 1.0) / single_tick_pct, 6)


def _return_vs_tick(values: list[float], periods: int, single_tick_pct: float) -> float | None:
    if len(values) <= periods or single_tick_pct <= 0:
        return None
    base = values[-1 - periods]
    if base <= 0:
        return None
    return round(((values[-1] / base) - 1.0) / single_tick_pct, 6)
