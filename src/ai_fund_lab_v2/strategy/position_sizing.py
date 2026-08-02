from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.status_contract import numeric_resolution, status_contract_fields
from ai_fund_lab_v2.strategy.target_weight_precision import (
    TARGET_WEIGHT_DECIMALS,
    target_weight_sum_tolerance,
)


SCHEMA_VERSION = "position_sizing.v1"
CONFIG_SCHEMA_VERSION = "position_sizing_config.v1"
PRODUCER_VERSION = "phase22_j_position_sizing_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"
ALLOCATION_QUALITY_AUTHORITY = "ALLOCATION_QUALITY_AUTHORITY"
ALLOCATION_QUALITY_CANONICAL_FIELD = "allocation_quality_score"
ALLOCATION_QUALITY_LEGACY_FIELD = "quality_score"
RAW_OPPORTUNITY_AUTHORITY = "OPPORTUNITY_RANKING_AUTHORITY"
RAW_OPPORTUNITY_CANONICAL_FIELD = "runtime_opportunity_score"
RAW_OPPORTUNITY_LEGACY_FIELDS = ("input_score", "opportunity_score")
REFERENCE_PRICE_AUTHORITY = "REFERENCE_PRICE_AUTHORITY"

SOURCE_STATUSES_BLOCK = {"BLOCK", "MISSING", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
SIZING_STATUSES = {
    "SIZED",
    "CAPPED",
    "RESOLVED_ZERO_ALLOCATION",
    "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
    "MINIMUM_NOTIONAL_UNMET",
    "VOLATILITY_UNAVAILABLE",
    "QUALITY_UNAVAILABLE",
    "TARGET_WEIGHT_UNAVAILABLE",
    "UPSTREAM_REVIEW_REQUIRED",
    "SAFETY_CONSTRAINED",
    "WITHHELD",
    "UNRESOLVED",
}
PM_ACTIONS = {"NEW", "HOLD", "ADD", "REDUCE", "EXIT", "UNRESOLVED"}
MEMBERSHIP_INTENTS = {"RETAIN", "ADD_CANDIDATE", "REDUCE_CANDIDATE", "REMOVE_CANDIDATE", "EXCLUDE", "UNRESOLVED"}
FORBIDDEN_FIELDS = {"share_quantity", "quantity", "quantity_candidate", "broker_quantity", "order_quantity", "lot_size", "round_lot", "lot_rounding_result", "pending_id", "submit_command"}


class PositionSizingError(RuntimeError):
    pass


class PositionSizingConfigError(PositionSizingError):
    pass


class PositionSizingSchemaError(PositionSizingError):
    pass


class PositionSizingConsumerError(PositionSizingError):
    pass


@dataclass(frozen=True)
class PositionSizingSourceSummary:
    status: str
    business_date: str
    feature_date: str
    source_ref: str
    source_hash: str
    rows: tuple[Mapping[str, Any], ...] = ()
    summary: Mapping[str, Any] | None = None

    def to_dict(self, *, requested_business_date: str) -> dict[str, Any]:
        return {
            "status": self.status,
            "business_date": self.business_date,
            "feature_date": self.feature_date,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "row_count": len(self.rows),
            "summary": dict(self.summary or {}),
            "business_date_aligned": self.business_date == requested_business_date,
            "feature_date_lte_business_date": bool(self.feature_date and self.feature_date <= requested_business_date),
        }


@dataclass(frozen=True)
class QualityResolution:
    resolved_quality: float | None
    authority: str
    resolution_status: str
    source_field: str
    canonical_field: str
    legacy_alias_used: bool
    review_reason: str
    source_decision_id: str
    source_artifact_class: str
    lineage: Mapping[str, Any]
    fields_observed: Mapping[str, float]
    conflict_detected: bool
    legacy_usage: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_quality": self.resolved_quality,
            "authority": self.authority,
            "resolution_status": self.resolution_status,
            "source_field": self.source_field,
            "canonical_field": self.canonical_field,
            "legacy_alias_used": self.legacy_alias_used,
            "review_reason": self.review_reason,
            "source_decision_id": self.source_decision_id,
            "source_artifact_class": self.source_artifact_class,
            "lineage": dict(self.lineage),
            "fields_observed": dict(self.fields_observed),
            "conflict_detected": self.conflict_detected,
            "legacy_usage": self.legacy_usage,
        }


@dataclass(frozen=True)
class RuntimeOpportunityScoreResolution:
    resolved_score: float | None
    authority: str
    resolution_status: str
    source_field: str
    canonical_field: str
    legacy_attribution_used: bool
    review_reason: str
    source_decision_id: str
    source_artifact_class: str
    lineage: Mapping[str, Any]
    fields_observed: Mapping[str, float]
    conflict_detected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_score": self.resolved_score,
            "authority": self.authority,
            "resolution_status": self.resolution_status,
            "source_field": self.source_field,
            "canonical_field": self.canonical_field,
            "legacy_attribution_used": self.legacy_attribution_used,
            "review_reason": self.review_reason,
            "source_decision_id": self.source_decision_id,
            "source_artifact_class": self.source_artifact_class,
            "lineage": dict(self.lineage),
            "fields_observed": dict(self.fields_observed),
            "conflict_detected": self.conflict_detected,
        }


@dataclass(frozen=True)
class PositionSizingConfig:
    config_version: str
    config_source: str
    sizing_method: str
    opportunity_adjustment: Mapping[str, float]
    volatility_adjustment: Mapping[str, Any]
    pm_intent_adjustment: Mapping[str, float]
    minimum_meaningful_notional: Mapping[str, Any]
    strategy_maximum_position_weight: float
    safety_concentration_reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "sizing_method": self.sizing_method,
            "opportunity_adjustment": dict(self.opportunity_adjustment),
            "volatility_adjustment": dict(self.volatility_adjustment),
            "pm_intent_adjustment": dict(self.pm_intent_adjustment),
            "minimum_meaningful_notional": dict(self.minimum_meaningful_notional),
            "strategy_maximum_position_weight": self.strategy_maximum_position_weight,
            "safety_concentration_reference": self.safety_concentration_reference,
        }


@dataclass(frozen=True)
class PositionSizingProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "position_sizing" / business_date / "position_sizing.json"


