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
from ai_fund_lab_v2.strategy import strategy_intelligence
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
PRODUCTION_ARTIFACT_LIFECYCLE_STATUS = "ACCEPTED"
PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY = "ELIGIBLE"
MEMBERSHIP_INTENTS = {"RETAIN", "ADD_CANDIDATE", "REDUCE_CANDIDATE", "REMOVE_CANDIDATE", "EXCLUDE", "UNRESOLVED"}
WEIGHT_INTENTS = {"INCREASE", "MAINTAIN", "DECREASE", "REMOVE", "AVOID", "UNRESOLVED"}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
BROKER_ELIGIBILITY_GATING_OWNER = "PORTFOLIO_CONSTRUCTION"
BROKER_ELIGIBILITY_AUTHORITY_TYPE = "BROKER_PRODUCT_CLASSIFICATION_EXECUTION_ELIGIBILITY"
LOT_AWARE_REALLOCATION_AUTHORITY_TYPE = "PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION"
LOW_PRICE_RISK_ALLOCATION_AUTHORITY_TYPE = "PORTFOLIO_CONSTRUCTION_LOW_PRICE_RISK_ALLOCATION_AUTHORITY"
SEMANTIC_REENTRY_AUTHORITY_TYPE = "PORTFOLIO_CONSTRUCTION_SEMANTIC_REENTRY_AUTHORITY"
REENTRY_COOLDOWN_BUSINESS_DAYS = 3
DEFAULT_MINIMUM_TICK = 1.0
LIQUIDITY_CAPACITY_TARGET_PARTICIPATION = 0.01
PRICE_TICK_RISK_CAPS = {
    "WATCH": 0.12,
    "ELEVATED": 0.10,
    "SEVERE": 0.08,
    "EXTREME": 0.05,
}
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
OPPORTUNITY_RELATIVE_METADATA_NO_BUY_REASONS = {"non_positive_expected_edge_score", "below_opportunity_top20"}
OPPORTUNITY_HARD_NO_BUY_REASONS = {
    "high_downside_risk_score",
    "corporate_event_block",
    "corporate_action_block",
    "liquidity_block",
    "not_currently_listed",
    "unsupported_broker_product_category",
    "broker_product_category_unsupported",
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
    strategy_intelligence_artifact_path: Path | str | None = None,
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
        strategy_intelligence_artifact_path=strategy_intelligence_artifact_path,
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
    strategy_intelligence_artifact_path: Path | str | None = None,
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
    si_result = strategy_intelligence.validate_strategy_intelligence_compatibility(
        strategy_intelligence_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )

    source_status = "VALID"
    reason_codes: list[str] = []
    upstream_statuses = [market_result["status"], corporate_result["status"], policy_result["status"], pm_result["status"]]
    if strategy_intelligence_artifact_path is not None:
        upstream_statuses.append(si_result["status"])
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
        opportunity_score_summary=opportunity_summary.summary or {},
        current_rows=current_portfolio_summary.rows,
        pm_rows=_pm_rows(position_management_artifact_path),
    )
    members = _attach_buy_quality(members, buy_quality_summary)
    members, si_reasons = _attach_strategy_intelligence(
        members,
        strategy_intelligence_artifact_path=strategy_intelligence_artifact_path,
        business_date=business_date,
    )
    reason_codes.extend(si_reasons)
    members, broker_eligibility_reasons = _apply_broker_eligibility_to_new_exposure(members)
    reason_codes.extend(reconciliation_reasons)
    reason_codes.extend(broker_eligibility_reasons)
    weight_contract = _resolve_target_weight_contract(
        business_date=business_date,
        members=members,
        policy_config_summary=policy_config_summary,
        current_portfolio_summary=current_portfolio_summary,
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
                si_result.get("feature_date"),
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
            si_result.get("feature_date", ""),
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
        {"role": "strategy_intelligence", "path": str(strategy_intelligence_artifact_path or ""), "required": strategy_intelligence_artifact_path is not None, "status": si_result["status"]},
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
        *(
            [{"role": "strategy_intelligence", "path": str(strategy_intelligence_artifact_path), "sha256": sha256_file(Path(strategy_intelligence_artifact_path))}]
            if strategy_intelligence_artifact_path and Path(strategy_intelligence_artifact_path).is_file()
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
        "strategy_intelligence": si_result,
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
        "strategy_intelligence_status": si_result["status"],
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
    production_ready = (
        payload.get("producer_result_status") == "PASS"
        and payload.get("artifact_lifecycle_status") == PRODUCTION_ARTIFACT_LIFECYCLE_STATUS
        and payload.get("runtime_consumer_eligibility") == PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY
    )
    if production_ready:
        for field in ("position_sizing_decided", "quantity_decided", "runtime_switch_performed"):
            if payload.get(field) is not False:
                errors.append(f"phase30_s_field_must_remain_false:{field}")
        if payload.get("allocation_decided") is not True:
            errors.append("phase30_s_allocation_decided_required_for_production")
        if payload.get("production_consumer_connected") is not True:
            errors.append("phase30_s_production_consumer_connected_required")
        if payload.get("legacy_authority_active") is not False:
            errors.append("phase30_s_legacy_authority_must_be_inactive_for_production")
    else:
        if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
            errors.append("phase22_e_artifact_lifecycle_must_be_draft_or_phase30_s_production_ready")
        if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
            errors.append("phase22_e_runtime_consumer_eligibility_must_be_not_eligible_or_phase30_s_production_ready")
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
        if payload.get("runtime_consumer_eligibility") == PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY and payload.get("allocation_decided") is True:
            return payload
        raise PortfolioConstructionConsumerError("Portfolio Construction artifact is not production-consumable")
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise PortfolioConstructionConsumerError("Phase22-E Portfolio Construction must remain NOT_ELIGIBLE")
    return payload


def promote_final_portfolio_construction_for_production(payload: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(payload)
    reason_codes = sorted(set(str(item) for item in updated.get("reason_codes") or [] if str(item)))
    producer_status = str(updated.get("producer_result_status") or "")
    reallocation = updated.get("lot_aware_final_reallocation") if isinstance(updated.get("lot_aware_final_reallocation"), dict) else {}
    production_ready = producer_status == "PASS" and str(reallocation.get("status") or "") == "PASS"
    lifecycle = PRODUCTION_ARTIFACT_LIFECYCLE_STATUS if production_ready else ARTIFACT_LIFECYCLE_STATUS
    consumer = PRODUCTION_RUNTIME_CONSUMER_ELIGIBILITY if production_ready else RUNTIME_CONSUMER_ELIGIBILITY
    updated.update(
        {
            "artifact_lifecycle_status": lifecycle,
            "runtime_consumer_eligibility": consumer,
            "allocation_decided": production_ready,
            "quantity_decided": False,
            "production_consumer_connected": production_ready,
            "runtime_switch_performed": False,
            "legacy_authority_active": not production_ready,
        }
    )
    updated.update(
        status_contract_fields(
            producer_result_status=producer_status,
            artifact_lifecycle_status=lifecycle,
            runtime_consumer_eligibility=consumer,
            reason_codes=reason_codes,
            decision_resolution="RESOLVED" if producer_status == "PASS" else "UNRESOLVED",
        )
    )
    return updated


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
    opportunity_score_summary: Mapping[str, Any],
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
                opportunity_score_summary=opportunity_score_summary,
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
        no_buy_classification = _classify_opportunity_no_buy_reason(
            no_buy_reason,
            score_contract=_opportunity_score_semantic_contract(row=row, summary=opportunity_score_summary),
        )
        no_buy_blocked = bool(no_buy_classification["blocks_buy"])
        eligible = _candidate_eligible(candidate or row) and not no_buy_blocked
        membership_intent = "ADD_CANDIDATE" if eligible else "EXCLUDE"
        weight_intent = "INCREASE" if eligible else "AVOID"
        eligibility_reason = (
            f"opportunity_no_buy_reason_hard_block:{no_buy_reason}"
            if no_buy_blocked
            else "candidate_eligible"
            if eligible
            else "candidate_ineligible"
        )
        eligibility_reasons = ["opportunity_rank_preserved", eligibility_reason]
        if no_buy_blocked:
            eligibility_reasons.append(f"opportunity_no_buy_reason_present:{no_buy_reason}")
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
                reason_codes=eligibility_reasons,
                no_buy_reason_classification=no_buy_classification,
                opportunity_score_summary=opportunity_score_summary,
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
                opportunity_score_summary=opportunity_score_summary,
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
    no_buy_reason_classification: Mapping[str, Any] | None = None,
    opportunity_score_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    broker_listed_info = _broker_listed_info_payload(security_code, opportunity, candidate, current, pm)
    classification = dict(no_buy_reason_classification or _classify_opportunity_no_buy_reason("", score_contract={}))
    canonical_pm_campaign_id = _canonical_campaign_identity(pm or {})
    canonical_current_campaign_id = _first_nonempty(
        _canonical_campaign_identity(current or {}),
        canonical_pm_campaign_id,
    )
    target_member_eligibility = {
        "status": "PASS" if membership_intent in {"RETAIN", "ADD_CANDIDATE"} else "BLOCKED",
        "reason": "target_member_competition_eligible" if membership_intent in {"RETAIN", "ADD_CANDIDATE"} else "not_target_member_eligible",
        "hard_blocking_reasons": list(classification.get("hard_blocking_reasons") or []),
        "soft_relative_reasons": list(classification.get("soft_relative_reasons") or []),
    }
    if classification.get("status") == "REVIEW_REQUIRED":
        target_member_eligibility = {
            **target_member_eligibility,
            "status": "BLOCKED",
            "reason": str(classification.get("review_reason") or "semantic_metadata_missing"),
        }
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
        "current_position_campaign_id": canonical_current_campaign_id,
        "pm_position_campaign_id": canonical_pm_campaign_id,
        "opportunity_position_campaign_id": str((opportunity or {}).get("position_campaign_id") or (opportunity or {}).get("campaign_id") or ""),
        "portfolio_policy_reference": "",
        "input_candidate_order": _candidate_order(candidate or {}),
        "input_opportunity_rank": _canonical_opportunity_rank(opportunity or {}),
        **_opportunity_rank_authority_payload(opportunity or {}),
        "input_score": _score(opportunity or candidate or {}),
        **_score_authority_payload(
            business_date=business_date,
            candidate=candidate,
            opportunity=opportunity,
            opportunity_score_summary=opportunity_score_summary or {},
        ),
        "no_buy_reason_classification": classification,
        "target_member_eligibility": target_member_eligibility,
        **_phase29_l16_observable_fields(opportunity, candidate, current, pm),
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


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _canonical_campaign_identity(row: Mapping[str, Any]) -> str:
    for field in ("position_campaign_id", "campaign_id", "strategy_intelligence_campaign_id"):
        value = str(row.get(field) or "").strip()
        if value and not value.startswith("runtime-current-"):
            return value
    return ""


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


def _phase29_l16_observable_fields(*rows: Mapping[str, Any] | None) -> dict[str, Any]:
    fields = (
        "reference_price",
        "reference_price_authority",
        "reference_price_resolution",
        "reference_price_type",
        "reference_price_date",
        "minimum_tick",
        "rolling_median_traded_value_20",
        "rolling_median_traded_value_20_authority",
        "rolling_median_traded_value_20_resolution",
        "price_momentum_return_20d",
        "trend_close_over_ma_20d",
        "prior_exit_business_date",
        "prior_exit_reason",
        "prior_exit_reason_codes",
        "prior_same_symbol_exit_count",
        "last_exit_business_date",
        "last_exit_reason",
        "previous_exit_business_date",
        "previous_exit_reason",
        "previous_exit_reason_codes",
        "current_quantity",
        "corporate_action_status",
        "corporate_event_status",
        "corporate_action_blocking_status",
        "corporate_event_blocking_status",
    )
    payload: dict[str, Any] = {}
    for field in fields:
        for row in rows:
            if row and row.get(field) not in (None, ""):
                payload[field] = row.get(field)
                break
    return payload


def _resolve_low_price_reentry_allocation_guard(
    *,
    row: Mapping[str, Any],
    business_date: str,
    normal_target_weight: float,
    target_membership: bool,
    target_weight_reason: str,
    zero_weight_reason: str,
    review_reason: str,
    portfolio_equity: float | None,
) -> dict[str, Any]:
    current_position = bool(row.get("current_position"))
    pm_action = str(row.get("pm_action") or "").upper()
    membership = str(row.get("membership_intent") or "").upper()
    current_weight = _optional_ratio(row.get("current_weight")) or 0.0
    is_buy_add = current_position and pm_action == "ADD"
    is_buy_new = (not current_position) and membership == "ADD_CANDIDATE"
    is_buy_side_allocation = is_buy_new or is_buy_add
    reference_price = _positive_number_from_row(row, ("reference_price", "close", "Close", "C", "AdjC", "price"))
    minimum_tick = _positive_number_from_row(row, ("minimum_tick", "tick_size", "price_tick")) or DEFAULT_MINIMUM_TICK
    single_tick_pct = round(minimum_tick / reference_price, 8) if reference_price and minimum_tick > 0 else None
    price_tier = _price_tick_risk_tier(single_tick_pct)
    price_tick_cap = PRICE_TICK_RISK_CAPS.get(price_tier)
    rolling_value = _positive_number_from_row(
        row,
        (
            "rolling_median_traded_value_20",
            "rolling_median_va_20",
            "liquidity_rolling_median_traded_value_20",
            "traded_value_median_20d",
            "rolling_median_turnover_value_20",
        ),
    )
    rolling_source_field = _positive_number_source_field(
        row,
        (
            "rolling_median_traded_value_20",
            "rolling_median_va_20",
            "liquidity_rolling_median_traded_value_20",
            "traded_value_median_20d",
            "rolling_median_turnover_value_20",
        ),
    )
    proposed_notional = (
        round(max(normal_target_weight, 0.0) * portfolio_equity, 2)
        if portfolio_equity is not None and normal_target_weight >= 0
        else None
    )
    capacity_ratio = (
        round(proposed_notional / rolling_value, 8)
        if proposed_notional is not None and rolling_value and rolling_value > 0
        else None
    )
    liquidity_status = _liquidity_capacity_status(capacity_ratio)
    liquidity_cap = (
        round((rolling_value * LIQUIDITY_CAPACITY_TARGET_PARTICIPATION) / portfolio_equity, TARGET_WEIGHT_DECIMALS)
        if rolling_value and portfolio_equity and portfolio_equity > 0
        else None
    )
    semantic_buy = _semantic_reentry_evidence(row=row, business_date=business_date, is_buy_new=is_buy_new)
    recovery = _reentry_recovery_evidence(row=row, semantic=semantic_buy, capacity_ratio=capacity_ratio, liquidity_status=liquidity_status)

    final_weight = round(float(normal_target_weight or 0.0), TARGET_WEIGHT_DECIMALS)
    final_membership = bool(target_membership)
    reason = target_weight_reason
    zero_reason = zero_weight_reason
    review = review_reason
    cap_reason = "NONE"
    reason_code = ""
    member_reason_code = ""
    adjustments: list[dict[str, Any]] = []

    if is_buy_new and semantic_buy["semantic_buy_type"] == "REENTRY":
        if semantic_buy["reentry_cooldown_status"] != "PASS":
            final_weight = 0.0
            final_membership = False
            reason = "semantic_reentry_cooldown_blocked"
            zero_reason = "reentry_minimum_cooldown_not_satisfied"
            review = ""
            reason_code = "semantic_reentry_cooldown_blocked"
            member_reason_code = "reentry_minimum_cooldown_not_satisfied"
        elif recovery["reentry_recovery_status"] != "PASS":
            final_weight = 0.0
            final_membership = False
            reason = "semantic_reentry_recovery_hurdle_not_satisfied"
            zero_reason = str(recovery["reentry_recovery_reason"])
            review = "" if recovery["reentry_recovery_status"] == "FAIL_CLOSED" else str(recovery["reentry_recovery_reason"])
            reason_code = "semantic_reentry_recovery_blocked"
            member_reason_code = str(recovery["reentry_recovery_reason"])

    low_price_guard_active = is_buy_side_allocation and price_tier in PRICE_TICK_RISK_CAPS and final_weight > 0
    if low_price_guard_active and rolling_value is None:
        final_weight = current_weight if is_buy_add else 0.0
        final_membership = bool(row.get("target_membership")) if is_buy_add else False
        reason = "low_price_liquidity_evidence_missing_fail_closed"
        zero_reason = "" if is_buy_add else "low_price_liquidity_evidence_missing_fail_closed"
        review = "low_price_liquidity_evidence_missing_fail_closed"
        cap_reason = "low_price_liquidity_evidence_missing_fail_closed"
        reason_code = reason_code or "low_price_liquidity_evidence_missing_fail_closed"
        member_reason_code = member_reason_code or "low_price_liquidity_evidence_missing_fail_closed"
    elif is_buy_side_allocation and final_weight > 0:
        caps = [final_weight]
        if price_tick_cap is not None:
            caps.append(price_tick_cap)
        if liquidity_cap is not None:
            caps.append(liquidity_cap)
        capped_weight = round(min(caps), TARGET_WEIGHT_DECIMALS)
        if is_buy_add:
            capped_weight = round(max(capped_weight, current_weight), TARGET_WEIGHT_DECIMALS)
        if capped_weight < final_weight:
            cap_reason = _allocation_cap_reason(
                normal_target_weight=final_weight,
                capped_weight=capped_weight,
                price_tick_cap=price_tick_cap,
                liquidity_cap=liquidity_cap,
            )
            final_weight = capped_weight
            reason = "low_price_risk_allocation_cap_applied"
            reason_code = reason_code or "low_price_risk_allocation_cap_applied"
            member_reason_code = member_reason_code or cap_reason

    if final_weight != round(float(normal_target_weight or 0.0), TARGET_WEIGHT_DECIMALS) or member_reason_code:
        adjustments.append(
            {
                "authority": LOW_PRICE_RISK_ALLOCATION_AUTHORITY_TYPE,
                "semantic_buy_type": semantic_buy["semantic_buy_type"],
                "normal_target_weight": round(float(normal_target_weight or 0.0), TARGET_WEIGHT_DECIMALS),
                "final_risk_adjusted_target_weight": final_weight,
                "price_tick_risk_tier": price_tier,
                "liquidity_capacity_status": liquidity_status,
                "allocation_cap_reason": cap_reason,
            }
        )

    member_fields = {
        **semantic_buy,
        **recovery,
        "single_tick_pct": single_tick_pct,
        "price_tick_risk_tier": price_tier,
        "rolling_median_traded_value_20": rolling_value,
        "rolling_median_traded_value_20_authority": row.get("rolling_median_traded_value_20_authority") or {},
        "rolling_median_traded_value_20_resolution": row.get("rolling_median_traded_value_20_resolution") or {},
        "capacity_source": str(row.get("technical_recovery_source") or row.get("capacity_source") or ""),
        "capacity_source_field": rolling_source_field or "",
        "capacity_ratio": capacity_ratio,
        "liquidity_capacity_status": liquidity_status,
        "normal_target_weight": round(float(normal_target_weight or 0.0), TARGET_WEIGHT_DECIMALS),
        "price_tick_cap_weight": price_tick_cap,
        "liquidity_capacity_cap_weight": liquidity_cap,
        "final_risk_adjusted_target_weight": final_weight,
        "allocation_cap_reason": cap_reason,
    }
    return {
        "target_weight": final_weight,
        "target_membership": final_membership,
        "target_weight_reason": reason,
        "zero_weight_reason": zero_reason,
        "review_reason": review,
        "reason_code": reason_code,
        "member_reason_code": member_reason_code,
        "cap_applied": final_weight < round(float(normal_target_weight or 0.0), TARGET_WEIGHT_DECIMALS),
        "adjustments": adjustments,
        "member_fields": member_fields,
        "low_price_risk_allocation_authority": {
            "authority_type": LOW_PRICE_RISK_ALLOCATION_AUTHORITY_TYPE,
            "business_date": business_date,
            "portfolio_equity_source": "current_portfolio_summary",
            "current_authoritative_portfolio_equity": portfolio_equity,
            "minimum_tick": minimum_tick,
            "single_tick_pct": single_tick_pct,
            "price_tick_risk_tier": price_tier,
            "price_tick_cap_weight": price_tick_cap,
            "rolling_median_traded_value_20": rolling_value,
            "rolling_median_traded_value_20_authority": row.get("rolling_median_traded_value_20_authority") or {},
            "rolling_median_traded_value_20_resolution": row.get("rolling_median_traded_value_20_resolution") or {},
            "capacity_source": str(row.get("technical_recovery_source") or row.get("capacity_source") or ""),
            "capacity_source_field": rolling_source_field or "",
            "capacity_ratio": capacity_ratio,
            "liquidity_capacity_status": liquidity_status,
            "liquidity_capacity_target_participation": LIQUIDITY_CAPACITY_TARGET_PARTICIPATION,
            "liquidity_capacity_cap_weight": liquidity_cap,
            "status": "PASS" if not review or review != "low_price_liquidity_evidence_missing_fail_closed" else "REVIEW_REQUIRED",
        },
        "semantic_reentry_authority": {
            "authority_type": SEMANTIC_REENTRY_AUTHORITY_TYPE,
            "business_date": business_date,
            **semantic_buy,
            **recovery,
        },
    }


def _semantic_reentry_evidence(*, row: Mapping[str, Any], business_date: str, is_buy_new: bool) -> dict[str, Any]:
    pm_action = str(row.get("pm_action") or "").upper()
    if bool(row.get("current_position")):
        return {
            "semantic_buy_type": "BUY_ADD" if pm_action == "ADD" else "NOT_APPLICABLE",
            "prior_exit_business_date": "",
            "business_days_since_exit": None,
            "reentry_cooldown_threshold_bd": REENTRY_COOLDOWN_BUSINESS_DAYS,
            "reentry_cooldown_status": "NOT_APPLICABLE",
        }
    prior_exit = _prior_exit_business_date(row)
    if not prior_exit or prior_exit >= business_date:
        return {
            "semantic_buy_type": "BUY_NEW",
            "prior_exit_business_date": "",
            "business_days_since_exit": None,
            "reentry_cooldown_threshold_bd": REENTRY_COOLDOWN_BUSINESS_DAYS,
            "reentry_cooldown_status": "NOT_APPLICABLE",
        }
    days_since_exit = _completed_business_days_between(prior_exit, business_date)
    status = "PASS" if days_since_exit >= REENTRY_COOLDOWN_BUSINESS_DAYS else "FAIL_CLOSED"
    return {
        "semantic_buy_type": "REENTRY",
        "prior_exit_business_date": prior_exit,
        "business_days_since_exit": days_since_exit,
        "reentry_cooldown_threshold_bd": REENTRY_COOLDOWN_BUSINESS_DAYS,
        "reentry_cooldown_status": status,
    }


def _reentry_recovery_evidence(*, row: Mapping[str, Any], semantic: Mapping[str, Any], capacity_ratio: float | None, liquidity_status: str) -> dict[str, Any]:
    rank = _canonical_opportunity_rank(row)
    edge = _finite_number(row.get("runtime_opportunity_score", row.get("expected_edge_score", row.get("score"))))
    quality_action = str(row.get("quality_action") or row.get("buy_quality_action") or "")
    trend = _finite_number(row.get("trend_close_over_ma_20d"))
    momentum = _finite_number(row.get("price_momentum_return_20d"))
    entry_evidence = row.get("entry_admission") if isinstance(row.get("entry_admission"), Mapping) else {}
    entry_state = str(row.get("entry_admission_state") or entry_evidence.get("entry_state") or "").upper()
    entry_action = str(row.get("entry_admission_action") or entry_evidence.get("admission_action") or "").upper()
    entry_sufficiency = str(row.get("entry_admission_evidence_sufficiency") or entry_evidence.get("evidence_sufficiency") or "").upper()
    cq_status = str(
        row.get("strategy_intelligence_continuation_quality_status")
        or row.get("continuation_quality_status")
        or row.get("cq_status")
        or ""
    ).upper()
    downside_status = str(row.get("strategy_intelligence_downside_risk_status") or row.get("downside_risk_status") or "").upper()
    prior_exit_count = int(_finite_number(row.get("prior_same_symbol_exit_count") or row.get("prior_closed_campaign_count")) or 0)
    ca_evidence = _corporate_action_evidence(row)
    ca_status = ca_evidence["status"]
    previous_exit_reason = _previous_exit_reason(row)
    previous_exit_reason_class = _previous_exit_reason_class(previous_exit_reason, row.get("prior_exit_reason_codes") or row.get("previous_exit_reason_codes") or row.get("source_pm_reason_codes"))
    base = {
        "reentry_recovery_status": "NOT_APPLICABLE",
        "reentry_recovery_reason": "not_reentry",
        "reentry_rank": rank,
        "reentry_expected_edge": edge,
        "reentry_score_gate_status": "DIAGNOSTIC_ONLY",
        "reentry_opportunity_qualification_status": "NOT_APPLICABLE",
        "reentry_buy_quality_action": quality_action,
        "reentry_trend_close_over_ma_20d": trend,
        "reentry_price_momentum_return_20d": momentum,
        "reentry_corporate_action_status": ca_status,
        "reentry_corporate_action_source_status": ca_evidence["source_status"],
        "reentry_corporate_action_source": ca_evidence["source"],
        "previous_exit_reason": previous_exit_reason,
        "previous_exit_reason_class": previous_exit_reason_class,
        "reentry_trend_recovery_status": "NOT_APPLICABLE",
        "reentry_momentum_recovery_status": "NOT_APPLICABLE",
        "reentry_entry_admission_state": entry_state,
        "reentry_entry_admission_action": entry_action,
        "reentry_entry_admission_status": "NOT_APPLICABLE",
        "reentry_continuation_quality_status": cq_status,
        "reentry_downside_risk_status": downside_status,
        "prior_same_symbol_exit_count": prior_exit_count,
        "reentry_capacity_status": liquidity_status,
    }
    if semantic.get("semantic_buy_type") != "REENTRY":
        return base
    failures: list[str] = []
    unknowns: list[str] = []
    insufficient_prior_context = previous_exit_reason_class == "GENERIC" or previous_exit_reason.upper() in {"", "UNKNOWN", "EXIT", "SELL"}
    if insufficient_prior_context:
        unknowns.append("insufficient_prior_exit_context")
    if rank is None:
        unknowns.append("reentry_rank_missing")
    elif rank > 10:
        failures.append("reentry_opportunity_not_requalified")
    if not quality_action:
        unknowns.append("reentry_buy_quality_action_missing")
    elif quality_action not in {"REDUCED_ALLOCATION_ONLY", "FULL_ALLOCATION_ELIGIBLE"}:
        failures.append("reentry_buy_quality_not_requalified")
    if ca_status == "UNKNOWN":
        unknowns.append("reentry_corporate_action_source_missing")
    elif ca_status not in {"PASS", "RESOLVED", "NO_BLOCKING_EVENT", "NO_EVENT"}:
        failures.append("reentry_corporate_action_blocking")
    if capacity_ratio is None:
        unknowns.append("reentry_capacity_unavailable")
    elif liquidity_status == "SEVERE" or capacity_ratio > 0.03:
        failures.append("reentry_capacity_unavailable")
    if entry_action or entry_state:
        if entry_action in {"BUY_WAIT", "REJECT", "REVIEW_REQUIRED", "NO_ADD"} or entry_state in {
            "OVERHEATED_DECELERATING_ENTRY",
            "REVERSAL_RISK_ENTRY",
            "INSUFFICIENT_ENTRY_EVIDENCE",
        }:
            failures.append("reentry_entry_admission_not_allowed")
    if entry_sufficiency == "INSUFFICIENT":
        failures.append("reentry_entry_admission_not_allowed")
    if cq_status and cq_status not in {"PASS", "OK", "ACCEPTABLE"}:
        failures.append("reentry_continuation_quality_not_acceptable")
    if downside_status and downside_status not in {"PASS", "OK", "ACCEPTABLE"}:
        failures.append("reentry_downside_risk_not_acceptable")
    trend_pass = trend is not None and trend >= 1.0
    momentum_pass = momentum is not None and momentum >= 0.0
    if prior_exit_count >= 2 and (insufficient_prior_context or entry_action in {"BUY_WAIT", "REJECT", "REVIEW_REQUIRED", "NO_ADD"} or not (trend_pass and momentum_pass)):
        failures.append("reentry_repeated_unresolved_churn")
    technical_required = previous_exit_reason_class in {"TREND_MOMENTUM", "HARD_STOP", "CORPORATE_ACTION"}
    if technical_required:
        if trend is None and momentum is None:
            unknowns.append("reentry_technical_recovery_missing")
        elif not trend_pass:
            failures.append("reentry_trend_recovery_not_satisfied")
        elif not momentum_pass:
            failures.append("reentry_momentum_recovery_not_satisfied")
    if previous_exit_reason_class == "HARD_STOP" and quality_action != "FULL_ALLOCATION_ELIGIBLE":
        failures.append("reentry_hard_stop_new_thesis_not_sufficient")
    if previous_exit_reason_class == "PORTFOLIO_COMPETITION" and rank is not None and rank > 5:
        failures.append("reentry_opportunity_recovery_not_sufficient")
    if "REVERSAL" in previous_exit_reason.upper():
        if entry_state != "HEALTHY_CONTINUATION_ENTRY" or entry_action in {"BUY_WAIT", "REJECT", "REVIEW_REQUIRED", "NO_ADD"}:
            failures.append("reentry_reversal_not_normalized")
    trend_status = "PASS" if trend_pass else ("UNKNOWN" if trend is None else "FAIL")
    momentum_status = "PASS" if momentum_pass else ("UNKNOWN" if momentum is None else "FAIL")
    qualified = not failures and not unknowns
    resolved_base = {
        **base,
        "reentry_opportunity_qualification_status": "PASS" if rank is not None and rank <= 10 else ("UNKNOWN" if rank is None else "FAIL"),
        "reentry_trend_recovery_status": trend_status,
        "reentry_momentum_recovery_status": momentum_status,
        "reentry_entry_admission_status": (
            "NOT_PROVIDED"
            if not (entry_action or entry_state)
            else ("PASS" if "reentry_entry_admission_not_allowed" not in failures and "reentry_reversal_not_normalized" not in failures else "FAIL")
        ),
    }
    if failures:
        return {**resolved_base, "reentry_recovery_status": "FAIL_CLOSED", "reentry_recovery_reason": failures[0]}
    if unknowns:
        return {**resolved_base, "reentry_recovery_status": "REVIEW_REQUIRED", "reentry_recovery_reason": unknowns[0]}
    return {**resolved_base, "reentry_recovery_status": "PASS", "reentry_recovery_reason": "reentry_recovery_qualified" if qualified else "reentry_recovery_hurdle_passed"}


def _price_tick_risk_tier(single_tick_pct: float | None) -> str:
    if single_tick_pct is None:
        return "UNKNOWN"
    if single_tick_pct < 0.01:
        return "NORMAL"
    if single_tick_pct < 0.02:
        return "WATCH"
    if single_tick_pct < 0.05:
        return "ELEVATED"
    if single_tick_pct < 0.10:
        return "SEVERE"
    return "EXTREME"


def _liquidity_capacity_status(capacity_ratio: float | None) -> str:
    if capacity_ratio is None:
        return "UNKNOWN"
    if capacity_ratio <= 0.005:
        return "NORMAL"
    if capacity_ratio <= 0.01:
        return "WATCH"
    if capacity_ratio <= 0.03:
        return "CAP_REQUIRED"
    return "SEVERE"


def _allocation_cap_reason(*, normal_target_weight: float, capped_weight: float, price_tick_cap: float | None, liquidity_cap: float | None) -> str:
    if liquidity_cap is not None and capped_weight <= liquidity_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return "liquidity_capacity_cap_applied"
    if price_tick_cap is not None and capped_weight <= price_tick_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return "price_tick_risk_cap_applied"
    if capped_weight < normal_target_weight:
        return "risk_allocation_cap_applied"
    return "NONE"


def _current_authoritative_equity(summary: PortfolioConstructionSourceSummary) -> float | None:
    data = dict(summary.summary or {})
    for key in ("portfolio_total_equity", "portfolio_value", "total_equity", "current_authoritative_portfolio_equity"):
        value = _finite_number(data.get(key))
        if value is not None and value > 0:
            return value
    return None


def _positive_number_from_row(row: Mapping[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        raw = row.get(field)
        value = _finite_number(raw)
        if value is None and raw not in (None, ""):
            try:
                parsed = float(raw)
            except (TypeError, ValueError):
                parsed = math.nan
            value = parsed if math.isfinite(parsed) else None
        if value is not None and value > 0:
            return value
    return None


def _positive_number_source_field(row: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        raw = row.get(field)
        value = _finite_number(raw)
        if value is None and raw not in (None, ""):
            try:
                parsed = float(raw)
            except (TypeError, ValueError):
                parsed = math.nan
            value = parsed if math.isfinite(parsed) else None
        if value is not None and value > 0:
            return field
    return ""


def _prior_exit_business_date(row: Mapping[str, Any]) -> str:
    for field in ("prior_exit_business_date", "last_exit_business_date", "previous_exit_business_date"):
        value = str(row.get(field) or "").strip()
        if not value:
            continue
        try:
            _validate_iso_date(value[:10], field=field)
        except Exception:
            continue
        return value[:10]
    return ""


def _completed_business_days_between(start_date: str, end_date: str) -> int:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return 0
    if end <= start:
        return 0
    days = 0
    current = start
    while True:
        current = date.fromordinal(current.toordinal() + 1)
        if current >= end:
            break
        if current.weekday() < 5:
            days += 1
    return days


def _corporate_action_status(row: Mapping[str, Any]) -> str:
    for field in ("corporate_action_status", "corporate_event_status", "corporate_action_blocking_status", "corporate_event_blocking_status"):
        value = str(row.get(field) or "").strip().upper()
        if value:
            return value
    return "UNKNOWN"


def _corporate_action_evidence(row: Mapping[str, Any]) -> dict[str, str]:
    for field in ("corporate_action_status", "corporate_event_status", "corporate_action_blocking_status", "corporate_event_blocking_status"):
        value = str(row.get(field) or "").strip().upper()
        if value:
            return {
                "status": value,
                "source_status": str(row.get("corporate_action_source_status") or row.get("corporate_event_source_status") or "ROW_FIELD").upper(),
                "source": str(row.get("corporate_action_source") or field),
            }
    source_status = str(row.get("corporate_action_source_status") or row.get("corporate_event_source_status") or "").strip().upper()
    return {
        "status": "UNKNOWN",
        "source_status": source_status or "SOURCE_MISSING",
        "source": str(row.get("corporate_action_source") or row.get("corporate_event_source") or ""),
    }


def _previous_exit_reason(row: Mapping[str, Any]) -> str:
    for field in ("prior_exit_reason", "previous_exit_reason", "last_exit_reason", "source_decision_type", "decision_type"):
        value = str(row.get(field) or "").strip()
        if value:
            return value
    return "UNKNOWN"


def _previous_exit_reason_class(reason: str, reason_codes: Any = None) -> str:
    raw_codes = reason_codes if isinstance(reason_codes, list) else []
    text = " ".join([reason, *[str(item) for item in raw_codes]]).upper()
    if any(token in text for token in ("CORPORATE", "SPLIT", "MERGER", "TOB", "DELIST", "QUARANTINE")):
        return "CORPORATE_ACTION"
    if any(token in text for token in ("HARD_STOP", "STOP", "LOSS_CONTROL", "DRAWDOWN")):
        return "HARD_STOP"
    if any(token in text for token in ("REVERSAL", "OVERHEAT", "OVERHEATED", "EXHAUSTION")):
        return "REVERSAL"
    if any(token in text for token in ("TREND", "MOMENTUM", "EDGE_BREAK", "OPPORTUNITY_BROKEN", "WEAKEN")):
        return "TREND_MOMENTUM"
    if any(token in text for token in ("PORTFOLIO", "COMPETITION", "REALLOCATION", "REBALANCE", "CAPACITY", "ALLOCATION")):
        return "PORTFOLIO_COMPETITION"
    if any(token in text for token in ("ADMIN", "MANUAL", "OPERATIONAL", "QUARANTINED_TERMINAL")):
        return "ADMINISTRATIVE"
    if text.strip() in {"", "UNKNOWN"}:
        return "GENERIC"
    return "GENERIC"


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
    current_portfolio_summary: PortfolioConstructionSourceSummary,
    portfolio_policy_reference: str,
    source_hashes: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = dict(policy_config_summary.summary or {})
    current_equity = _current_authoritative_equity(current_portfolio_summary)
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
        elif quality_action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE"} and _buy_wait_applies_to_member(row):
            zero_reason = "buy_quality_wait"
            reason = "buy_quality_wait"
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
        elif (
            isinstance(raw_score, (int, float))
            and not isinstance(raw_score, bool)
            and float(raw_score) < 0
            and not row.get("current_position")
            and not _uncalibrated_relative_score_contract(row)
        ):
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
        l16_adjustment = _resolve_low_price_reentry_allocation_guard(
            row=row,
            business_date=business_date,
            normal_target_weight=weight,
            target_membership=target_membership,
            target_weight_reason=reason,
            zero_weight_reason=zero_reason,
            review_reason=review_reason,
            portfolio_equity=current_equity,
        )
        weight = l16_adjustment["target_weight"]
        target_membership = l16_adjustment["target_membership"]
        reason = l16_adjustment["target_weight_reason"]
        zero_reason = l16_adjustment["zero_weight_reason"]
        review_reason = l16_adjustment["review_reason"]
        if l16_adjustment["reason_code"]:
            reason_codes.append(str(l16_adjustment["reason_code"]))
        if l16_adjustment["member_reason_code"]:
            existing_member_reasons = list(row.get("reason_codes") or [])
            row = {**row, "reason_codes": sorted(set([*existing_member_reasons, str(l16_adjustment["member_reason_code"])]))}
        resolution = {
            **resolution,
            "reason": reason,
            "resolved_weight": weight,
            "zero_weight_reason": zero_reason,
            "review_reason": review_reason,
            "cap_applied": bool(resolution.get("cap_applied")) or bool(l16_adjustment["cap_applied"]),
            "adjustments": list(resolution.get("adjustments") or []) + list(l16_adjustment["adjustments"]),
        }
        authority = {
            **authority,
            "low_price_risk_allocation_authority": l16_adjustment["low_price_risk_allocation_authority"],
            "semantic_reentry_authority": l16_adjustment["semantic_reentry_authority"],
        }
        updated = {
            **row,
            "target_membership": target_membership,
            "target_weight": weight,
            "target_weight_authority": authority,
            "target_weight_resolution": resolution,
            "weight_reason": reason,
            **l16_adjustment["member_fields"],
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
        requested_increment = 0.0
        if current_position and pm_action in {"HOLD", "ADD"}:
            baseline = current_weight if current_weight is not None else target
            requested_increment = round(
                max(
                    float(member.get("requested_incremental_weight") or 0.0),
                    float(member.get("accepted_incremental_weight") or 0.0),
                    target - baseline,
                    0.0,
                ),
                TARGET_WEIGHT_DECIMALS,
            )
            participant_type = "BUY_ADD" if pm_action == "ADD" and requested_increment > 0 else "NONE"
        elif current_position:
            baseline = target
        elif membership == "ADD_CANDIDATE":
            requested_increment = round(
                max(
                    float(member.get("requested_buy_new_weight") or 0.0),
                    float(member.get("accepted_buy_new_weight") or 0.0),
                    target,
                    0.0,
                ),
                TARGET_WEIGHT_DECIMALS,
            )
            participant_type = "BUY_NEW" if requested_increment > 0 else "NONE"
        baseline = round(baseline, TARGET_WEIGHT_DECIMALS)
        baseline_total += baseline
        prepared.append(
            {
                "index": index,
                "baseline": baseline,
                "draft_target": target,
                "requested_increment": requested_increment,
                "participant_type": participant_type,
            }
        )
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
    rebatch_allocations: list[dict[str, Any]] = []
    allocation_iterations: list[dict[str, Any]] = []
    candidates = []
    for item in prepared:
        if item["participant_type"] == "NONE":
            accepted_by_index[item["index"]] = 0.0
            continue
        member = members[item["index"]]
        symbol = str(member.get("security_code") or member.get("symbol") or "")
        feasibility = feasibility_by_symbol.get(symbol)
        request = round(
            max(
                float(item.get("requested_increment") or 0.0),
                float(item["draft_target"]) - float(item["baseline"]),
                0.0,
            ),
            TARGET_WEIGHT_DECIMALS,
        )
        candidates.append(
            {
                **item,
                "symbol": symbol,
                "request": request,
                "priority": _positive_int(member.get("construction_priority"), 999999),
                "quality_order": _quality_adjusted_reallocation_order(member),
                "score": _finite_number(member.get("runtime_opportunity_score")) or 0.0,
                "feasibility": feasibility,
            }
        )
    one_lot_admissions_by_index: dict[int, dict[str, Any]] = {}
    minimum_one_lot_authority_by_index: dict[int, dict[str, Any]] = {}
    for item in sorted(candidates, key=lambda value: (value["quality_order"], value["priority"], value["symbol"])):
        feasibility = item["feasibility"]
        member = members[item["index"]]
        min_weight = _optional_ratio((feasibility or {}).get("minimum_executable_weight"))
        lot_resolution = dict((feasibility or {}).get("phase29_l19_lot_resolution") or {})
        feasibility_classification = str((feasibility or {}).get("lot_first_feasibility_classification") or "")
        lot_feasible = bool((feasibility or {}).get("lot_feasible"))
        broker_eligible = (feasibility or {}).get("broker_eligible") is not False and str(member.get("broker_eligibility_status") or "") != "FAIL_CLOSED"
        required = item["request"]
        iteration = len(accepted_by_index) + len(skipped) + 1
        base_skip_evidence = {
            "symbol": item["symbol"],
            "participant_type": item["participant_type"],
            "reallocation_iteration": iteration,
            "opportunity_cost_order": item["priority"],
            "requested_weight": item["request"],
            "draft_target_weight": item["draft_target"],
            "baseline_weight": item["baseline"],
            "lot_resolution": lot_resolution,
            "residual_recycled": False,
            "residual_destination": "Cash",
        }
        if feasibility is None:
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = "lot_feasibility_unknown_fail_closed"
            skipped.append({**base_skip_evidence, "reason": "lot_feasibility_unknown_fail_closed", "request": item["request"], "blocked_reason": "lot_feasibility_unknown_fail_closed"})
            continue
        if (
            str(lot_resolution.get("boundary_classification") or "") == "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX"
            or lot_resolution.get("safety_hard_cap_preserved") is False
        ):
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = "minimum_lot_exceeds_safety_hard_cap"
            skipped.append(
                {
                    **base_skip_evidence,
                    "reason": "minimum_lot_exceeds_safety_hard_cap",
                    "blocked_reason": str(lot_resolution.get("boundary_classification") or "minimum_lot_exceeds_safety_hard_cap"),
                    "required_weight": min_weight,
                    "feasibility_classification": "SAFETY_HARD_BLOCKED",
                }
            )
            continue
        second_lot_promotion = _second_lot_plus_add_promotion_evidence(
            item=item,
            member=member,
            lot_resolution=lot_resolution,
            one_lot_weight=min_weight,
        )
        one_lot_fallback_requested = (
            bool(lot_resolution.get("one_lot_fallback_applied"))
            and item["participant_type"] != "BUY_ADD"
        ) or (
            min_weight is not None
            and item["request"] > 0
            and item["request"] < min_weight - TARGET_WEIGHT_ABSOLUTE_TOLERANCE
            and item["participant_type"] != "BUY_ADD"
        )
        if not lot_feasible or one_lot_fallback_requested:
            if min_weight is not None:
                required = max(required, min_weight)
            else:
                required = 0.0
        if (
            item["participant_type"] == "BUY_ADD"
            and min_weight is not None
            and 0 < item["request"] < min_weight - TARGET_WEIGHT_ABSOLUTE_TOLERANCE
            and not second_lot_promotion["promotion_candidate"]
        ):
            required = 0.0
        if second_lot_promotion["promotion_candidate"]:
            required = max(required, float(second_lot_promotion["upper_boundary_weight"]))
        canonical_discrete_requirement = _canonical_discrete_executable_requirement_weight(
            item=item,
            lot_resolution=lot_resolution,
        )
        budget_requirement_source = "DRAFT_CONTINUOUS_ALLOCATION"
        if canonical_discrete_requirement is not None:
            required = canonical_discrete_requirement
            budget_requirement_source = "CANONICAL_DISCRETE_EXECUTABLE_REQUIREMENT"
        base_skip_evidence["budget_requirement_source"] = budget_requirement_source
        base_skip_evidence["canonical_discrete_executable_required_weight"] = canonical_discrete_requirement
        soft_strategy_overshoot_allowed = _lot_aware_strategy_cap_overshoot_allowed(
            item=item,
            member=member,
            lot_resolution=lot_resolution,
            required_weight=required,
            single_name_cap=single_name_cap,
        )
        one_lot_admission = _quality_adjusted_one_lot_admission(
            item=item,
            member=member,
            lot_resolution=lot_resolution,
            required_weight=required,
            single_name_cap=single_name_cap,
            soft_strategy_overshoot_allowed=soft_strategy_overshoot_allowed,
        )
        one_lot_admissions_by_index[item["index"]] = one_lot_admission
        if one_lot_admission["status"] in {"DEFER", "FAIL_CLOSED", "REVIEW_REQUIRED"}:
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = str(one_lot_admission["blocked_reason"])
            skipped.append(
                {
                    **base_skip_evidence,
                    "reason": str(one_lot_admission["blocked_reason"]),
                    "blocked_reason": str(one_lot_admission["blocked_reason"]),
                    "required_weight": required,
                    "feasibility_classification": "QUALITY_ADJUSTED_ONE_LOT_BLOCKED",
                    "one_lot_admission": one_lot_admission,
                }
            )
            reason_codes.append("quality_adjusted_one_lot_admission_deferred_or_blocked")
            continue
        if not broker_eligible or required <= 0:
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = "lot_or_broker_infeasible"
            skipped.append({**base_skip_evidence, "reason": "lot_or_broker_infeasible", "blocked_reason": "lot_or_broker_infeasible", "feasibility": feasibility, "feasibility_classification": feasibility_classification, "one_lot_admission": one_lot_admission})
            continue
        if single_name_cap is not None:
            max_increment = round(max(float(single_name_cap) - float(item["baseline"]), 0.0), TARGET_WEIGHT_DECIMALS)
            if required > max_increment and not soft_strategy_overshoot_allowed:
                accepted_by_index[item["index"]] = 0.0
                skipped_by_index[item["index"]] = "minimum_lot_exceeds_concentration_cap"
                skipped.append(
                    {
                        **base_skip_evidence,
                        "reason": "minimum_lot_exceeds_concentration_cap",
                        "blocked_reason": str(lot_resolution.get("boundary_classification") or "minimum_lot_exceeds_concentration_cap"),
                        "required_weight": required,
                        "max_increment": max_increment,
                        "feasibility_classification": "CONCENTRATION_BLOCKED",
                        "one_lot_admission": one_lot_admission,
                    }
                )
                continue
        if required > remaining:
            accepted_by_index[item["index"]] = 0.0
            skipped_by_index[item["index"]] = "minimum_lot_exceeds_remaining_budget"
            skipped.append({**base_skip_evidence, "reason": "minimum_lot_exceeds_remaining_budget", "blocked_reason": "minimum_lot_exceeds_remaining_budget", "required_weight": required, "remaining_budget": remaining, "feasibility_classification": "CAPITAL_BLOCKED", "one_lot_admission": one_lot_admission, "second_lot_plus_promotion": second_lot_promotion})
            continue
        minimum_one_lot_authority = _minimum_executable_one_lot_authority(
            item=item,
            member=member,
            lot_resolution=lot_resolution,
            original_request_weight=item["request"],
            final_promoted_weight=required,
            single_name_cap=single_name_cap,
            soft_strategy_overshoot_allowed=soft_strategy_overshoot_allowed,
            one_lot_admission=one_lot_admission,
        )
        if minimum_one_lot_authority:
            minimum_one_lot_authority_by_index[item["index"]] = minimum_one_lot_authority
        accepted_by_index[item["index"]] = required
        remaining = round(max(remaining - required, 0.0), TARGET_WEIGHT_DECIMALS)
        allocation_iterations.append(
            {
                "symbol": item["symbol"],
                "participant_type": item["participant_type"],
                "accepted_lot_increment_weight": required,
                "budget_requirement_source": budget_requirement_source,
                "canonical_discrete_executable_required_weight": canonical_discrete_requirement,
                "reallocation_iteration": iteration,
                "opportunity_cost_order": item["priority"],
                "residual_recycled": item["draft_target"] <= item["baseline"] and item["request"] > 0,
                "residual_destination": item["symbol"],
                "lot_resolution": lot_resolution,
                "one_lot_admission": one_lot_admission,
                "minimum_executable_one_lot_authority": minimum_one_lot_authority,
                "second_lot_plus_promotion": second_lot_promotion,
                "reason": "cap_constrained_lot_floor_allocation",
                "strategy_cap_overshoot_applied": soft_strategy_overshoot_allowed,
                "strategy_cap_overshoot_reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP" if soft_strategy_overshoot_allowed else "",
            }
        )
        if required > item["request"]:
            promoted.append(
                {
                    "symbol": item["symbol"],
                    "from_weight": item["request"],
                    "to_weight": required,
                    "budget_requirement_source": budget_requirement_source,
                    "canonical_discrete_executable_required_weight": canonical_discrete_requirement,
                    "reason": "ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP"
                    if soft_strategy_overshoot_allowed
                    else "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION"
                    if second_lot_promotion["promotion_candidate"]
                    else "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
                    "strategy_cap_overshoot_applied": soft_strategy_overshoot_allowed,
                    "one_lot_admission": one_lot_admission,
                    "minimum_executable_one_lot_authority": minimum_one_lot_authority,
                    "second_lot_plus_promotion": second_lot_promotion,
                }
            )
        if item["draft_target"] <= item["baseline"] and item["request"] > 0:
            rebatch_allocations.append(
                {
                    "symbol": item["symbol"],
                    "participant_type": item["participant_type"],
                    "accepted_lot_increment_weight": required,
                    "budget_requirement_source": budget_requirement_source,
                    "canonical_discrete_executable_required_weight": canonical_discrete_requirement,
                    "reallocation_iteration": iteration,
                    "opportunity_cost_order": item["priority"],
                    "residual_recycled": True,
                    "residual_destination": item["symbol"],
                    "lot_resolution": lot_resolution,
                    "one_lot_admission": one_lot_admission,
                    "minimum_executable_one_lot_authority": minimum_one_lot_authority,
                    "second_lot_plus_promotion": second_lot_promotion,
                    "reason": "request_positive_rebatched_after_lot_first_recycling",
                }
            )
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
                "requested_lot_first_increment_weight": item.get("requested_increment", 0.0),
            }
        )
        feasibility = feasibility_by_symbol.get(str(member.get("security_code") or member.get("symbol") or ""))
        feasibility_classification = str((feasibility or {}).get("lot_first_feasibility_classification") or "")
        lot_resolution = dict((feasibility or {}).get("phase29_l19_lot_resolution") or {})
        one_lot_admission = one_lot_admissions_by_index.get(item["index"]) or _quality_adjusted_one_lot_admission(
            item=item,
            member=member,
            lot_resolution=lot_resolution,
            required_weight=accepted,
            single_name_cap=single_name_cap,
            soft_strategy_overshoot_allowed=False,
        )
        semantic_type = _lot_authority_semantic_type(member=member, participant_type=item["participant_type"])
        minimum_one_lot_authority = minimum_one_lot_authority_by_index.get(item["index"], {})
        minimum_one_lot_admitted = bool(minimum_one_lot_authority)
        second_lot_promotion = _second_lot_plus_add_promotion_evidence(
            item=item,
            member=member,
            lot_resolution=lot_resolution,
            one_lot_weight=_optional_ratio((feasibility or {}).get("minimum_executable_weight")),
        )
        final_allocated_quantity = _final_discrete_allocated_quantity(
            accepted_weight=accepted,
            lot_resolution=lot_resolution,
            second_lot_promotion=second_lot_promotion,
        )
        pc_quantity_authority = _pc_positive_executable_quantity_authority(
            accepted_weight=accepted,
            final_allocated_quantity=final_allocated_quantity,
        )
        lot_overshoot_reason = lot_resolution.get("lot_overshoot_reason", "")
        if minimum_one_lot_admitted:
            lot_overshoot_reason = "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED"
        elif (
            second_lot_promotion["promotion_candidate"]
            and not soft_strategy_overshoot_allowed
            and accepted >= float(second_lot_promotion["upper_boundary_weight"]) - TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        ):
            lot_overshoot_reason = "SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION"
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
                        "quality_adjusted_one_lot_admission": one_lot_admission,
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
                        "requested_lot_first_increment_weight": item.get("requested_increment", 0.0),
                        "one_lot_admission": one_lot_admission,
                        "minimum_executable_one_lot_authority": minimum_one_lot_authority,
                        "second_lot_plus_promotion": second_lot_promotion,
                        "lot_first_feasibility_classification": feasibility_classification,
                        "skip_reason": skipped_by_index.get(item["index"], ""),
                        "strategy_cap_overshoot_applied": accepted > 0 and bool(lot_resolution.get("strategy_cap_overshoot_applied")),
                        "strategy_cap_overshoot_reason": str(lot_resolution.get("lot_overshoot_reason") or ""),
                        "continuous_target_weight": lot_resolution.get("continuous_target_weight", item["draft_target"]),
                        "continuous_target_notional": lot_resolution.get("continuous_target_notional"),
                        "normal_lot_quantity": lot_resolution.get("normal_lot_quantity", lot_resolution.get("requested_lots")),
                        "one_lot_quantity": lot_resolution.get("one_lot_quantity"),
                        "one_lot_notional": lot_resolution.get("one_lot_notional"),
                        "one_lot_feasibility_status": lot_resolution.get("one_lot_feasibility_status"),
                        "one_lot_fallback_applied": accepted > 0 and bool(lot_resolution.get("one_lot_fallback_applied")),
                        "blocker_reason": skipped_by_index.get(item["index"], ""),
                        "final_allocated_quantity": final_allocated_quantity,
                        "pc_positive_executable_quantity_authority": pc_quantity_authority,
                        "residual_capital_after_allocation_weight": remaining,
                        "phase29_l19_lot_resolution": lot_resolution,
                    },
                },
                "lot_aware_final_target_weight": final_weight,
                "lot_aware_accepted_incremental_weight": accepted if item["participant_type"] == "BUY_ADD" else 0.0,
                "lot_aware_accepted_buy_new_weight": accepted if item["participant_type"] == "BUY_NEW" else 0.0,
                "lot_first_feasibility_classification": feasibility_classification,
                "lot_first_rebatch_participant": item["participant_type"] != "NONE",
                "lot_first_rebatch_skip_reason": skipped_by_index.get(item["index"], ""),
                "phase29_l19_lot_resolution": {
                    **lot_resolution,
                    "symbol": str(member.get("security_code") or member.get("symbol") or ""),
                    "semantic_type": semantic_type,
                    "requested_target_weight": item["draft_target"],
                    "requested_incremental_weight": item.get("requested_increment", 0.0),
                    "final_target_weight": final_weight,
                    "blocked_reason": skipped_by_index.get(item["index"], ""),
                    "residual_notional": None,
                    "residual_recycled": accepted > 0,
                    "residual_destination": str(member.get("security_code") or member.get("symbol") or "") if accepted > 0 else "Cash",
                    "preflight_executable_quantity_delta": lot_resolution.get("executable_quantity_delta"),
                    "final_quantity_delta": None,
                    "strategy_target_cap": lot_resolution.get("strategy_target_cap", lot_resolution.get("strategy_cap_weight")),
                    "strategy_cap_overshoot_applied": accepted > 0 and bool(lot_resolution.get("strategy_cap_overshoot_applied")),
                    "strategy_cap_overshoot_weight": lot_resolution.get("strategy_cap_overshoot_weight"),
                    "post_trade_weight": lot_resolution.get("post_trade_weight"),
                    "safety_hard_cap": lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")),
                    "safety_margin_after_trade": lot_resolution.get("safety_margin_after_trade"),
                    "lot_overshoot_reason": lot_overshoot_reason,
                    "minimum_executable_one_lot_admitted": minimum_one_lot_admitted,
                    "minimum_executable_one_lot_reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED" if minimum_one_lot_admitted else "",
                    "minimum_executable_one_lot_authority": minimum_one_lot_authority,
                    "second_lot_plus_promotion": second_lot_promotion,
                    "continuous_target_weight": lot_resolution.get("continuous_target_weight", item["draft_target"]),
                    "continuous_target_notional": lot_resolution.get("continuous_target_notional"),
                    "normal_lot_quantity": lot_resolution.get("normal_lot_quantity", lot_resolution.get("requested_lots")),
                    "one_lot_quantity": lot_resolution.get("one_lot_quantity"),
                    "one_lot_notional": lot_resolution.get("one_lot_notional"),
                    "one_lot_feasibility_status": lot_resolution.get("one_lot_feasibility_status"),
                    "one_lot_fallback_applied": accepted > 0 and bool(lot_resolution.get("one_lot_fallback_applied")),
                    "blocker_reason": skipped_by_index.get(item["index"], ""),
                    "final_allocated_quantity": final_allocated_quantity,
                    "pc_positive_executable_quantity_authority": pc_quantity_authority,
                    "residual_capital_after_allocation_weight": remaining,
                },
                "one_lot_admission": one_lot_admission,
            }
        )
    total = round(sum(float(member.get("target_weight") or 0.0) for member in final_members), TARGET_WEIGHT_DECIMALS)
    if skipped:
        reason_codes.append("lot_aware_infeasible_allocations_reallocated_or_cash")
    if promoted:
        reason_codes.append("lot_aware_minimum_executable_lot_authorized")
    if minimum_one_lot_authority_by_index:
        reason_codes.append("MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED")
    if rebatch_allocations:
        reason_codes.append("lot_first_rebatch_recycled_request_positive_capital")
    deployable_budget = round(max(float(target_gross_exposure) - baseline_total, 0.0), TARGET_WEIGHT_DECIMALS)
    allocated_increment = round(max(total - baseline_total, 0.0), TARGET_WEIGHT_DECIMALS)
    residual_cash_reason = "COMPETITION_EXHAUSTED"
    if remaining <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        residual_cash_reason = "TARGET_GROSS_EXPOSURE_FULLY_ALLOCATED"
    elif not candidates:
        residual_cash_reason = "NO_ELIGIBLE_OPPORTUNITY"
    elif all(str(item.get("reason") or "") in {"minimum_lot_exceeds_concentration_cap", "minimum_lot_exceeds_safety_hard_cap"} for item in skipped) and skipped:
        residual_cash_reason = "CONCENTRATION_LIMIT"
    elif any(str(item.get("reason") or "") == "minimum_lot_exceeds_remaining_budget" for item in skipped):
        residual_cash_reason = "CAPITAL_BELOW_NEXT_LOT"
    elif all(str(item.get("reason") or "") in {"lot_or_broker_infeasible"} for item in skipped) and skipped:
        residual_cash_reason = "NO_LOT_FEASIBLE_OPPORTUNITY"
    capital_conservation = {
        "authority_type": "PORTFOLIO_CONSTRUCTION_LOT_FIRST_CAPITAL_CONSERVATION",
        "target_gross_exposure": target_gross_exposure,
        "baseline_existing_required_weight": baseline_total,
        "deployable_budget_weight": deployable_budget,
        "allocated_increment_weight": allocated_increment,
        "residual_cash_weight": remaining,
        "conservation_lhs_weight": round(allocated_increment + remaining, TARGET_WEIGHT_DECIMALS),
        "conservation_rhs_weight": deployable_budget,
        "conservation_difference_weight": round((allocated_increment + remaining) - deployable_budget, TARGET_WEIGHT_DECIMALS),
        "status": "PASS" if abs((allocated_increment + remaining) - deployable_budget) <= _target_weight_sum_tolerance(len(members)) else "REVIEW_REQUIRED",
    }
    residual_recycled_weight = round(sum(float(row.get("accepted_lot_increment_weight") or 0.0) for row in allocation_iterations), TARGET_WEIGHT_DECIMALS)
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
            "rebatch_allocations": rebatch_allocations,
            "phase29_l19_allocation_iterations": allocation_iterations,
            "lot_first_rebatch_enabled": True,
            "lot_first_rebatch_candidate_count": len(candidates),
            "phase29_l19_cap_constrained_lot_floor_enabled": True,
            "phase29_l19_strategy_safety_cap_separated": any(bool((item.get("lot_resolution") or {}).get("safety_hard_cap_weight")) for item in skipped + allocation_iterations + rebatch_allocations),
            "phase29_l19_reallocation_iterations": len(candidates),
            "phase29_l19_residual_recycled_weight": residual_recycled_weight,
            "phase29_l19_candidate_exhaustion_status": "EXHAUSTED_TO_CASH" if candidates and remaining > TARGET_WEIGHT_ABSOLUTE_TOLERANCE and not allocation_iterations else "ALLOCATED_OR_NOT_APPLICABLE",
            "residual_cash_reason": residual_cash_reason,
            "capital_conservation": capital_conservation,
            "ps_preflight_decides_economic_allocation": False,
            "pc_remains_target_weight_authority": True,
            "quality_adjusted_one_lot_admission_enabled": True,
        },
    }


