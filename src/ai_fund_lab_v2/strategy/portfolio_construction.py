from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

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
from ai_fund_lab_v2.strategy import position_management
from ai_fund_lab_v2.strategy.status_contract import compatibility_status_from_payload, status_contract_fields


SCHEMA_VERSION = "portfolio_construction.v1"
PRODUCER_VERSION = "phase22_e_portfolio_construction_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

MEMBERSHIP_INTENTS = {"RETAIN", "ADD_CANDIDATE", "REDUCE_CANDIDATE", "REMOVE_CANDIDATE", "EXCLUDE", "UNRESOLVED"}
WEIGHT_INTENTS = {"INCREASE", "MAINTAIN", "DECREASE", "REMOVE", "AVOID", "UNRESOLVED"}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
BLOCKING_UPSTREAM_STATUSES = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING}
REVIEW_UPSTREAM_STATUSES = {SOURCE_REVIEW_REQUIRED, SOURCE_NOT_ELIGIBLE}
FORBIDDEN_CONCRETE_FIELDS = {
    "target_weight",
    "target_weight_pct",
    "weight_percentage",
    "target_position_count",
    "target_positions",
    "maximum_positions",
    "cash_ratio",
    "target_cash_ratio",
    "exposure",
    "target_exposure_ratio",
    "position_size",
    "allocation_jpy",
    "target_notional",
    "delta_notional",
    "quantity",
    "quantity_candidate",
    "broker_quantity",
    "order_quantity",
    "lot_rounding_result",
}


class PortfolioConstructionError(RuntimeError):
    pass


class PortfolioConstructionSchemaError(PortfolioConstructionError):
    pass


class PortfolioConstructionConsumerError(PortfolioConstructionError):
    pass


@dataclass(frozen=True)
class PortfolioConstructionSourceSummary:
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
class PortfolioConstructionProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "portfolio_construction" / business_date / "portfolio_construction.json"