def load_position_sizing_config(path: Path | str) -> PositionSizingConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise PositionSizingConfigError(f"position sizing config missing: {config_path}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise PositionSizingConfigError("unsupported position sizing config")
    strategy_cap = _ratio(payload.get("strategy_maximum_position_weight"), None)
    if strategy_cap == 0.20:
        raise PositionSizingConfigError("legacy max_position_weight=0.20 must not be reused as Strategy sizing cap")
    if strategy_cap <= 0:
        raise PositionSizingConfigError("strategy maximum position weight must be positive")
    return PositionSizingConfig(
        config_version=_text(payload, "config_version"),
        config_source=str(config_path),
        sizing_method=_text(payload, "sizing_method"),
        opportunity_adjustment=_numeric_mapping(payload, "opportunity_adjustment"),
        volatility_adjustment=dict(payload.get("volatility_adjustment") or {}),
        pm_intent_adjustment=_numeric_mapping(payload, "pm_intent_adjustment"),
        minimum_meaningful_notional=dict(payload.get("minimum_meaningful_notional") or {}),
        strategy_maximum_position_weight=strategy_cap,
        safety_concentration_reference=_text(payload, "safety_concentration_reference"),
    )


def produce_position_sizing_artifact(
    *,
    business_date: str,
    portfolio_construction_summary: PositionSizingSourceSummary,
    capital_deployment_summary: PositionSizingSourceSummary,
    dynamic_position_count_summary: PositionSizingSourceSummary,
    dynamic_cash_exposure_summary: PositionSizingSourceSummary,
    position_management_summary: PositionSizingSourceSummary,
    opportunity_summary: PositionSizingSourceSummary,
    current_position_summary: PositionSizingSourceSummary,
    price_volatility_summary: PositionSizingSourceSummary,
    safety_limit_summary: PositionSizingSourceSummary,
    config: PositionSizingConfig | None,
    output_path: Path | str,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> PositionSizingProducerResult:
    payload, evidence = build_position_sizing_payload(
        business_date=business_date,
        portfolio_construction_summary=portfolio_construction_summary,
        capital_deployment_summary=capital_deployment_summary,
        dynamic_position_count_summary=dynamic_position_count_summary,
        dynamic_cash_exposure_summary=dynamic_cash_exposure_summary,
        position_management_summary=position_management_summary,
        opportunity_summary=opportunity_summary,
        current_position_summary=current_position_summary,
        price_volatility_summary=price_volatility_summary,
        safety_limit_summary=safety_limit_summary,
        config=config,
        as_of=as_of,
        expected_config_hash=expected_config_hash,
    )
    validate_position_sizing_artifact(payload)
    artifact_hash = position_sizing_hash(payload)
    final = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final)
    return PositionSizingProducerResult(final["producer_result_status"], ",".join(final.get("reason_codes") or []), str(path), artifact_hash, final, evidence)


def build_position_sizing_payload(
    *,
    business_date: str,
    portfolio_construction_summary: PositionSizingSourceSummary,
    capital_deployment_summary: PositionSizingSourceSummary,
    dynamic_position_count_summary: PositionSizingSourceSummary,
    dynamic_cash_exposure_summary: PositionSizingSourceSummary,
    position_management_summary: PositionSizingSourceSummary,
    opportunity_summary: PositionSizingSourceSummary,
    current_position_summary: PositionSizingSourceSummary,
    price_volatility_summary: PositionSizingSourceSummary,
    safety_limit_summary: PositionSizingSourceSummary,
    config: PositionSizingConfig | None,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _date(business_date)
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _timestamp(as_of)
    summaries = {
        "portfolio_construction": portfolio_construction_summary,
        "capital_deployment": capital_deployment_summary,
        "dynamic_position_count": dynamic_position_count_summary,
        "dynamic_cash_exposure": dynamic_cash_exposure_summary,
        "position_management": position_management_summary,
        "opportunity": opportunity_summary,
        "current_position": current_position_summary,
        "price_volatility": price_volatility_summary,
        "safety_limit": safety_limit_summary,
    }
    status = "PASS"
    source_status = "VALID"
    reasons: list[str] = []
    for name, summary in summaries.items():
        if summary.business_date != business_date or not summary.feature_date or summary.feature_date > business_date:
            status = "BLOCK"
            reasons.append(f"{name}_date_mismatch")
        if summary.status in SOURCE_STATUSES_BLOCK:
            status = "BLOCK"
            source_status = "AUTHORITY_CONFLICT"
            reasons.append(f"{name}_block:{summary.status}")
        elif _capital_deployment_shadow_cycle_placeholder(name, summary):
            continue
        elif summary.status != "PASS" and status != "BLOCK":
            status = "REVIEW_REQUIRED"
            reasons.append(f"{name}_review_required:{summary.status}")
    config_hash = ""
    config_source_hash = ""
    config_payload = None
    if config is None:
        if status != "BLOCK":
            status = "REVIEW_REQUIRED"
        reasons.append("position_sizing_config_required")
    else:
        config_payload = config.to_dict()
        config_hash = stable_payload_hash(config_payload)
        config_source_hash = sha256_file(Path(config.config_source)) if Path(config.config_source).is_file() else config_hash
        if expected_config_hash and _strip_sha256(expected_config_hash) != config_hash:
            status = "BLOCK"
            source_status = "HASH_MISMATCH"
            reasons.append("position_sizing_config_hash_mismatch")

    target_count_raw = dynamic_position_count_summary.summary.get("target_position_count")
    target_exposure_raw = dynamic_cash_exposure_summary.summary.get("target_gross_exposure_ratio")
    target_count_unresolved = target_count_raw is None
    target_exposure_unresolved = target_exposure_raw is None
    target_count = None if target_count_unresolved else _positive_int(target_count_raw, 0)
    target_exposure = None if target_exposure_unresolved else _ratio(target_exposure_raw, 0.0)
    if (target_count_unresolved or target_exposure_unresolved) and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("position_count_or_exposure_unresolved")
    portfolio_value = _positive_float(
        current_position_summary.summary.get("portfolio_total_equity", current_position_summary.summary.get("portfolio_value")),
        0.0,
    )
    if portfolio_value <= 0:
        if status != "BLOCK":
            status = "REVIEW_REQUIRED"
        reasons.append("portfolio_total_equity_required_for_asset_proportional_sizing")
    safety_authority = _resolve_safety_maximum_position_weight(safety_limit_summary)
    safety_cap = safety_authority["safety_maximum_position_weight"]
    if safety_authority["safety_authority_status"] == "BLOCK":
        status = "BLOCK"
        reasons.append(str(safety_authority["reason_code"]))
    elif safety_authority["safety_authority_status"] != "PASS" and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append(str(safety_authority["reason_code"]))
    if safety_cap == 0.20:
        status = "BLOCK"
        reasons.append("legacy_0_20_implicit_safety_concentration_forbidden")
    if (
        config
        and safety_authority["safety_authority_status"] == "PASS"
        and safety_cap is not None
        and not safety_authority["explicit_zero_cap"]
        and config.strategy_maximum_position_weight > safety_cap
    ):
        status = "BLOCK"
        reasons.append("configured_max_position_weight_above_safety_cap")
    effective_cap = min(config.strategy_maximum_position_weight, safety_cap) if config and safety_cap is not None else None

    sizing_rows = _rows_with_price_volatility(portfolio_construction_summary.rows, price_volatility_summary)
    positions: list[dict[str, Any]] = []
    if config is None or status != "PASS":
        positions = [_unresolved_position(row, config=config, safety_cap=effective_cap) for row in sizing_rows]
        total_target_weight = 0.0
    else:
        positions, sizing_reasons = _size_positions(
            config=config,
            rows=sizing_rows,
            target_count=target_count or 0,
            target_exposure=target_exposure or 0.0,
            portfolio_value=portfolio_value,
            safety_cap=safety_cap or 0.0,
        )
        reasons.extend(sizing_reasons)
        if any(item["sizing_status"] in {"TARGET_WEIGHT_UNAVAILABLE", "QUALITY_UNAVAILABLE", "VOLATILITY_UNAVAILABLE", "WITHHELD"} for item in positions):
            status = "REVIEW_REQUIRED"
            for item in positions:
                if item["sizing_status"] == "TARGET_WEIGHT_UNAVAILABLE":
                    resolution = item.get("target_weight_resolution") or {}
                    review_reason = str(resolution.get("review_reason") or resolution.get("reason") or "target_weight_authority_unavailable")
                    reasons.append(review_reason)
                    reasons.append("target_weight_authority_unavailable")
        total_target_weight = round(sum(float(item["target_weight"]) for item in positions), TARGET_WEIGHT_DECIMALS)
        sized_position_count = sum(1 for item in positions if item["sizing_status"] in {"SIZED", "CAPPED"})
        aggregate_tolerance = target_weight_sum_tolerance(sized_position_count)
        if target_exposure is not None and total_target_weight > target_exposure + aggregate_tolerance:
            status = "BLOCK"
            reasons.append("aggregate_target_weight_above_exposure_cap")
        if safety_cap is not None and any(float(item["target_weight"]) > safety_cap + 0.000001 for item in positions):
            status = "BLOCK"
            reasons.append("produced_position_weight_above_safety_cap")

    feature_date = min([s.feature_date for s in summaries.values() if s.feature_date] or [business_date])
    future = any(s.feature_date and s.feature_date > business_date for s in summaries.values())
    if future:
        status = "BLOCK"
        reasons.append("future_source_date_detected")
    source_hashes = [{"role": name, "path": s.source_ref, "sha256": _strip_sha256(s.source_hash)} for name, s in summaries.items()]
    if config:
        source_hashes.append({"role": "position_sizing_config", "path": config.config_source, "sha256": config_source_hash})

    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reasons)),
            decision_resolution="UNRESOLVED" if target_count_unresolved or target_exposure_unresolved or status != "PASS" else "RESOLVED",
        ),
        "sizing_method": config.sizing_method if config else "",
        "target_gross_exposure_ratio": None if target_exposure is None else round(target_exposure, 6),
        "target_gross_exposure_ratio_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "target_position_count": target_count,
        "target_position_count_resolution": numeric_resolution(target_count, unresolved=target_count is None),
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_total_equity": round(portfolio_value, 2),
        "minimum_meaningful_notional_policy": dict(config.minimum_meaningful_notional) if config else {},
        "strategy_maximum_position_weight": config.strategy_maximum_position_weight if config else None,
        "strategy_maximum_position_weight_source": f"{config.config_source}#strategy_maximum_position_weight" if config else "",
        "safety_maximum_position_weight": safety_cap,
        "safety_maximum_position_weight_source": safety_authority["safety_maximum_position_weight_source"],
        "safety_authority_status": safety_authority["safety_authority_status"],
        "effective_maximum_position_weight": effective_cap,
        "effective_maximum_position_weight_derivation": safety_authority["effective_maximum_position_weight_derivation"] if config else "position_sizing_config_missing",
        "explicit_zero_cap": safety_authority["explicit_zero_cap"],
        "emergency_brake_active": safety_authority["emergency_brake_active"],
        "market_context_risk_state": _extract_market_context_risk_state(dynamic_cash_exposure_summary),
        "dynamic_position_count": target_count,
        "dynamic_position_count_resolution": numeric_resolution(target_count, unresolved=target_count is None),
        "dynamic_cash_exposure": None if target_exposure is None else round(target_exposure, 6),
        "dynamic_cash_exposure_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "aggregate_exposure_cap": None if target_exposure is None else round(target_exposure, 6),
        "aggregate_exposure_cap_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "safety_authority_resolution": safety_authority,
        "positions": positions,
        "positions_sized": sum(1 for item in positions if item["sizing_status"] in {"SIZED", "CAPPED"}),
        "positions_withheld": sum(1 for item in positions if item["sizing_status"] not in {"SIZED", "CAPPED"}),
        "total_target_weight": round(sum(float(item["target_weight"]) for item in positions), TARGET_WEIGHT_DECIMALS),
        "target_weight_sum_tolerance": target_weight_sum_tolerance(
            sum(1 for item in positions if item["sizing_status"] in {"SIZED", "CAPPED"})
        ),
        "target_weight_precision": {
            "rounding_digits": TARGET_WEIGHT_DECIMALS,
            "tolerance_method": "max_absolute_or_half_rounding_unit_per_sized_position",
        },
        "residual_cash_ratio": round(max(1.0 - sum(float(item["target_weight"]) for item in positions), 0.0), TARGET_WEIGHT_DECIMALS),
        "concrete_target_weight_decided": status == "PASS",
        "target_notional_decided": status == "PASS",
        "share_quantity_decided": False,
        "lot_rounding_decided": False,
        "order_price_decided": False,
        "pending_decided": False,
        "submit_decided": False,
        "config_reference": config.config_source if config else "",
        "config_hash": f"sha256:{config_hash}" if config_hash else "",
        "config_payload": config_payload,
        "reason_codes": sorted(set(reasons)),
        "reason_code_contract": {
            "configured_max_position_weight_above_safety_cap": "Config maximum position weight exceeds the independent safety concentration cap before any position is produced.",
            "produced_position_weight_above_safety_cap": "At least one produced target position weight exceeds the independent safety concentration cap.",
            "aggregate_target_weight_above_exposure_cap": "Produced total target weight exceeds target gross exposure.",
            "missing_safety_maximum_position_weight_authority": "Safety concentration authority is missing and must not be represented as a zero cap.",
            "explicit_zero_safety_cap_without_authority": "A zero safety concentration cap requires explicit emergency or risk-off authority.",
        },
        "upstream_artifacts": {name: s.to_dict(requested_business_date=business_date) for name, s in summaries.items()},
        "source_artifacts": [{"role": name, "path": s.source_ref, "required": True, "status": s.status} for name, s in summaries.items()],
        "source_hashes": source_hashes,
        "temporal_safety": {"point_in_time": not future, "future_leakage_used": future, "feature_date_lte_business_date": feature_date <= business_date, "implicit_latest_fallback_used": False, "previous_day_position_sizing_copied": False},
        "shadow_comparison": {"legacy_max_position_weight": 0.20, "legacy_quantity_result": "downstream_runtime_authority_preserved", "would_change_buy_allocation": status == "PASS", "would_change_add_allocation": status == "PASS", "would_change_reduce_target": status == "PASS", "would_change_exit_target": status == "PASS", "runtime_behavior_changed": False},
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    return payload, {"schema_version": "phase22_j_position_sizing_evidence.v1", "producer_result_status": status, "reason_codes": payload["reason_codes"]}


