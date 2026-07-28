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
)
from ai_fund_lab_v2.strategy import portfolio_construction
from ai_fund_lab_v2.strategy.status_contract import compatibility_status_from_payload, status_contract_fields


SCHEMA_VERSION = "capital_deployment.v1"
PRODUCER_VERSION = "phase22_f_capital_deployment_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"

PORTFOLIO_CAPITAL_POSTURES = {"DEPLOY", "MAINTAIN", "CONSERVE", "WITHHOLD", "UNRESOLVED"}
CASH_RESERVE_POSTURES = {"AVAILABLE", "PRESERVE", "CONFLICT", "UNRESOLVED"}
EXPOSURE_POSTURES = {"EXPAND", "MAINTAIN", "REDUCE", "CONFLICT", "UNRESOLVED"}
MEMBER_ALLOCATION_POSTURES = {"PRIORITIZE", "NORMAL", "DEPRIORITIZE", "WITHHOLD", "UNRESOLVED"}
CAPITAL_CONSTRAINT_STATUSES = {
    "CAPITAL_SUFFICIENT",
    "CAPITAL_CONSTRAINED",
    "CASH_RESERVE_CONFLICT",
    "EXPOSURE_CONFLICT",
    "ALLOCATION_UNRESOLVED",
    "SOURCE_UNAVAILABLE",
    "PENDING_RESERVATION_CONFLICT",
}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
BLOCKING_UPSTREAM_STATUSES = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING}
REVIEW_UPSTREAM_STATUSES = {SOURCE_REVIEW_REQUIRED, SOURCE_NOT_ELIGIBLE}
FORBIDDEN_CONCRETE_FIELDS = {
    "target_position_count",
    "target_positions",
    "target_cash_ratio",
    "cash_ratio",
    "target_exposure_ratio",
    "target_weight",
    "target_weight_pct",
    "weight_percentage",
    "allocation_jpy",
    "target_notional",
    "delta_notional",
    "share_quantity",
    "quantity",
    "quantity_candidate",
    "broker_quantity",
    "order_quantity",
    "lot_size",
    "lot_rounding_result",
    "minimum_order_amount",
}


class CapitalDeploymentError(RuntimeError):
    pass


class CapitalDeploymentSchemaError(CapitalDeploymentError):
    pass


class CapitalDeploymentConsumerError(CapitalDeploymentError):
    pass


@dataclass(frozen=True)
class CapitalDeploymentSourceSummary:
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
class CapitalDeploymentProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "capital_deployment" / business_date / "capital_deployment.json"


