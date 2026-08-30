from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.strategy.status_contract import numeric_resolution, status_contract_fields
from ai_fund_lab_v2.strategy.target_weight_precision import (
    TARGET_WEIGHT_ABSOLUTE_TOLERANCE,
    TARGET_WEIGHT_DECIMALS,
    target_weight_sum_tolerance,
)


SCHEMA_VERSION = "position_sizing.v1"
CONFIG_SCHEMA_VERSION = "position_sizing_config.v1"
PRODUCER_VERSION = "phase22_j_position_sizing_producer.v1"
LOT_FEASIBILITY_SCHEMA_VERSION = "ps_lot_feasibility_preflight.v1"
CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION = "position_sizing.canonical_lot_residual_evidence.v1"
G61_COMPATIBILITY_CONSUMPTION_SCHEMA_VERSION = "position_sizing.g61_lot_aware_compatibility_consumption.v1"
G61_COMPATIBILITY_SCHEMA_VERSION = "portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"
PRODUCTION_ARTIFACT_LIFECYCLE_STATUS = "ACCEPTED"
PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY = "ELIGIBLE"
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
ALLOCATION_QUALITY_AUTHORITY = "ALLOCATION_QUALITY_AUTHORITY"
ALLOCATION_QUALITY_CANONICAL_FIELD = "allocation_quality_score"
ALLOCATION_QUALITY_LEGACY_FIELD = "quality_score"
RAW_OPPORTUNITY_AUTHORITY = "OPPORTUNITY_RANKING_AUTHORITY"
RAW_OPPORTUNITY_CANONICAL_FIELD = "runtime_opportunity_score"
RAW_OPPORTUNITY_LEGACY_FIELDS = ("input_score", "opportunity_score")
REFERENCE_PRICE_AUTHORITY = "REFERENCE_PRICE_AUTHORITY"
REDUCE_EXECUTABLE_SEMANTIC = "REDUCE_EXECUTABLE"
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT = "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT"
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL = "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL"
CANONICAL_SIZING_EVIDENCE_CLASSES = {
    "EXECUTABLE",
    "LOT_INFEASIBLE",
    "STRATEGY_CAP_BOUND",
    "SAFETY_CAP_BOUND",
    "INSUFFICIENT_CASH",
    "NO_POSITIVE_QUANTITY_DELTA",
    "INVALID_INPUT",
    "UNAVAILABLE_AUTHORITY",
}

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


def build_lot_feasibility_preflight(
    *,
    business_date: str,
    rows: list[Mapping[str, Any]],
    portfolio_value: float,
    config: PositionSizingConfig,
    safety_cap: float | None = None,
) -> list[dict[str, Any]]:
    return [
        _lot_feasibility_row(row, business_date=business_date, portfolio_value=portfolio_value, config=config, safety_cap=safety_cap)
        for row in sorted(rows, key=lambda item: (_positive_int(item.get("construction_priority"), 999999), str(item.get("security_code") or item.get("symbol") or "")))
        if _lot_preflight_required(row)
    ]


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
    production_consumer_connected: bool = False,
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
        production_consumer_connected=production_consumer_connected,
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
    production_consumer_connected: bool = False,
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
    passive_convergence_authority = _resolve_passive_convergence_authority(portfolio_construction_summary.summary or {})
    if target_exposure_unresolved and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("position_exposure_unresolved")
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
    g61_compatibility_consumption = _g61_lot_aware_compatibility_consumption_summary(
        business_date=business_date,
        portfolio_construction_summary=portfolio_construction_summary.summary or {},
    )
    if g61_compatibility_consumption["status"] == "BLOCK":
        status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
        reasons.extend(g61_compatibility_consumption["reason_codes"])

    sizing_rows = _apply_canonical_deployment_set_to_sizing_rows(
        portfolio_construction_summary.rows,
        portfolio_construction_summary.summary,
    )
    sizing_rows = _apply_g61_compatibility_to_sizing_rows(sizing_rows, g61_compatibility_consumption)
    sizing_rows = _rows_with_price_volatility(sizing_rows, price_volatility_summary)
    positions: list[dict[str, Any]] = []
    if config is None or status != "PASS":
        positions = [_unresolved_position(row, config=config, safety_cap=effective_cap) for row in sizing_rows]
        lot_feasibility_preflight: list[dict[str, Any]] = []
        total_target_weight = 0.0
    else:
        lot_feasibility_preflight = build_lot_feasibility_preflight(
            business_date=business_date,
            rows=sizing_rows,
            portfolio_value=portfolio_value,
            config=config,
            safety_cap=safety_cap,
        )
        positions, sizing_reasons = _size_positions(
            config=config,
            rows=sizing_rows,
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
            if _passive_convergence_aggregate_over_target_authorized(
                passive_convergence_authority,
                total_target_weight=total_target_weight,
                target_exposure=target_exposure,
                aggregate_tolerance=aggregate_tolerance,
            ):
                reasons.append("aggregate_over_target_passive_convergence_authorized")
            else:
                status = "BLOCK"
                reasons.append("aggregate_target_weight_above_exposure_cap")
        if safety_cap is not None and any(
            float(item["target_weight"]) > safety_cap + 0.000001
            and not _position_cap_exception_is_directionally_allowed(item, target=float(item["target_weight"]))
            for item in positions
        ):
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
    production_ready = bool(production_consumer_connected) and status == "PASS"
    lifecycle = PRODUCTION_ARTIFACT_LIFECYCLE_STATUS if production_ready else ARTIFACT_LIFECYCLE_STATUS
    consumer_eligibility = PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY if production_ready else RUNTIME_CONSUMER_ELIGIBILITY

    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": lifecycle,
        "source_authority_status": source_status,
        "producer_result_status": status,
        "runtime_consumer_eligibility": consumer_eligibility,
        **status_contract_fields(
            producer_result_status=status,
            artifact_lifecycle_status=lifecycle,
            runtime_consumer_eligibility=consumer_eligibility,
            reason_codes=sorted(set(reasons)),
            decision_resolution="UNRESOLVED" if target_exposure_unresolved or status != "PASS" else "RESOLVED",
        ),
        "sizing_method": config.sizing_method if config else "",
        "target_gross_exposure_ratio": None if target_exposure is None else round(target_exposure, 6),
        "target_gross_exposure_ratio_resolution": numeric_resolution(target_exposure, unresolved=target_exposure is None),
        "target_position_count": target_count,
        "target_position_count_resolution": numeric_resolution(target_count, unresolved=target_count is None),
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_total_equity": round(portfolio_value, 2),
        "minimum_meaningful_notional_policy": dict(config.minimum_meaningful_notional) if config else {},
        "lot_feasibility_preflight_schema_version": LOT_FEASIBILITY_SCHEMA_VERSION,
        "lot_feasibility_preflight": lot_feasibility_preflight,
        "canonical_sizing_evidence_schema_version": CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION,
        "canonical_sizing_evidence": _canonical_sizing_evidence_summary(positions, lot_feasibility_preflight),
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
        "passive_convergence_authority": passive_convergence_authority,
        "canonical_deployment_set_consumption": _canonical_deployment_set_consumption_summary(positions, portfolio_construction_summary.summary),
        "g61_lot_aware_compatibility_consumption": g61_compatibility_consumption,
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
        "share_quantity_decided": production_ready,
        "lot_rounding_decided": production_ready,
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
        "production_consumer_connected": production_ready,
        "runtime_switch_performed": False,
        "legacy_authority_active": not production_ready,
    }
    return payload, {"schema_version": "phase22_j_position_sizing_evidence.v1", "producer_result_status": status, "reason_codes": payload["reason_codes"]}


def validate_position_sizing_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version","business_date","as_of","feature_date","artifact_lifecycle_status","source_authority_status","producer_result_status","runtime_consumer_eligibility","target_gross_exposure_ratio","positions","total_target_weight","residual_cash_ratio","concrete_target_weight_decided","target_notional_decided","share_quantity_decided","lot_rounding_decided","source_artifacts","source_hashes","temporal_safety","strategy_maximum_position_weight","strategy_maximum_position_weight_source","safety_maximum_position_weight","safety_maximum_position_weight_source","safety_authority_status","effective_maximum_position_weight","effective_maximum_position_weight_derivation","explicit_zero_cap","emergency_brake_active","market_context_risk_state","dynamic_cash_exposure","aggregate_exposure_cap","canonical_sizing_evidence_schema_version","canonical_sizing_evidence"}
    errors = [f"required_field_missing:{f}" for f in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported_schema_version")
    if payload.get("artifact_lifecycle_status") not in ARTIFACT_LIFECYCLE_STATUSES:
        errors.append("invalid_artifact_lifecycle_status")
    if payload.get("runtime_consumer_eligibility") not in RUNTIME_CONSUMER_ELIGIBILITIES:
        errors.append("invalid_runtime_consumer_eligibility")
    target_unresolved = (
        payload.get("target_gross_exposure_ratio_resolution") == "UNRESOLVED"
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
        passive_convergence_authority = _passive_convergence_authority_from_payload(payload)
        if not _passive_convergence_aggregate_over_target_authorized(
            passive_convergence_authority,
            total_target_weight=total,
            target_exposure=target_exposure,
            aggregate_tolerance=aggregate_tolerance,
        ):
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
        for field in ("dynamic_cash_exposure", "aggregate_exposure_cap"):
            if payload.get(field) is not None:
                errors.append(f"unresolved_ratio_must_be_null:{field}")
    if not isinstance(positions, list):
        errors.append("positions_not_list")
    else:
        for index, position in enumerate(positions):
            errors.extend(_validate_position(position, index=index, safety_cap=safety_cap))
    if payload.get("canonical_sizing_evidence_schema_version") != CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION:
        errors.append("invalid_canonical_sizing_evidence_schema_version")
    if not isinstance(payload.get("canonical_sizing_evidence"), dict):
        errors.append("canonical_sizing_evidence_not_object")
    errors.extend(_validate_g61_compatibility_consumption(payload.get("g61_lot_aware_compatibility_consumption")))
    for field in sorted(FORBIDDEN_FIELDS & set(payload)):
        errors.append(f"quantity_or_runtime_field_forbidden:{field}")
    production_ready = (
        payload.get("producer_result_status") == "PASS"
        and payload.get("artifact_lifecycle_status") == PRODUCTION_ARTIFACT_LIFECYCLE_STATUS
        and payload.get("runtime_consumer_eligibility") == PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY
    )
    if production_ready:
        for field in ("share_quantity_decided", "lot_rounding_decided", "production_consumer_connected"):
            if payload.get(field) is not True:
                errors.append(f"{field}_must_be_true_for_production")
        for field in ("order_price_decided", "pending_decided", "submit_decided", "runtime_switch_performed"):
            if payload.get(field) is not False:
                errors.append(f"{field}_must_be_false")
        if payload.get("legacy_authority_active") is not False:
            errors.append("legacy_authority_must_be_inactive_for_production")
    else:
        if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
            errors.append("artifact_lifecycle_must_be_draft_or_phase30_s_production_ready")
        if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
            errors.append("runtime_consumer_eligibility_must_be_not_eligible_or_phase30_s_production_ready")
        for field in ("share_quantity_decided","lot_rounding_decided","order_price_decided","pending_decided","submit_decided","production_consumer_connected","runtime_switch_performed"):
            if payload.get(field) is not False:
                errors.append(f"{field}_must_be_false")
        if payload.get("legacy_authority_active") is not True:
            errors.append("legacy_authority_must_remain_active")
    temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), dict) else {}
    if temporal.get("implicit_latest_fallback_used") is not False: errors.append("implicit_latest_fallback_forbidden")
    if temporal.get("previous_day_position_sizing_copied") is not False: errors.append("previous_day_copy_forbidden")
    if errors:
        raise PositionSizingSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def _validate_g61_compatibility_consumption(consumption: Any) -> list[str]:
    if consumption is None:
        return []
    if not isinstance(consumption, dict):
        return ["g61_compatibility_consumption_not_object"]
    errors: list[str] = []
    if consumption.get("schema_version") != G61_COMPATIBILITY_CONSUMPTION_SCHEMA_VERSION:
        errors.append("invalid_g61_compatibility_consumption_schema")
    status = str(consumption.get("status") or "")
    if status not in {"PASS", "BLOCK", "NOT_AVAILABLE_LEGACY_COMPATIBILITY"}:
        errors.append("invalid_g61_compatibility_consumption_status")
    if status == "NOT_AVAILABLE_LEGACY_COMPATIBILITY":
        return errors
    if consumption.get("pc_discrete_quantity_authority") is not False:
        errors.append("g61_pc_discrete_quantity_authority_forbidden")
    if consumption.get("position_sizing_quantity_owner") not in {"POSITION_SIZING", None}:
        errors.append("invalid_g61_position_sizing_quantity_owner")
    if consumption.get("lower_priority_implicit_promotion") is not False:
        errors.append("g61_lower_priority_implicit_promotion_forbidden")
    if consumption.get("position_sizing_recomputes_capital_priority") is not False:
        errors.append("g61_ps_capital_priority_redecision_forbidden")
    if consumption.get("ordinary_lot_feasibility_priority_redecision_allowed") is not False:
        errors.append("g61_ordinary_lot_priority_redecision_forbidden")
    return errors


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
        if (
            payload.get("runtime_consumer_eligibility") == PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY
            and payload.get("share_quantity_decided") is True
            and payload.get("lot_rounding_decided") is True
        ):
            return payload
        raise PositionSizingConsumerError("Position Sizing artifact is not production-consumable")
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


def _size_positions(*, config: PositionSizingConfig, rows: tuple[Mapping[str, Any], ...], target_exposure: float, portfolio_value: float, safety_cap: float) -> tuple[list[dict[str, Any]], list[str]]:
    if target_exposure <= 0:
        return (
            [
                _zero_allocation_position(
                    row,
                    config=config,
                    safety_cap=safety_cap,
                    reason="target_gross_exposure_zero",
                )
                for row in rows
            ],
            [],
        )
    active_row_count = max(sum(1 for row in rows if float(row.get("target_weight") or 0.0) > 0.0), 1)
    base = target_exposure / float(active_row_count)
    raw: list[dict[str, Any]] = []
    reasons: list[str] = []
    max_weight = min(config.strategy_maximum_position_weight, safety_cap)
    for row in rows:
        item = _raw_position(
            row,
            config=config,
            base=base,
            max_weight=max_weight,
            portfolio_value=portfolio_value,
            safety_cap=safety_cap,
        )
        raw.append(item)
    active_total = sum(float(item["capped_weight"]) for item in raw if item["sizing_status"] in {"SIZED", "CAPPED"})
    scale = min(1.0, target_exposure / active_total) if active_total > 0 else 0.0
    positions = []
    for item in raw:
        if item.get("position_type") == "EXISTING_POSITION":
            positions.append(item)
            continue
        if item["sizing_status"] in {"SIZED", "CAPPED"}:
            target_weight = round(float(item["capped_weight"]) * scale, 6)
            target_notional = round(target_weight * portfolio_value, 2)
            current_notional = round(float(item["current_weight"]) * portfolio_value, 2)
            incremental = round(target_notional - current_notional, 2)
            item = {**item, "target_weight": target_weight, "weight_delta": round(target_weight - float(item["current_weight"]), 6), "target_notional": target_notional, "current_notional": current_notional, "incremental_target_notional": incremental, "incremental_buy_notional": round(max(incremental, 0.0), 2)}
        positions.append(item)
    return positions, reasons