def validate_position_sizing_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version","business_date","as_of","feature_date","artifact_lifecycle_status","source_authority_status","producer_result_status","runtime_consumer_eligibility","target_gross_exposure_ratio","target_position_count","positions","total_target_weight","residual_cash_ratio","concrete_target_weight_decided","target_notional_decided","share_quantity_decided","lot_rounding_decided","source_artifacts","source_hashes","temporal_safety","strategy_maximum_position_weight","strategy_maximum_position_weight_source","safety_maximum_position_weight","safety_maximum_position_weight_source","safety_authority_status","effective_maximum_position_weight","effective_maximum_position_weight_derivation","explicit_zero_cap","emergency_brake_active","market_context_risk_state","dynamic_position_count","dynamic_cash_exposure","aggregate_exposure_cap"}
    errors = [f"required_field_missing:{f}" for f in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported_schema_version")
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS: errors.append("artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY: errors.append("runtime_consumer_eligibility_must_be_not_eligible")
    target_unresolved = (
        payload.get("target_gross_exposure_ratio_resolution") == "UNRESOLVED"
        or payload.get("target_position_count_resolution") == "UNRESOLVED"
    )
    target_exposure = None if target_unresolved and payload.get("target_gross_exposure_ratio") is None else _ratio_field(errors, payload, "target_gross_exposure_ratio")
    total = _ratio_field(errors, payload, "total_target_weight")
    positions = payload.get("positions")
    sized_count = 0
    if isinstance(positions, list):
        sized_count = sum(
            1
            for position in positions
            if isinstance(position, dict) and position.get("sizing_status") in {"SIZED", "CAPPED"}
        )
    aggregate_tolerance = target_weight_sum_tolerance(sized_count)
    if target_exposure is not None and total is not None and total > target_exposure + aggregate_tolerance:
        errors.append("aggregate_target_weight_above_exposure_cap")
    safety_cap = _optional_ratio_field(errors, payload, "safety_maximum_position_weight")
    _optional_ratio_field(errors, payload, "effective_maximum_position_weight")
    if payload.get("safety_authority_status") not in {"PASS", "REVIEW_REQUIRED", "BLOCK"}:
        errors.append("invalid_safety_authority_status")
    if safety_cap is None and payload.get("safety_authority_status") == "PASS":
        errors.append("safety_cap_required_when_authority_pass")
    if safety_cap == 0 and payload.get("explicit_zero_cap") is not True:
        errors.append("zero_safety_cap_requires_explicit_zero_cap")
    if safety_cap == 0.20:
        errors.append("legacy_0_20_implicit_safety_concentration_forbidden")
    if target_unresolved:
        for field in ("target_position_count", "dynamic_position_count"):
            if payload.get(field) is not None:
                errors.append(f"unresolved_count_must_be_null:{field}")
        for field in ("dynamic_cash_exposure", "aggregate_exposure_cap"):
            if payload.get(field) is not None:
                errors.append(f"unresolved_ratio_must_be_null:{field}")
    if not isinstance(positions, list):
        errors.append("positions_not_list")
    else:
        for index, position in enumerate(positions):
            errors.extend(_validate_position(position, index=index, safety_cap=safety_cap))
    for field in sorted(FORBIDDEN_FIELDS & set(payload)):
        errors.append(f"quantity_or_runtime_field_forbidden:{field}")
    for field in ("share_quantity_decided","lot_rounding_decided","order_price_decided","pending_decided","submit_decided","production_consumer_connected","runtime_switch_performed"):
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
    temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), dict) else {}
    if temporal.get("implicit_latest_fallback_used") is not False: errors.append("implicit_latest_fallback_forbidden")
    if temporal.get("previous_day_position_sizing_copied") is not False: errors.append("previous_day_copy_forbidden")
    if errors:
        raise PositionSizingSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    for item in payload.get("source_hashes") or []:
        path = Path(str(item.get("path") or ""))
        if path.is_file() and sha256_file(path) != _strip_sha256(str(item.get("sha256") or "")):
            mismatches.append(str(path))
    return {"status": "BLOCK" if mismatches else "PASS", "mismatches": mismatches}


