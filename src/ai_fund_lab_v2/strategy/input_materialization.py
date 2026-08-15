from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


PRICE_VOLATILITY_SCHEMA_VERSION = "strategy_price_volatility_materialization.v1"
TECHNICAL_FEATURE_SCHEMA_VERSION = "strategy_pm_technical_feature_materialization.v1"
PRODUCER_VERSION = "phase22_qe_strategy_input_materializer.v1"
REFERENCE_PRICE_AUTHORITY = "REFERENCE_PRICE_AUTHORITY"
REFERENCE_PRICE_FIELD = "reference_price"
REFERENCE_PRICE_TYPE = "planning_reference_close"
LIQUIDITY_CAPACITY_AUTHORITY = "LIQUIDITY_CAPACITY_AUTHORITY"
ROLLING_MEDIAN_TRADED_VALUE_FIELD = "rolling_median_traded_value_20"
ROLLING_TRADED_VALUE_LOOKBACK_BUSINESS_DAYS = 20
PRICE_LOOKBACK_BUSINESS_DAYS = 20
MINIMUM_PRICE_OBSERVATIONS = 21
PM_TECHNICAL_REQUIRED_COLUMNS = (
    "price_momentum_return_1d",
    "price_momentum_return_3d",
    "price_momentum_return_5d",
    "price_momentum_return_10d",
    "price_momentum_return_20d",
    "recent_move_volatility_z_1d",
    "recent_move_volatility_z_3d",
    "momentum_5d_vs_20d_delta",
    "momentum_1d_vs_5d_delta",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
)


@dataclass(frozen=True)
class StrategyInputMaterializationResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]


def produce_price_volatility_artifact(
    *,
    business_date: str,
    feature_date: str,
    source_path: Path | str,
    output_path: Path | str,
    symbols: Iterable[str] = (),
    as_of: str | None = None,
) -> StrategyInputMaterializationResult:
    payload = _build_materialized_payload(
        schema_version=PRICE_VOLATILITY_SCHEMA_VERSION,
        business_date=business_date,
        feature_date=feature_date,
        source_path=Path(source_path),
        symbols=tuple(symbols),
        as_of=as_of,
        include_pm_features=False,
    )
    return _write_result(output_path, payload)


def produce_pm_technical_feature_artifact(
    *,
    business_date: str,
    feature_date: str,
    source_path: Path | str,
    output_path: Path | str,
    symbols: Iterable[str] = (),
    as_of: str | None = None,
) -> StrategyInputMaterializationResult:
    payload = _build_materialized_payload(
        schema_version=TECHNICAL_FEATURE_SCHEMA_VERSION,
        business_date=business_date,
        feature_date=feature_date,
        source_path=Path(source_path),
        symbols=tuple(symbols),
        as_of=as_of,
        include_pm_features=True,
    )
    return _write_result(output_path, payload)


