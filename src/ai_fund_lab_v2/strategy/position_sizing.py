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
    TARGET_WEIGHT_ABSOLUTE_TOLERANCE,
    TARGET_WEIGHT_DECIMALS,
    target_weight_sum_tolerance,
)


SCHEMA_VERSION = "position_sizing.v1"
CONFIG_SCHEMA_VERSION = "position_sizing_config.v1"
PRODUCER_VERSION = "phase22_j_position_sizing_producer.v1"
LOT_FEASIBILITY_SCHEMA_VERSION = "ps_lot_feasibility_preflight.v1"
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

    sizing_rows = _rows_with_price_volatility(portfolio_construction_summary.rows, price_volatility_summary)
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
    required = {"schema_version","business_date","as_of","feature_date","artifact_lifecycle_status","source_authority_status","producer_result_status","runtime_consumer_eligibility","target_gross_exposure_ratio","positions","total_target_weight","residual_cash_ratio","concrete_target_weight_decided","target_notional_decided","share_quantity_decided","lot_rounding_decided","source_artifacts","source_hashes","temporal_safety","strategy_maximum_position_weight","strategy_maximum_position_weight_source","safety_maximum_position_weight","safety_maximum_position_weight_source","safety_authority_status","effective_maximum_position_weight","effective_maximum_position_weight_derivation","explicit_zero_cap","emergency_brake_active","market_context_risk_state","dynamic_cash_exposure","aggregate_exposure_cap"}
    errors = [f"required_field_missing:{f}" for f in sorted(required - set(payload))]
    if payload.get("schema_version") != SCHEMA_VERSION: errors.append("unsupported_schema_version")
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS: errors.append("artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY: errors.append("runtime_consumer_eligibility_must_be_not_eligible")
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
    quality_adjustment_scope = "BUY_NEW_TOTAL_TARGET"
    minimum_meaningful_notional_applied_to = "TOTAL_TARGET_NOTIONAL"
    position_type = "EXISTING_POSITION" if existing_position else "NEW_POSITION"
    baseline_quantity_preserved = False
    transaction_delta_weight = round(max(target - current_weight, 0.0), 6)
    transaction_target_notional = round(max((target - current_weight) * portfolio_value, 0.0), 2)
    transaction_quantity_candidate = 0
    reduce_fraction_candidate = _ratio(row.get("reduce_fraction"), 0.0) if pm_action == "REDUCE" else 0.0

    if existing_position and pm_action in {"HOLD", "ADD", "REDUCE", "EXIT", "UNRESOLVED"}:
        adjusted = target
        quality_adjustment_scope = "INCREMENTAL_TRANSACTION_ONLY" if pm_action == "ADD" else "NOT_APPLIED_TO_EXISTING_BASELINE"
        minimum_meaningful_notional_applied_to = "TRANSACTION_DELTA_NOTIONAL"
        reasons.append("existing_position_baseline_quantity_authoritative")
        if pm_action in {"HOLD", "ADD", "UNRESOLVED"}:
            baseline_quantity_preserved = True
    else:
        adjusted = target * quality
    if pm_action == "EXIT" or membership in {"REMOVE_CANDIDATE", "EXCLUDE"}:
        adjusted = 0.0
    elif pm_action == "REDUCE":
        adjusted = min(adjusted, current_weight * 0.5) if not existing_position else min(target, current_weight)
    elif membership == "ADD_CANDIDATE" and adaptive_quality["quality_action"] in {"REVIEW_REQUIRED", "REJECT"}:
        adjusted = 0.0
        status = "QUALITY_UNAVAILABLE" if adaptive_quality["quality_action"] == "REVIEW_REQUIRED" else "WITHHELD"
        uncertainty = "BUY_QUALITY_REVIEW_REQUIRED" if adaptive_quality["quality_action"] == "REVIEW_REQUIRED" else "BUY_QUALITY_REJECTED"
        reasons.append("buy_quality_not_auto_submittable")
        reasons.append(str(adaptive_quality["review_reason"] or adaptive_quality["quality_action"]))
    capped = max(adjusted, 0.0) if existing_position else min(max(adjusted, 0.0), max_weight)
    if capped < adjusted:
        status = "CAPPED"
        reasons.append("position_concentration_cap_applied")
    target = round(capped, 6) if status in {"SIZED", "CAPPED"} else 0.0
    target_notional = round(target * portfolio_value, 2)
    target_quantity_candidate = 0
    price_required = target_notional > 0
    quantity_status = "RESOLVED_ZERO_DELTA" if current_quantity == 0 else "RESOLVED_CANDIDATE"
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
            if transaction_target_notional < min_notional or transaction_quantity_candidate <= 0:
                quantity_status = "RESOLVED_ZERO_DELTA"
                transaction_quantity_candidate = 0
                reasons.append("ADD_INCREMENT_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT")
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
            transaction_quantity_candidate = math.floor(raw_reduce_quantity / trading_unit) * trading_unit if trading_unit > 0 else 0
            if transaction_quantity_candidate <= 0 or transaction_quantity_candidate * price < min_notional:
                transaction_quantity_candidate = 0
                transaction_target_notional = 0.0
                quantity_status = "RESOLVED_ZERO_DELTA"
                reasons.append("REDUCE_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT")
            else:
                target_quantity_candidate = int(max(current_quantity - transaction_quantity_candidate, 0))
                quantity_status = "RESOLVED_CANDIDATE"
                reasons.append("REDUCE_PARTIAL_QUANTITY_DELTA")
    elif price_required and reference_price_resolution["status"] != "PASS":
        quantity_status = "PRICE_UNAVAILABLE"
        reasons.append(str(reference_price_resolution["review_reason"] or "reference_price_unavailable"))
    elif price_required and price > 0 and trading_unit > 0:
        target_quantity_candidate = _lot_quantity(target_notional, price=price, trading_unit=trading_unit)
        quantity_status = "RESOLVED_ZERO_DELTA" if target_quantity_candidate == current_quantity else "RESOLVED_CANDIDATE"
    if status in {"SIZED", "CAPPED"} and not existing_position and 0 < target_notional < min_notional:
        status = "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
        uncertainty = "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY"
        reasons.append("minimum_meaningful_notional_unmet")
        target_quantity_candidate = 0
        quantity_status = "NO_ORDER_MINIMUM_NOTIONAL_UNMET"
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
    if safety_cap is not None and target > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        if retained_baseline:
            reasons.append("PASSIVE_CONCENTRATION_DRIFT_RETAINED")
            reasons.append("SAFETY_CAP_DRIFT_NO_RISK_INCREASE")
        elif risk_reducing:
            reasons.append("SAFETY_CAP_DRIFT_RISK_REDUCING_TRANSACTION_ALLOWED")
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
        "reduce_fraction": round(reduce_fraction_candidate, 6),
        "transaction_delta_weight": transaction_delta_weight,
        "transaction_target_notional": transaction_target_notional,
        "transaction_quantity_candidate": int(transaction_quantity_candidate),
        "target_weight_authority": dict(row.get("target_weight_authority") or {}),
        "target_weight_resolution": dict(target_weight_resolution),
        **_phase29_l16_strategy_evidence(row),
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
        "capacity_ratio",
        "liquidity_capacity_status",
        "normal_target_weight",
        "price_tick_cap_weight",
        "liquidity_capacity_cap_weight",
        "final_risk_adjusted_target_weight",
        "allocation_cap_reason",
    )
    return {field: row.get(field) for field in fields if field in row}


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
    minimum_executable_weight = round(min_notional / portfolio_value, TARGET_WEIGHT_DECIMALS) if portfolio_value > 0 else None
    one_lot_post_trade_weight = None if minimum_executable_weight is None else round(current_weight + minimum_executable_weight, TARGET_WEIGHT_DECIMALS)
    concentration_feasible = minimum_executable_weight is not None and minimum_executable_weight <= concentration_headroom + TARGET_WEIGHT_ABSOLUTE_TOLERANCE
    one_lot_notional = price * trading_unit if price > 0 and trading_unit > 0 else 0.0
    one_lot_weight = one_lot_notional / portfolio_value if portfolio_value > 0 and one_lot_notional > 0 else 0.0
    requested_lots = int(target_basis_notional // one_lot_notional) if one_lot_notional > 0 else 0
    minimum_policy_lots = int(math.ceil(min_notional / one_lot_notional)) if one_lot_notional > 0 and min_notional > 0 else 0
    maximum_strategy_feasible_lots = int(max(math.floor((concentration_headroom * portfolio_value) / one_lot_notional), 0)) if one_lot_notional > 0 and portfolio_value > 0 else 0
    maximum_safety_feasible_lots = int(max(math.floor((safety_headroom * portfolio_value) / one_lot_notional), 0)) if one_lot_notional > 0 and portfolio_value > 0 else 0
    executable_lots = 0
    if requested_lots >= minimum_policy_lots and minimum_policy_lots > 0:
        executable_lots = min(requested_lots, maximum_strategy_feasible_lots)
    executable_quantity_delta = int(executable_lots * trading_unit)
    one_minimum_policy_lot_post_trade_weight = round(current_weight + max(minimum_policy_lots, 1) * one_lot_weight, TARGET_WEIGHT_DECIMALS) if one_lot_weight > 0 else None
    if minimum_policy_lots > maximum_safety_feasible_lots:
        boundary_classification = "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX"
    elif minimum_policy_lots > maximum_strategy_feasible_lots:
        boundary_classification = "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX"
    elif executable_lots > 0:
        boundary_classification = "CAP_CONSTRAINED_LOT_EXECUTABLE"
    elif target_basis_notional < min_notional:
        boundary_classification = "REQUEST_BELOW_MINIMUM_EXECUTABLE_NOTIONAL"
    else:
        boundary_classification = "NO_EXECUTABLE_LOT"
    lot_feasible = (
        reference_price_resolution["status"] == "PASS"
        and broker_eligible
        and target_basis_notional >= min_notional
        and draft_quantity_delta > 0
    )
    reason_codes: list[str] = []
    if reference_price_resolution["status"] != "PASS":
        reason_codes.append("reference_price_unavailable")
    if not broker_eligible:
        reason_codes.append("broker_eligibility_fail_closed")
    if target_basis_notional < min_notional:
        reason_codes.append("below_minimum_executable_notional")
    if draft_quantity_delta <= 0:
        reason_codes.append("below_minimum_tradable_quantity")
    if not concentration_feasible:
        reason_codes.append("minimum_lot_exceeds_concentration_headroom")
    if reference_price_resolution["status"] != "PASS":
        feasibility_classification = "UNKNOWN_FAIL_CLOSED"
    elif not broker_eligible:
        feasibility_classification = "BROKER_OR_SAFETY_BLOCKED"
    elif not concentration_feasible:
        feasibility_classification = "CONCENTRATION_BLOCKED"
    elif lot_feasible:
        feasibility_classification = "EXECUTABLE_NOW"
    elif capital_feasible and minimum_executable_weight is not None:
        feasibility_classification = "EXECUTABLE_IF_RECYCLED"
    else:
        feasibility_classification = "CAPITAL_BLOCKED"
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
        "minimum_executable_notional": round(min_notional, 2),
        "minimum_executable_weight": minimum_executable_weight,
        "phase29_l19_lot_resolution": {
            "authority_type": "PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION",
            "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
            "requested_target_weight": round(target_weight, TARGET_WEIGHT_DECIMALS),
            "requested_incremental_weight": round(max(target_weight - current_weight, requested_add if intent_type == "BUY_ADD" else requested_buy_new, 0.0), TARGET_WEIGHT_DECIMALS),
            "strategy_cap_weight": round(concentration_cap, TARGET_WEIGHT_DECIMALS),
            "safety_hard_cap_weight": round(float(safety_hard_cap), TARGET_WEIGHT_DECIMALS),
            "remaining_strategy_headroom": round(concentration_headroom, TARGET_WEIGHT_DECIMALS),
            "remaining_safety_headroom": round(safety_headroom, TARGET_WEIGHT_DECIMALS),
            "one_lot_notional": round(one_lot_notional, 2),
            "one_lot_weight": round(one_lot_weight, TARGET_WEIGHT_DECIMALS),
            "minimum_policy_lots": minimum_policy_lots,
            "minimum_policy_lot_weight": round(max(minimum_policy_lots, 1) * one_lot_weight, TARGET_WEIGHT_DECIMALS) if one_lot_weight > 0 else 0.0,
            "post_trade_weight": one_minimum_policy_lot_post_trade_weight,
            "maximum_strategy_feasible_lots": maximum_strategy_feasible_lots,
            "maximum_safety_feasible_lots": maximum_safety_feasible_lots,
            "requested_lots": requested_lots,
            "executable_lots": executable_lots,
            "executable_quantity_delta": executable_quantity_delta,
            "boundary_classification": boundary_classification,
            "strategy_cap_preserved": True,
            "safety_hard_cap_preserved": minimum_policy_lots <= maximum_safety_feasible_lots if minimum_policy_lots > 0 else True,
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
        "broker_eligible": broker_eligible,
        "producer_result_status": "PASS" if lot_feasible else "REVIEW_REQUIRED",
        "reason_codes": sorted(set(reason_codes)),
        "source_lineage": {
            "position_reference": str(row.get("position_reference") or row.get("member_id") or ""),
            "target_weight_authority": dict(row.get("target_weight_authority") or {}),
            "reference_price_authority": dict(row.get("reference_price_authority") or {}),
        },
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
    if not decision_id or not action:
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