def load_position_sizing_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_position_sizing_artifact(payload)
    if for_production:
        raise PositionSizingConsumerError("Phase22-J Position Sizing is not production-consumable")
    return payload


def position_sizing_hash(payload: dict[str, Any]) -> str:
    return stable_payload_hash({k: v for k, v in payload.items() if k != "artifact_hash"})


def stable_payload_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _size_positions(*, config: PositionSizingConfig, rows: tuple[Mapping[str, Any], ...], target_count: int, target_exposure: float, portfolio_value: float, safety_cap: float) -> tuple[list[dict[str, Any]], list[str]]:
    if target_count <= 0 or target_exposure <= 0:
        return (
            [
                _zero_allocation_position(
                    row,
                    config=config,
                    safety_cap=safety_cap,
                    reason="actual_target_position_count_zero" if target_count <= 0 else "target_gross_exposure_zero",
                )
                for row in rows
            ],
            [],
        )
    base = target_exposure / float(target_count)
    raw: list[dict[str, Any]] = []
    reasons: list[str] = []
    max_weight = min(config.strategy_maximum_position_weight, safety_cap)
    for row in rows:
        item = _raw_position(row, config=config, base=base, max_weight=max_weight, portfolio_value=portfolio_value)
        raw.append(item)
    active_total = sum(float(item["capped_weight"]) for item in raw if item["sizing_status"] in {"SIZED", "CAPPED"})
    scale = min(1.0, target_exposure / active_total) if active_total > 0 else 0.0
    positions = []
    for item in raw:
        if item["sizing_status"] in {"SIZED", "CAPPED"}:
            target_weight = round(float(item["capped_weight"]) * scale, 6)
            target_notional = round(target_weight * portfolio_value, 2)
            min_notional = float(item["minimum_meaningful_notional"])
            current_notional = round(float(item["current_weight"]) * portfolio_value, 2)
            incremental = round(target_notional - current_notional, 2)
            if 0 < target_notional < min_notional:
                item = {
                    **item,
                    "target_weight": target_weight,
                    "weight_delta": round(target_weight - float(item["current_weight"]), 6),
                    "target_notional": target_notional,
                    "current_notional": current_notional,
                    "incremental_target_notional": incremental,
                    "incremental_buy_notional": 0.0,
                    "target_quantity_candidate": 0,
                    "quantity_delta_candidate": int(0 - float(item["current_quantity"])),
                    "quantity_status": "NO_ORDER_MINIMUM_NOTIONAL_UNMET",
                    "sizing_status": "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
                    "uncertainty": "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
                    "reason_codes": sorted(set(item["reason_codes"] + ["minimum_meaningful_notional_unmet"])),
                }
            else:
                item = {**item, "target_weight": target_weight, "weight_delta": round(target_weight - float(item["current_weight"]), 6), "target_notional": target_notional, "current_notional": current_notional, "incremental_target_notional": incremental, "incremental_buy_notional": round(max(incremental, 0.0), 2)}
        positions.append(item)
    return positions, reasons


def _zero_allocation_position(row: Mapping[str, Any], *, config: PositionSizingConfig, safety_cap: float, reason: str) -> dict[str, Any]:
    base = _raw_position(row, config=config, base=0.0, max_weight=min(config.strategy_maximum_position_weight, safety_cap), portfolio_value=0.0)
    return {
        **base,
        "base_weight": 0.0,
        "quality_adjustment": 0.0,
        "volatility_adjustment": 0.0,
        "pm_intent_adjustment": 0.0,
        "adjusted_weight": 0.0,
        "capped_weight": 0.0,
        "target_weight": 0.0,
        "weight_delta": round(0.0 - float(base["current_weight"]), 6),
        "target_notional": 0.0,
        "current_notional": 0.0,
        "incremental_target_notional": 0.0,
        "incremental_buy_notional": 0.0,
        "sizing_status": "RESOLVED_ZERO_ALLOCATION",
        "uncertainty": "RESOLVED_ZERO_ALLOCATION",
        "reason_codes": sorted(set([reason, "zero_allocation_authorized"])),
    }


