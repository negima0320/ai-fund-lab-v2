from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.broker.issue_code_normalizer import classify_broker_security
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import opportunity_no_buy_reason_blocks_buy
from ai_fund_lab_v2.strategy.add_investment_evidence import resolve_add_investment_evidence
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
from ai_fund_lab_v2.strategy.reduce_intensity_authority import resolve_reduce_intensity_authority
from ai_fund_lab_v2.strategy.status_contract import compatibility_status_from_payload, status_contract_fields
from ai_fund_lab_v2.strategy.target_weight_precision import (
    TARGET_WEIGHT_ABSOLUTE_TOLERANCE,
    TARGET_WEIGHT_DECIMALS,
    target_weight_sum_tolerance,
)


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
BROKER_ELIGIBILITY_GATING_OWNER = "PORTFOLIO_CONSTRUCTION"
BROKER_ELIGIBILITY_AUTHORITY_TYPE = "BROKER_PRODUCT_CLASSIFICATION_EXECUTION_ELIGIBILITY"
LOT_AWARE_REALLOCATION_AUTHORITY_TYPE = "PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION"
BLOCKING_UPSTREAM_STATUSES = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING}
REVIEW_UPSTREAM_STATUSES = {SOURCE_REVIEW_REQUIRED, SOURCE_NOT_ELIGIBLE}
FORBIDDEN_CONCRETE_FIELDS = {
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
    buy_quality_summary: PortfolioConstructionSourceSummary | None = None,
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
        buy_quality_summary=buy_quality_summary,
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
    buy_quality_summary: PortfolioConstructionSourceSummary | None = None,
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
        "buy_quality": (buy_quality_summary or _empty_summary("buy_quality", business_date)).to_dict(requested_business_date=business_date),
    }
    for name, summary in (
        ("candidate", candidate_summary),
        ("opportunity", opportunity_summary),
        ("current_portfolio", current_portfolio_summary),
        ("pending", pending_summary or _empty_summary("pending", business_date)),
        ("policy_config", policy_config_summary),
        ("buy_quality", buy_quality_summary or _empty_summary("buy_quality", business_date)),
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
    members = _attach_buy_quality(members, buy_quality_summary)
    members, broker_eligibility_reasons = _apply_broker_eligibility_to_new_exposure(members)
    reason_codes.extend(reconciliation_reasons)
    reason_codes.extend(broker_eligibility_reasons)
    weight_contract = _resolve_target_weight_contract(
        business_date=business_date,
        members=members,
        policy_config_summary=policy_config_summary,
        portfolio_policy_reference=str(policy_result.get("artifact_path") or portfolio_policy_artifact_path or ""),
        source_hashes=[
            {"role": "candidate", "path": candidate_summary.source_ref, "sha256": _strip_sha256(candidate_summary.source_hash)},
            {"role": "opportunity", "path": opportunity_summary.source_ref, "sha256": _strip_sha256(opportunity_summary.source_hash)},
            {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "sha256": _strip_sha256(current_portfolio_summary.source_hash)},
            {"role": "policy_config", "path": policy_config_summary.source_ref, "sha256": _strip_sha256(policy_config_summary.source_hash)},
        ],
    )
    members = weight_contract["members"]
    reason_codes.extend(weight_contract["reason_codes"])
    if weight_contract["status"] == "BLOCK":
        producer_status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
    elif weight_contract["status"] == "REVIEW_REQUIRED" and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"
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
                (buy_quality_summary.feature_date if buy_quality_summary else business_date),
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
            (buy_quality_summary.feature_date if buy_quality_summary else ""),
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
        {"role": "buy_quality", "path": (buy_quality_summary.source_ref if buy_quality_summary else ""), "required": False, "status": (buy_quality_summary.status if buy_quality_summary else "PASS")},
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
        *(
            [{"role": "buy_quality", "path": buy_quality_summary.source_ref, "sha256": _strip_sha256(buy_quality_summary.source_hash)}]
            if buy_quality_summary and buy_quality_summary.source_hash
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
        "target_weight_method": weight_contract["method"],
        "portfolio_policy_allocation_authority": weight_contract["portfolio_policy_allocation_authority"],
        "broker_eligibility_gating_owner": BROKER_ELIGIBILITY_GATING_OWNER,
        "broker_eligibility_authority_type": BROKER_ELIGIBILITY_AUTHORITY_TYPE,
        "target_gross_exposure": weight_contract["target_gross_exposure"],
        "resolved_target_member_count": weight_contract["resolved_target_member_count"],
        "single_name_weight_cap": weight_contract["single_name_weight_cap"],
        "incremental_budget_reconciliation": weight_contract["incremental_budget_reconciliation"],
        "baseline_existing_required_weight": weight_contract["incremental_budget_reconciliation"][
            "baseline_existing_required_weight"
        ],
        "available_incremental_budget": weight_contract["incremental_budget_reconciliation"][
            "available_incremental_budget"
        ],
        "total_target_weight": weight_contract["total_target_weight"],
        "target_weight_sum_tolerance": weight_contract["target_weight_sum_tolerance"],
        "membership_intent_taxonomy": sorted(MEMBERSHIP_INTENTS),
        "weight_intent_taxonomy": sorted(WEIGHT_INTENTS),
        "position_count_policy_reference": str((policy_result.get("artifact_path") or portfolio_policy_artifact_path or "")),
        "cash_policy_reference": str((policy_result.get("artifact_path") or portfolio_policy_artifact_path or "")),
        "exposure_policy_reference": str((policy_result.get("artifact_path") or portfolio_policy_artifact_path or "")),
        "concrete_values_decided": weight_contract["status"] == "PASS",
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": weight_contract["target_gross_exposure"] is not None,
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
        "position_count_decided",
        "cash_ratio_decided",
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
                current=current_by_code.get(code),
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
        no_buy_reason = str(row.get("no_buy_reason") or "").strip()
        no_buy_blocked = opportunity_no_buy_reason_blocks_buy(no_buy_reason)
        eligible = _candidate_eligible(candidate or row) and not no_buy_blocked
        membership_intent = "ADD_CANDIDATE" if eligible else "EXCLUDE"
        weight_intent = "INCREASE" if eligible else "AVOID"
        eligibility_reason = (
            f"opportunity_no_buy_reason_present:{no_buy_reason}"
            if no_buy_blocked
            else "candidate_eligible"
            if eligible
            else "candidate_ineligible"
        )
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
                current=None,
                reason_codes=["opportunity_rank_preserved", eligibility_reason],
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
                current=None,
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
    current: Mapping[str, Any] | None,
    reason_codes: list[str],
) -> dict[str, Any]:
    broker_listed_info = _broker_listed_info_payload(security_code, opportunity, candidate, current, pm)
    return {
        "member_id": f"phase22-e-{business_date}-{security_code}",
        "security_code": security_code,
        "symbol": security_code,
        "current_position": current_position,
        "membership_intent": membership_intent,
        "target_membership": membership_intent in {"RETAIN", "ADD_CANDIDATE"},
        "target_weight": 0.0,
        "target_weight_authority": {},
        "target_weight_resolution": {
            "status": "REVIEW_REQUIRED",
            "reason": "target_weight_authority_not_resolved",
            "resolved_weight": 0.0,
            "base_weight": 0.0,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "unresolved_authority",
            "review_reason": "target_weight_authority_not_resolved",
        },
        "construction_priority": construction_priority,
        "weight_intent": weight_intent,
        "candidate_reference": str((candidate or {}).get("candidate_id") or (candidate or {}).get("source_ref") or ""),
        "opportunity_reference": str((opportunity or {}).get("opportunity_id") or (opportunity or {}).get("source_ref") or ""),
        "position_management_reference": str((pm or {}).get("position_id") or (pm or {}).get("source_pm_decision_ref") or ""),
        "source_pm_decision_ref": str((pm or {}).get("source_pm_decision_ref") or (pm or {}).get("position_id") or ""),
        "source_pm_reason_codes": list((pm or {}).get("reason_codes") or (pm or {}).get("decision_reason_codes") or []),
        "current_position_reference": str((current or {}).get("position_id") or (current or {}).get("current_position_reference") or ""),
        "current_position_campaign_id": str((current or {}).get("position_campaign_id") or (current or {}).get("campaign_id") or ""),
        "pm_position_campaign_id": str((pm or {}).get("position_campaign_id") or (pm or {}).get("campaign_id") or (pm or {}).get("lifecycle_reference") or ""),
        "opportunity_position_campaign_id": str((opportunity or {}).get("position_campaign_id") or (opportunity or {}).get("campaign_id") or ""),
        "portfolio_policy_reference": "",
        "input_candidate_order": _candidate_order(candidate or {}),
        "input_opportunity_rank": _canonical_opportunity_rank(opportunity or {}),
        **_opportunity_rank_authority_payload(opportunity or {}),
        "input_score": _score(opportunity or candidate or {}),
        **_score_authority_payload(business_date=business_date, candidate=candidate, opportunity=opportunity),
        **_add_allocation_evidence_payload(opportunity=opportunity, pm=pm, current=current),
        "pm_action": str((pm or {}).get("action") or ""),
        "pm_intensity": str((pm or {}).get("intensity") or ""),
        "reduce_intensity": str((pm or {}).get("reduce_intensity") or (pm or {}).get("intensity") or ""),
        "membership_reason": ";".join(sorted(set(reason_codes))),
        "weight_reason": "target_weight_authority_not_resolved",
        "confidence": _confidence(opportunity or candidate or pm or {}),
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": sorted(set(reason_codes)),
        **({"broker_listed_info": broker_listed_info} if broker_listed_info is not None else {}),
        **_current_position_weight_payload(current_row=current if current_position else None),
    }


def _apply_broker_eligibility_to_new_exposure(members: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    updated: list[dict[str, Any]] = []
    payload_reasons: list[str] = []
    for member in members:
        classified = _broker_eligibility_payload(member)
        if classified is None:
            updated.append(member)
            continue
        reasons = list(member.get("reason_codes") or [])
        patched = {
            **member,
            "broker_eligibility": classified,
            "broker_eligibility_status": classified["status"],
            "broker_eligibility_reason": classified["reason"],
            "broker_eligibility_gating_owner": BROKER_ELIGIBILITY_GATING_OWNER,
        }
        reason = str(classified["reason"])
        if classified["status"] == "PASS":
            reasons.append(reason)
            patched["reason_codes"] = sorted(set(reasons))
            patched["membership_reason"] = ";".join(sorted(set(reasons)))
            updated.append(patched)
            continue
        if not patched.get("current_position") and patched.get("membership_intent") == "ADD_CANDIDATE":
            reasons.extend([reason, "broker_eligibility_buy_new_excluded"])
            payload_reasons.append(f"broker_eligibility_buy_new_excluded:{patched.get('security_code')}:{reason}")
            patched.update(
                {
                    "membership_intent": "EXCLUDE",
                    "target_membership": False,
                    "weight_intent": "AVOID",
                    "membership_reason": ";".join(sorted(set(reasons))),
                    "reason_codes": sorted(set(reasons)),
                }
            )
        elif patched.get("current_position") and str(patched.get("pm_action") or "").upper() == "ADD":
            reasons.extend([reason, "broker_eligibility_buy_add_excluded_existing_position_visible"])
            payload_reasons.append(f"broker_eligibility_buy_add_excluded:{patched.get('security_code')}:{reason}")
            patched.update(
                {
                    "weight_intent": "MAINTAIN",
                    "membership_reason": ";".join(sorted(set(reasons))),
                    "reason_codes": sorted(set(reasons)),
                }
            )
        elif patched.get("current_position"):
            reasons.append("broker_eligibility_existing_position_visibility_preserved")
            patched["reason_codes"] = sorted(set(reasons))
            patched["membership_reason"] = ";".join(sorted(set(reasons)))
        updated.append(patched)
    return updated, sorted(set(payload_reasons))


def _broker_eligibility_payload(member: Mapping[str, Any]) -> dict[str, Any] | None:
    listed_info = member.get("broker_listed_info")
    if not isinstance(listed_info, Mapping):
        return None
    classification = classify_broker_security(dict(listed_info))
    code = str(listed_info.get("code") or "")
    member_code = str(member.get("security_code") or member.get("symbol") or "")
    current_listed = bool(listed_info.get("current_listed", True))
    reason = classification.reason
    tradable = classification.tradable
    if member_code and code and code != member_code:
        tradable = False
        reason = "listed_info_code_mismatch"
    elif not current_listed:
        tradable = False
        reason = "listed_info_not_current"
    status = "PASS" if tradable else "FAIL_CLOSED"
    return {
        "authority_type": BROKER_ELIGIBILITY_AUTHORITY_TYPE,
        "gating_owner": BROKER_ELIGIBILITY_GATING_OWNER,
        "status": status,
        "tradable": tradable,
        "broker_security_type": classification.broker_security_type,
        "normalization_mode": classification.normalization_mode,
        "reason": reason,
        "authority": classification.authority,
        "code": code,
        "product_category": str(listed_info.get("product_category") or ""),
        "security_type": str(listed_info.get("security_type") or ""),
        "market": str(listed_info.get("market") or ""),
        "current_listed": current_listed,
    }


def _broker_listed_info_payload(security_code: str, *rows: Mapping[str, Any] | None) -> dict[str, Any] | None:
    for row in rows:
        if not row:
            continue
        nested = row.get("listed_info")
        if isinstance(nested, Mapping):
            info = _normalize_broker_listed_info(security_code, nested)
            if info is not None:
                return info
        info = _normalize_broker_listed_info(security_code, row)
        if info is not None:
            return info
    return None


def _normalize_broker_listed_info(security_code: str, row: Mapping[str, Any]) -> dict[str, Any] | None:
    product_category = str(row.get("product_category") or row.get("ProdCat") or "").strip()
    security_type = str(row.get("security_type") or row.get("SecType") or row.get("Type") or product_category).strip()
    market = str(row.get("market") or row.get("MktNm") or row.get("market_name") or "").strip()
    code = str(row.get("code") or row.get("Code") or row.get("security_code") or row.get("symbol") or security_code).strip()
    if not product_category and not security_type and not market:
        return None
    current_raw = row.get("current_listed", row.get("is_current_listed", True))
    current_listed = str(current_raw).lower() not in {"false", "0", "no", "nan", "none", ""}
    return {
        "code": code,
        "market": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
    }


def _resolve_target_weight_contract(
    *,
    business_date: str,
    members: list[dict[str, Any]],
    policy_config_summary: PortfolioConstructionSourceSummary,
    portfolio_policy_reference: str,
    source_hashes: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = dict(policy_config_summary.summary or {})
    policy_authority = resolve_portfolio_policy_allocation_authority(
        business_date=business_date,
        policy_config_summary=policy_config_summary,
        portfolio_policy_reference=portfolio_policy_reference,
        source_hashes=source_hashes,
    )
    target_gross_exposure = policy_authority["target_gross_exposure"]
    deprecated_target_member_count = policy_authority["target_position_count"]
    single_name_cap = policy_authority["single_name_weight_cap"]
    source_paths = [item["path"] for item in source_hashes if item.get("path")]
    status = policy_authority["status"]
    reason_codes: list[str] = list(policy_authority["reason_codes"])
    method = {
        "method_id": "production_v1_equal_weight_target_allocation",
        "method_version": "phase23_ao_v1",
        "basis": "target_gross_exposure / eligible_target_member_count with single-name cap",
        "opportunity_score_weight_transform_used": False,
    }
    selected_candidates = _select_target_members(members)
    selected_codes = {row["security_code"] for row in selected_candidates}
    effective_count = len(selected_codes)
    if target_gross_exposure == 0:
        effective_count = 0
    base_weight = 0.0
    if status == "PASS" and effective_count > 0:
        base_weight = min(float(target_gross_exposure) / float(effective_count), float(single_name_cap))
    weighted: list[dict[str, Any]] = []
    for row in members:
        selected = row["security_code"] in selected_codes and status == "PASS" and effective_count > 0
        raw_score = row.get("runtime_opportunity_score")
        zero_reason = ""
        review_reason = ""
        reason = "target_weight_resolved"
        weight = round(base_weight, TARGET_WEIGHT_DECIMALS) if selected else 0.0
        target_membership_override: bool | None = None
        reduce_member_fields: dict[str, Any] = {}
        reduce_authority_fields: dict[str, Any] = {}
        reduce_adjustments: list[dict[str, Any]] = []
        quality_adjustment = _optional_ratio(row.get("quality_allocation_adjustment"))
        quality_action = str(row.get("quality_action") or "")
        if status != "PASS":
            zero_reason = "unresolved_authority"
            review_reason = "target_weight_authority_unresolved"
            reason = "target_weight_authority_unresolved"
        elif quality_action in {"REJECT", "BUY_REJECTED"} and not row.get("current_position"):
            zero_reason = "buy_quality_rejected"
            reason = "buy_quality_rejected"
            weight = 0.0
        elif quality_action in {"REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED"} and not row.get("current_position"):
            zero_reason = "buy_quality_review_required"
            review_reason = "buy_quality_review_required"
            reason = "buy_quality_review_required"
            weight = 0.0
        elif selected and quality_action == "REDUCED_ALLOCATION_ONLY":
            adjustment = quality_adjustment if quality_adjustment is not None else 0.0
            reason = "target_weight_quality_reduction_required_downstream"
        elif row.get("membership_intent") in {"EXCLUDE", "UNRESOLVED"}:
            zero_reason = "opportunity_not_selected"
            reason = "member_not_selected"
        elif row.get("membership_intent") == "REDUCE_CANDIDATE":
            current_weight = _optional_ratio(row.get("current_weight"))
            intensity_resolution = resolve_reduce_intensity_authority(
                row.get("reduce_intensity") or row.get("pm_intensity"),
                business_date=business_date,
                source_pm_decision_ref=str(row.get("source_pm_decision_ref") or row.get("position_management_reference") or ""),
            )
            if current_weight is None or current_weight <= 0:
                if status != "BLOCK":
                    status = "REVIEW_REQUIRED"
                zero_reason = "reduce_current_weight_missing"
                review_reason = "reduce_current_weight_missing"
                reason = "reduce_current_weight_missing"
                weight = 0.0
                reason_codes.append("reduce_current_weight_missing_fail_closed")
            elif intensity_resolution["status"] != "PASS":
                if status != "BLOCK":
                    status = "REVIEW_REQUIRED"
                zero_reason = str(intensity_resolution["reason"])
                review_reason = str(intensity_resolution["reason"])
                reason = str(intensity_resolution["reason"])
                weight = 0.0
                reason_codes.append(f"reduce_intensity_review_required:{intensity_resolution['reason']}")
            else:
                reduce_fraction = float(intensity_resolution["reduce_fraction"])
                remaining_weight = round(current_weight * (1.0 - reduce_fraction), TARGET_WEIGHT_DECIMALS)
                released_weight = round(current_weight - remaining_weight, TARGET_WEIGHT_DECIMALS)
                if not (0.0 < remaining_weight < current_weight):
                    if status != "BLOCK":
                        status = "REVIEW_REQUIRED"
                    zero_reason = "reduce_partial_target_invalid"
                    review_reason = "reduce_partial_target_invalid"
                    reason = "reduce_partial_target_invalid"
                    weight = 0.0
                    reason_codes.append("reduce_partial_target_invalid_fail_closed")
                else:
                    weight = remaining_weight
                    reason = "reduce_partial_target_resolved"
                    zero_reason = ""
                    target_membership_override = True
                    reduce_authority_fields = {
                        "reduce_fraction_authority": intensity_resolution["authority"],
                    }
                    reduce_member_fields = {
                        "reduce_intensity": intensity_resolution["reduce_intensity"],
                        "reduce_fraction": reduce_fraction,
                        "reduce_fraction_authority": intensity_resolution["authority"],
                        "remaining_target_weight": remaining_weight,
                        "released_reduce_capacity": released_weight,
                    }
                    reduce_adjustments = [
                        {
                            "authority": "CANONICAL_REDUCE_INTENSITY_AUTHORITY",
                            "source_pm_decision_ref": str(row.get("source_pm_decision_ref") or row.get("position_management_reference") or ""),
                            "reduce_intensity": intensity_resolution["reduce_intensity"],
                            "reduce_fraction": reduce_fraction,
                            "current_weight": current_weight,
                            "remaining_target_weight": remaining_weight,
                            "released_reduce_capacity": released_weight,
                        }
                    ]
        elif row.get("membership_intent") == "REMOVE_CANDIDATE":
            zero_reason = "existing_position_exit"
            reason = "existing_position_exit"
        elif target_gross_exposure == 0:
            zero_reason = "policy_zero_exposure"
            reason = "policy_zero_exposure"
        elif isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool) and float(raw_score) < 0 and not row.get("current_position"):
            zero_reason = "opportunity_not_selected"
            reason = "negative_opportunity_not_selected"
            weight = 0.0
        elif not selected:
            zero_reason = "opportunity_not_selected"
            reason = "opportunity_not_selected"
        cap_applied = selected and status == "PASS" and target_gross_exposure is not None and effective_count > 0 and float(target_gross_exposure) / float(effective_count) > float(single_name_cap)
        target_membership = target_membership_override if target_membership_override is not None else selected
        authority = {
            "authority_type": "TARGET_WEIGHT_AUTHORITY",
            "method_id": method["method_id"],
            "method_version": method["method_version"],
            "business_date": business_date,
            "portfolio_policy_decision_id": policy_authority["source_decision_id"],
            "portfolio_policy_artifact_path": policy_authority["source_artifact_path"],
            "portfolio_policy_artifact_hash": policy_authority["source_artifact_hash"],
            "target_position_count": deprecated_target_member_count,
            "target_position_count_decision_authority": "DEPRECATED_METADATA_ONLY",
            "target_gross_exposure": target_gross_exposure,
            "cash_reserve": policy_authority["cash_reserve"],
            "resolved_target_member_count": effective_count,
            "single_name_weight_cap": single_name_cap,
            "portfolio_policy_reference": portfolio_policy_reference,
            "opportunity_reference": row.get("opportunity_reference", ""),
            "existing_position_reference": row.get("position_management_reference", "") if row.get("current_position") else "",
            "position_management_reference": row.get("position_management_reference", ""),
            "source_artifact_paths": source_paths,
            "source_artifact_hashes": source_hashes,
            "PIT_status": "PASS",
        }
        resolution = {
            "status": "PASS" if status == "PASS" else "REVIEW_REQUIRED",
            "reason": reason,
            "resolved_weight": weight,
            "base_weight": round(base_weight, TARGET_WEIGHT_DECIMALS),
            "adjustments": [],
            "cap_applied": cap_applied,
            "normalization_applied": False,
            "zero_weight_reason": zero_reason,
            "review_reason": review_reason,
        }
        if selected and quality_action:
            resolution["adjustments"] = [
                {
                    "authority": "ADAPTIVE_BUY_QUALITY_AUTHORITY",
                    "quality_action": quality_action,
                    "quality_decision_id": str(row.get("quality_decision_id") or ""),
                    "quality_allocation_adjustment": quality_adjustment if quality_adjustment is not None else 0.0,
                    "pre_quality_base_weight": round(base_weight, TARGET_WEIGHT_DECIMALS),
                    "post_quality_target_weight": round(weight * (quality_adjustment if quality_adjustment is not None else 0.0), TARGET_WEIGHT_DECIMALS)
                    if quality_action == "REDUCED_ALLOCATION_ONLY"
                    else weight,
                }
            ]
        if weight == 0 and not zero_reason and status == "PASS":
            resolution["zero_weight_reason"] = "other_explicit_contract_reason"
        add_bridge = _resolve_canonical_add_allocation_bridge(
            row=row,
            selected=selected,
            candidate_target_weight=weight,
            single_name_cap=single_name_cap,
            target_gross_exposure=target_gross_exposure,
            members=members,
            business_date=business_date,
        )
        if add_bridge:
            weight = add_bridge["post_add_target_weight"]
            target_membership = weight > 0.0 or bool(row.get("target_membership"))
            reason = str(add_bridge["target_weight_reason"])
            zero_reason = str(add_bridge["zero_weight_reason"])
            review_reason = str(add_bridge["review_reason"])
            resolution = {
                **resolution,
                "reason": reason,
                "resolved_weight": weight,
                "zero_weight_reason": zero_reason,
                "review_reason": review_reason,
                "add_allocation_bridge": add_bridge["trace"],
            }
            authority = {**authority, "add_allocation_bridge_authority": add_bridge["authority"]}
        updated = {
            **row,
            "target_membership": target_membership,
            "target_weight": weight,
            "target_weight_authority": authority,
            "target_weight_resolution": resolution,
            "weight_reason": reason,
            **reduce_member_fields,
            **(add_bridge["member_fields"] if add_bridge else {}),
        }
        if reduce_authority_fields:
            updated["target_weight_authority"] = {**dict(updated["target_weight_authority"]), **reduce_authority_fields}
        if reduce_adjustments:
            updated["target_weight_resolution"] = {
                **dict(updated["target_weight_resolution"]),
                "adjustments": list(updated["target_weight_resolution"].get("adjustments") or []) + reduce_adjustments,
            }
        weighted.append(updated)
    reconciliation = _reconcile_incremental_budget(
        members=weighted,
        target_gross_exposure=target_gross_exposure,
        target_weight_sum_tolerance=_target_weight_sum_tolerance(effective_count),
    )
    weighted = reconciliation["members"]
    total_weight = reconciliation["final_target_weight_sum"]
    target_weight_sum_tolerance = _target_weight_sum_tolerance(effective_count)
    reason_codes.extend(reconciliation["reason_codes"])
    invalid_positive_increment_over_target = _positive_increment_over_target(
        final_target_weight_sum=total_weight,
        target_gross_exposure=target_gross_exposure,
        tolerance=target_weight_sum_tolerance,
        accepted_add=float(reconciliation["evidence"].get("accepted_add_increment") or 0.0),
        accepted_buy_new=float(reconciliation["evidence"].get("accepted_buy_new_weight") or 0.0),
    )
    if invalid_positive_increment_over_target:
        status = "BLOCK"
        reason_codes.append("positive_increment_over_target_gross_exposure")
    elif (
        target_gross_exposure is not None
        and total_weight > float(target_gross_exposure) + target_weight_sum_tolerance
        and reconciliation["evidence"].get("aggregate_exposure_state") != "OVER_TARGET_EXISTING_BASELINE"
    ):
        status = "BLOCK"
        reason_codes.append("total_target_weight_above_target_gross_exposure")
    return {
        "status": status,
        "reason_codes": reason_codes,
        "method": method,
        "members": weighted,
        "target_gross_exposure": target_gross_exposure,
        "resolved_target_member_count": effective_count,
        "single_name_weight_cap": single_name_cap,
        "total_target_weight": round(total_weight, 6),
        "target_weight_sum_tolerance": target_weight_sum_tolerance,
        "portfolio_policy_allocation_authority": policy_authority,
        "incremental_budget_reconciliation": reconciliation["evidence"],
    }


def _reconcile_incremental_budget(
    *,
    members: list[dict[str, Any]],
    target_gross_exposure: float | None,
    target_weight_sum_tolerance: float,
) -> dict[str, Any]:
    if target_gross_exposure is None:
        total = round(sum(float(member.get("target_weight") or 0.0) for member in members), TARGET_WEIGHT_DECIMALS)
        return {
            "members": members,
            "final_target_weight_sum": total,
            "reason_codes": [],
            "evidence": {
                "status": "NOT_APPLICABLE",
                "reason": "target_gross_exposure_unresolved",
                "target_gross_exposure": None,
                "baseline_existing_required_weight": 0.0,
                "available_incremental_budget": 0.0,
                "requested_add_increment": 0.0,
                "accepted_add_increment": 0.0,
                "requested_buy_new_weight": 0.0,
                "accepted_buy_new_weight": 0.0,
                "released_reduce_capacity": 0.0,
                "trimmed_incremental_weight": 0.0,
                "final_target_weight_sum": total,
            },
        }

    baseline_total = 0.0
    requested_add = 0.0
    requested_buy_new = 0.0
    released_reduce = 0.0
    participant_requests: list[dict[str, Any]] = []
    prepared: list[dict[str, Any]] = []
    reason_codes: list[str] = []
    for index, member in enumerate(members):
        current_weight = _optional_ratio(member.get("current_weight"))
        original_target = round(float(member.get("target_weight") or 0.0), TARGET_WEIGHT_DECIMALS)
        pm_action = str(member.get("pm_action") or "").upper()
        membership = str(member.get("membership_intent") or "").upper()
        current_position = bool(member.get("current_position"))
        baseline = 0.0
        request = 0.0
        participant_type = "NONE"
        if current_position and membership in {"REDUCE_CANDIDATE", "REMOVE_CANDIDATE", "EXCLUDE"}:
            baseline = original_target
            if current_weight is not None:
                released_reduce += round(max(current_weight - baseline, 0.0), TARGET_WEIGHT_DECIMALS)
        elif current_position and pm_action in {"HOLD", "ADD"}:
            baseline = current_weight if current_weight is not None else original_target
            if pm_action == "ADD" and current_weight is not None:
                request = round(max(original_target - baseline, 0.0), TARGET_WEIGHT_DECIMALS)
                requested_add += request
                participant_type = "ADD_INCREMENT"
            elif pm_action == "HOLD" and current_weight is not None and original_target > baseline:
                reason_codes.append("hold_equal_weight_increase_reconciled_to_current_weight")
        elif current_position:
            baseline = original_target
        elif membership == "ADD_CANDIDATE":
            request = original_target
            requested_buy_new += request
            participant_type = "BUY_NEW"
        baseline = round(baseline, TARGET_WEIGHT_DECIMALS)
        baseline_total += baseline
        prepared.append(
            {
                "index": index,
                "baseline": baseline,
                "request": request,
                "participant_type": participant_type,
                "original_target": original_target,
            }
        )
        if request > 0:
            participant_requests.append(
                {
                    "index": index,
                    "request": request,
                    "participant_type": participant_type,
                    "priority": _positive_int(member.get("construction_priority"), 999999),
                    "security_code": str(member.get("security_code") or ""),
                }
            )

    baseline_total = round(baseline_total, TARGET_WEIGHT_DECIMALS)
    available_budget = round(max(float(target_gross_exposure) - baseline_total, 0.0), TARGET_WEIGHT_DECIMALS)
    allocation_budget = round(
        max(float(target_gross_exposure) + target_weight_sum_tolerance - baseline_total, 0.0),
        TARGET_WEIGHT_DECIMALS,
    )
    if baseline_total > float(target_gross_exposure) + target_weight_sum_tolerance and _is_passive_convergence_baseline(
        members=members,
        prepared=prepared,
    ):
        reason_codes.append("existing_baseline_over_dynamic_target_passive_convergence")
        if requested_add > 0 or requested_buy_new > 0:
            reason_codes.append("positive_increment_suppressed_while_over_target")
        final_members = [
            _member_with_budget_reconciliation(
                member=member,
                prepared=prepared_item,
                accepted_increment=0.0,
                available_budget=available_budget,
                target_gross_exposure=target_gross_exposure,
                reason="existing_baseline_over_dynamic_target_passive_convergence",
            )
            for member, prepared_item in zip(members, prepared)
        ]
        final_sum = round(sum(float(member.get("target_weight") or 0.0) for member in final_members), TARGET_WEIGHT_DECIMALS)
        return {
            "members": final_members,
            "final_target_weight_sum": final_sum,
            "reason_codes": sorted(set(reason_codes)),
            "evidence": {
                "status": "PASS",
                "reason": "existing_baseline_over_dynamic_target_passive_convergence",
                "transition_mode": "PASSIVE_CONVERGENCE",
                "aggregate_exposure_state": "OVER_TARGET_EXISTING_BASELINE",
                "positive_increment_allowed": False,
                "target_gross_exposure": target_gross_exposure,
                "baseline_existing_required_weight": baseline_total,
                "available_incremental_budget": available_budget,
                "requested_add_increment": round(requested_add, TARGET_WEIGHT_DECIMALS),
                "accepted_add_increment": 0.0,
                "requested_buy_new_weight": round(requested_buy_new, TARGET_WEIGHT_DECIMALS),
                "accepted_buy_new_weight": 0.0,
                "released_reduce_capacity": round(released_reduce, TARGET_WEIGHT_DECIMALS),
                "trimmed_incremental_weight": round(requested_add + requested_buy_new, TARGET_WEIGHT_DECIMALS),
                "final_target_weight_sum": final_sum,
            },
        }
    if baseline_total > float(target_gross_exposure) + target_weight_sum_tolerance:
        reason_codes.append("baseline_existing_required_weight_above_target_gross_exposure")
        final_members = [
            _member_with_budget_reconciliation(
                member=member,
                prepared=prepared_item,
                accepted_increment=0.0,
                available_budget=available_budget,
                target_gross_exposure=target_gross_exposure,
                reason="baseline_existing_required_weight_above_target_gross_exposure",
            )
            for member, prepared_item in zip(members, prepared)
        ]
        final_sum = round(sum(float(member.get("target_weight") or 0.0) for member in final_members), TARGET_WEIGHT_DECIMALS)
        return {
            "members": final_members,
            "final_target_weight_sum": final_sum,
            "reason_codes": sorted(set(reason_codes)),
            "evidence": {
                "status": "BLOCK",
                "reason": "baseline_existing_required_weight_above_target_gross_exposure",
                "target_gross_exposure": target_gross_exposure,
                "baseline_existing_required_weight": baseline_total,
                "available_incremental_budget": available_budget,
                "requested_add_increment": round(requested_add, TARGET_WEIGHT_DECIMALS),
                "accepted_add_increment": 0.0,
                "requested_buy_new_weight": round(requested_buy_new, TARGET_WEIGHT_DECIMALS),
                "accepted_buy_new_weight": 0.0,
                "released_reduce_capacity": round(released_reduce, TARGET_WEIGHT_DECIMALS),
                "trimmed_incremental_weight": round(requested_add + requested_buy_new, TARGET_WEIGHT_DECIMALS),
                "final_target_weight_sum": final_sum,
            },
        }

    total_requested_incremental = round(requested_add + requested_buy_new, TARGET_WEIGHT_DECIMALS)
    accepted_by_index: dict[int, float] = {}
    remaining = allocation_budget if total_requested_incremental <= allocation_budget else available_budget
    for request in sorted(participant_requests, key=lambda item: (item["priority"], item["security_code"])):
        accepted = min(float(request["request"]), remaining)
        accepted = round(max(accepted, 0.0), TARGET_WEIGHT_DECIMALS)
        accepted_by_index[int(request["index"])] = accepted
        remaining = round(max(remaining - accepted, 0.0), TARGET_WEIGHT_DECIMALS)
    accepted_add = 0.0
    accepted_buy_new = 0.0
    for item in participant_requests:
        accepted = accepted_by_index.get(int(item["index"]), 0.0)
        if item["participant_type"] == "ADD_INCREMENT":
            accepted_add += accepted
        elif item["participant_type"] == "BUY_NEW":
            accepted_buy_new += accepted
    accepted_add = round(accepted_add, TARGET_WEIGHT_DECIMALS)
    accepted_buy_new = round(accepted_buy_new, TARGET_WEIGHT_DECIMALS)
    trimmed = round(max(requested_add + requested_buy_new - accepted_add - accepted_buy_new, 0.0), TARGET_WEIGHT_DECIMALS)
    if trimmed > 0:
        reason_codes.append("incremental_budget_trimmed_to_target_gross_exposure")
    final_members = [
        _member_with_budget_reconciliation(
            member=member,
            prepared=prepared_item,
            accepted_increment=accepted_by_index.get(int(prepared_item["index"]), 0.0),
            available_budget=available_budget,
            target_gross_exposure=target_gross_exposure,
            reason="incremental_budget_reconciled",
        )
        for member, prepared_item in zip(members, prepared)
    ]
    final_sum = round(sum(float(member.get("target_weight") or 0.0) for member in final_members), TARGET_WEIGHT_DECIMALS)
    return {
        "members": final_members,
        "final_target_weight_sum": final_sum,
        "reason_codes": sorted(set(reason_codes)),
        "evidence": {
            "status": "PASS",
            "reason": "incremental_budget_reconciled",
            "target_gross_exposure": target_gross_exposure,
            "baseline_existing_required_weight": baseline_total,
            "available_incremental_budget": available_budget,
            "requested_add_increment": round(requested_add, TARGET_WEIGHT_DECIMALS),
            "accepted_add_increment": accepted_add,
            "requested_buy_new_weight": round(requested_buy_new, TARGET_WEIGHT_DECIMALS),
            "accepted_buy_new_weight": accepted_buy_new,
            "released_reduce_capacity": round(released_reduce, TARGET_WEIGHT_DECIMALS),
            "trimmed_incremental_weight": trimmed,
            "final_target_weight_sum": final_sum,
        },
    }


def apply_lot_aware_final_reallocation(
    *,
    members: list[dict[str, Any]],
    lot_feasibility_rows: list[Mapping[str, Any]],
    target_gross_exposure: float | None,
    single_name_cap: float | None,
) -> dict[str, Any]:
    feasibility_by_symbol = {
        str(row.get("symbol") or row.get("security_code") or ""): dict(row)
        for row in lot_feasibility_rows
        if str(row.get("symbol") or row.get("security_code") or "")
    }
    if target_gross_exposure is None:
        return {
            "members": members,
            "evidence": {"status": "NOT_APPLICABLE", "reason": "target_gross_exposure_unresolved"},
            "reason_codes": [],
        }
    prepared: list[dict[str, Any]] = []
    baseline_total = 0.0
    reason_codes: list[str] = []
    for index, member in enumerate(members):
        current_weight = _optional_ratio(member.get("current_weight"))
        target = round(float(member.get("target_weight") or 0.0), TARGET_WEIGHT_DECIMALS)
        pm_action = str(member.get("pm_action") or "").upper()
        membership = str(member.get("membership_intent") or "").upper()
        current_position = bool(member.get("current_position"))
        baseline = 0.0
        participant_type = "NONE"
        if current_position and pm_action in {"HOLD", "ADD"}:
            baseline = current_weight if current_weight is not None else target
            participant_type = "BUY_ADD" if pm_action == "ADD" and target > baseline else "NONE"
        elif current_position:
            baseline = target
        elif membership == "ADD_CANDIDATE":
            participant_type = "BUY_NEW" if target > 0 else "NONE"
        baseline = round(baseline, TARGET_WEIGHT_DECIMALS)
        baseline_total += baseline
        prepared.append({"index": index, "baseline": baseline, "draft_target": target, "participant_type": participant_type})
    baseline_total = round(baseline_total, TARGET_WEIGHT_DECIMALS)
    if baseline_total > float(target_gross_exposure) + _target_weight_sum_tolerance(len(members)) and _is_passive_convergence_baseline(members=members, prepared=[{"baseline": item["baseline"]} for item in prepared]):
        return {
            "members": members,
            "evidence": {
                "status": "PASS",
                "reason": "passive_convergence_preserved_no_lot_reallocation",
                "positive_increment_allowed": False,
                "baseline_existing_required_weight": baseline_total,
            },
            "reason_codes": ["lot_aware_reallocation_skipped_passive_convergence"],
        }
    remaining = round(max(float(target_gross_exposure) - baseline_total, 0.0), TARGET_WEIGHT_DECIMALS)
    accepted_by_index: dict[int, float] = {}
    skipped: list[dict[str, Any]] = []
    skipped_by_index: dict[int, str] = {}
    promoted: list[dict[str, Any]] = []
    candidates = []
    for item in prepared:
        if item["participant_type"] == "NONE":
            accepted_by_index[item["index"]] = 0.0
            continue
        member = members[item["index"]]
        symbol = str(member.get("security_code") or member.get("symbol") or "")
        feasibility = feasibility_by_symbol.get(symbol)
        request = round(max(float(item["draft_target"]) - float(item["baseline"]), 0.0), TARGET_WEIGHT_DECIMALS)
        candidates.append(
            {
                **item,
                "symbol": symbol,
                "request": request,
                "priority": _positive_int(member.get("construction_priority"), 999999),
                "score": _finite_number(member.get("runtime_opportunity_score")) or 0.0,
                "feasibility": feasibility,
            }
        )
    for item in sorted(candidates, key=lambda value: (value["priority"], value["symbol"])):
        feasibility = item["feasibility"]
        member = members[item["index"]]
        min_weight = _optional_ratio((feasibility or {}).get("minimum_executable_weight"))
        lot_feasible = bool((feasibility or {}).get("lot_feasible"))
        broker_eligible = (feasibility or {}).get("broker_eligible") is not False and str(member.get("broker_eligibility_status") or "") != "FAIL_CLOSED"
        required = item["request"]
        if not lot_feasible:
            if min_weight is not None and required < min_weight:
                required = min_weight
            else:
                required = 0.0
        if not broker_eligible or required <= 0:
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = "lot_or_broker_infeasible"
            skipped.append({"symbol": item["symbol"], "reason": "lot_or_broker_infeasible", "feasibility": feasibility})
            continue
        if single_name_cap is not None:
            max_increment = round(max(float(single_name_cap) - float(item["baseline"]), 0.0), TARGET_WEIGHT_DECIMALS)
            if required > max_increment:
                accepted_by_index[item["index"]] = 0.0
                skipped_by_index[item["index"]] = "minimum_lot_exceeds_concentration_cap"
                skipped.append({"symbol": item["symbol"], "reason": "minimum_lot_exceeds_concentration_cap", "required_weight": required, "max_increment": max_increment})
                continue
        if required > remaining:
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = "minimum_lot_exceeds_remaining_budget"
            skipped.append({"symbol": item["symbol"], "reason": "minimum_lot_exceeds_remaining_budget", "required_weight": required, "remaining_budget": remaining})
            continue
        accepted_by_index[item["index"]] = required
        remaining = round(max(remaining - required, 0.0), TARGET_WEIGHT_DECIMALS)
        if required > item["request"]:
            promoted.append({"symbol": item["symbol"], "from_weight": item["request"], "to_weight": required, "reason": "minimum_executable_lot_authorized_by_pc"})
    final_members = []
    for member, item in zip(members, prepared):
        accepted = accepted_by_index.get(item["index"], 0.0)
        final_weight = round(float(item["baseline"]) + accepted, TARGET_WEIGHT_DECIMALS)
        resolution = dict(member.get("target_weight_resolution") or {})
        if final_weight == 0.0 and resolution.get("status") == "PASS" and not resolution.get("zero_weight_reason"):
            resolution["zero_weight_reason"] = skipped_by_index.get(item["index"], "lot_aware_zero_weight_preserved")
        adjustments = list(resolution.get("adjustments") or [])
        adjustments.append(
            {
                "authority": LOT_AWARE_REALLOCATION_AUTHORITY_TYPE,
                "pre_lot_target_weight": item["draft_target"],
                "post_lot_target_weight": final_weight,
                "accepted_lot_increment_weight": accepted,
            }
        )
        final_members.append(
            {
                **member,
                "target_weight": final_weight,
                "target_membership": final_weight > 0 if not member.get("current_position") else bool(member.get("target_membership")) and final_weight > 0,
                "target_weight_authority": {
                    **dict(member.get("target_weight_authority") or {}),
                    "lot_aware_final_reallocation_authority": {
                        "authority_type": LOT_AWARE_REALLOCATION_AUTHORITY_TYPE,
                        "ps_preflight_decides_economic_allocation": False,
                    },
                },
                "target_weight_resolution": {
                    **resolution,
                    "resolved_weight": final_weight,
                    "reason": "lot_aware_final_reallocation",
                    "adjustments": adjustments,
                    "lot_aware_final_reallocation": {
                        "authority_type": LOT_AWARE_REALLOCATION_AUTHORITY_TYPE,
                        "pre_lot_target_weight": item["draft_target"],
                        "post_lot_target_weight": final_weight,
                        "accepted_lot_increment_weight": accepted,
                    },
                },
                "lot_aware_final_target_weight": final_weight,
                "lot_aware_accepted_incremental_weight": accepted if item["participant_type"] == "BUY_ADD" else 0.0,
                "lot_aware_accepted_buy_new_weight": accepted if item["participant_type"] == "BUY_NEW" else 0.0,
            }
        )
    total = round(sum(float(member.get("target_weight") or 0.0) for member in final_members), TARGET_WEIGHT_DECIMALS)
    if skipped:
        reason_codes.append("lot_aware_infeasible_allocations_reallocated_or_cash")
    if promoted:
        reason_codes.append("lot_aware_minimum_executable_lot_authorized")
    return {
        "members": final_members,
        "reason_codes": sorted(set(reason_codes)),
        "evidence": {
            "status": "PASS",
            "authority_type": LOT_AWARE_REALLOCATION_AUTHORITY_TYPE,
            "target_gross_exposure": target_gross_exposure,
            "baseline_existing_required_weight": baseline_total,
            "final_target_weight_sum": total,
            "remaining_cash_weight": remaining,
            "skipped": skipped,
            "promoted": promoted,
            "ps_preflight_decides_economic_allocation": False,
            "pc_remains_target_weight_authority": True,
        },
    }


def _positive_increment_over_target(
    *,
    final_target_weight_sum: float,
    target_gross_exposure: float | None,
    tolerance: float,
    accepted_add: float,
    accepted_buy_new: float,
) -> bool:
    if target_gross_exposure is None:
        return False
    if round(max(float(accepted_add), 0.0) + max(float(accepted_buy_new), 0.0), TARGET_WEIGHT_DECIMALS) <= 0:
        return False
    return float(final_target_weight_sum) > float(target_gross_exposure) + float(tolerance)


def _is_passive_convergence_baseline(*, members: list[dict[str, Any]], prepared: list[dict[str, Any]]) -> bool:
    for member, prepared_item in zip(members, prepared):
        baseline = round(float(prepared_item.get("baseline") or 0.0), TARGET_WEIGHT_DECIMALS)
        if baseline <= 0:
            continue
        if not member.get("current_position"):
            return False
        pm_action = str(member.get("pm_action") or "").upper()
        membership = str(member.get("membership_intent") or "").upper()
        if membership in {"REDUCE_CANDIDATE", "REMOVE_CANDIDATE", "EXCLUDE"}:
            continue
        current_weight = _optional_ratio(member.get("current_weight"))
        if pm_action in {"HOLD", "ADD"} and current_weight is not None and baseline == round(current_weight, TARGET_WEIGHT_DECIMALS):
            continue
        return False
    return True


def _member_with_budget_reconciliation(
    *,
    member: dict[str, Any],
    prepared: Mapping[str, Any],
    accepted_increment: float,
    available_budget: float,
    target_gross_exposure: float,
    reason: str,
) -> dict[str, Any]:
    baseline = round(float(prepared.get("baseline") or 0.0), TARGET_WEIGHT_DECIMALS)
    request = round(float(prepared.get("request") or 0.0), TARGET_WEIGHT_DECIMALS)
    accepted_increment = round(float(accepted_increment or 0.0), TARGET_WEIGHT_DECIMALS)
    final_weight = round(baseline + accepted_increment, TARGET_WEIGHT_DECIMALS)
    trimmed = round(max(request - accepted_increment, 0.0), TARGET_WEIGHT_DECIMALS)
    participant_type = str(prepared.get("participant_type") or "NONE")
    reconciliation = {
        "authority_type": "PORTFOLIO_CONSTRUCTION_INCREMENTAL_BUDGET_RECONCILIATION",
        "target_gross_exposure": target_gross_exposure,
        "available_incremental_budget": available_budget,
        "participant_type": participant_type,
        "baseline_existing_weight": baseline,
        "requested_incremental_weight": request if participant_type == "ADD_INCREMENT" else 0.0,
        "accepted_incremental_weight": accepted_increment if participant_type == "ADD_INCREMENT" else 0.0,
        "requested_buy_new_weight": request if participant_type == "BUY_NEW" else 0.0,
        "accepted_buy_new_weight": accepted_increment if participant_type == "BUY_NEW" else 0.0,
        "trimmed_incremental_weight": trimmed,
        "final_target_weight": final_weight,
        "reason": reason,
    }
    resolution = dict(member.get("target_weight_resolution") or {})
    adjustments = list(resolution.get("adjustments") or [])
    original_target = round(float(prepared.get("original_target") or 0.0), TARGET_WEIGHT_DECIMALS)
    if final_weight != original_target or request > 0:
        adjustments.append(
            {
                "authority": "PORTFOLIO_CONSTRUCTION_INCREMENTAL_BUDGET_RECONCILIATION",
                "pre_reconciliation_target_weight": original_target,
                "post_reconciliation_target_weight": final_weight,
                "baseline_existing_weight": baseline,
                "requested_incremental_weight": request,
                "accepted_incremental_weight": accepted_increment,
                "trimmed_incremental_weight": trimmed,
            }
        )
    zero_reason = str(resolution.get("zero_weight_reason") or "")
    if final_weight == 0.0 and not zero_reason:
        zero_reason = "incremental_budget_zero_allocation"
    review_reason = str(resolution.get("review_reason") or "")
    if trimmed > 0:
        review_reason = ",".join(part for part in (review_reason, "incremental_budget_trimmed_or_deferred") if part)
    return {
        **member,
        "target_membership": final_weight > 0.0 if not member.get("current_position") else bool(member.get("target_membership")) and final_weight > 0.0,
        "target_weight": final_weight,
        "weight_reason": reason if final_weight != original_target or trimmed > 0 else member.get("weight_reason", reason),
        "target_weight_authority": {
            **dict(member.get("target_weight_authority") or {}),
            "incremental_budget_reconciliation_authority": {
                "authority_type": "PORTFOLIO_CONSTRUCTION_INCREMENTAL_BUDGET_RECONCILIATION",
                "target_gross_exposure": target_gross_exposure,
                "available_incremental_budget": available_budget,
            },
        },
        "target_weight_resolution": {
            **resolution,
            "reason": reason if final_weight != original_target or trimmed > 0 else resolution.get("reason", reason),
            "resolved_weight": final_weight,
            "adjustments": adjustments,
            "normalization_applied": bool(resolution.get("normalization_applied")) or final_weight != original_target or trimmed > 0,
            "zero_weight_reason": zero_reason,
            "review_reason": review_reason,
            "incremental_budget_reconciliation": reconciliation,
        },
        "baseline_existing_weight": baseline,
        "requested_incremental_weight": request if participant_type == "ADD_INCREMENT" else 0.0,
        "accepted_incremental_weight": accepted_increment if participant_type == "ADD_INCREMENT" else 0.0,
        "requested_buy_new_weight": request if participant_type == "BUY_NEW" else 0.0,
        "accepted_buy_new_weight": accepted_increment if participant_type == "BUY_NEW" else 0.0,
        "trimmed_incremental_weight": trimmed,
        "incremental_budget_reconciliation": reconciliation,
    }


def _resolve_canonical_add_allocation_bridge(
    *,
    row: Mapping[str, Any],
    selected: bool,
    candidate_target_weight: float,
    single_name_cap: float | None,
    target_gross_exposure: float | None,
    members: list[dict[str, Any]],
    business_date: str,
) -> dict[str, Any] | None:
    if not row.get("current_position") or str(row.get("pm_action") or "").upper() != "ADD":
        return None
    current_weight = _optional_ratio(row.get("current_weight"))
    reason_codes: list[str] = []
    add_evidence = resolve_add_investment_evidence(row=row, members=members, business_date=business_date)
    expected_edge = dict(add_evidence["expected_edge"])
    incremental_value = dict(add_evidence["incremental_value"])
    opportunity_cost = dict(add_evidence["opportunity_cost"])
    campaign_evidence = dict(add_evidence["campaign_continuation"])
    no_loss = dict(add_evidence["no_loss_averaging"])
    campaign = str(campaign_evidence.get("status") or "FAIL_CLOSED")
    no_loss_status = str(no_loss.get("status") or "FAIL_CLOSED")
    concentration = _explicit_pass_or_default(row, ("concentration_status", "add_concentration_status"), default="PASS")
    capital = _explicit_pass_or_default(row, ("capital_availability_status", "add_capital_availability_status"), default="PASS")
    execution = _execution_feasibility_state(row)
    if current_weight is None:
        reason_codes.append("ADD_REQUIRED_EVIDENCE_MISSING")
        current_weight = float(candidate_target_weight)
        current_weight_observed = False
    else:
        current_weight_observed = True
    add_increment_request = round(max(float(candidate_target_weight), 0.0), TARGET_WEIGHT_DECIMALS)
    desired_increment = round(max(float(candidate_target_weight) - current_weight, 0.0), TARGET_WEIGHT_DECIMALS)
    broker_status = str(row.get("broker_eligibility_status") or "")
    if broker_status == "FAIL_CLOSED":
        broker_reason = str(row.get("broker_eligibility_reason") or "broker_eligibility_fail_closed")
        reason_codes.extend([broker_reason, "broker_eligibility_buy_add_excluded_existing_position_visible", "ADD_TARGET_WEIGHT_UNCHANGED"])
        review_reason = ",".join(sorted(set(reason_codes)))
        trace = {
            "status": "FAIL_CLOSED",
            "business_date": business_date,
            "current_weight_observed": current_weight_observed,
            "eligibility_checks": {"pm_add": "PASS", "broker_execution_eligibility": "FAIL_CLOSED"},
            "broker_eligibility": dict(row.get("broker_eligibility") or {}),
            "expected_edge_improvement": {"status": "NOT_EVALUATED", "state": "BROKER_ELIGIBILITY_FAIL_CLOSED"},
            "incremental_investment_value": {"status": "NOT_EVALUATED", "state": "BROKER_ELIGIBILITY_FAIL_CLOSED"},
            "opportunity_cost": {"status": "NOT_EVALUATED", "state": "BROKER_ELIGIBILITY_FAIL_CLOSED"},
            "add_investment_evidence": {**add_evidence, "producer_result_status": "NOT_EVALUATED_BROKER_FAIL_CLOSED"},
        }
        return {
            "post_add_target_weight": current_weight,
            "target_weight_reason": "add_target_weight_unchanged",
            "zero_weight_reason": "ADD_TARGET_WEIGHT_UNCHANGED",
            "review_reason": review_reason,
            "trace": trace,
            "authority": {
                "authority_type": "CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY",
                "business_date": business_date,
                "decision_scope": "portfolio_construction_target_weight_existing_position_add",
                "pm_quantity_authority_used": False,
                "legacy_add_executable_used": False,
            },
            "member_fields": {
                "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
                "current_target_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
                "desired_incremental_weight": desired_increment,
                "add_increment_request_weight": add_increment_request,
                "post_add_target_weight": current_weight,
                "normalized_target_weight": current_weight,
                "target_weight_change": 0.0,
                "target_weight_reason_codes": sorted(set(reason_codes)),
                "add_allocation_eligibility_status": "FAIL_CLOSED",
                "expected_edge_improvement_state": "BROKER_ELIGIBILITY_FAIL_CLOSED",
                "incremental_investment_value_state": "BROKER_ELIGIBILITY_FAIL_CLOSED",
                "opportunity_cost_status": "NOT_EVALUATED",
                "no_loss_averaging_status": "NOT_EVALUATED",
                "add_investment_evidence": trace["add_investment_evidence"],
            },
        }
    post_add_target = current_weight
    target_reason = "add_target_weight_unchanged"
    zero_reason = "ADD_TARGET_WEIGHT_UNCHANGED"
    review_reason = ""
    eligibility_checks = {
        "pm_add": "PASS",
        "expected_edge_improvement": expected_edge["status"],
        "incremental_investment_value": incremental_value["status"],
        "opportunity_cost": opportunity_cost["status"],
        "campaign_continuation": campaign,
        "no_loss_averaging": no_loss_status,
        "concentration": concentration,
        "capital_availability": capital,
        "execution_feasibility": execution,
    }
    if not selected:
        reason_codes.append("ADD_TARGET_WEIGHT_UNCHANGED")
    if not current_weight_observed:
        review_reason = "ADD_REQUIRED_EVIDENCE_MISSING"
    if expected_edge["status"] != "PASS":
        reason_codes.append("ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED" if expected_edge["state"] == "UNKNOWN" else f"ADD_EXPECTED_EDGE_{expected_edge['state']}")
    if incremental_value["status"] != "PASS":
        reason_codes.append(f"ADD_INCREMENTAL_VALUE_{incremental_value['state']}")
    if opportunity_cost["status"] != "PASS":
        reason_codes.append("ADD_OPPORTUNITY_COST_FAIL")
    if campaign != "PASS":
        reason_codes.append("ADD_CAMPAIGN_CONTINUATION_FAIL")
    if no_loss_status != "PASS":
        reason_codes.append("ADD_NO_LOSS_AVERAGING_FAIL")
    if concentration != "PASS":
        reason_codes.append("ADD_CONCENTRATION_CONSTRAINT")
    if capital != "PASS":
        reason_codes.append("ADD_CAPITAL_UNAVAILABLE")
    if execution == "BLOCK":
        reason_codes.append("ADD_EXECUTION_FEASIBILITY_BLOCK")
    eligible = (
        selected
        and current_weight_observed
        and expected_edge["status"] == "PASS"
        and incremental_value["status"] == "PASS"
        and opportunity_cost["status"] == "PASS"
        and campaign == "PASS"
        and no_loss_status == "PASS"
        and concentration == "PASS"
        and capital == "PASS"
        and execution != "BLOCK"
        and add_increment_request > 0
    )
    if eligible:
        cap = single_name_cap if single_name_cap is not None else 1.0
        exposure_cap = target_gross_exposure if target_gross_exposure is not None else 1.0
        max_add_target = min(float(cap), float(exposure_cap))
        post_add_target = round(min(current_weight + add_increment_request, max_add_target), TARGET_WEIGHT_DECIMALS)
        if post_add_target > current_weight:
            target_reason = "canonical_add_allocation_bridge_pass"
            zero_reason = ""
            reason_codes.append("ADD_TARGET_WEIGHT_INCREASED")
        else:
            reason_codes.append("ADD_TARGET_WEIGHT_UNCHANGED")
            zero_reason = "ADD_TARGET_WEIGHT_UNCHANGED"
    target_change = round(post_add_target - current_weight, TARGET_WEIGHT_DECIMALS) if current_weight_observed else 0.0
    if target_change <= 0 and not review_reason:
        review_reason = ",".join(sorted(set(reason_codes))) if reason_codes else ""
    trace = {
        "status": "PASS" if target_change > 0 else "FAIL_CLOSED",
        "business_date": business_date,
        "current_weight_observed": current_weight_observed,
        "eligibility_checks": eligibility_checks,
        "expected_edge_improvement": expected_edge,
        "incremental_investment_value": incremental_value,
        "opportunity_cost": opportunity_cost,
        "no_loss_averaging": no_loss,
        "add_investment_evidence": add_evidence,
    }
    return {
        "post_add_target_weight": post_add_target,
        "target_weight_reason": target_reason,
        "zero_weight_reason": zero_reason,
        "review_reason": review_reason,
        "trace": trace,
        "authority": {
            "authority_type": "CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY",
            "business_date": business_date,
            "decision_scope": "portfolio_construction_target_weight_existing_position_add",
            "pm_quantity_authority_used": False,
            "legacy_add_executable_used": False,
            "add_investment_evidence_schema_version": add_evidence["schema_version"],
            "add_investment_evidence_producer_version": add_evidence["producer_version"],
        },
        "member_fields": {
            "current_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
            "current_target_weight": round(current_weight, TARGET_WEIGHT_DECIMALS),
            "desired_incremental_weight": desired_increment,
            "add_increment_request_weight": add_increment_request,
            "post_add_target_weight": post_add_target,
            "normalized_target_weight": post_add_target,
            "target_weight_change": target_change,
            "target_weight_reason_codes": sorted(set(reason_codes)),
            "add_allocation_eligibility_status": "PASS" if target_change > 0 else "FAIL_CLOSED",
            "expected_edge_improvement_state": expected_edge["state"],
            "incremental_investment_value_state": incremental_value["state"],
            "opportunity_cost_status": opportunity_cost["status"],
            "no_loss_averaging_status": no_loss.get("state"),
            "add_investment_evidence": add_evidence,
        },
    }


def _resolve_expected_edge_improvement(row: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    explicit_state = str(row.get("expected_edge_improvement_state") or row.get("add_expected_edge_improvement_state") or "").upper()
    current_score = _finite_number(row.get("runtime_opportunity_score"))
    baseline_score = _finite_number(
        row.get("expected_edge_baseline_score", row.get("previous_expected_edge_score", row.get("entry_expected_edge_baseline_score")))
    )
    if explicit_state in {"IMPROVING", "STABLE_ADEQUATE", "WEAKENING", "INSUFFICIENT", "UNKNOWN"}:
        state = explicit_state
    elif current_score is not None and baseline_score is not None:
        state = "IMPROVING" if current_score > baseline_score else ("STABLE_ADEQUATE" if current_score == baseline_score else "WEAKENING")
    else:
        state = "UNKNOWN"
    baseline_type = str(row.get("expected_edge_baseline_type") or ("same_campaign_latest_accepted_pm_decision" if baseline_score is not None else "UNKNOWN"))
    pass_state = state == "IMPROVING" or (state == "STABLE_ADEQUATE" and str(row.get("stable_adequate_opportunity_cost_superior") or "").upper() == "PASS")
    return {
        "status": "PASS" if pass_state else "FAIL_CLOSED",
        "state": state,
        "current_score": current_score,
        "baseline_score": baseline_score,
        "baseline_type": baseline_type,
        "business_date": business_date,
        "unknown_fail_closed": state == "UNKNOWN",
    }


def _resolve_incremental_investment_value(row: Mapping[str, Any], *, expected_edge: Mapping[str, Any]) -> dict[str, Any]:
    explicit_state = str(row.get("incremental_investment_value_state") or row.get("add_incremental_investment_value_state") or "").upper()
    if explicit_state in {"POSITIVE", "NEUTRAL", "NEGATIVE", "UNKNOWN"}:
        state = explicit_state
    elif expected_edge.get("status") == "PASS":
        state = "POSITIVE"
    else:
        state = "UNKNOWN"
    return {"status": "PASS" if state == "POSITIVE" else "FAIL_CLOSED", "state": state}


def _resolve_add_opportunity_cost(*, row: Mapping[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    explicit = str(row.get("opportunity_cost_status") or row.get("add_opportunity_cost_status") or "").upper()
    if explicit in {"PASS", "FAIL", "UNKNOWN"}:
        return {"status": "PASS" if explicit == "PASS" else "FAIL_CLOSED", "state": explicit}
    score = _finite_number(row.get("runtime_opportunity_score"))
    new_scores = [
        _finite_number(member.get("runtime_opportunity_score"))
        for member in members
        if not member.get("current_position") and str(member.get("membership_intent") or "") == "ADD_CANDIDATE"
    ]
    comparable = [value for value in new_scores if value is not None]
    if score is None:
        return {"status": "FAIL_CLOSED", "state": "UNKNOWN"}
    if comparable and max(comparable) > score:
        return {"status": "FAIL_CLOSED", "state": "NEW_BUY_SUPERIOR", "best_new_buy_score": max(comparable)}
    return {"status": "PASS", "state": "PASS", "best_new_buy_score": max(comparable) if comparable else None}


def _explicit_pass_or_unknown(row: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = str(row.get(field) or "").upper()
        if value in {"PASS", "FAIL", "UNKNOWN", "BLOCK"}:
            return "PASS" if value == "PASS" else "FAIL_CLOSED"
    return "FAIL_CLOSED"


def _explicit_pass_or_default(row: Mapping[str, Any], fields: tuple[str, ...], *, default: str) -> str:
    for field in fields:
        value = str(row.get(field) or "").upper()
        if value in {"PASS", "FAIL", "UNKNOWN", "BLOCK"}:
            return "PASS" if value == "PASS" else "FAIL_CLOSED"
    return default


def _execution_feasibility_state(row: Mapping[str, Any]) -> str:
    value = str(row.get("execution_feasibility_status") or row.get("add_execution_feasibility_status") or "").upper()
    return "BLOCK" if value == "BLOCK" else "PASS"


def _target_weight_sum_tolerance(selected_member_count: int) -> float:
    return target_weight_sum_tolerance(selected_member_count)


def resolve_portfolio_policy_allocation_authority(
    *,
    business_date: str,
    policy_config_summary: PortfolioConstructionSourceSummary,
    portfolio_policy_reference: str,
    source_hashes: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = dict(policy_config_summary.summary or {})
    target_gross_exposure_ratio = _optional_ratio(summary.get("target_gross_exposure_ratio"))
    target_gross_exposure = _optional_ratio(summary.get("target_gross_exposure", summary.get("target_gross_exposure_ratio")))
    cash_reserve_ratio = _optional_ratio(summary.get("cash_reserve_ratio"))
    cash_reserve = _optional_ratio(summary.get("cash_reserve", summary.get("cash_reserve_ratio")))
    target_member_count = _optional_int(summary.get("target_position_count", summary.get("resolved_target_member_count")))
    single_name_cap = _optional_ratio(summary.get("single_name_weight_cap"))
    source_hash = _strip_sha256(str(policy_config_summary.source_hash or ""))
    for item in source_hashes:
        if item.get("role") in {"policy_config", "portfolio_policy"} and item.get("sha256"):
            source_hash = _strip_sha256(str(item.get("sha256") or source_hash))
    reason_codes: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []
    if target_member_count is not None and target_member_count < 0:
        invalid.append("target_position_count")
    if target_gross_exposure is None:
        missing.append("target_gross_exposure")
    if cash_reserve is None:
        missing.append("cash_reserve")
    if single_name_cap is None:
        missing.append("single_name_weight_cap")
    if target_gross_exposure_ratio is not None and target_gross_exposure is not None and abs(float(target_gross_exposure_ratio) - float(target_gross_exposure)) > 0.000001:
        invalid.append("target_gross_exposure_ratio_conflict")
    if cash_reserve_ratio is not None and cash_reserve is not None and abs(float(cash_reserve_ratio) - float(cash_reserve)) > 0.000001:
        invalid.append("cash_reserve_ratio_conflict")
    if policy_config_summary.business_date != business_date:
        invalid.append("business_date_mismatch")
    if invalid:
        reason_codes.extend(f"portfolio_policy_allocation_authority_invalid:{field}" for field in invalid)
    if missing:
        reason_codes.extend(f"portfolio_policy_allocation_authority_missing:{field}" for field in missing)
    status = "BLOCK" if invalid else "REVIEW_REQUIRED" if missing else "PASS"
    if status != "PASS":
        reason_codes.append("target_weight_authority_unresolved")
    return {
        "status": status,
        "reason_codes": sorted(set(reason_codes)),
        "target_position_count": target_member_count,
        "target_gross_exposure": target_gross_exposure,
        "cash_reserve": cash_reserve,
        "single_name_weight_cap": single_name_cap,
        "deployment_posture": str(summary.get("deployment_posture") or ""),
        "source_decision_id": str(summary.get("decision_id") or summary.get("artifact_hash") or source_hash),
        "source_artifact_path": portfolio_policy_reference or policy_config_summary.source_ref,
        "source_artifact_hash": source_hash,
        "business_date": policy_config_summary.business_date,
        "review_reason": ",".join(reason_codes),
    }


def _select_target_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in members:
        score = row.get("runtime_opportunity_score")
        negative_new = isinstance(score, (int, float)) and not isinstance(score, bool) and float(score) < 0 and not row.get("current_position")
        quality_action = str(row.get("quality_action") or row.get("buy_quality_action") or "")
        quality_blocks_buy = quality_action in {"REJECT", "BUY_REJECTED", "REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED"}
        selectable = row.get("membership_intent") == "RETAIN" or (row.get("membership_intent") == "ADD_CANDIDATE" and not negative_new and not quality_blocks_buy)
        reason_codes = {str(reason) for reason in row.get("reason_codes") or []}
        occupies_buy_slot = row.get("membership_intent") in {"RETAIN", "ADD_CANDIDATE"} or any(reason.startswith("opportunity_no_buy_reason_present:") for reason in reason_codes)
        if occupies_buy_slot:
            candidates.append({**row, "_selection_selectable": selectable})
    ordered = sorted(candidates, key=lambda row: (_positive_int(row.get("construction_priority"), 999999), str(row.get("security_code") or "")))
    return [{key: value for key, value in row.items() if key != "_selection_selectable"} for row in ordered if row.get("_selection_selectable")]


def _attach_buy_quality(
    members: list[dict[str, Any]],
    buy_quality_summary: PortfolioConstructionSourceSummary | None,
) -> list[dict[str, Any]]:
    if buy_quality_summary is None or not buy_quality_summary.rows:
        return members
    decisions = {
        str(row.get("symbol") or row.get("security_code") or "").strip(): dict(row)
        for row in buy_quality_summary.rows
        if isinstance(row, Mapping) and str(row.get("symbol") or row.get("security_code") or "").strip()
    }
    updated: list[dict[str, Any]] = []
    for member in members:
        code = str(member.get("security_code") or member.get("symbol") or "").strip()
        decision = decisions.get(code)
        if not decision:
            updated.append(member)
            continue
        action = str(decision.get("quality_action") or "")
        quality_fields = _buy_quality_fields(decision, buy_quality_summary)
        reasons = list(member.get("reason_codes") or [])
        membership_intent = str(member.get("membership_intent") or "")
        weight_intent = str(member.get("weight_intent") or "")
        if not member.get("current_position") and action in {"REJECT", "BUY_REJECTED"}:
            membership_intent = "EXCLUDE"
            weight_intent = "AVOID"
            reasons.append("buy_quality_rejected")
        elif not member.get("current_position") and action in {"REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED"}:
            membership_intent = "UNRESOLVED"
            weight_intent = "UNRESOLVED"
            reasons.append("buy_quality_review_required")
        elif not member.get("current_position") and action == "REDUCED_ALLOCATION_ONLY":
            reasons.append("buy_quality_reduced_allocation_only")
        elif not member.get("current_position") and action == "FULL_ALLOCATION_ELIGIBLE":
            reasons.append("buy_quality_full_allocation_eligible")
        updated.append(
            {
                **member,
                **quality_fields,
                "membership_intent": membership_intent,
                "target_membership": membership_intent in {"RETAIN", "ADD_CANDIDATE"},
                "weight_intent": weight_intent,
                "membership_reason": ";".join(sorted(set(reasons))),
                "reason_codes": sorted(set(reasons)),
            }
        )
    return updated


def _buy_quality_fields(decision: Mapping[str, Any], summary: PortfolioConstructionSourceSummary) -> dict[str, Any]:
    return {
        "quality_decision_id": str(decision.get("quality_decision_id") or ""),
        "quality_score": decision.get("quality_score"),
        "quality_band": str(decision.get("quality_band") or ""),
        "quality_action": str(decision.get("quality_action") or ""),
        "quality_status": str(decision.get("quality_status") or ""),
        "quality_reason_codes": list(decision.get("quality_reason_codes") or []),
        "component_scores": dict(decision.get("component_scores") or {}),
        "component_statuses": dict(decision.get("component_statuses") or {}),
        "component_weights": dict(decision.get("component_weights") or {}),
        "quality_policy_version": str(decision.get("policy_version") or ""),
        "quality_allocation_adjustment": decision.get("quality_allocation_adjustment"),
        "source_candidate_id": str(decision.get("source_candidate_id") or ""),
        "source_opportunity_id": str(decision.get("source_opportunity_id") or ""),
        "buy_quality_artifact_path": summary.source_ref,
        "buy_quality_artifact_hash": _strip_sha256(summary.source_hash),
        "buy_quality_authority": {
            "authority_type": "ADAPTIVE_BUY_QUALITY_AUTHORITY",
            "producer": "Production Strategy BUY Quality Resolver",
            "policy_version": str(decision.get("policy_version") or ""),
            "quality_decision_id": str(decision.get("quality_decision_id") or ""),
            "quality_action": str(decision.get("quality_action") or ""),
            "quality_score": decision.get("quality_score"),
            "source_artifact_path": summary.source_ref,
            "source_artifact_hash": _strip_sha256(summary.source_hash),
            "PIT_status": str(decision.get("PIT_status") or ""),
            "future_information_used": bool(decision.get("future_information_used")),
            "historical_result_input_used": bool(decision.get("historical_result_input_used")),
            "paper_ledger_input_used": bool(decision.get("paper_ledger_input_used")),
        },
    }


def _validate_member(member: Any, *, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(member, dict):
        return [f"portfolio_member_not_object:{index}"]
    required = {
        "member_id",
        "security_code",
        "symbol",
        "current_position",
        "membership_intent",
        "target_membership",
        "target_weight",
        "target_weight_authority",
        "target_weight_resolution",
        "construction_priority",
        "weight_intent",
        "candidate_reference",
        "opportunity_reference",
        "position_management_reference",
        "portfolio_policy_reference",
        "membership_reason",
        "weight_reason",
        "confidence",
        "uncertainty",
        "reason_codes",
    }
    errors.extend(f"portfolio_member_required_field_missing:{index}:{field}" for field in sorted(required - set(member)))
    if not member.get("security_code"):
        errors.append(f"security_code_empty:{index}")
    if member.get("symbol") != member.get("security_code"):
        errors.append(f"symbol_security_code_mismatch:{index}")
    if not isinstance(member.get("target_membership"), bool):
        errors.append(f"invalid_target_membership:{index}")
    target_weight = member.get("target_weight")
    if isinstance(target_weight, bool) or not isinstance(target_weight, (int, float)) or not math.isfinite(float(target_weight)) or not 0 <= float(target_weight) <= 1:
        errors.append(f"invalid_target_weight:{index}")
    if not isinstance(member.get("target_weight_authority"), dict):
        errors.append(f"invalid_target_weight_authority:{index}")
    if not isinstance(member.get("target_weight_resolution"), dict):
        errors.append(f"invalid_target_weight_resolution:{index}")
    else:
        resolution = member.get("target_weight_resolution") or {}
        if resolution.get("status") not in {"PASS", "REVIEW_REQUIRED"}:
            errors.append(f"invalid_target_weight_resolution_status:{index}")
        resolved = resolution.get("resolved_weight")
        if (
            resolution.get("status") == "PASS"
            and (isinstance(resolved, bool) or not isinstance(resolved, (int, float)) or abs(float(target_weight or 0.0) - float(resolved)) > 0.000001)
        ):
            errors.append(f"target_weight_resolution_mismatch:{index}")
        if float(target_weight or 0.0) == 0.0 and not resolution.get("zero_weight_reason") and resolution.get("status") == "PASS":
            errors.append(f"missing_zero_weight_reason:{index}")
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
    if "runtime_opportunity_score" in member:
        score = member.get("runtime_opportunity_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            errors.append(f"invalid_runtime_opportunity_score:{index}")
        authority = member.get("runtime_opportunity_score_authority")
        if not isinstance(authority, dict):
            errors.append(f"missing_runtime_opportunity_score_authority:{index}")
        elif authority.get("prediction_semantics") != "runtime_opportunity_score":
            errors.append(f"invalid_runtime_opportunity_score_semantics:{index}")
    if "allocation_quality_score" in member:
        score = member.get("allocation_quality_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0 <= float(score) <= 1:
            errors.append(f"invalid_allocation_quality_score:{index}")
        authority = member.get("allocation_quality_authority")
        if not isinstance(authority, dict):
            errors.append(f"missing_allocation_quality_authority:{index}")
        elif authority.get("output_semantics") != "allocation_quality_score":
            errors.append(f"invalid_allocation_quality_semantics:{index}")
    if "quality_score" in member:
        score = member.get("quality_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0 <= float(score) <= 1:
            errors.append(f"invalid_buy_quality_score:{index}")
        authority = member.get("buy_quality_authority")
        if not isinstance(authority, dict) or authority.get("authority_type") != "ADAPTIVE_BUY_QUALITY_AUTHORITY":
            errors.append(f"legacy_quality_score_forbidden:{index}")
    if "quality_score_authority" in member:
        errors.append(f"legacy_quality_score_authority_forbidden:{index}")
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
    value = row.get("canonical_opportunity_buy_rank", row.get("opportunity_buy_rank", row.get("buy_rank", row.get("rank", row.get("opportunity_rank", 999999)))))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 999999


def _canonical_opportunity_rank(row: Mapping[str, Any]) -> int | None:
    if not row:
        return None
    value = row.get("canonical_opportunity_buy_rank", row.get("opportunity_buy_rank", row.get("buy_rank")))
    if value in (None, "") and not row.get("rank_authority_status"):
        value = row.get("opportunity_rank", row.get("rank"))
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _opportunity_rank_authority_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    if not row:
        return {
            "input_opportunity_rank_authority": "",
            "input_opportunity_rank_source_path": "",
            "input_opportunity_rank_source_hash": "",
            "input_opportunity_row_id": "",
            "input_opportunity_row_authority_hash": "",
        }
    rank = _canonical_opportunity_rank(row)
    source_path = str(row.get("rank_authority_source_path") or row.get("source_artifact_path") or row.get("source_ref") or "")
    source_hash = str(row.get("rank_authority_source_hash") or row.get("source_artifact_hash") or row.get("artifact_hash") or row.get("source_hash") or "")
    row_id = str(row.get("rank_authority_row_id") or row.get("opportunity_id") or row.get("row_id") or "")
    row_hash = str(row.get("rank_authority_row_hash") or row.get("row_authority_hash") or row.get("source_row_hash") or "")
    status = str(row.get("rank_authority_status") or ("PASS" if rank is not None else "REVIEW_REQUIRED"))
    authority = str(row.get("rank_authority") or "OPPORTUNITY_BUY_RANK_AUTHORITY")
    reason = str(row.get("rank_authority_reason") or ("" if rank is not None else "opportunity_rank_authority_missing_or_invalid"))
    return {
        "opportunity_buy_rank": rank,
        "opportunity_row_id": row_id,
        "opportunity_row_authority_hash": row_hash,
        "opportunity_artifact_path": source_path,
        "opportunity_artifact_hash": source_hash,
        "input_opportunity_rank_authority": authority if rank is not None and status == "PASS" else "",
        "input_opportunity_rank_source_path": source_path,
        "input_opportunity_rank_source_hash": source_hash,
        "input_opportunity_row_id": row_id,
        "input_opportunity_row_authority_hash": row_hash,
        "rank_authority_status": status,
        "rank_authority": authority,
        "rank_authority_field": str(row.get("rank_authority_field") or "buy_rank"),
        "rank_authority_reason": reason,
    }


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


def _optional_ratio(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    numeric = float(value)
    if not 0 <= numeric <= 1:
        return None
    return numeric


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return default
    return value


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return numeric


def _score_source_field(row: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    for key in fields:
        value = row.get(key)
        if _finite_number(value) is not None:
            return key
    return ""


def _score_authority_payload(
    *,
    business_date: str,
    candidate: Mapping[str, Any] | None,
    opportunity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if opportunity:
        source_field = _score_source_field(opportunity, ("expected_edge_score", "opportunity_score", "score"))
        if source_field:
            score = _finite_number(opportunity.get(source_field))
            if score is not None:
                payload["runtime_opportunity_score"] = round(score, 8)
                payload["runtime_opportunity_score_authority"] = {
                    "authority": "OPPORTUNITY_RANKING_AUTHORITY",
                    "canonical_field": "runtime_opportunity_score",
                    "source_field": source_field,
                    "source_decision_id": str(opportunity.get("opportunity_id") or opportunity.get("source_ref") or ""),
                    "source_artifact_class": "opportunity",
                    "source_artifact_path": str(opportunity.get("source_artifact_path") or ""),
                    "source_artifact_hash": str(opportunity.get("source_artifact_hash") or ""),
                    "candidate_reference": str((candidate or {}).get("candidate_id") or (candidate or {}).get("source_ref") or ""),
                    "opportunity_reference": str(opportunity.get("opportunity_id") or opportunity.get("source_ref") or ""),
                    "prediction_semantics": str(opportunity.get("prediction_semantics") or "runtime_opportunity_score"),
                    "transformation_stage": str(opportunity.get("transformation_stage") or "accepted_generation_bound_imputer_scaler_model"),
                    "calibration_applied": bool(opportunity.get("calibration_applied")) if "calibration_applied" in opportunity else False,
                    "population_scope": str(opportunity.get("population_scope") or "CandidateTopN_single_business_day"),
                    "business_date": business_date,
                }
    quality_source = opportunity or candidate or {}
    quality_field = _score_source_field(quality_source, ("allocation_quality_score",))
    if quality_field:
        quality = _finite_number(quality_source.get(quality_field))
        if quality is not None:
            payload["allocation_quality_score"] = round(quality, 8)
            payload["allocation_quality_authority"] = {
                "authority": "ALLOCATION_QUALITY_AUTHORITY",
                "canonical_field": "allocation_quality_score",
                "source_field": quality_field,
                "source_decision_id": str((opportunity or {}).get("opportunity_id") or (candidate or {}).get("candidate_id") or ""),
                "source_artifact_class": "opportunity" if opportunity else ("candidate" if candidate else ""),
                "candidate_reference": str((candidate or {}).get("candidate_id") or (candidate or {}).get("source_ref") or ""),
                "opportunity_reference": str((opportunity or {}).get("opportunity_id") or (opportunity or {}).get("source_ref") or ""),
                "input_semantics": str(quality_source.get("allocation_quality_input_semantics") or "allocation_quality_score"),
                "output_semantics": "allocation_quality_score",
                "output_range_contract": "[0,1]",
                "business_date": business_date,
                "pit_status": "PIT",
            }
    return payload


def _add_allocation_evidence_payload(
    *,
    opportunity: Mapping[str, Any] | None,
    pm: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    sources = (opportunity or {}, pm or {}, current or {})
    for field in (
        "expected_edge_baseline_score",
        "expected_edge_current_score",
        "expected_edge_baseline_business_date",
        "previous_expected_edge_business_date",
        "entry_expected_edge_baseline_business_date",
        "add_expected_edge_baseline_business_date",
        "expected_edge_baseline_campaign_id",
        "previous_expected_edge_score",
        "entry_expected_edge_baseline_score",
        "expected_edge_baseline_type",
        "expected_edge_improvement_state",
        "add_expected_edge_improvement_state",
        "stable_adequate_opportunity_cost_superior",
        "incremental_investment_value_state",
        "add_incremental_investment_value_state",
        "opportunity_cost_status",
        "add_opportunity_cost_status",
        "campaign_continuation_status",
        "add_campaign_continuation_status",
        "no_loss_averaging_status",
        "add_no_loss_averaging_status",
        "concentration_status",
        "add_concentration_status",
        "capital_availability_status",
        "add_capital_availability_status",
        "execution_feasibility_status",
        "add_execution_feasibility_status",
        "position_campaign_id",
        "campaign_id",
    ):
        for source in sources:
            if field in source:
                payload[field] = source.get(field)
                break
    return payload


def _current_position_weight_payload(*, current_row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not current_row:
        return {}
    current_weight = _optional_ratio(current_row.get("current_weight", current_row.get("weight")))
    if current_weight is None:
        market_value = _finite_number(current_row.get("market_value", current_row.get("value", current_row.get("current_notional"))))
        total_equity = _finite_number(current_row.get("portfolio_total_equity", current_row.get("portfolio_value")))
        if market_value is not None and total_equity is not None and total_equity > 0:
            current_weight = market_value / total_equity
    payload: dict[str, Any] = {}
    if current_weight is not None and 0 <= current_weight <= 1:
        payload["current_weight"] = round(current_weight, TARGET_WEIGHT_DECIMALS)
    if "quantity" in current_row or "current_quantity" in current_row:
        quantity = _finite_number(current_row.get("current_quantity", current_row.get("quantity")))
        if quantity is not None and quantity >= 0:
            payload["current_quantity"] = int(quantity)
    return payload


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