def _build_materialized_payload(
    *,
    schema_version: str,
    business_date: str,
    feature_date: str,
    source_path: Path,
    symbols: tuple[str, ...],
    as_of: str | None,
    include_pm_features: bool,
) -> dict[str, Any]:
    as_of = as_of or datetime.now(timezone.utc).isoformat()
    source_hash = _file_hash(source_path)
    status = "PASS"
    validation_status = "PASS"
    decision_resolution = "RESOLVED"
    coverage_status = "FULL"
    reason_codes: list[str] = []
    rows: list[dict[str, Any]] = []
    source_columns: list[str] = []
    future_row_rejection_count = 0
    selected_source_row_count = 0
    requested_symbols = sorted({str(symbol) for symbol in symbols if str(symbol)})
    if feature_date > business_date:
        status = "BLOCK"
        validation_status = "BLOCK"
        decision_resolution = "UNRESOLVED"
        reason_codes.append("PIT_INVALID")
    if not source_path.is_file():
        status = "REVIEW_REQUIRED"
        validation_status = "REVIEW_REQUIRED"
        decision_resolution = "UNRESOLVED"
        coverage_status = "SOURCE_NOT_AVAILABLE"
        reason_codes.append("SOURCE_NOT_AVAILABLE")
    else:
        try:
            frame = pd.read_parquet(source_path)
            source_columns = [str(column) for column in frame.columns]
            normalized = _normalize_price_frame(frame)
            if normalized.empty:
                status = "REVIEW_REQUIRED"
                validation_status = "REVIEW_REQUIRED"
                decision_resolution = "UNRESOLVED"
                coverage_status = "SOURCE_NOT_AVAILABLE"
                reason_codes.append("SOURCE_NOT_AVAILABLE")
            else:
                future_row_rejection_count = int((normalized["target_date"] > feature_date).sum())
                pit_frame = normalized[normalized["target_date"] <= feature_date].copy()
                selected_source_row_count = int(len(pit_frame))
                rows = _calculation_rows(
                    pit_frame,
                    feature_date=feature_date,
                    requested_symbols=requested_symbols,
                    include_pm_features=include_pm_features,
                    source_path=source_path,
                    source_hash=source_hash,
                )
                missing_rows = [row for row in rows if row["coverage_status"] != "AVAILABLE"]
                if not rows:
                    status = "REVIEW_REQUIRED"
                    validation_status = "REVIEW_REQUIRED"
                    decision_resolution = "UNRESOLVED"
                    coverage_status = "SOURCE_NOT_AVAILABLE"
                    reason_codes.append("SOURCE_NOT_AVAILABLE")
                elif missing_rows:
                    status = "REVIEW_REQUIRED"
                    validation_status = "REVIEW_REQUIRED"
                    decision_resolution = "UNRESOLVED"
                    coverage_status = "PARTIAL_SYMBOL_COVERAGE"
                    reason_codes.append("PARTIAL_SYMBOL_COVERAGE")
                    if any(row["coverage_status"] == "INSUFFICIENT_OBSERVATIONS" for row in missing_rows):
                        reason_codes.append("INSUFFICIENT_OBSERVATIONS")
        except Exception as exc:
            status = "REVIEW_REQUIRED"
            validation_status = "REVIEW_REQUIRED"
            decision_resolution = "UNRESOLVED"
            coverage_status = "CALCULATION_ERROR"
            reason_codes.append("CALCULATION_ERROR")
            rows = []
            source_columns = source_columns or []
            calculation_error = f"{type(exc).__name__}:{exc}"
    payload = {
        "schema_version": schema_version,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "feature_date": feature_date,
        "as_of": as_of,
        "lookback_window": {"business_days": PRICE_LOOKBACK_BUSINESS_DAYS},
        "minimum_observations": MINIMUM_PRICE_OBSERVATIONS,
        "price_basis": "adjusted_close_preferred_else_close",
        "corporate_action_adjustment": "uses adjusted close column when present; otherwise source close is treated as provider-normalized",
        "missing_trading_day_policy": "use observed PIT rows only; no forward fill or zero fill",
        "coverage_threshold": "all requested symbols require sufficient PIT observations; partial coverage is REVIEW_REQUIRED",
        "calculation_formula": {
            "daily_return": "close_t / close_t_minus_1 - 1",
            "volatility_return_std_20d": "sample standard deviation of last 20 daily returns",
            "annualization": "none",
        },
        "required_technical_features": list(PM_TECHNICAL_REQUIRED_COLUMNS) if include_pm_features else [],
        "source_dataset": "J-Quants equities_bars_daily",
        "source_path": str(source_path),
        "source_content_hash": source_hash,
        "source_columns": source_columns,
        "producer_result_status": status,
        "producer_calculation_completed": bool(rows),
        "validation_status": validation_status,
        "artifact_lifecycle_status": "DRAFT",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "human_review_status": "REVIEW_REQUIRED" if status != "PASS" else "NOT_REQUIRED",
        "downstream_calculation_eligibility": "CALCULATION_ALLOWED" if status == "PASS" else "CALCULATION_NOT_ALLOWED",
        "decision_resolution": decision_resolution,
        "coverage_status": coverage_status,
        "direct_reason_codes": sorted(set(reason_codes)),
        "propagated_reason_codes": [],
        "reason_codes": sorted(set(reason_codes)),
        "pit_validation": {
            "status": "PASS" if status != "BLOCK" and "PIT_INVALID" not in reason_codes else "BLOCK",
            "point_in_time": "PIT_INVALID" not in reason_codes,
            "latest_fallback_used": False,
            "future_rows_consumed": False,
            "future_row_rejection_count": future_row_rejection_count,
            "selected_source_row_count": selected_source_row_count,
        },
        "requested_symbols": requested_symbols,
        "rows": rows,
        "row_count": len(rows),
        "symbol_count": len({row.get("symbol") for row in rows if row.get("symbol")}),
        "upstream_hashes": [{"role": "market_quotes", "path": str(source_path), "sha256": source_hash}],
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
    }
    if "calculation_error" in locals():
        payload["calculation_error"] = calculation_error
    return payload


