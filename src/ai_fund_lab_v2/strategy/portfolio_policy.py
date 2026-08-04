from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.strategy.candidate_opportunity_compatibility import (
    INCOMPATIBLE_DATE,
    INCOMPATIBLE_HASH,
    INCOMPATIBLE_SCHEMA,
    SOURCE_BLOCKED,
    SOURCE_MISSING,
    SOURCE_NOT_ELIGIBLE,
    SOURCE_REVIEW_REQUIRED,
    validate_corporate_event_compatibility,
    validate_market_context_compatibility,
)
from ai_fund_lab_v2.strategy import dynamic_cash_exposure
from ai_fund_lab_v2.strategy import dynamic_position_count
from ai_fund_lab_v2.strategy.status_contract import status_contract_fields


SCHEMA_VERSION = "portfolio_policy.v1"
PRODUCER_VERSION = "phase22_c_portfolio_policy_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"
INTERNAL_POSITION_COUNT_CONFIG_PATH = Path("configs/strategy/dynamic_position_count.json")
INTERNAL_CASH_EXPOSURE_CONFIG_PATH = Path("configs/strategy/dynamic_cash_exposure.json")

RISK_POSTURES = {"RISK_ON", "BALANCED", "DEFENSIVE", "RISK_OFF", "UNRESOLVED"}
ENTRY_POSTURES = {"EXPAND", "MAINTAIN", "RESTRICT", "PAUSE", "UNRESOLVED"}
POSITION_COUNT_POSTURES = {"INCREASE", "MAINTAIN", "DECREASE", "UNRESOLVED"}
CASH_POSTURES = {"DEPLOY", "MAINTAIN", "RAISE", "UNRESOLVED"}
EXPOSURE_POSTURES = {"INCREASE", "MAINTAIN", "REDUCE", "UNRESOLVED"}
POSITION_MANAGEMENT_BIASES = {"ADD_BIASED", "NEUTRAL", "REDUCE_BIASED", "EXIT_BIASED", "UNRESOLVED"}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
FORBIDDEN_CONCRETE_FIELDS = {
    "minimum_positions",
    "target_positions",
    "maximum_positions",
    "target_cash_ratio",
    "cash_ratio",
    "target_exposure_ratio",
    "gross_exposure",
    "position_size",
    "minimum_holding",
    "cooldown",
}
BLOCKING_UPSTREAM_STATUSES = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING}
REVIEW_UPSTREAM_STATUSES = {SOURCE_REVIEW_REQUIRED, SOURCE_NOT_ELIGIBLE}


class PortfolioPolicyError(RuntimeError):
    pass


class PortfolioPolicySchemaError(PortfolioPolicyError):
    pass


class PortfolioPolicyConsumerError(PortfolioPolicyError):
    pass


class PortfolioPolicyConfigError(PortfolioPolicyError):
    pass


@dataclass(frozen=True)
class PortfolioPolicyInputSummary:
    status: str
    business_date: str
    feature_date: str
    summary: dict[str, Any]
    source_ref: str = ""
    source_hash: str = ""


@dataclass(frozen=True)
class PortfolioPolicyConfig:
    config_version: str
    config_source: str
    intent_policy: dict[str, str]
    single_name_weight_cap: float | None = None
    single_name_weight_cap_source: str = ""
    require_explicit_intent_policy: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "portfolio_policy_config.v1",
            "config_version": self.config_version,
            "config_source": self.config_source,
            "intent_policy": dict(self.intent_policy),
            "single_name_weight_cap": self.single_name_weight_cap,
            "single_name_weight_cap_source": self.single_name_weight_cap_source,
            "require_explicit_intent_policy": self.require_explicit_intent_policy,
        }


@dataclass(frozen=True)
class PortfolioPolicyProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "portfolio_policy" / business_date / "portfolio_policy.json"


def load_portfolio_policy_config(path: Path | str) -> PortfolioPolicyConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise PortfolioPolicyConfigError(f"missing_portfolio_policy_config_authority:{config_path}")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != "portfolio_policy_config.v1":
        raise PortfolioPolicyConfigError("unsupported portfolio policy config schema")
    intent = payload.get("intent_policy")
    if not isinstance(intent, dict):
        raise PortfolioPolicyConfigError("portfolio policy intent_policy required")
    missing_intents = sorted(_required_intent_fields() - set(intent))
    if missing_intents:
        raise PortfolioPolicyConfigError(f"portfolio policy required intents missing:{','.join(missing_intents)}")
    invalid_intents = _invalid_intent_values({str(k): str(v) for k, v in intent.items()})
    if invalid_intents:
        raise PortfolioPolicyConfigError(f"portfolio policy invalid intents:{sorted(invalid_intents)}")
    single_name_weight_cap = _config_ratio(payload.get("single_name_weight_cap"), field="single_name_weight_cap")
    return PortfolioPolicyConfig(
        config_version=str(payload.get("config_version") or ""),
        config_source=str(config_path),
        intent_policy={str(k): str(v) for k, v in intent.items()},
        single_name_weight_cap=single_name_weight_cap,
        single_name_weight_cap_source=str(payload.get("single_name_weight_cap_source") or f"{config_path}#single_name_weight_cap"),
        require_explicit_intent_policy=bool(payload.get("require_explicit_intent_policy", True)),
    )