def _lot_aware_strategy_cap_overshoot_allowed(
    *,
    item: Mapping[str, Any],
    member: Mapping[str, Any],
    lot_resolution: Mapping[str, Any],
    required_weight: float,
    single_name_cap: float | None,
) -> bool:
    participant_type = str(item.get("participant_type") or "")
    if participant_type not in {"BUY_NEW", "BUY_ADD"} or single_name_cap is None:
        return False
    if str(lot_resolution.get("boundary_classification") or "") != "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX":
        return False
    if participant_type == "BUY_ADD":
        if str(member.get("pm_action") or "").upper() != "ADD" or not bool(member.get("current_position")):
            return False
        if str(member.get("add_allocation_eligibility_status") or "") != "PASS":
            return False
        if str(member.get("incremental_investment_value_state") or "") != "POSITIVE":
            return False
        if str(member.get("opportunity_cost_status") or "") != "PASS":
            return False
    elif bool(member.get("current_position")) or str(member.get("membership_intent") or "").upper() != "ADD_CANDIDATE":
        return False
    if required_weight <= 0:
        return False
    baseline = float(item.get("baseline") or 0.0)
    post_trade_weight = _optional_ratio(lot_resolution.get("post_trade_weight"))
    safety_hard_cap = _optional_ratio(lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")))
    if post_trade_weight is None:
        post_trade_weight = round(baseline + required_weight, TARGET_WEIGHT_DECIMALS)
    if safety_hard_cap is None:
        return False
    if post_trade_weight > safety_hard_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    if post_trade_weight <= float(single_name_cap) + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return False
    return bool(lot_resolution.get("safety_hard_cap_preserved") is not False)


def _second_lot_plus_add_promotion_evidence(
    *,
    item: Mapping[str, Any],
    member: Mapping[str, Any],
    lot_resolution: Mapping[str, Any],
    one_lot_weight: float | None,
) -> dict[str, Any]:
    request = round(float(item.get("request", item.get("requested_increment", 0.0)) or 0.0), TARGET_WEIGHT_DECIMALS)
    baseline = round(float(item.get("baseline") or 0.0), TARGET_WEIGHT_DECIMALS)
    symbol = str(item.get("symbol") or member.get("security_code") or member.get("symbol") or "")
    base = {
        "schema_version": "second_lot_plus_residual_promotion.v1",
        "authority_type": LOT_AWARE_REALLOCATION_AUTHORITY_TYPE,
        "symbol": symbol,
        "status": "NOT_APPLICABLE",
        "promotion_candidate": False,
        "current_executable_lots": _positive_int(member.get("current_quantity"), 0)
        // max(_positive_int(lot_resolution.get("one_lot_quantity"), 0), 1),
        "requested_incremental_weight": request,
        "one_lot_weight": one_lot_weight,
        "lower_boundary_lots": 0,
        "upper_boundary_lots": 0,
        "lower_boundary_weight": 0.0,
        "upper_boundary_weight": 0.0,
        "distance_to_lower_weight": 0.0,
        "distance_to_upper_weight": 0.0,
        "tie_rule": "MIDPOINT_PROMOTES_TO_UPPER_ONLY_AFTER_EXISTING_PC_PRIORITY_AND_CAPITAL_GUARDS_PASS",
        "future_information_used": False,
    }
    if str(item.get("participant_type") or "") != "BUY_ADD":
        return base
    if not bool(member.get("current_position")) or str(member.get("pm_action") or "").upper() != "ADD":
        return base
    if one_lot_weight is None or one_lot_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE or request <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return base
    requested_lots = request / one_lot_weight
    lower_lots = int(math.floor(requested_lots))
    upper_lots = int(math.ceil(requested_lots))
    lower_weight = round(lower_lots * one_lot_weight, TARGET_WEIGHT_DECIMALS)
    upper_weight = round(upper_lots * one_lot_weight, TARGET_WEIGHT_DECIMALS)
    distance_to_lower = round(max(request - lower_weight, 0.0), TARGET_WEIGHT_DECIMALS)
    distance_to_upper = round(max(upper_weight - request, 0.0), TARGET_WEIGHT_DECIMALS)
    candidate = upper_lots > lower_lots and distance_to_upper <= distance_to_lower + TARGET_WEIGHT_ABSOLUTE_TOLERANCE
    status = "CANDIDATE" if candidate else "BELOW_NEAREST_LOT_PROMOTION_DISTANCE"
    if str(member.get("add_allocation_eligibility_status") or "") not in {"", "PASS"}:
        candidate = False
        status = "ADD_CONTRACT_BLOCKED"
    if str(member.get("incremental_investment_value_state") or "") not in {"", "POSITIVE"}:
        candidate = False
        status = "INCREMENTAL_VALUE_BLOCKED"
    if str(member.get("opportunity_cost_status") or "") not in {"", "PASS"}:
        candidate = False
        status = "OPPORTUNITY_COST_BLOCKED"
    if str(member.get("entry_admission_action") or "").upper() == "NO_ADD":
        candidate = False
        status = "NO_ADD_BLOCKED"
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        candidate = False
        status = "SAFETY_HARD_CAP_BLOCKED"
    return {
        **base,
        "status": status,
        "promotion_candidate": candidate,
        "baseline_weight": baseline,
        "requested_increment_lots": round(requested_lots, 6),
        "lower_boundary_lots": lower_lots,
        "upper_boundary_lots": upper_lots,
        "lower_boundary_weight": lower_weight,
        "upper_boundary_weight": upper_weight,
        "distance_to_lower_weight": distance_to_lower,
        "distance_to_upper_weight": distance_to_upper,
        "nearest_lot_distance_evidence": {
            "requested_increment_lots": round(requested_lots, 6),
            "closer_boundary": "UPPER" if distance_to_upper <= distance_to_lower + TARGET_WEIGHT_ABSOLUTE_TOLERANCE else "LOWER",
            "threshold_source": "DETERMINISTIC_LOT_MIDPOINT_NOT_HISTORICAL_OUTCOME",
        },
    }


def _canonical_discrete_executable_requirement_weight(
    *,
    item: Mapping[str, Any],
    lot_resolution: Mapping[str, Any],
) -> float | None:
    if str(item.get("participant_type") or "") not in {"BUY_NEW", "BUY_ADD"}:
        return None
    if (
        str(lot_resolution.get("boundary_classification") or "") == "MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX"
        or lot_resolution.get("safety_hard_cap_preserved") is False
    ):
        return None
    one_lot_weight = _optional_ratio(lot_resolution.get("one_lot_weight"))
    if one_lot_weight is None or one_lot_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return None
    one_lot_quantity = _positive_int(lot_resolution.get("one_lot_quantity"), 0)
    if one_lot_quantity <= 0:
        return None
    executable_quantity = _positive_int(lot_resolution.get("final_allocated_quantity"), 0)
    if executable_quantity <= 0:
        executable_quantity = _positive_int(lot_resolution.get("executable_quantity_delta"), 0)
    if executable_quantity <= 0:
        executable_quantity = _positive_int(lot_resolution.get("normal_lot_quantity"), 0)
    if executable_quantity <= 0 or executable_quantity % one_lot_quantity != 0:
        return None
    quantity_derived_requirement = round(
        one_lot_weight * (executable_quantity / one_lot_quantity),
        TARGET_WEIGHT_DECIMALS,
    )
    if quantity_derived_requirement <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return None
    post_trade_weight = _optional_ratio(lot_resolution.get("post_trade_weight"))
    if post_trade_weight is not None:
        baseline_weight = _optional_ratio(lot_resolution.get("current_weight"))
        if baseline_weight is None:
            baseline_weight = max(float(item.get("baseline") or 0.0), 0.0)
        post_trade_requirement = round(max(post_trade_weight - baseline_weight, 0.0), TARGET_WEIGHT_DECIMALS)
        if (
            post_trade_requirement > TARGET_WEIGHT_ABSOLUTE_TOLERANCE
            and abs(post_trade_requirement - quantity_derived_requirement) > TARGET_WEIGHT_ABSOLUTE_TOLERANCE
        ):
            return None
    return quantity_derived_requirement


def _final_discrete_allocated_quantity(
    *,
    accepted_weight: float,
    lot_resolution: Mapping[str, Any],
    second_lot_promotion: Mapping[str, Any],
) -> int:
    if accepted_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return 0
    one_lot_quantity = _positive_int(lot_resolution.get("one_lot_quantity"), 0)
    if one_lot_quantity <= 0:
        return _positive_int(lot_resolution.get("final_allocated_quantity"), _positive_int(lot_resolution.get("executable_quantity_delta"), 0))
    if second_lot_promotion.get("promotion_candidate") is True:
        upper_lots = _positive_int(second_lot_promotion.get("upper_boundary_lots"), 0)
        upper_weight = float(second_lot_promotion.get("upper_boundary_weight") or 0.0)
        if upper_lots > 0 and accepted_weight >= upper_weight - TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
            return int(upper_lots * one_lot_quantity)
    if bool(lot_resolution.get("one_lot_fallback_applied")):
        return one_lot_quantity
    one_lot_weight = _optional_ratio(lot_resolution.get("one_lot_weight"))
    if one_lot_weight is not None and one_lot_weight > TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        lots = int(math.floor((accepted_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE) / one_lot_weight))
        if lots > 0:
            return int(lots * one_lot_quantity)
    return _positive_int(lot_resolution.get("final_allocated_quantity"), _positive_int(lot_resolution.get("executable_quantity_delta"), 0))


def _pc_positive_executable_quantity_authority(*, accepted_weight: float, final_allocated_quantity: int) -> dict[str, Any]:
    quantity = _positive_int(final_allocated_quantity, 0)
    return {
        "authority_type": "PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY",
        "status": "PASS" if accepted_weight > TARGET_WEIGHT_ABSOLUTE_TOLERANCE and quantity > 0 else "NOT_APPLICABLE",
        "final_allocated_quantity": quantity,
        "accepted_lot_increment_weight": round(float(accepted_weight or 0.0), TARGET_WEIGHT_DECIMALS),
        "ps_must_consume_canonical_quantity": accepted_weight > TARGET_WEIGHT_ABSOLUTE_TOLERANCE and quantity > 0,
        "future_information_used": False,
    }


def _quality_adjusted_reallocation_order(member: Mapping[str, Any]) -> int:
    action = str(member.get("entry_admission_action") or "").upper()
    state = str(member.get("entry_admission_state") or "").upper()
    add_worthiness = str(member.get("strategy_intelligence_add_worthiness_state") or "").upper()
    if bool(member.get("current_position")) and add_worthiness in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "PASS"}:
        return 0
    if bool(member.get("current_position")) and add_worthiness == "NO_ADD":
        return 3
    if action in {"BUY_NEW_ALLOWED", "ADD_ALLOWED"} or state == "HEALTHY_CONTINUATION_ENTRY":
        return 0
    if action in {"BUY_NEW_REDUCED_ONLY", "ADD_REDUCED_ONLY"} or state == "CONTINUATION_WITH_CAUTION":
        return 1
    if not action and not state:
        return 1
    if action in {"BUY_WAIT", "NO_ADD"} or state in {"OVERHEATED_DECELERATING_ENTRY", "REVERSAL_RISK_ENTRY"}:
        return 3
    return 2