def _calculation_rows(
    frame: pd.DataFrame,
    *,
    feature_date: str,
    requested_symbols: list[str],
    include_pm_features: bool,
    source_path: Path,
    source_hash: str,
) -> list[dict[str, Any]]:
    symbols = requested_symbols or sorted(frame["code"].dropna().astype(str).unique().tolist())
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        symbol_frame = frame[frame["code"].astype(str) == symbol].sort_values("target_date").copy()
        symbol_frame = symbol_frame[symbol_frame["target_date"] <= feature_date]
        obs = int(len(symbol_frame))
        base = {
            "symbol": symbol,
            "code": symbol,
            "business_date": feature_date,
            "feature_date": feature_date,
            "source_path": str(source_path),
            "source_content_hash": source_hash,
            "feature_source_artifact": str(source_path),
            "feature_source_hash": source_hash,
            "required_features": list(PM_TECHNICAL_REQUIRED_COLUMNS) if include_pm_features else ["volatility_value"],
            "optional_features": [],
            "missing_features": [],
            "defaulted_features": [],
            "observation_count": obs,
            "minimum_observations": MINIMUM_PRICE_OBSERVATIONS,
            "temporal_validation_status": "PASS",
            "pit_validation": "PASS",
        }
        if obs < MINIMUM_PRICE_OBSERVATIONS:
            rows.append(
                {
                    **base,
                    "coverage_status": "INSUFFICIENT_OBSERVATIONS",
                    "volatility_value": None,
                    "decision_resolution": "UNRESOLVED",
                    "missing_features": ["insufficient_observations"],
                }
            )
            continue
        close = pd.to_numeric(symbol_frame["close"], errors="coerce")
        volume = pd.to_numeric(symbol_frame["volume"], errors="coerce")
        traded_value = close * volume
        returns = close.pct_change()
        vol20 = _finite_or_none(returns.tail(PRICE_LOOKBACK_BUSINESS_DAYS).std())
        latest = symbol_frame.iloc[-1]
        reference_price = _finite_or_none(latest.get("close"))
        reference_price_date = str(latest.get("target_date") or feature_date)
        reference_price_payload = _reference_price_payload(
            symbol=symbol,
            reference_price=reference_price,
            reference_price_date=reference_price_date,
            feature_date=feature_date,
            source_path=source_path,
            source_hash=source_hash,
        )
        if vol20 is None or vol20 <= 0:
            rows.append(
                {
                    **base,
                    "coverage_status": "INSUFFICIENT_OBSERVATIONS",
                    "volatility_value": None,
                    **reference_price_payload,
                    "decision_resolution": "UNRESOLVED",
                    "missing_features": ["volatility_return_std_20d"],
                }
            )
            continue
        row = {
            **base,
            "coverage_status": "AVAILABLE",
            "volatility_value": round(vol20, 10),
            "volatility_return_std_20d": round(vol20, 10),
            **reference_price_payload,
            **_liquidity_capacity_payload(
                symbol=symbol,
                traded_value=traded_value,
                feature_date=feature_date,
                source_path=source_path,
                source_hash=source_hash,
            ),
            "decision_resolution": "RESOLVED",
        }
        if include_pm_features:
            ma5 = _finite_or_none(close.tail(5).mean())
            ma20 = _finite_or_none(close.tail(20).mean())
            vol5 = _finite_or_none(volume.tail(5).mean())
            vol20_avg = _finite_or_none(volume.tail(20).mean())
            return_1d = _return_over(close, 1)
            return_3d = _return_over(close, 3)
            return_5d = _return_over(close, 5)
            return_10d = _return_over(close, 10)
            return_20d = _return_over(close, 20)
            row.update(
                {
                    "target_date": feature_date,
                    "feature_as_of_date": feature_date,
                    "data_until": feature_date,
                    "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
                    "price_momentum_return_1d": return_1d,
                    "price_momentum_return_3d": return_3d,
                    "price_momentum_return_5d": return_5d,
                    "price_momentum_return_10d": return_10d,
                    "price_momentum_return_20d": return_20d,
                    "recent_move_volatility_z_1d": _volatility_z(return_1d, vol20, scale=1.0),
                    "recent_move_volatility_z_3d": _volatility_z(return_3d, vol20, scale=3.0**0.5),
                    "momentum_5d_vs_20d_delta": _difference_or_none(return_5d, return_20d),
                    "momentum_1d_vs_5d_delta": _difference_or_none(return_1d, return_5d),
                    "trend_close_over_ma_20d": _ratio_or_none(_finite_or_none(close.iloc[-1]), ma20),
                    "trend_ma_5_20_ratio": _ratio_or_none(ma5, ma20),
                    "volume_momentum_ratio_5d": _ratio_or_none(vol5, vol20_avg),
                }
            )
            missing = [name for name in PM_TECHNICAL_REQUIRED_COLUMNS if row.get(name) is None]
            row["missing_features"] = missing
            if missing:
                row["coverage_status"] = "INSUFFICIENT_OBSERVATIONS"
                row["decision_resolution"] = "UNRESOLVED"
        rows.append(row)
    return rows