def produce_portfolio_policy_artifact(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    candidate_summary: PortfolioPolicyInputSummary,
    opportunity_summary: PortfolioPolicyInputSummary,
    current_portfolio_summary: Mapping[str, Any],
    current_cash_summary: Mapping[str, Any],
    current_exposure_summary: Mapping[str, Any],
    policy_config: PortfolioPolicyConfig | None,
    output_path: Path | str,
    pending_reservation_summary: Mapping[str, Any] | None = None,
    safety_limit_summary: Mapping[str, Any] | None = None,
    position_count_config: dynamic_position_count.DynamicPositionCountConfig | None = None,
    cash_exposure_config: dynamic_cash_exposure.DynamicCashExposureConfig | None = None,
    position_count_safety_hard_maximum: int | None = None,
    existing_active_max_positions: int = 5,
    as_of: str | None = None,
    expected_policy_config_hash: str | None = None,
) -> PortfolioPolicyProducerResult:
    payload, evidence = build_portfolio_policy_payload(
        business_date=business_date,
        market_context_artifact_path=market_context_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_portfolio_summary=current_portfolio_summary,
        current_cash_summary=current_cash_summary,
        current_exposure_summary=current_exposure_summary,
        pending_reservation_summary=pending_reservation_summary,
        safety_limit_summary=safety_limit_summary,
        position_count_config=position_count_config,
        cash_exposure_config=cash_exposure_config,
        position_count_safety_hard_maximum=position_count_safety_hard_maximum,
        existing_active_max_positions=existing_active_max_positions,
        policy_config=policy_config,
        as_of=as_of,
        expected_policy_config_hash=expected_policy_config_hash,
    )
    validate_portfolio_policy_artifact(payload)
    artifact_hash = portfolio_policy_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return PortfolioPolicyProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_portfolio_policy_payload(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    candidate_summary: PortfolioPolicyInputSummary,
    opportunity_summary: PortfolioPolicyInputSummary,
    current_portfolio_summary: Mapping[str, Any],
    current_cash_summary: Mapping[str, Any],
    current_exposure_summary: Mapping[str, Any],
    policy_config: PortfolioPolicyConfig | None,
    pending_reservation_summary: Mapping[str, Any] | None = None,
    safety_limit_summary: Mapping[str, Any] | None = None,
    position_count_config: dynamic_position_count.DynamicPositionCountConfig | None = None,
    cash_exposure_config: dynamic_cash_exposure.DynamicCashExposureConfig | None = None,
    position_count_safety_hard_maximum: int | None = None,
    existing_active_max_positions: int = 5,
    as_of: str | None = None,
    expected_policy_config_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    market_result = validate_market_context_compatibility(
        market_context_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    corporate_result = validate_corporate_event_compatibility(
        corporate_event_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    summaries = {
        "candidate_summary": _summary_payload(candidate_summary, business_date=business_date),
        "opportunity_summary": _summary_payload(opportunity_summary, business_date=business_date),
    }
    current_summaries = {
        "current_portfolio_summary": dict(current_portfolio_summary),
        "current_cash_summary": dict(current_cash_summary),
        "current_exposure_summary": dict(current_exposure_summary),
    }
    reason_codes: list[str] = []
    source_status = "VALID"
    upstream_statuses = [market_result.status, corporate_result.status]
    if any(status in BLOCKING_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "BLOCK"
        reason_codes.extend([f"upstream_block:{status}" for status in upstream_statuses if status in BLOCKING_UPSTREAM_STATUSES])
        source_status = "HASH_MISMATCH" if INCOMPATIBLE_HASH in upstream_statuses else ("MISSING" if SOURCE_MISSING in upstream_statuses else "AUTHORITY_CONFLICT")
    elif any(status in REVIEW_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "REVIEW_REQUIRED"
        reason_codes.extend([f"upstream_review_required:{status}" for status in upstream_statuses if status in REVIEW_UPSTREAM_STATUSES])
    else:
        producer_status = "PASS"

    if not _summary_aligned(candidate_summary, business_date=business_date):
        producer_status = "BLOCK"
        reason_codes.append("candidate_summary_date_mismatch")
    if not _summary_aligned(opportunity_summary, business_date=business_date):
        producer_status = "BLOCK"
        reason_codes.append("opportunity_summary_date_mismatch")
    if candidate_summary.status == "BLOCK" or opportunity_summary.status == "BLOCK":
        producer_status = "BLOCK"
        reason_codes.append("summary_input_block")
    elif candidate_summary.status != "PASS" or opportunity_summary.status != "PASS":
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("summary_input_review_required")

    config_hash = ""
    config_source_hash = ""
    config_payload: dict[str, Any] | None = None
    if policy_config is None:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("policy_config_required")
    else:
        config_payload = policy_config.to_dict()
        config_hash = stable_payload_hash(config_payload)
        config_path = Path(policy_config.config_source)
        if config_path.is_file():
            config_source_hash = sha256_file(config_path)
        else:
            config_source_hash = config_hash
        if expected_policy_config_hash and _strip_sha256(expected_policy_config_hash) != config_hash:
            producer_status = "BLOCK"
            source_status = "HASH_MISMATCH"
            reason_codes.append("policy_config_hash_mismatch")
        missing_intents = sorted(_required_intent_fields() - set(policy_config.intent_policy))
        invalid_intents = _invalid_intent_values(policy_config.intent_policy)
        if missing_intents:
            if producer_status != "BLOCK":
                producer_status = "REVIEW_REQUIRED"
            reason_codes.append("policy_config_intent_required")
        if invalid_intents:
            producer_status = "BLOCK"
            reason_codes.append("policy_config_invalid_intent")

    source_artifacts = [
        {"role": "market_context", "path": str(market_context_artifact_path or ""), "required": True, "status": market_result.status},
        {"role": "corporate_event", "path": str(corporate_event_artifact_path or ""), "required": True, "status": corporate_result.status},
        {"role": "candidate_summary", "path": candidate_summary.source_ref, "required": True, "status": candidate_summary.status},
        {"role": "opportunity_summary", "path": opportunity_summary.source_ref, "required": True, "status": opportunity_summary.status},
        {"role": "policy_config", "path": policy_config.config_source if policy_config else "", "required": True, "status": "PASS" if policy_config else "REVIEW_REQUIRED"},
    ]
    source_hashes = [
        *([{"role": "candidate_summary", "path": candidate_summary.source_ref, "sha256": _strip_sha256(candidate_summary.source_hash)}] if candidate_summary.source_hash else []),
        *([{"role": "opportunity_summary", "path": opportunity_summary.source_ref, "sha256": _strip_sha256(opportunity_summary.source_hash)}] if opportunity_summary.source_hash else []),
        *([{"role": "policy_config", "path": policy_config.config_source, "sha256": config_source_hash}] if policy_config else []),
    ]
    if not candidate_summary.source_hash or not opportunity_summary.source_hash or not config_hash:
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("source_lineage_hash_required")

    policy_intent = _policy_intent(policy_config)
    feature_date = min(
        [value for value in (market_result.feature_date, corporate_result.feature_date, candidate_summary.feature_date, opportunity_summary.feature_date) if value]
        or [business_date]
    )
    future_leakage_used = any(value and value > business_date for value in (feature_date, candidate_summary.feature_date, opportunity_summary.feature_date))
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_feature_date_detected")
    if position_count_config is None:
        position_count_config = _load_internal_position_count_config()
    if cash_exposure_config is None:
        cash_exposure_config = _load_internal_cash_exposure_config()
    internal_policy = _resolve_internal_portfolio_policy(
        business_date=business_date,
        as_of=as_of,
        producer_status=producer_status,
        policy_intent=policy_intent,
        market_context_artifact_path=market_context_artifact_path,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_portfolio_summary=current_portfolio_summary,
        current_cash_summary=current_cash_summary,
        current_exposure_summary=current_exposure_summary,
        pending_reservation_summary=pending_reservation_summary or {},
        safety_limit_summary=safety_limit_summary or {},
        policy_config=policy_config,
        position_count_config=position_count_config,
        cash_exposure_config=cash_exposure_config,
        position_count_safety_hard_maximum=position_count_safety_hard_maximum,
        existing_active_max_positions=existing_active_max_positions,
    )
    reason_codes.extend(str(code) for code in internal_policy["reason_codes"])
    if internal_policy["status"] == "BLOCK":
        producer_status = "BLOCK"
    elif internal_policy["status"] == "REVIEW_REQUIRED" and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"
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
            decision_resolution="RESOLVED" if producer_status == "PASS" else "UNRESOLVED",
        ),
        "risk_posture": policy_intent["risk_posture"],
        "entry_posture": policy_intent["entry_posture"],
        "position_count_posture": policy_intent["position_count_posture"],
        "cash_posture": policy_intent["cash_posture"],
        "exposure_posture": policy_intent["exposure_posture"],
        "position_management_bias": policy_intent["position_management_bias"],
        "target_position_count_resolution": internal_policy["target_position_count_resolution"],
        "target_position_count": internal_policy["target_position_count"],
        "minimum_position_count": internal_policy["minimum_position_count"],
        "maximum_position_count": internal_policy["maximum_position_count"],
        "resolved_candidate_capacity": internal_policy["resolved_candidate_capacity"],
        "resolved_opportunity_capacity": internal_policy["resolved_opportunity_capacity"],
        "meaningful_allocation_position_count": internal_policy["meaningful_allocation_position_count"],
        "target_gross_exposure_ratio_resolution": internal_policy["target_gross_exposure_ratio_resolution"],
        "target_gross_exposure_ratio": internal_policy["target_gross_exposure_ratio"],
        "target_gross_exposure": internal_policy["target_gross_exposure_ratio"],
        "minimum_gross_exposure_ratio": internal_policy["minimum_gross_exposure_ratio"],
        "maximum_gross_exposure_ratio": internal_policy["maximum_gross_exposure_ratio"],
        "cash_reserve_ratio_resolution": internal_policy["cash_reserve_ratio_resolution"],
        "cash_reserve_ratio": internal_policy["cash_reserve_ratio"],
        "cash_reserve": internal_policy["cash_reserve_ratio"],
        "minimum_cash_ratio": internal_policy["minimum_cash_ratio"],
        "maximum_cash_ratio": internal_policy["maximum_cash_ratio"],
        "single_name_weight_cap": internal_policy["single_name_weight_cap"],
        "single_name_weight_cap_source": internal_policy["single_name_weight_cap_source"],
        "single_name_weight_cap_authority": internal_policy["single_name_weight_cap_authority"],
        "deployment_posture": internal_policy["deployment_posture"],
        "portfolio_level_decision_owner": "portfolio_policy",
        "dynamic_position_count_merge_status": "KEEP_INTERNAL_REMOVE_RUNTIME_WIRING",
        "dynamic_cash_exposure_merge_status": "KEEP_INTERNAL_REMOVE_RUNTIME_WIRING",
        "dynamic_position_count_artifact_policy": "REMOVE",
        "dynamic_cash_exposure_artifact_policy": "REMOVE",
        "internal_resolvers": internal_policy["internal_resolvers"],
        "confidence": 0.0 if producer_status != "PASS" else 1.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED" if producer_status == "REVIEW_REQUIRED" else ("BLOCKING_INPUT" if producer_status == "BLOCK" else "LOW"),
        "reason_codes": sorted(set(reason_codes)),
        "deferred_concrete_values": sorted(FORBIDDEN_CONCRETE_FIELDS),
        "concrete_values_decided": producer_status == "PASS",
        "upstream_artifacts": {
            "market_context": market_result.to_dict(),
            "corporate_event": corporate_result.to_dict(),
            **summaries,
            **current_summaries,
            "internal_policy_resolvers": internal_policy["upstream_artifacts"],
            "policy_config_hash": f"sha256:{config_hash}" if config_hash else "",
            "policy_config": config_payload,
        },
        "source_artifacts": source_artifacts,
        "source_hashes": [*source_hashes, *internal_policy["source_hashes"]],
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
            "implicit_latest_fallback_used": False,
            "previous_day_policy_copied": False,
        },
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": False,
    }
    evidence = {
        "schema_version": "phase22_c_portfolio_policy_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "market_context_status": market_result.status,
        "corporate_event_status": corporate_result.status,
        "candidate_summary_status": candidate_summary.status,
        "opportunity_summary_status": opportunity_summary.status,
        "concrete_values_decided": payload["concrete_values_decided"],
        "target_position_count": payload["target_position_count"],
        "target_gross_exposure_ratio": payload["target_gross_exposure_ratio"],
        "cash_reserve_ratio": payload["cash_reserve_ratio"],
        "single_name_weight_cap": payload["single_name_weight_cap"],
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def validate_portfolio_policy_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = {
        "schema_version",
        "business_date",
        "as_of",
        "feature_date",
        "artifact_lifecycle_status",
        "source_authority_status",
        "producer_result_status",
        "runtime_consumer_eligibility",
        "risk_posture",
        "entry_posture",
        "position_count_posture",
        "cash_posture",
        "exposure_posture",
        "position_management_bias",
        "target_position_count_resolution",
        "target_position_count",
        "target_gross_exposure_ratio_resolution",
        "target_gross_exposure_ratio",
        "target_gross_exposure",
        "cash_reserve_ratio_resolution",
        "cash_reserve_ratio",
        "cash_reserve",
        "single_name_weight_cap",
        "single_name_weight_cap_source",
        "single_name_weight_cap_authority",
        "deployment_posture",
        "confidence",
        "uncertainty",
        "reason_codes",
        "deferred_concrete_values",
        "concrete_values_decided",
        "upstream_artifacts",
        "source_artifacts",
        "source_hashes",
        "temporal_safety",
    }
    errors.extend(f"required_field_missing:{field}" for field in sorted(required - set(payload)))
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    _enum_check(errors, payload, "artifact_lifecycle_status", ARTIFACT_LIFECYCLE_STATUSES)
    _enum_check(errors, payload, "source_authority_status", SOURCE_AUTHORITY_STATUSES)
    _enum_check(errors, payload, "producer_result_status", PRODUCER_RESULT_STATUSES)
    _enum_check(errors, payload, "runtime_consumer_eligibility", RUNTIME_CONSUMER_ELIGIBILITIES)
    _enum_check(errors, payload, "risk_posture", RISK_POSTURES)
    _enum_check(errors, payload, "entry_posture", ENTRY_POSTURES)
    _enum_check(errors, payload, "position_count_posture", POSITION_COUNT_POSTURES)
    _enum_check(errors, payload, "cash_posture", CASH_POSTURES)
    _enum_check(errors, payload, "exposure_posture", EXPOSURE_POSTURES)
    _enum_check(errors, payload, "position_management_bias", POSITION_MANAGEMENT_BIASES)
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_c_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_c_runtime_consumer_eligibility_must_be_not_eligible")
    forbidden_present = sorted(FORBIDDEN_CONCRETE_FIELDS & set(payload))
    errors.extend(f"concrete_value_field_forbidden:{field}" for field in forbidden_present)
    if payload.get("concrete_values_decided") not in {True, False}:
        errors.append("concrete_values_decided_not_boolean")
    _optional_non_negative_int(errors, payload, "target_position_count")
    _optional_ratio(errors, payload, "target_gross_exposure_ratio")
    _optional_ratio(errors, payload, "target_gross_exposure")
    _optional_ratio(errors, payload, "cash_reserve_ratio")
    _optional_ratio(errors, payload, "cash_reserve")
    _optional_ratio(errors, payload, "single_name_weight_cap")
    if (
        payload.get("target_gross_exposure_ratio") is not None
        and payload.get("target_gross_exposure") is not None
        and abs(float(payload["target_gross_exposure_ratio"]) - float(payload["target_gross_exposure"])) > 0.000001
    ):
        errors.append("target_gross_exposure_ratio_absolute_conflict")
    if (
        payload.get("cash_reserve_ratio") is not None
        and payload.get("cash_reserve") is not None
        and abs(float(payload["cash_reserve_ratio"]) - float(payload["cash_reserve"])) > 0.000001
    ):
        errors.append("cash_reserve_ratio_absolute_conflict")
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
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        errors.append("invalid_confidence_range")
    if not isinstance(payload.get("reason_codes"), list):
        errors.append("reason_codes_not_list")
    if not isinstance(payload.get("upstream_artifacts"), dict):
        errors.append("upstream_artifacts_not_object")
    if not isinstance(payload.get("single_name_weight_cap_authority"), dict):
        errors.append("single_name_weight_cap_authority_not_object")
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
        if temporal.get("previous_day_policy_copied") is not False:
            errors.append("previous_day_policy_copy_forbidden")
    if errors:
        raise PortfolioPolicySchemaError(";".join(errors))
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


def load_portfolio_policy_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_portfolio_policy_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise PortfolioPolicyConsumerError("BLOCK Portfolio Policy artifact is not fixture-consumable")
    if for_production:
        raise PortfolioPolicyConsumerError("Phase22-C Portfolio Policy artifact is not production-consumable")
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise PortfolioPolicyConsumerError("Phase22-C Portfolio Policy must remain NOT_ELIGIBLE")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_artifacts") if isinstance(payload.get("upstream_artifacts"), dict) else {}
    return {
        "schema_version": "phase22_c_produced_not_consumed_validation.v1",
        "portfolio_policy_artifact_produced": bool(payload),
        "portfolio_policy_schema_valid": True,
        "market_context_shadow_read": bool((upstream.get("market_context") or {}).get("shadow_read_allowed")),
        "corporate_event_shadow_read": bool((upstream.get("corporate_event") or {}).get("shadow_read_allowed")),
        "portfolio_policy_production_consumer_connected": bool(payload.get("portfolio_level_decision_owner") == "portfolio_policy"),
        "runtime_switch_performed": False,
        "legacy_authority_active": bool(payload.get("legacy_authority_active", False)),
        "candidate_behavior_changed": False,
        "opportunity_behavior_changed": False,
        "pm_behavior_changed": False,
        "position_management_changed": False,
        "portfolio_construction_changed": False,
        "capital_deployment_changed": False,
        "runtime_planning_changed": False,
        "pending_changed": False,
        "submit_changed": False,
        "status": "PASS" if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE" else "BLOCK",
    }


def portfolio_policy_hash(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    return stable_payload_hash(clean)


def stable_payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_internal_portfolio_policy(
    *,
    business_date: str,
    as_of: str,
    producer_status: str,
    policy_intent: Mapping[str, Any],
    market_context_artifact_path: Path | str | None,
    candidate_summary: PortfolioPolicyInputSummary,
    opportunity_summary: PortfolioPolicyInputSummary,
    current_portfolio_summary: Mapping[str, Any],
    current_cash_summary: Mapping[str, Any],
    current_exposure_summary: Mapping[str, Any],
    pending_reservation_summary: Mapping[str, Any],
    safety_limit_summary: Mapping[str, Any],
    policy_config: PortfolioPolicyConfig | None,
    position_count_config: dynamic_position_count.DynamicPositionCountConfig | None,
    cash_exposure_config: dynamic_cash_exposure.DynamicCashExposureConfig | None,
    position_count_safety_hard_maximum: int | None,
    existing_active_max_positions: int,
) -> dict[str, Any]:
    market_payload = _read_json_if_file(market_context_artifact_path)
    policy_summary = {
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "portfolio_policy:inline_intent",
        "source_hash": stable_payload_hash(dict(policy_intent)),
        "summary": dict(policy_intent),
    }
    status = "PASS" if producer_status == "PASS" else producer_status
    dpc_payload, _ = dynamic_position_count.build_dynamic_position_count_payload(
        business_date=business_date,
        market_context_summary=_dpc_source(status=status, business_date=business_date, summary=market_payload, source_ref=str(market_context_artifact_path or ""), source_hash=_path_hash(market_context_artifact_path)),
        portfolio_policy_summary=_dpc_source(status=status, business_date=business_date, summary=policy_summary["summary"], source_ref=policy_summary["source_ref"], source_hash=policy_summary["source_hash"]),
        candidate_summary=_dpc_source_from_pp(candidate_summary),
        opportunity_summary=_dpc_source_from_pp(opportunity_summary),
        current_portfolio_summary=_dpc_source(status="PASS", business_date=business_date, summary=current_portfolio_summary, source_ref="portfolio_policy:current_portfolio_summary", source_hash=stable_payload_hash(dict(current_portfolio_summary))),
        safety_hard_maximum=position_count_safety_hard_maximum,
        existing_active_max_positions=existing_active_max_positions,
        config=position_count_config,
        as_of=as_of,
    )
    dce_payload, _ = dynamic_cash_exposure.build_dynamic_cash_exposure_payload(
        business_date=business_date,
        market_context_summary=_dce_source(status=status, business_date=business_date, summary=market_payload, source_ref=str(market_context_artifact_path or ""), source_hash=_path_hash(market_context_artifact_path)),
        portfolio_policy_summary=_dce_source(status=status, business_date=business_date, summary=policy_summary["summary"], source_ref=policy_summary["source_ref"], source_hash=policy_summary["source_hash"]),
        dynamic_position_count_summary=_dce_source(status=str(dpc_payload.get("producer_result_status") or "REVIEW_REQUIRED"), business_date=business_date, summary=dpc_payload, source_ref="portfolio_policy:internal_dynamic_position_count", source_hash=dynamic_position_count.dynamic_position_count_hash(dpc_payload)),
        candidate_summary=_dce_source_from_pp(candidate_summary),
        opportunity_summary=_dce_source_from_pp(opportunity_summary),
        current_cash_summary=_dce_source(status="PASS", business_date=business_date, summary=current_cash_summary, source_ref="portfolio_policy:current_cash_summary", source_hash=stable_payload_hash(dict(current_cash_summary))),
        current_exposure_summary=_dce_source(status="PASS", business_date=business_date, summary=current_exposure_summary, source_ref="portfolio_policy:current_exposure_summary", source_hash=stable_payload_hash(dict(current_exposure_summary))),
        pending_reservation_summary=_dce_source(status="PASS", business_date=business_date, summary=pending_reservation_summary, source_ref="portfolio_policy:pending_reservation_summary", source_hash=stable_payload_hash(dict(pending_reservation_summary))),
        safety_limit_summary=_dce_source(status="PASS", business_date=business_date, summary=safety_limit_summary, source_ref="portfolio_policy:safety_limit_summary", source_hash=stable_payload_hash(dict(safety_limit_summary))),
        config=cash_exposure_config,
        as_of=as_of,
    )
    statuses = [str(dpc_payload.get("producer_result_status") or ""), str(dce_payload.get("producer_result_status") or "")]
    merged_status = "BLOCK" if "BLOCK" in statuses else "REVIEW_REQUIRED" if "REVIEW_REQUIRED" in statuses else "PASS"
    target_position_count = dpc_payload.get("target_position_count")
    target_gross_exposure_ratio = dce_payload.get("target_gross_exposure_ratio")
    cash_reserve_ratio = dce_payload.get("target_cash_ratio")
    reason_codes = [
        *(f"internal_dynamic_position_count:{code}" for code in dpc_payload.get("reason_codes", []) or []),
        *(f"internal_dynamic_cash_exposure:{code}" for code in dce_payload.get("reason_codes", []) or []),
    ]
    cap_authority = _resolve_single_name_weight_cap(
        policy_config=policy_config,
        safety_limit_summary=safety_limit_summary,
    )
    if cap_authority["status"] != "PASS":
        merged_status = "BLOCK" if cap_authority["status"] == "BLOCK" or "BLOCK" in statuses else "REVIEW_REQUIRED"
        reason_codes.append(str(cap_authority["reason_code"]))
    return {
        "status": merged_status,
        "reason_codes": sorted(set(reason_codes)),
        "target_position_count_resolution": dpc_payload.get("target_position_count_resolution") or "UNRESOLVED",
        "target_position_count": target_position_count,
        "minimum_position_count": dpc_payload.get("minimum_position_count"),
        "maximum_position_count": dpc_payload.get("maximum_position_count"),
        "resolved_candidate_capacity": dpc_payload.get("resolved_candidate_capacity"),
        "resolved_opportunity_capacity": dpc_payload.get("resolved_opportunity_capacity"),
        "meaningful_allocation_position_count": dpc_payload.get("meaningful_allocation_position_count"),
        "target_gross_exposure_ratio_resolution": dce_payload.get("target_gross_exposure_ratio_resolution") or "UNRESOLVED",
        "target_gross_exposure_ratio": target_gross_exposure_ratio,
        "minimum_gross_exposure_ratio": dce_payload.get("minimum_gross_exposure_ratio"),
        "maximum_gross_exposure_ratio": dce_payload.get("maximum_gross_exposure_ratio"),
        "cash_reserve_ratio_resolution": dce_payload.get("target_cash_ratio_resolution") or "UNRESOLVED",
        "cash_reserve_ratio": cash_reserve_ratio,
        "minimum_cash_ratio": dce_payload.get("minimum_cash_ratio"),
        "maximum_cash_ratio": dce_payload.get("maximum_cash_ratio"),
        "single_name_weight_cap": cap_authority["single_name_weight_cap"],
        "single_name_weight_cap_source": cap_authority["source"],
        "single_name_weight_cap_authority": cap_authority,
        "deployment_posture": _deployment_posture(target_gross_exposure_ratio, cash_reserve_ratio),
        "internal_resolvers": {
            "dynamic_position_count": {
                "merge_decision": "KEEP_INTERNAL",
                "runtime_wiring": "REMOVE_RUNTIME_WIRING",
                "public_artifact_policy": "REMOVE",
                "schema_version": dpc_payload.get("schema_version"),
                "producer_result_status": dpc_payload.get("producer_result_status"),
                "config_reference": dpc_payload.get("config_reference"),
                "config_hash": dpc_payload.get("config_hash"),
            },
            "dynamic_cash_exposure": {
                "merge_decision": "KEEP_INTERNAL",
                "runtime_wiring": "REMOVE_RUNTIME_WIRING",
                "public_artifact_policy": "REMOVE",
                "schema_version": dce_payload.get("schema_version"),
                "producer_result_status": dce_payload.get("producer_result_status"),
                "config_reference": dce_payload.get("config_reference"),
                "config_hash": dce_payload.get("config_hash"),
            },
        },
        "upstream_artifacts": {
            "dynamic_position_count_internal": dpc_payload,
            "dynamic_cash_exposure_internal": dce_payload,
        },
        "source_hashes": [
            *[{"role": f"internal_dynamic_position_count.{item.get('role')}", "path": item.get("path", ""), "sha256": item.get("sha256", "")} for item in dpc_payload.get("source_hashes", []) or []],
            *[{"role": f"internal_dynamic_cash_exposure.{item.get('role')}", "path": item.get("path", ""), "sha256": item.get("sha256", "")} for item in dce_payload.get("source_hashes", []) or []],
            *cap_authority["source_hashes"],
        ],
    }


def _resolve_single_name_weight_cap(
    *,
    policy_config: PortfolioPolicyConfig | None,
    safety_limit_summary: Mapping[str, Any],
) -> dict[str, Any]:
    if policy_config and policy_config.single_name_weight_cap is not None:
        return {
            "status": "PASS",
            "reason_code": "single_name_weight_cap_resolved_from_portfolio_policy_config",
            "single_name_weight_cap": float(policy_config.single_name_weight_cap),
            "source": policy_config.single_name_weight_cap_source or f"{policy_config.config_source}#single_name_weight_cap",
            "source_hashes": [],
            "canonical_owner": "portfolio_policy",
        }
    cap = _cap_from_safety_limit_summary(safety_limit_summary)
    if cap is not None:
        return {
            "status": "PASS",
            "reason_code": "single_name_weight_cap_resolved_from_safety_limit_summary",
            "single_name_weight_cap": cap,
            "source": "portfolio_policy:safety_limit_summary#concentration.maximum_position_weight",
            "source_hashes": [{"role": "single_name_weight_cap.safety_limit_summary", "path": "portfolio_policy:safety_limit_summary", "sha256": stable_payload_hash(dict(safety_limit_summary))}],
            "canonical_owner": "portfolio_policy",
        }
    return {
        "status": "REVIEW_REQUIRED",
        "reason_code": "single_name_weight_cap_authority_missing",
        "single_name_weight_cap": None,
        "source": "",
        "source_hashes": [],
        "canonical_owner": "portfolio_policy",
    }


def _cap_from_safety_limit_summary(summary: Mapping[str, Any]) -> float | None:
    concentration = summary.get("concentration")
    if isinstance(concentration, Mapping):
        value = concentration.get("maximum_position_weight")
        cap = _ratio_or_none(value)
        if cap is not None:
            return cap
    return _ratio_or_none(summary.get("maximum_position_weight"))


def _load_internal_position_count_config() -> dynamic_position_count.DynamicPositionCountConfig | None:
    try:
        return dynamic_position_count.load_dynamic_position_count_config(INTERNAL_POSITION_COUNT_CONFIG_PATH)
    except Exception:
        return None


def _load_internal_cash_exposure_config() -> dynamic_cash_exposure.DynamicCashExposureConfig | None:
    try:
        return dynamic_cash_exposure.load_dynamic_cash_exposure_config(INTERNAL_CASH_EXPOSURE_CONFIG_PATH)
    except Exception:
        return None


def _deployment_posture(target_gross_exposure_ratio: Any, cash_reserve_ratio: Any) -> str:
    if target_gross_exposure_ratio is None or cash_reserve_ratio is None:
        return "UNRESOLVED"
    if float(target_gross_exposure_ratio) <= 0:
        return "PAUSE"
    if float(cash_reserve_ratio) >= 0.35:
        return "DEFENSIVE_DEPLOYMENT"
    if float(target_gross_exposure_ratio) >= 0.75:
        return "DEPLOY"
    return "BALANCED_DEPLOYMENT"


def _dpc_source_from_pp(summary: PortfolioPolicyInputSummary) -> dynamic_position_count.DynamicPositionCountSourceSummary:
    return dynamic_position_count.DynamicPositionCountSourceSummary(
        status=summary.status,
        business_date=summary.business_date,
        feature_date=summary.feature_date,
        source_ref=summary.source_ref,
        source_hash=summary.source_hash,
        summary=dict(summary.summary),
    )


def _dce_source_from_pp(summary: PortfolioPolicyInputSummary) -> dynamic_cash_exposure.CashExposureSourceSummary:
    return dynamic_cash_exposure.CashExposureSourceSummary(
        status=summary.status,
        business_date=summary.business_date,
        feature_date=summary.feature_date,
        source_ref=summary.source_ref,
        source_hash=summary.source_hash,
        summary=dict(summary.summary),
    )


def _dpc_source(*, status: str, business_date: str, summary: Mapping[str, Any], source_ref: str, source_hash: str) -> dynamic_position_count.DynamicPositionCountSourceSummary:
    return dynamic_position_count.DynamicPositionCountSourceSummary(
        status=status,
        business_date=business_date,
        feature_date=str(summary.get("feature_date") or business_date),
        source_ref=source_ref,
        source_hash=source_hash,
        summary=dict(summary),
    )


def _dce_source(*, status: str, business_date: str, summary: Mapping[str, Any], source_ref: str, source_hash: str) -> dynamic_cash_exposure.CashExposureSourceSummary:
    return dynamic_cash_exposure.CashExposureSourceSummary(
        status=status,
        business_date=business_date,
        feature_date=str(summary.get("feature_date") or business_date),
        source_ref=source_ref,
        source_hash=source_hash,
        summary=dict(summary),
    )


def _read_json_if_file(path: Path | str | None) -> dict[str, Any]:
    if path is None:
        return {}
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _path_hash(path: Path | str | None) -> str:
    candidate = Path(path) if path else None
    if candidate and candidate.is_file():
        return sha256_file(candidate)
    return ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _summary_payload(summary: PortfolioPolicyInputSummary, *, business_date: str) -> dict[str, Any]:
    return {
        "status": summary.status,
        "business_date": summary.business_date,
        "feature_date": summary.feature_date,
        "summary": dict(summary.summary),
        "source_ref": summary.source_ref,
        "source_hash": summary.source_hash,
        "business_date_aligned": summary.business_date == business_date,
        "feature_date_lte_business_date": bool(summary.feature_date and summary.feature_date <= business_date),
    }


def _summary_aligned(summary: PortfolioPolicyInputSummary, *, business_date: str) -> bool:
    return summary.business_date == business_date and bool(summary.feature_date) and summary.feature_date <= business_date


def _policy_intent(config: PortfolioPolicyConfig | None) -> dict[str, str]:
    if config is None:
        return {
            "risk_posture": "UNRESOLVED",
            "entry_posture": "UNRESOLVED",
            "position_count_posture": "UNRESOLVED",
            "cash_posture": "UNRESOLVED",
            "exposure_posture": "UNRESOLVED",
            "position_management_bias": "UNRESOLVED",
        }
    return {field: str(config.intent_policy.get(field) or "UNRESOLVED") for field in sorted(_required_intent_fields())}


def _required_intent_fields() -> set[str]:
    return {"risk_posture", "entry_posture", "position_count_posture", "cash_posture", "exposure_posture", "position_management_bias"}


def _invalid_intent_values(intent: Mapping[str, str]) -> dict[str, str]:
    allowed = {
        "risk_posture": RISK_POSTURES,
        "entry_posture": ENTRY_POSTURES,
        "position_count_posture": POSITION_COUNT_POSTURES,
        "cash_posture": CASH_POSTURES,
        "exposure_posture": EXPOSURE_POSTURES,
        "position_management_bias": POSITION_MANAGEMENT_BIASES,
    }
    return {field: value for field, value in intent.items() if field in allowed and value not in allowed[field]}


def _enum_check(errors: list[str], payload: dict[str, Any], field: str, allowed: set[str]) -> None:
    if payload.get(field) not in allowed:
        errors.append(f"invalid_enum:{field}")


def _optional_non_negative_int(errors: list[str], payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"invalid_non_negative_int:{field}")


def _optional_ratio(errors: list[str], payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
        errors.append(f"invalid_ratio:{field}")


def _config_ratio(value: Any, *, field: str) -> float | None:
    if value is None:
        return None
    parsed = _ratio_or_none(value)
    if parsed is None:
        raise PortfolioPolicyConfigError(f"invalid_ratio:{field}")
    return parsed


def _ratio_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not 0 <= parsed <= 1:
        return None
    return parsed


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
