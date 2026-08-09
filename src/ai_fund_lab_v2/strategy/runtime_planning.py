from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import opportunity_no_buy_reason_blocks_buy
from ai_fund_lab_v2.strategy import capital_deployment, portfolio_construction
from ai_fund_lab_v2.strategy.candidate_opportunity_compatibility import (
    INCOMPATIBLE_DATE,
    INCOMPATIBLE_HASH,
    INCOMPATIBLE_SCHEMA,
    SOURCE_BLOCKED,
    SOURCE_MISSING,
    SOURCE_NOT_ELIGIBLE,
    SOURCE_REVIEW_REQUIRED,
)
from ai_fund_lab_v2.strategy.status_contract import compatibility_status_from_payload, status_contract_fields


SCHEMA_VERSION = "runtime_planning.v1"
PRODUCER_VERSION = "phase22_g_runtime_planning_producer.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "ELIGIBLE"
QUANTITY_AUTHORITY = "PHASE22_J_POSITION_SIZING"
CANONICAL_QUANTITY_AUTHORITY = "PHASE27_D2D_POSITION_SIZING_PLAN"

PLANNING_INTENTS = {"BUY_NEW", "BUY_ADD", "SELL_REDUCE", "SELL_EXIT", "NO_ACTION", "NO_ORDER", "UNRESOLVED"}
ORDER_SIDE_INTENTS = {"BUY", "SELL", "NONE", "UNRESOLVED"}
PENDING_ELIGIBILITIES = {"CANDIDATE_ONLY", "NOT_REQUIRED", "REVIEW_REQUIRED", "BLOCKED"}
QUANTITY_STATUSES = {
    "RESOLVED_EXECUTABLE",
    "RESOLVED_ZERO_ALLOCATION",
    "RESOLVED_ZERO_DELTA",
    "RESOLVED_CANDIDATE",
    "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
    "NO_ORDER_MINIMUM_NOTIONAL_UNMET",
    "PRICE_UNAVAILABLE",
    "REVIEW_REQUIRED_MISSING_PRICE",
    "REVIEW_REQUIRED_MISSING_TRADABLE_UNIT",
    "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED",
    "UNRESOLVED",
    "NOT_REQUIRED",
}
SOURCE_AUTHORITY_STATUSES = {"VALID", "MISSING", "STALE", "HASH_MISMATCH", "AUTHORITY_CONFLICT"}
PRODUCER_RESULT_STATUSES = {"PASS", "REVIEW_REQUIRED", "BLOCK"}
RUNTIME_CONSUMER_ELIGIBILITIES = {"ELIGIBLE", "NOT_ELIGIBLE", "REVIEW_REQUIRED", "BLOCKED"}
ARTIFACT_LIFECYCLE_STATUSES = {"DRAFT", "VALIDATED", "REVIEW_REQUIRED", "ACCEPTED", "LEGACY", "REVOKED", "REJECTED"}
BLOCKING_UPSTREAM_STATUSES = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING}
REVIEW_UPSTREAM_STATUSES = {SOURCE_REVIEW_REQUIRED, SOURCE_NOT_ELIGIBLE}
FORBIDDEN_CONCRETE_FIELDS = {
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
    "order_price",
    "pending_id",
    "pending_item",
    "submit_command",
    "broker_request",
}


class RuntimePlanningError(RuntimeError):
    pass


class RuntimePlanningSchemaError(RuntimePlanningError):
    pass


class RuntimePlanningConsumerError(RuntimePlanningError):
    pass


@dataclass(frozen=True)
class RuntimePlanningSourceSummary:
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
class RuntimePlanningProducerResult:
    status: str
    reason: str
    artifact_path: str
    artifact_hash: str
    payload: dict[str, Any]
    evidence: dict[str, Any]


def default_runtime_artifact_path(runtime_root: Path | str, business_date: str) -> Path:
    return Path(runtime_root) / "strategy_artifacts" / "runtime_planning" / business_date / "runtime_planning.json"


def produce_runtime_planning_artifact(
    *,
    business_date: str,
    portfolio_construction_artifact_path: Path | str | None,
    capital_deployment_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    current_portfolio_summary: RuntimePlanningSourceSummary,
    current_cash_summary: RuntimePlanningSourceSummary,
    current_position_summary: RuntimePlanningSourceSummary,
    pending_summary: RuntimePlanningSourceSummary,
    planning_config_summary: RuntimePlanningSourceSummary,
    output_path: Path | str,
    position_sizing_artifact_path: Path | str | None = None,
    position_sizing_plan_artifact_path: Path | str | None = None,
    opportunity_artifact_path: Path | str | None = None,
    as_of: str | None = None,
) -> RuntimePlanningProducerResult:
    payload, evidence = build_runtime_planning_payload(
        business_date=business_date,
        portfolio_construction_artifact_path=portfolio_construction_artifact_path,
        capital_deployment_artifact_path=capital_deployment_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        position_management_artifact_path=position_management_artifact_path,
        position_sizing_artifact_path=position_sizing_artifact_path,
        position_sizing_plan_artifact_path=position_sizing_plan_artifact_path,
        current_portfolio_summary=current_portfolio_summary,
        current_cash_summary=current_cash_summary,
        current_position_summary=current_position_summary,
        pending_summary=pending_summary,
        planning_config_summary=planning_config_summary,
        as_of=as_of,
        opportunity_artifact_path=opportunity_artifact_path,
    )
    validate_runtime_planning_artifact(payload)
    artifact_hash = runtime_planning_hash(payload)
    final_payload = {**payload, "artifact_hash": artifact_hash}
    path = Path(output_path)
    _write_json(path, final_payload)
    return RuntimePlanningProducerResult(
        status=str(final_payload["producer_result_status"]),
        reason=",".join(final_payload.get("reason_codes") or []),
        artifact_path=str(path),
        artifact_hash=artifact_hash,
        payload=final_payload,
        evidence=evidence,
    )