def _liquidity_capacity_payload(
    *,
    symbol: str,
    traded_value: pd.Series,
    feature_date: str,
    source_path: Path,
    source_hash: str,
) -> dict[str, Any]:
    window = pd.to_numeric(traded_value.tail(ROLLING_TRADED_VALUE_LOOKBACK_BUSINESS_DAYS), errors="coerce")
    valid = window.dropna()
    rolling_value = _finite_or_none(valid.median()) if len(valid) == ROLLING_TRADED_VALUE_LOOKBACK_BUSINESS_DAYS else None
    status = "PASS" if rolling_value is not None and rolling_value > 0 else "REVIEW_REQUIRED"
    reason = "rolling_median_traded_value_resolved" if status == "PASS" else "rolling_median_traded_value_missing_or_invalid"
    return {
        ROLLING_MEDIAN_TRADED_VALUE_FIELD: round(rolling_value, 2) if rolling_value is not None and rolling_value > 0 else None,
        "rolling_median_traded_value_20_authority": {
            "authority_type": LIQUIDITY_CAPACITY_AUTHORITY,
            "canonical_field": ROLLING_MEDIAN_TRADED_VALUE_FIELD,
            "source_authority": "MARKET_EVIDENCE_AUTHORITY",
            "source_dataset": "J-Quants equities_bars_daily",
            "source_formula": "median(close * volume over last 20 PIT rows)",
            "source_fields": ["close", "volume"],
            "lookback_business_days": ROLLING_TRADED_VALUE_LOOKBACK_BUSINESS_DAYS,
            "source_path": str(source_path),
            "source_hash": source_hash,
            "symbol": symbol,
            "business_date": feature_date,
            "PIT_status": "PASS",
            "latest_fallback_used": False,
        },
        "rolling_median_traded_value_20_resolution": {
            "status": status,
            "reason": reason,
            "resolved_value": round(rolling_value, 2) if rolling_value is not None and rolling_value > 0 else None,
            "source_fields": ["close", "volume"],
            "capacity_required_for": "reentry_capacity_ratio",
            "review_reason": "" if status == "PASS" else reason,
        },
    }


