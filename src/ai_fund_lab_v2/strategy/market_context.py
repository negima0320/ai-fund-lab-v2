from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.strategy.status_contract import status_contract_fields


SCHEMA_VERSION = "strategy_market_context.v1"
PRODUCER_VERSION = "phase22_a_market_context_producer.v1"
CONFIG_SCHEMA_VERSION = "market_context_config.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

TREND_REGIMES = {"BULL", "BEAR", "RANGE", "RECOVERY", "CORRECTION", "UNCERTAIN"}
BREADTH_REGIMES = {"STRONG", "NEUTRAL", "WEAK"}
VOLATILITY_REGIMES = {"HIGH", "NORMAL", "LOW"}
SECTOR_DISPERSION_REGIMES = {"HIGH", "MODERATE", "LOW"}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}


class MarketContextError(RuntimeError):
    pass


class MarketContextSchemaError(MarketContextError):
    pass


class MarketContextConsumerError(MarketContextError):
    pass


class MarketContextConfigError(MarketContextError):
    pass


@dataclass(frozen=True)
class MarketContextThresholds:
    bull_return_20d_min: float
    bear_return_20d_max: float
    strong_breadth_min: float
    weak_breadth_max: float
    high_volatility_min: float
    low_volatility_max: float
    high_sector_dispersion_min: float
    low_sector_dispersion_max: float

    def validate(self) -> None:
        if self.bear_return_20d_max > self.bull_return_20d_min:
            raise ValueError("bear_return_20d_max must be <= bull_return_20d_min")
        if self.weak_breadth_max > self.strong_breadth_min:
            raise ValueError("weak_breadth_max must be <= strong_breadth_min")
        if self.low_volatility_max > self.high_volatility_min:
            raise ValueError("low_volatility_max must be <= high_volatility_min")
        if self.low_sector_dispersion_max > self.high_sector_dispersion_min:
            raise ValueError("low_sector_dispersion_max must be <= high_sector_dispersion_min")


@dataclass(frozen=True)
class MarketContextInputPaths:
    daily_quotes_path: Path
    listed_issues_path: Path | None = None
    trading_calendar_path: Path | None = None


@dataclass(frozen=True)
class MarketContextAuthorityConfig:
    config_version: str
    config_source: str
    benchmark: dict[str, Any]
    sector: dict[str, Any]
    trend: dict[str, Any]
    breadth: dict[str, Any]
    volatility: dict[str, Any]
    regime_mapping: dict[str, Any]
    confidence: dict[str, Any]
    uncertainty: dict[str, Any]
    pit_contract: dict[str, Any]
    failure_contract: dict[str, Any]
    bootstrap_contract: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "benchmark": dict(self.benchmark),
            "sector": dict(self.sector),
            "trend": dict(self.trend),
            "breadth": dict(self.breadth),
            "volatility": dict(self.volatility),
            "regime_mapping": dict(self.regime_mapping),
            "confidence": dict(self.confidence),
            "uncertainty": dict(self.uncertainty),
            "pit_contract": dict(self.pit_contract),
            "failure_contract": dict(self.failure_contract),
            "bootstrap_contract": dict(self.bootstrap_contract),
        }


@dataclass(frozen=True)
class MarketContextProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "market_context" / business_date / "market_context.json"


def resolve_default_input_paths(operations_root: Path | str) -> MarketContextInputPaths:
    root = Path(operations_root)
    return MarketContextInputPaths(
        daily_quotes_path=root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
        listed_issues_path=root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
        trading_calendar_path=root / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
    )


