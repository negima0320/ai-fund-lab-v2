from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.status_contract import numeric_resolution, status_contract_fields


SCHEMA_VERSION = "dynamic_position_count.v1"
PRODUCER_VERSION = "phase22_h_dynamic_position_count_producer.v1"
CONFIG_SCHEMA_VERSION = "dynamic_position_count_config.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"
DEPRECATED_FIXED_MAXIMUM_FIELDS = (
    "maximum_position_count",
    "strategy_maximum_position_count",
    "safety_hard_maximum",
)

SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
POSITION_COUNT_POSTURES = {"INCREASE", "MAINTAIN", "DECREASE", "PAUSE_NEW_ENTRY", "UNRESOLVED"}
CAPACITY_CONSTRAINT_STATUSES = {
    "SUFFICIENT",
    "CANDIDATE_CONSTRAINED",
    "OPPORTUNITY_CONSTRAINED",
    "MARKET_RISK_CONSTRAINED",
    "UNCERTAINTY_CONSTRAINED",
    "SAFETY_CAP_CONSTRAINED",
    "SOURCE_UNAVAILABLE",
}
TREND_REGIMES = {"BULL", "BEAR", "RANGE", "RECOVERY", "CORRECTION"}
BREADTH_REGIMES = {"STRONG", "NEUTRAL", "WEAK"}
VOLATILITY_REGIMES = {"HIGH", "NORMAL", "LOW"}
RISK_POSTURES = {"RISK_ON", "BALANCED", "DEFENSIVE", "RISK_OFF", "UNRESOLVED"}
ENTRY_POSTURES = {"EXPAND", "MAINTAIN", "RESTRICT", "PAUSE", "UNRESOLVED"}
BLOCKING_SOURCE_STATUSES = {"BLOCK", "MISSING", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
REVIEW_SOURCE_STATUSES = {"REVIEW_REQUIRED", "NOT_ELIGIBLE", "STALE"}


class DynamicPositionCountError(RuntimeError):
    pass


class DynamicPositionCountConfigError(DynamicPositionCountError):
    pass


class DynamicPositionCountSchemaError(DynamicPositionCountError):
    pass


class DynamicPositionCountConsumerError(DynamicPositionCountError):
    pass


@dataclass(frozen=True)
class DynamicPositionCountSourceSummary:
    status: str
    business_date: str
    feature_date: str
    source_ref: str
    source_hash: str
    summary: Mapping[str, Any]

    def to_dict(self, *, requested_business_date: str) -> dict[str, Any]:
        return {
            "status": self.status,
            "business_date": self.business_date,
            "feature_date": self.feature_date,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "summary": dict(self.summary),
            "business_date_aligned": self.business_date == requested_business_date,
            "feature_date_lte_business_date": bool(self.feature_date and self.feature_date <= requested_business_date),
        }


@dataclass(frozen=True)
class DynamicPositionCountConfig:
    config_version: str
    config_source: str
    legacy_active_max_positions_reference: str
    strategy_minimum_position_count: int
    strategy_maximum_position_count: int | None
    safety_hard_maximum_reference: str
    safety_hard_maximum_status: str
    regime_rules: Mapping[str, int]
    breadth_rules: Mapping[str, Mapping[str, int]]
    volatility_rules: Mapping[str, Mapping[str, int]]
    portfolio_policy_rules: Mapping[str, Mapping[str, int]]
    opportunity_capacity_rules: Mapping[str, Any]
    uncertainty_rules: Mapping[str, Mapping[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "config_version": self.config_version,
            "config_source": self.config_source,
            "legacy_active_max_positions_reference": self.legacy_active_max_positions_reference,
            "strategy_minimum_position_count": self.strategy_minimum_position_count,
            "strategy_maximum_position_count": self.strategy_maximum_position_count,
            "deprecated_fields": {
                "strategy_maximum_position_count": "deprecated_not_authoritative_not_used_for_target_calculation",
                "maximum_position_count": "deprecated_schema_compatibility_only",
                "safety_hard_maximum": "safety_observability_only_not_strategy_capacity_cap",
            },
            "safety_hard_maximum_reference": self.safety_hard_maximum_reference,
            "safety_hard_maximum_status": self.safety_hard_maximum_status,
            "regime_rules": dict(self.regime_rules),
            "breadth_rules": _deep_dict(self.breadth_rules),
            "volatility_rules": _deep_dict(self.volatility_rules),
            "portfolio_policy_rules": _deep_dict(self.portfolio_policy_rules),
            "opportunity_capacity_rules": dict(self.opportunity_capacity_rules),
            "uncertainty_rules": _deep_dict(self.uncertainty_rules),
        }


@dataclass(frozen=True)
class DynamicPositionCountProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


@dataclass(frozen=True)
class CapacityResolution:
    artifact_class: str
    resolved_count: int
    canonical_field: str
    source_field: str
    resolution_status: str
    resolution_reason: str
    legacy_alias_used: bool
    conflict_detected: bool
    source_schema_version: str
    source_path: str
    source_hash: str
    fields_observed: Mapping[str, int]
    conflicts: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_class": self.artifact_class,
            "resolved_count": self.resolved_count,
            "canonical_field": self.canonical_field,
            "source_field": self.source_field,
            "resolution_status": self.resolution_status,
            "resolution_reason": self.resolution_reason,
            "legacy_alias_used": self.legacy_alias_used,
            "conflict_detected": self.conflict_detected,
            "source_schema_version": self.source_schema_version,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "fields_observed": dict(self.fields_observed),
            "conflicts": [dict(item) for item in self.conflicts],
        }


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "dynamic_position_count" / business_date / "dynamic_position_count.json"


def load_dynamic_position_count_config(path: Path | str) -> DynamicPositionCountConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise DynamicPositionCountConfigError(f"dynamic position count config missing: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DynamicPositionCountConfigError(f"dynamic position count config invalid json: {exc}") from exc
    if not isinstance(payload, dict):
        raise DynamicPositionCountConfigError("dynamic position count config must be a JSON object")
    if payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise DynamicPositionCountConfigError("unsupported dynamic position count config schema_version")
    minimum = _required_int(payload, "strategy_minimum_position_count", minimum=0)
    maximum_value = payload.get("strategy_maximum_position_count")
    maximum = _optional_int(maximum_value, "strategy_maximum_position_count", minimum=0)
    safety_status = _required_text(payload, "safety_hard_maximum_status")
    if safety_status not in {"PASS", "RESOLVED", "REVIEW_REQUIRED", "BLOCK", "NOT_APPLICABLE", "REMOVED"}:
        raise DynamicPositionCountConfigError("safety_hard_maximum_status unsupported")
    config = DynamicPositionCountConfig(
        config_version=_required_text(payload, "config_version"),
        config_source=str(config_path),
        legacy_active_max_positions_reference=_required_text(payload, "legacy_active_max_positions_reference"),
        strategy_minimum_position_count=minimum,
        strategy_maximum_position_count=maximum,
        safety_hard_maximum_reference=_required_text(payload, "safety_hard_maximum_reference"),
        safety_hard_maximum_status=safety_status,
        regime_rules=_required_int_mapping(payload, "regime_rules", keys=TREND_REGIMES),
        breadth_rules=_required_rule_mapping(payload, "breadth_rules", keys=BREADTH_REGIMES),
        volatility_rules=_required_rule_mapping(payload, "volatility_rules", keys=VOLATILITY_REGIMES),
        portfolio_policy_rules=_required_policy_rules(payload),
        opportunity_capacity_rules=_required_object(payload, "opportunity_capacity_rules"),
        uncertainty_rules=_required_rule_mapping(payload, "uncertainty_rules", keys={"HIGH", "MEDIUM", "LOW", "UPSTREAM_REVIEW_REQUIRED"}),
    )
    for value in config.regime_rules.values():
        if value < minimum:
            raise DynamicPositionCountConfigError("regime rule target must be >= configured strategy minimum")
    return config


def produce_dynamic_position_count_artifact(
    *,
    business_date: str,
    market_context_summary: DynamicPositionCountSourceSummary,
    portfolio_policy_summary: DynamicPositionCountSourceSummary,
    candidate_summary: DynamicPositionCountSourceSummary,
    opportunity_summary: DynamicPositionCountSourceSummary,
    current_portfolio_summary: DynamicPositionCountSourceSummary,
    safety_hard_maximum: int | None,
    existing_active_max_positions: int,
    config: DynamicPositionCountConfig | None,
    output_path: Path | str,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> DynamicPositionCountProducerResult:
    payload, evidence = build_dynamic_position_count_payload(
        business_date=business_date,
        market_context_summary=market_context_summary,
        portfolio_policy_summary=portfolio_policy_summary,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_portfolio_summary=current_portfolio_summary,
        safety_hard_maximum=safety_hard_maximum,
        existing_active_max_positions=existing_active_max_positions,
        config=config,
        as_of=as_of,
        expected_config_hash=expected_config_hash,
    )
    validate_dynamic_position_count_artifact(payload)
    artifact_hash = dynamic_position_count_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return DynamicPositionCountProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_dynamic_position_count_payload(
    *,
    business_date: str,
    market_context_summary: DynamicPositionCountSourceSummary,
    portfolio_policy_summary: DynamicPositionCountSourceSummary,
    candidate_summary: DynamicPositionCountSourceSummary,
    opportunity_summary: DynamicPositionCountSourceSummary,
    current_portfolio_summary: DynamicPositionCountSourceSummary,
    safety_hard_maximum: int | None,
    existing_active_max_positions: int,
    config: DynamicPositionCountConfig | None,
    as_of: str | None = None,
    expected_config_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    if safety_hard_maximum is None:
        resolved_safety_hard_maximum = None
    else:
        resolved_safety_hard_maximum = _coerce_count(safety_hard_maximum, "safety_hard_maximum")
    existing_active_max_positions = _coerce_count(existing_active_max_positions, "existing_active_max_positions")
    summaries = {
        "market_context": market_context_summary,
        "portfolio_policy": portfolio_policy_summary,
        "candidate": candidate_summary,
        "opportunity": opportunity_summary,
        "current_portfolio": current_portfolio_summary,
    }
    reason_codes: list[str] = []
    producer_status = "PASS"
    source_status = "VALID"

    for name, summary in summaries.items():
        if not _summary_aligned(summary, business_date=business_date):
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_date_mismatch")
        if summary.status in BLOCKING_SOURCE_STATUSES:
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_block:{summary.status}")
            source_status = "MISSING" if summary.status == "MISSING" else "AUTHORITY_CONFLICT"
        elif summary.status != "PASS":
            if producer_status != "BLOCK":
                producer_status = "REVIEW_REQUIRED"
            reason_codes.append(f"{name}_review_required:{summary.status}")

    config_hash = ""
    config_source_hash = ""
    config_payload: dict[str, Any] | None = None
    if config is None:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("dynamic_position_count_config_required")
    else:
        config_payload = config.to_dict()
        config_hash = stable_payload_hash(config_payload)
        config_path = Path(config.config_source)
        config_source_hash = sha256_file(config_path) if config_path.is_file() else config_hash
        if expected_config_hash and _strip_sha256(expected_config_hash) != config_hash:
            producer_status = "BLOCK"
            source_status = "HASH_MISMATCH"
            reason_codes.append("dynamic_position_count_config_hash_mismatch")
        if config.safety_hard_maximum_status in {"REVIEW_REQUIRED", "BLOCK"}:
            if producer_status != "BLOCK":
                producer_status = "REVIEW_REQUIRED"
            reason_codes.append("safety_hard_maximum_review_required")
        elif config.safety_hard_maximum_status in {"NOT_APPLICABLE", "REMOVED"}:
            reason_codes.append("fixed_position_count_safety_hard_maximum_removed")
        elif (
            config.safety_hard_maximum_reference == config.legacy_active_max_positions_reference
            and resolved_safety_hard_maximum == existing_active_max_positions
        ):
            producer_status = "BLOCK"
            reason_codes.append("legacy_max_positions_must_not_be_implicit_safety_hard_maximum")
        if config.safety_hard_maximum_status in {"NOT_APPLICABLE", "REMOVED"}:
            resolved_safety_hard_maximum = None

    feature_date = min([summary.feature_date for summary in summaries.values() if summary.feature_date] or [business_date])
    future_leakage_used = any(summary.feature_date and summary.feature_date > business_date for summary in summaries.values())
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_source_date_detected")

    candidate_capacity_resolution = resolve_capacity_count(candidate_summary, artifact_class="candidate")
    opportunity_capacity_resolution = resolve_capacity_count(opportunity_summary, artifact_class="opportunity")
    capacity_review_reasons: list[str] = []
    capacity_conflicts = [*candidate_capacity_resolution.conflicts, *opportunity_capacity_resolution.conflicts]
    for resolution in (candidate_capacity_resolution, opportunity_capacity_resolution):
        if resolution.resolution_status != "PASS":
            if producer_status != "BLOCK":
                producer_status = "REVIEW_REQUIRED"
            reason_codes.append(resolution.resolution_reason)
            capacity_review_reasons.append(resolution.resolution_reason)
    available_candidate_count = candidate_capacity_resolution.resolved_count
    available_opportunity_count = opportunity_capacity_resolution.resolved_count
    current_position_count = _summary_count(current_portfolio_summary, "current_position_count", fallback_field="position_count")
    eligible_opportunity_count = min(available_candidate_count, available_opportunity_count)
    capital_affordable_position_count = _summary_count_optional(current_portfolio_summary, "capital_affordable_position_count", eligible_opportunity_count)
    liquidity_feasible_position_count = min(
        eligible_opportunity_count,
        _summary_count_optional(opportunity_summary, "liquidity_feasible_position_count", eligible_opportunity_count),
    )
    meaningful_allocation_position_count = min(
        liquidity_feasible_position_count,
        _summary_count_optional(opportunity_summary, "meaningful_allocation_position_count", liquidity_feasible_position_count),
    )

    unresolved_target = config is None or producer_status != "PASS"
    if unresolved_target:
        minimum_position_count = 0 if config is None else config.strategy_minimum_position_count
        target_position_count = None
        maximum_position_count = None
        capacity_status = "SOURCE_UNAVAILABLE" if producer_status != "BLOCK" else "SOURCE_UNAVAILABLE"
        posture = "UNRESOLVED"
        confidence = 0.0
        uncertainty = "UPSTREAM_REVIEW_REQUIRED" if producer_status == "REVIEW_REQUIRED" else "BLOCKING_INPUT"
    else:
        decision = _decide_counts(
            config=config,
            market_context=market_context_summary.summary,
            portfolio_policy=portfolio_policy_summary.summary,
            available_candidate_count=available_candidate_count,
            available_opportunity_count=meaningful_allocation_position_count,
            current_position_count=current_position_count,
        )
        minimum_position_count = decision["minimum_position_count"]
        target_position_count = decision["target_position_count"]
        maximum_position_count = decision["maximum_position_count"]
        capacity_status = decision["capacity_constraint_status"]
        posture = decision["position_count_posture"]
        confidence = decision["confidence"]
        uncertainty = decision["uncertainty"]
        reason_codes.extend(decision["reason_codes"])

    source_artifacts = [
        {"role": name, "path": summary.source_ref, "required": True, "status": summary.status}
        for name, summary in summaries.items()
    ]
    source_artifacts.append({"role": "dynamic_position_count_config", "path": config.config_source if config else "", "required": True, "status": "PASS" if config else "REVIEW_REQUIRED"})
    source_hashes = [
        {"role": name, "path": summary.source_ref, "sha256": _strip_sha256(summary.source_hash)}
        for name, summary in summaries.items()
    ]
    if config:
        source_hashes.append({"role": "dynamic_position_count_config", "path": config.config_source, "sha256": config_source_hash})
    if not all(item["sha256"] for item in source_hashes):
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("source_lineage_hash_required")

    actual_target_position_count = target_position_count
    shadow_comparison = {
        "existing_active_max_positions": existing_active_max_positions,
        "dynamic_minimum": minimum_position_count,
        "dynamic_target": target_position_count,
        "dynamic_maximum": maximum_position_count,
        "difference_from_existing": None if target_position_count is None else target_position_count - existing_active_max_positions,
        "would_change_available_slots": None
        if target_position_count is None
        else max(target_position_count - current_position_count, 0) != max(existing_active_max_positions - current_position_count, 0),
        "runtime_behavior_changed": False,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "business_date": business_date,
        "as_of": as_of,
        "feature_date": feature_date,
        "artifact_lifecycle_status": ARTIFACT_LIFECYCLE_STATUS,
        "source_authority_status": source_status,
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": RUNTIME_CONSUMER_ELIGIBILITY,
        **status_contract_fields(
            producer_result_status=producer_status,
            artifact_lifecycle_status=ARTIFACT_LIFECYCLE_STATUS,
            runtime_consumer_eligibility=RUNTIME_CONSUMER_ELIGIBILITY,
            reason_codes=sorted(set(reason_codes)),
            decision_resolution=numeric_resolution(target_position_count, unresolved=target_position_count is None),
        ),
        "target_position_count_resolution": numeric_resolution(target_position_count, unresolved=target_position_count is None),
        "minimum_position_count": minimum_position_count,
        "target_position_count": target_position_count,
        "maximum_position_count": maximum_position_count,
        "safety_hard_maximum": resolved_safety_hard_maximum,
        "legacy_active_max_positions": existing_active_max_positions,
        "strategy_minimum_position_count": minimum_position_count,
        "strategy_target_position_count": target_position_count,
        "strategy_maximum_position_count": maximum_position_count,
        "fixed_maximum_fields_authority": {
            field: "deprecated_not_authoritative_not_used_for_target_calculation"
            for field in DEPRECATED_FIXED_MAXIMUM_FIELDS
        },
        "strategy_fixed_position_cap_used": False,
        "safety_hard_maximum_used_for_target_calculation": False,
        "eligible_opportunity_count": eligible_opportunity_count,
        "capital_affordable_position_count": capital_affordable_position_count,
        "liquidity_feasible_position_count": liquidity_feasible_position_count,
        "meaningful_allocation_position_count": meaningful_allocation_position_count,
        "actual_target_position_count": actual_target_position_count,
        "constraint_reasons": sorted(set(reason_codes)),
        "capacity_posture": posture,
        "safety_hard_maximum_status": config.safety_hard_maximum_status if config else "REVIEW_REQUIRED",
        "ceiling_authority_status": _ceiling_authority_status(producer_status, config),
        "difference_from_legacy_ceiling": None,
        "current_position_count": current_position_count,
        "available_candidate_count": available_candidate_count,
        "available_opportunity_count": available_opportunity_count,
        "candidate_capacity_resolution": candidate_capacity_resolution.to_dict(),
        "opportunity_capacity_resolution": opportunity_capacity_resolution.to_dict(),
        "resolved_candidate_capacity": available_candidate_count,
        "resolved_opportunity_capacity": available_opportunity_count,
        "capacity_resolution_status": "PASS" if not capacity_review_reasons else "REVIEW_REQUIRED",
        "capacity_constraint_reasons": sorted(set(decision["reason_codes"] if not unresolved_target else [])),
        "capacity_conflicts": capacity_conflicts,
        "capacity_review_reasons": sorted(set(capacity_review_reasons)),
        "source_paths": [item["path"] for item in source_artifacts],
        "source_schema_versions": {
            "candidate": candidate_capacity_resolution.source_schema_version,
            "opportunity": opportunity_capacity_resolution.source_schema_version,
        },
        "position_count_posture": posture,
        "capacity_constraint_status": capacity_status,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "reason_codes": sorted(set(reason_codes)),
        "market_context_reference": market_context_summary.source_ref,
        "portfolio_policy_reference": portfolio_policy_summary.source_ref,
        "candidate_reference": candidate_summary.source_ref,
        "opportunity_reference": opportunity_summary.source_ref,
        "config_reference": config.config_source if config else "",
        "config_hash": f"sha256:{config_hash}" if config_hash else "",
        "config_payload": config_payload,
        "upstream_artifacts": {
            name: summary.to_dict(requested_business_date=business_date)
            for name, summary in summaries.items()
        },
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
            "implicit_latest_fallback_used": False,
            "previous_day_target_copied": False,
        },
        "shadow_comparison": shadow_comparison,
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_max_positions_authority_active": True,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False,
    }
    evidence = {
        "schema_version": "phase22_h_dynamic_position_count_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "capacity_constraint_status": capacity_status,
        "position_count_posture": posture,
        "minimum_position_count": minimum_position_count,
        "target_position_count": target_position_count,
        "maximum_position_count": maximum_position_count,
        "strategy_fixed_position_cap_used": False,
        "actual_target_position_count": actual_target_position_count,
        "meaningful_allocation_position_count": meaningful_allocation_position_count,
        "candidate_capacity_resolution": candidate_capacity_resolution.to_dict(),
        "opportunity_capacity_resolution": opportunity_capacity_resolution.to_dict(),
        "capacity_resolution_status": "PASS" if not capacity_review_reasons else "REVIEW_REQUIRED",
        "reason_codes": payload["reason_codes"],
        "runtime_behavior_changed": False,
    }
    return payload, evidence


def validate_dynamic_position_count_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {
        "schema_version",
        "producer_version",
        "business_date",
        "as_of",
        "feature_date",
        "artifact_lifecycle_status",
        "source_authority_status",
        "producer_result_status",
        "runtime_consumer_eligibility",
        "minimum_position_count",
        "target_position_count",
        "legacy_active_max_positions",
        "strategy_minimum_position_count",
        "strategy_target_position_count",
        "strategy_fixed_position_cap_used",
        "actual_target_position_count",
        "meaningful_allocation_position_count",
        "safety_hard_maximum_status",
        "ceiling_authority_status",
        "current_position_count",
        "available_candidate_count",
        "available_opportunity_count",
        "eligible_opportunity_count",
        "capital_affordable_position_count",
        "liquidity_feasible_position_count",
        "position_count_posture",
        "capacity_constraint_status",
        "confidence",
        "uncertainty",
        "reason_codes",
        "source_artifacts",
        "source_hashes",
        "temporal_safety",
        "shadow_comparison",
        "production_consumer_connected",
        "runtime_switch_performed",
        "legacy_authority_active",
    }
    errors.extend(f"required_field_missing:{field}" for field in sorted(required - set(payload)))
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    _enum_check(errors, payload, "artifact_lifecycle_status", ARTIFACT_LIFECYCLE_STATUSES)
    _enum_check(errors, payload, "source_authority_status", SOURCE_AUTHORITY_STATUSES)
    _enum_check(errors, payload, "producer_result_status", PRODUCER_RESULT_STATUSES)
    _enum_check(errors, payload, "runtime_consumer_eligibility", RUNTIME_CONSUMER_ELIGIBILITIES)
    _enum_check(errors, payload, "position_count_posture", POSITION_COUNT_POSTURES)
    _enum_check(errors, payload, "capacity_constraint_status", CAPACITY_CONSTRAINT_STATUSES)
    _enum_check(errors, payload, "safety_hard_maximum_status", {"PASS", "RESOLVED", "REVIEW_REQUIRED", "BLOCK", "NOT_APPLICABLE", "REMOVED"})
    _enum_check(errors, payload, "ceiling_authority_status", {"SEPARATED", "REVIEW_REQUIRED", "BLOCK"})
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_h_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_h_runtime_consumer_eligibility_must_be_not_eligible")
    for field in ("business_date", "feature_date"):
        try:
            _validate_iso_date(str(payload.get(field) or ""), field=field)
        except Exception:
            errors.append(f"invalid_date_format:{field}")
    try:
        _validate_rfc3339_timestamp(str(payload.get("as_of") or ""), field="as_of")
    except Exception:
        errors.append("invalid_timestamp_format:as_of")
    if str(payload.get("feature_date") or "9999-99-99") > str(payload.get("business_date") or ""):
        errors.append("feature_date_after_business_date")
    counts = {}
    nullable_unresolved_counts = {
        "target_position_count",
        "strategy_target_position_count",
        "actual_target_position_count",
    }
    target_unresolved = payload.get("target_position_count_resolution") == "UNRESOLVED"
    for field in (
        "minimum_position_count",
        "target_position_count",
        "legacy_active_max_positions",
        "strategy_minimum_position_count",
        "strategy_target_position_count",
        "actual_target_position_count",
        "meaningful_allocation_position_count",
        "current_position_count",
        "available_candidate_count",
        "available_opportunity_count",
    ):
        value = payload.get(field)
        if target_unresolved and field in nullable_unresolved_counts and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"invalid_count:{field}")
        else:
            counts[field] = value
    safety_value = payload.get("safety_hard_maximum")
    if safety_value is not None and (isinstance(safety_value, bool) or not isinstance(safety_value, int) or safety_value < 0):
        errors.append("invalid_count:safety_hard_maximum")
    elif safety_value is not None:
        counts["safety_hard_maximum"] = safety_value
    hierarchy_fields = {
        "minimum_position_count",
        "target_position_count",
        "available_candidate_count",
        "available_opportunity_count",
    }
    if hierarchy_fields <= set(counts):
        if not counts["minimum_position_count"] <= counts["target_position_count"]:
            errors.append("invalid_count_hierarchy")
        if counts["target_position_count"] > counts["available_candidate_count"]:
            errors.append("target_exceeds_available_candidate_count")
        if counts["target_position_count"] > counts["available_opportunity_count"]:
            errors.append("target_exceeds_available_opportunity_count")
    if {"minimum_position_count", "strategy_minimum_position_count"} <= set(counts) and counts["minimum_position_count"] != counts["strategy_minimum_position_count"]:
        errors.append("strategy_minimum_alias_mismatch")
    if {"target_position_count", "strategy_target_position_count"} <= set(counts) and counts["target_position_count"] != counts["strategy_target_position_count"]:
        errors.append("strategy_target_alias_mismatch")
    if payload.get("strategy_fixed_position_cap_used") is not False:
        errors.append("strategy_fixed_position_cap_must_not_be_used")
    confidence = payload.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        errors.append("invalid_confidence_range")
    if not isinstance(payload.get("reason_codes"), list):
        errors.append("reason_codes_not_list")
    if "capacity_resolution_status" in payload and payload.get("capacity_resolution_status") not in {"PASS", "REVIEW_REQUIRED"}:
        errors.append("invalid_enum:capacity_resolution_status")
    for field in ("candidate_capacity_resolution", "opportunity_capacity_resolution"):
        if field not in payload:
            continue
        value = payload.get(field)
        if not isinstance(value, dict):
            errors.append(f"{field}_not_object")
            continue
        if value.get("resolution_status") not in {"PASS", "REVIEW_REQUIRED"}:
            errors.append(f"invalid_capacity_resolution_status:{field}")
        resolved = value.get("resolved_count")
        if isinstance(resolved, bool) or not isinstance(resolved, int) or resolved < 0:
            errors.append(f"invalid_capacity_resolved_count:{field}")
    for field in ("capacity_constraint_reasons", "capacity_conflicts", "capacity_review_reasons", "source_paths"):
        if field in payload and not isinstance(payload.get(field), list):
            errors.append(f"{field}_not_list")
    if "source_schema_versions" in payload and not isinstance(payload.get("source_schema_versions"), dict):
        errors.append("source_schema_versions_not_object")
    if not isinstance(payload.get("source_artifacts"), list) or not payload.get("source_artifacts"):
        errors.append("source_artifacts_missing")
    if not isinstance(payload.get("source_hashes"), list) or not payload.get("source_hashes"):
        errors.append("source_hashes_missing")
    temporal = payload.get("temporal_safety")
    if not isinstance(temporal, dict):
        errors.append("temporal_safety_not_object")
    else:
        if temporal.get("future_leakage_used") is True and payload.get("producer_result_status") != "BLOCK":
            errors.append("future_leakage_must_block")
        if temporal.get("implicit_latest_fallback_used") is not False:
            errors.append("implicit_latest_fallback_forbidden")
        if temporal.get("previous_day_target_copied") is not False:
            errors.append("previous_day_target_copy_forbidden")
    for field in (
        "production_consumer_connected",
        "runtime_switch_performed",
        "cash_ratio_decided",
        "exposure_decided",
        "position_sizing_decided",
        "allocation_decided",
        "quantity_decided",
        "lot_rounding_decided",
    ):
        if payload.get(field) is not False:
            errors.append(f"phase22_h_field_must_be_false:{field}")
    if payload.get("legacy_authority_active") is not True:
        errors.append("phase22_h_legacy_authority_must_remain_active")
    if errors:
        raise DynamicPositionCountSchemaError(";".join(errors))
    return {"status": "PASS", "errors": []}


def verify_source_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    missing = []
    for item in payload.get("source_hashes") or []:
        path_text = str(item.get("path") or "")
        expected = _strip_sha256(str(item.get("sha256") or ""))
        if not path_text:
            missing.append(path_text)
            continue
        path = Path(path_text)
        if not path.is_file():
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": str(path), "expected": expected, "actual": actual})
    if mismatches:
        return {"status": "BLOCK", "reason": "source_hash_mismatch", "mismatches": mismatches, "missing": missing}
    if missing:
        return {"status": "REVIEW_REQUIRED", "reason": "source_missing", "mismatches": [], "missing": missing}
    return {"status": "PASS", "reason": "source_hashes_match", "mismatches": [], "missing": []}


def load_dynamic_position_count_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_dynamic_position_count_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise DynamicPositionCountConsumerError("BLOCK Dynamic Position Count artifact is not fixture-consumable")
    if for_production:
        raise DynamicPositionCountConsumerError("Phase22-H Dynamic Position Count artifact is not production-consumable")
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise DynamicPositionCountConsumerError("Phase22-H Dynamic Position Count must remain NOT_ELIGIBLE")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase22_h_produced_not_consumed_validation.v1",
        "dynamic_position_count_artifact_produced": bool(payload),
        "dynamic_position_count_schema_valid": True,
        "dynamic_position_count_production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_max_positions_authority_active": True,
        "runtime_behavior_changed": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False,
        "status": "PASS" if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE" else "BLOCK",
    }


def _ceiling_authority_status(producer_status: str, config: DynamicPositionCountConfig | None) -> str:
    if producer_status == "BLOCK":
        return "BLOCK"
    if config is None or config.safety_hard_maximum_status in {"REVIEW_REQUIRED", "BLOCK"}:
        return "REVIEW_REQUIRED"
    return "SEPARATED"


def dynamic_position_count_hash(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    return stable_payload_hash(clean)


def resolve_capacity_count(summary: DynamicPositionCountSourceSummary, *, artifact_class: str) -> CapacityResolution:
    if artifact_class == "candidate":
        canonical_field = "candidate_capacity_count"
        legacy_aliases = ("consumer_eligible_rows", "available_candidate_count", "eligible_candidate_count", "row_count")
        conflict_reason = "CANDIDATE_CAPACITY_FIELD_CONFLICT"
        missing_reason = "CANDIDATE_CAPACITY_FIELD_MISSING"
        invalid_reason = "CANDIDATE_CAPACITY_FIELD_INVALID"
    elif artifact_class == "opportunity":
        canonical_field = "opportunity_capacity_count"
        legacy_aliases = ("consumer_eligible_rows", "available_opportunity_count", "valid_opportunity_count", "ranking_count", "row_count")
        conflict_reason = "OPPORTUNITY_CAPACITY_FIELD_CONFLICT"
        missing_reason = "OPPORTUNITY_CAPACITY_FIELD_MISSING"
        invalid_reason = "OPPORTUNITY_CAPACITY_FIELD_INVALID"
    else:
        raise DynamicPositionCountSchemaError(f"unsupported capacity artifact_class: {artifact_class}")

    payload = summary.summary
    fields = (canonical_field, *legacy_aliases)
    observed_raw = {field: payload[field] for field in fields if field in payload}
    source_schema_version = str(payload.get("schema_version") or payload.get("artifact_schema_version") or "")
    parsed: dict[str, int] = {}
    invalid_fields: list[str] = []
    for field, value in observed_raw.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            invalid_fields.append(field)
        else:
            parsed[field] = value

    if invalid_fields:
        return CapacityResolution(
            artifact_class=artifact_class,
            resolved_count=0,
            canonical_field=canonical_field,
            source_field="",
            resolution_status="REVIEW_REQUIRED",
            resolution_reason=invalid_reason,
            legacy_alias_used=False,
            conflict_detected=False,
            source_schema_version=source_schema_version,
            source_path=summary.source_ref,
            source_hash=_strip_sha256(summary.source_hash),
            fields_observed=parsed,
            conflicts=tuple({"field": field, "value": observed_raw[field], "reason": "non_negative_integer_required"} for field in invalid_fields),
        )
    if not parsed:
        return CapacityResolution(
            artifact_class=artifact_class,
            resolved_count=0,
            canonical_field=canonical_field,
            source_field="",
            resolution_status="REVIEW_REQUIRED",
            resolution_reason=missing_reason,
            legacy_alias_used=False,
            conflict_detected=False,
            source_schema_version=source_schema_version,
            source_path=summary.source_ref,
            source_hash=_strip_sha256(summary.source_hash),
            fields_observed={},
            conflicts=(),
        )

    row_count = parsed.get("row_count")
    rejected_rows = payload.get("rejected_rows")
    specific_zero_fields = {
        field: value
        for field, value in parsed.items()
        if field not in {"row_count", "ranking_count"} and value == 0
    }
    legitimate_zero = bool(specific_zero_fields) and isinstance(row_count, int) and isinstance(rejected_rows, int) and row_count > 0 and rejected_rows == row_count
    if legitimate_zero:
        parsed = {field: value for field, value in parsed.items() if field not in {"row_count", "ranking_count"}}

    unique_counts = set(parsed.values())
    if len(unique_counts) > 1:
        source_field = canonical_field if canonical_field in parsed else next(iter(parsed))
        return CapacityResolution(
            artifact_class=artifact_class,
            resolved_count=int(parsed[source_field]),
            canonical_field=canonical_field,
            source_field=source_field,
            resolution_status="REVIEW_REQUIRED",
            resolution_reason=conflict_reason,
            legacy_alias_used=source_field != canonical_field,
            conflict_detected=True,
            source_schema_version=source_schema_version,
            source_path=summary.source_ref,
            source_hash=_strip_sha256(summary.source_hash),
            fields_observed=parsed,
            conflicts=(
                {
                    "reason": conflict_reason,
                    "fields": dict(parsed),
                },
            ),
        )

    if canonical_field in parsed:
        source_field = canonical_field
    else:
        source_field = next(field for field in legacy_aliases if field in parsed)
    resolved = int(parsed[source_field])
    return CapacityResolution(
        artifact_class=artifact_class,
        resolved_count=resolved,
        canonical_field=canonical_field,
        source_field=source_field,
        resolution_status="PASS",
        resolution_reason="LEGITIMATE_ZERO_CAPACITY" if legitimate_zero else "CAPACITY_RESOLVED",
        legacy_alias_used=source_field != canonical_field,
        conflict_detected=False,
        source_schema_version=source_schema_version,
        source_path=summary.source_ref,
        source_hash=_strip_sha256(summary.source_hash),
        fields_observed=parsed,
        conflicts=(),
    )


def stable_payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _decide_counts(
    *,
    config: DynamicPositionCountConfig,
    market_context: Mapping[str, Any],
    portfolio_policy: Mapping[str, Any],
    available_candidate_count: int,
    available_opportunity_count: int,
    current_position_count: int,
) -> dict[str, Any]:
    trend = str(market_context.get("trend_regime") or "RANGE")
    breadth = str(market_context.get("market_breadth") or "NEUTRAL")
    volatility = str(market_context.get("volatility_regime") or "NORMAL")
    risk_posture = str(portfolio_policy.get("risk_posture") or "UNRESOLVED")
    entry_posture = str(portfolio_policy.get("entry_posture") or "UNRESOLVED")
    uncertainty = str(market_context.get("uncertainty") or portfolio_policy.get("uncertainty") or "LOW")
    if uncertainty not in config.uncertainty_rules:
        uncertainty = "MEDIUM"

    base_target = int(config.regime_rules[trend])
    target = base_target
    reason_codes = [f"trend_regime:{trend}", f"market_breadth:{breadth}", f"volatility_regime:{volatility}"]

    breadth_rule = config.breadth_rules[breadth]
    target += int(breadth_rule.get("target_delta", 0))

    volatility_rule = config.volatility_rules[volatility]
    target += int(volatility_rule.get("target_delta", 0))

    uncertainty_rule = config.uncertainty_rules[uncertainty]
    target += int(uncertainty_rule.get("target_delta", 0))

    meaningful_capacity = min(available_candidate_count, available_opportunity_count)
    if risk_posture == "RISK_ON" and entry_posture == "EXPAND" and breadth == "STRONG":
        target = meaningful_capacity
        reason_codes.append("capacity_expansion_uses_full_eligible_opportunity_count")
    minimum = min(config.strategy_minimum_position_count, meaningful_capacity)
    raw_target = max(target, minimum)
    capacity_limited_target = min(raw_target, meaningful_capacity)
    target = max(minimum if capacity_limited_target >= minimum else 0, capacity_limited_target)
    if minimum > target:
        minimum = target

    capacity_status = "SUFFICIENT"
    if trend in {"BEAR", "CORRECTION"} or risk_posture in {"DEFENSIVE", "RISK_OFF"} or entry_posture in {"RESTRICT", "PAUSE"}:
        capacity_status = "MARKET_RISK_CONSTRAINED"
        reason_codes.append("market_or_policy_risk_constrained")
    if uncertainty in {"HIGH", "UPSTREAM_REVIEW_REQUIRED"}:
        capacity_status = "UNCERTAINTY_CONSTRAINED"
        reason_codes.append("uncertainty_constrained")
    if available_candidate_count < raw_target:
        capacity_status = "CANDIDATE_CONSTRAINED"
        reason_codes.append("candidate_capacity_constrained")
    if available_opportunity_count < raw_target:
        capacity_status = "OPPORTUNITY_CONSTRAINED"
        reason_codes.append("opportunity_capacity_constrained")

    if entry_posture == "PAUSE" or target == 0:
        posture = "PAUSE_NEW_ENTRY"
    elif target > current_position_count:
        posture = "INCREASE"
    elif target < current_position_count:
        posture = "DECREASE"
    else:
        posture = "MAINTAIN"
    confidence = min(
        _ratio(market_context.get("confidence"), default=1.0),
        _ratio(portfolio_policy.get("confidence"), default=1.0),
    )
    if capacity_status != "SUFFICIENT":
        confidence = min(confidence, 0.8)
    return {
        "minimum_position_count": int(minimum),
        "target_position_count": int(target),
        "maximum_position_count": None,
        "capacity_constraint_status": capacity_status,
        "position_count_posture": posture,
        "confidence": round(float(confidence), 6),
        "uncertainty": uncertainty,
        "reason_codes": reason_codes,
    }


def _summary_count(summary: DynamicPositionCountSourceSummary, field: str, *, fallback_field: str) -> int:
    payload = summary.summary
    value = payload.get(field, payload.get(fallback_field, 0))
    return _coerce_count(value, field)


def _summary_count_optional(summary: DynamicPositionCountSourceSummary, field: str, default: int) -> int:
    value = summary.summary.get(field, default)
    return _coerce_count(value, field)


def _summary_aligned(summary: DynamicPositionCountSourceSummary, *, business_date: str) -> bool:
    return summary.business_date == business_date and bool(summary.feature_date) and summary.feature_date <= business_date


def _coerce_count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DynamicPositionCountSchemaError(f"{field} must be a non-negative integer")
    return value


def _ratio(value: Any, *, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(0.0, min(float(value), 1.0))


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DynamicPositionCountConfigError(f"{field} must be a non-empty string")
    return value.strip()


def _required_int(payload: Mapping[str, Any], field: str, *, minimum: int) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DynamicPositionCountConfigError(f"{field} must be an integer >= {minimum}")
    return value


def _optional_int(value: Any, field: str, *, minimum: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DynamicPositionCountConfigError(f"{field} must be an integer >= {minimum}")
    return value


def _required_object(payload: Mapping[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise DynamicPositionCountConfigError(f"{field} must be an object")
    return dict(value)


def _required_int_mapping(payload: Mapping[str, Any], field: str, *, keys: set[str]) -> dict[str, int]:
    value = _required_object(payload, field)
    missing = keys - set(value)
    if missing:
        raise DynamicPositionCountConfigError(f"{field} missing keys: {','.join(sorted(missing))}")
    result: dict[str, int] = {}
    for key in keys:
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise DynamicPositionCountConfigError(f"{field}.{key} must be a non-negative integer")
        result[key] = item
    return result


def _required_rule_mapping(payload: Mapping[str, Any], field: str, *, keys: set[str]) -> dict[str, dict[str, int]]:
    value = _required_object(payload, field)
    missing = keys - set(value)
    if missing:
        raise DynamicPositionCountConfigError(f"{field} missing keys: {','.join(sorted(missing))}")
    result: dict[str, dict[str, int]] = {}
    for key in keys:
        rule = value[key]
        if not isinstance(rule, dict):
            raise DynamicPositionCountConfigError(f"{field}.{key} must be an object")
        result[key] = {
            "target_delta": _rule_int(rule, "target_delta"),
            "maximum_cap": _rule_int(rule, "maximum_cap", minimum=0),
        }
    return result


def _required_policy_rules(payload: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    rules = _required_object(payload, "portfolio_policy_rules")
    return {
        "risk_posture_caps": _required_nested_caps(rules, "risk_posture_caps", keys=RISK_POSTURES),
        "entry_posture_caps": _required_nested_caps(rules, "entry_posture_caps", keys=ENTRY_POSTURES),
    }


def _required_nested_caps(payload: Mapping[str, Any], field: str, *, keys: set[str]) -> dict[str, int]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise DynamicPositionCountConfigError(f"portfolio_policy_rules.{field} must be an object")
    missing = keys - set(value)
    if missing:
        raise DynamicPositionCountConfigError(f"portfolio_policy_rules.{field} missing keys: {','.join(sorted(missing))}")
    result: dict[str, int] = {}
    for key in keys:
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise DynamicPositionCountConfigError(f"portfolio_policy_rules.{field}.{key} must be a non-negative integer")
        result[key] = item
    return result


def _rule_int(rule: Mapping[str, Any], field: str, *, minimum: int | None = None) -> int:
    value = rule.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DynamicPositionCountConfigError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise DynamicPositionCountConfigError(f"{field} must be >= {minimum}")
    return value


def _deep_dict(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: dict(value) if isinstance(value, Mapping) else value for key, value in payload.items()}


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