def _apply_canonical_deployment_set_to_sizing_rows(
    rows: Sequence[Mapping[str, Any]],
    portfolio_construction_summary: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    deployment_set = _canonical_deployment_set_from_pc_summary(portfolio_construction_summary)
    multi_selected = _multi_allocation_sizing_selection_by_key(portfolio_construction_summary)
    if not deployment_set and not multi_selected:
        return tuple(rows)
    if not deployment_set:
        deployment_set = {}
    selected = {
        (str(item.get("competitor_type") or ""), str(item.get("symbol") or ""))
        for item in deployment_set.get("selected_deployments") or []
        if isinstance(item, Mapping)
    }
    final_winner_type = str(deployment_set.get("final_winner_type") or "")
    cash_winner = bool(deployment_set.get("cash_winner")) or final_winner_type == "CASH_OPTIONALITY"
    no_deployable = bool(deployment_set.get("no_deployable_opportunity"))
    deployment_hash = str(deployment_set.get("deployment_set_hash") or "")
    adjusted: list[Mapping[str, Any]] = []
    for row in rows:
        competitor_type = _deployment_competitor_type(row)
        symbol = str(row.get("security_code") or row.get("symbol") or "")
        if competitor_type not in {"NEW_BUY", "ADD"}:
            adjusted.append(
                {
                    **dict(row),
                    "canonical_deployment_set_sizing_eligibility": "NOT_INCREMENTAL_DEPLOYMENT_COMPETITOR",
                    "canonical_deployment_set_hash": deployment_hash,
                    "final_capital_winner_type": final_winner_type,
                    "final_capital_winner_symbol": str(deployment_set.get("final_winner_symbol") or ""),
                }
            )
            continue
        multi_selection = multi_selected.get((competitor_type, symbol), {})
        if multi_selection:
            target_weight = _ratio(multi_selection.get("authorized_allocation_weight"), None)
            next_row = dict(row)
            if target_weight is not None:
                current_weight = _ratio(next_row.get("current_weight"), 0.0) if competitor_type == "ADD" else 0.0
                next_row["target_weight"] = round(current_weight + target_weight, TARGET_WEIGHT_DECIMALS)
                if competitor_type == "ADD":
                    next_row["accepted_incremental_weight"] = target_weight
                    next_row["lot_aware_accepted_incremental_weight"] = target_weight
                else:
                    next_row["accepted_buy_new_weight"] = target_weight
                    next_row["lot_aware_accepted_buy_new_weight"] = target_weight
            reason_codes = list(next_row.get("reason_codes") or [])
            reason_codes.append("multi_allocation_g61_executable_selected_for_sizing")
            g102_lot_resolution = _g102_item_scoped_pc_lot_resolution_from_selection(multi_selection)
            if g102_lot_resolution:
                next_row["phase29_l19_lot_resolution"] = g102_lot_resolution
                next_row["semantic_buy_type"] = str(g102_lot_resolution.get("semantic_type") or next_row.get("semantic_buy_type") or "")
                next_row["target_weight_resolution"] = {
                    **dict(next_row.get("target_weight_resolution") or {}),
                    "status": "PASS",
                    "reason": "g102_item_scoped_pc_discrete_quantity_authority",
                    "resolved_weight": _ratio(g102_lot_resolution.get("final_target_weight"), next_row.get("target_weight")),
                    "lot_aware_final_reallocation": {
                        "authority_type": "PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION",
                        "accepted_lot_increment_weight": target_weight,
                        "post_lot_target_weight": g102_lot_resolution.get("final_target_weight"),
                        "pre_lot_target_weight": target_weight,
                        "final_allocated_quantity": g102_lot_resolution.get("final_allocated_quantity"),
                        "pc_positive_executable_quantity_authority": dict(
                            g102_lot_resolution.get("pc_positive_executable_quantity_authority") or {}
                        ),
                        "phase29_l19_lot_resolution": g102_lot_resolution,
                    },
                }
                reason_codes.append("G102_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY_CONSUMED_BY_PS")
            adjusted.append(
                {
                    **next_row,
                    "canonical_deployment_set_sizing_eligibility": "SELECTED_BY_CANONICAL_MULTI_ALLOCATION",
                    "canonical_deployment_set_hash": deployment_hash,
                    "final_capital_winner_type": "MULTI_ALLOCATION",
                    "final_capital_winner_symbol": "",
                    "final_capital_winner_binds_before_discrete_sizing": True,
                    "multi_allocation_set_hash": str(multi_selection.get("multi_allocation_set_hash") or ""),
                    "multi_allocation_authorized_weight": target_weight,
                    "reason_codes": sorted(set(reason_codes)),
                }
            )
            continue
        pc_final_authority = _pc_final_discrete_authority_for_sizing(row)
        if pc_final_authority and competitor_type in {"NEW_BUY", "REENTRY"}:
            adjusted.append(
                _pc_final_discrete_authority_deployment_row(
                    row,
                    competitor_type=competitor_type,
                    deployment_set=deployment_set,
                    authority=pc_final_authority,
                )
            )
            continue
        selected_for_deployment = (competitor_type, symbol) in selected and not cash_winner and not no_deployable
        if selected_for_deployment:
            adjusted.append(
                {
                    **dict(row),
                    "canonical_deployment_set_sizing_eligibility": "SELECTED_FOR_DEPLOYMENT",
                    "canonical_deployment_set_hash": deployment_hash,
                    "final_capital_winner_type": final_winner_type,
                    "final_capital_winner_symbol": str(deployment_set.get("final_winner_symbol") or ""),
                    "final_capital_winner_binds_before_discrete_sizing": True,
                }
            )
            continue
        adjusted.append(
            _zero_incremental_deployment_row(
                row,
                competitor_type=competitor_type,
                deployment_set=deployment_set,
                reason="cash_winner_defeated_security"
                if cash_winner
                else "canonical_capital_competition_defeated_security",
            )
        )
    return tuple(adjusted)


def _pc_final_discrete_authority_for_sizing(row: Mapping[str, Any]) -> Mapping[str, Any]:
    lot_resolution = _lot_aware_strategy_cap_lot_resolution(row)
    authority = (
        lot_resolution.get("pc_positive_executable_quantity_authority")
        if isinstance(lot_resolution.get("pc_positive_executable_quantity_authority"), Mapping)
        else {}
    )
    if str(authority.get("authority_type") or "") not in {
        "",
        "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
    }:
        return {}
    if str(authority.get("status") or "") != "PASS":
        return {}
    if authority.get("ps_must_consume_canonical_quantity") is not True:
        return {}
    if _positive_int(authority.get("final_allocated_quantity"), 0) <= 0:
        return {}
    if _positive_int(lot_resolution.get("final_allocated_quantity"), 0) <= 0:
        return {}
    return authority


def _pc_final_discrete_authority_deployment_row(
    row: Mapping[str, Any],
    *,
    competitor_type: str,
    deployment_set: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    next_row = dict(row)
    resolution = dict(next_row.get("target_weight_resolution") or {})
    target_authority = dict(next_row.get("target_weight_authority") or {})
    reason_codes = list(next_row.get("reason_codes") or [])
    reason_codes.append("pc_final_discrete_authority_selected_for_sizing")
    if bool(deployment_set.get("cash_winner")) or str(deployment_set.get("final_winner_type") or "") == "CASH_OPTIONALITY":
        reason_codes.append("stale_deployment_set_cash_winner_not_reapplied_after_pc_final_selection")
    binding = {
        "schema_version": str(deployment_set.get("schema_version") or ""),
        "owner": "PORTFOLIO_CONSTRUCTION",
        "cardinality_contract": str(deployment_set.get("cardinality_contract") or ""),
        "final_winner_type": "PC_FINAL_DISCRETE_AUTHORITY",
        "final_winner_symbol": str(next_row.get("security_code") or next_row.get("symbol") or ""),
        "cash_winner": False,
        "selected_symbol_set": [str(next_row.get("security_code") or next_row.get("symbol") or "")],
        "deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
        "final_capital_winner_binds_before_discrete_sizing": True,
        "pc_final_discrete_authority_precedence": True,
        "pc_positive_executable_quantity_authority": dict(authority),
    }
    return {
        **next_row,
        "target_weight_authority": {
            **target_authority,
            "canonical_deployment_set_owner": "PORTFOLIO_CONSTRUCTION",
            "canonical_deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
            "capital_winner_authority_owner": "PORTFOLIO_CONSTRUCTION",
            "pc_final_discrete_authority_is_final_strategy_capital_authority": True,
            "position_sizing_remains_discrete_quantity_owner": True,
            "position_sizing_capital_winner_authority": False,
        },
        "target_weight_resolution": {
            **resolution,
            "status": "PASS",
            "reason": "pc_final_discrete_authority_selected_for_sizing",
            "canonical_deployment_set_binding": binding,
        },
        "canonical_deployment_set_sizing_eligibility": "SELECTED_BY_PC_FINAL_DISCRETE_AUTHORITY",
        "canonical_deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
        "final_capital_winner_type": "PC_FINAL_DISCRETE_AUTHORITY",
        "final_capital_winner_symbol": str(next_row.get("security_code") or next_row.get("symbol") or ""),
        "final_capital_winner_binds_before_discrete_sizing": True,
        "deployment_competitor_type": competitor_type,
        "reason_codes": sorted(set(reason_codes)),
    }


def _g102_item_scoped_pc_lot_resolution_from_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
    resolution = selection.get("phase29_l19_lot_resolution") if isinstance(selection.get("phase29_l19_lot_resolution"), Mapping) else {}
    authority = (
        resolution.get("pc_positive_executable_quantity_authority")
        if isinstance(resolution.get("pc_positive_executable_quantity_authority"), Mapping)
        else {}
    )
    if str(authority.get("authority_type") or "") != "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY":
        return {}
    if str(authority.get("status") or "") != "PASS":
        return {}
    if authority.get("ps_must_consume_canonical_quantity") is not True:
        return {}
    if _positive_int(authority.get("final_allocated_quantity"), 0) <= 0:
        return {}
    return dict(resolution)


def _multi_allocation_sizing_selection_by_key(
    portfolio_construction_summary: Mapping[str, Any],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    multi_set = _canonical_multi_allocation_set_from_pc_summary(portfolio_construction_summary)
    if not multi_set:
        return {}
    compatibility = (
        multi_set.get("lot_aware_allocation_to_sizing_compatibility")
        if isinstance(multi_set.get("lot_aware_allocation_to_sizing_compatibility"), Mapping)
        else {}
    )
    rows = compatibility.get("compatibility_rows") if isinstance(compatibility.get("compatibility_rows"), list) else []
    executable_keys = {
        (str(item.get("competitor_type") or ""), str(item.get("symbol") or ""))
        for item in rows
        if isinstance(item, Mapping)
        and str(item.get("compatibility_state") or "") == "LOT_EXECUTABLE_COMPATIBLE"
        and item.get("implicit_priority_promotion_allowed") is False
        and item.get("position_sizing_quantity_authority_preserved") is True
        and item.get("pc_quantity_authority") is False
    }
    if not executable_keys:
        return {}
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for allocation in multi_set.get("security_allocations") or []:
        if not isinstance(allocation, Mapping):
            continue
        key = (str(allocation.get("competitor_type") or ""), str(allocation.get("symbol") or ""))
        if key in executable_keys:
            result[key] = {
                **dict(allocation),
                "multi_allocation_set_hash": str(multi_set.get("multi_allocation_set_hash") or ""),
            }
    return result


def _canonical_deployment_set_from_pc_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = summary.get("canonical_deployment_set")
    if isinstance(direct, Mapping):
        return direct
    competition = summary.get("capital_competition") if isinstance(summary.get("capital_competition"), Mapping) else {}
    nested = competition.get("canonical_deployment_set") if isinstance(competition.get("canonical_deployment_set"), Mapping) else {}
    return nested


def _canonical_multi_allocation_set_from_pc_summary(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = summary.get("canonical_multi_allocation_deployment_set")
    if isinstance(direct, Mapping):
        return direct
    competition = summary.get("capital_competition") if isinstance(summary.get("capital_competition"), Mapping) else {}
    nested = (
        competition.get("canonical_multi_allocation_deployment_set")
        if isinstance(competition.get("canonical_multi_allocation_deployment_set"), Mapping)
        else {}
    )
    return nested


def _g61_lot_aware_compatibility_consumption_summary(
    *,
    business_date: str,
    portfolio_construction_summary: Mapping[str, Any],
) -> dict[str, Any]:
    multi_set = _canonical_multi_allocation_set_from_pc_summary(portfolio_construction_summary)
    base = {
        "schema_version": G61_COMPATIBILITY_CONSUMPTION_SCHEMA_VERSION,
        "owner": "POSITION_SIZING",
        "business_date": business_date,
        "pc_authority_owner": "PORTFOLIO_CONSTRUCTION",
        "position_sizing_quantity_owner": "POSITION_SIZING",
        "pc_discrete_quantity_authority": False,
        "position_sizing_recomputes_capital_priority": False,
        "ordinary_lot_feasibility_priority_redecision_allowed": False,
        "candidate_rank_authority_mutation": False,
        "candidate_eligibility_authority_mutation": False,
        "market_quality_semantics_changed": False,
        "risk_pacing_semantics_changed": False,
        "runtime_order_behavior_change_count": 0,
        "future_input_count": 0,
        "historical_outcome_strategy_input_count": 0,
    }
    if not multi_set:
        return {
            **base,
            "status": "NOT_AVAILABLE_LEGACY_COMPATIBILITY",
            "g61_compatibility_consumed_by_ps": False,
            "reason_codes": ["G61_COMPATIBILITY_NOT_AVAILABLE_LEGACY_COMPATIBILITY"],
        }
    compatibility = (
        multi_set.get("lot_aware_allocation_to_sizing_compatibility")
        if isinstance(multi_set.get("lot_aware_allocation_to_sizing_compatibility"), Mapping)
        else {}
    )
    errors: list[str] = []
    if not compatibility:
        errors.append("G61_COMPATIBILITY_MISSING")
    elif str(compatibility.get("schema_version") or "") != G61_COMPATIBILITY_SCHEMA_VERSION:
        errors.append("G61_COMPATIBILITY_SCHEMA_INVALID")
    if compatibility and str(compatibility.get("business_date") or "") != business_date:
        errors.append("G61_COMPATIBILITY_DATE_MISMATCH")
    if compatibility and str(compatibility.get("authority_status") or "") != "SHADOW_NON_AUTHORITATIVE":
        errors.append("G61_COMPATIBILITY_AUTHORITY_STATUS_INVALID")
    rows = compatibility.get("compatibility_rows") if isinstance(compatibility.get("compatibility_rows"), list) else []
    if compatibility and not isinstance(compatibility.get("compatibility_rows"), list):
        errors.append("G61_COMPATIBILITY_ROWS_MALFORMED")
    if compatibility and compatibility.get("lower_priority_implicit_promotion_allowed") is not False:
        errors.append("LOWER_PRIORITY_IMPLICIT_PROMOTION_NOT_PROHIBITED")
    if compatibility and compatibility.get("priority_inversion_after_compatibility") is not False:
        errors.append("G61_PRIORITY_INVERSION_AFTER_COMPATIBILITY")
    if compatibility and compatibility.get("residual_capital_explicit") is not True:
        errors.append("G61_RESIDUAL_CAPITAL_NOT_EXPLICIT")
    malformed_rows = [
        str(item.get("symbol") or "")
        for item in rows
        if not isinstance(item, Mapping)
        or str(item.get("schema_version") or "") != G61_COMPATIBILITY_SCHEMA_VERSION
        or str(item.get("business_date") or "") != business_date
        or item.get("implicit_priority_promotion_allowed") is not False
        or item.get("position_sizing_quantity_authority_preserved") is not True
        or item.get("pc_quantity_authority") is not False
    ]
    if malformed_rows:
        errors.append("G61_COMPATIBILITY_ROW_MALFORMED")
    status = "BLOCK" if errors else "PASS"
    return {
        **base,
        "status": status,
        "g61_compatibility_consumed_by_ps": status == "PASS",
        "canonical_multi_allocation_set_hash": str(multi_set.get("multi_allocation_set_hash") or ""),
        "compatibility_hash": str(compatibility.get("compatibility_hash") or ""),
        "allocation_count": len(rows),
        "lot_executable_count": int(compatibility.get("lot_executable_count") or 0) if compatibility else 0,
        "executable_multi_security": bool(compatibility.get("executable_multi_security")) if compatibility else False,
        "add_compatibility": str(compatibility.get("add_compatibility") or "") if compatibility else "",
        "capital_conservation": dict(compatibility.get("capital_conservation") or {}) if compatibility else {},
        "lower_priority_implicit_promotion": bool(compatibility.get("lower_priority_implicit_promotion_allowed"))
        if compatibility
        else False,
        "priority_semantics_preserved_through_ps": status == "PASS",
        "residual_capital_explicit_through_ps": bool(compatibility.get("residual_capital_explicit")) if compatibility else False,
        "residual_capital_weight": _ratio(compatibility.get("residual_capital_weight"), 0.0) if compatibility else 0.0,
        "unresolved_higher_priority_allocation_count": sum(
            1
            for item in rows
            if isinstance(item, Mapping)
            and str(item.get("compatibility_state") or "") in {"LOT_INFEASIBLE_RESIDUAL_REQUIRED", "CAP_HEADROOM_INSUFFICIENT"}
        ),
        "lower_priority_rows_requiring_explicit_residual_resolution": sum(
            1
            for item in rows
            if isinstance(item, Mapping)
            and item.get("lower_priority_execution_requires_explicit_residual_resolution") is True
        ),
        "compatibility_rows_by_symbol": {
            str(item.get("symbol") or ""): {
                "allocation_rank": item.get("allocation_rank"),
                "compatibility_state": str(item.get("compatibility_state") or ""),
                "lower_priority_execution_requires_explicit_residual_resolution": bool(
                    item.get("lower_priority_execution_requires_explicit_residual_resolution")
                ),
                "implicit_priority_promotion_allowed": False,
                "residual_capital_weight": _ratio(item.get("residual_capital_weight"), 0.0),
            }
            for item in rows
            if isinstance(item, Mapping) and str(item.get("symbol") or "")
        },
        "reason_codes": sorted(set(errors or ["G61_COMPATIBILITY_CONSUMED_BY_PS", "LOWER_PRIORITY_IMPLICIT_PROMOTION_PROHIBITED"])),
    }


def _apply_g61_compatibility_to_sizing_rows(
    rows: Sequence[Mapping[str, Any]],
    consumption: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    by_symbol = (
        consumption.get("compatibility_rows_by_symbol")
        if isinstance(consumption.get("compatibility_rows_by_symbol"), Mapping)
        else {}
    )
    if not by_symbol:
        return tuple(rows)
    enriched: list[Mapping[str, Any]] = []
    for row in rows:
        symbol = str(row.get("security_code") or row.get("symbol") or "")
        compatibility = by_symbol.get(symbol) if isinstance(by_symbol.get(symbol), Mapping) else {}
        if not compatibility:
            enriched.append(row)
            continue
        reason_codes = list(row.get("reason_codes") or [])
        reason_codes.append("G61_COMPATIBILITY_CONSUMED_BY_PS")
        if compatibility.get("lower_priority_execution_requires_explicit_residual_resolution") is True:
            reason_codes.append("LOWER_PRIORITY_EXECUTION_REQUIRES_EXPLICIT_RESIDUAL_RESOLUTION")
        enriched.append(
            {
                **dict(row),
                "g61_lot_aware_compatibility_consumed_by_ps": True,
                "g61_lot_aware_compatibility": dict(compatibility),
                "lower_priority_implicit_promotion_allowed": False,
                "position_sizing_recomputes_capital_priority": False,
                "ordinary_lot_feasibility_priority_redecision_allowed": False,
                "reason_codes": sorted(set(reason_codes)),
            }
        )
    return tuple(enriched)


def _deployment_competitor_type(row: Mapping[str, Any]) -> str:
    if bool(row.get("current_position")) and str(row.get("pm_action") or "").upper() == "ADD":
        return "ADD"
    if not bool(row.get("current_position")) and str(row.get("membership_intent") or "").upper() == "ADD_CANDIDATE":
        return "NEW_BUY"
    return ""


def _zero_incremental_deployment_row(
    row: Mapping[str, Any],
    *,
    competitor_type: str,
    deployment_set: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    current_weight = _ratio(row.get("current_weight"), 0.0) if competitor_type == "ADD" else 0.0
    resolution = dict(row.get("target_weight_resolution") or {})
    target_authority = dict(row.get("target_weight_authority") or {})
    reason_codes = list(row.get("reason_codes") or [])
    reason_codes.extend([reason, "final_capital_winner_binds_before_discrete_sizing"])
    return {
        **dict(row),
        "target_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
        "accepted_incremental_weight": 0.0,
        "lot_aware_accepted_incremental_weight": 0.0,
        "accepted_buy_new_weight": 0.0,
        "lot_aware_accepted_buy_new_weight": 0.0,
        "target_weight_authority": {
            **target_authority,
            "canonical_deployment_set_owner": "PORTFOLIO_CONSTRUCTION",
            "canonical_deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
            "capital_winner_authority_owner": "PORTFOLIO_CONSTRUCTION",
            "position_sizing_remains_discrete_quantity_owner": True,
            "position_sizing_capital_winner_authority": False,
        },
        "target_weight_resolution": {
            **resolution,
            "status": "PASS",
            "reason": reason,
            "resolved_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
            "zero_weight_reason": reason if current_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE else "",
            "review_reason": "",
            "canonical_deployment_set_binding": {
                "schema_version": str(deployment_set.get("schema_version") or ""),
                "owner": "PORTFOLIO_CONSTRUCTION",
                "cardinality_contract": str(deployment_set.get("cardinality_contract") or ""),
                "final_winner_type": str(deployment_set.get("final_winner_type") or ""),
                "final_winner_symbol": str(deployment_set.get("final_winner_symbol") or ""),
                "cash_winner": bool(deployment_set.get("cash_winner")),
                "selected_symbol_set": list(deployment_set.get("selected_symbol_set") or []),
                "deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
                "final_capital_winner_binds_before_discrete_sizing": True,
            },
        },
        "canonical_deployment_set_sizing_eligibility": "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION",
        "canonical_deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
        "final_capital_winner_type": str(deployment_set.get("final_winner_type") or ""),
        "final_capital_winner_symbol": str(deployment_set.get("final_winner_symbol") or ""),
        "final_capital_winner_binds_before_discrete_sizing": True,
        "deployment_competitor_type": competitor_type,
        "reason_codes": sorted(set(reason_codes)),
    }


def _canonical_deployment_set_consumption_summary(
    positions: Sequence[Mapping[str, Any]],
    portfolio_construction_summary: Mapping[str, Any],
) -> dict[str, Any]:
    deployment_set = _canonical_deployment_set_from_pc_summary(portfolio_construction_summary)
    if not deployment_set:
        return {
            "schema_version": "position_sizing.canonical_deployment_set_consumption.v1",
            "status": "NOT_AVAILABLE_LEGACY_COMPATIBILITY",
            "owner": "POSITION_SIZING",
            "capital_winner_authority": "PORTFOLIO_CONSTRUCTION",
            "position_sizing_capital_winner_authority": False,
        }
    defeated = [
        item
        for item in positions
        if str(item.get("canonical_deployment_set_sizing_eligibility") or "")
        == "DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION"
    ]
    defeated_with_positive_increment = [
        item
        for item in defeated
        if int(item.get("quantity_delta_candidate") or 0) > 0
        or float(item.get("incremental_buy_notional") or 0.0) > 0.0
    ]
    return {
        "schema_version": "position_sizing.canonical_deployment_set_consumption.v1",
        "status": "PASS" if not defeated_with_positive_increment else "BLOCK",
        "owner": "POSITION_SIZING",
        "capital_winner_authority": "PORTFOLIO_CONSTRUCTION",
        "canonical_deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
        "cardinality_contract": str(deployment_set.get("cardinality_contract") or ""),
        "final_winner_type": str(deployment_set.get("final_winner_type") or ""),
        "final_winner_symbol": str(deployment_set.get("final_winner_symbol") or ""),
        "selected_symbol_set": list(deployment_set.get("selected_symbol_set") or []),
        "defeated_security_evidence_row_count": len(defeated),
        "defeated_security_sizing_input_count": len(defeated_with_positive_increment),
        "defeated_security_positive_increment_count": len(defeated_with_positive_increment),
        "cash_winner_security_sizing_input_count": 0
        if str(deployment_set.get("final_winner_type") or "") == "CASH_OPTIONALITY"
        else len(list(deployment_set.get("selected_deployments") or [])),
        "final_capital_winner_binds_before_discrete_sizing": True,
        "position_sizing_remains_discrete_quantity_owner": True,
        "position_sizing_capital_winner_authority": False,
        "downstream_cash_redecision_count": 0,
        "future_information_used": False,
        "historical_outcome_used": False,
        "paper_ledger_input_used": False,
        "audit_result_input_used": False,
    }


def _zero_allocation_position(row: Mapping[str, Any], *, config: PositionSizingConfig, safety_cap: float, reason: str) -> dict[str, Any]:
    base = _raw_position(
        row,
        config=config,
        base=0.0,
        max_weight=min(config.strategy_maximum_position_weight, safety_cap),
        portfolio_value=0.0,
        safety_cap=safety_cap,
    )
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


def _resolved_lot_aware_add_increment(row: Mapping[str, Any]) -> float:
    direct = _ratio(row.get("lot_aware_accepted_incremental_weight"), 0.0)
    if direct > 0:
        return direct
    resolution = row.get("target_weight_resolution") if isinstance(row.get("target_weight_resolution"), Mapping) else {}
    lot_resolution = resolution.get("lot_aware_final_reallocation") if isinstance(resolution, Mapping) and isinstance(resolution.get("lot_aware_final_reallocation"), Mapping) else {}
    nested = _ratio(lot_resolution.get("accepted_lot_increment_weight") if isinstance(lot_resolution, Mapping) else None, 0.0)
    return nested if nested > 0 else 0.0


def _buy_quality_blocks_incremental_add(
    *,
    row: Mapping[str, Any],
    existing_position: bool,
    pm_action: str,
    adaptive_quality: Mapping[str, Any],
) -> bool:
    if not existing_position or pm_action != "ADD":
        return False
    quality_action = str(adaptive_quality.get("quality_action") or "").upper()
    quality_adjustment = _ratio(adaptive_quality.get("quality_allocation_adjustment"), 0.0)
    explicit_quality_adjustment = "quality_allocation_adjustment" in row
    return quality_action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE"} or (
        explicit_quality_adjustment and quality_adjustment <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
    )


def _raw_position(
    row: Mapping[str, Any],
    *,
    config: PositionSizingConfig,
    base: float,
    max_weight: float,
    portfolio_value: float,
    safety_cap: float | None = None,
) -> dict[str, Any]:
    code = str(row.get("security_code") or row.get("symbol") or "")
    membership = str(row.get("membership_intent") or "UNRESOLVED").upper()
    pm_action = str(row.get("pm_action") or ("NEW" if membership == "ADD_CANDIDATE" else "HOLD")).upper()
    if pm_action not in PM_ACTIONS:
        pm_action = "UNRESOLVED"
    current_weight = _ratio(row.get("current_weight"), 0.0)
    target_weight_resolution = resolve_target_weight(row)
    runtime_opportunity_resolution = resolve_runtime_opportunity_score(row)
    quality_resolution = resolve_quality_score(row)
    adaptive_quality = resolve_adaptive_buy_quality(row)
    quality = adaptive_quality["quality_allocation_adjustment"]
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
    reference_price_resolution = resolve_reference_price(row)
    price = _positive_float(reference_price_resolution["resolved_price"], 0.0)
    min_notional = _minimum_notional(config, price)
    current_quantity = _positive_float(row.get("current_quantity"), 0.0)
    trading_unit = _positive_float(row.get("trading_unit"), _positive_float(config.minimum_meaningful_notional.get("tradable_unit"), 100.0))
    existing_position = current_quantity > 0
    accepted_incremental_weight = _ratio(row.get("accepted_incremental_weight"), 0.0)
    lot_aware_accepted_incremental_weight = _resolved_lot_aware_add_increment(row)
    incremental_add_quality_blocked = _buy_quality_blocks_incremental_add(
        row=row,
        existing_position=existing_position,
        pm_action=pm_action,
        adaptive_quality=adaptive_quality,
    )
    if incremental_add_quality_blocked:
        accepted_incremental_weight = 0.0
        lot_aware_accepted_incremental_weight = 0.0
    quality_adjustment_scope = "BUY_NEW_TOTAL_TARGET"
    minimum_meaningful_notional_applied_to = "TOTAL_TARGET_NOTIONAL"
    position_type = "EXISTING_POSITION" if existing_position else "NEW_POSITION"
    baseline_quantity_preserved = False
    transaction_delta_weight = round(max(target - current_weight, 0.0), 6)
    transaction_target_notional = round(max((target - current_weight) * portfolio_value, 0.0), 2)
    transaction_quantity_candidate = 0
    reduce_fraction_candidate = _ratio(row.get("reduce_fraction"), 0.0) if pm_action == "REDUCE" else 0.0
    reduce_intensity = str(row.get("reduce_intensity") or row.get("pm_reduce_intensity") or "")
    raw_reduce_quantity = 0.0
    rounded_reduce_quantity = 0.0
    reduce_execution_semantic = ""
    reduce_executability_status = "NOT_APPLICABLE"
    reduce_intentional_no_order = False
    reduce_intentional_no_order_reason = ""
    reduce_final_sell_quantity = 0.0

    if existing_position and pm_action in {"HOLD", "ADD", "REDUCE", "EXIT", "UNRESOLVED"}:
        adjusted = target
        quality_adjustment_scope = "INCREMENTAL_TRANSACTION_ONLY" if pm_action == "ADD" else "NOT_APPLIED_TO_EXISTING_BASELINE"
        minimum_meaningful_notional_applied_to = "TRANSACTION_DELTA_NOTIONAL"
        reasons.append("existing_position_baseline_quantity_authoritative")
        if pm_action in {"HOLD", "ADD", "UNRESOLVED"}:
            baseline_quantity_preserved = True
        if incremental_add_quality_blocked:
            adjusted = current_weight
            target = current_weight
            reasons.append("BUY_QUALITY_BLOCKS_INCREMENTAL_ADD")
    else:
        adjusted = target * quality
    if pm_action == "EXIT" or membership in {"REMOVE_CANDIDATE", "EXCLUDE"}:
        adjusted = 0.0
    elif pm_action == "REDUCE":
        adjusted = min(adjusted, current_weight * 0.5) if not existing_position else min(target, current_weight)
    elif membership == "ADD_CANDIDATE" and adaptive_quality["quality_action"] in {"BUY_WAIT", "REVIEW_REQUIRED", "REJECT"}:
        adjusted = 0.0
        if adaptive_quality["quality_action"] == "BUY_WAIT":
            status = "QUALITY_WAIT"
            uncertainty = "BUY_QUALITY_WAIT"
        else:
            status = "QUALITY_UNAVAILABLE" if adaptive_quality["quality_action"] == "REVIEW_REQUIRED" else "WITHHELD"
            uncertainty = "BUY_QUALITY_REVIEW_REQUIRED" if adaptive_quality["quality_action"] == "REVIEW_REQUIRED" else "BUY_QUALITY_REJECTED"
        reasons.append("buy_quality_not_auto_submittable")
        reasons.append(str(adaptive_quality["review_reason"] or adaptive_quality["quality_action"]))
    strategy_soft_cap_overshoot_authorized = _lot_aware_strategy_cap_overshoot_authorized_row(row, target=max(adjusted, 0.0), strategy_cap=max_weight)
    unauthorized_new_exposure_overshoot = (
        not existing_position
        and membership == "ADD_CANDIDATE"
        and max_weight > TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        and max(adjusted, 0.0) > max_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        and not strategy_soft_cap_overshoot_authorized
    )
    capped = (
        max(adjusted, 0.0)
        if existing_position or strategy_soft_cap_overshoot_authorized or unauthorized_new_exposure_overshoot
        else min(max(adjusted, 0.0), max_weight)
    )
    if unauthorized_new_exposure_overshoot:
        reasons.append("unauthorized_strategy_cap_overshoot")
    if capped < adjusted:
        status = "CAPPED"
        reasons.append("position_concentration_cap_applied")
    target = round(capped, 6) if status in {"SIZED", "CAPPED"} else 0.0
    target_notional = round(target * portfolio_value, 2)
    target_quantity_candidate = 0
    price_required = target_notional > 0
    quantity_status = "RESOLVED_ZERO_DELTA" if current_quantity == 0 else "RESOLVED_CANDIDATE"
    one_lot_quantity_authority = _resolve_one_lot_discrete_quantity_authority(
        row,
        target=target,
        strategy_cap=max_weight,
        current_quantity=int(current_quantity),
        price=price,
        trading_unit=trading_unit,
    )
    pc_discrete_quantity_authority = _resolve_pc_discrete_executable_quantity_authority(
        row,
        target=target,
        strategy_cap=max_weight,
        current_quantity=int(current_quantity),
        price=price,
        trading_unit=trading_unit,
    )
    one_lot_authority_consumed = False
    pc_discrete_quantity_authority_consumed = False
    if existing_position and pm_action in {"HOLD", "UNRESOLVED"}:
        target_quantity_candidate = int(current_quantity)
        quantity_status = "RESOLVED_ZERO_DELTA"
        transaction_delta_weight = 0.0
        transaction_target_notional = 0.0
        reasons.append("existing_position_baseline_preserved_no_transaction_delta")
        if pm_action == "UNRESOLVED":
            status = "UNRESOLVED"
            uncertainty = "UNRESOLVED"
            reasons.append("pm_action_unresolved_no_implicit_exit")
    elif existing_position and pm_action == "ADD":
        if incremental_add_quality_blocked:
            increment_weight = 0.0
        else:
            increment_weight = (
                lot_aware_accepted_incremental_weight
                if lot_aware_accepted_incremental_weight > 0
                else accepted_incremental_weight
                if accepted_incremental_weight > 0
                else max(target - current_weight, 0.0)
            )
        transaction_delta_weight = round(max(increment_weight, 0.0), 6)
        transaction_target_notional = round(transaction_delta_weight * portfolio_value, 2)
        target_quantity_candidate = int(current_quantity)
        if transaction_delta_weight <= 0:
            quantity_status = "RESOLVED_ZERO_DELTA"
            reasons.append("ADD_TARGET_WEIGHT_UNCHANGED")
        elif reference_price_resolution["status"] != "PASS":
            quantity_status = "PRICE_UNAVAILABLE"
            reasons.append(str(reference_price_resolution["review_reason"] or "reference_price_unavailable"))
        else:
            transaction_quantity_candidate = _lot_quantity(transaction_target_notional, price=price, trading_unit=trading_unit)
            if pc_discrete_quantity_authority["authorized"] and pc_discrete_quantity_authority["semantic_type"] == "BUY_ADD":
                transaction_quantity_candidate = int(pc_discrete_quantity_authority["discrete_authorized_quantity"])
                transaction_target_notional = round(float(pc_discrete_quantity_authority["discrete_authorized_notional"]), 2)
                target_quantity_candidate = int(pc_discrete_quantity_authority["final_target_quantity"])
                quantity_status = "RESOLVED_CANDIDATE"
                pc_discrete_quantity_authority_consumed = True
                reasons.append("PC_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_CONSUMED")
                reasons.append("ADD_POSITIVE_QUANTITY_DELTA")
            elif one_lot_quantity_authority["authorized"] and one_lot_quantity_authority["semantic_type"] == "BUY_ADD":
                transaction_quantity_candidate = int(one_lot_quantity_authority["discrete_authorized_quantity"])
                transaction_target_notional = round(float(one_lot_quantity_authority["discrete_authorized_notional"]), 2)
                target_quantity_candidate = int(current_quantity) + transaction_quantity_candidate
                quantity_status = "RESOLVED_CANDIDATE"
                one_lot_authority_consumed = True
                reasons.append("ONE_LOT_DISCRETE_QUANTITY_AUTHORITY_CONSUMED")
                reasons.append("ADD_POSITIVE_QUANTITY_DELTA")
            elif transaction_quantity_candidate <= 0:
                quantity_status = "RESOLVED_ZERO_DELTA"
                transaction_quantity_candidate = 0
                reasons.append("ADD_INCREMENT_NOT_EXECUTABLE_BELOW_LOT")
            else:
                target_quantity_candidate = int(current_quantity) + transaction_quantity_candidate
                quantity_status = "RESOLVED_CANDIDATE"
                reasons.append("ADD_POSITIVE_QUANTITY_DELTA")
    elif existing_position and pm_action == "REDUCE":
        reduce_fraction = reduce_fraction_candidate
        if reduce_fraction <= 0.0 and current_weight > 0:
            reduce_fraction = max((current_weight - target) / current_weight, 0.0)
            reduce_fraction_candidate = reduce_fraction
        reduce_fraction = min(max(reduce_fraction, 0.0), 1.0)
        raw_reduce_quantity = current_quantity * reduce_fraction
        transaction_delta_weight = round(max(current_weight - target, 0.0), 6)
        transaction_target_notional = round(raw_reduce_quantity * price, 2) if price > 0 else 0.0
        target_quantity_candidate = int(current_quantity)
        if reference_price_resolution["status"] != "PASS":
            quantity_status = "PRICE_UNAVAILABLE"
            reasons.append(str(reference_price_resolution["review_reason"] or "reference_price_unavailable"))
        else:
            rounded_reduce_quantity = math.floor(raw_reduce_quantity / trading_unit) * trading_unit if trading_unit > 0 else 0
            transaction_quantity_candidate = rounded_reduce_quantity
            reduce_final_sell_quantity = transaction_quantity_candidate
            if rounded_reduce_quantity <= 0:
                transaction_quantity_candidate = 0
                reduce_final_sell_quantity = 0.0
                transaction_target_notional = 0.0
                quantity_status = "RESOLVED_ZERO_DELTA"
                reasons.append("REDUCE_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT")
                reasons.append(REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT)
                reasons.append("REDUCE_INTENTIONAL_NO_ORDER")
                reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
                reduce_executability_status = "INTENTIONAL_NO_ORDER"
                reduce_intentional_no_order = True
                reduce_intentional_no_order_reason = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
            elif rounded_reduce_quantity * price < min_notional:
                transaction_quantity_candidate = 0
                reduce_final_sell_quantity = 0.0
                transaction_target_notional = 0.0
                quantity_status = "RESOLVED_ZERO_DELTA"
                reasons.append("REDUCE_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT")
                reasons.append(REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL)
                reasons.append("REDUCE_INTENTIONAL_NO_ORDER")
                reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
                reduce_executability_status = "INTENTIONAL_NO_ORDER"
                reduce_intentional_no_order = True
                reduce_intentional_no_order_reason = REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
            else:
                target_quantity_candidate = int(max(current_quantity - transaction_quantity_candidate, 0))
                quantity_status = "RESOLVED_CANDIDATE"
                reasons.append("REDUCE_PARTIAL_QUANTITY_DELTA")
                reduce_execution_semantic = REDUCE_EXECUTABLE_SEMANTIC
                reduce_executability_status = "EXECUTABLE"
    elif price_required and reference_price_resolution["status"] != "PASS":
        quantity_status = "PRICE_UNAVAILABLE"
        reasons.append(str(reference_price_resolution["review_reason"] or "reference_price_unavailable"))
    elif price_required and price > 0 and trading_unit > 0:
        target_quantity_candidate = _lot_quantity(target_notional, price=price, trading_unit=trading_unit)
        if (
            one_lot_quantity_authority["authorized"]
            and one_lot_quantity_authority["semantic_type"] in {"BUY_NEW", "REENTRY"}
        ):
            target_quantity_candidate = int(one_lot_quantity_authority["final_target_quantity"])
            transaction_quantity_candidate = int(one_lot_quantity_authority["discrete_authorized_quantity"])
            transaction_target_notional = round(float(one_lot_quantity_authority["discrete_authorized_notional"]), 2)
            one_lot_authority_consumed = True
            reasons.append("ONE_LOT_DISCRETE_QUANTITY_AUTHORITY_CONSUMED")
        elif (
            pc_discrete_quantity_authority["authorized"]
            and pc_discrete_quantity_authority["semantic_type"] in {"BUY_NEW", "REENTRY"}
        ):
            target_quantity_candidate = int(pc_discrete_quantity_authority["final_target_quantity"])
            transaction_quantity_candidate = int(pc_discrete_quantity_authority["discrete_authorized_quantity"])
            transaction_target_notional = round(float(pc_discrete_quantity_authority["discrete_authorized_notional"]), 2)
            pc_discrete_quantity_authority_consumed = True
            reasons.append("PC_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_CONSUMED")
        quantity_status = "RESOLVED_ZERO_DELTA" if target_quantity_candidate == current_quantity else "RESOLVED_CANDIDATE"
    if status in {"SIZED", "CAPPED"} and not existing_position and 0 < target_notional < min_notional:
        reasons.append("minimum_meaningful_notional_diagnostic_unmet")
    quantity_delta_candidate = int(target_quantity_candidate - current_quantity)
    if pm_action == "ADD":
        bridge_status = str(row.get("add_allocation_eligibility_status") or "").upper()
        if quantity_delta_candidate > 0:
            reasons.append("ADD_POSITIVE_QUANTITY_DELTA")
        elif bridge_status == "FAIL_CLOSED" or transaction_delta_weight <= 0:
            reasons.append("ADD_TARGET_WEIGHT_UNCHANGED")
        elif target_notional <= round(current_weight * portfolio_value, 2):
            reasons.append("ADD_TARGET_NOTIONAL_DELTA_ZERO")
        elif target_quantity_candidate == current_quantity:
            reasons.append("ADD_LOT_ROUNDING_ZERO")
        else:
            reasons.append("ADD_POSITION_SIZING_ZERO_DELTA")
        if target_weight_resolution["status"] != "PASS":
            reasons.append("ADD_REQUIRED_EVIDENCE_MISSING")
    baseline_weight = _ratio(row.get("baseline_existing_weight"), current_weight)
    retained_baseline = (
        existing_position
        and pm_action in {"HOLD", "ADD"}
        and membership == "RETAIN"
        and accepted_incremental_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        and quantity_delta_candidate == 0
        and (
            abs(target - current_weight) <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
            or abs(target - baseline_weight) <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        )
    )
    risk_reducing = (
        existing_position
        and pm_action == "REDUCE"
        and quantity_delta_candidate <= 0
        and target <= current_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE
    )
    if target > max_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        if retained_baseline:
            reasons.append("EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT")
        elif risk_reducing:
            reasons.append("EXISTING_POSITION_RISK_REDUCING_ABOVE_CAP_ACCEPTED")
        elif _lot_aware_strategy_cap_overshoot_authorized_row(row, target=target, strategy_cap=max_weight):
            reasons.append("LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP")
    if safety_cap is not None and target > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        if retained_baseline:
            reasons.append("PASSIVE_CONCENTRATION_DRIFT_RETAINED")
            reasons.append("SAFETY_CAP_DRIFT_NO_RISK_INCREASE")
        elif risk_reducing:
            reasons.append("SAFETY_CAP_DRIFT_RISK_REDUCING_TRANSACTION_ALLOWED")
    zero_delta_taxonomy = _pc_ps_zero_delta_taxonomy(
        row,
        quantity_status=quantity_status,
        quantity_delta_candidate=quantity_delta_candidate,
        target=target,
        current_weight=current_weight,
        target_notional=target_notional,
        transaction_target_notional=transaction_target_notional,
        min_notional=min_notional,
        price=price,
        trading_unit=trading_unit,
        max_weight=max_weight,
        portfolio_value=portfolio_value,
    )
    canonical_sizing_evidence = _canonical_position_sizing_evidence(
        row=row,
        symbol=code,
        pm_action=pm_action,
        membership=membership,
        target_weight=target,
        current_weight=current_weight,
        target_notional=target_notional,
        transaction_target_notional=transaction_target_notional,
        transaction_quantity_candidate=int(transaction_quantity_candidate),
        quantity_delta_candidate=int(quantity_delta_candidate),
        quantity_status=quantity_status,
        sizing_status=status,
        price=price,
        trading_unit=trading_unit,
        max_weight=max_weight,
        safety_cap=safety_cap,
        portfolio_value=portfolio_value,
        min_notional=min_notional,
        zero_delta_taxonomy=zero_delta_taxonomy,
        reason_codes=reasons,
    )
    return {
        "security_code": code,
        "position_reference": str(row.get("position_reference") or row.get("member_id") or code),
        "membership_intent": membership,
        "pm_action": pm_action,
        "current_weight": round(current_weight, 6),
        "baseline_existing_weight": round(_ratio(row.get("baseline_existing_weight"), current_weight), 6),
        "base_weight": round(base, 6),
        "quality_adjustment": round(quality, 6),
        "buy_quality_adjustment": round(quality, 6),
        "quality_decision_id": adaptive_quality["quality_decision_id"],
        "quality_score": adaptive_quality["quality_score"],
        "quality_band": adaptive_quality["quality_band"],
        "quality_action": adaptive_quality["quality_action"],
        "quality_status": adaptive_quality["quality_status"],
        "quality_reason_codes": adaptive_quality["quality_reason_codes"],
        "quality_policy_version": adaptive_quality["quality_policy_version"],
        "component_scores": adaptive_quality["component_scores"],
        "component_statuses": adaptive_quality["component_statuses"],
        "buy_quality_authority": adaptive_quality["buy_quality_authority"],
        "pre_quality_base_weight": round(target, 6),
        "quality_allocation_adjustment": round(quality, 6),
        "post_quality_target_weight": round(capped, 6),
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
        "position_type": position_type,
        "baseline_quantity_preserved": baseline_quantity_preserved,
        "quality_adjustment_scope": quality_adjustment_scope,
        "minimum_meaningful_notional_applied_to": minimum_meaningful_notional_applied_to,
        "accepted_incremental_weight": round(accepted_incremental_weight, 6),
        "lot_aware_accepted_incremental_weight": round(lot_aware_accepted_incremental_weight, 6),
        "lot_aware_accepted_buy_new_weight": round(_ratio(row.get("lot_aware_accepted_buy_new_weight"), 0.0), 6),
        "add_allocation_eligibility_status": str(row.get("add_allocation_eligibility_status") or ""),
        "incremental_investment_value_state": str(row.get("incremental_investment_value_state") or ""),
        "opportunity_cost_status": str(row.get("opportunity_cost_status") or ""),
        "phase29_l19_lot_resolution": dict(row.get("phase29_l19_lot_resolution") or {}),
        "reduce_fraction": round(reduce_fraction_candidate, 6),
        "target_reduce_ratio": round(reduce_fraction_candidate, 6),
        "raw_reduce_quantity": round(raw_reduce_quantity, 6),
        "rounded_reduce_quantity": int(rounded_reduce_quantity),
        "reduce_final_sell_quantity": int(reduce_final_sell_quantity),
        "reduce_execution_semantic": reduce_execution_semantic,
        "reduce_executability_status": reduce_executability_status,
        "reduce_intentional_no_order": reduce_intentional_no_order,
        "reduce_intentional_no_order_reason": reduce_intentional_no_order_reason,
        "reduce_executability_evidence": {
            "source_decision": "REDUCE" if pm_action == "REDUCE" else "",
            "symbol": code,
            "reduce_intensity": reduce_intensity,
            "target_reduce_ratio": round(reduce_fraction_candidate, 6),
            "position_quantity_before": int(current_quantity) if pm_action == "REDUCE" else 0,
            "raw_reduce_quantity": round(raw_reduce_quantity, 6),
            "tradable_unit": int(trading_unit),
            "rounded_executable_quantity": int(rounded_reduce_quantity),
            "final_sell_quantity": int(reduce_final_sell_quantity),
            "execution_semantic": reduce_execution_semantic,
            "intentional_no_order": reduce_intentional_no_order,
            "intentional_no_order_reason": reduce_intentional_no_order_reason,
            "position_effect": "UNCHANGED"
            if reduce_intentional_no_order
            else ("REDUCED" if reduce_execution_semantic == REDUCE_EXECUTABLE_SEMANTIC else ""),
            "next_evaluation": "NEXT_DAILY_PM_REEVALUATION" if reduce_intentional_no_order else "",
        },
        "transaction_delta_weight": transaction_delta_weight,
        "transaction_target_notional": transaction_target_notional,
        "transaction_quantity_candidate": int(transaction_quantity_candidate),
        "continuous_target_notional": target_notional,
        "discrete_authorized_quantity": int(one_lot_quantity_authority["discrete_authorized_quantity"]),
        "discrete_authorized_notional": round(float(one_lot_quantity_authority["discrete_authorized_notional"]), 2),
        "pc_discrete_authorized_quantity": int(pc_discrete_quantity_authority["discrete_authorized_quantity"]),
        "pc_discrete_authorized_notional": round(float(pc_discrete_quantity_authority["discrete_authorized_notional"]), 2),
        "final_target_quantity": int(target_quantity_candidate),
        "final_quantity_delta": int(quantity_delta_candidate),
        "one_lot_authority_consumed": one_lot_authority_consumed,
        "pc_discrete_quantity_authority_consumed": pc_discrete_quantity_authority_consumed,
        "one_lot_authority_reason": str(one_lot_quantity_authority["authority_reason"] if one_lot_authority_consumed else ""),
        "pc_discrete_quantity_authority_reason": str(pc_discrete_quantity_authority["authority_reason"] if pc_discrete_quantity_authority_consumed else ""),
        "safety_hard_cap_validation": str(one_lot_quantity_authority["safety_hard_cap_validation"]),
        "target_weight_authority": dict(row.get("target_weight_authority") or {}),
        "target_weight_resolution": dict(target_weight_resolution),
        **_phase29_l16_strategy_evidence(row),
        "target_quantity_candidate": target_quantity_candidate,
        "current_quantity": int(current_quantity),
        "quantity_delta_candidate": quantity_delta_candidate,
        "quantity_status": quantity_status,
        "pc_ps_zero_delta_taxonomy": zero_delta_taxonomy,
        "canonical_sizing_evidence": canonical_sizing_evidence,
        "canonical_sizing_evidence_class": canonical_sizing_evidence["evidence_class"],
        "sizing_outcome_terminality": canonical_sizing_evidence["terminality"],
        "residual_capital_classification": canonical_sizing_evidence["residual_capital_classification"],
        "canonical_deployment_set_sizing_eligibility": str(row.get("canonical_deployment_set_sizing_eligibility") or ""),
        "canonical_deployment_set_hash": str(row.get("canonical_deployment_set_hash") or ""),
        "g61_lot_aware_compatibility_consumed_by_ps": bool(row.get("g61_lot_aware_compatibility_consumed_by_ps")),
        "g61_lot_aware_compatibility": dict(row.get("g61_lot_aware_compatibility") or {}),
        "lower_priority_implicit_promotion_allowed": bool(row.get("lower_priority_implicit_promotion_allowed")),
        "position_sizing_recomputes_capital_priority": bool(row.get("position_sizing_recomputes_capital_priority")),
        "ordinary_lot_feasibility_priority_redecision_allowed": bool(
            row.get("ordinary_lot_feasibility_priority_redecision_allowed")
        ),
        "final_capital_winner_type": str(row.get("final_capital_winner_type") or ""),
        "final_capital_winner_symbol": str(row.get("final_capital_winner_symbol") or ""),
        "final_capital_winner_binds_before_discrete_sizing": bool(row.get("final_capital_winner_binds_before_discrete_sizing")),
        "deployment_competitor_type": str(row.get("deployment_competitor_type") or _deployment_competitor_type(row)),
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
        "legacy_allocation_quality_score": quality_resolution.resolved_quality,
        "legacy_allocation_quality_authority": quality_resolution.authority,
        "legacy_allocation_quality_resolution": quality_resolution.to_dict(),
        "confidence": round(min(_ratio(row.get("confidence"), 1.0), _ratio(row.get("opportunity_confidence"), 1.0)), 6),
        "uncertainty": uncertainty,
        "reason_codes": sorted(set(reasons)),
    }


def _phase29_l16_strategy_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "semantic_buy_type",
        "prior_exit_business_date",
        "business_days_since_exit",
        "reentry_cooldown_threshold_bd",
        "reentry_cooldown_status",
        "reentry_recovery_status",
        "reentry_recovery_reason",
        "reentry_rank",
        "reentry_expected_edge",
        "reentry_buy_quality_action",
        "reentry_trend_close_over_ma_20d",
        "reentry_price_momentum_return_20d",
        "reentry_corporate_action_status",
        "single_tick_pct",
        "price_tick_risk_tier",
        "rolling_median_traded_value_20",
        "rolling_median_traded_value_20_authority",
        "rolling_median_traded_value_20_resolution",
        "capacity_source",
        "capacity_source_field",
        "capacity_ratio",
        "liquidity_capacity_status",
        "normal_target_weight",
        "price_tick_cap_weight",
        "liquidity_capacity_cap_weight",
        "final_risk_adjusted_target_weight",
        "allocation_cap_reason",
    )
    return {field: row.get(field) for field in fields if field in row}


def _pc_ps_zero_delta_taxonomy(
    row: Mapping[str, Any],
    *,
    quantity_status: str,
    quantity_delta_candidate: int,
    target: float,
    current_weight: float,
    target_notional: float,
    transaction_target_notional: float,
    min_notional: float,
    price: float,
    trading_unit: float,
    max_weight: float,
    portfolio_value: float,
) -> dict[str, Any]:
    if quantity_status != "RESOLVED_ZERO_DELTA" or quantity_delta_candidate > 0:
        classification = "NOT_APPLICABLE"
    else:
        quality_action = str(row.get("quality_action") or "").upper()
        selection_tier = str(row.get("selection_quality_tier") or "").upper()
        membership = str(row.get("membership_intent") or "").upper()
        pm_action = str(row.get("pm_action") or "").upper()
        positive_target = target > current_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE if bool(row.get("current_position")) else target > 0
        one_lot_notional = price * trading_unit if price > 0 and trading_unit > 0 else 0.0
        one_lot_weight = one_lot_notional / portfolio_value if portfolio_value > 0 and one_lot_notional > 0 else 0.0
        concentration_headroom = max(max_weight - current_weight, 0.0)
        draft_notional = max(transaction_target_notional, target_notional if not row.get("current_position") else 0.0, 0.0)
        if quality_action in {"BUY_WAIT", "REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED", "REJECT", "BUY_REJECTED"} or selection_tier in {
            "CAUTION_CONTINUATION",
            "INSUFFICIENT_QUALITY",
            "REJECT",
        }:
            classification = "QUALITY_DEFERRED_TO_CASH"
        elif not positive_target or membership in {"EXCLUDE", "UNRESOLVED"} or pm_action in {"HOLD", "UNRESOLVED"}:
            classification = "ZERO_INCREMENTAL_TARGET"
        elif one_lot_weight > 0 and concentration_headroom + TARGET_WEIGHT_ABSOLUTE_TOLERANCE < one_lot_weight:
            classification = "CONCENTRATION_HEADROOM_LIMIT"
        elif one_lot_notional > 0 and draft_notional < one_lot_notional:
            classification = "GENUINE_LOT_INFEASIBILITY"
        elif 0 < draft_notional < min_notional:
            classification = "MINIMUM_MEANINGFUL_NOTIONAL"
        else:
            classification = "RESIDUAL_CAPITAL_TOO_SMALL"
    return {
        "schema_version": "pc_ps_zero_delta_taxonomy.v1",
        "classification": classification,
        "quantity_status": quantity_status,
        "quantity_delta_candidate": int(quantity_delta_candidate),
        "target_weight": round(target, TARGET_WEIGHT_DECIMALS),
        "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
        "rank_score_not_action_authority": True,
        "selection_quality_tier": str(row.get("selection_quality_tier") or ""),
        "future_information_used": False,
    }


def _canonical_position_sizing_evidence(
    *,
    row: Mapping[str, Any],
    symbol: str,
    pm_action: str,
    membership: str,
    target_weight: float,
    current_weight: float,
    target_notional: float,
    transaction_target_notional: float,
    transaction_quantity_candidate: int,
    quantity_delta_candidate: int,
    quantity_status: str,
    sizing_status: str,
    price: float,
    trading_unit: float,
    max_weight: float,
    safety_cap: float | None,
    portfolio_value: float,
    min_notional: float,
    zero_delta_taxonomy: Mapping[str, Any],
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    executable_quantity = abs(int(transaction_quantity_candidate or quantity_delta_candidate or 0))
    executable_notional = round(executable_quantity * price, 2) if price > 0 else 0.0
    requested_notional = round(max(transaction_target_notional, target_notional if not bool(row.get("current_position")) else 0.0, 0.0), 2)
    residual_notional = round(max(requested_notional - executable_notional, 0.0), 2)
    classification = str(zero_delta_taxonomy.get("classification") or "")
    evidence_class = "EXECUTABLE"
    terminality = "EXECUTABLE"
    constraint_reason_codes: list[str] = []
    if sizing_status in {"TARGET_WEIGHT_UNAVAILABLE", "QUALITY_UNAVAILABLE", "VOLATILITY_UNAVAILABLE", "UPSTREAM_REVIEW_REQUIRED"} or quantity_status == "PRICE_UNAVAILABLE":
        evidence_class = "UNAVAILABLE_AUTHORITY"
        terminality = "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY"
        constraint_reason_codes.append("UNAVAILABLE_AUTHORITY")
    elif quantity_delta_candidate == 0 and quantity_status == "RESOLVED_ZERO_DELTA":
        if classification == "GENUINE_LOT_INFEASIBILITY":
            evidence_class = "LOT_INFEASIBLE"
            terminality = "RECONSIDERABLE"
            constraint_reason_codes.append("LOT_INFEASIBLE")
        elif classification == "CONCENTRATION_HEADROOM_LIMIT":
            evidence_class = "STRATEGY_CAP_BOUND"
            terminality = "RECONSIDERABLE"
            constraint_reason_codes.append("STRATEGY_CAP_BOUND")
        elif classification in {"ZERO_INCREMENTAL_TARGET", "QUALITY_DEFERRED_TO_CASH"}:
            evidence_class = "NO_POSITIVE_QUANTITY_DELTA"
            terminality = "RECONSIDERABLE" if pm_action == "ADD" else "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY"
            constraint_reason_codes.append("NO_POSITIVE_QUANTITY_DELTA")
        elif classification in {"RESIDUAL_CAPITAL_TOO_SMALL", "MINIMUM_MEANINGFUL_NOTIONAL"}:
            evidence_class = "INSUFFICIENT_CASH"
            terminality = "RECONSIDERABLE"
            constraint_reason_codes.append("INSUFFICIENT_CASH")
        else:
            evidence_class = "INVALID_INPUT"
            terminality = "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY"
            constraint_reason_codes.append("UNEXPLAINED_ZERO_QUANTITY")
    if safety_cap is not None and target_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        evidence_class = "SAFETY_CAP_BOUND"
        terminality = "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY"
        constraint_reason_codes.append("SAFETY_CAP_BOUND")
    elif target_weight > max_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE and evidence_class != "SAFETY_CAP_BOUND":
        evidence_class = "STRATEGY_CAP_BOUND"
        terminality = "RECONSIDERABLE"
        constraint_reason_codes.append("STRATEGY_CAP_BOUND")
    residual_class = _canonical_residual_capital_classification(
        evidence_class=evidence_class,
        terminality=terminality,
        residual_notional=residual_notional,
        requested_notional=requested_notional,
    )
    return {
        "schema_version": CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION,
        "symbol": symbol,
        "intent_type": _canonical_sizing_intent_type(row=row, pm_action=pm_action, membership=membership),
        "evidence_class": evidence_class,
        "terminality": terminality,
        "requested_notional": requested_notional,
        "requested_weight": round(target_weight if not bool(row.get("current_position")) else max(target_weight - current_weight, 0.0), TARGET_WEIGHT_DECIMALS),
        "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
        "target_weight": round(target_weight, TARGET_WEIGHT_DECIMALS),
        "executable_quantity": executable_quantity,
        "executable_notional": executable_notional,
        "quantity_delta": int(quantity_delta_candidate),
        "lot_size": int(trading_unit),
        "lot_size_authority": "POSITION_SIZING_CONFIG",
        "residual_capital": residual_notional,
        "residual_capital_weight": round(residual_notional / portfolio_value, TARGET_WEIGHT_DECIMALS) if portfolio_value > 0 else 0.0,
        "residual_capital_classification": residual_class,
        "minimum_meaningful_notional": round(min_notional, 2),
        "constraint_reason_codes": sorted(set(constraint_reason_codes or reason_codes)),
        "quantity_authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
        "raw_zero_quantity_reinterpreted": False,
        "zero_quantity_reason_required": quantity_delta_candidate == 0,
        "unexplained_zero_quantity_fail_closed": evidence_class == "INVALID_INPUT",
        "future_information_used": False,
    }


def _canonical_residual_capital_classification(
    *,
    evidence_class: str,
    terminality: str,
    residual_notional: float,
    requested_notional: float,
) -> str:
    if evidence_class == "EXECUTABLE" and residual_notional <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return "VALID_POLICY_RESERVE"
    if evidence_class == "LOT_INFEASIBLE":
        return "REALLOCATABLE_RESIDUAL" if requested_notional > 0 else "UNAVOIDABLE_LOT_RESIDUAL"
    if evidence_class == "INSUFFICIENT_CASH":
        return "UNAVOIDABLE_LOT_RESIDUAL"
    if evidence_class == "SAFETY_CAP_BOUND":
        return "VALID_SAFETY_RESERVE"
    if terminality == "RECONSIDERABLE":
        return "REALLOCATABLE_RESIDUAL"
    if evidence_class in {"UNAVAILABLE_AUTHORITY", "INVALID_INPUT"}:
        return "NO_VALID_COMPETITOR"
    return "VALID_POLICY_RESERVE"


def _canonical_sizing_intent_type(*, row: Mapping[str, Any], pm_action: str, membership: str) -> str:
    if bool(row.get("current_position")) and pm_action == "ADD":
        return "ADD"
    if not bool(row.get("current_position")) and membership == "ADD_CANDIDATE":
        return "NEW_BUY"
    if pm_action in {"REDUCE", "EXIT"}:
        return pm_action
    return "NO_ACTION"


def _canonical_sizing_evidence_summary(
    positions: Sequence[Mapping[str, Any]],
    lot_feasibility_preflight: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    evidence = [dict(item.get("canonical_sizing_evidence") or {}) for item in positions if isinstance(item, Mapping)]
    evidence = [item for item in evidence if item]
    classes = sorted(set(str(item.get("evidence_class") or "") for item in evidence if item.get("evidence_class")))
    return {
        "schema_version": CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION,
        "authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
        "evidence_classes": classes,
        "position_evidence_count": len(evidence),
        "lot_preflight_evidence_count": len(lot_feasibility_preflight),
        "raw_zero_quantity_reinterpretation": False,
        "zero_quantity_reason_required": True,
        "unexplained_zero_quantity_fail_closed": True,
        "position_sizing_decides_reconsideration": False,
    }


def _lot_preflight_required(row: Mapping[str, Any]) -> bool:
    membership = str(row.get("membership_intent") or "").upper()
    pm_action = str(row.get("pm_action") or "").upper()
    target = _ratio(row.get("target_weight"), 0.0)
    current = _ratio(row.get("current_weight"), 0.0)
    requested_add = _ratio(row.get("requested_incremental_weight"), 0.0)
    requested_buy_new = _ratio(row.get("requested_buy_new_weight"), 0.0)
    if membership == "ADD_CANDIDATE" and not row.get("current_position") and target > 0:
        return True
    if membership == "ADD_CANDIDATE" and not row.get("current_position") and requested_buy_new > 0:
        return True
    if bool(row.get("current_position")) and pm_action == "ADD" and requested_add > 0:
        return True
    return bool(row.get("current_position")) and pm_action == "ADD" and target > current


def _lot_feasibility_row(
    row: Mapping[str, Any],
    *,
    business_date: str,
    portfolio_value: float,
    config: PositionSizingConfig,
    safety_cap: float | None = None,
) -> dict[str, Any]:
    symbol = str(row.get("security_code") or row.get("symbol") or "")
    membership = str(row.get("membership_intent") or "").upper()
    pm_action = str(row.get("pm_action") or ("NEW" if membership == "ADD_CANDIDATE" else "")).upper()
    current_weight = _ratio(row.get("current_weight"), 0.0)
    target_weight = _ratio(row.get("target_weight"), 0.0)
    requested_add = _ratio(row.get("requested_incremental_weight"), 0.0)
    requested_buy_new = _ratio(row.get("requested_buy_new_weight"), 0.0)
    current_quantity = _positive_float(row.get("current_quantity"), 0.0)
    reference_price_resolution = resolve_reference_price(row)
    price = _positive_float(reference_price_resolution["resolved_price"], 0.0)
    trading_unit = _positive_float(row.get("trading_unit"), _positive_float(config.minimum_meaningful_notional.get("tradable_unit"), 100.0))
    min_notional = _minimum_notional(config, price)
    draft_target_notional = round(target_weight * portfolio_value, 2)
    current_notional = round(current_weight * portfolio_value, 2)
    draft_delta_notional = round(max(draft_target_notional - current_notional, 0.0), 2)
    intent_type = "BUY_ADD" if bool(row.get("current_position")) and pm_action == "ADD" else "BUY_NEW"
    requested_basis_notional = round((requested_add if intent_type == "BUY_ADD" else requested_buy_new) * portfolio_value, 2)
    target_basis_notional = max(draft_delta_notional if intent_type == "BUY_ADD" else draft_target_notional, requested_basis_notional)
    draft_quantity_delta = _lot_quantity(target_basis_notional, price=price, trading_unit=trading_unit) if price > 0 and trading_unit > 0 else 0
    min_qty = int(trading_unit) if trading_unit > 0 else 0
    broker_eligible = str(row.get("broker_eligibility_status") or "PASS") != "FAIL_CLOSED"
    capital_feasible = portfolio_value > 0 and min_notional <= portfolio_value
    concentration_cap = config.strategy_maximum_position_weight
    concentration_headroom = max(concentration_cap - current_weight, 0.0)
    safety_hard_cap = safety_cap if safety_cap is not None else concentration_cap
    safety_headroom = max(float(safety_hard_cap) - current_weight, 0.0)
    one_lot_notional = price * trading_unit if price > 0 and trading_unit > 0 else 0.0
    one_lot_weight = one_lot_notional / portfolio_value if portfolio_value > 0 and one_lot_notional > 0 else 0.0
    minimum_executable_weight = round(one_lot_weight, TARGET_WEIGHT_DECIMALS) if one_lot_weight > 0 else None
    one_lot_post_trade_weight = None if minimum_executable_weight is None else round(current_weight + minimum_executable_weight, TARGET_WEIGHT_DECIMALS)
    concentration_feasible = minimum_executable_weight is not None and minimum_executable_weight <= concentration_headroom + TARGET_WEIGHT_ABSOLUTE_TOLERANCE
    positive_investment_intent = target_basis_notional > 0
    requested_lots = int(target_basis_notional // one_lot_notional) if one_lot_notional > 0 else 0
    minimum_policy_lots = int(math.ceil(min_notional / one_lot_notional)) if one_lot_notional > 0 and min_notional > 0 else 0
    maximum_strategy_feasible_lots = int(max(math.floor((concentration_headroom * portfolio_value) / one_lot_notional), 0)) if one_lot_notional > 0 and portfolio_value > 0 else 0
    maximum_safety_feasible_lots = int(max(math.floor((safety_headroom * portfolio_value) / one_lot_notional), 0)) if one_lot_notional > 0 and portfolio_value > 0 else 0
    one_lot_safety_feasible = maximum_safety_feasible_lots >= 1
    one_lot_strategy_feasible = maximum_strategy_feasible_lots >= 1
    strategy_cap_overshoot_eligible = (
        positive_investment_intent
        and not one_lot_strategy_feasible
        and one_lot_safety_feasible
    )
    executable_lots = 0
    expression_lots = max(requested_lots, 1 if positive_investment_intent else 0)
    if expression_lots > 0:
        lot_cap = maximum_safety_feasible_lots if strategy_cap_overshoot_eligible else maximum_strategy_feasible_lots
        executable_lots = min(expression_lots, lot_cap)
    executable_quantity_delta = int(executable_lots * trading_unit)
    one_minimum_policy_lot_post_trade_weight = round(current_weight + one_lot_weight, TARGET_WEIGHT_DECIMALS) if one_lot_weight > 0 else None
    if positive_investment_intent and not one_lot_safety_feasible:
        boundary_classification = "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX"
    elif positive_investment_intent and not one_lot_strategy_feasible:
        boundary_classification = "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX"
    elif executable_lots > 0:
        boundary_classification = "CAP_CONSTRAINED_LOT_EXECUTABLE"
    elif not positive_investment_intent:
        boundary_classification = "NO_POSITIVE_INVESTMENT_INTENT"
    elif target_basis_notional < min_notional:
        boundary_classification = "REQUEST_BELOW_MINIMUM_EXECUTABLE_NOTIONAL"
    else:
        boundary_classification = "NO_EXECUTABLE_LOT"
    lot_feasible = (
        reference_price_resolution["status"] == "PASS"
        and broker_eligible
        and positive_investment_intent
        and one_lot_safety_feasible
        and one_lot_notional > 0
    )
    reason_codes: list[str] = []
    if reference_price_resolution["status"] != "PASS":
        reason_codes.append("reference_price_unavailable")
    if not broker_eligible:
        reason_codes.append("broker_eligibility_fail_closed")
    if target_basis_notional < min_notional:
        reason_codes.append("minimum_meaningful_notional_diagnostic_unmet")
    if draft_quantity_delta <= 0:
        reason_codes.append("below_minimum_tradable_quantity")
    if positive_investment_intent and not one_lot_safety_feasible:
        reason_codes.append("minimum_lot_exceeds_safety_hard_cap")
    if not concentration_feasible and not strategy_cap_overshoot_eligible:
        reason_codes.append("minimum_lot_exceeds_concentration_headroom")
    if reference_price_resolution["status"] != "PASS":
        feasibility_classification = "UNKNOWN_FAIL_CLOSED"
    elif not broker_eligible:
        feasibility_classification = "BROKER_OR_SAFETY_BLOCKED"
    elif positive_investment_intent and not one_lot_safety_feasible:
        feasibility_classification = "SAFETY_HARD_BLOCKED"
    elif not concentration_feasible and not strategy_cap_overshoot_eligible:
        feasibility_classification = "CONCENTRATION_BLOCKED"
    elif lot_feasible:
        feasibility_classification = "EXECUTABLE_NOW"
    elif capital_feasible and minimum_executable_weight is not None:
        feasibility_classification = "EXECUTABLE_IF_RECYCLED"
    else:
        feasibility_classification = "CAPITAL_BLOCKED"
    canonical_preflight_evidence = _canonical_lot_preflight_sizing_evidence(
        symbol=symbol,
        intent_type=intent_type,
        boundary_classification=boundary_classification,
        feasibility_classification=feasibility_classification,
        target_basis_notional=target_basis_notional,
        executable_quantity_delta=executable_quantity_delta,
        one_lot_notional=one_lot_notional,
        trading_unit=trading_unit,
        current_weight=current_weight,
        target_weight=target_weight,
        one_lot_weight=one_lot_weight,
        portfolio_value=portfolio_value,
        reason_codes=reason_codes,
    )
    return {
        "schema_version": LOT_FEASIBILITY_SCHEMA_VERSION,
        "symbol": symbol,
        "business_date": business_date,
        "side": "BUY",
        "intent_type": intent_type,
        "reference_price": price if reference_price_resolution["status"] == "PASS" else None,
        "reference_price_resolution": reference_price_resolution,
        "tradable_unit": int(trading_unit),
        "minimum_executable_quantity": min_qty,
        "minimum_executable_notional": round(one_lot_notional, 2),
        "minimum_executable_weight": round(one_lot_weight, TARGET_WEIGHT_DECIMALS) if one_lot_weight > 0 else minimum_executable_weight,
        "minimum_meaningful_notional": round(min_notional, 2),
        "minimum_meaningful_notional_policy_status": "DIAGNOSTIC_ONLY",
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
            "requested_target_weight": round(target_weight, TARGET_WEIGHT_DECIMALS),
            "requested_incremental_weight": round(max(target_weight - current_weight, requested_add if intent_type == "BUY_ADD" else requested_buy_new, 0.0), TARGET_WEIGHT_DECIMALS),
            "strategy_cap_weight": round(concentration_cap, TARGET_WEIGHT_DECIMALS),
            "strategy_target_cap": round(concentration_cap, TARGET_WEIGHT_DECIMALS),
            "safety_hard_cap_weight": round(float(safety_hard_cap), TARGET_WEIGHT_DECIMALS),
            "safety_hard_cap": round(float(safety_hard_cap), TARGET_WEIGHT_DECIMALS),
            "remaining_strategy_headroom": round(concentration_headroom, TARGET_WEIGHT_DECIMALS),
            "remaining_safety_headroom": round(safety_headroom, TARGET_WEIGHT_DECIMALS),
            "one_lot_notional": round(one_lot_notional, 2),
            "one_lot_weight": round(one_lot_weight, TARGET_WEIGHT_DECIMALS),
            "one_lot_quantity": int(trading_unit),
            "one_lot_feasibility_status": "PASS" if lot_feasible else "FAIL_CLOSED",
            "one_lot_fallback_applied": lot_feasible and draft_quantity_delta <= 0,
            "normal_lot_quantity": int(draft_quantity_delta),
            "continuous_target_weight": round(target_weight, TARGET_WEIGHT_DECIMALS),
            "continuous_target_notional": round(target_basis_notional, 2),
            "previous_meaningful_notional_threshold": round(min_notional, 2),
            "minimum_meaningful_notional_policy_status": "DIAGNOSTIC_ONLY",
            "minimum_policy_lots": minimum_policy_lots,
            "minimum_policy_lot_weight": round(max(minimum_policy_lots, 1) * one_lot_weight, TARGET_WEIGHT_DECIMALS) if one_lot_weight > 0 else 0.0,
            "post_trade_weight": one_minimum_policy_lot_post_trade_weight,
            "maximum_strategy_feasible_lots": maximum_strategy_feasible_lots,
            "maximum_safety_feasible_lots": maximum_safety_feasible_lots,
            "requested_lots": requested_lots,
            "executable_lots": executable_lots,
            "executable_quantity_delta": executable_quantity_delta,
            "boundary_classification": boundary_classification,
            "strategy_cap_overshoot_applied": strategy_cap_overshoot_eligible,
            "strategy_cap_overshoot_weight": round(max((one_minimum_policy_lot_post_trade_weight or 0.0) - concentration_cap, 0.0), TARGET_WEIGHT_DECIMALS),
            "safety_margin_after_trade": round(max(float(safety_hard_cap) - (one_minimum_policy_lot_post_trade_weight or current_weight), 0.0), TARGET_WEIGHT_DECIMALS),
            "lot_overshoot_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP" if strategy_cap_overshoot_eligible else "",
            "strategy_cap_preserved": True,
            "safety_hard_cap_preserved": one_lot_safety_feasible if positive_investment_intent else True,
        },
        "draft_target_weight": round(target_weight, TARGET_WEIGHT_DECIMALS),
        "draft_target_notional": draft_target_notional,
        "requested_basis_notional": requested_basis_notional,
        "target_basis_notional": round(target_basis_notional, 2),
        "current_quantity": int(current_quantity),
        "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
        "current_notional": current_notional,
        "draft_quantity_delta": int(draft_quantity_delta),
        "draft_delta_notional": draft_delta_notional,
        "lot_feasible": lot_feasible,
        "capital_feasible": capital_feasible,
        "concentration_feasible": concentration_feasible,
        "concentration_cap": round(concentration_cap, TARGET_WEIGHT_DECIMALS),
        "concentration_headroom_weight": round(concentration_headroom, TARGET_WEIGHT_DECIMALS),
        "one_lot_post_trade_weight": one_lot_post_trade_weight,
        "lot_first_feasibility_classification": feasibility_classification,
        "canonical_sizing_evidence": canonical_preflight_evidence,
        "canonical_sizing_evidence_class": canonical_preflight_evidence["evidence_class"],
        "sizing_outcome_terminality": canonical_preflight_evidence["terminality"],
        "residual_capital_classification": canonical_preflight_evidence["residual_capital_classification"],
        "broker_eligible": broker_eligible,
        "producer_result_status": "PASS" if lot_feasible else "REVIEW_REQUIRED",
        "reason_codes": sorted(set(reason_codes)),
        "source_lineage": {
            "position_reference": str(row.get("position_reference") or row.get("member_id") or ""),
            "target_weight_authority": dict(row.get("target_weight_authority") or {}),
            "reference_price_authority": dict(row.get("reference_price_authority") or {}),
        },
    }


def _canonical_lot_preflight_sizing_evidence(
    *,
    symbol: str,
    intent_type: str,
    boundary_classification: str,
    feasibility_classification: str,
    target_basis_notional: float,
    executable_quantity_delta: int,
    one_lot_notional: float,
    trading_unit: float,
    current_weight: float,
    target_weight: float,
    one_lot_weight: float,
    portfolio_value: float,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    evidence_class = "EXECUTABLE"
    terminality = "EXECUTABLE"
    constraint_reasons: list[str] = []
    if boundary_classification == "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX" or feasibility_classification == "SAFETY_HARD_BLOCKED":
        evidence_class = "SAFETY_CAP_BOUND"
        terminality = "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY"
        constraint_reasons.append("SAFETY_CAP_BOUND")
    elif boundary_classification == "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX" or feasibility_classification == "CONCENTRATION_BLOCKED":
        evidence_class = "STRATEGY_CAP_BOUND"
        terminality = "RECONSIDERABLE"
        constraint_reasons.append("STRATEGY_CAP_BOUND")
    elif boundary_classification == "NO_POSITIVE_INVESTMENT_INTENT":
        evidence_class = "NO_POSITIVE_QUANTITY_DELTA"
        terminality = "RECONSIDERABLE"
        constraint_reasons.append("NO_POSITIVE_QUANTITY_DELTA")
    elif boundary_classification in {"REQUEST_BELOW_MINIMUM_EXECUTABLE_NOTIONAL", "NO_EXECUTABLE_LOT"}:
        evidence_class = "LOT_INFEASIBLE"
        terminality = "RECONSIDERABLE"
        constraint_reasons.append("LOT_INFEASIBLE")
    elif executable_quantity_delta <= 0:
        evidence_class = "INSUFFICIENT_CASH"
        terminality = "RECONSIDERABLE"
        constraint_reasons.append("INSUFFICIENT_CASH")
    executable_notional = round(max(executable_quantity_delta, 0) / max(trading_unit, 1.0) * one_lot_notional, 2)
    residual = round(max(target_basis_notional - executable_notional, 0.0), 2)
    return {
        "schema_version": CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION,
        "symbol": symbol,
        "intent_type": "ADD" if intent_type == "BUY_ADD" else "NEW_BUY",
        "evidence_class": evidence_class,
        "terminality": terminality,
        "requested_notional": round(target_basis_notional, 2),
        "requested_weight": round(max(target_weight - current_weight, target_weight if intent_type == "BUY_NEW" else 0.0), TARGET_WEIGHT_DECIMALS),
        "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
        "target_weight": round(target_weight, TARGET_WEIGHT_DECIMALS),
        "executable_quantity": int(max(executable_quantity_delta, 0)),
        "executable_notional": executable_notional,
        "quantity_delta": int(max(executable_quantity_delta, 0)),
        "lot_size": int(trading_unit),
        "lot_size_authority": "POSITION_SIZING_CONFIG",
        "residual_capital": residual,
        "residual_capital_weight": round(residual / portfolio_value, TARGET_WEIGHT_DECIMALS) if portfolio_value > 0 else 0.0,
        "residual_capital_classification": _canonical_residual_capital_classification(
            evidence_class=evidence_class,
            terminality=terminality,
            residual_notional=residual,
            requested_notional=target_basis_notional,
        ),
        "constraint_reason_codes": sorted(set(constraint_reasons or reason_codes)),
        "quantity_authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
        "raw_zero_quantity_reinterpreted": False,
        "zero_quantity_reason_required": executable_quantity_delta <= 0,
        "unexplained_zero_quantity_fail_closed": evidence_class == "INVALID_INPUT",
        "future_information_used": False,
    }


def _unresolved_position(row: Mapping[str, Any], *, config: PositionSizingConfig | None, safety_cap: float | None) -> dict[str, Any]:
    max_weight = min(config.strategy_maximum_position_weight, safety_cap) if config and safety_cap is not None else safety_cap or 0.0
    current_weight = _ratio(row.get("current_weight"), 0.0)
    canonical_sizing_evidence = {
        "schema_version": CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION,
        "symbol": str(row.get("security_code") or row.get("symbol") or ""),
        "intent_type": "UNRESOLVED",
        "evidence_class": "UNAVAILABLE_AUTHORITY",
        "terminality": "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY",
        "requested_notional": 0.0,
        "requested_weight": 0.0,
        "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
        "target_weight": 0.0,
        "executable_quantity": 0,
        "executable_notional": 0.0,
        "quantity_delta": 0,
        "lot_size": 0,
        "lot_size_authority": "",
        "residual_capital": 0.0,
        "residual_capital_weight": 0.0,
        "residual_capital_classification": "NO_VALID_COMPETITOR",
        "constraint_reason_codes": ["UNAVAILABLE_AUTHORITY"],
        "quantity_authority_owner": "POSITION_SIZING",
        "pc_reconsideration_owner": "PORTFOLIO_CONSTRUCTION",
        "raw_zero_quantity_reinterpreted": False,
        "zero_quantity_reason_required": True,
        "unexplained_zero_quantity_fail_closed": False,
        "future_information_used": False,
    }
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
        "canonical_sizing_evidence": canonical_sizing_evidence,
        "canonical_sizing_evidence_class": canonical_sizing_evidence["evidence_class"],
        "sizing_outcome_terminality": canonical_sizing_evidence["terminality"],
        "residual_capital_classification": canonical_sizing_evidence["residual_capital_classification"],
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
    adaptive_buy_quality_present = isinstance(row.get("buy_quality_authority"), Mapping) or bool(row.get("quality_decision_id"))
    for field in (ALLOCATION_QUALITY_CANONICAL_FIELD, ALLOCATION_QUALITY_LEGACY_FIELD):
        if field not in row:
            continue
        if field == ALLOCATION_QUALITY_LEGACY_FIELD and adaptive_buy_quality_present:
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


def resolve_adaptive_buy_quality(row: Mapping[str, Any]) -> dict[str, Any]:
    action = str(row.get("quality_action") or "")
    status = str(row.get("quality_status") or "")
    score = _optional_quality_score(row.get("quality_score"))
    adjustment_raw = _optional_quality_score(row.get("quality_allocation_adjustment"))
    decision_id = str(row.get("quality_decision_id") or "")
    authority = dict(row.get("buy_quality_authority") or {})
    canonical_actions = {
        "FULL_ALLOCATION_ELIGIBLE",
        "REDUCED_ALLOCATION_ONLY",
        "BUY_WAIT",
        "TEMPORARY_BUY_INELIGIBLE",
        "REVIEW_REQUIRED",
        "BUY_REVIEW_REQUIRED",
        "REJECT",
        "BUY_REJECTED",
    }
    if action and action not in canonical_actions:
        authority_action = str(row.get("legacy_buy_quality_action") or authority.get("quality_action") or "")
        if authority_action in canonical_actions:
            action = authority_action
            if not decision_id:
                decision_id = str(authority.get("quality_decision_id") or "")
            if score is None:
                score = _optional_quality_score(authority.get("quality_score"))
            if not status:
                status = "PASS"
    if not decision_id or not action:
        reason_codes = {str(item) for item in row.get("reason_codes") or []}
        if "buy_quality_full_allocation_eligible" in reason_codes:
            return _adaptive_quality_result(
                row,
                action="FULL_ALLOCATION_ELIGIBLE",
                status=status or "PASS",
                adjustment=1.0,
                reason="buy_quality_action_resolved_from_portfolio_construction_reason_code",
            )
        if "buy_quality_reduced_allocation_only" in reason_codes:
            return _adaptive_quality_result(
                row,
                action="REDUCED_ALLOCATION_ONLY",
                status=status or "PASS",
                adjustment=adjustment_raw if adjustment_raw is not None else (min(max(score or 0.0, 0.25), 0.85) if score is not None else 0.0),
                reason="buy_quality_action_resolved_from_portfolio_construction_reason_code",
            )
        if "buy_quality_rejected" in reason_codes:
            return _adaptive_quality_result(
                row,
                action="REJECT",
                status=status or "PASS",
                adjustment=0.0,
                reason="buy_quality_action_resolved_from_portfolio_construction_reason_code",
            )
        return _adaptive_quality_result(
            row,
            action="REVIEW_REQUIRED",
            status="REVIEW_REQUIRED",
            adjustment=0.0,
            reason="adaptive_buy_quality_decision_missing",
        )
    if action == "FULL_ALLOCATION_ELIGIBLE":
        adjustment = 1.0
        reason = ""
    elif action == "REDUCED_ALLOCATION_ONLY":
        adjustment = adjustment_raw if adjustment_raw is not None else (min(max(score or 0.0, 0.25), 0.85) if score is not None else 0.0)
        reason = ""
    elif action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE"}:
        adjustment = 0.0
        reason = "adaptive_buy_quality_buy_wait"
        action = "BUY_WAIT"
        status = status or "PASS"
    elif action in {"REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED"}:
        adjustment = 0.0
        reason = "adaptive_buy_quality_review_required"
    elif action in {"REJECT", "BUY_REJECTED"}:
        adjustment = 0.0
        reason = "adaptive_buy_quality_rejected"
    else:
        adjustment = 0.0
        reason = "adaptive_buy_quality_action_invalid"
        action = "REVIEW_REQUIRED"
        status = "REVIEW_REQUIRED"
    return _adaptive_quality_result(
        row,
        action="REJECT" if action == "BUY_REJECTED" else "REVIEW_REQUIRED" if action == "BUY_REVIEW_REQUIRED" else action,
        status=status,
        adjustment=adjustment,
        reason=reason,
    )


def _adaptive_quality_result(row: Mapping[str, Any], *, action: str, status: str, adjustment: float, reason: str) -> dict[str, Any]:
    reasons = list(row.get("quality_reason_codes") or [])
    if reason:
        reasons.append(reason)
    return {
        "quality_decision_id": str(row.get("quality_decision_id") or ""),
        "quality_score": _optional_quality_score(row.get("quality_score")),
        "quality_band": str(row.get("quality_band") or ""),
        "quality_action": action,
        "quality_status": status,
        "quality_reason_codes": sorted(set(reasons)),
        "quality_policy_version": str(row.get("quality_policy_version") or ""),
        "quality_allocation_adjustment": round(max(0.0, min(1.0, float(adjustment))), 6),
        "component_scores": dict(row.get("component_scores") or {}),
        "component_statuses": dict(row.get("component_statuses") or {}),
        "buy_quality_authority": dict(row.get("buy_quality_authority") or {}),
        "review_reason": reason,
    }


def _optional_quality_score(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    return max(0.0, min(1.0, float(value)))


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


def _lot_quantity(notional: float, *, price: float, trading_unit: float) -> int:
    if notional <= 0 or price <= 0 or trading_unit <= 0:
        return 0
    unit = int(trading_unit)
    if unit <= 0:
        return 0
    return max(int(notional // (price * unit)) * unit, 0)


def _resolve_one_lot_discrete_quantity_authority(
    row: Mapping[str, Any],
    *,
    target: float,
    strategy_cap: float,
    current_quantity: int,
    price: float,
    trading_unit: float,
) -> dict[str, Any]:
    lot_resolution = _lot_aware_strategy_cap_lot_resolution(row)
    semantic = str(row.get("semantic_buy_type") or lot_resolution.get("semantic_type") or "").upper()
    empty = {
        "authorized": False,
        "semantic_type": semantic,
        "discrete_authorized_quantity": 0,
        "discrete_authorized_notional": 0.0,
        "final_target_quantity": current_quantity,
        "authority_reason": "",
        "safety_hard_cap_validation": "NOT_APPLICABLE",
    }
    if semantic not in {"BUY_NEW", "REENTRY", "BUY_ADD"}:
        return empty
    strategy_overshoot_authorized = _lot_aware_strategy_cap_overshoot_authorized_row(row, target=target, strategy_cap=strategy_cap)
    minimum_one_lot_authorized = _minimum_executable_one_lot_authorized_row(
        row,
        target=target,
        strategy_cap=strategy_cap,
        current_quantity=current_quantity,
    )
    if not strategy_overshoot_authorized and not minimum_one_lot_authorized:
        return empty
    one_lot_quantity = _positive_int(lot_resolution.get("one_lot_quantity"), 0)
    if one_lot_quantity <= 0:
        return empty
    final_allocated_quantity = _positive_int(lot_resolution.get("final_allocated_quantity"), 0)
    executable_quantity_delta = _positive_int(lot_resolution.get("executable_quantity_delta"), 0)
    preflight_quantity_delta = _positive_int(lot_resolution.get("preflight_executable_quantity_delta"), 0)
    authorized_quantity = final_allocated_quantity or executable_quantity_delta or preflight_quantity_delta or one_lot_quantity
    unit = int(trading_unit) if trading_unit > 0 else 0
    if authorized_quantity <= 0 or authorized_quantity > one_lot_quantity:
        return empty
    if unit <= 0 or authorized_quantity % unit != 0 or one_lot_quantity % unit != 0:
        return empty
    if price <= 0:
        return empty
    expected_notional = round(price * authorized_quantity, 2)
    recorded_notional = _positive_float(lot_resolution.get("one_lot_notional"), 0.0)
    if recorded_notional > 0 and abs(recorded_notional - expected_notional) > max(1.0, expected_notional * 0.001):
        return empty
    safety_cap = _optional_ratio_value(lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")))
    post_trade_weight = _optional_ratio_value(lot_resolution.get("post_trade_weight", lot_resolution.get("final_target_weight")))
    if safety_cap is None:
        return empty
    if post_trade_weight is not None and post_trade_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if target > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return empty
    return {
        "authorized": True,
        "semantic_type": semantic,
        "discrete_authorized_quantity": int(authorized_quantity),
        "discrete_authorized_notional": expected_notional,
        "final_target_quantity": int(current_quantity + authorized_quantity),
        "authority_reason": str(
            lot_resolution.get("lot_overshoot_reason")
            or ("MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED" if minimum_one_lot_authorized else "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP")
        ),
        "safety_hard_cap_validation": "PASS",
    }


def _resolve_pc_discrete_executable_quantity_authority(
    row: Mapping[str, Any],
    *,
    target: float,
    strategy_cap: float,
    current_quantity: int,
    price: float,
    trading_unit: float,
) -> dict[str, Any]:
    lot_resolution = _lot_aware_strategy_cap_lot_resolution(row)
    semantic = str(row.get("semantic_buy_type") or lot_resolution.get("semantic_type") or "").upper()
    empty = {
        "authorized": False,
        "semantic_type": semantic,
        "discrete_authorized_quantity": 0,
        "discrete_authorized_notional": 0.0,
        "final_target_quantity": current_quantity,
        "authority_reason": "",
        "safety_hard_cap_validation": "NOT_APPLICABLE",
    }
    if semantic not in {"BUY_NEW", "REENTRY", "BUY_ADD"}:
        return empty
    authority = lot_resolution.get("pc_positive_executable_quantity_authority")
    nested = {}
    resolution = row.get("target_weight_resolution")
    if isinstance(resolution, Mapping):
        lot_aware = resolution.get("lot_aware_final_reallocation")
        if isinstance(lot_aware, Mapping):
            nested = lot_aware.get("pc_positive_executable_quantity_authority") if isinstance(lot_aware.get("pc_positive_executable_quantity_authority"), Mapping) else {}
    if not isinstance(authority, Mapping):
        authority = nested
    if not isinstance(authority, Mapping) or str(authority.get("status") or "") != "PASS":
        return empty
    authorized_quantity = _positive_int(authority.get("final_allocated_quantity"), 0)
    if authorized_quantity <= 0:
        return empty
    unit = int(trading_unit) if trading_unit > 0 else 0
    if unit <= 0 or authorized_quantity % unit != 0:
        return empty
    if price <= 0:
        return empty
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return empty
    safety_cap = _optional_ratio_value(lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")))
    post_trade_weight = _optional_ratio_value(lot_resolution.get("post_trade_weight", lot_resolution.get("final_target_weight")))
    if safety_cap is None:
        return empty
    if target > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if post_trade_weight is not None and post_trade_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return empty
    if target > strategy_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE and not _lot_aware_strategy_cap_overshoot_authorized_row(row, target=target, strategy_cap=strategy_cap):
        return empty
    if semantic == "BUY_ADD" and not _lot_aware_strategy_cap_add_economics_pass(row):
        return empty
    if semantic in {"BUY_NEW", "REENTRY"} and current_quantity != 0:
        return empty
    if semantic == "BUY_ADD" and current_quantity <= 0:
        return empty
    return {
        "authorized": True,
        "semantic_type": semantic,
        "discrete_authorized_quantity": int(authorized_quantity),
        "discrete_authorized_notional": round(price * authorized_quantity, 2),
        "final_target_quantity": int(current_quantity + authorized_quantity),
        "authority_reason": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
        "safety_hard_cap_validation": "PASS",
    }


def _resolve_passive_convergence_authority(summary: Mapping[str, Any]) -> dict[str, Any]:
    pc = summary if isinstance(summary, Mapping) else {}
    reconciliation = pc.get("incremental_budget_reconciliation")
    recon = reconciliation if isinstance(reconciliation, Mapping) else {}

    aggregate_exposure_state = str(recon.get("aggregate_exposure_state") or pc.get("aggregate_exposure_state") or "")
    transition_mode = str(recon.get("transition_mode") or pc.get("transition_mode") or "")
    positive_increment_allowed = recon.get("positive_increment_allowed")
    if positive_increment_allowed is None:
        positive_increment_allowed = pc.get("positive_increment_allowed")
    accepted_add_increment = _optional_ratio_value(
        recon.get("accepted_add_increment", recon.get("accepted_add_weight", pc.get("accepted_add_increment", pc.get("accepted_add_weight"))))
    )
    accepted_buy_new_weight = _optional_ratio_value(recon.get("accepted_buy_new_weight", pc.get("accepted_buy_new_weight")))
    target_gross_exposure = _optional_ratio_value(recon.get("target_gross_exposure", pc.get("target_gross_exposure")))
    baseline_existing_required_weight = _optional_ratio_value(
        recon.get("baseline_existing_required_weight", pc.get("baseline_existing_required_weight"))
    )
    final_target_weight_sum = _optional_ratio_value(recon.get("final_target_weight_sum", pc.get("total_target_weight")))

    missing = []
    for field, value in (
        ("aggregate_exposure_state", aggregate_exposure_state),
        ("transition_mode", transition_mode),
        ("positive_increment_allowed", positive_increment_allowed),
        ("accepted_add_increment", accepted_add_increment),
        ("accepted_buy_new_weight", accepted_buy_new_weight),
        ("target_gross_exposure", target_gross_exposure),
        ("baseline_existing_required_weight", baseline_existing_required_weight),
    ):
        if value in (None, ""):
            missing.append(field)

    conditions = {
        "aggregate_exposure_state": aggregate_exposure_state == "OVER_TARGET_EXISTING_BASELINE",
        "transition_mode": transition_mode == "PASSIVE_CONVERGENCE",
        "positive_increment_allowed": positive_increment_allowed is False,
        "accepted_add_increment_zero": accepted_add_increment is not None
        and accepted_add_increment <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE,
        "accepted_buy_new_weight_zero": accepted_buy_new_weight is not None
        and accepted_buy_new_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE,
    }
    authorized = not missing and all(conditions.values())
    return {
        "authority_type": "PORTFOLIO_CONSTRUCTION_PASSIVE_CONVERGENCE_AUTHORITY",
        "authority_status": "PASS" if authorized else "MISSING" if missing else "BLOCK",
        "authorized": authorized,
        "source": "portfolio_construction.incremental_budget_reconciliation",
        "aggregate_exposure_state": aggregate_exposure_state,
        "transition_mode": transition_mode,
        "positive_increment_allowed": positive_increment_allowed,
        "accepted_add_increment": accepted_add_increment,
        "accepted_buy_new_weight": accepted_buy_new_weight,
        "target_gross_exposure": target_gross_exposure,
        "baseline_existing_required_weight": baseline_existing_required_weight,
        "final_target_weight_sum": final_target_weight_sum,
        "missing_fields": missing,
        "conditions": conditions,
    }


def _passive_convergence_authority_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    authority = payload.get("passive_convergence_authority")
    if isinstance(authority, Mapping):
        return dict(authority)
    upstream = payload.get("upstream_artifacts")
    if isinstance(upstream, Mapping):
        portfolio_construction = upstream.get("portfolio_construction")
        if isinstance(portfolio_construction, Mapping):
            summary = portfolio_construction.get("summary")
            if isinstance(summary, Mapping):
                return _resolve_passive_convergence_authority(summary)
    return _resolve_passive_convergence_authority({})


def _passive_convergence_aggregate_over_target_authorized(
    authority: Mapping[str, Any],
    *,
    total_target_weight: float,
    target_exposure: float,
    aggregate_tolerance: float,
) -> bool:
    if authority.get("authorized") is not True:
        return False
    authority_target = _optional_ratio_value(authority.get("target_gross_exposure"))
    if authority_target is None or abs(authority_target - target_exposure) > aggregate_tolerance:
        return False
    baseline = _optional_ratio_value(authority.get("baseline_existing_required_weight"))
    final_sum = _optional_ratio_value(authority.get("final_target_weight_sum"))
    allowed_total = max(value for value in (baseline, final_sum) if value is not None) if any(
        value is not None for value in (baseline, final_sum)
    ) else None
    if allowed_total is None:
        return False
    if allowed_total <= target_exposure + aggregate_tolerance:
        return False
    return total_target_weight <= allowed_total + aggregate_tolerance


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
    if (
        target is not None
        and maximum is not None
        and target > maximum + 0.000001
        and not _position_cap_exception_is_directionally_allowed(position, target=target)
        and not _lot_aware_strategy_cap_overshoot_authorized_position(position, target=target, strategy_cap=maximum)
    ):
        errors.append(f"target_weight_above_position_cap:{index}")
    if (
        target is not None
        and safety_cap is not None
        and target > safety_cap + 0.000001
        and not _position_cap_exception_is_directionally_allowed(position, target=target)
    ):
        errors.append(f"target_weight_above_safety_cap:{index}")
    for field in ("target_notional", "current_notional", "incremental_buy_notional"):
        if isinstance(position.get(field), bool) or not isinstance(position.get(field), (int, float)) or float(position.get(field)) < 0:
            errors.append(f"invalid_notional:{index}:{field}")
    if isinstance(position.get("incremental_target_notional"), bool) or not isinstance(position.get("incremental_target_notional"), (int, float)):
        errors.append(f"invalid_notional:{index}:incremental_target_notional")
    for field in sorted(FORBIDDEN_FIELDS & set(position)):
        errors.append(f"quantity_or_runtime_field_forbidden:{index}:{field}")
    canonical = position.get("canonical_sizing_evidence")
    if not isinstance(canonical, dict):
        errors.append(f"canonical_sizing_evidence_missing:{index}")
    else:
        if canonical.get("schema_version") != CANONICAL_SIZING_EVIDENCE_SCHEMA_VERSION:
            errors.append(f"invalid_canonical_sizing_evidence_schema:{index}")
        if canonical.get("evidence_class") not in CANONICAL_SIZING_EVIDENCE_CLASSES:
            errors.append(f"invalid_canonical_sizing_evidence_class:{index}")
        if canonical.get("terminality") not in {"EXECUTABLE", "RECONSIDERABLE", "TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY"}:
            errors.append(f"invalid_sizing_outcome_terminality:{index}")
        if canonical.get("quantity_authority_owner") != "POSITION_SIZING":
            errors.append(f"invalid_quantity_authority_owner:{index}")
        if canonical.get("pc_reconsideration_owner") != "PORTFOLIO_CONSTRUCTION":
            errors.append(f"invalid_pc_reconsideration_owner:{index}")
        if canonical.get("raw_zero_quantity_reinterpreted") is not False:
            errors.append(f"raw_zero_quantity_reinterpretation_forbidden:{index}")
        quantity_delta = position.get("quantity_delta_candidate", position.get("final_quantity_delta", canonical.get("quantity_delta")))
        if quantity_delta == 0 and canonical.get("evidence_class") == "EXECUTABLE":
            errors.append(f"zero_quantity_requires_canonical_reason:{index}")
        if quantity_delta == 0 and not canonical.get("constraint_reason_codes"):
            errors.append(f"zero_quantity_constraint_reason_required:{index}")
    if not isinstance(position.get("reason_codes"), list):
        errors.append(f"reason_codes_not_list:{index}")
    return errors


def _position_cap_exception_is_directionally_allowed(position: Mapping[str, Any], *, target: float) -> bool:
    current_quantity = _positive_float(position.get("current_quantity"), 0.0)
    if current_quantity <= 0:
        return False
    current_weight = _ratio(position.get("current_weight"), 0.0)
    baseline_weight = _ratio(position.get("baseline_existing_weight"), current_weight)
    accepted_increment = _ratio(position.get("accepted_incremental_weight"), 0.0)
    quantity_delta = _int_or_none(position.get("quantity_delta_candidate"))
    pm_action = str(position.get("pm_action") or "").upper()
    membership = str(position.get("membership_intent") or "").upper()
    if (
        pm_action in {"HOLD", "ADD"}
        and membership == "RETAIN"
        and accepted_increment <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        and quantity_delta == 0
        and (
            abs(target - current_weight) <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
            or abs(target - baseline_weight) <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        )
    ):
        return True
    if pm_action == "REDUCE" and quantity_delta is not None and quantity_delta <= 0 and target <= current_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return True
    return False


def _lot_aware_strategy_cap_overshoot_authorized_row(row: Mapping[str, Any], *, target: float, strategy_cap: float) -> bool:
    projected = {
        "current_quantity": row.get("current_quantity"),
        "pm_action": row.get("pm_action"),
        "membership_intent": row.get("membership_intent"),
        "semantic_buy_type": row.get("semantic_buy_type"),
        "add_allocation_eligibility_status": row.get("add_allocation_eligibility_status"),
        "incremental_investment_value_state": row.get("incremental_investment_value_state"),
        "opportunity_cost_status": row.get("opportunity_cost_status"),
        "lot_aware_accepted_incremental_weight": row.get("lot_aware_accepted_incremental_weight"),
        "lot_aware_accepted_buy_new_weight": row.get("lot_aware_accepted_buy_new_weight"),
        "target_weight_resolution": row.get("target_weight_resolution"),
        "phase29_l19_lot_resolution": row.get("phase29_l19_lot_resolution"),
    }
    return _lot_aware_strategy_cap_overshoot_authorized_position(projected, target=target, strategy_cap=strategy_cap)


def _minimum_executable_one_lot_authorized_row(
    row: Mapping[str, Any],
    *,
    target: float,
    strategy_cap: float,
    current_quantity: int,
) -> bool:
    lot_resolution = _lot_aware_strategy_cap_lot_resolution(row)
    authority = lot_resolution.get("minimum_executable_one_lot_authority")
    if not isinstance(authority, Mapping):
        authority = row.get("minimum_executable_one_lot_authority")
    if not isinstance(authority, Mapping):
        return False
    semantic = str(row.get("semantic_buy_type") or lot_resolution.get("semantic_type") or authority.get("intent") or "").upper()
    if semantic not in {"BUY_NEW", "REENTRY"}:
        return False
    if current_quantity != 0 or _positive_float(row.get("current_quantity"), 0.0) > 0:
        return False
    if str(row.get("membership_intent") or "").upper() != "ADD_CANDIDATE":
        return False
    if str(authority.get("decision") or "") != "ADMIT":
        return False
    if str(authority.get("reason") or authority.get("admission_reason") or "") != "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED":
        return False
    if str(lot_resolution.get("minimum_executable_one_lot_reason") or "") != "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED":
        return False
    if lot_resolution.get("minimum_executable_one_lot_admitted") is not True:
        return False
    if target > strategy_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    if str(lot_resolution.get("one_lot_feasibility_status") or "") != "PASS":
        return False
    if lot_resolution.get("one_lot_fallback_applied") is not True:
        return False
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return False
    one_lot_quantity = _positive_int(lot_resolution.get("one_lot_quantity"), 0)
    final_quantity = _positive_int(lot_resolution.get("final_allocated_quantity"), 0)
    if one_lot_quantity <= 0 or final_quantity <= 0 or final_quantity > one_lot_quantity:
        return False
    safety_cap = _optional_ratio_value(lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")))
    post_trade_weight = _optional_ratio_value(lot_resolution.get("post_trade_weight", lot_resolution.get("final_target_weight")))
    if safety_cap is None or target > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    if post_trade_weight is not None and post_trade_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    accepted = _ratio(row.get("lot_aware_accepted_buy_new_weight"), 0.0)
    if accepted <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    one_lot_weight = _optional_ratio_value(lot_resolution.get("one_lot_weight"))
    if one_lot_weight is not None and accepted > one_lot_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    return True


def _lot_aware_strategy_cap_overshoot_authorized_position(position: Mapping[str, Any], *, target: float, strategy_cap: float) -> bool:
    if target <= strategy_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    lot_resolution = _lot_aware_strategy_cap_lot_resolution(position)
    semantic = str(position.get("semantic_buy_type") or lot_resolution.get("semantic_type") or "").upper()
    membership = str(position.get("membership_intent") or "").upper()
    pm_action = str(position.get("pm_action") or "").upper()
    current_quantity = _positive_float(position.get("current_quantity"), 0.0)
    is_buy_add = current_quantity > 0 and pm_action == "ADD" and membership == "RETAIN" and semantic == "BUY_ADD"
    is_new_exposure = current_quantity <= 0 and membership == "ADD_CANDIDATE" and semantic in {"BUY_NEW", "REENTRY"}
    if not (is_buy_add or is_new_exposure):
        return False
    if str(lot_resolution.get("boundary_classification") or "") != "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX":
        return False
    if lot_resolution.get("strategy_cap_overshoot_applied") is not True:
        return False
    if lot_resolution.get("one_lot_fallback_applied") is not True:
        return False
    if str(lot_resolution.get("one_lot_feasibility_status") or "") != "PASS":
        return False
    if _positive_int(lot_resolution.get("one_lot_quantity"), 0) <= 0:
        return False
    final_quantity = _positive_int(lot_resolution.get("final_allocated_quantity"), 0)
    if final_quantity > 0 and final_quantity > _positive_int(lot_resolution.get("one_lot_quantity"), 0):
        return False
    raw_margin = lot_resolution.get("safety_margin_after_trade")
    if raw_margin is not None:
        try:
            if float(raw_margin) < -TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
                return False
        except (TypeError, ValueError):
            return False
    lot_overshoot_reason = str(lot_resolution.get("lot_overshoot_reason") or "")
    if lot_overshoot_reason not in {
        "LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
        "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP",
        "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION",
    }:
        return False
    if lot_overshoot_reason == "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION":
        pc_quantity_authority = lot_resolution.get("pc_positive_executable_quantity_authority")
        if not isinstance(pc_quantity_authority, Mapping):
            return False
        if str(pc_quantity_authority.get("status") or "") != "PASS":
            return False
        if pc_quantity_authority.get("ps_must_consume_canonical_quantity") is not True:
            return False
        pc_authorized_quantity = _positive_int(pc_quantity_authority.get("final_allocated_quantity"), 0)
        lot_authorized_quantity = (
            _positive_int(lot_resolution.get("final_allocated_quantity"), 0)
            or _positive_int(lot_resolution.get("executable_quantity_delta"), 0)
            or _positive_int(lot_resolution.get("preflight_executable_quantity_delta"), 0)
        )
        if pc_authorized_quantity <= 0 or lot_authorized_quantity <= 0 or pc_authorized_quantity != lot_authorized_quantity:
            return False
    safety_cap = _optional_ratio_value(lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")))
    if safety_cap is None or target > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return False
    if is_buy_add and not _lot_aware_strategy_cap_add_economics_pass(position):
        return False
    accepted = _ratio(position.get("lot_aware_accepted_incremental_weight" if is_buy_add else "lot_aware_accepted_buy_new_weight"), 0.0)
    if accepted <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    return True


def _lot_aware_strategy_cap_lot_resolution(position: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = position.get("phase29_l19_lot_resolution")
    if isinstance(direct, Mapping):
        return direct
    resolution = position.get("target_weight_resolution")
    lot_aware = resolution.get("lot_aware_final_reallocation") if isinstance(resolution, Mapping) else None
    if isinstance(lot_aware, Mapping):
        nested = lot_aware.get("phase29_l19_lot_resolution")
        if isinstance(nested, Mapping):
            return nested
    return {}


def _lot_aware_strategy_cap_add_economics_pass(position: Mapping[str, Any]) -> bool:
    if (
        str(position.get("add_allocation_eligibility_status") or "") == "PASS"
        and str(position.get("incremental_investment_value_state") or "") == "POSITIVE"
        and str(position.get("opportunity_cost_status") or "") == "PASS"
    ):
        return True
    resolution = position.get("target_weight_resolution")
    bridge = resolution.get("add_allocation_bridge") if isinstance(resolution, Mapping) else None
    if not isinstance(bridge, Mapping):
        return False
    checks = bridge.get("eligibility_checks")
    if not isinstance(checks, Mapping):
        return False
    return (
        str(bridge.get("status") or "") == "PASS"
        and str(checks.get("incremental_investment_value") or checks.get("incremental_value") or "") == "PASS"
        and str(checks.get("opportunity_cost") or "") == "PASS"
        and str(checks.get("pm_add") or "") == "PASS"
    )


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


def _optional_ratio_value(value: Any) -> float | None:
    try:
        return _ratio(value, None)
    except Exception:
        return None


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