def load_market_context_config(path: Path | str) -> MarketContextAuthorityConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise MarketContextConfigError(f"market context config missing: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MarketContextConfigError(f"market context config invalid json: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise MarketContextConfigError("unsupported market context config schema_version")
    required_objects = (
        "benchmark",
        "sector",
        "trend",
        "breadth",
        "volatility",
        "regime_mapping",
        "confidence",
        "uncertainty",
        "pit_contract",
        "failure_contract",
        "bootstrap_contract",
    )
    for field in required_objects:
        if not isinstance(payload.get(field), dict):
            raise MarketContextConfigError(f"market context config field must be object:{field}")
    config = MarketContextAuthorityConfig(
        config_version=_required_text(payload, "config_version"),
        config_source=str(config_path),
        benchmark=dict(payload["benchmark"]),
        sector=dict(payload["sector"]),
        trend=dict(payload["trend"]),
        breadth=dict(payload["breadth"]),
        volatility=dict(payload["volatility"]),
        regime_mapping=dict(payload["regime_mapping"]),
        confidence=dict(payload["confidence"]),
        uncertainty=dict(payload["uncertainty"]),
        pit_contract=dict(payload["pit_contract"]),
        failure_contract=dict(payload["failure_contract"]),
        bootstrap_contract=dict(payload["bootstrap_contract"]),
    )
    _validate_market_context_config(config)
    return config


def produce_market_context_artifact(
    *,
    business_date: str,
    input_paths: MarketContextInputPaths,
    output_path: Path | str,
    thresholds: MarketContextThresholds | None = None,
    config: MarketContextAuthorityConfig | None = None,
    as_of: str | None = None,
    expected_source_hashes: dict[str, str] | None = None,
) -> MarketContextProducerResult:
    _validate_iso_date(business_date, field="business_date")
    payload, evidence = build_market_context_payload(
        business_date=business_date,
        input_paths=input_paths,
        thresholds=thresholds,
        config=config,
        as_of=as_of,
        expected_source_hashes=expected_source_hashes,
    )
    validate_market_context_artifact(payload)
    artifact_hash = market_context_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return MarketContextProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_market_context_payload(
    *,
    business_date: str,
    input_paths: MarketContextInputPaths,
    thresholds: MarketContextThresholds | None = None,
    config: MarketContextAuthorityConfig | None = None,
    as_of: str | None = None,
    expected_source_hashes: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if thresholds is not None:
        thresholds.validate()
    if config is not None:
        _validate_market_context_config(config)
        thresholds = _thresholds_from_config(config)
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    source_status, source_artifacts, source_hashes, source_reasons = resolve_source_authority(
        input_paths=input_paths,
        expected_source_hashes=expected_source_hashes or {},
    )
    metrics: dict[str, Any] = {}
    metrics_status = "REVIEW_REQUIRED"
    metric_reasons: list[str] = []
    future_leakage_used = False
    feature_date = business_date

    if source_status != "MISSING":
        metrics, metric_reasons = calculate_market_context_metrics(
            business_date=business_date,
            input_paths=input_paths,
        )
        metrics_status = "PASS" if not metric_reasons else ("BLOCK" if any(reason in {"future_source_row_rejected", "feature_date_after_business_date"} for reason in metric_reasons) else "REVIEW_REQUIRED")
        feature_date = str(metrics.get("feature_date") or business_date)
        future_leakage_used = any(reason in {"future_source_row_detected", "feature_date_after_business_date"} for reason in metric_reasons)

    reason_codes = sorted(set([*source_reasons, *metric_reasons]))
    authority = _authority_context(config=config, metrics=metrics, input_paths=input_paths)
    taxonomy = _taxonomy_from_metrics(metrics=metrics, thresholds=thresholds, config=config)
    if thresholds is None:
        reason_codes.append("market_context_threshold_config_required")
    reason_codes.extend(authority["reason_codes"])
    if "metric_conflict_uncertain" in taxonomy.get("reason_codes", []):
        reason_codes.append("metric_conflict_uncertain")
    if config is not None and authority["sector_source_status"] != "VALID":
        reason_codes.append("sector_authority_review_required")

    if source_status in {"HASH_MISMATCH", "AUTHORITY_CONFLICT"} or metrics_status == "BLOCK":
        producer_status = "BLOCK"
    elif (
        source_status == "MISSING"
        or source_status == "STALE"
        or thresholds is None
        or metrics_status == "REVIEW_REQUIRED"
        or "metric_conflict_uncertain" in reason_codes
        or (config is not None and authority["benchmark_coverage_status"] != "PASS")
    ):
        producer_status = "REVIEW_REQUIRED"
    else:
        producer_status = "PASS"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "trend_regime": taxonomy["trend_regime"],
        "trend_strength": taxonomy["trend_strength"],
        "market_breadth": taxonomy["market_breadth"],
        "volatility_regime": taxonomy["volatility_regime"],
        "sector_dispersion": taxonomy["sector_dispersion"],
        "benchmark_id": authority["benchmark_id"],
        "benchmark_source_type": authority["benchmark_source_type"],
        "benchmark_universe": authority["benchmark_universe"],
        "benchmark_weighting": authority["benchmark_weighting"],
        "benchmark_coverage": authority["benchmark_coverage"],
        "trend_metric": taxonomy["trend_metric"],
        "trend_value": taxonomy["trend_value"],
        "trend_state": taxonomy["trend_regime"],
        "breadth_metric": taxonomy["breadth_metric"],
        "breadth_value": taxonomy["breadth_value"],
        "breadth_state": taxonomy["market_breadth"],
        "breadth_eligible_count": authority["breadth_eligible_count"],
        "breadth_valid_count": authority["breadth_valid_count"],
        "volatility_metric": taxonomy["volatility_metric"],
        "volatility_value": taxonomy["volatility_value"],
        "volatility_state": taxonomy["volatility_regime"],
        "volatility_observation_count": authority["volatility_observation_count"],
        "regime_state": taxonomy["regime_state"],
        "regime_reason_codes": taxonomy["reason_codes"],
        "sector_contexts": authority["sector_contexts"],
        "confidence": taxonomy["confidence"],
        "uncertainty": taxonomy["uncertainty"],
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=producer_status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reason_codes)),
            decision_resolution="RESOLVED" if producer_status == "PASS" else "UNRESOLVED",
        ),
        "reason_codes": sorted(set(reason_codes)),
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "config_hash": sha256_file(Path(config.config_source)) if config is not None and Path(config.config_source).is_file() else "",
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
            "latest_fallback_used": False,
            "previous_day_context_copied": False,
            "classification_effective_date_lte_business_date": authority["classification_effective_date_lte_business_date"],
        },
        "metrics": _json_safe(metrics),
        "threshold_policy": _threshold_policy_payload(thresholds),
        "authority_policy": authority["policy"],
    }
    evidence = {
        "schema_version": "phase22_a_market_context_producer_evidence.v1",
        "business_date": business_date,
        "source_authority_status": source_status,
        "producer_result_status": producer_status,
        "future_leakage_used": future_leakage_used,
        "reason_codes": payload["reason_codes"],
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "threshold_policy_present": thresholds is not None,
        "config_policy_present": config is not None,
        "benchmark_coverage_status": authority["benchmark_coverage_status"],
        "sector_source_status": authority["sector_source_status"],
    }
    return payload, evidence