def _lot_authority_semantic_type(*, member: Mapping[str, Any], participant_type: str) -> str:
    semantic = str(member.get("semantic_buy_type") or "").upper()
    participant = str(participant_type or "").upper()
    if participant == "BUY_NEW" and semantic in {"BUY_NEW", "REENTRY"}:
        return semantic
    if participant == "BUY_ADD":
        return "BUY_ADD"
    return participant


def _minimum_executable_one_lot_authority(
    *,
    item: Mapping[str, Any],
    member: Mapping[str, Any],
    lot_resolution: Mapping[str, Any],
    original_request_weight: float,
    final_promoted_weight: float,
    single_name_cap: float | None,
    soft_strategy_overshoot_allowed: bool,
    one_lot_admission: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = _lot_authority_semantic_type(member=member, participant_type=str(item.get("participant_type") or ""))
    if semantic not in {"BUY_NEW", "REENTRY"}:
        return {}
    if bool(member.get("current_position")) or float(item.get("baseline") or 0.0) > TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return {}
    if float(original_request_weight or 0.0) <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return {}
    one_lot_weight = _optional_ratio(lot_resolution.get("one_lot_weight", lot_resolution.get("minimum_executable_weight")))
    if one_lot_weight is None or one_lot_weight <= TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return {}
    if float(original_request_weight or 0.0) >= one_lot_weight - TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return {}
    if final_promoted_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE < one_lot_weight:
        return {}
    if final_promoted_weight > one_lot_weight + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return {}
    if soft_strategy_overshoot_allowed:
        return {}
    if single_name_cap is not None and final_promoted_weight > float(single_name_cap) + TARGET_WEIGHT_ABSOLUTE_TOLERANCE:
        return {}
    if str(one_lot_admission.get("status") or "") != "PASS":
        return {}
    if str(lot_resolution.get("one_lot_feasibility_status") or "") != "PASS":
        return {}
    if lot_resolution.get("safety_hard_cap_preserved") is False:
        return {}
    safety_cap = _optional_ratio(lot_resolution.get("safety_hard_cap", lot_resolution.get("safety_hard_cap_weight")))
    post_trade_weight = _optional_ratio(lot_resolution.get("post_trade_weight", final_promoted_weight))
    if safety_cap is None or (post_trade_weight is not None and post_trade_weight > safety_cap + TARGET_WEIGHT_ABSOLUTE_TOLERANCE):
        return {}
    one_lot_quantity = _positive_int(lot_resolution.get("one_lot_quantity"), 0)
    if one_lot_quantity <= 0:
        return {}
    target_ratio = round(float(original_request_weight) / one_lot_weight, 6)
    return {
        "schema_version": "minimum_executable_one_lot_authority.v1",
        "authority_type": "PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION",
        "decision": "ADMIT",
        "reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
        "symbol": str(item.get("symbol") or member.get("security_code") or member.get("symbol") or ""),
        "intent": semantic,
        "current_quantity": int(_positive_int(member.get("current_quantity"), 0)),
        "original_pc_target_weight": round(float(item.get("draft_target") or original_request_weight or 0.0), TARGET_WEIGHT_DECIMALS),
        "original_pc_increment_weight": round(float(original_request_weight), TARGET_WEIGHT_DECIMALS),
        "original_pc_target_notional": lot_resolution.get("continuous_target_notional"),
        "one_lot_weight": round(one_lot_weight, TARGET_WEIGHT_DECIMALS),
        "one_lot_notional": lot_resolution.get("one_lot_notional"),
        "target_to_one_lot_ratio": target_ratio,
        "projected_one_lot_portfolio_weight": post_trade_weight,
        "strategy_cap": single_name_cap,
        "safety_cap": safety_cap,
        "admission_decision": str(one_lot_admission.get("status") or ""),
        "admission_reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
        "final_promoted_target_weight": round(float(final_promoted_weight), TARGET_WEIGHT_DECIMALS),
        "ps_final_quantity": one_lot_quantity,
        "future_information_used": False,
    }


def _quality_adjusted_one_lot_admission(
    *,
    item: Mapping[str, Any],
    member: Mapping[str, Any],
    lot_resolution: Mapping[str, Any],
    required_weight: float,
    single_name_cap: float | None,
    soft_strategy_overshoot_allowed: bool,
) -> dict[str, Any]:
    participant_type = str(item.get("participant_type") or "NONE")
    continuous_target = _optional_ratio(lot_resolution.get("continuous_target_weight", item.get("draft_target")))
    minimum_weight = _optional_ratio(lot_resolution.get("one_lot_weight", lot_resolution.get("minimum_executable_weight")))
    if minimum_weight is None:
        minimum_weight = _optional_ratio(lot_resolution.get("minimum_policy_lot_weight"))
    baseline = round(float(item.get("baseline") or 0.0), TARGET_WEIGHT_DECIMALS)
    effective_post_trade = _optional_ratio(lot_resolution.get("post_trade_weight"))
    if effective_post_trade is None:
        effective_post_trade = round(baseline + max(required_weight, 0.0), TARGET_WEIGHT_DECIMALS)
    overshoot_weight = round(max(effective_post_trade - float(single_name_cap or effective_post_trade), 0.0), TARGET_WEIGHT_DECIMALS)
    target_basis = continuous_target if continuous_target and continuous_target > 0 else float(item.get("draft_target") or 0.0)
    overshoot_ratio = round(effective_post_trade / target_basis, 6) if target_basis > 0 else None
    boundary = str(lot_resolution.get("boundary_classification") or "")
    one_lot_fallback = bool(lot_resolution.get("one_lot_fallback_applied")) or (
        minimum_weight is not None and float(item.get("request") or 0.0) > 0 and float(item.get("request") or 0.0) < minimum_weight - TARGET_WEIGHT_ABSOLUTE_TOLERANCE
    )
    strategy_overshoot = boundary == "DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX" or soft_strategy_overshoot_allowed
    safety_preserved = lot_resolution.get("safety_hard_cap_preserved") is not False
    entry_action = str(member.get("entry_admission_action") or "")
    entry_state = str(member.get("entry_admission_state") or "")
    quality_action = str(member.get("quality_action") or "")
    add_worthiness = _add_worthiness_state(member)
    relative_opportunity = str(member.get("strategy_intelligence_relative_strength_state") or "")
    opportunity_cost = str(member.get("opportunity_cost_status") or "")
    reason_codes: list[str] = []
    status = "PASS"
    blocked_reason = ""
    tolerance = "NOT_REQUIRED"

    if not one_lot_fallback and not strategy_overshoot:
        reason_codes.append("one_lot_no_strategy_overshoot")
    elif not safety_preserved:
        status = "FAIL_CLOSED"
        blocked_reason = "minimum_lot_exceeds_safety_hard_cap"
        tolerance = "SAFETY_BLOCKED"
        reason_codes.append("safety_hard_cap_not_preserved")
    elif participant_type == "BUY_NEW" and entry_action in {"BUY_WAIT"}:
        status = "DEFER"
        blocked_reason = "quality_adjusted_one_lot_entry_buy_wait"
        tolerance = "DEFER"
        reason_codes.append("entry_admission_buy_wait_blocks_one_lot_overshoot")
    elif participant_type == "BUY_NEW" and entry_action in {"REJECT_BUY_NEW"}:
        status = "FAIL_CLOSED"
        blocked_reason = "quality_adjusted_one_lot_entry_rejected"
        tolerance = "FAIL"
        reason_codes.append("entry_admission_reject_blocks_one_lot_overshoot")
    elif participant_type == "BUY_NEW" and entry_action in {"REVIEW_REQUIRED"}:
        status = "REVIEW_REQUIRED"
        blocked_reason = "quality_adjusted_one_lot_entry_review_required"
        tolerance = "REVIEW_REQUIRED"
        reason_codes.append("entry_admission_review_blocks_one_lot_overshoot")
    elif participant_type == "BUY_NEW" and entry_state in {"OVERHEATED_DECELERATING_ENTRY", "REVERSAL_RISK_ENTRY"}:
        status = "DEFER"
        blocked_reason = "quality_adjusted_one_lot_overheated_or_reversal_entry"
        tolerance = "DEFER"
        reason_codes.append("overheated_or_reversal_entry_blocks_one_lot_overshoot")
    elif participant_type == "BUY_ADD" and add_worthiness not in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "PASS"}:
        status = "FAIL_CLOSED"
        blocked_reason = "minimum_lot_exceeds_concentration_cap"
        tolerance = "FAIL"
        reason_codes.append("add_worthiness_blocks_one_lot_overshoot")
    elif participant_type == "BUY_NEW" and entry_action in {"BUY_NEW_ALLOWED", "BUY_NEW_REDUCED_ONLY", ""}:
        tolerance = "PASS"
        reason_codes.append("entry_admission_allows_one_lot_overshoot")
    elif participant_type == "BUY_ADD":
        tolerance = "PASS"
        reason_codes.append("add_worthiness_allows_one_lot_overshoot")
    else:
        tolerance = "PASS"
        reason_codes.append("one_lot_admission_backward_compatible_pass")

    return {
        "schema_version": "one_lot_admission.v1",
        "status": status,
        "blocked_reason": blocked_reason,
        "lifecycle_intent": participant_type,
        "continuous_target_weight": continuous_target,
        "minimum_executable_weight": minimum_weight,
        "effective_post_trade_weight": effective_post_trade,
        "overshoot_weight": overshoot_weight,
        "overshoot_ratio_to_target": overshoot_ratio,
        "strategy_concentration_tolerance": tolerance,
        "safety_hard_cap_preserved": safety_preserved,
        "entry_state": entry_state,
        "entry_admission_action": entry_action,
        "buy_quality_action": quality_action,
        "add_worthiness_state": add_worthiness,
        "relative_opportunity_state": relative_opportunity,
        "opportunity_cost_state": opportunity_cost,
        "residual_destination_if_skipped": "Cash" if status in {"DEFER", "FAIL_CLOSED", "REVIEW_REQUIRED"} else str(item.get("symbol") or ""),
        "reason_codes": sorted(set(reason_codes)),
        "future_information_used": False,
    }