def produce_portfolio_construction_artifact(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    candidate_summary: PortfolioConstructionSourceSummary,
    opportunity_summary: PortfolioConstructionSourceSummary,
    current_portfolio_summary: PortfolioConstructionSourceSummary,
    pending_summary: PortfolioConstructionSourceSummary | None,
    policy_config_summary: PortfolioConstructionSourceSummary,
    output_path: Path | str,
    as_of: str | None = None,
) -> PortfolioConstructionProducerResult:
    payload, evidence = build_portfolio_construction_payload(
        business_date=business_date,
        market_context_artifact_path=market_context_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        position_management_artifact_path=position_management_artifact_path,
        candidate_summary=candidate_summary,
        opportunity_summary=opportunity_summary,
        current_portfolio_summary=current_portfolio_summary,
        pending_summary=pending_summary,
        policy_config_summary=policy_config_summary,
        as_of=as_of,
    )
    validate_portfolio_construction_artifact(payload)
    artifact_hash = portfolio_construction_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return PortfolioConstructionProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_portfolio_construction_payload(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    candidate_summary: PortfolioConstructionSourceSummary,
    opportunity_summary: PortfolioConstructionSourceSummary,
    current_portfolio_summary: PortfolioConstructionSourceSummary,
    pending_summary: PortfolioConstructionSourceSummary | None,
    policy_config_summary: PortfolioConstructionSourceSummary,
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    market_result = validate_market_context_compatibility(
        market_context_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    ).to_dict()
    corporate_result = validate_corporate_event_compatibility(
        corporate_event_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    ).to_dict()
    policy_result = validate_portfolio_policy_compatibility(
        portfolio_policy_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    pm_result = validate_position_management_compatibility(
        position_management_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )

    source_status = "VALID"
    reason_codes: list[str] = []
    upstream_statuses = [market_result["status"], corporate_result["status"], policy_result["status"], pm_result["status"]]
    if any(status in BLOCKING_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "BLOCK"
        reason_codes.extend([f"upstream_block:{status}" for status in upstream_statuses if status in BLOCKING_UPSTREAM_STATUSES])
        source_status = "HASH_MISMATCH" if INCOMPATIBLE_HASH in upstream_statuses else ("MISSING" if SOURCE_MISSING in upstream_statuses else "AUTHORITY_CONFLICT")
    elif any(status in REVIEW_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "REVIEW_REQUIRED"
        reason_codes.extend([f"upstream_review_required:{status}" for status in upstream_statuses if status in REVIEW_UPSTREAM_STATUSES])
    else:
        producer_status = "PASS"

    summaries = {
        "candidate": candidate_summary.to_dict(requested_business_date=business_date),
        "opportunity": opportunity_summary.to_dict(requested_business_date=business_date),
        "current_portfolio": current_portfolio_summary.to_dict(requested_business_date=business_date),
        "pending": (pending_summary or _empty_summary("pending", business_date)).to_dict(requested_business_date=business_date),
        "policy_config": policy_config_summary.to_dict(requested_business_date=business_date),
    }
    for name, summary in (
        ("candidate", candidate_summary),
        ("opportunity", opportunity_summary),
        ("current_portfolio", current_portfolio_summary),
        ("pending", pending_summary or _empty_summary("pending", business_date)),
        ("policy_config", policy_config_summary),
    ):
        if not _summary_aligned(summary, business_date=business_date):
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_date_mismatch")
        if summary.status == "BLOCK":
            producer_status = "BLOCK"
            reason_codes.append(f"{name}_block")
        elif summary.status != "PASS" and producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
            reason_codes.append(f"{name}_review_required")

    members, reconciliation_reasons = _reconcile_members(
        business_date=business_date,
        candidate_rows=candidate_summary.rows,
        opportunity_rows=opportunity_summary.rows,
        current_rows=current_portfolio_summary.rows,
        pm_rows=_pm_rows(position_management_artifact_path),
    )
    reason_codes.extend(reconciliation_reasons)
    duplicate_conflicts = [reason for reason in reconciliation_reasons if reason.startswith("duplicate_security_unresolved")]
    if duplicate_conflicts:
        producer_status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
    missing_current = [reason for reason in reconciliation_reasons if reason.startswith("missing_current_position_reference")]
    if missing_current and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"
    conflicting = [reason for reason in reconciliation_reasons if reason.startswith("conflicting_membership_intent")]
    if conflicting and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"

    feature_date = min(
        [
            value
            for value in (
                market_result.get("feature_date"),
                corporate_result.get("feature_date"),
                policy_result.get("feature_date"),
                pm_result.get("feature_date"),
                candidate_summary.feature_date,
                opportunity_summary.feature_date,
                current_portfolio_summary.feature_date,
                (pending_summary.feature_date if pending_summary else business_date),
                policy_config_summary.feature_date,
            )
            if value
        ]
        or [business_date]
    )
    future_leakage_used = any(
        value and value > business_date
        for value in (
            feature_date,
            candidate_summary.feature_date,
            opportunity_summary.feature_date,
            current_portfolio_summary.feature_date,
            (pending_summary.feature_date if pending_summary else ""),
            policy_config_summary.feature_date,
        )
    )
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_feature_or_snapshot_date_detected")

    source_artifacts = [
        {"role": "market_context", "path": str(market_context_artifact_path or ""), "required": True, "status": market_result["status"]},
        {"role": "corporate_event", "path": str(corporate_event_artifact_path or ""), "required": True, "status": corporate_result["status"]},
        {"role": "portfolio_policy", "path": str(portfolio_policy_artifact_path or ""), "required": True, "status": policy_result["status"]},
        {"role": "position_management", "path": str(position_management_artifact_path or ""), "required": True, "status": pm_result["status"]},
        {"role": "candidate", "path": candidate_summary.source_ref, "required": True, "status": candidate_summary.status},
        {"role": "opportunity", "path": opportunity_summary.source_ref, "required": True, "status": opportunity_summary.status},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "required": True, "status": current_portfolio_summary.status},
        {"role": "pending", "path": (pending_summary.source_ref if pending_summary else ""), "required": False, "status": (pending_summary.status if pending_summary else "PASS")},
        {"role": "policy_config", "path": policy_config_summary.source_ref, "required": True, "status": policy_config_summary.status},
    ]
    source_hashes = [
        {"role": "candidate", "path": candidate_summary.source_ref, "sha256": _strip_sha256(candidate_summary.source_hash)},
        {"role": "opportunity", "path": opportunity_summary.source_ref, "sha256": _strip_sha256(opportunity_summary.source_hash)},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "sha256": _strip_sha256(current_portfolio_summary.source_hash)},
        {"role": "policy_config", "path": policy_config_summary.source_ref, "sha256": _strip_sha256(policy_config_summary.source_hash)},
        *(
            [{"role": "pending", "path": pending_summary.source_ref, "sha256": _strip_sha256(pending_summary.source_hash)}]
            if pending_summary and pending_summary.source_hash
            else []
        ),
    ]
    if not all(item["sha256"] for item in source_hashes):
        if producer_status != "BLOCK":
            producer_status = "REVIEW_REQUIRED"
        reason_codes.append("source_lineage_hash_required")

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
        "portfolio_members": members,
        "member_count": len(members),
        "membership_intent_taxonomy": sorted(MEMBERSHIP_INTENTS),
        "weight_intent_taxonomy": sorted(WEIGHT_INTENTS),
        "position_count_policy_reference": str((policy_result.get("artifact_path") or portfolio_policy_artifact_path or "")),
        "cash_policy_reference": str((policy_result.get("artifact_path") or portfolio_policy_artifact_path or "")),
        "exposure_policy_reference": str((policy_result.get("artifact_path") or portfolio_policy_artifact_path or "")),
        "concrete_values_decided": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "reason_codes": sorted(set(reason_codes)),
        "upstream_artifacts": {
            "market_context": market_result,
            "corporate_event": corporate_result,
            "portfolio_policy": policy_result,
            "position_management": pm_result,
            **summaries,
        },
        "source_artifacts": source_artifacts,
        "source_hashes": source_hashes,
        "temporal_safety": {
            "point_in_time": not future_leakage_used,
            "future_leakage_used": future_leakage_used,
            "feature_date_lte_business_date": feature_date <= business_date,
            "implicit_latest_fallback_used": False,
            "previous_day_portfolio_construction_copied": False,
        },
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    evidence = {
        "schema_version": "phase22_e_portfolio_construction_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "portfolio_member_count": len(members),
        "market_context_status": market_result["status"],
        "corporate_event_status": corporate_result["status"],
        "portfolio_policy_status": policy_result["status"],
        "position_management_status": pm_result["status"],
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def validate_portfolio_policy_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> dict[str, Any]:
    return position_management.validate_portfolio_policy_compatibility(
        path,
        requested_business_date=requested_business_date,
        production_use_requested=production_use_requested,
    )


def validate_position_management_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return _missing_upstream("position_management", requested_business_date, str(path or ""))
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        position_management.validate_position_management_artifact(payload)
    except Exception as exc:
        return {
            **_missing_upstream("position_management", requested_business_date, str(path)),
            "status": INCOMPATIBLE_SCHEMA,
            "reason_codes": [f"schema_validation_failed:{exc}"],
        }
    expected_hash = str(payload.get("artifact_hash") or "")
    actual_hash = position_management.position_management_hash(payload)
    business_date = str(payload.get("business_date") or "")
    feature_date = str(payload.get("feature_date") or "")
    date_ok = business_date == requested_business_date and bool(feature_date) and feature_date <= business_date
    status = "COMPATIBLE_NOT_CONNECTED"
    if not date_ok:
        status = INCOMPATIBLE_DATE
    elif not expected_hash or expected_hash != actual_hash:
        status = INCOMPATIBLE_HASH
    else:
        status = compatibility_status_from_payload(
            payload,
            compatible_status="COMPATIBLE_NOT_CONNECTED",
            source_review_required=SOURCE_REVIEW_REQUIRED,
            source_blocked=SOURCE_BLOCKED,
        )
    reasons = list(payload.get("reason_codes") or [])
    if production_use_requested:
        reasons.append("production_use_rejected")
    return {
        "artifact_kind": "position_management",
        "artifact_path": str(path),
        "schema_version": str(payload.get("schema_version") or ""),
        "status": status,
        "schema_compatible": True,
        "shadow_read_allowed": status in {"COMPATIBLE_NOT_CONNECTED", SOURCE_NOT_ELIGIBLE, SOURCE_REVIEW_REQUIRED},
        "production_decision_allowed": False,
        "business_date": business_date,
        "feature_date": feature_date,
        "business_date_aligned": date_ok,
        "feature_date_point_in_time": date_ok and (payload.get("temporal_safety") or {}).get("future_leakage_used") is not True,
        "artifact_hash_valid": bool(expected_hash) and expected_hash == actual_hash,
        "lifecycle_status": str(payload.get("artifact_lifecycle_status") or ""),
        "producer_result_status": str(payload.get("producer_result_status") or ""),
        "runtime_consumer_eligibility": str(payload.get("runtime_consumer_eligibility") or ""),
        "reason_codes": sorted(set(reasons)),
    }


def validate_portfolio_construction_artifact(payload: dict[str, Any]) -> dict[str, Any]:
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
        "portfolio_members",
        "membership_intent_taxonomy",
        "weight_intent_taxonomy",
        "position_count_policy_reference",
        "cash_policy_reference",
        "exposure_policy_reference",
        "concrete_values_decided",
        "position_count_decided",
        "cash_ratio_decided",
        "exposure_decided",
        "position_sizing_decided",
        "allocation_decided",
        "quantity_decided",
        "reason_codes",
        "upstream_artifacts",
        "source_artifacts",
        "source_hashes",
        "temporal_safety",
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
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_e_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_e_runtime_consumer_eligibility_must_be_not_eligible")
    for field in (
        "concrete_values_decided",
        "position_count_decided",
        "cash_ratio_decided",
        "exposure_decided",
        "position_sizing_decided",
        "allocation_decided",
        "quantity_decided",
        "production_consumer_connected",
        "runtime_switch_performed",
    ):
        if payload.get(field) is not False:
            errors.append(f"phase22_e_field_must_be_false:{field}")
    if payload.get("legacy_authority_active") is not True:
        errors.append("phase22_e_legacy_authority_must_remain_active")
    if sorted(payload.get("membership_intent_taxonomy") or []) != sorted(MEMBERSHIP_INTENTS):
        errors.append("membership_intent_taxonomy_mismatch")
    if sorted(payload.get("weight_intent_taxonomy") or []) != sorted(WEIGHT_INTENTS):
        errors.append("weight_intent_taxonomy_mismatch")
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
    members = payload.get("portfolio_members")
    if not isinstance(members, list):
        errors.append("portfolio_members_not_list")
    else:
        seen: set[str] = set()
        for index, member in enumerate(members):
            errors.extend(_validate_member(member, index=index))
            if isinstance(member, dict):
                code = str(member.get("security_code") or "")
                if code in seen:
                    errors.append(f"duplicate_security_code:{code}")
                seen.add(code)
    for field in sorted(FORBIDDEN_CONCRETE_FIELDS & set(payload)):
        errors.append(f"concrete_field_forbidden:{field}")
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
        if temporal.get("previous_day_portfolio_construction_copied") is not False:
            errors.append("previous_day_portfolio_construction_copy_forbidden")
    if errors:
        raise PortfolioConstructionSchemaError(";".join(errors))
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


def load_portfolio_construction_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_portfolio_construction_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise PortfolioConstructionConsumerError("BLOCK Portfolio Construction artifact is not fixture-consumable")
    if for_production:
        raise PortfolioConstructionConsumerError("Phase22-E Portfolio Construction artifact is not production-consumable")
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise PortfolioConstructionConsumerError("Phase22-E Portfolio Construction must remain NOT_ELIGIBLE")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_artifacts") if isinstance(payload.get("upstream_artifacts"), dict) else {}
    return {
        "schema_version": "phase22_e_produced_not_consumed_validation.v1",
        "portfolio_construction_artifact_produced": bool(payload),
        "portfolio_construction_schema_valid": True,
        "candidate_shadow_read": bool(upstream.get("candidate")),
        "opportunity_shadow_read": bool(upstream.get("opportunity")),
        "portfolio_policy_shadow_read": bool((upstream.get("portfolio_policy") or {}).get("shadow_read_allowed")),
        "position_management_shadow_read": bool((upstream.get("position_management") or {}).get("shadow_read_allowed")),
        "portfolio_construction_production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "candidate_behavior_changed": False,
        "opportunity_behavior_changed": False,
        "pm_behavior_changed": False,
        "capital_deployment_changed": False,
        "runtime_planning_changed": False,
        "pending_changed": False,
        "submit_changed": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "quantity_decided": False,
        "status": "PASS" if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE" else "BLOCK",
    }


def portfolio_construction_hash(payload: dict[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    return stable_payload_hash(clean)


def stable_payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _reconcile_members(
    *,
    business_date: str,
    candidate_rows: Iterable[Mapping[str, Any]],
    opportunity_rows: Iterable[Mapping[str, Any]],
    current_rows: Iterable[Mapping[str, Any]],
    pm_rows: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    reasons: list[str] = []
    candidate_by_code = {_code(row): dict(row) for row in candidate_rows if _code(row)}
    opportunity_by_code = {_code(row): dict(row) for row in opportunity_rows if _code(row)}
    current_by_code: dict[str, dict[str, Any]] = {}
    for row in current_rows:
        code = _code(row)
        if not code:
            continue
        if code in current_by_code:
            reasons.append(f"duplicate_security_unresolved:{code}")
        current_by_code[code] = dict(row)
    pm_by_code: dict[str, dict[str, Any]] = {}
    for row in pm_rows:
        code = _code(row)
        if not code:
            continue
        if code not in current_by_code:
            reasons.append(f"missing_current_position_reference:{code}")
        pm_by_code[code] = dict(row)

    members: list[dict[str, Any]] = []
    used_codes: set[str] = set()
    priority = 1
    for code in sorted(current_by_code):
        pm = pm_by_code.get(code, {})
        candidate = candidate_by_code.get(code)
        opportunity = opportunity_by_code.get(code)
        action = str(pm.get("action") or "UNRESOLVED").upper()
        membership_intent, weight_intent = _membership_from_pm_action(action)
        if candidate or opportunity:
            reasons.append(f"duplicate_existing_candidate_reconciled:{code}")
        members.append(
            _member(
                business_date=business_date,
                security_code=code,
                current_position=True,
                membership_intent=membership_intent,
                weight_intent=weight_intent,
                construction_priority=priority,
                candidate=candidate,
                opportunity=opportunity,
                pm=pm,
                reason_codes=[f"pm_action:{action}", *([f"candidate_duplicate_reconciled:{code}"] if candidate or opportunity else [])],
            )
        )
        used_codes.add(code)
        priority += 1

    opportunity_order = sorted(
        [dict(row) for row in opportunity_rows if _code(row) and _code(row) not in used_codes],
        key=lambda row: (_rank(row), _candidate_order(candidate_by_code.get(_code(row), {})), _code(row)),
    )
    for row in opportunity_order:
        code = _code(row)
        candidate = candidate_by_code.get(code)
        eligible = _candidate_eligible(candidate or row)
        membership_intent = "ADD_CANDIDATE" if eligible else "EXCLUDE"
        weight_intent = "INCREASE" if eligible else "AVOID"
        members.append(
            _member(
                business_date=business_date,
                security_code=code,
                current_position=False,
                membership_intent=membership_intent,
                weight_intent=weight_intent,
                construction_priority=priority,
                candidate=candidate,
                opportunity=row,
                pm=None,
                reason_codes=["opportunity_rank_preserved", "candidate_eligible" if eligible else "candidate_ineligible"],
            )
        )
        used_codes.add(code)
        priority += 1

    candidate_order = sorted(
        [dict(row) for row in candidate_rows if _code(row) and _code(row) not in used_codes],
        key=lambda row: (_candidate_order(row), _code(row)),
    )
    for row in candidate_order:
        code = _code(row)
        eligible = _candidate_eligible(row)
        members.append(
            _member(
                business_date=business_date,
                security_code=code,
                current_position=False,
                membership_intent="UNRESOLVED" if eligible else "EXCLUDE",
                weight_intent="UNRESOLVED" if eligible else "AVOID",
                construction_priority=priority,
                candidate=row,
                opportunity=None,
                pm=None,
                reason_codes=["candidate_without_opportunity_rank" if eligible else "candidate_ineligible"],
            )
        )
        priority += 1
    return members, reasons


def _member(
    *,
    business_date: str,
    security_code: str,
    current_position: bool,
    membership_intent: str,
    weight_intent: str,
    construction_priority: int,
    candidate: Mapping[str, Any] | None,
    opportunity: Mapping[str, Any] | None,
    pm: Mapping[str, Any] | None,
    reason_codes: list[str],
) -> dict[str, Any]:
    return {
        "member_id": f"phase22-e-{business_date}-{security_code}",
        "security_code": security_code,
        "current_position": current_position,
        "membership_intent": membership_intent,
        "construction_priority": construction_priority,
        "weight_intent": weight_intent,
        "candidate_reference": str((candidate or {}).get("candidate_id") or (candidate or {}).get("source_ref") or ""),
        "opportunity_reference": str((opportunity or {}).get("opportunity_id") or (opportunity or {}).get("source_ref") or ""),
        "position_management_reference": str((pm or {}).get("position_id") or (pm or {}).get("source_pm_decision_ref") or ""),
        "portfolio_policy_reference": "",
        "input_candidate_order": _candidate_order(candidate or {}),
        "input_opportunity_rank": _rank(opportunity or {}),
        "input_score": _score(opportunity or candidate or {}),
        "pm_action": str((pm or {}).get("action") or ""),
        "pm_intensity": str((pm or {}).get("intensity") or ""),
        "confidence": _confidence(opportunity or candidate or pm or {}),
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": sorted(set(reason_codes)),
    }


def _validate_member(member: Any, *, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(member, dict):
        return [f"portfolio_member_not_object:{index}"]
    required = {
        "member_id",
        "security_code",
        "current_position",
        "membership_intent",
        "construction_priority",
        "weight_intent",
        "candidate_reference",
        "opportunity_reference",
        "position_management_reference",
        "portfolio_policy_reference",
        "confidence",
        "uncertainty",
        "reason_codes",
    }
    errors.extend(f"portfolio_member_required_field_missing:{index}:{field}" for field in sorted(required - set(member)))
    if not member.get("security_code"):
        errors.append(f"security_code_empty:{index}")
    if member.get("membership_intent") not in MEMBERSHIP_INTENTS:
        errors.append(f"invalid_membership_intent:{index}")
    if member.get("weight_intent") not in WEIGHT_INTENTS:
        errors.append(f"invalid_weight_intent:{index}")
    if not isinstance(member.get("construction_priority"), int) or member.get("construction_priority") < 1:
        errors.append(f"invalid_construction_priority:{index}")
    confidence = member.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        errors.append(f"invalid_confidence:{index}")
    if not isinstance(member.get("reason_codes"), list):
        errors.append(f"reason_codes_not_list:{index}")
    for field in sorted(FORBIDDEN_CONCRETE_FIELDS & set(member)):
        errors.append(f"concrete_field_forbidden:{index}:{field}")
    return errors


def _pm_rows(path: Path | str | None) -> list[dict[str, Any]]:
    if path is None or not Path(path).is_file():
        return []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    positions = payload.get("positions")
    return [dict(row) for row in positions] if isinstance(positions, list) else []


def _membership_from_pm_action(action: str) -> tuple[str, str]:
    if action == "HOLD":
        return "RETAIN", "MAINTAIN"
    if action == "ADD":
        return "RETAIN", "INCREASE"
    if action == "REDUCE":
        return "REDUCE_CANDIDATE", "DECREASE"
    if action == "EXIT":
        return "REMOVE_CANDIDATE", "REMOVE"
    return "UNRESOLVED", "UNRESOLVED"


def _summary_aligned(summary: PortfolioConstructionSourceSummary, *, business_date: str) -> bool:
    return summary.business_date == business_date and bool(summary.feature_date) and summary.feature_date <= business_date


def _empty_summary(role: str, business_date: str) -> PortfolioConstructionSourceSummary:
    return PortfolioConstructionSourceSummary(
        status="PASS",
        business_date=business_date,
        feature_date=business_date,
        source_ref="",
        source_hash=stable_payload_hash({"role": role, "business_date": business_date, "empty": True}),
        rows=(),
        summary={"empty": True},
    )


def _missing_upstream(kind: str, requested_business_date: str, path: str) -> dict[str, Any]:
    return {
        "artifact_kind": kind,
        "artifact_path": path,
        "schema_version": "",
        "status": SOURCE_MISSING,
        "schema_compatible": False,
        "shadow_read_allowed": False,
        "production_decision_allowed": False,
        "business_date": requested_business_date,
        "feature_date": "",
        "business_date_aligned": False,
        "feature_date_point_in_time": False,
        "artifact_hash_valid": False,
        "reason_codes": ["artifact_missing"],
    }


def _code(row: Mapping[str, Any] | None) -> str:
    row = row or {}
    return str(row.get("security_code") or row.get("code") or row.get("symbol") or "").strip()


def _rank(row: Mapping[str, Any]) -> int:
    value = row.get("rank", row.get("opportunity_rank", 999999))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 999999


def _candidate_order(row: Mapping[str, Any]) -> int:
    value = row.get("candidate_order", row.get("order", row.get("rank", 999999)))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 999999


def _score(row: Mapping[str, Any]) -> float:
    value = row.get("expected_edge_score", row.get("score", row.get("candidate_score", 0.0)))
    try:
        return round(float(value), 8)
    except (TypeError, ValueError):
        return 0.0


def _candidate_eligible(row: Mapping[str, Any] | None) -> bool:
    row = row or {}
    if "universe_eligible" in row:
        return bool(row.get("universe_eligible"))
    if "eligible" in row:
        return bool(row.get("eligible"))
    return True


def _confidence(row: Mapping[str, Any]) -> float:
    value = row.get("confidence", row.get("expected_edge_score", row.get("score", 0.0)))
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric < 0:
        return 0.0
    if numeric > 1:
        return 1.0
    return round(numeric, 8)


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