def resolve_source_authority(
    *,
    input_paths: MarketContextInputPaths,
    expected_source_hashes: dict[str, str] | None = None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, str]], list[str]]:
    expected = expected_source_hashes or {}
    refs = [
        ("jquants_daily_quotes", input_paths.daily_quotes_path, True),
        ("jquants_listed_issues", input_paths.listed_issues_path, False),
        ("jquants_trading_calendar", input_paths.trading_calendar_path, False),
    ]
    source_artifacts: list[dict[str, Any]] = []
    source_hashes: list[dict[str, str]] = []
    reasons: list[str] = []
    status = "VALID"
    for role, maybe_path, required in refs:
        path = Path(maybe_path) if maybe_path is not None else None
        exists = bool(path and path.is_file())
        source_artifacts.append({"role": role, "path": str(path or ""), "required": required, "exists": exists})
        if not exists:
            if required:
                status = "MISSING"
                reasons.append(f"{role}_missing")
            else:
                reasons.append(f"{role}_optional_missing")
            continue
        actual = sha256_file(path)
        source_hashes.append({"role": role, "path": str(path), "sha256": actual})
        expected_hash = expected.get(role) or expected.get(str(path))
        if expected_hash and _strip_sha256(expected_hash) != actual:
            status = "HASH_MISMATCH"
            reasons.append(f"{role}_hash_mismatch")
    return status, source_artifacts, sorted(source_hashes, key=lambda item: (item["role"], item["path"])), sorted(set(reasons))


def calculate_market_context_metrics(*, business_date: str, input_paths: MarketContextInputPaths) -> tuple[dict[str, Any], list[str]]:
    import pandas as pd

    quotes_path = Path(input_paths.daily_quotes_path)
    if not quotes_path.is_file():
        return {}, ["jquants_daily_quotes_missing"]
    frame = pd.read_parquet(quotes_path)
    if frame.empty:
        return {}, ["jquants_daily_quotes_empty"]
    date_col = _first_column(frame, ("target_date", "Date", "date"))
    code_col = _first_column(frame, ("code", "Code", "LocalCode", "symbol"))
    close_col = _first_column(frame, ("Close", "C", "AdjustmentClose", "close"))
    volume_col = _first_column(frame, ("Volume", "Vo", "volume"))
    missing_cols = [name for name, value in {"date": date_col, "code": code_col, "close": close_col}.items() if not value]
    if missing_cols:
        return {}, [f"daily_quotes_required_column_missing:{','.join(missing_cols)}"]
    working = frame[[date_col, code_col, close_col, *([volume_col] if volume_col else [])]].copy()
    working.columns = ["target_date", "code", "close", *(["volume"] if volume_col else [])]
    working["target_date"] = working["target_date"].astype(str)
    working["code"] = working["code"].astype(str)
    working["close"] = pd.to_numeric(working["close"], errors="coerce")
    if "volume" in working:
        working["volume"] = pd.to_numeric(working["volume"], errors="coerce")
    future_row_count = int((working["target_date"] > business_date).sum())
    max_source_date = str(working["target_date"].max())
    working = working[working["target_date"] <= business_date].dropna(subset=["close"])
    if working.empty:
        return {
            "max_source_date": max_source_date,
            "future_source_row_count": future_row_count,
            "future_rows_used": False,
        }, ["future_source_row_rejected" if future_row_count else "no_pit_daily_quote_rows"]
    dates = sorted(working["target_date"].unique())
    feature_date = dates[-1]
    if feature_date > business_date:
        return {"feature_date": feature_date}, ["feature_date_after_business_date"]
    latest = working[working["target_date"] == feature_date].copy()
    if len(dates) < 21:
        return {"feature_date": feature_date, "available_business_days": len(dates)}, ["insufficient_lookback_20d"]
    start_5 = dates[-6] if len(dates) >= 6 else dates[0]
    start_20 = dates[-21]
    returns = _symbol_returns(working, feature_date=feature_date, start_5=start_5, start_20=start_20)
    if returns.empty:
        return {"feature_date": feature_date, "available_business_days": len(dates)}, ["insufficient_symbol_return_coverage"]
    sector_returns = _sector_returns(returns, input_paths.listed_issues_path)
    metrics = {
        "feature_date": feature_date,
        "selected_as_of": feature_date,
        "max_source_date": max_source_date,
        "future_source_row_count": future_row_count,
        "future_rows_used": False,
        "available_business_days": len(dates),
        "symbol_count": int(latest["code"].nunique()),
        "return_5d_equal_weight": _finite_mean(returns["return_5d"]),
        "return_20d_equal_weight": _finite_mean(returns["return_20d"]),
        "breadth_5d_positive_ratio": _positive_ratio(returns["return_5d"]),
        "breadth_20d_positive_ratio": _positive_ratio(returns["return_20d"]),
        "volatility_20d_equal_weight": _mean_symbol_volatility(working, last_dates=dates[-21:]),
        "volatility_observation_count": int(max(len(dates[-21:]) - 1, 0)),
        "sector_return_20d_dispersion": _finite_std(sector_returns),
        "sector_count": int(len(sector_returns)),
        "return_20d_valid_count": int(returns["return_20d"].dropna().shape[0]),
        "source_window_start_date": start_20,
        "source_window_end_date": feature_date,
    }
    return metrics, []