def _add_worthiness_state(member: Mapping[str, Any]) -> str:
    structured = str(member.get("strategy_intelligence_add_worthiness_state") or "").upper()
    if structured:
        return structured
    action = str(member.get("entry_admission_action") or "").upper()
    if action in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "NO_ADD"}:
        return action
    if str(member.get("add_allocation_eligibility_status") or "") == "PASS" and str(member.get("incremental_investment_value_state") or "") == "POSITIVE" and str(member.get("opportunity_cost_status") or "") == "PASS":
        return "PASS"
    if bool(member.get("current_position")) and str(member.get("pm_action") or "").upper() == "ADD":
        return "NO_ADD"
    return "NOT_APPLICABLE"


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
    add_worthiness_state = str(row.get("strategy_intelligence_add_worthiness_state") or "").upper()
    entry_admission_action = str(row.get("entry_admission_action") or "").upper()
    entry_admission_state = str(row.get("entry_admission_state") or "").upper()
    add_worthiness_allows_increment = add_worthiness_state in {"", "ADD_ALLOWED", "ADD_REDUCED_ONLY", "PASS"}
    entry_admission_allows_increment = entry_admission_action not in {"NO_ADD", "BUY_WAIT", "REJECT", "REVIEW_REQUIRED"} and entry_admission_state not in {
        "REVERSAL_RISK_ENTRY",
        "OVERHEATED_DECELERATING_ENTRY",
        "INSUFFICIENT_ENTRY_EVIDENCE",
    }
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
        "add_worthiness": "PASS" if add_worthiness_allows_increment else "FAIL_CLOSED",
        "entry_admission": "PASS" if entry_admission_allows_increment else "FAIL_CLOSED",
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
    if not add_worthiness_allows_increment:
        reason_codes.append("ADD_WORTHINESS_NO_ADD")
    if not entry_admission_allows_increment:
        reason_codes.append("ADD_ENTRY_ADMISSION_NO_ADD")
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
        and add_worthiness_allows_increment
        and entry_admission_allows_increment
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
        negative_new = (
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and float(score) < 0
            and not row.get("current_position")
            and not _uncalibrated_relative_score_contract(row)
        )
        quality_action = str(row.get("quality_action") or row.get("buy_quality_action") or "")
        quality_blocks_buy = quality_action in {"REJECT", "BUY_REJECTED", "REVIEW_REQUIRED", "BUY_REVIEW_REQUIRED"} or (
            quality_action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE"} and _buy_wait_applies_to_member(row)
        )
        selectable = row.get("membership_intent") == "RETAIN" or (row.get("membership_intent") == "ADD_CANDIDATE" and not negative_new and not quality_blocks_buy)
        reason_codes = {str(reason) for reason in row.get("reason_codes") or []}
        occupies_buy_slot = row.get("membership_intent") in {"RETAIN", "ADD_CANDIDATE"} or any(
            reason.startswith("opportunity_no_buy_reason_hard_block:") or reason.startswith("opportunity_no_buy_reason_present:")
            for reason in reason_codes
        )
        if occupies_buy_slot:
            candidates.append({**row, "_selection_selectable": selectable})
    quality_tier_available = any(str(row.get("selection_quality_tier") or "") for row in candidates)
    ordered = sorted(
        candidates,
        key=lambda row: (
            _selection_quality_priority(row) if quality_tier_available else 0,
            _positive_int(row.get("construction_priority"), 999999),
            str(row.get("security_code") or ""),
        ),
    )
    return [{key: value for key, value in row.items() if key != "_selection_selectable"} for row in ordered if row.get("_selection_selectable")]