def _raw_position(row: Mapping[str, Any], *, config: PositionSizingConfig, base: float, max_weight: float, portfolio_value: float) -> dict[str, Any]:
    code = str(row.get("security_code") or row.get("symbol") or "")
    membership = str(row.get("membership_intent") or "UNRESOLVED").upper()
    pm_action = str(row.get("pm_action") or ("NEW" if membership == "ADD_CANDIDATE" else "HOLD")).upper()
    if pm_action not in PM_ACTIONS:
        pm_action = "UNRESOLVED"
    current_weight = _ratio(row.get("current_weight"), 0.0)
    target_weight_resolution = resolve_target_weight(row)
    runtime_opportunity_resolution = resolve_runtime_opportunity_score(row)
    quality_resolution = resolve_quality_score(row)
    quality = 1.0
    vol = _volatility_multiplier(row, config)
    reasons = [f"pm_action:{pm_action}", f"membership_intent:{membership}"]
    status = "SIZED"
    uncertainty = "LOW"
    target = target_weight_resolution["resolved_weight"]
    if target_weight_resolution["status"] != "PASS":
        target = 0.0
        status = "TARGET_WEIGHT_UNAVAILABLE"
        uncertainty = "TARGET_WEIGHT_UNAVAILABLE"
        reasons.append("target_weight_missing_fail_closed")
        reasons.append(str(target_weight_resolution["review_reason"]))
    if vol is None:
        vol = 1.0
        reasons.append("volatility_missing_noncanonical_observability")
    adjusted = target
    if pm_action == "EXIT" or membership in {"REMOVE_CANDIDATE", "EXCLUDE"}:
        adjusted = 0.0
    elif pm_action == "REDUCE":
        adjusted = min(adjusted, current_weight * 0.5)
    capped = min(max(adjusted, 0.0), max_weight)
    if capped < adjusted:
        status = "CAPPED"
        reasons.append("position_concentration_cap_applied")
    reference_price_resolution = resolve_reference_price(row)
    price = _positive_float(reference_price_resolution["resolved_price"], 0.0)
    min_notional = _minimum_notional(config, price)
    target = round(capped, 6) if status in {"SIZED", "CAPPED"} else 0.0
    current_quantity = _positive_float(row.get("current_quantity"), 0.0)
    trading_unit = _positive_float(row.get("trading_unit"), _positive_float(config.minimum_meaningful_notional.get("tradable_unit"), 100.0))
    target_notional = round(target * portfolio_value, 2)
    target_quantity_candidate = 0
    price_required = target_notional > 0
    quantity_status = "RESOLVED_ZERO_DELTA" if current_quantity == 0 else "RESOLVED_CANDIDATE"
    if price_required and reference_price_resolution["status"] != "PASS":
        quantity_status = "PRICE_UNAVAILABLE"
        reasons.append(str(reference_price_resolution["review_reason"] or "reference_price_unavailable"))
    elif price_required and price > 0 and trading_unit > 0:
        raw_quantity = int(target_notional // (price * trading_unit)) * int(trading_unit)
        target_quantity_candidate = max(raw_quantity, 0)
        quantity_status = "RESOLVED_ZERO_DELTA" if target_quantity_candidate == current_quantity else "RESOLVED_CANDIDATE"
    if status in {"SIZED", "CAPPED"} and 0 < target_notional < min_notional:
        status = "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
        uncertainty = "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
        reasons.append("minimum_meaningful_notional_unmet")
        target_quantity_candidate = 0
        quantity_status = "NO_ORDER_MINIMUM_NOTIONAL_UNMET"
    quantity_delta_candidate = int(target_quantity_candidate - current_quantity)
    return {
        "security_code": code,
        "position_reference": str(row.get("position_reference") or row.get("member_id") or code),
        "membership_intent": membership,
        "pm_action": pm_action,
        "current_weight": round(current_weight, 6),
        "base_weight": round(base, 6),
        "quality_adjustment": round(quality, 6),
        "volatility_adjustment": round(vol, 6),
        "pm_intent_adjustment": round(float(config.pm_intent_adjustment.get(pm_action, 1.0)), 6),
        "adjusted_weight": round(max(adjusted, 0.0), 6),
        "capped_weight": round(capped, 6),
        "target_weight": target,
        "weight_delta": round(target - current_weight, 6),
        "target_notional": target_notional if status != "TARGET_WEIGHT_UNAVAILABLE" else 0.0,
        "current_notional": round(current_weight * portfolio_value, 2),
        "incremental_target_notional": round((target - current_weight) * portfolio_value, 2),
        "incremental_buy_notional": round(max((target - current_weight) * portfolio_value, 0.0), 2),
        "target_weight_authority": dict(row.get("target_weight_authority") or {}),
        "target_weight_resolution": dict(target_weight_resolution),
        "target_quantity_candidate": target_quantity_candidate,
        "current_quantity": int(current_quantity),
        "quantity_delta_candidate": quantity_delta_candidate,
        "quantity_status": quantity_status,
        "reference_price": price if reference_price_resolution["status"] == "PASS" else None,
        "reference_price_authority": dict(row.get("reference_price_authority") or {}),
        "reference_price_resolution": reference_price_resolution,
        "reference_price_required": price_required,
        "reference_price_type": str(row.get("reference_price_type") or ""),
        "reference_price_date": str(row.get("reference_price_date") or ""),
        "trading_unit": int(trading_unit),
        "trading_unit_authority": str(row.get("trading_unit_authority") or config.config_source + "#minimum_meaningful_notional.tradable_unit"),
        "sizing_reason": ";".join(sorted(set(reasons))),
        "minimum_meaningful_notional": round(min_notional, 2),
        "maximum_position_weight": round(max_weight, 6),
        "sizing_priority": _positive_int(row.get("allocation_priority") or row.get("construction_priority"), 999),
        "sizing_status": status,
        "opportunity_buy_rank": _int_or_none(row.get("opportunity_buy_rank", row.get("input_opportunity_rank"))),
        "input_opportunity_rank": _int_or_none(row.get("input_opportunity_rank", row.get("opportunity_buy_rank"))),
        "rank_authority_status": str(row.get("rank_authority_status") or ""),
        "rank_authority": str(row.get("rank_authority") or row.get("input_opportunity_rank_authority") or ""),
        "rank_authority_field": str(row.get("rank_authority_field") or ""),
        "rank_authority_reason": str(row.get("rank_authority_reason") or ""),
        "opportunity_row_id": str(row.get("opportunity_row_id") or row.get("input_opportunity_row_id") or ""),
        "opportunity_row_authority_hash": str(row.get("opportunity_row_authority_hash") or row.get("input_opportunity_row_authority_hash") or ""),
        "opportunity_artifact_path": str(row.get("opportunity_artifact_path") or row.get("input_opportunity_rank_source_path") or ""),
        "opportunity_artifact_hash": str(row.get("opportunity_artifact_hash") or row.get("input_opportunity_rank_source_hash") or ""),
        "runtime_opportunity_score": runtime_opportunity_resolution.resolved_score,
        "runtime_opportunity_score_authority": runtime_opportunity_resolution.authority,
        "runtime_opportunity_score_resolution": runtime_opportunity_resolution.to_dict(),
        "allocation_quality_score": quality_resolution.resolved_quality,
        "allocation_quality_authority": quality_resolution.authority,
        "allocation_quality_resolution": quality_resolution.to_dict(),
        "legacy_quality_path_status": "NON_CANONICAL_OBSERVABILITY",
        "quality_score": quality_resolution.resolved_quality,
        "quality_authority": quality_resolution.authority,
        "quality_resolution": quality_resolution.to_dict(),
        "confidence": round(min(_ratio(row.get("confidence"), 1.0), _ratio(row.get("opportunity_confidence"), 1.0)), 6),
        "uncertainty": uncertainty,
        "reason_codes": sorted(set(reasons)),
    }


def _unresolved_position(row: Mapping[str, Any], *, config: PositionSizingConfig | None, safety_cap: float | None) -> dict[str, Any]:
    max_weight = min(config.strategy_maximum_position_weight, safety_cap) if config and safety_cap is not None else safety_cap or 0.0
    current_weight = _ratio(row.get("current_weight"), 0.0)
    return {
        "security_code": str(row.get("security_code") or row.get("symbol") or ""),
        "position_reference": str(row.get("position_reference") or row.get("member_id") or row.get("security_code") or ""),
        "membership_intent": str(row.get("membership_intent") or "UNRESOLVED").upper(),
        "pm_action": str(row.get("pm_action") or "UNRESOLVED").upper(),
        "current_weight": round(current_weight, 6),
        "base_weight": 0.0,
        "quality_adjustment": 0.0,
        "volatility_adjustment": 0.0,
        "pm_intent_adjustment": 0.0,
        "adjusted_weight": 0.0,
        "capped_weight": 0.0,
        "target_weight": 0.0,
        "weight_delta": round(0.0 - current_weight, 6),
        "target_notional": 0.0,
        "current_notional": 0.0,
        "incremental_target_notional": 0.0,
        "incremental_buy_notional": 0.0,
        "minimum_meaningful_notional": 0.0,
        "maximum_position_weight": round(max_weight, 6),
        "sizing_priority": _positive_int(row.get("allocation_priority") or row.get("construction_priority"), 999),
        "sizing_status": "UPSTREAM_REVIEW_REQUIRED",
        "confidence": 0.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": ["upstream_review_required"],
    }


def _capital_deployment_shadow_cycle_placeholder(name: str, summary: PositionSizingSourceSummary) -> bool:
    if name != "capital_deployment" or summary.status == "PASS":
        return False
    return str((summary.summary or {}).get("reason") or "") == "capital_deployment_is_downstream_of_position_sizing_in_shadow_chain"


def resolve_quality_score(row: Mapping[str, Any]) -> QualityResolution:
    return resolve_allocation_quality_score(row)


def resolve_target_weight(row: Mapping[str, Any]) -> dict[str, Any]:
    value = row.get("target_weight")
    authority = row.get("target_weight_authority")
    resolution = row.get("target_weight_resolution")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "target_weight_invalid",
            "resolved_weight": 0.0,
            "base_weight": 0.0,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "unresolved_authority",
            "review_reason": "target_weight_invalid",
        }
    if not isinstance(authority, Mapping) or authority.get("authority_type") != "TARGET_WEIGHT_AUTHORITY":
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "target_weight_authority_missing",
            "resolved_weight": 0.0,
            "base_weight": 0.0,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "unresolved_authority",
            "review_reason": "target_weight_authority_missing",
        }
    if not isinstance(resolution, Mapping) or resolution.get("status") not in {"PASS", "REVIEW_REQUIRED"}:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "target_weight_resolution_missing",
            "resolved_weight": 0.0,
            "base_weight": 0.0,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "unresolved_authority",
            "review_reason": "target_weight_resolution_missing",
        }
    if resolution.get("status") != "PASS":
        return {**dict(resolution), "resolved_weight": 0.0, "review_reason": resolution.get("review_reason") or resolution.get("reason") or "target_weight_review_required"}
    resolved = round(float(value), 8)
    return {
        **dict(resolution),
        "status": "PASS",
        "resolved_weight": resolved,
        "review_reason": "",
    }