def validate_market_context_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {
        "schema_version",
        "business_date",
        "as_of",
        "feature_date",
        "trend_regime",
        "trend_strength",
        "market_breadth",
        "volatility_regime",
        "sector_dispersion",
        "confidence",
        "uncertainty",
        "artifact_lifecycle_status",
        "source_authority_status",
        "producer_result_status",
        "runtime_consumer_eligibility",
        "reason_codes",
        "source_artifacts",
        "source_hashes",
        "temporal_safety",
    }
    missing = sorted(required - set(payload))
    errors.extend(f"required_field_missing:{field}" for field in missing)
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    _enum_check(errors, payload, "trend_regime", TREND_REGIMES)
    _enum_check(errors, payload, "market_breadth", BREADTH_REGIMES)
    _enum_check(errors, payload, "volatility_regime", VOLATILITY_REGIMES)
    _enum_check(errors, payload, "sector_dispersion", SECTOR_DISPERSION_REGIMES)
    _enum_check(errors, payload, "artifact_lifecycle_status", ARTIFACT_LIFECYCLE_STATUSES)
    _enum_check(errors, payload, "source_authority_status", SOURCE_AUTHORITY_STATUSES)
    _enum_check(errors, payload, "producer_result_status", PRODUCER_RESULT_STATUSES)
    _enum_check(errors, payload, "runtime_consumer_eligibility", RUNTIME_CONSUMER_ELIGIBILITIES)
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_a_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_a_runtime_consumer_eligibility_must_be_not_eligible")
    for field in ("business_date", "feature_date"):
        try:
            _validate_iso_date(str(payload.get(field) or ""), field=field)
        except Exception:
            errors.append(f"invalid_date_format:{field}")
    try:
        _validate_rfc3339_timestamp(str(payload.get("as_of") or ""), field="as_of")
    except Exception:
        errors.append("invalid_timestamp_format:as_of")
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        errors.append("invalid_confidence_range")
    if not isinstance(payload.get("trend_strength"), (int, float)) or isinstance(payload.get("trend_strength"), bool):
        errors.append("invalid_trend_strength")
    if "trend_state" in payload and payload.get("trend_state") != payload.get("trend_regime"):
        errors.append("trend_state_must_match_trend_regime")
    if "breadth_state" in payload and payload.get("breadth_state") != payload.get("market_breadth"):
        errors.append("breadth_state_must_match_market_breadth")
    if "volatility_state" in payload and payload.get("volatility_state") != payload.get("volatility_regime"):
        errors.append("volatility_state_must_match_volatility_regime")
    if "benchmark_coverage" in payload and (not isinstance(payload.get("benchmark_coverage"), (int, float)) or isinstance(payload.get("benchmark_coverage"), bool)):
        errors.append("invalid_benchmark_coverage")
    if ("breadth_eligible_count" in payload or "breadth_valid_count" in payload) and (
        not isinstance(payload.get("breadth_eligible_count"), int) or not isinstance(payload.get("breadth_valid_count"), int)
    ):
        errors.append("invalid_breadth_counts")
    if "volatility_observation_count" in payload and not isinstance(payload.get("volatility_observation_count"), int):
        errors.append("invalid_volatility_observation_count")
    if "regime_reason_codes" in payload and not isinstance(payload.get("regime_reason_codes"), list):
        errors.append("regime_reason_codes_not_list")
    if "sector_contexts" in payload and not isinstance(payload.get("sector_contexts"), list):
        errors.append("sector_contexts_not_list")
    if not isinstance(payload.get("reason_codes"), list):
        errors.append("reason_codes_not_list")
    if not isinstance(payload.get("source_artifacts"), list):
        errors.append("source_artifacts_not_list")
    if not isinstance(payload.get("source_hashes"), list):
        errors.append("source_hashes_not_list")
    temporal = payload.get("temporal_safety")
    if not isinstance(temporal, dict):
        errors.append("temporal_safety_not_object")
    else:
        if temporal.get("future_leakage_used") is True and payload.get("producer_result_status") != "BLOCK":
            errors.append("future_leakage_must_block")
        if temporal.get("latest_fallback_used") is True:
            errors.append("latest_fallback_blocked")
        if temporal.get("previous_day_context_copied") is True:
            errors.append("previous_day_context_copy_blocked")
        if str(payload.get("feature_date") or "9999-99-99") > str(payload.get("business_date") or ""):
            errors.append("feature_date_after_business_date")
    if errors:
        raise MarketContextSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    missing = []
    for item in payload.get("source_hashes") or []:
        path = Path(str(item.get("path") or ""))
        expected = str(item.get("sha256") or "")
        if not path.is_file():
            missing.append(str(path))
            continue
        actual = sha256_file(path)
        if actual != _strip_sha256(expected):
            mismatches.append({"path": str(path), "expected": expected, "actual": actual})
    if mismatches:
        return {"status": "BLOCK", "reason": "source_hash_mismatch", "mismatches": mismatches, "missing": missing}
    if missing:
        return {"status": "REVIEW_REQUIRED", "reason": "source_missing", "mismatches": [], "missing": missing}
    return {"status": "PASS", "reason": "source_hashes_match", "mismatches": [], "missing": []}