def build_runtime_planning_payload(
    *,
    business_date: str,
    portfolio_construction_artifact_path: Path | str | None,
    capital_deployment_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    current_portfolio_summary: RuntimePlanningSourceSummary,
    current_cash_summary: RuntimePlanningSourceSummary,
    current_position_summary: RuntimePlanningSourceSummary,
    pending_summary: RuntimePlanningSourceSummary,
    planning_config_summary: RuntimePlanningSourceSummary,
    position_sizing_artifact_path: Path | str | None = None,
    position_sizing_plan_artifact_path: Path | str | None = None,
    as_of: str | None = None,
    opportunity_artifact_path: Path | str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")

    construction_result = capital_deployment.validate_portfolio_construction_compatibility(
        portfolio_construction_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    deployment_result = _merged_capital_deployment_reference(
        capital_deployment_artifact_path,
        requested_business_date=business_date,
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

    producer_status = "PASS"
    source_status = "VALID"
    reason_codes: list[str] = []
    upstream_statuses = [
        construction_result["status"],
        policy_result["status"],
        pm_result["status"],
    ]
    if any(status in BLOCKING_UPSTREAM_STATUSES for status in upstream_statuses):
        producer_status = "BLOCK"
        source_status = "HASH_MISMATCH" if INCOMPATIBLE_HASH in upstream_statuses else ("MISSING" if SOURCE_MISSING in upstream_statuses else "AUTHORITY_CONFLICT")
        reason_codes.extend(f"upstream_block:{status}" for status in upstream_statuses if status in BLOCKING_UPSTREAM_STATUSES)
    elif any(status in REVIEW_UPSTREAM_STATUSES for status in upstream_statuses):
        reason_codes.extend(f"upstream_review_required:{status}" for status in upstream_statuses if status in REVIEW_UPSTREAM_STATUSES)

    summaries = {
        "current_portfolio": current_portfolio_summary.to_dict(requested_business_date=business_date),
        "current_cash": current_cash_summary.to_dict(requested_business_date=business_date),
        "current_position": current_position_summary.to_dict(requested_business_date=business_date),
        "pending": pending_summary.to_dict(requested_business_date=business_date),
        "planning_config": {
            **planning_config_summary.to_dict(requested_business_date=business_date),
            "status": "NON_CANONICAL_OBSERVABILITY",
            "authority_deleted": True,
        },
    }
    for name, summary in (
        ("current_portfolio", current_portfolio_summary),
        ("current_cash", current_cash_summary),
        ("current_position", current_position_summary),
        ("pending", pending_summary),
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

    pc_payload = _load_json_if_valid(portfolio_construction_artifact_path)
    cd_payload = _load_json_if_valid(capital_deployment_artifact_path)
    pm_payload = _load_json_if_valid(position_management_artifact_path)
    ps_payload = _load_json_if_valid(position_sizing_artifact_path)
    canonical_ps_payload = _load_json_if_valid(position_sizing_plan_artifact_path)
    canonical_ps_status = _position_sizing_plan_source_status(
        canonical_ps_payload,
        position_sizing_plan_artifact_path,
        business_date=business_date,
    )
    if canonical_ps_status == "BLOCK":
        producer_status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
        reason_codes.append("upstream_block:position_sizing_plan")
    elif canonical_ps_status == "REVIEW_REQUIRED" and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"
        reason_codes.append("upstream_review_required:position_sizing_plan")
    opportunity_payload = _load_json_if_valid(opportunity_artifact_path)
    selected_ps_payload, quantity_source_mode = _select_runtime_quantity_source(
        legacy_ps_payload=ps_payload,
        canonical_ps_payload=canonical_ps_payload,
        canonical_path=position_sizing_plan_artifact_path,
    )
    plans, mapping_reasons = _build_plans(
        business_date=business_date,
        pc_payload=pc_payload,
        cd_payload=cd_payload,
        pm_payload=pm_payload,
        ps_payload=selected_ps_payload,
        quantity_source_mode=quantity_source_mode,
        opportunity_payload=opportunity_payload,
        opportunity_artifact_path=opportunity_artifact_path,
        current_position_rows=current_position_summary.rows,
        pending_rows=pending_summary.rows,
        source_hash_seed=_source_hash_seed(
            portfolio_construction_artifact_path,
            capital_deployment_artifact_path,
            portfolio_policy_artifact_path,
            position_management_artifact_path,
            position_sizing_artifact_path,
            position_sizing_plan_artifact_path,
            current_portfolio_summary,
            current_cash_summary,
            current_position_summary,
            pending_summary,
            planning_config_summary,
        ),
    )
    reason_codes.extend(mapping_reasons)
    if any(reason.startswith(("planning_conflict_block", "missing_current_position_for_sell", "add_without_current_position")) for reason in mapping_reasons):
        producer_status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
    elif any(reason.startswith(("planning_conflict_review", "unresolved_mapping", "review_required_", "existing_pending_conflict", "upstream_block_propagation")) for reason in mapping_reasons) and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"

    feature_date = min(
        [
            value
            for value in (
                construction_result.get("feature_date"),
            policy_result.get("feature_date"),
            pm_result.get("feature_date"),
                current_portfolio_summary.feature_date,
                current_cash_summary.feature_date,
                current_position_summary.feature_date,
                pending_summary.feature_date,
            )
            if value
        ]
        or [business_date]
    )
    future_leakage_used = any(
        value and value > business_date
        for value in (
            feature_date,
            current_portfolio_summary.feature_date,
            current_cash_summary.feature_date,
            current_position_summary.feature_date,
            pending_summary.feature_date,
        )
    )
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_current_or_pending_date_detected")

    source_artifacts = [
        {"role": "portfolio_construction", "path": str(portfolio_construction_artifact_path or ""), "required": True, "status": construction_result["status"]},
        {"role": "capital_deployment", "path": str(capital_deployment_artifact_path or ""), "required": False, "status": deployment_result["status"]},
        {"role": "portfolio_policy", "path": str(portfolio_policy_artifact_path or ""), "required": True, "status": policy_result["status"]},
        {"role": "position_management", "path": str(position_management_artifact_path or ""), "required": True, "status": pm_result["status"]},
        {"role": "position_sizing", "path": str(position_sizing_artifact_path or ""), "required": False, "status": _position_sizing_source_status(ps_payload, position_sizing_artifact_path)},
        {"role": "position_sizing_plan", "path": str(position_sizing_plan_artifact_path or ""), "required": False, "status": canonical_ps_status},
        {"role": "opportunity_ranking", "path": str(opportunity_artifact_path or ""), "required": False, "status": _opportunity_source_status(opportunity_payload, opportunity_artifact_path, business_date=business_date)},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "required": True, "status": current_portfolio_summary.status},
        {"role": "current_cash", "path": current_cash_summary.source_ref, "required": True, "status": current_cash_summary.status},
        {"role": "current_position", "path": current_position_summary.source_ref, "required": True, "status": current_position_summary.status},
        {"role": "pending", "path": pending_summary.source_ref, "required": True, "status": pending_summary.status},
        {"role": "planning_config", "path": planning_config_summary.source_ref, "required": False, "status": "NON_CANONICAL_OBSERVABILITY"},
    ]
    source_hashes = _source_hashes(
        portfolio_construction_artifact_path,
        capital_deployment_artifact_path,
        portfolio_policy_artifact_path,
        position_management_artifact_path,
        position_sizing_artifact_path,
        position_sizing_plan_artifact_path,
        opportunity_artifact_path,
        current_portfolio_summary,
        current_cash_summary,
        current_position_summary,
        pending_summary,
        planning_config_summary,
    )
    if not source_hashes or any(not item["sha256"] for item in source_hashes):
        producer_status = "BLOCK"
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
        "planning_intent_taxonomy": sorted(PLANNING_INTENTS),
        "order_side_intent_taxonomy": sorted(ORDER_SIDE_INTENTS),
        "plans": plans,
        "plan_count": len(plans),
        "concrete_allocation_decided": False,
        "concrete_quantity_decided": False,
        "lot_rounding_decided": False,
        "pending_written": False,
        "submit_generated": False,
        "reason_codes": sorted(set(reason_codes)),
        "upstream_artifacts": {
            "portfolio_construction": construction_result,
            "capital_deployment": deployment_result,
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
            "previous_day_runtime_planning_copied": False,
        },
        "production_consumer_connected": False,
        "pending_writer_connected": True,
        "runtime_switch_performed": True,
        "legacy_authority_active": False,
        "legacy_planning_authority_used": False,
        "planning_fallback_used": False,
        "planning_config_authority_used": False,
        "planning_authority_winner": "strategy_runtime_planning",
        "planning_source": "runtime_planning.v1",
        "canonical_quantity_source": quantity_source_mode,
        "canonical_quantity_delta_priority": quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN",
        "pm_fallback_scope": "LEGACY_COMPATIBILITY_ONLY" if quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN" else "LEGACY_COMPATIBILITY",
        "existing_morning_planning_changed": True,
        "existing_add_planning_changed": True,
        "existing_sell_planning_changed": False,
        "pending_changed": True,
        "approval_changed": False,
        "submit_changed": False,
        "execution_changed": False,
    }
    evidence = {
        "schema_version": "phase22_g_runtime_planning_producer_evidence.v1",
        "business_date": business_date,
        "producer_result_status": producer_status,
        "plan_count": len(plans),
        "portfolio_construction_status": construction_result["status"],
        "capital_deployment_status": deployment_result["status"],
        "portfolio_policy_status": policy_result["status"],
        "position_management_status": pm_result["status"],
        "reason_codes": payload["reason_codes"],
    }
    return payload, evidence


def validate_capital_deployment_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return _missing_upstream("capital_deployment", requested_business_date, str(path or ""))
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        capital_deployment.validate_capital_deployment_artifact(payload)
    except Exception as exc:
        return {
            **_missing_upstream("capital_deployment", requested_business_date, str(path)),
            "status": INCOMPATIBLE_SCHEMA,
            "reason_codes": [f"schema_validation_failed:{exc}"],
        }
    expected_hash = str(payload.get("artifact_hash") or "")
    actual_hash = capital_deployment.capital_deployment_hash(payload)
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
        "artifact_kind": "capital_deployment",
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


def _merged_capital_deployment_reference(path: Path | str | None, *, requested_business_date: str) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return {
            "artifact_kind": "capital_deployment",
            "artifact_path": str(path or ""),
            "schema_version": "",
            "status": "MERGED_INTO_RUNTIME_PLANNING",
            "schema_compatible": True,
            "shadow_read_allowed": True,
            "production_decision_allowed": False,
            "business_date": requested_business_date,
            "feature_date": requested_business_date,
            "business_date_aligned": True,
            "feature_date_point_in_time": True,
            "artifact_hash_valid": True,
            "lifecycle_status": "MERGED",
            "producer_result_status": "NOT_APPLICABLE",
            "runtime_consumer_eligibility": "NOT_APPLICABLE",
            "reason_codes": ["capital_deployment_public_decision_stage_removed"],
        }
    result = validate_capital_deployment_compatibility(path, requested_business_date=requested_business_date, production_use_requested=False)
    return {**result, "status": "NON_CANONICAL_OBSERVABILITY", "production_decision_allowed": False, "reason_codes": sorted(set([*result.get("reason_codes", []), "capital_deployment_noncanonical_observability"]))}


def validate_runtime_planning_artifact(payload: dict[str, Any]) -> dict[str, Any]:
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
        "plans",
        "plan_count",
        "concrete_allocation_decided",
        "concrete_quantity_decided",
        "lot_rounding_decided",
        "pending_written",
        "submit_generated",
        "source_artifacts",
        "source_hashes",
        "temporal_safety",
        "production_consumer_connected",
        "pending_writer_connected",
        "runtime_switch_performed",
        "legacy_authority_active",
        "legacy_planning_authority_used",
        "planning_fallback_used",
        "planning_config_authority_used",
        "planning_authority_winner",
        "planning_source",
    }
    errors.extend(f"required_field_missing:{field}" for field in sorted(required - set(payload)))
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    _enum_check(errors, payload, "artifact_lifecycle_status", ARTIFACT_LIFECYCLE_STATUSES)
    _enum_check(errors, payload, "source_authority_status", SOURCE_AUTHORITY_STATUSES)
    _enum_check(errors, payload, "producer_result_status", PRODUCER_RESULT_STATUSES)
    _enum_check(errors, payload, "runtime_consumer_eligibility", RUNTIME_CONSUMER_ELIGIBILITIES)
    if payload.get("artifact_lifecycle_status") != ARTIFACT_LIFECYCLE_STATUS:
        errors.append("phase22_g_artifact_lifecycle_must_be_draft")
    if payload.get("runtime_consumer_eligibility") != RUNTIME_CONSUMER_ELIGIBILITY:
        errors.append("phase26_step5_runtime_consumer_eligibility_must_be_eligible")
    for field in (
        "concrete_allocation_decided",
        "concrete_quantity_decided",
        "lot_rounding_decided",
        "pending_written",
        "submit_generated",
        "production_consumer_connected",
        "existing_sell_planning_changed",
        "approval_changed",
        "submit_changed",
        "execution_changed",
    ):
        if payload.get(field) is not False:
            errors.append(f"phase22_g_field_must_be_false:{field}")
    for field in (
        "pending_writer_connected",
        "runtime_switch_performed",
        "existing_morning_planning_changed",
        "existing_add_planning_changed",
        "pending_changed",
    ):
        if payload.get(field) is not True:
            errors.append(f"phase26_step5_field_must_be_true:{field}")
    if payload.get("legacy_authority_active") is not False:
        errors.append("phase26_step5_legacy_authority_must_be_inactive")
    if payload.get("legacy_planning_authority_used") is not False:
        errors.append("phase26_step5_legacy_planning_authority_used_must_be_false")
    if payload.get("planning_fallback_used") is not False:
        errors.append("phase26_step5_planning_fallback_used_must_be_false")
    if payload.get("planning_config_authority_used") is not False:
        errors.append("phase26_step5_planning_config_authority_used_must_be_false")
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
    plans = payload.get("plans")
    if not isinstance(plans, list):
        errors.append("plans_not_list")
    else:
        if payload.get("plan_count") != len(plans):
            errors.append("plan_count_mismatch")
        ids: set[str] = set()
        by_security: dict[str, set[str]] = {}
        for index, plan in enumerate(plans):
            errors.extend(_validate_plan(plan, index=index))
            if isinstance(plan, dict):
                planning_id = str(plan.get("planning_id") or "")
                if planning_id in ids:
                    errors.append(f"duplicate_planning_id:{planning_id}")
                ids.add(planning_id)
                by_security.setdefault(str(plan.get("security_code") or ""), set()).add(str(plan.get("planning_intent") or ""))
        for security_code, intents in by_security.items():
            if {"BUY_NEW", "BUY_ADD"} <= intents:
                errors.append(f"buy_new_buy_add_conflict:{security_code}")
            if intents & {"BUY_NEW", "BUY_ADD"} and intents & {"SELL_REDUCE", "SELL_EXIT"}:
                errors.append(f"buy_sell_conflict:{security_code}")
            if {"SELL_REDUCE", "SELL_EXIT"} <= intents:
                errors.append(f"reduce_exit_conflict:{security_code}")
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
        if temporal.get("previous_day_runtime_planning_copied") is not False:
            errors.append("previous_day_runtime_planning_copy_forbidden")
    if errors:
        raise RuntimePlanningSchemaError(";".join(errors))
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
        return {"status": "BLOCK", "reason": "source_missing", "mismatches": [], "missing": missing}
    return {"status": "PASS", "reason": "source_hashes_match", "mismatches": [], "missing": []}


def load_runtime_planning_fixture(path: Path | str, *, for_production: bool = False) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_runtime_planning_artifact(payload)
    if payload.get("producer_result_status") == "BLOCK":
        raise RuntimePlanningConsumerError("BLOCK Runtime Planning artifact is not fixture-consumable")
    if for_production:
        raise RuntimePlanningConsumerError("Phase22-G Runtime Planning artifact is not production-consumable")
    return payload


def produced_but_not_consumed_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_artifacts") if isinstance(payload.get("upstream_artifacts"), dict) else {}
    return {
        "schema_version": "phase22_g_produced_not_consumed_validation.v1",
        "runtime_planning_artifact_produced": bool(payload),
        "runtime_planning_schema_valid": True,
        "portfolio_construction_shadow_read": bool((upstream.get("portfolio_construction") or {}).get("shadow_read_allowed")),
        "capital_deployment_shadow_read": bool((upstream.get("capital_deployment") or {}).get("shadow_read_allowed")),
        "position_management_shadow_read": bool((upstream.get("position_management") or {}).get("shadow_read_allowed")),
        "portfolio_policy_shadow_read": bool((upstream.get("portfolio_policy") or {}).get("shadow_read_allowed")),
        "runtime_planning_production_consumer_connected": True,
        "pending_written": True,
        "submit_generated": False,
        "runtime_switch_performed": True,
        "legacy_authority_active": False,
        "existing_morning_planning_changed": True,
        "existing_add_planning_changed": True,
        "existing_sell_planning_changed": False,
        "pending_changed": True,
        "approval_changed": False,
        "submit_changed": False,
        "execution_changed": False,
        "concrete_allocation_decided": False,
        "concrete_quantity_decided": False,
        "lot_rounding_decided": False,
    }


def runtime_planning_hash(payload: Mapping[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    return hashlib.sha256(json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_plans(
    *,
    business_date: str,
    pc_payload: dict[str, Any],
    cd_payload: dict[str, Any],
    pm_payload: dict[str, Any],
    ps_payload: dict[str, Any],
    quantity_source_mode: str,
    opportunity_payload: dict[str, Any],
    opportunity_artifact_path: Path | str | None,
    current_position_rows: tuple[Mapping[str, Any], ...],
    pending_rows: tuple[Mapping[str, Any], ...],
    source_hash_seed: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    pc_members = {str(item.get("security_code") or ""): item for item in pc_payload.get("portfolio_members") or [] if str(item.get("security_code") or "")}
    cd_members = {str(item.get("security_code") or ""): item for item in cd_payload.get("members") or [] if str(item.get("security_code") or "")}
    pm_positions = {str(item.get("security_code") or ""): item for item in pm_payload.get("positions") or [] if str(item.get("security_code") or "")}
    sizing_positions = {str(item.get("security_code") or ""): item for item in ps_payload.get("positions") or [] if str(item.get("security_code") or "")}
    opportunity_rows = _opportunity_rows_by_symbol(
        payload=opportunity_payload,
        opportunity_artifact_path=opportunity_artifact_path,
        business_date=business_date,
    )
    current_position_authorities = _current_position_membership_authorities(
        business_date=business_date,
        rows=current_position_rows,
    )
    current_codes = set(current_position_authorities)
    pending_codes = {str(row.get("security_code") or row.get("symbol") or "") for row in pending_rows}
    codes = sorted((set(pc_members) | set(pm_positions) | set(sizing_positions) | current_codes) - {""})
    upstream_blocked = (
        str(pc_payload.get("producer_result_status") or "") == "BLOCK"
        or str(ps_payload.get("producer_result_status") or "") == "BLOCK"
    )
    plans: list[dict[str, Any]] = []
    reasons: list[str] = []
    if upstream_blocked:
        reasons.append("upstream_block_propagation:position_sizing_or_portfolio_construction")
    seen_intents: dict[str, set[str]] = {}
    for code in codes:
        pc_member = pc_members.get(code, {})
        cd_member = cd_members.get(code, {})
        pm_position = pm_positions.get(code, {})
        sizing = sizing_positions.get(code, {})
        opportunity_authority = opportunity_rows.get(code)
        current_authority = current_position_authorities.get(code, {})
        liquidation_authority = _full_liquidation_authority(
            pm_position=pm_position,
            pc_member=pc_member,
            sizing=sizing,
        )
        intent, intent_reasons = _resolve_intent(
            code,
            pc_member,
            cd_member,
            pm_position,
            sizing,
            current_codes,
            current_authority,
            quantity_source_mode=quantity_source_mode,
            full_liquidation_authority_present=liquidation_authority["full_liquidation_authority_present"],
        )
        reasons.extend(intent_reasons)
        if intent == "NO_ACTION" and str(pc_member.get("membership_intent") or "") == "EXCLUDE":
            continue
        quantity_status, planned_quantity, quantity_delta, no_order_reason, quantity_reasons = _resolve_quantity_status(
            intent=intent,
            sizing=sizing,
            upstream_blocked=upstream_blocked,
        )
        plan_reasons = list(dict.fromkeys([*intent_reasons, *quantity_reasons]))
        opportunity_no_buy_reason = str((opportunity_authority or {}).get("opportunity_no_buy_reason") or "").strip()
        if intent in {"BUY_NEW", "BUY_ADD"} and opportunity_no_buy_reason_blocks_buy(opportunity_no_buy_reason):
            intent = "NO_ORDER"
            quantity_status = "NOT_REQUIRED"
            planned_quantity = 0
            quantity_delta = _int_or_none(sizing.get("quantity_delta_candidate")) if sizing else None
            no_order_reason = "opportunity_no_buy_reason_present"
            plan_reasons.append(f"opportunity_no_buy_reason_present:{opportunity_no_buy_reason}")
        canonical_zero_no_action = (
            quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN"
            and quantity_status == "RESOLVED_ZERO_DELTA"
            and intent == "NO_ACTION"
        )
        if (
            quantity_status
            in {"RESOLVED_ZERO_ALLOCATION", "RESOLVED_ZERO_DELTA", "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY", "NO_ORDER_MINIMUM_NOTIONAL_UNMET"}
            and not canonical_zero_no_action
        ):
            intent = "NO_ORDER"
        side = "BUY" if intent in {"BUY_NEW", "BUY_ADD"} else ("SELL" if intent in {"SELL_REDUCE", "SELL_EXIT"} else ("NONE" if intent in {"NO_ACTION", "NO_ORDER"} else "UNRESOLVED"))
        quantity_required = intent in {"BUY_NEW", "BUY_ADD", "SELL_REDUCE", "SELL_EXIT"}
        pending_eligibility = "CANDIDATE_ONLY" if quantity_required else ("NOT_REQUIRED" if intent in {"NO_ACTION", "NO_ORDER"} else "REVIEW_REQUIRED")
        if quantity_status.startswith("REVIEW_REQUIRED") and "quantity_not_produced_due_to_upstream_block" not in quantity_reasons:
            reasons.append(f"review_required_quantity_authority:{code}:{quantity_status}")
        if intent == "BUY_ADD" and code not in current_codes:
            plan_reasons.append("add_without_current_position")
            reasons.append(f"add_without_current_position:{code}")
            pending_eligibility = "BLOCKED"
        if intent in {"SELL_REDUCE", "SELL_EXIT"} and code not in current_codes:
            plan_reasons.append("missing_current_position_for_sell")
            reasons.append(f"missing_current_position_for_sell:{code}")
            pending_eligibility = "BLOCKED"
        if code in pending_codes and quantity_required:
            plan_reasons.append("existing_pending_conflict")
            reasons.append(f"existing_pending_conflict:{code}")
            pending_eligibility = "REVIEW_REQUIRED"
        seen_intents.setdefault(code, set()).add(intent)
        pm_fallback_used = any(str(reason).startswith("pm_") and "maps_to" in str(reason) for reason in intent_reasons)
        plan = {
            "planning_id": _planning_id(business_date, code, intent, pc_member, pm_position, source_hash_seed),
            "security_code": code,
            "planning_intent": intent,
            "order_side_intent": side,
            "position_reference": str(pm_position.get("position_id") or ""),
            "portfolio_construction_reference": str(pc_member.get("member_id") or ""),
            "capital_deployment_reference": str(cd_member.get("membership_reference") or ""),
            "position_management_reference": str(pm_position.get("position_id") or pc_member.get("position_management_reference") or ""),
            "quantity_required": quantity_required,
            "quantity_authority": (CANONICAL_QUANTITY_AUTHORITY if quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN" else QUANTITY_AUTHORITY) if quantity_required else "",
            "quantity_status": quantity_status,
            "target_quantity_candidate": _int_or_none(sizing.get("target_quantity_candidate")),
            "quantity_delta_candidate": quantity_delta,
            "planned_quantity": planned_quantity if quantity_required else 0,
            "quantity_reference": str(sizing.get("position_reference") or "") if quantity_required else "",
            "canonical_quantity_source": quantity_source_mode,
            "canonical_quantity_delta_priority": quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN",
            "source_pm_action": liquidation_authority["source_pm_action"],
            "source_pm_decision_id": liquidation_authority["source_pm_decision_id"],
            "source_pm_reason_codes": liquidation_authority["source_pm_reason_codes"],
            "full_liquidation_authority_present": liquidation_authority["full_liquidation_authority_present"],
            "full_liquidation_authority_source": liquidation_authority["full_liquidation_authority_source"],
            "pm_fallback_used": pm_fallback_used,
            "pm_fallback_scope": (
                ("LEGACY_COMPATIBILITY_ONLY" if quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN" else "LEGACY_COMPATIBILITY")
                if pm_fallback_used
                else "NOT_USED"
            ),
            "pending_eligibility": pending_eligibility,
            "no_order_reason": no_order_reason,
            "current_position_membership_authority": current_authority,
            "planning_reason": ";".join(sorted(set(plan_reasons))),
            "pending_candidate_contract": {
                "pending_candidate_generated": False,
                "pending_writer_connected": False,
                "submit_allowed": False,
                "broker_write_allowed": False,
            },
            "confidence": float(pm_position.get("confidence") or pc_member.get("confidence") or 0.0),
            "uncertainty": str(pm_position.get("uncertainty") or pc_member.get("uncertainty") or "UPSTREAM_REVIEW_REQUIRED"),
            "reason_codes": sorted(set(plan_reasons)),
            "opportunity_buy_rank": _int_or_none(
                sizing.get("opportunity_buy_rank")
                if sizing.get("opportunity_buy_rank") not in (None, "")
                else pc_member.get("opportunity_buy_rank", pc_member.get("input_opportunity_rank"))
            ),
            "portfolio_input_opportunity_rank": _int_or_none(pc_member.get("input_opportunity_rank")),
            "position_sizing_opportunity_buy_rank": _int_or_none(sizing.get("opportunity_buy_rank")),
            "rank_authority_status": str(sizing.get("rank_authority_status") or pc_member.get("rank_authority_status") or ""),
            "rank_authority": str(sizing.get("rank_authority") or pc_member.get("rank_authority") or pc_member.get("input_opportunity_rank_authority") or ""),
            "rank_authority_field": str(sizing.get("rank_authority_field") or pc_member.get("rank_authority_field") or ""),
            "rank_authority_reason": str(sizing.get("rank_authority_reason") or pc_member.get("rank_authority_reason") or ""),
            "opportunity_row_id": str(sizing.get("opportunity_row_id") or pc_member.get("opportunity_row_id") or pc_member.get("input_opportunity_row_id") or ""),
            "opportunity_row_authority_hash": str(
                sizing.get("opportunity_row_authority_hash") or pc_member.get("opportunity_row_authority_hash") or pc_member.get("input_opportunity_row_authority_hash") or ""
            ),
            "opportunity_artifact_path": str(sizing.get("opportunity_artifact_path") or pc_member.get("opportunity_artifact_path") or pc_member.get("input_opportunity_rank_source_path") or ""),
            "opportunity_artifact_hash": str(sizing.get("opportunity_artifact_hash") or pc_member.get("opportunity_artifact_hash") or pc_member.get("input_opportunity_rank_source_hash") or ""),
            "quality_decision_id": str(sizing.get("quality_decision_id") or pc_member.get("quality_decision_id") or ""),
            "quality_score": _float_or_none(sizing.get("quality_score", pc_member.get("quality_score"))),
            "quality_band": str(sizing.get("quality_band") or pc_member.get("quality_band") or ""),
            "quality_action": str(sizing.get("quality_action") or pc_member.get("quality_action") or ""),
            "quality_status": str(sizing.get("quality_status") or pc_member.get("quality_status") or ""),
            "quality_reason_codes": list(sizing.get("quality_reason_codes") or pc_member.get("quality_reason_codes") or []),
            "component_scores": dict(sizing.get("component_scores") or pc_member.get("component_scores") or {}),
            "component_statuses": dict(sizing.get("component_statuses") or pc_member.get("component_statuses") or {}),
            "quality_policy_version": str(sizing.get("quality_policy_version") or pc_member.get("quality_policy_version") or ""),
            "quality_allocation_adjustment": _float_or_none(sizing.get("quality_allocation_adjustment", pc_member.get("quality_allocation_adjustment"))),
            "pre_quality_base_weight": _float_or_none(sizing.get("pre_quality_base_weight", pc_member.get("target_weight"))),
            "post_quality_target_weight": _float_or_none(sizing.get("post_quality_target_weight", sizing.get("target_weight"))),
            "buy_quality_authority": dict(sizing.get("buy_quality_authority") or pc_member.get("buy_quality_authority") or {}),
            "buy_quality_artifact_path": str(sizing.get("buy_quality_artifact_path") or pc_member.get("buy_quality_artifact_path") or ""),
            "buy_quality_artifact_hash": str(sizing.get("buy_quality_artifact_hash") or pc_member.get("buy_quality_artifact_hash") or ""),
        }
        if quantity_required:
            plan.update(_price_authority_fields(sizing))
        if opportunity_authority:
            plan["opportunity_authority"] = opportunity_authority
        plans.append(plan)
    for code, intents in seen_intents.items():
        if {"BUY_NEW", "BUY_ADD"} <= intents:
            reasons.append(f"planning_conflict_block:buy_new_buy_add:{code}")
        if intents & {"BUY_NEW", "BUY_ADD"} and intents & {"SELL_REDUCE", "SELL_EXIT"}:
            reasons.append(f"planning_conflict_block:buy_sell:{code}")
        if {"SELL_REDUCE", "SELL_EXIT"} <= intents:
            reasons.append(f"planning_conflict_block:reduce_exit:{code}")
    return plans, sorted(set(reasons))


def _price_authority_fields(sizing: Mapping[str, Any]) -> dict[str, Any]:
    authority = (
        dict(sizing.get("reference_price_authority") or {})
        if isinstance(sizing.get("reference_price_authority"), Mapping)
        else {}
    )
    symbol = str(sizing.get("security_code") or sizing.get("symbol") or "").strip()
    if symbol and not str(authority.get("symbol") or authority.get("security_code") or "").strip():
        authority["symbol"] = symbol
    fields: dict[str, Any] = {
        "reference_price": _float_or_none(sizing.get("reference_price")),
        "reference_price_authority": authority,
        "reference_price_resolution": dict(sizing.get("reference_price_resolution") or {}) if isinstance(sizing.get("reference_price_resolution"), Mapping) else {},
        "reference_price_type": str(sizing.get("reference_price_type") or ""),
        "reference_price_date": str(sizing.get("reference_price_date") or ""),
    }
    return fields


def _full_liquidation_authority(
    *,
    pm_position: Mapping[str, Any],
    pc_member: Mapping[str, Any],
    sizing: Mapping[str, Any],
) -> dict[str, Any]:
    source_pm_action = _source_pm_action(pm_position=pm_position, pc_member=pc_member, sizing=sizing)
    source_pm_decision_id = str(
        pm_position.get("source_pm_decision_ref")
        or pm_position.get("pm_decision_id")
        or pm_position.get("decision_id")
        or pc_member.get("source_pm_decision_ref")
        or pc_member.get("source_pm_decision_id")
        or sizing.get("source_pm_decision_ref")
        or sizing.get("source_pm_decision_id")
        or ""
    )
    reason_codes = _source_pm_reason_codes(pm_position=pm_position, pc_member=pc_member, sizing=sizing)
    present = source_pm_action == "EXIT"
    return {
        "source_pm_action": source_pm_action,
        "source_pm_decision_id": source_pm_decision_id,
        "source_pm_reason_codes": reason_codes,
        "full_liquidation_authority_present": present,
        "full_liquidation_authority_source": "PM_EXIT" if present else "NONE",
    }


def _source_pm_action(
    *,
    pm_position: Mapping[str, Any],
    pc_member: Mapping[str, Any],
    sizing: Mapping[str, Any],
) -> str:
    for value in (
        pm_position.get("action"),
        pc_member.get("pm_action"),
        sizing.get("source_pm_intent"),
        sizing.get("pm_action"),
    ):
        text = str(value or "").strip().upper()
        if text:
            return text
    return "UNRESOLVED"


def _source_pm_reason_codes(
    *,
    pm_position: Mapping[str, Any],
    pc_member: Mapping[str, Any],
    sizing: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for source in (pm_position, pc_member, sizing):
        values = source.get("reason_codes")
        if isinstance(values, list):
            reasons.extend(str(value) for value in values if str(value))
        reason = source.get("decision_reason") or source.get("reason")
        if reason:
            reasons.extend(part for part in str(reason).replace(";", "|").split("|") if part)
    return sorted(set(reasons))


def _current_position_membership_authorities(
    *,
    business_date: str,
    rows: tuple[Mapping[str, Any], ...],
) -> dict[str, dict[str, Any]]:
    authorities: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            continue
        symbol = str(row.get("security_code") or row.get("symbol") or row.get("code") or row.get("issue_code") or "").strip()
        if not symbol:
            continue
        authorities[symbol] = _resolve_current_position_membership_authority(
            business_date=business_date,
            symbol=symbol,
            row=row,
            row_index=index,
        )
    return authorities


def _resolve_current_position_membership_authority(
    *,
    business_date: str,
    symbol: str,
    row: Mapping[str, Any],
    row_index: int,
) -> dict[str, Any]:
    quantity = _float(row.get("quantity"))
    source = str(row.get("source") or row.get("ownership_authority") or "").strip()
    position_state_as_of = _date_text(
        row.get("position_state_as_of")
        or row.get("as_of")
        or row.get("state_as_of")
        or row.get("opened_business_date")
        or row.get("business_date")
    )
    acquisition_date = _date_text(row.get("acquired_at") or row.get("acquisition_date") or row.get("opened_business_date"))
    fill_date = _date_text(row.get("fill_date") or row.get("filled_at") or row.get("source_execution_business_date") or row.get("last_execution_date"))
    valuation_as_of = _date_text(row.get("valuation_as_of") or row.get("valuation_date") or row.get("source_market_date") or position_state_as_of)
    source_market_date = _date_text(row.get("source_market_date") or valuation_as_of or position_state_as_of)
    previous_trading_date = _date_text(row.get("previous_trading_date") or row.get("previous_business_date"))
    fill_quantity = _int_or_none(row.get("fill_quantity") if row.get("fill_quantity") not in (None, "") else row.get("filled_quantity"))
    quantity_as_int = _int_or_none(quantity)
    identity_symbols = {
        value
        for value in (
            str(row.get("security_code") or "").strip(),
            str(row.get("symbol") or "").strip(),
            str(row.get("code") or "").strip(),
            str(row.get("issue_code") or "").strip(),
        )
        if value
    }
    reasons: list[str] = []
    status = "PASS"
    membership = "CURRENT_PORTFOLIO_MEMBER"
    ownership = "RUNTIME_OWNED" if _is_runtime_owned_position_source(source) else "EXTERNAL_OR_UNKNOWN"
    if quantity <= 0:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_quantity_missing_or_non_positive")
    if identity_symbols and any(value != symbol for value in identity_symbols):
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_symbol_mismatch")
    if not source:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_ownership_authority_missing")
    elif not _is_runtime_owned_position_source(source):
        status = "REVIEW_REQUIRED"
        membership = "NON_RUNTIME_OWNED_EXTERNAL_POSITION"
        reasons.append("current_position_not_runtime_owned")
    if not position_state_as_of:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_state_as_of_missing")
    elif position_state_as_of > business_date:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_state_future_date")
    if acquisition_date and acquisition_date > business_date:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_acquisition_future_date")
    if fill_date and fill_date > business_date:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_fill_future_date")
    if valuation_as_of and valuation_as_of > business_date:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_valuation_future_date")
    if source_market_date and source_market_date > business_date:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_source_market_future_date")
    if previous_trading_date and previous_trading_date > business_date:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_previous_trading_future_date")
    if fill_quantity is not None and quantity_as_int is not None and fill_quantity != quantity_as_int:
        status = "REVIEW_REQUIRED"
        reasons.append("current_position_fill_quantity_mismatch")
    if source == "runtime_v2_runtime_owned_fill_projection" and (
        position_state_as_of == business_date or fill_date == business_date
    ):
        membership = "NEWLY_FILLED_PORTFOLIO_MEMBER"
    authority_hash = hashlib.sha256(
        json.dumps(
            {
                "business_date": business_date,
                "symbol": symbol,
                "quantity": quantity,
                "source": source,
                "position_state_as_of": position_state_as_of,
                "acquisition_date": acquisition_date,
                "fill_date": fill_date,
                "valuation_as_of": valuation_as_of,
                "source_market_date": source_market_date,
                "previous_trading_date": previous_trading_date,
                "status": status,
                "membership": membership,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "phase23_bq_current_position_membership_authority.v1",
        "authority": "runtime_owned_current_position_membership",
        "status": status,
        "membership": membership,
        "ownership": ownership,
        "symbol": symbol,
        "business_date": business_date,
        "as_of": position_state_as_of,
        "position_state_as_of": position_state_as_of,
        "acquisition_date": acquisition_date,
        "fill_date": fill_date,
        "valuation_as_of": valuation_as_of,
        "source_market_date": source_market_date,
        "previous_trading_date": previous_trading_date,
        "quantity": quantity,
        "source": source,
        "row_index": row_index,
        "position_reference": str(row.get("position_id") or row.get("current_position_reference") or f"runtime-current-{symbol}"),
        "position_lifecycle_id": str(row.get("position_lifecycle_id") or row.get("position_campaign_id") or row.get("source_execution_id") or ""),
        "reason_codes": reasons,
        "temporal_contract": {
            "business_date": business_date,
            "position_state_as_of": position_state_as_of,
            "acquisition_date": acquisition_date,
            "fill_date": fill_date,
            "valuation_as_of": valuation_as_of,
            "previous_trading_date": previous_trading_date,
            "source_market_date": source_market_date,
            "position_state_not_after_business_date": bool(position_state_as_of and position_state_as_of <= business_date),
            "valuation_not_after_business_date": bool(not valuation_as_of or valuation_as_of <= business_date),
            "market_pit_not_after_business_date": bool(not source_market_date or source_market_date <= business_date),
        },
        "authority_hash": authority_hash,
    }


def _is_runtime_owned_position_source(source: str) -> bool:
    return source in {
        "runtime_v2_runtime_owned_fill_projection",
        "runtime_owned_execution_ledger",
        "runtime_current_position_adapter_input",
    } or source.startswith("runtime_owned_") or source.startswith("runtime_v2_runtime_owned_")


def _resolve_quantity_status(
    *,
    intent: str,
    sizing: Mapping[str, Any],
    upstream_blocked: bool = False,
) -> tuple[str, int, int | None, str, list[str]]:
    if intent not in {"BUY_NEW", "BUY_ADD", "SELL_REDUCE", "SELL_EXIT"}:
        return "NOT_REQUIRED", 0, _int_or_none(sizing.get("quantity_delta_candidate")) if sizing else None, "no_action_strategy_intent", []
    if not sizing:
        if upstream_blocked:
            return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, None, "", ["quantity_not_produced_due_to_upstream_block"]
        return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, None, "", ["position_sizing_authority_missing"]
    quantity_status = str(sizing.get("quantity_status") or "")
    target_quantity = _int_or_none(sizing.get("target_quantity_candidate"))
    quantity_delta = _int_or_none(sizing.get("quantity_delta_candidate"))
    if str(sizing.get("schema_version") or "") == "position_sizing_plan.v1":
        sizing_status = str(sizing.get("sizing_status") or "")
        if sizing_status in {"ADD_NOT_SIZED", "HOLD_NOT_SIZED", "REDUCE_NOT_SIZED", "EXIT_NOT_SIZED", "UNRESOLVED_NOT_SIZED"}:
            return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, quantity_delta, "", [f"canonical_position_sizing_plan_not_sized:{sizing_status}"]
        if quantity_delta is not None and target_quantity is not None:
            if quantity_delta == 0:
                return "RESOLVED_ZERO_DELTA", 0, quantity_delta, "zero_quantity_delta", ["canonical_quantity_delta_resolved_zero"]
            return "RESOLVED_EXECUTABLE", abs(quantity_delta), quantity_delta, "", ["canonical_position_sizing_plan_quantity_delta_resolved"]
        return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, quantity_delta, "", ["canonical_position_sizing_plan_quantity_delta_missing"]
    if quantity_status in {"RESOLVED_CANDIDATE", "RESOLVED_ZERO_DELTA"} and quantity_delta is not None and target_quantity is not None:
        if quantity_delta == 0:
            return "RESOLVED_ZERO_DELTA", 0, quantity_delta, "zero_quantity_delta", ["no_order_zero_quantity_delta"]
        return "RESOLVED_EXECUTABLE", abs(quantity_delta), quantity_delta, "", ["position_sizing_quantity_candidate_resolved"]
    if quantity_status == "NO_ORDER_MINIMUM_NOTIONAL_UNMET":
        return "NO_ORDER_MINIMUM_NOTIONAL_UNMET", 0, quantity_delta, "NO_ORDER_MINIMUM_NOTIONAL_UNMET", ["no_order_minimum_notional_unmet"]
    if quantity_status == "PRICE_UNAVAILABLE":
        return "REVIEW_REQUIRED_MISSING_PRICE", 0, quantity_delta, "", ["position_sizing_price_unavailable"]
    sizing_status = str(sizing.get("sizing_status") or "")
    if sizing_status == "RESOLVED_ZERO_ALLOCATION":
        return "RESOLVED_ZERO_ALLOCATION", 0, quantity_delta, "zero_target_allocation", ["no_order_zero_allocation_authorized"]
    if sizing_status in {"NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY", "MINIMUM_NOTIONAL_UNMET"}:
        return "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY", 0, quantity_delta, "NO_ORDER_MINIMUM_NOTIONAL_UNMET", ["no_order_below_minimum_tradable_quantity"]
    if sizing_status in {"SIZED", "CAPPED"}:
        return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, quantity_delta, "", ["canonical_quantity_candidate_missing"]
    if upstream_blocked and sizing_status == "UPSTREAM_REVIEW_REQUIRED":
        return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, quantity_delta, "", ["quantity_not_produced_due_to_upstream_block"]
    return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", 0, quantity_delta, "", [f"position_sizing_status_unresolved:{quantity_status or sizing_status or 'missing'}"]


def _resolve_intent(
    code: str,
    pc_member: Mapping[str, Any],
    cd_member: Mapping[str, Any],
    pm_position: Mapping[str, Any],
    sizing: Mapping[str, Any],
    current_codes: set[str],
    current_position_authority: Mapping[str, Any] | None = None,
    quantity_source_mode: str = "LEGACY_POSITION_SIZING",
    full_liquidation_authority_present: bool = False,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    pm_action = str(pm_position.get("action") or "").upper()
    membership = str(pc_member.get("membership_intent") or "").upper()
    quantity_delta = _int_or_none(sizing.get("quantity_delta_candidate"))
    target_quantity = _int_or_none(sizing.get("target_quantity_candidate"))
    canonical_source = quantity_source_mode == "CANONICAL_POSITION_SIZING_PLAN" or str(sizing.get("schema_version") or "") == "position_sizing_plan.v1"
    current_authority = current_position_authority or {}
    current_authority_status = str(current_authority.get("status") or "")
    current_membership = str(current_authority.get("membership") or "")
    if canonical_source and quantity_delta is not None:
        if quantity_delta > 0:
            return ("BUY_ADD" if code in current_codes else "BUY_NEW"), ["canonical_positive_quantity_delta_maps_to_buy_add" if code in current_codes else "canonical_positive_quantity_delta_maps_to_buy_new"]
        if quantity_delta < 0:
            if target_quantity == 0:
                if full_liquidation_authority_present:
                    return "SELL_EXIT", ["canonical_negative_quantity_delta_maps_to_sell_exit", "full_liquidation_authority:PM_EXIT"]
                return "UNRESOLVED", [f"planning_conflict_review:full_liquidation_authority_missing:{code}"]
            return "SELL_REDUCE", ["canonical_negative_quantity_delta_maps_to_sell_reduce"]
        return "NO_ACTION", ["canonical_zero_quantity_delta_maps_to_no_action"]
    if quantity_delta is not None and quantity_delta != 0:
        if quantity_delta > 0:
            return ("BUY_ADD" if code in current_codes else "BUY_NEW"), ["position_sizing_positive_quantity_delta_maps_to_buy_add" if code in current_codes else "position_sizing_positive_quantity_delta_maps_to_buy_new"]
        if target_quantity == 0:
            if full_liquidation_authority_present:
                return "SELL_EXIT", ["position_sizing_negative_quantity_delta_maps_to_sell_exit", "full_liquidation_authority:PM_EXIT"]
            return "UNRESOLVED", [f"planning_conflict_review:full_liquidation_authority_missing:{code}"]
        return "SELL_REDUCE", ["position_sizing_negative_quantity_delta_maps_to_sell_reduce"]
    if code in current_codes and quantity_delta == 0:
        if current_authority_status == "PASS" and current_membership in {"CURRENT_PORTFOLIO_MEMBER", "NEWLY_FILLED_PORTFOLIO_MEMBER", "RETAINED_PORTFOLIO_MEMBER", "EXITING_PORTFOLIO_MEMBER"}:
            return "NO_ACTION", [
                f"current_position_membership_resolved:{current_membership.lower()}",
                "current_position_zero_delta_maps_to_no_action",
            ]
        authority_reasons = [str(reason) for reason in current_authority.get("reason_codes") or [] if str(reason)]
        return "UNRESOLVED", [
            f"unresolved_mapping:{reason}" for reason in (authority_reasons or ["current_position_membership_authority_unresolved"])
        ]
    if canonical_source and pm_action in {"ADD", "REDUCE", "EXIT", "HOLD"}:
        return "UNRESOLVED", [f"planning_conflict_review:canonical_delta_missing_pm_fallback_disabled:{code}"]
    if pm_action == "ADD":
        return "BUY_ADD", ["pm_add_maps_to_buy_add"]
    if pm_action == "REDUCE":
        return "SELL_REDUCE", ["pm_reduce_maps_to_sell_reduce"]
    if pm_action == "EXIT":
        return "SELL_EXIT", ["pm_exit_maps_to_sell_exit"]
    if pm_action == "HOLD":
        if membership in {"REMOVE_CANDIDATE", "REDUCE_CANDIDATE"}:
            return "UNRESOLVED", [f"planning_conflict_review:portfolio_membership_requires_pm_sell_intent:{code}"]
        return "NO_ACTION", ["pm_hold_maps_to_no_action"]
    if membership == "ADD_CANDIDATE":
        return "BUY_NEW", ["portfolio_add_candidate_maps_to_buy_new"]
    if membership == "EXCLUDE":
        return "NO_ACTION", ["portfolio_exclude_maps_to_no_plan"]
    if membership == "UNRESOLVED":
        return "UNRESOLVED", ["unresolved_mapping:portfolio_membership_unresolved"]
    if membership in {"REMOVE_CANDIDATE", "REDUCE_CANDIDATE"}:
        return "UNRESOLVED", [f"planning_conflict_review:sell_requires_position_management_intent:{code}"]
    if membership == "RETAIN":
        return "NO_ACTION", ["portfolio_retain_without_pm_action_maps_to_no_action"]
    reasons.append("unresolved_mapping:source_intent_missing")
    return "UNRESOLVED", reasons


def _validate_plan(plan: Any, *, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return [f"plan_not_object:{index}"]
    required = {
        "planning_id",
        "security_code",
        "planning_intent",
        "order_side_intent",
        "quantity_required",
        "quantity_authority",
        "quantity_status",
        "target_quantity_candidate",
        "quantity_delta_candidate",
        "planned_quantity",
        "pending_eligibility",
        "no_order_reason",
        "planning_reason",
        "pending_candidate_contract",
        "reason_codes",
    }
    errors.extend(f"plan_required_field_missing:{index}:{field}" for field in sorted(required - set(plan)))
    if not str(plan.get("planning_id") or ""):
        errors.append(f"planning_id_missing:{index}")
    if not str(plan.get("security_code") or ""):
        errors.append(f"security_code_missing:{index}")
    if plan.get("planning_intent") not in PLANNING_INTENTS:
        errors.append(f"invalid_planning_intent:{index}")
    if plan.get("order_side_intent") not in ORDER_SIDE_INTENTS:
        errors.append(f"invalid_order_side_intent:{index}")
    if plan.get("pending_eligibility") not in PENDING_ELIGIBILITIES:
        errors.append(f"invalid_pending_eligibility:{index}")
    if plan.get("quantity_status") not in QUANTITY_STATUSES:
        errors.append(f"invalid_quantity_status:{index}")
    if plan.get("quantity_required") is True:
        if plan.get("quantity_authority") not in {QUANTITY_AUTHORITY, CANONICAL_QUANTITY_AUTHORITY}:
            errors.append(f"invalid_quantity_authority:{index}")
        if plan.get("quantity_status") not in {"RESOLVED_EXECUTABLE", "REVIEW_REQUIRED_MISSING_PRICE", "REVIEW_REQUIRED_MISSING_TRADABLE_UNIT", "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED", "UNRESOLVED"}:
            errors.append(f"invalid_required_quantity_status:{index}")
        planned = plan.get("planned_quantity")
        if plan.get("quantity_status") == "RESOLVED_EXECUTABLE" and (isinstance(planned, bool) or not isinstance(planned, int) or planned <= 0):
            errors.append(f"invalid_planned_quantity:{index}")
        if plan.get("quantity_status") != "RESOLVED_EXECUTABLE" and planned not in {0, None}:
            errors.append(f"planned_quantity_must_be_zero_when_unresolved:{index}")
        if plan.get("quantity_status") == "RESOLVED_EXECUTABLE":
            errors.extend(_validate_executable_price_authority(plan, index=index))
    elif plan.get("quantity_required") is False:
        if plan.get("quantity_authority") not in {"", None}:
            errors.append(f"quantity_authority_forbidden_when_not_required:{index}")
        planned = plan.get("planned_quantity")
        if planned not in {0, None}:
            errors.append(f"planned_quantity_forbidden_when_not_required:{index}")
    else:
        errors.append(f"quantity_required_not_boolean:{index}")
    pending_contract = plan.get("pending_candidate_contract")
    if not isinstance(pending_contract, dict):
        errors.append(f"pending_candidate_contract_not_object:{index}")
    else:
        for field in ("pending_candidate_generated", "pending_writer_connected", "submit_allowed", "broker_write_allowed"):
            if pending_contract.get(field) is not False:
                errors.append(f"pending_contract_field_must_be_false:{index}:{field}")
    for field in sorted(FORBIDDEN_CONCRETE_FIELDS & set(plan)):
        errors.append(f"plan_concrete_field_forbidden:{index}:{field}")
    return errors


def _validate_executable_price_authority(plan: Mapping[str, Any], *, index: int) -> list[str]:
    errors: list[str] = []
    price = _float_or_none(plan.get("reference_price"))
    if price is None or price <= 0:
        errors.append(f"reference_price_missing_for_executable_plan:{index}")
    authority = plan.get("reference_price_authority")
    if not isinstance(authority, Mapping) or not authority:
        errors.append(f"reference_price_authority_missing_for_executable_plan:{index}")
    else:
        symbol = str(plan.get("security_code") or "")
        authority_symbol = str(authority.get("symbol") or authority.get("security_code") or "")
        if authority_symbol and authority_symbol != symbol:
            errors.append(f"reference_price_symbol_mismatch:{index}")
        business_date = str(plan.get("business_date") or "")
        authority_business_date = str(authority.get("business_date") or "")
        if business_date and authority_business_date and authority_business_date != business_date:
            errors.append(f"reference_price_business_date_mismatch:{index}")
        if str(authority.get("PIT_status") or "") != "PASS":
            errors.append(f"reference_price_pit_status_not_pass:{index}")
    resolution = plan.get("reference_price_resolution")
    if not isinstance(resolution, Mapping) or str(resolution.get("status") or "") != "PASS":
        errors.append(f"reference_price_resolution_not_pass:{index}")
    if not str(plan.get("reference_price_type") or ""):
        errors.append(f"reference_price_type_missing_for_executable_plan:{index}")
    if not str(plan.get("reference_price_date") or ""):
        errors.append(f"reference_price_date_missing_for_executable_plan:{index}")
    return errors


def _planning_id(
    business_date: str,
    code: str,
    intent: str,
    pc_member: Mapping[str, Any],
    pm_position: Mapping[str, Any],
    source_hash_seed: str,
) -> str:
    identity = {
        "business_date": business_date,
        "security_code": code,
        "planning_intent": intent,
        "position_id": str(pm_position.get("position_id") or ""),
        "membership_reference": str(pc_member.get("member_id") or ""),
        "source_hash_seed": source_hash_seed,
    }
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"rp-{business_date}-{code}-{intent.lower()}-{digest}"


def _load_json_if_valid(path: Path | str | None) -> dict[str, Any]:
    if path is None or not Path(path).is_file():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _opportunity_rows_by_symbol(
    *,
    payload: Mapping[str, Any],
    opportunity_artifact_path: Path | str | None,
    business_date: str,
) -> dict[str, dict[str, Any]]:
    if not payload or not opportunity_artifact_path:
        return {}
    artifact_path = str(opportunity_artifact_path)
    artifact_hash = sha256_file(opportunity_artifact_path) if Path(opportunity_artifact_path).is_file() else ""
    artifact_business_date = str(payload.get("business_date") or "")
    artifact_feature_date = str(payload.get("feature_date") or payload.get("target_date") or "")
    if artifact_business_date and artifact_business_date != business_date:
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(payload.get("rankings") or [], start=1):
        if not isinstance(row, Mapping):
            continue
        symbol = str(row.get("symbol") or row.get("code") or row.get("security_code") or "").strip()
        if not symbol:
            continue
        row_business_date = str(row.get("business_date") or artifact_business_date or business_date)
        row_feature_date = str(row.get("feature_date") or row.get("target_date") or artifact_feature_date or business_date)
        if row_business_date != business_date or row_feature_date > business_date:
            continue
        buy_rank = _int_or_none(row.get("opportunity_buy_rank") if row.get("opportunity_buy_rank") not in (None, "") else row.get("buy_rank"))
        row_identity = _opportunity_row_id(row=row, business_date=business_date, symbol=symbol, index=index)
        rows[symbol] = {
            "schema_version": "phase23_bd_opportunity_item_authority.v1",
            "opportunity_authority": "runtime_v2_opportunity_ranking_row",
            "opportunity_source": artifact_path,
            "opportunity_artifact_path": artifact_path,
            "opportunity_artifact_hash": artifact_hash,
            "opportunity_business_date": row_business_date,
            "opportunity_feature_date": row_feature_date,
            "opportunity_symbol": symbol,
            "opportunity_row_id": row_identity,
            "opportunity_rank": buy_rank,
            "opportunity_buy_rank": buy_rank,
            "opportunity_status": str(payload.get("status") or "PASS"),
            "opportunity_eligibility": "BUY_ELIGIBLE",
            "opportunity_expected_edge_score": row.get("expected_edge_score"),
            "opportunity_expected_return": row.get("expected_return", row.get("expected_edge_score")),
            "opportunity_no_buy_reason": str(row.get("no_buy_reason") or ""),
            "opportunity_model_version": str(row.get("model_version") or ""),
            "ranking_schema_version": str(payload.get("schema_version") or ""),
            "ranking_schema_name": str(row.get("schema_name") or ""),
            "ranking_artifact_role": str(row.get("artifact_role") or ""),
            "row_index": index,
            "row_authority_hash": hashlib.sha256(
                json.dumps(
                    {
                        "business_date": row_business_date,
                        "feature_date": row_feature_date,
                        "symbol": symbol,
                        "row_id": row_identity,
                        "buy_rank": buy_rank,
                        "expected_edge_score": row.get("expected_edge_score"),
                        "artifact_hash": artifact_hash,
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
    return rows


def _opportunity_row_id(*, row: Mapping[str, Any], business_date: str, symbol: str, index: int) -> str:
    explicit = str(row.get("opportunity_id") or row.get("row_id") or "")
    if explicit:
        return explicit
    rank = str(row.get("buy_rank") or row.get("rank") or index)
    digest = hashlib.sha256(
        json.dumps(
            {
                "business_date": str(row.get("business_date") or business_date),
                "feature_date": str(row.get("feature_date") or row.get("target_date") or business_date),
                "symbol": symbol,
                "rank": rank,
                "expected_edge_score": row.get("expected_edge_score"),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"opportunity-{business_date}-{symbol}-{rank}-{digest}"


def _source_hashes(
    portfolio_construction_artifact_path: Path | str | None,
    capital_deployment_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    position_sizing_artifact_path: Path | str | None,
    position_sizing_plan_artifact_path: Path | str | None,
    opportunity_artifact_path: Path | str | None,
    current_portfolio_summary: RuntimePlanningSourceSummary,
    current_cash_summary: RuntimePlanningSourceSummary,
    current_position_summary: RuntimePlanningSourceSummary,
    pending_summary: RuntimePlanningSourceSummary,
    planning_config_summary: RuntimePlanningSourceSummary,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for role, path in (
        ("portfolio_construction", portfolio_construction_artifact_path),
        ("portfolio_policy", portfolio_policy_artifact_path),
        ("position_management", position_management_artifact_path),
    ):
        items.append({"role": role, "path": str(path or ""), "sha256": sha256_file(path) if path and Path(path).is_file() else ""})
    if capital_deployment_artifact_path and Path(capital_deployment_artifact_path).is_file():
        items.append({"role": "capital_deployment_noncanonical_observability", "path": str(capital_deployment_artifact_path), "sha256": sha256_file(capital_deployment_artifact_path)})
    if position_sizing_artifact_path and Path(position_sizing_artifact_path).is_file():
        items.append({"role": "position_sizing", "path": str(position_sizing_artifact_path), "sha256": sha256_file(position_sizing_artifact_path)})
    if position_sizing_plan_artifact_path and Path(position_sizing_plan_artifact_path).is_file():
        items.append({"role": "position_sizing_plan", "path": str(position_sizing_plan_artifact_path), "sha256": sha256_file(position_sizing_plan_artifact_path)})
    if opportunity_artifact_path and Path(opportunity_artifact_path).is_file():
        items.append({"role": "opportunity_ranking", "path": str(opportunity_artifact_path), "sha256": sha256_file(opportunity_artifact_path)})
    for role, summary in (
        ("current_portfolio", current_portfolio_summary),
        ("current_cash", current_cash_summary),
        ("current_position", current_position_summary),
        ("pending", pending_summary),
    ):
        items.append({"role": role, "path": summary.source_ref, "sha256": _strip_sha256(summary.source_hash)})
    if planning_config_summary.source_hash:
        items.append({"role": "planning_config_noncanonical_observability", "path": planning_config_summary.source_ref, "sha256": _strip_sha256(planning_config_summary.source_hash)})
    return items


def _position_sizing_source_status(payload: Mapping[str, Any], path: Path | str | None) -> str:
    if path is None or not Path(path).is_file():
        return "MISSING_OPTIONAL"
    status = str(payload.get("producer_result_status") or "")
    if status == "PASS":
        return "PASS"
    if status == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    if status == "BLOCK":
        return "BLOCK"
    return "UNRESOLVED"


def _position_sizing_plan_source_status(payload: Mapping[str, Any], path: Path | str | None, *, business_date: str) -> str:
    if path is None or not Path(path).is_file():
        return "MISSING_OPTIONAL"
    if not payload:
        return "UNRESOLVED"
    if str(payload.get("schema_version") or "") != "position_sizing_plan.v1":
        return "BLOCK"
    if str(payload.get("business_date") or "") != business_date:
        return "BLOCK"
    if str(payload.get("authority_mode") or "") != "SHADOW" or str(payload.get("decision_effect") or "") != "NONE":
        return "BLOCK"
    status = str(payload.get("artifact_status") or payload.get("producer_result_status") or "")
    if status == "PASS":
        return "PASS"
    if status == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    if status == "BLOCK":
        return "BLOCK"
    return "UNRESOLVED"


def _select_runtime_quantity_source(
    *,
    legacy_ps_payload: dict[str, Any],
    canonical_ps_payload: dict[str, Any],
    canonical_path: Path | str | None,
) -> tuple[dict[str, Any], str]:
    if canonical_path is not None and canonical_ps_payload:
        return _runtime_position_sizing_payload_from_plan(canonical_ps_payload), "CANONICAL_POSITION_SIZING_PLAN"
    return legacy_ps_payload, "LEGACY_POSITION_SIZING"


def _runtime_position_sizing_payload_from_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    positions = []
    for row in payload.get("positions") or []:
        if not isinstance(row, Mapping):
            continue
        positions.append(
            {
                **dict(row),
                "schema_version": "position_sizing_plan.v1",
                "security_code": str(row.get("symbol") or row.get("security_code") or ""),
                "position_reference": str(row.get("source_target_portfolio_decision_id") or row.get("position_campaign_id") or ""),
                "quantity_status": _quantity_status_from_position_sizing_plan_row(row),
                "runtime_quantity_source": "position_sizing_plan.v1",
            }
        )
    return {
        "schema_version": "position_sizing_plan.v1",
        "producer_result_status": str(payload.get("artifact_status") or payload.get("producer_result_status") or ""),
        "business_date": str(payload.get("business_date") or ""),
        "feature_date": str(payload.get("business_date") or ""),
        "positions": positions,
    }


def _quantity_status_from_position_sizing_plan_row(row: Mapping[str, Any]) -> str:
    sizing_status = str(row.get("sizing_status") or "")
    delta = _int_or_none(row.get("quantity_delta_candidate"))
    if sizing_status in {"ADD_NOT_SIZED", "HOLD_NOT_SIZED", "REDUCE_NOT_SIZED", "EXIT_NOT_SIZED", "UNRESOLVED_NOT_SIZED"}:
        return "REVIEW_REQUIRED_AUTHORITY_UNRESOLVED"
    if delta == 0:
        return "RESOLVED_ZERO_DELTA"
    if delta is not None:
        return "RESOLVED_CANDIDATE"
    return "UNRESOLVED"


def _opportunity_source_status(payload: Mapping[str, Any], path: Path | str | None, *, business_date: str) -> str:
    if path is None or not Path(path).is_file():
        return "MISSING_OPTIONAL"
    if not payload:
        return "UNRESOLVED"
    if str(payload.get("business_date") or "") not in {"", business_date}:
        return "BLOCK"
    status = str(payload.get("status") or payload.get("producer_result_status") or "")
    if status == "PASS":
        return "PASS"
    if status == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    if status == "BLOCK":
        return "BLOCK"
    return "UNRESOLVED"


def _float(value: Any) -> float:
    if isinstance(value, bool) or value in {None, ""}:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    return text[:10] if text else ""


def _float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None
    try:
        return float(value)
    except Exception:
        return 0.0


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value in {None, ""}:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if not number.is_integer():
        return None
    return int(number)


def _source_hash_seed(*items: Any) -> str:
    payload = []
    for item in items:
        if isinstance(item, RuntimePlanningSourceSummary):
            payload.append({"path": item.source_ref, "sha256": _strip_sha256(item.source_hash)})
        elif item and Path(item).is_file():
            payload.append({"path": str(item), "sha256": sha256_file(item)})
        else:
            payload.append({"path": str(item or ""), "sha256": ""})
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()


def _missing_upstream(kind: str, requested_business_date: str, path: str) -> dict[str, Any]:
    return {
        "artifact_kind": kind,
        "artifact_path": path,
        "schema_version": "",
        "status": SOURCE_MISSING,
        "schema_compatible": False,
        "shadow_read_allowed": False,
        "production_decision_allowed": False,
        "business_date": "",
        "feature_date": "",
        "business_date_aligned": False,
        "feature_date_point_in_time": False,
        "artifact_hash_valid": False,
        "lifecycle_status": "",
        "producer_result_status": "",
        "runtime_consumer_eligibility": "",
        "reason_codes": [f"{kind}_missing_for_business_date:{requested_business_date}"],
    }


def _summary_aligned(summary: RuntimePlanningSourceSummary, *, business_date: str) -> bool:
    return summary.business_date == business_date and bool(summary.feature_date) and summary.feature_date <= business_date


def _enum_check(errors: list[str], payload: Mapping[str, Any], field: str, allowed: set[str]) -> None:
    if payload.get(field) not in allowed:
        errors.append(f"invalid_enum:{field}")


def _validate_iso_date(value: str, *, field: str) -> None:
    try:
        date.fromisoformat(value)
    except Exception as exc:
        raise RuntimePlanningSchemaError(f"{field} must be ISO date") from exc


def _validate_rfc3339_timestamp(value: str, *, field: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise RuntimePlanningSchemaError(f"{field} must be RFC3339 timestamp") from exc


def _strip_sha256(value: str) -> str:
    return value.replace("sha256:", "", 1)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