def resolve_reference_price(row: Mapping[str, Any]) -> dict[str, Any]:
    value = row.get("reference_price")
    authority = row.get("reference_price_authority")
    resolution = row.get("reference_price_resolution")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "reference_price_missing_or_invalid",
            "resolved_price": None,
            "source_field": "",
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "review_reason": "reference_price_missing_or_invalid",
            "latest_fallback_used": False,
        }
    if not isinstance(authority, Mapping) or authority.get("authority_type") != REFERENCE_PRICE_AUTHORITY:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "reference_price_authority_missing",
            "resolved_price": None,
            "source_field": "",
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "review_reason": "reference_price_authority_missing",
            "latest_fallback_used": False,
        }
    if authority.get("latest_fallback_used") is True:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "reference_price_latest_fallback_forbidden",
            "resolved_price": None,
            "source_field": str(authority.get("source_field") or ""),
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "review_reason": "reference_price_latest_fallback_forbidden",
            "latest_fallback_used": True,
        }
    if str(authority.get("PIT_status") or "") == "BLOCK":
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "reference_price_pit_invalid",
            "resolved_price": None,
            "source_field": str(authority.get("source_field") or ""),
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "review_reason": "reference_price_pit_invalid",
            "latest_fallback_used": False,
        }
    if isinstance(resolution, Mapping) and resolution.get("status") not in {"PASS", "REVIEW_REQUIRED"}:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "reference_price_resolution_invalid",
            "resolved_price": None,
            "source_field": str(authority.get("source_field") or ""),
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "review_reason": "reference_price_resolution_invalid",
            "latest_fallback_used": False,
        }
    if isinstance(resolution, Mapping) and resolution.get("status") == "REVIEW_REQUIRED":
        return {
            **dict(resolution),
            "status": "REVIEW_REQUIRED",
            "resolved_price": None,
            "authority_type": REFERENCE_PRICE_AUTHORITY,
            "review_reason": resolution.get("review_reason") or resolution.get("reason") or "reference_price_review_required",
            "latest_fallback_used": False,
        }
    return {
        "status": "PASS",
        "reason": "reference_price_resolved",
        "resolved_price": round(float(value), 10),
        "source_field": str(authority.get("source_field") or "reference_price"),
        "authority_type": REFERENCE_PRICE_AUTHORITY,
        "source_authority": str(authority.get("source_authority") or ""),
        "source_path": str(authority.get("source_path") or ""),
        "source_hash": str(authority.get("source_hash") or ""),
        "price_type": str(authority.get("price_type") or row.get("reference_price_type") or ""),
        "price_date": str(authority.get("price_date") or row.get("reference_price_date") or ""),
        "review_reason": "",
        "latest_fallback_used": False,
    }


def resolve_runtime_opportunity_score(row: Mapping[str, Any]) -> RuntimeOpportunityScoreResolution:
    fields: dict[str, float] = {}
    invalid: list[str] = []
    for field in (RAW_OPPORTUNITY_CANONICAL_FIELD, *RAW_OPPORTUNITY_LEGACY_FIELDS):
        if field not in row:
            continue
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            invalid.append(field)
            continue
        fields[field] = float(value)
    authority_payload = row.get("runtime_opportunity_score_authority")
    lineage = dict(authority_payload) if isinstance(authority_payload, Mapping) else {}
    source_decision_id = str(
        lineage.get("source_decision_id")
        or row.get("opportunity_reference")
        or row.get("candidate_reference")
        or row.get("position_reference")
        or row.get("member_id")
        or row.get("security_code")
        or ""
    )
    source_artifact_class = str(
        lineage.get("source_artifact_class")
        or ("opportunity" if row.get("opportunity_reference") else ("candidate" if row.get("candidate_reference") else ""))
    )
    if invalid:
        return RuntimeOpportunityScoreResolution(
            resolved_score=None,
            authority=RAW_OPPORTUNITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=RAW_OPPORTUNITY_CANONICAL_FIELD,
            legacy_attribution_used=False,
            review_reason="runtime_opportunity_score_invalid:" + ",".join(sorted(invalid)),
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=False,
        )
    if not fields:
        return RuntimeOpportunityScoreResolution(
            resolved_score=None,
            authority=RAW_OPPORTUNITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=RAW_OPPORTUNITY_CANONICAL_FIELD,
            legacy_attribution_used=False,
            review_reason="runtime_opportunity_score_missing",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed={},
            conflict_detected=False,
        )
    if RAW_OPPORTUNITY_CANONICAL_FIELD in fields and not lineage:
        return RuntimeOpportunityScoreResolution(
            resolved_score=None,
            authority=RAW_OPPORTUNITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=RAW_OPPORTUNITY_CANONICAL_FIELD,
            legacy_attribution_used=False,
            review_reason="runtime_opportunity_score_authority_missing",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=False,
        )
    semantics = str(lineage.get("prediction_semantics") or lineage.get("semantics") or "")
    if RAW_OPPORTUNITY_CANONICAL_FIELD in fields and semantics and semantics != "runtime_opportunity_score":
        return RuntimeOpportunityScoreResolution(
            resolved_score=None,
            authority=RAW_OPPORTUNITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=RAW_OPPORTUNITY_CANONICAL_FIELD,
            legacy_attribution_used=False,
            review_reason="runtime_opportunity_score_semantic_conflict",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=True,
        )
    unique_values = {round(value, 12) for value in fields.values()}
    if len(unique_values) > 1:
        return RuntimeOpportunityScoreResolution(
            resolved_score=None,
            authority=RAW_OPPORTUNITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=RAW_OPPORTUNITY_CANONICAL_FIELD,
            legacy_attribution_used=RAW_OPPORTUNITY_CANONICAL_FIELD not in fields,
            review_reason="runtime_opportunity_score_field_conflict",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=True,
        )
    source_field = RAW_OPPORTUNITY_CANONICAL_FIELD if RAW_OPPORTUNITY_CANONICAL_FIELD in fields else next(field for field in RAW_OPPORTUNITY_LEGACY_FIELDS if field in fields)
    return RuntimeOpportunityScoreResolution(
        resolved_score=round(fields[source_field], 8),
        authority=RAW_OPPORTUNITY_AUTHORITY,
        resolution_status="PASS",
        source_field=source_field,
        canonical_field=RAW_OPPORTUNITY_CANONICAL_FIELD,
        legacy_attribution_used=source_field != RAW_OPPORTUNITY_CANONICAL_FIELD,
        review_reason="",
        source_decision_id=source_decision_id,
        source_artifact_class=source_artifact_class,
        lineage=lineage,
        fields_observed=fields,
        conflict_detected=False,
    )