def produce_capital_deployment_artifact(
    *,
    business_date: str,
    portfolio_construction_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    current_cash_summary: CapitalDeploymentSourceSummary,
    current_exposure_summary: CapitalDeploymentSourceSummary,
    current_portfolio_summary: CapitalDeploymentSourceSummary,
    pending_reservation_summary: CapitalDeploymentSourceSummary,
    policy_config_summary: CapitalDeploymentSourceSummary,
    output_path: Path | str,
    as_of: str | None = None,
) -> CapitalDeploymentProducerResult:
    payload, evidence = build_capital_deployment_payload(
        business_date=business_date,
        portfolio_construction_artifact_path=portfolio_construction_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        position_management_artifact_path=position_management_artifact_path,
        current_cash_summary=current_cash_summary,
        current_exposure_summary=current_exposure_summary,
        current_portfolio_summary=current_portfolio_summary,
        pending_reservation_summary=pending_reservation_summary,
        policy_config_summary=policy_config_summary,
        as_of=as_of,
    )
    validate_capital_deployment_artifact(payload)
    artifact_hash = capital_deployment_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return CapitalDeploymentProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_capital_deployment_payload(
    *,
    business_date: str,
    portfolio_construction_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    current_cash_summary: CapitalDeploymentSourceSummary,
    current_exposure_summary: CapitalDeploymentSourceSummary,
    current_portfolio_summary: CapitalDeploymentSourceSummary,
    pending_reservation_summary: CapitalDeploymentSourceSummary,
    policy_config_summary: CapitalDeploymentSourceSummary,
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")
    construction_result = validate_portfolio_construction_compatibility(
        portfolio_construction_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    policy_result = portfolio_construction.validate_portfolio_policy_compatibility(
        portfolio_policy_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    pm_result = portfolio_construction.validate_position_management_compatibility(
        position_management_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )

    source_status = "VALID"
    reason_codes: list[str] = []
    upstream_statuses = [construction_result["status"], policy_result["status"], pm_result["status"]]
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
        "current_cash": current_cash_summary.to_dict(requested_business_date=business_date),
        "current_exposure": current_exposure_summary.to_dict(requested_business_date=business_date),
        "current_portfolio": current_portfolio_summary.to_dict(requested_business_date=business_date),
        "pending_reservation": pending_reservation_summary.to_dict(requested_business_date=business_date),
        "policy_config": policy_config_summary.to_dict(requested_business_date=business_date),
    }
    for name, summary in (
        ("current_cash", current_cash_summary),
        ("current_exposure", current_exposure_summary),
        ("current_portfolio", current_portfolio_summary),
        ("pending_reservation", pending_reservation_summary),
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

    constraint_status = _capital_constraint_status(
        current_cash_summary=current_cash_summary,
        current_exposure_summary=current_exposure_summary,
        pending_reservation_summary=pending_reservation_summary,
    )
    if constraint_status in {"CAPITAL_CONSTRAINED", "CASH_RESERVE_CONFLICT", "EXPOSURE_CONFLICT", "PENDING_RESERVATION_CONFLICT", "ALLOCATION_UNRESOLVED", "SOURCE_UNAVAILABLE"} and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"
        reason_codes.append(f"capital_constraint:{constraint_status}")

    members = _members_from_portfolio_construction(portfolio_construction_artifact_path, capital_constraint_status=constraint_status)
    feature_date = min(
        [
            value
            for value in (
                construction_result.get("feature_date"),
                policy_result.get("feature_date"),
                pm_result.get("feature_date"),
                current_cash_summary.feature_date,
                current_exposure_summary.feature_date,
                current_portfolio_summary.feature_date,
                pending_reservation_summary.feature_date,
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
            current_cash_summary.feature_date,
            current_exposure_summary.feature_date,
            current_portfolio_summary.feature_date,
            pending_reservation_summary.feature_date,
            policy_config_summary.feature_date,
        )
    )
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_cash_exposure_or_pending_date_detected")

    source_artifacts = [
        {"role": "portfolio_construction", "path": str(portfolio_construction_artifact_path or ""), "required": True, "status": construction_result["status"]},
        {"role": "portfolio_policy", "path": str(portfolio_policy_artifact_path or ""), "required": True, "status": policy_result["status"]},
        {"role": "position_management", "path": str(position_management_artifact_path or ""), "required": True, "status": pm_result["status"]},
        {"role": "current_cash", "path": current_cash_summary.source_ref, "required": True, "status": current_cash_summary.status},
        {"role": "current_exposure", "path": current_exposure_summary.source_ref, "required": True, "status": current_exposure_summary.status},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "required": True, "status": current_portfolio_summary.status},
        {"role": "pending_reservation", "path": pending_reservation_summary.source_ref, "required": True, "status": pending_reservation_summary.status},
        {"role": "policy_config", "path": policy_config_summary.source_ref, "required": True, "status": policy_config_summary.status},
    ]
    source_hashes = [
        {"role": "current_cash", "path": current_cash_summary.source_ref, "sha256": _strip_sha256(current_cash_summary.source_hash)},
        {"role": "current_exposure", "path": current_exposure_summary.source_ref, "sha256": _strip_sha256(current_exposure_summary.source_hash)},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "sha256": _strip_sha256(current_portfolio_summary.source_hash)},
        {"role": "pending_reservation", "path": pending_reservation_summary.source_ref, "sha256": _strip_sha256(pending_reservation_summary.source_hash)},
        {"role": "policy_config", "path": policy_config_summary.source_ref, "sha256": _strip_sha256(policy_config_summary.source_hash)},
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
        "portfolio_capital_posture": _portfolio_capital_posture(constraint_status),
        "cash_reserve_posture": _cash_reserve_posture(constraint_status),
        "exposure_posture": _exposure_posture(constraint_status),
        "capital_constraint_status": constraint_status,
        "members": members,
        "member_count": len(members),
        "position_count_policy_reference": str(policy_result.get("artifact_path") or portfolio_policy_artifact_path or ""),
        "cash_policy_reference": str(policy_result.get("artifact_path") or portfolio_policy_artifact_path or ""),
        "exposure_policy_reference": str(policy_result.get("artifact_path") or portfolio_policy_artifact_path or ""),
        "sizing_policy_reference": str(policy_config_summary.source_ref or ""),
        "concrete_values_decided": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False,
        "reason_codes": sorted(set(reason_codes)),
        "upstream_artifacts": {
            "portfolio_construction": construction_result,
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
            "previous_day_capital_deployment_copied": False,
        },
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_capital_deployment_authority_active": True,
    }
    evidence = {
        "schema_version": "phase22_f_capital_deployment_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "capital_constraint_status": constraint_status,
        "portfolio_construction_status": construction_result["status"],
        "portfolio_policy_status": policy_result["status"],
        "position_management_status": pm_result["status"],
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def validate_portfolio_construction_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return _missing_upstream("portfolio_construction", requested_business_date, str(path or ""))
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        portfolio_construction.validate_portfolio_construction_artifact(payload)
    except Exception as exc:
        return {
            **_missing_upstream("portfolio_construction", requested_business_date, str(path)),
            "status": INCOMPATIBLE_SCHEMA,
            "reason_codes": [f"schema_validation_failed:{exc}"],
        }
    expected_hash = str(payload.get("artifact_hash") or "")
    actual_hash = portfolio_construction.portfolio_construction_hash(payload)
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
        "artifact_kind": "portfolio_construction",
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


def validate_capital_deployment_artifact(payload: dict[str, Any]) -> dict[str, Any]:
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
        "portfolio_capital_posture",
        "cash_reserve_posture",
        "exposure_posture",
        "capital_constraint_status",
        "members",
        "position_count_policy_reference",
        "cash_policy_reference",
        "exposure_policy_reference",
        "sizing_policy_reference",
        "concrete_values_decided",
        "allocation_decided",
        "quantity_decided",
        "lot_rounding_decided",
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
    _enum_check(errors, payload, "portfolio_capital_posture", PORTFOLIO_CAPITAL_POSTURES)
    _enum_check(errors, payload, "cash_reserve_posture", CASH_RESERVE_POSTURES)
    _enum_check(errors, payload, "exposure_posture", EXPOSURE_POSTURES)
    _enum_check(errors, payload, "capital_constraint_status", CAPITAL_CONSTRAINT_STATUSES)
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_f_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase22_f_runtime_consumer_eligibility_must_be_not_eligible")
    for field in (
        "concrete_values_decided",
        "position_count_decided",
        "cash_ratio_decided",
        "exposure_decided",
        "position_sizing_decided",
        "allocation_decided",
        "quantity_decided",
        "lot_rounding_decided",
        "production_consumer_connected",
        "runtime_switch_performed",
    ):
        if payload.get(field) is not False:
            errors.append(f"phase22_f_field_must_be_false:{field}")
    if payload.get("legacy_authority_active") is not True:
        errors.append("phase22_f_legacy_authority_must_remain_active")
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
    members = payload.get("members")
    if not isinstance(members, list):
        errors.append("members_not_list")
    else:
        for index, member in enumerate(members):
            errors.extend(_validate_member(member, index=index))
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
        if temporal.get("previous_day_capital_deployment_copied") is not False:
            errors.append("previous_day_capital_deployment_copy_forbidden")
    if errors:
        raise CapitalDeploymentSchemaError(";".join(errors))
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


def load_capital_deployment_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_capital_deployment_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise CapitalDeploymentConsumerError("BLOCK Capital Deployment artifact is not fixture-consumable")
    if for_production:
        raise CapitalDeploymentConsumerError("Phase22-F Capital Deployment artifact is not production-consumable")
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise CapitalDeploymentConsumerError("Phase22-F Capital Deployment must remain NOT_ELIGIBLE")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_artifacts") if isinstance(payload.get("upstream_artifacts"), dict) else {}
    return {
        "schema_version": "phase22_f_produced_not_consumed_validation.v1",
        "capital_deployment_artifact_produced": bool(payload),
        "capital_deployment_schema_valid": True,
        "portfolio_construction_shadow_read": bool((upstream.get("portfolio_construction") or {}).get("shadow_read_allowed")),
        "portfolio_policy_shadow_read": bool((upstream.get("portfolio_policy") or {}).get("shadow_read_allowed")),
        "position_management_shadow_read": bool((upstream.get("position_management") or {}).get("shadow_read_allowed")),
        "capital_deployment_production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_capital_deployment_behavior_changed": False,
        "runtime_planning_changed": False,
        "pending_changed": False,
        "submit_changed": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False,
        "status": "PASS" if payload and payload.get("runtime_consumer_eligibility") == "NOT_ELIGIBLE" else "BLOCK",
    }


def capital_deployment_hash(payload: dict[str, Any]) -> str:
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


def _capital_constraint_status(
    *,
    current_cash_summary: CapitalDeploymentSourceSummary,
    current_exposure_summary: CapitalDeploymentSourceSummary,
    pending_reservation_summary: CapitalDeploymentSourceSummary,
) -> str:
    statuses = {current_cash_summary.status, current_exposure_summary.status, pending_reservation_summary.status}
    if any(status in {"MISSING", "REVIEW_REQUIRED"} for status in statuses):
        return "SOURCE_UNAVAILABLE"
    if str(pending_reservation_summary.summary.get("reservation_status") or "").upper() == "CONFLICT":
        return "PENDING_RESERVATION_CONFLICT"
    if str(current_cash_summary.summary.get("cash_constraint_status") or "").upper() == "CONFLICT":
        return "CASH_RESERVE_CONFLICT"
    if str(current_exposure_summary.summary.get("exposure_constraint_status") or "").upper() == "CONFLICT":
        return "EXPOSURE_CONFLICT"
    if str(current_cash_summary.summary.get("capital_constraint_status") or "").upper() == "CONSTRAINED":
        return "CAPITAL_CONSTRAINED"
    if str(current_exposure_summary.summary.get("capital_constraint_status") or "").upper() == "CONSTRAINED":
        return "CAPITAL_CONSTRAINED"
    return "CAPITAL_SUFFICIENT"


def _portfolio_capital_posture(status: str) -> str:
    return {
        "CAPITAL_SUFFICIENT": "MAINTAIN",
        "CAPITAL_CONSTRAINED": "CONSERVE",
        "CASH_RESERVE_CONFLICT": "CONSERVE",
        "EXPOSURE_CONFLICT": "WITHHOLD",
        "PENDING_RESERVATION_CONFLICT": "WITHHOLD",
        "ALLOCATION_UNRESOLVED": "UNRESOLVED",
        "SOURCE_UNAVAILABLE": "UNRESOLVED",
    }.get(status, "UNRESOLVED")


def _cash_reserve_posture(status: str) -> str:
    return "CONFLICT" if status == "CASH_RESERVE_CONFLICT" else ("PRESERVE" if status in {"CAPITAL_CONSTRAINED", "PENDING_RESERVATION_CONFLICT"} else ("UNRESOLVED" if status == "SOURCE_UNAVAILABLE" else "AVAILABLE"))


def _exposure_posture(status: str) -> str:
    return "CONFLICT" if status == "EXPOSURE_CONFLICT" else ("REDUCE" if status in {"CAPITAL_CONSTRAINED", "PENDING_RESERVATION_CONFLICT"} else ("UNRESOLVED" if status == "SOURCE_UNAVAILABLE" else "MAINTAIN"))


def _members_from_portfolio_construction(path: Path | str | None, *, capital_constraint_status: str) -> list[dict[str, Any]]:
    if path is None or not Path(path).is_file():
        return []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    members = []
    for index, member in enumerate(payload.get("portfolio_members") or [], start=1):
        if not isinstance(member, dict):
            continue
        posture = _allocation_posture(member, capital_constraint_status=capital_constraint_status)
        members.append(
            {
                "security_code": str(member.get("security_code") or ""),
                "membership_reference": str(member.get("member_id") or ""),
                "allocation_posture": posture,
                "allocation_priority": int(member.get("construction_priority") or index),
                "capital_constraint_status": capital_constraint_status,
                "portfolio_construction_reference": str(member.get("member_id") or ""),
                "position_management_reference": str(member.get("position_management_reference") or ""),
                "confidence": _confidence(member),
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "reason_codes": sorted({"construction_weight_intent:" + str(member.get("weight_intent") or ""), "no_concrete_allocation_in_phase22_f"}),
            }
        )
    return members


def _allocation_posture(member: Mapping[str, Any], *, capital_constraint_status: str) -> str:
    if capital_constraint_status in {"PENDING_RESERVATION_CONFLICT", "EXPOSURE_CONFLICT", "SOURCE_UNAVAILABLE"}:
        return "UNRESOLVED" if capital_constraint_status == "SOURCE_UNAVAILABLE" else "WITHHOLD"
    weight_intent = str(member.get("weight_intent") or "").upper()
    membership_intent = str(member.get("membership_intent") or "").upper()
    if membership_intent == "EXCLUDE" or weight_intent in {"REMOVE", "AVOID"}:
        return "WITHHOLD"
    if weight_intent == "INCREASE":
        return "DEPRIORITIZE" if capital_constraint_status == "CAPITAL_CONSTRAINED" else "PRIORITIZE"
    if weight_intent == "DECREASE":
        return "DEPRIORITIZE"
    if weight_intent == "MAINTAIN":
        return "NORMAL"
    return "UNRESOLVED"


def _validate_member(member: Any, *, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(member, dict):
        return [f"member_not_object:{index}"]
    required = {
        "security_code",
        "membership_reference",
        "allocation_posture",
        "allocation_priority",
        "capital_constraint_status",
        "portfolio_construction_reference",
        "position_management_reference",
        "confidence",
        "uncertainty",
        "reason_codes",
    }
    errors.extend(f"member_required_field_missing:{index}:{field}" for field in sorted(required - set(member)))
    if not member.get("security_code"):
        errors.append(f"security_code_empty:{index}")
    if member.get("allocation_posture") not in MEMBER_ALLOCATION_POSTURES:
        errors.append(f"invalid_allocation_posture:{index}")
    if member.get("capital_constraint_status") not in CAPITAL_CONSTRAINT_STATUSES:
        errors.append(f"invalid_member_capital_constraint_status:{index}")
    if not isinstance(member.get("allocation_priority"), int) or member.get("allocation_priority") < 1:
        errors.append(f"invalid_allocation_priority:{index}")
    confidence = member.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        errors.append(f"invalid_confidence:{index}")
    if not isinstance(member.get("reason_codes"), list):
        errors.append(f"reason_codes_not_list:{index}")
    for field in sorted(FORBIDDEN_CONCRETE_FIELDS & set(member)):
        errors.append(f"concrete_field_forbidden:{index}:{field}")
    return errors


def _summary_aligned(summary: CapitalDeploymentSourceSummary, *, business_date: str) -> bool:
    return summary.business_date == business_date and bool(summary.feature_date) and summary.feature_date <= business_date


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


def _confidence(row: Mapping[str, Any]) -> float:
    value = row.get("confidence", 0.0)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(max(numeric, 0.0), 1.0), 8)


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