def _selection_quality_priority(row: Mapping[str, Any]) -> int:
    tier = str(row.get("selection_quality_tier") or "").upper()
    return {
        "HIGH_QUALITY_CONTINUATION": 0,
        "VALID_CONTINUATION": 1,
        "CAUTION_CONTINUATION": 2,
        "INSUFFICIENT_QUALITY": 3,
        "REJECT": 4,
    }.get(tier, 2)


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
        elif not member.get("current_position") and action in {"BUY_WAIT", "TEMPORARY_BUY_INELIGIBLE"} and _buy_wait_applies_to_member(member):
            membership_intent = "EXCLUDE"
            weight_intent = "AVOID"
            reasons.append("buy_quality_wait")
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


def _attach_strategy_intelligence(
    members: list[dict[str, Any]],
    *,
    strategy_intelligence_artifact_path: Path | str | None,
    business_date: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    if strategy_intelligence_artifact_path is None:
        return members, ["strategy_intelligence_not_connected"]
    if not Path(strategy_intelligence_artifact_path).is_file():
        return members, ["strategy_intelligence_missing_fail_closed"]
    payload = strategy_intelligence.load_strategy_intelligence_artifact(strategy_intelligence_artifact_path)
    by_symbol = strategy_intelligence.symbol_intelligence_by_symbol(payload)
    reasons: list[str] = []
    updated: list[dict[str, Any]] = []
    for member in members:
        code = str(member.get("security_code") or member.get("symbol") or "").strip()
        evidence = by_symbol.get(code)
        if not evidence:
            if not member.get("current_position"):
                patched = {
                    **member,
                    "membership_intent": "UNRESOLVED",
                    "target_membership": False,
                    "weight_intent": "UNRESOLVED",
                    "quality_action": "BUY_REVIEW_REQUIRED",
                    "strategy_intelligence_consumer_status": "MISSING_SYMBOL_EVIDENCE",
                    "reason_codes": sorted(set([*list(member.get("reason_codes") or []), "strategy_intelligence_symbol_missing"])),
                }
                patched["membership_reason"] = ";".join(patched["reason_codes"])
                updated.append(patched)
            else:
                updated.append({**member, "strategy_intelligence_consumer_status": "MISSING_SYMBOL_EVIDENCE"})
            reasons.append(f"strategy_intelligence_symbol_missing:{code}")
            continue
        si_fields = _strategy_intelligence_member_fields(evidence, payload, strategy_intelligence_artifact_path)
        member_reasons = list(member.get("reason_codes") or [])
        membership_intent = str(member.get("membership_intent") or "")
        weight_intent = str(member.get("weight_intent") or "")
        quality_action = str(member.get("quality_action") or "")
        if not member.get("current_position"):
            eligibility = evidence.get("eligibility") if isinstance(evidence.get("eligibility"), Mapping) else {}
            cq = evidence.get("continuation_quality") if isinstance(evidence.get("continuation_quality"), Mapping) else {}
            entry = evidence.get("entry_admission") if isinstance(evidence.get("entry_admission"), Mapping) else {}
            selection_quality = evidence.get("selection_quality_comparator") if isinstance(evidence.get("selection_quality_comparator"), Mapping) else {}
            selection_tier = str(selection_quality.get("tier") or "").upper()
            disqualifying = list(eligibility.get("disqualifying_facts") or [])
            if str(eligibility.get("status") or "") != "PASS":
                membership_intent = "EXCLUDE" if disqualifying else "UNRESOLVED"
                weight_intent = "AVOID" if disqualifying else "UNRESOLVED"
                quality_action = "BUY_REJECTED" if disqualifying else "BUY_REVIEW_REQUIRED"
                member_reasons.append("strategy_intelligence_eligibility_not_pass")
            elif entry and str(entry.get("admission_action") or "") == "BUY_WAIT":
                membership_intent = "EXCLUDE"
                weight_intent = "AVOID"
                quality_action = "BUY_WAIT"
                member_reasons.append("strategy_intelligence_buy_wait")
                member_reasons.append("strategy_intelligence_entry_buy_wait")
            elif entry and str(entry.get("admission_action") or "") == "REJECT_BUY_NEW":
                membership_intent = "EXCLUDE"
                weight_intent = "AVOID"
                quality_action = "BUY_REJECTED"
                member_reasons.append("strategy_intelligence_entry_rejected")
            elif entry and str(entry.get("admission_action") or "") == "REVIEW_REQUIRED":
                membership_intent = "UNRESOLVED"
                weight_intent = "UNRESOLVED"
                quality_action = "BUY_REVIEW_REQUIRED"
                member_reasons.append("strategy_intelligence_entry_review_required")
            elif entry and str(entry.get("admission_action") or "") == "BUY_NEW_REDUCED_ONLY":
                quality_action = "REDUCED_ALLOCATION_ONLY"
                member_reasons.append("strategy_intelligence_entry_reduced_allocation_only")
            elif entry and str(entry.get("admission_action") or "") == "BUY_NEW_ALLOWED":
                quality_action = quality_action if quality_action in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY"} else "SI_EVIDENCE_ELIGIBLE"
                member_reasons.append("strategy_intelligence_entry_allowed")
            elif selection_tier == "REJECT":
                membership_intent = "EXCLUDE"
                weight_intent = "AVOID"
                quality_action = "BUY_REJECTED"
                member_reasons.append("strategy_intelligence_selection_quality_reject")
            elif selection_tier == "INSUFFICIENT_QUALITY":
                membership_intent = "UNRESOLVED"
                weight_intent = "UNRESOLVED"
                quality_action = "BUY_REVIEW_REQUIRED"
                member_reasons.append("strategy_intelligence_selection_quality_insufficient")
            elif str(cq.get("status") or "") != "PASS":
                membership_intent = "EXCLUDE"
                weight_intent = "AVOID"
                quality_action = "BUY_WAIT"
                member_reasons.append("strategy_intelligence_buy_wait")
            else:
                quality_action = "SI_EVIDENCE_ELIGIBLE"
                member_reasons.append("strategy_intelligence_buy_evidence_pass")
            if selection_tier in {"HIGH_QUALITY_CONTINUATION", "VALID_CONTINUATION"}:
                member_reasons.append("selection_quality_rank_score_supporting_only")
            elif selection_tier == "CAUTION_CONTINUATION":
                member_reasons.append("selection_quality_caution_continuation")
        patched = {
            **member,
            **si_fields,
            "legacy_buy_quality_action": str(member.get("quality_action") or ""),
            "quality_action": quality_action,
            "membership_intent": membership_intent,
            "target_membership": membership_intent in {"RETAIN", "ADD_CANDIDATE"},
            "weight_intent": weight_intent,
            "membership_reason": ";".join(sorted(set(member_reasons))),
            "reason_codes": sorted(set(member_reasons)),
        }
        updated.append(patched)
    return updated, sorted(set(reasons))


def _strategy_intelligence_member_fields(
    evidence: Mapping[str, Any],
    payload: Mapping[str, Any],
    artifact_path: Path | str,
) -> dict[str, Any]:
    eligibility = evidence.get("eligibility") if isinstance(evidence.get("eligibility"), Mapping) else {}
    cq = evidence.get("continuation_quality") if isinstance(evidence.get("continuation_quality"), Mapping) else {}
    risk = evidence.get("downside_risk") if isinstance(evidence.get("downside_risk"), Mapping) else {}
    edge = evidence.get("expected_edge") if isinstance(evidence.get("expected_edge"), Mapping) else {}
    entry = evidence.get("entry_admission") if isinstance(evidence.get("entry_admission"), Mapping) else {}
    selection_quality = evidence.get("selection_quality_comparator") if isinstance(evidence.get("selection_quality_comparator"), Mapping) else {}
    lifecycle = evidence.get("lifecycle_context") if isinstance(evidence.get("lifecycle_context"), Mapping) else {}
    profit = evidence.get("profit_protection_evidence") if isinstance(evidence.get("profit_protection_evidence"), Mapping) else {}
    relative = cq.get("relative_strength") if isinstance(cq.get("relative_strength"), Mapping) else {}
    add_history = lifecycle.get("add_history_summary") if isinstance(lifecycle.get("add_history_summary"), Mapping) else {}
    reduce_history = lifecycle.get("reduce_history_summary") if isinstance(lifecycle.get("reduce_history_summary"), Mapping) else {}
    add_worthiness = _campaign_aware_add_worthiness_state(
        lifecycle=lifecycle,
        cq=cq,
        risk=risk,
        profit=profit,
        entry=entry,
    )
    return {
        "strategy_intelligence_consumer_status": "CONNECTED",
        "strategy_intelligence_artifact_path": str(artifact_path),
        "strategy_intelligence_artifact_hash": str(payload.get("artifact_hash") or ""),
        "strategy_intelligence_business_date": str(payload.get("business_date") or ""),
        "strategy_intelligence_eligibility_status": str(eligibility.get("status") or ""),
        "strategy_intelligence_continuation_quality_status": str(cq.get("status") or ""),
        "strategy_intelligence_downside_risk_status": str(risk.get("status") or ""),
        "strategy_intelligence_relative_strength_state": str(relative.get("state") or ""),
        "strategy_intelligence_expected_edge_calibration_status": str(edge.get("calibration_status") or ""),
        "strategy_intelligence_expected_edge_economic_units_available": bool(edge.get("economic_units_available", False)),
        "strategy_intelligence_campaign_id": str(lifecycle.get("position_campaign_id") or ""),
        "strategy_intelligence_campaign_identity_authority_status": str(lifecycle.get("campaign_identity_authority_status") or ""),
        "strategy_intelligence_campaign_age_business_days": lifecycle.get("campaign_age_business_days"),
        "strategy_intelligence_current_campaign_relative_return": lifecycle.get("current_campaign_relative_return"),
        "strategy_intelligence_observed_campaign_mfe": lifecycle.get("observed_campaign_mfe"),
        "strategy_intelligence_observed_giveback": lifecycle.get("observed_giveback"),
        "strategy_intelligence_add_history_count": int(add_history.get("event_count") or 0),
        "strategy_intelligence_reduce_history_count": int(reduce_history.get("event_count") or 0),
        "strategy_intelligence_profit_protection_status": str(profit.get("status") or ""),
        "strategy_intelligence_add_worthiness_state": add_worthiness,
        "strategy_intelligence_lifecycle_quality_connected": True,
        "entry_admission": dict(entry),
        "entry_admission_state": str(entry.get("entry_state") or ""),
        "entry_admission_action": str(entry.get("admission_action") or ""),
        "entry_admission_evidence_sufficiency": str(entry.get("evidence_sufficiency") or ""),
        "selection_quality_comparator": dict(selection_quality),
        "selection_quality_tier": str(selection_quality.get("tier") or ""),
        "selection_quality_reason_codes": list(selection_quality.get("reason_codes") or []),
        "selection_quality_evidence_sufficiency": str(selection_quality.get("evidence_sufficiency") or ""),
        "selection_quality_rank_score_role": str(selection_quality.get("rank_score_role") or ""),
        "selection_quality_expected_edge_role": str(selection_quality.get("expected_edge_role") or ""),
        "selection_quality_not_action_authority": bool(selection_quality.get("not_action_authority", True)),
        "selection_quality_score_only_hard_rejection_retired": bool(selection_quality.get("score_only_hard_rejection_retired", False)),
        "selection_quality_below_top20_only_hard_rejection_retired": bool(selection_quality.get("below_top20_only_hard_rejection_retired", False)),
        "strategy_intelligence_not_action_authority": True,
        "strategy_intelligence_production_evidence": True,
        "strategy_intelligence_future_information_used": bool(
            (evidence.get("provenance") if isinstance(evidence.get("provenance"), Mapping) else {}).get("future_information_used", False)
        ),
    }


def _campaign_aware_add_worthiness_state(
    *,
    lifecycle: Mapping[str, Any],
    cq: Mapping[str, Any],
    risk: Mapping[str, Any],
    profit: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> str:
    entry_action = str(entry.get("admission_action") or "").upper()
    if entry_action in {"ADD_ALLOWED", "ADD_REDUCED_ONLY", "NO_ADD"}:
        return entry_action
    if str(lifecycle.get("current_position_state") or "").upper() != "HELD":
        return "NOT_APPLICABLE"
    if str(lifecycle.get("campaign_identity_authority_status") or "").upper() != "COMPLETE":
        return "NO_ADD"
    add_history = lifecycle.get("add_history_summary") if isinstance(lifecycle.get("add_history_summary"), Mapping) else {}
    reduce_history = lifecycle.get("reduce_history_summary") if isinstance(lifecycle.get("reduce_history_summary"), Mapping) else {}
    if int(add_history.get("event_count") or 0) >= 5:
        return "NO_ADD"
    if int(reduce_history.get("event_count") or 0) > 0:
        return "NO_ADD"
    if str(cq.get("status") or "").upper() != "PASS":
        return "NO_ADD"
    if str(risk.get("status") or "").upper() not in {"PASS", "REVIEW_REQUIRED", ""}:
        return "NO_ADD"
    if str(profit.get("status") or "").upper() in {"OBSERVED", "PASS", "PARTIAL", "NOT_APPLICABLE", ""}:
        return "ADD_ALLOWED"
    return "NO_ADD"


def _buy_wait_applies_to_member(row: Mapping[str, Any]) -> bool:
    semantic = str(row.get("semantic_buy_type") or row.get("buy_semantic") or "").upper()
    if semantic and semantic != "BUY_NEW":
        return False
    return not bool(row.get("current_position"))


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
        "momentum_trajectory_schema_version": str(decision.get("momentum_trajectory_schema_version") or ""),
        "momentum_trajectory_classification": str(decision.get("momentum_trajectory_classification") or ""),
        "momentum_trajectory_status": str(decision.get("momentum_trajectory_status") or ""),
        "momentum_trajectory_action": str(decision.get("momentum_trajectory_action") or ""),
        "momentum_trajectory_component_score": decision.get("momentum_trajectory_component_score"),
        "momentum_trajectory_reason_codes": list(decision.get("momentum_trajectory_reason_codes") or []),
        "momentum_trajectory_feature_snapshot": dict(decision.get("momentum_trajectory_feature_snapshot") or {}),
        "momentum_trajectory_authority": dict(decision.get("momentum_trajectory_authority") or {}),
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
            "momentum_trajectory_classification": str(decision.get("momentum_trajectory_classification") or ""),
            "momentum_trajectory_action": str(decision.get("momentum_trajectory_action") or ""),
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


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _opportunity_score_semantic_contract(*, row: Mapping[str, Any], summary: Mapping[str, Any] | None) -> dict[str, Any]:
    summary = summary or {}
    canonical_score_field = str(row.get("canonical_score_field") or summary.get("canonical_score_field") or "")
    score_semantic_role = str(
        row.get("score_semantic_role")
        or row.get("semantic_role")
        or summary.get("score_semantic_role")
        or summary.get("semantic_role")
        or ""
    )
    calibration_applied = _optional_bool(row.get("calibration_applied"))
    if calibration_applied is None:
        calibration_applied = _optional_bool(summary.get("calibration_applied"))
    economic_units_available = _optional_bool(row.get("economic_units_available"))
    if economic_units_available is None:
        economic_units_available = _optional_bool(summary.get("economic_units_available"))
    missing = []
    if not canonical_score_field:
        missing.append("canonical_score_field")
    if not score_semantic_role:
        missing.append("score_semantic_role")
    if calibration_applied is None:
        missing.append("calibration_applied")
    if economic_units_available is None:
        missing.append("economic_units_available")
    is_uncalibrated_relative = (
        canonical_score_field == "runtime_opportunity_score"
        and score_semantic_role == "uncalibrated_relative_model_score"
        and calibration_applied is False
        and economic_units_available is False
    )
    return {
        "canonical_score_field": canonical_score_field,
        "score_semantic_role": score_semantic_role,
        "calibration_applied": calibration_applied,
        "economic_units_available": economic_units_available,
        "is_uncalibrated_relative_score": is_uncalibrated_relative,
        "semantic_metadata_complete": not missing,
        "missing_fields": missing,
    }


def _no_buy_reason_parts(no_buy_reason: Any) -> set[str]:
    return {part.strip().lower() for part in str(no_buy_reason or "").split("|") if part.strip()}


def _classify_opportunity_no_buy_reason(no_buy_reason: Any, *, score_contract: Mapping[str, Any]) -> dict[str, Any]:
    reasons = {reason for reason in _no_buy_reason_parts(no_buy_reason) if reason not in {"", "none", "nan", "null"}}
    hard_reasons = sorted(reasons & OPPORTUNITY_HARD_NO_BUY_REASONS)
    soft_relative_reasons = sorted(reasons & OPPORTUNITY_RELATIVE_METADATA_NO_BUY_REASONS)
    unknown_reasons = sorted(reasons - OPPORTUNITY_HARD_NO_BUY_REASONS - OPPORTUNITY_RELATIVE_METADATA_NO_BUY_REASONS)
    semantic_metadata_complete = bool(score_contract.get("semantic_metadata_complete"))
    uncalibrated_relative = bool(score_contract.get("is_uncalibrated_relative_score"))
    if not reasons:
        return {
            "status": "PASS",
            "blocks_buy": False,
            "no_buy_reason": "",
            "hard_blocking_reasons": [],
            "soft_relative_reasons": [],
            "unknown_reasons": [],
            "score_contract": dict(score_contract),
            "review_reason": "",
        }
    if hard_reasons or unknown_reasons:
        return {
            "status": "BLOCKED",
            "blocks_buy": True,
            "no_buy_reason": str(no_buy_reason or ""),
            "hard_blocking_reasons": [*hard_reasons, *unknown_reasons],
            "soft_relative_reasons": soft_relative_reasons,
            "unknown_reasons": unknown_reasons,
            "score_contract": dict(score_contract),
            "review_reason": "",
        }
    if not semantic_metadata_complete:
        return {
            "status": "REVIEW_REQUIRED",
            "blocks_buy": True,
            "no_buy_reason": str(no_buy_reason or ""),
            "hard_blocking_reasons": sorted(reasons),
            "soft_relative_reasons": [],
            "unknown_reasons": [],
            "score_contract": dict(score_contract),
            "review_reason": "semantic_metadata_missing",
        }
    economic_units_available = bool(score_contract.get("economic_units_available"))
    if economic_units_available and "non_positive_expected_edge_score" in reasons:
        return {
            "status": "BLOCKED",
            "blocks_buy": True,
            "no_buy_reason": str(no_buy_reason or ""),
            "hard_blocking_reasons": ["non_positive_expected_edge_score"],
            "soft_relative_reasons": sorted(reasons - {"non_positive_expected_edge_score"}),
            "unknown_reasons": [],
            "score_contract": dict(score_contract),
            "review_reason": "",
        }
    return {
        "status": "PASS" if uncalibrated_relative else "REVIEW_REQUIRED",
        "blocks_buy": not uncalibrated_relative,
        "no_buy_reason": str(no_buy_reason or ""),
        "hard_blocking_reasons": [] if uncalibrated_relative else sorted(reasons),
        "soft_relative_reasons": soft_relative_reasons if uncalibrated_relative else [],
        "unknown_reasons": [],
        "score_contract": dict(score_contract),
        "review_reason": "" if uncalibrated_relative else "unsupported_score_semantic_contract",
    }


def _uncalibrated_relative_score_contract(row: Mapping[str, Any]) -> bool:
    authority = row.get("runtime_opportunity_score_authority")
    if not isinstance(authority, Mapping):
        return False
    return (
        str(authority.get("canonical_field") or "") == "runtime_opportunity_score"
        and str(authority.get("score_semantic_role") or "") == "uncalibrated_relative_model_score"
        and authority.get("calibration_applied") is False
        and authority.get("economic_units_available") is False
    )


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
    opportunity_score_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if opportunity:
        source_field = _score_source_field(opportunity, ("runtime_opportunity_score", "expected_edge_score", "opportunity_score", "score"))
        if source_field:
            score = _finite_number(opportunity.get(source_field))
            if score is not None:
                score_contract = _opportunity_score_semantic_contract(row=opportunity, summary=opportunity_score_summary or {})
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
                    "score_semantic_role": score_contract["score_semantic_role"],
                    "transformation_stage": str(opportunity.get("transformation_stage") or "accepted_generation_bound_imputer_scaler_model"),
                    "calibration_applied": score_contract["calibration_applied"],
                    "economic_units_available": score_contract["economic_units_available"],
                    "semantic_metadata_complete": score_contract["semantic_metadata_complete"],
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
        "strategy_intelligence_add_worthiness_state",
        "entry_admission_state",
        "entry_admission_action",
        "position_campaign_id",
        "campaign_id",
        "strategy_intelligence_campaign_id",
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