def load_market_context_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_market_context_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise MarketContextConsumerError("BLOCK artifact is not fixture-consumable")
    if for_production and payload.get("runtime_consumer_eligibility") != "ELIGIBLE":
        raise MarketContextConsumerError("Market Context artifact is not runtime consumer eligible")
    if payload.get("runtime_consumer_eligibility") == "ELIGIBLE" and payload.get("artifact_lifecycle_status") != "ACCEPTED":
        raise MarketContextConsumerError("runtime eligible artifact must be ACCEPTED")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase22_a_produced_but_not_consumed_validation.v1",
        "artifact_produced": bool(payload),
        "production_consumer_connected": False,
        "runtime_consumer_eligibility": payload.get("runtime_consumer_eligibility"),
        "legacy_authority_active": True,
        "runtime_switch_performed": False,
        "status": "PASS"
        if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE"
        else "BLOCK",
    }


def market_context_hash(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _taxonomy_from_metrics(
    *,
    metrics: dict[str, Any],
    thresholds: MarketContextThresholds | None,
    config: MarketContextAuthorityConfig | None = None,
) -> dict[str, Any]:
    if not metrics or thresholds is None:
        return {
            "trend_regime": "RANGE",
            "trend_strength": 0.0,
            "market_breadth": "NEUTRAL",
            "volatility_regime": "NORMAL",
            "sector_dispersion": "MODERATE",
            "trend_metric": "",
            "trend_value": 0.0,
            "breadth_metric": "",
            "breadth_value": 0.0,
            "volatility_metric": "",
            "volatility_value": 0.0,
            "regime_state": "UNCERTAIN",
            "reason_codes": ["threshold_or_source_review_required"],
            "confidence": 0.0,
            "uncertainty": "THRESHOLD_OR_SOURCE_REVIEW_REQUIRED",
        }
    ret20 = float(metrics.get("return_20d_equal_weight") or 0.0)
    ret5 = float(metrics.get("return_5d_equal_weight") or 0.0)
    breadth = float(metrics.get("breadth_20d_positive_ratio") or 0.0)
    volatility = float(metrics.get("volatility_20d_equal_weight") or 0.0)
    dispersion = float(metrics.get("sector_return_20d_dispersion") or 0.0)
    reason_codes: list[str] = []
    if ret20 >= thresholds.bull_return_20d_min:
        trend = "BULL"
    elif ret20 <= thresholds.bear_return_20d_max:
        trend = "BEAR"
    elif ret20 >= 0 and ret5 >= 0:
        trend = "RECOVERY"
    elif ret20 < 0 and ret5 < 0:
        trend = "CORRECTION"
    else:
        trend = "RANGE"
    breadth_state = "STRONG" if breadth >= thresholds.strong_breadth_min else ("WEAK" if breadth <= thresholds.weak_breadth_max else "NEUTRAL")
    volatility_state = "HIGH" if volatility >= thresholds.high_volatility_min else ("LOW" if volatility <= thresholds.low_volatility_max else "NORMAL")
    if trend == "BULL" and breadth_state == "WEAK":
        trend = "UNCERTAIN"
        reason_codes.append("metric_conflict_uncertain")
    if trend == "BEAR" and breadth_state == "STRONG":
        trend = "UNCERTAIN"
        reason_codes.append("metric_conflict_uncertain")
    regime_state = "HIGH_VOLATILITY" if volatility_state == "HIGH" else trend
    if trend == "UNCERTAIN":
        regime_state = "UNCERTAIN"
    confidence = _confidence_from_metrics(metrics, reason_codes=reason_codes, config=config)
    return {
        "trend_regime": trend,
        "trend_strength": _round_float(abs(ret20)),
        "market_breadth": breadth_state,
        "volatility_regime": volatility_state,
        "sector_dispersion": "HIGH" if dispersion >= thresholds.high_sector_dispersion_min else ("LOW" if dispersion <= thresholds.low_sector_dispersion_max else "MODERATE"),
        "trend_metric": (config.trend.get("metric") if config else "return_20d_equal_weight"),
        "trend_value": _round_float(ret20),
        "breadth_metric": (config.breadth.get("metric") if config else "breadth_20d_positive_ratio"),
        "breadth_value": _round_float(breadth),
        "volatility_metric": (config.volatility.get("metric") if config else "volatility_20d_equal_weight"),
        "volatility_value": _round_float(volatility),
        "regime_state": regime_state,
        "reason_codes": reason_codes or [f"trend:{trend}", f"breadth:{breadth_state}", f"volatility:{volatility_state}"],
        "confidence": confidence,
        "uncertainty": "UNCERTAIN" if trend == "UNCERTAIN" else ("MEDIUM" if confidence < 0.8 else "LOW"),
    }


def _threshold_policy_payload(thresholds: MarketContextThresholds | None) -> dict[str, Any]:
    if thresholds is None:
        return {"status": "CONFIG_REQUIRED", "source": "", "values": None}
    return {
        "status": "EXPLICIT_TEST_OR_CALLER_SUPPLIED",
        "source": "caller",
        "values": {
            "bull_return_20d_min": thresholds.bull_return_20d_min,
            "bear_return_20d_max": thresholds.bear_return_20d_max,
            "strong_breadth_min": thresholds.strong_breadth_min,
            "weak_breadth_max": thresholds.weak_breadth_max,
            "high_volatility_min": thresholds.high_volatility_min,
            "low_volatility_max": thresholds.low_volatility_max,
            "high_sector_dispersion_min": thresholds.high_sector_dispersion_min,
            "low_sector_dispersion_max": thresholds.low_sector_dispersion_max,
        },
    }


def _thresholds_from_config(config: MarketContextAuthorityConfig) -> MarketContextThresholds:
    trend_thresholds = dict(config.trend.get("thresholds") or {})
    breadth_thresholds = dict(config.breadth.get("thresholds") or {})
    volatility_thresholds = dict(config.volatility.get("thresholds") or {})
    sector_thresholds = dict(config.sector.get("dispersion_thresholds") or {})
    return MarketContextThresholds(
        bull_return_20d_min=float(trend_thresholds["bull_return_20d_min"]),
        bear_return_20d_max=float(trend_thresholds["bear_return_20d_max"]),
        strong_breadth_min=float(breadth_thresholds["strong_min"]),
        weak_breadth_max=float(breadth_thresholds["weak_max"]),
        high_volatility_min=float(volatility_thresholds["high_min"]),
        low_volatility_max=float(volatility_thresholds["low_max"]),
        high_sector_dispersion_min=float(sector_thresholds.get("high_min", 0.03)),
        low_sector_dispersion_max=float(sector_thresholds.get("low_max", 0.005)),
    )


def _authority_context(
    *,
    config: MarketContextAuthorityConfig | None,
    metrics: dict[str, Any],
    input_paths: MarketContextInputPaths,
) -> dict[str, Any]:
    valid_count = int(metrics.get("return_20d_valid_count") or 0)
    eligible_count = int(metrics.get("symbol_count") or 0)
    coverage = _round_float(valid_count / eligible_count) if eligible_count else 0.0
    sector_contexts = _sector_contexts(input_paths.listed_issues_path, metrics=metrics, config=config)
    if config is None:
        return {
            "benchmark_id": "",
            "benchmark_source_type": "",
            "benchmark_universe": "",
            "benchmark_weighting": "",
            "benchmark_coverage": coverage,
            "benchmark_coverage_status": "REVIEW_REQUIRED",
            "breadth_eligible_count": eligible_count,
            "breadth_valid_count": valid_count,
            "volatility_observation_count": int(metrics.get("volatility_observation_count") or 0),
            "sector_contexts": sector_contexts,
            "sector_source_status": "REVIEW_REQUIRED",
            "classification_effective_date_lte_business_date": True,
            "reason_codes": [],
            "policy": {"status": "CONFIG_REQUIRED"},
        }
    minimum_coverage = float(config.benchmark.get("minimum_coverage") or 1.0)
    sector_status = "VALID" if sector_contexts else "REVIEW_REQUIRED"
    return {
        "benchmark_id": str(config.benchmark.get("id") or ""),
        "benchmark_source_type": str(config.benchmark.get("source_type") or ""),
        "benchmark_universe": str(config.benchmark.get("universe") or ""),
        "benchmark_weighting": str(config.benchmark.get("weighting") or ""),
        "benchmark_coverage": coverage,
        "benchmark_coverage_status": "PASS" if coverage >= minimum_coverage else "REVIEW_REQUIRED",
        "breadth_eligible_count": eligible_count,
        "breadth_valid_count": valid_count,
        "volatility_observation_count": int(metrics.get("volatility_observation_count") or 0),
        "sector_contexts": sector_contexts,
        "sector_source_status": sector_status,
        "classification_effective_date_lte_business_date": True,
        "reason_codes": [] if coverage >= minimum_coverage else ["benchmark_coverage_insufficient"],
        "policy": config.to_dict(),
    }


def _sector_contexts(
    listed_issues_path: Path | None,
    *,
    metrics: dict[str, Any],
    config: MarketContextAuthorityConfig | None,
) -> list[dict[str, Any]]:
    if listed_issues_path is None or not Path(listed_issues_path).is_file():
        return []
    try:
        import pandas as pd

        listed = pd.read_parquet(listed_issues_path)
    except Exception:
        return []
    if listed.empty:
        return []
    code_col = _first_column(listed, ("code", "Code", "LocalCode"))
    sector_col = _first_column(listed, ("S33Nm", "S17Nm", "Sector33Code", "Sector17Code", "sector_key"))
    if not code_col or not sector_col:
        return []
    minimum_constituents = int((config.sector.get("minimum_constituents") if config else 1) or 1)
    sector = listed[[code_col, sector_col]].copy()
    sector.columns = ["code", "sector_key"]
    sector["sector_key"] = sector["sector_key"].fillna("").astype(str)
    sector = sector[sector["sector_key"] != ""]
    contexts = []
    for sector_key, group in sorted(sector.groupby("sector_key"), key=lambda item: str(item[0])):
        count = int(group["code"].nunique())
        contexts.append(
            {
                "sector_id": str(sector_key),
                "sector_name": str(sector_key),
                "constituent_count": count,
                "minimum_constituents": minimum_constituents,
                "source_status": "VALID" if count >= minimum_constituents else "REVIEW_REQUIRED",
                "trend_state": "UNCERTAIN" if count < minimum_constituents else "",
                "breadth_state": "NEUTRAL" if count >= minimum_constituents else "WEAK",
                "volatility_state": "",
                "relative_strength_reference": str((config.sector.get("relative_strength_reference") if config else "") or ""),
                "confidence": 1.0 if count >= minimum_constituents else 0.0,
            }
        )
    return contexts


def _confidence_from_metrics(
    metrics: dict[str, Any],
    *,
    reason_codes: list[str],
    config: MarketContextAuthorityConfig | None,
) -> float:
    if not metrics:
        return 0.0
    eligible = int(metrics.get("symbol_count") or 0)
    valid = int(metrics.get("return_20d_valid_count") or 0)
    coverage = (valid / eligible) if eligible else 0.0
    observation_target = int((config.volatility.get("minimum_observations") if config else 20) or 20)
    observations = int(metrics.get("volatility_observation_count") or 0)
    observation_score = min(1.0, observations / observation_target) if observation_target else 1.0
    conflict_penalty = 0.25 if reason_codes else 0.0
    return _round_float(max(0.0, min(1.0, 0.7 * coverage + 0.3 * observation_score - conflict_penalty)))


def _validate_market_context_config(config: MarketContextAuthorityConfig) -> None:
    if config.benchmark.get("source_type") != "JQUANTS_DERIVED_MARKET_PROXY":
        raise MarketContextConfigError("benchmark source_type must be JQUANTS_DERIVED_MARKET_PROXY")
    if str(config.benchmark.get("weighting") or "") != "EQUAL_WEIGHT":
        raise MarketContextConfigError("benchmark weighting must be EQUAL_WEIGHT")
    if not 0 < float(config.benchmark.get("minimum_coverage") or 0) <= 1:
        raise MarketContextConfigError("benchmark minimum_coverage must be in (0, 1]")
    if int(config.sector.get("minimum_constituents") or 0) < 1:
        raise MarketContextConfigError("sector minimum_constituents must be positive")
    thresholds = _thresholds_from_config(config)
    thresholds.validate()
    taxonomy = set(config.regime_mapping.get("taxonomy") or [])
    required_taxonomy = {"BULL", "RANGE", "BEAR", "CORRECTION", "RECOVERY", "HIGH_VOLATILITY", "UNCERTAIN"}
    if not required_taxonomy.issubset(taxonomy):
        raise MarketContextConfigError("regime taxonomy missing required states")
    if config.bootstrap_contract.get("fixed_fallback_allowed") is not False:
        raise MarketContextConfigError("bootstrap fixed fallback must be disabled")
    if config.pit_contract.get("latest_fallback_allowed") is not False:
        raise MarketContextConfigError("latest fallback must be disabled")


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise MarketContextConfigError(f"market context config field must be non-empty string:{field}")
    return value


def _symbol_returns(frame: Any, *, feature_date: str, start_5: str, start_20: str) -> Any:
    import pandas as pd

    latest = frame[frame["target_date"] == feature_date][["code", "close"]].rename(columns={"close": "close_latest"})
    start5 = frame[frame["target_date"] == start_5][["code", "close"]].rename(columns={"close": "close_5d"})
    start20 = frame[frame["target_date"] == start_20][["code", "close"]].rename(columns={"close": "close_20d"})
    returns = latest.merge(start5, on="code", how="inner").merge(start20, on="code", how="inner")
    returns = returns[(returns["close_5d"] > 0) & (returns["close_20d"] > 0)].copy()
    returns["return_5d"] = returns["close_latest"] / returns["close_5d"] - 1.0
    returns["return_20d"] = returns["close_latest"] / returns["close_20d"] - 1.0
    return returns.replace([math.inf, -math.inf], pd.NA).dropna(subset=["return_20d"])


def _sector_returns(returns: Any, listed_issues_path: Path | None) -> Any:
    import pandas as pd

    if listed_issues_path is None or not Path(listed_issues_path).is_file():
        return pd.Series(dtype="float64")
    listed = pd.read_parquet(listed_issues_path)
    if listed.empty:
        return pd.Series(dtype="float64")
    code_col = _first_column(listed, ("code", "Code", "LocalCode"))
    sector_col = _first_column(listed, ("S33Nm", "S17Nm", "Sector33Code", "Sector17Code", "sector_key"))
    if not code_col or not sector_col:
        return pd.Series(dtype="float64")
    sector = listed[[code_col, sector_col]].copy()
    sector.columns = ["code", "sector_key"]
    sector["code"] = sector["code"].astype(str)
    sector["sector_key"] = sector["sector_key"].fillna("UNKNOWN").astype(str)
    merged = returns.merge(sector.drop_duplicates("code", keep="last"), on="code", how="left")
    return merged.groupby("sector_key")["return_20d"].mean()


def _mean_symbol_volatility(frame: Any, *, last_dates: list[str]) -> float:
    import pandas as pd

    subset = frame[frame["target_date"].isin(last_dates)].sort_values(["code", "target_date"]).copy()
    subset["daily_return"] = subset.groupby("code")["close"].pct_change()
    vols = subset.groupby("code")["daily_return"].std(ddof=0).dropna()
    if vols.empty:
        return 0.0
    return _round_float(float(vols.mean()))


def _finite_mean(values: Any) -> float:
    values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return _round_float(sum(values) / len(values)) if values else 0.0


def _finite_std(values: Any) -> float:
    values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return _round_float(math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)))


def _positive_ratio(values: Any) -> float:
    values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not values:
        return 0.0
    return _round_float(sum(1 for value in values if value > 0) / len(values))


def _round_float(value: float) -> float:
    return round(float(value), 12)


def _first_column(frame: Any, candidates: tuple[str, ...]) -> str:
    columns = set(frame.columns)
    return next((column for column in candidates if column in columns), "")


def _enum_check(errors: list[str], payload: dict[str, Any], field: str, allowed: set[str]) -> None:
    if payload.get(field) not in allowed:
        errors.append(f"invalid_enum:{field}")


def _validate_iso_date(value: str, *, field: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be normalized YYYY-MM-DD")


def _validate_rfc3339_timestamp(value: str, *, field: str) -> None:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except Exception as exc:
        raise ValueError(f"{field} must be RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")


def _strip_sha256(value: str) -> str:
    return value[7:] if value.startswith("sha256:") else value


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float):
        return _round_float(value)
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