def resolve_allocation_quality_score(row: Mapping[str, Any]) -> QualityResolution:
    fields: dict[str, float] = {}
    invalid: list[str] = []
    for field in (ALLOCATION_QUALITY_CANONICAL_FIELD, ALLOCATION_QUALITY_LEGACY_FIELD):
        if field not in row:
            continue
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
            invalid.append(field)
            continue
        fields[field] = float(value)
    authority_payload = row.get("allocation_quality_authority")
    if not isinstance(authority_payload, Mapping) and ALLOCATION_QUALITY_LEGACY_FIELD in fields:
        authority_payload = row.get("quality_score_authority")
    lineage = dict(authority_payload) if isinstance(authority_payload, Mapping) else {}
    source_decision_id = str(
        lineage.get("source_decision_id")
        or row.get("opportunity_reference")
        or row.get("candidate_reference")
        or row.get("position_reference")
        or row.get("member_id")
        or row.get("security_code")
        or ""
    )
    source_artifact_class = str(
        lineage.get("source_artifact_class")
        or ("opportunity" if row.get("opportunity_reference") else ("candidate" if row.get("candidate_reference") else ""))
    )
    if invalid:
        return QualityResolution(
            resolved_quality=None,
            authority=ALLOCATION_QUALITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=ALLOCATION_QUALITY_CANONICAL_FIELD,
            legacy_alias_used=False,
            review_reason="allocation_quality_score_invalid:" + ",".join(sorted(invalid)),
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=False,
            legacy_usage="",
        )
    if not fields:
        legacy_raw = [field for field in RAW_OPPORTUNITY_LEGACY_FIELDS if field in row]
        return QualityResolution(
            resolved_quality=None,
            authority=ALLOCATION_QUALITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=ALLOCATION_QUALITY_CANONICAL_FIELD,
            legacy_alias_used=False,
            review_reason="allocation_quality_score_missing",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed={},
            conflict_detected=False,
            legacy_usage="raw_attribution_only:" + ",".join(legacy_raw) if legacy_raw else "",
        )
    if not lineage:
        return QualityResolution(
            resolved_quality=None,
            authority=ALLOCATION_QUALITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=ALLOCATION_QUALITY_CANONICAL_FIELD,
            legacy_alias_used=False,
            review_reason="allocation_quality_authority_missing",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=False,
            legacy_usage="",
        )
    semantics = str(lineage.get("output_semantics") or lineage.get("semantics") or "")
    if semantics and semantics != "allocation_quality_score":
        return QualityResolution(
            resolved_quality=None,
            authority=ALLOCATION_QUALITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=ALLOCATION_QUALITY_CANONICAL_FIELD,
            legacy_alias_used=False,
            review_reason="allocation_quality_semantic_conflict",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=True,
            legacy_usage="",
        )
    unique_values = {round(value, 12) for value in fields.values()}
    if len(unique_values) > 1:
        return QualityResolution(
            resolved_quality=None,
            authority=ALLOCATION_QUALITY_AUTHORITY,
            resolution_status="REVIEW_REQUIRED",
            source_field="",
            canonical_field=ALLOCATION_QUALITY_CANONICAL_FIELD,
            legacy_alias_used=ALLOCATION_QUALITY_CANONICAL_FIELD not in fields,
            review_reason="allocation_quality_score_field_conflict",
            source_decision_id=source_decision_id,
            source_artifact_class=source_artifact_class,
            lineage=lineage,
            fields_observed=fields,
            conflict_detected=True,
            legacy_usage="legacy_quality_score" if ALLOCATION_QUALITY_LEGACY_FIELD in fields else "",
        )
    source_field = ALLOCATION_QUALITY_CANONICAL_FIELD if ALLOCATION_QUALITY_CANONICAL_FIELD in fields else ALLOCATION_QUALITY_LEGACY_FIELD
    return QualityResolution(
        resolved_quality=round(fields[source_field], 8),
        authority=ALLOCATION_QUALITY_AUTHORITY,
        resolution_status="PASS",
        source_field=source_field,
        canonical_field=ALLOCATION_QUALITY_CANONICAL_FIELD,
        legacy_alias_used=source_field != ALLOCATION_QUALITY_CANONICAL_FIELD,
        review_reason="",
        source_decision_id=source_decision_id,
        source_artifact_class=source_artifact_class,
        lineage=lineage,
        fields_observed=fields,
        conflict_detected=False,
        legacy_usage="legacy_quality_score" if source_field == ALLOCATION_QUALITY_LEGACY_FIELD else "",
    )


def _quality_multiplier(resolution: QualityResolution, config: PositionSizingConfig) -> float | None:
    score = resolution.resolved_quality
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    adj = config.opportunity_adjustment
    lo = float(adj["score_min"]); hi = float(adj["score_max"])
    if hi <= lo:
        raise PositionSizingConfigError("invalid score range")
    normalized = min(max((float(score) - lo) / (hi - lo), 0.0), 1.0)
    multiplier = 1.0 + (normalized - 0.5) * float(adj["quality_multiplier_strength"])
    return min(max(multiplier, float(adj["minimum_multiplier"])), float(adj["maximum_multiplier"]))


def _volatility_multiplier(row: Mapping[str, Any], config: PositionSizingConfig) -> float | None:
    value = row.get("volatility")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
        return None
    adj = config.volatility_adjustment
    vol = min(max(float(value), float(adj["minimum_volatility"])), float(adj["maximum_volatility"]))
    multiplier = float(adj["reference_volatility"]) / vol
    return min(max(multiplier, float(adj["minimum_multiplier"])), float(adj["maximum_multiplier"]))


def _minimum_notional(config: PositionSizingConfig, price: float) -> float:
    policy = config.minimum_meaningful_notional
    base = _positive_float(policy.get("base_jpy"), 0.0)
    unit = _positive_float(policy.get("tradable_unit"), 100.0)
    buffer = _ratio(policy.get("price_buffer_ratio"), 0.0)
    round_lot_notional = price * unit * (1.0 + buffer) if price > 0 else 0.0
    return max(base, round_lot_notional)


def _resolve_safety_maximum_position_weight(safety_limit_summary: PositionSizingSourceSummary) -> dict[str, Any]:
    summary = dict(safety_limit_summary.summary or {})
    status = "PASS" if safety_limit_summary.status == "PASS" else "REVIEW_REQUIRED"
    reason = "safety_maximum_position_weight_resolved"
    source = ""
    value: Any = None
    if "maximum_position_weight" in summary:
        value = summary.get("maximum_position_weight")
        source = f"{safety_limit_summary.source_ref}#maximum_position_weight"
    else:
        concentration = summary.get("concentration")
        if isinstance(concentration, Mapping) and "maximum_position_weight" in concentration:
            value = concentration.get("maximum_position_weight")
            source = f"{safety_limit_summary.source_ref}#concentration.maximum_position_weight"
    explicit_zero = bool(summary.get("explicit_zero_cap") or summary.get("emergency_brake_active") or summary.get("hard_risk_off_active"))
    emergency = bool(summary.get("emergency_brake_active") or summary.get("hard_risk_off_active"))
    if value is None:
        return {
            "safety_authority_status": "REVIEW_REQUIRED" if safety_limit_summary.status != "PASS" else "BLOCK",
            "reason_code": "safety_concentration_limit_review_required" if safety_limit_summary.status != "PASS" else "missing_safety_maximum_position_weight_authority",
            "safety_maximum_position_weight": None,
            "safety_maximum_position_weight_source": source,
            "explicit_zero_cap": explicit_zero,
            "emergency_brake_active": emergency,
            "effective_maximum_position_weight_derivation": "missing_safety_authority_no_effective_cap",
        }
    try:
        cap = _ratio(value, None)
    except PositionSizingConfigError:
        return {
            "safety_authority_status": "BLOCK",
            "reason_code": "invalid_safety_maximum_position_weight_authority",
            "safety_maximum_position_weight": None,
            "safety_maximum_position_weight_source": source,
            "explicit_zero_cap": explicit_zero,
            "emergency_brake_active": emergency,
            "effective_maximum_position_weight_derivation": "invalid_safety_authority_no_effective_cap",
        }
    if cap == 0.0 and not explicit_zero:
        status = "BLOCK"
        reason = "explicit_zero_safety_cap_without_authority"
    return {
        "safety_authority_status": status,
        "reason_code": reason,
        "safety_maximum_position_weight": cap,
        "safety_maximum_position_weight_source": source,
        "explicit_zero_cap": cap == 0.0 and explicit_zero,
        "emergency_brake_active": emergency,
        "effective_maximum_position_weight_derivation": "min(strategy_maximum_position_weight, safety_maximum_position_weight)",
    }


def _extract_market_context_risk_state(dynamic_cash_exposure_summary: PositionSizingSourceSummary) -> str:
    summary = dynamic_cash_exposure_summary.summary or {}
    for key in ("market_context_risk_state", "risk_state", "risk_posture", "market_regime"):
        value = summary.get(key)
        if isinstance(value, str) and value:
            return value
    return "UNRESOLVED"


