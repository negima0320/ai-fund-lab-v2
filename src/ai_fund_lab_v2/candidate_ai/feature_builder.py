from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, median, pstdev
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.candidate_ai.leakage_audit import audit_feature_table
from ai_fund_lab_v2.candidate_ai.schemas import CandidateFeatureAudit
from ai_fund_lab_v2.candidate_ai.validation import FeatureTableValidationResult, validate_feature_table


DEFAULT_FEATURE_VERSION = "candidate_features_mock_v1"
DEFAULT_SOURCE_SNAPSHOT_ID = "mock_daily_quotes_normalized"
DEFAULT_FEATURE_SET_NAME = "candidate_feature_builder_mock"
MIN_LOOKBACK_ROWS = 21


@dataclass(frozen=True)
class CandidateFeatureBuildResult:
    rows: list[dict[str, Any]]
    validation: FeatureTableValidationResult
    audit: CandidateFeatureAudit


def build_candidate_features_mock(
    daily_quotes_normalized: Iterable[Mapping[str, Any]],
    *,
    as_of_date: str,
    target_date: str | None = None,
    feature_version: str = DEFAULT_FEATURE_VERSION,
    source_snapshot_id: str = DEFAULT_SOURCE_SNAPSHOT_ID,
) -> list[dict[str, Any]]:
    target = target_date or as_of_date
    grouped_rows = _group_visible_rows(daily_quotes_normalized, as_of_date=as_of_date)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    feature_rows = [
        _build_row(
            code=code,
            visible_rows=rows,
            as_of_date=as_of_date,
            target_date=target,
            feature_version=feature_version,
            source_snapshot_id=source_snapshot_id,
            created_at=created_at,
        )
        for code, rows in sorted(grouped_rows.items())
    ]
    return feature_rows


def build_candidate_features_mock_with_audit(
    daily_quotes_normalized: Iterable[Mapping[str, Any]],
    *,
    as_of_date: str,
    target_date: str | None = None,
    feature_version: str = DEFAULT_FEATURE_VERSION,
    source_snapshot_id: str = DEFAULT_SOURCE_SNAPSHOT_ID,
) -> CandidateFeatureBuildResult:
    rows = build_candidate_features_mock(
        daily_quotes_normalized,
        as_of_date=as_of_date,
        target_date=target_date,
        feature_version=feature_version,
        source_snapshot_id=source_snapshot_id,
    )
    validation = validate_feature_table(rows)
    audit = audit_feature_table(rows)
    return CandidateFeatureBuildResult(rows=rows, validation=validation, audit=audit)


def _group_visible_rows(
    daily_quotes_normalized: Iterable[Mapping[str, Any]],
    *,
    as_of_date: str,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in daily_quotes_normalized:
        row_date = str(row.get("date", ""))
        code = str(row.get("code", "")).strip()
        if not row_date or not code or row_date > as_of_date:
            continue
        grouped[code].append(dict(row))
    for rows in grouped.values():
        rows.sort(key=lambda item: str(item["date"]))
    return dict(grouped)


def _build_row(
    *,
    code: str,
    visible_rows: list[dict[str, Any]],
    as_of_date: str,
    target_date: str,
    feature_version: str,
    source_snapshot_id: str,
    created_at: str,
) -> dict[str, Any]:
    eligible = len(visible_rows) >= MIN_LOOKBACK_ROWS
    data_start_date = str(visible_rows[0]["date"]) if visible_rows else None
    data_end_date = str(visible_rows[-1]["date"]) if visible_rows else None
    base_row: dict[str, Any] = {
        "as_of_date": as_of_date,
        "target_date": target_date,
        "code": code,
        "feature_version": feature_version,
        "source_snapshot_id": source_snapshot_id,
        "feature_set_name": DEFAULT_FEATURE_SET_NAME,
        "created_at": created_at,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        "universe_eligible": eligible,
        "excluded_reason": "" if eligible else "insufficient_lookback",
        "missing_flags_insufficient_lookback": not eligible,
    }
    if not eligible:
        base_row.update(_empty_feature_values())
        return base_row

    closes = [_to_float(row["close"]) for row in visible_rows]
    volumes = [_to_float(row["volume"]) for row in visible_rows]
    traded_values = [_optional_float(_traded_value(row)) for row in visible_rows]
    returns_20d = [_safe_ratio(closes[index], closes[index - 1]) for index in range(len(closes) - 20, len(closes))]
    rolling_median_traded_value_20 = None
    if all(value is not None for value in traded_values[-20:]):
        rolling_median_traded_value_20 = _round(median([float(value) for value in traded_values[-20:]]))
    base_row.update(
        {
            "price_momentum_return_5d": _round(_safe_ratio(closes[-1], closes[-6])),
            "price_momentum_return_20d": _round(_safe_ratio(closes[-1], closes[-21])),
            "volume_momentum_ratio_5d": _round(_safe_divide(mean(volumes[-5:]), mean(volumes[-20:]))),
            "volatility_return_std_20d": _round(pstdev(returns_20d)),
            "trend_close_over_ma_20d": _round(_safe_ratio(closes[-1], mean(closes[-20:]))),
            "liquidity_avg_volume_20d": _round(mean(volumes[-20:])),
            "rolling_median_traded_value_20": rolling_median_traded_value_20,
        }
    )
    return base_row


def _empty_feature_values() -> dict[str, Any]:
    return {
        "price_momentum_return_5d": None,
        "price_momentum_return_20d": None,
        "volume_momentum_ratio_5d": None,
        "volatility_return_std_20d": None,
        "trend_close_over_ma_20d": None,
        "liquidity_avg_volume_20d": None,
        "rolling_median_traded_value_20": None,
    }


def _to_float(value: Any) -> float:
    return float(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _traded_value(row: Mapping[str, Any]) -> Any:
    for key in ("traded_value", "value_traded", "turnover_value", "Va", "TradingValue", "turnover"):
        if row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _safe_ratio(current: float, previous: float) -> float:
    return _safe_divide(current, previous) - 1.0


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _round(value: float) -> float:
    return round(value, 6)