def _reference_price_payload(
    *,
    symbol: str,
    reference_price: float | None,
    reference_price_date: str,
    feature_date: str,
    source_path: Path,
    source_hash: str,
) -> dict[str, Any]:
    if reference_price is None or reference_price <= 0:
        return {
            REFERENCE_PRICE_FIELD: None,
            "reference_price_type": REFERENCE_PRICE_TYPE,
            "reference_price_date": reference_price_date,
            "reference_price_authority": {
                "authority_type": REFERENCE_PRICE_AUTHORITY,
                "canonical_field": REFERENCE_PRICE_FIELD,
                "source_authority": "MARKET_EVIDENCE_AUTHORITY",
                "source_dataset": "J-Quants equities_bars_daily",
                "source_field": "close",
                "source_path": str(source_path),
                "source_hash": source_hash,
                "symbol": symbol,
                "business_date": feature_date,
                "price_date": reference_price_date,
                "price_type": REFERENCE_PRICE_TYPE,
                "PIT_status": "PASS" if reference_price_date <= feature_date else "BLOCK",
                "latest_fallback_used": False,
            },
            "reference_price_resolution": {
                "status": "REVIEW_REQUIRED",
                "reason": "reference_price_missing_or_invalid",
                "resolved_price": None,
                "source_field": "close",
                "price_required_for": "position_sizing_quantity_conversion",
                "review_reason": "reference_price_missing_or_invalid",
            },
        }
    return {
        REFERENCE_PRICE_FIELD: round(reference_price, 10),
        "reference_price_type": REFERENCE_PRICE_TYPE,
        "reference_price_date": reference_price_date,
        "reference_price_authority": {
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "canonical_field": REFERENCE_PRICE_FIELD,
            "source_authority": "MARKET_EVIDENCE_AUTHORITY",
            "source_dataset": "J-Quants equities_bars_daily",
            "source_field": "close",
            "source_path": str(source_path),
            "source_hash": source_hash,
            "symbol": symbol,
            "business_date": feature_date,
            "price_date": reference_price_date,
            "price_type": REFERENCE_PRICE_TYPE,
            "PIT_status": "PASS" if reference_price_date <= feature_date else "BLOCK",
            "latest_fallback_used": False,
        },
        "reference_price_resolution": {
            "status": "PASS" if reference_price_date <= feature_date else "REVIEW_REQUIRED",
            "reason": "reference_price_resolved" if reference_price_date <= feature_date else "reference_price_future_date",
            "resolved_price": round(reference_price, 10) if reference_price_date <= feature_date else None,
            "source_field": "close",
            "price_required_for": "position_sizing_quantity_conversion",
            "review_reason": "" if reference_price_date <= feature_date else "reference_price_future_date",
        },
    }


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    date_col = _first_existing(frame, ("target_date", "Date", "date"))
    code_col = _first_existing(frame, ("code", "Code", "symbol", "Symbol"))
    close_col = _first_existing(frame, ("AdjC", "adjusted_close", "Close", "C", "close"))
    volume_col = _first_existing(frame, ("AdjVo", "adjusted_volume", "Volume", "Vo", "volume"))
    if not date_col or not code_col or not close_col:
        return pd.DataFrame(columns=["target_date", "code", "close", "volume"])
    result = pd.DataFrame(
        {
            "target_date": frame[date_col].astype(str),
            "code": frame[code_col].astype(str),
            "close": pd.to_numeric(frame[close_col], errors="coerce"),
            "volume": pd.to_numeric(frame[volume_col], errors="coerce") if volume_col else float("nan"),
        }
    )
    result = result.dropna(subset=["target_date", "code", "close"])
    return result[result["close"] > 0]


def _write_result(output_path: Path | str, payload: dict[str, Any]) -> StrategyInputMaterializationResult:
    artifact_hash = stable_payload_hash(payload)
    final = {**payload, "content_hash": artifact_hash, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final)
    return StrategyInputMaterializationResult(
        status=str(final["producer_result_status"]),
        reason=",".join(final.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final,
    )


def stable_payload_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _first_existing(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    return next((name for name in candidates if name in frame.columns), "")


def _return_over(values: pd.Series, periods: int) -> float | None:
    if len(values) <= periods:
        return None
    current = _finite_or_none(values.iloc[-1])
    previous = _finite_or_none(values.iloc[-periods - 1])
    return None if current is None or previous in (None, 0.0) else round((current / previous) - 1.0, 10)


def _difference_or_none(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(left - right, 10)


def _volatility_z(value: float | None, volatility: float | None, *, scale: float) -> float | None:
    if value is None or volatility in (None, 0.0):
        return None
    return round(value / (float(volatility) * scale), 10)


def _ratio_or_none(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0.0):
        return None
    return round(numerator / denominator, 10)


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return number if math.isfinite(number) else None