def _rows_with_price_volatility(
    rows: tuple[Mapping[str, Any], ...],
    price_volatility_summary: PositionSizingSourceSummary,
) -> tuple[Mapping[str, Any], ...]:
    if not rows or price_volatility_summary.status != "PASS":
        return rows
    price_inputs_by_code: dict[str, dict[str, Any]] = {}
    for row in price_volatility_summary.rows:
        if not isinstance(row, Mapping):
            continue
        code = str(row.get("symbol") or row.get("code") or row.get("security_code") or "")
        if not code:
            continue
        payload: dict[str, Any] = {}
        value = row.get("volatility_value", row.get("volatility_return_std_20d"))
        if not isinstance(value, bool) and isinstance(value, (int, float)) and float(value) > 0:
            payload["volatility"] = float(value)
            payload["volatility_source"] = price_volatility_summary.source_ref
        price = row.get("reference_price")
        if not isinstance(price, bool) and isinstance(price, (int, float)) and math.isfinite(float(price)) and float(price) > 0:
            payload["reference_price"] = float(price)
            payload["reference_price_source"] = price_volatility_summary.source_ref
            for field in ("reference_price_authority", "reference_price_resolution", "reference_price_type", "reference_price_date"):
                if field in row:
                    payload[field] = row.get(field)
        if payload:
            price_inputs_by_code[code] = payload
    if not price_inputs_by_code:
        return rows
    enriched: list[Mapping[str, Any]] = []
    for row in rows:
        code = str(row.get("security_code") or row.get("symbol") or row.get("code") or "")
        if code not in price_inputs_by_code:
            enriched.append(row)
            continue
        updates = {}
        for key, value in price_inputs_by_code[code].items():
            if key in {"volatility", "reference_price"} and row.get(key) not in (None, ""):
                continue
            if key.endswith("_authority") and isinstance(row.get(key), Mapping):
                continue
            if key.endswith("_resolution") and isinstance(row.get(key), Mapping):
                continue
            if key in {"reference_price_type", "reference_price_date", "reference_price_source", "volatility_source"} and row.get(key) not in (None, ""):
                continue
            updates[key] = value
        enriched.append({**dict(row), **updates} if updates else row)
    return tuple(enriched)


def _validate_position(position: Any, *, index: int, safety_cap: float | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(position, dict):
        return [f"position_not_object:{index}"]
    required = {"security_code","membership_intent","pm_action","current_weight","base_weight","quality_adjustment","volatility_adjustment","adjusted_weight","capped_weight","target_weight","weight_delta","target_notional","current_notional","incremental_target_notional","incremental_buy_notional","minimum_meaningful_notional","maximum_position_weight","sizing_status","confidence","uncertainty","reason_codes"}
    errors.extend(f"position_required_field_missing:{index}:{f}" for f in sorted(required - set(position)))
    if position.get("sizing_status") not in SIZING_STATUSES:
        errors.append(f"invalid_sizing_status:{index}")
    for field in ("current_weight","base_weight","adjusted_weight","capped_weight","target_weight","maximum_position_weight","confidence"):
        _ratio_field(errors, position, field, prefix=f"position:{index}:")
    for field in ("quality_adjustment","volatility_adjustment","pm_intent_adjustment"):
        value = position.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 10:
            errors.append(f"invalid_multiplier:position:{index}:{field}")
    for field in ("quality_score", "allocation_quality_score"):
        if field in position:
            quality_score = position.get(field)
            if quality_score is not None and (
                isinstance(quality_score, bool)
                or not isinstance(quality_score, (int, float))
                or not math.isfinite(float(quality_score))
                or not 0 <= float(quality_score) <= 1
            ):
                errors.append(f"invalid_{field}:position:{index}")
    if "runtime_opportunity_score" in position:
        raw_score = position.get("runtime_opportunity_score")
        if raw_score is not None and (isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)) or not math.isfinite(float(raw_score))):
            errors.append(f"invalid_runtime_opportunity_score:position:{index}")
    if "quality_authority" in position and position.get("quality_authority") != ALLOCATION_QUALITY_AUTHORITY:
        errors.append(f"invalid_quality_authority:position:{index}")
    if "allocation_quality_authority" in position and position.get("allocation_quality_authority") != ALLOCATION_QUALITY_AUTHORITY:
        errors.append(f"invalid_allocation_quality_authority:position:{index}")
    if "runtime_opportunity_score_authority" in position and position.get("runtime_opportunity_score_authority") != RAW_OPPORTUNITY_AUTHORITY:
        errors.append(f"invalid_runtime_opportunity_score_authority:position:{index}")
    if "quality_resolution" in position:
        resolution = position.get("quality_resolution")
        if not isinstance(resolution, dict):
            errors.append(f"invalid_quality_resolution:position:{index}")
        elif resolution.get("resolution_status") not in {"PASS", "REVIEW_REQUIRED"}:
            errors.append(f"invalid_quality_resolution_status:position:{index}")
    for field in ("allocation_quality_resolution", "runtime_opportunity_score_resolution"):
        if field in position:
            resolution = position.get(field)
            if not isinstance(resolution, dict):
                errors.append(f"invalid_{field}:position:{index}")
            elif resolution.get("resolution_status") not in {"PASS", "REVIEW_REQUIRED"}:
                errors.append(f"invalid_{field}_status:position:{index}")
    target = _ratio_field(errors, position, "target_weight", prefix=f"position:{index}:")
    maximum = _ratio_field(errors, position, "maximum_position_weight", prefix=f"position:{index}:")
    if target is not None and maximum is not None and target > maximum + 0.000001:
        errors.append(f"target_weight_above_position_cap:{index}")
    if target is not None and safety_cap is not None and target > safety_cap + 0.000001:
        errors.append(f"target_weight_above_safety_cap:{index}")
    for field in ("target_notional", "current_notional", "incremental_buy_notional"):
        if isinstance(position.get(field), bool) or not isinstance(position.get(field), (int, float)) or float(position.get(field)) < 0:
            errors.append(f"invalid_notional:{index}:{field}")
    if isinstance(position.get("incremental_target_notional"), bool) or not isinstance(position.get("incremental_target_notional"), (int, float)):
        errors.append(f"invalid_notional:{index}:incremental_target_notional")
    for field in sorted(FORBIDDEN_FIELDS & set(position)):
        errors.append(f"quantity_or_runtime_field_forbidden:{index}:{field}")
    if not isinstance(position.get("reason_codes"), list):
        errors.append(f"reason_codes_not_list:{index}")
    return errors


def _numeric_mapping(payload: Mapping[str, Any], key: str) -> dict[str, float]:
    obj = payload.get(key)
    if not isinstance(obj, dict):
        raise PositionSizingConfigError(f"{key} required")
    result: dict[str, float] = {}
    for name, value in obj.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        result[str(name)] = float(value)
    return result


def _ratio(value: Any, default: float | None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if default is None: raise PositionSizingConfigError("ratio required")
        return default
    if not 0 <= float(value) <= 1:
        raise PositionSizingConfigError("ratio out of range")
    return float(value)


def _ratio_field(errors: list[str], payload: Mapping[str, Any], field: str, *, prefix: str = "") -> float | None:
    try: return _ratio(payload.get(field), None)
    except Exception: errors.append(f"invalid_ratio:{prefix}{field}"); return None


def _optional_ratio_field(errors: list[str], payload: Mapping[str, Any], field: str, *, prefix: str = "") -> float | None:
    if payload.get(field) is None:
        return None
    return _ratio_field(errors, payload, field, prefix=prefix)


def _positive_float(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(float(value), 0.0)


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return int(value)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise PositionSizingConfigError(f"{field} required")
    return value


def _date(value: str) -> None:
    if date.fromisoformat(value).isoformat() != value: raise ValueError("invalid date")


def _timestamp(value: str) -> None:
    if datetime.fromisoformat(value.replace("Z","+00:00")).tzinfo is None: raise ValueError("timestamp timezone required")


def _strip_sha256(value: str) -> str:
    return value[7:] if value.startswith("sha256:") else value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
