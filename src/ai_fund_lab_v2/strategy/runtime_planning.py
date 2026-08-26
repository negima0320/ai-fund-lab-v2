from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

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
REFINED_CAPITAL_LINEAGE_SCHEMA_VERSION = "refined_capital_decision_lineage.v1"
G63_RUNTIME_BINDING_SCHEMA_VERSION = "runtime_planning.g63_pc_ps_executable_binding.v1"
ARTIFACT_LIFECYCLE_STATUS = "DRAFT"
RUNTIME_CONSUMER_ELIGIBILITY = "ELIGIBLE"
QUANTITY_AUTHORITY = "PHASE22_J_POSITION_SIZING"
CANONICAL_QUANTITY_AUTHORITY = "PHASE27_D2D_POSITION_SIZING_PLAN"
REDUCE_INTENTIONAL_NO_ORDER_SEMANTICS = {
    "REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT",
    "REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL",
}

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
    policy_payload = _load_json_if_valid(portfolio_policy_artifact_path)
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
    g63_binding_precheck = _g63_runtime_binding_precheck(selected_ps_payload, business_date=business_date)
    if g63_binding_precheck["status"] == "BLOCK":
        producer_status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
        reason_codes.extend(g63_binding_precheck["reason_codes"])
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
    strategy_authority_lineage = _strategy_authority_lineage_envelope(
        business_date=business_date,
        as_of=as_of,
        pc_payload=pc_payload,
        policy_payload=policy_payload,
        pm_payload=pm_payload,
        ps_payload=selected_ps_payload,
        source_artifacts=source_artifacts,
        source_hashes=source_hashes,
        plans=plans,
    )
    plans = _attach_strategy_authority_lineage(plans, strategy_authority_lineage)
    g63_runtime_binding = _g63_runtime_executable_binding_summary(
        business_date=business_date,
        ps_payload=selected_ps_payload,
        plans=plans,
        precheck=g63_binding_precheck,
    )
    if g63_runtime_binding["status"] == "BLOCK":
        producer_status = "BLOCK"
        source_status = "AUTHORITY_CONFLICT"
        reason_codes.extend(g63_runtime_binding["reason_codes"])

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
        "strategy_authority_lineage": strategy_authority_lineage,
        "g63_pc_ps_runtime_executable_binding": g63_runtime_binding,
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
        economic_units_available = _optional_bool((opportunity_authority or {}).get("opportunity_economic_units_available"))
        if economic_units_available is None:
            economic_units_available = True
        if intent in {"BUY_NEW", "BUY_ADD"} and opportunity_no_buy_reason_blocks_buy(
            opportunity_no_buy_reason,
            economic_units_available=economic_units_available,
        ):
            intent = "NO_ORDER"
            quantity_status = "NOT_REQUIRED"
            planned_quantity = 0
            quantity_delta = _int_or_none(sizing.get("quantity_delta_candidate")) if sizing else None
            no_order_reason = "opportunity_no_buy_reason_present"
            plan_reasons.append(f"opportunity_no_buy_reason_present:{opportunity_no_buy_reason}")
        g63_binding = _g63_plan_binding_guard(
            code=code,
            intent=intent,
            sizing=sizing,
            planned_quantity=planned_quantity,
            quantity_delta=quantity_delta,
        )
        if g63_binding["runtime_blocked_implicit_promotion"]:
            intent = "NO_ORDER"
            quantity_status = "RESOLVED_ZERO_DELTA"
            planned_quantity = 0
            quantity_delta = 0
            no_order_reason = "G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED"
            plan_reasons.extend(g63_binding["reason_codes"])
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
            "canonical_marginal_capital_priority_index": _int_or_none(pc_member.get("canonical_marginal_capital_priority_index")),
            "marginal_capital_value_class": str(pc_member.get("marginal_capital_value_class") or ""),
            "marginal_capital_value_authority": dict(pc_member.get("marginal_capital_value_authority") or {}),
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
            "g63_runtime_binding": g63_binding,
            "g61_lot_aware_compatibility_consumed_by_runtime": g63_binding["g61_compatibility_consumed_by_runtime"],
            "runtime_capital_priority_redecision": False,
            "lower_priority_implicit_promotion_runtime": g63_binding["lower_priority_implicit_promotion_runtime"],
            "cash_winner_redecision_runtime": False,
            "ps_authorized_quantity_reoptimized_by_runtime": False,
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
            "reduce_execution_semantic": str(sizing.get("reduce_execution_semantic") or ""),
            "reduce_executability_status": str(sizing.get("reduce_executability_status") or ""),
            "reduce_intentional_no_order": bool(sizing.get("reduce_intentional_no_order")),
            "reduce_intentional_no_order_reason": str(sizing.get("reduce_intentional_no_order_reason") or ""),
            "reduce_executability_evidence": dict(sizing.get("reduce_executability_evidence") or {}),
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
    return _sort_plans_by_canonical_marginal_priority(plans), sorted(set(reasons))


def _strategy_authority_lineage_envelope(
    *,
    business_date: str,
    as_of: str,
    pc_payload: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    pm_payload: Mapping[str, Any],
    ps_payload: Mapping[str, Any],
    source_artifacts: Sequence[Mapping[str, Any]],
    source_hashes: Sequence[Mapping[str, Any]],
    plans: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pc_members = {str(item.get("security_code") or ""): item for item in pc_payload.get("portfolio_members") or [] if isinstance(item, Mapping)}
    ps_members = {str(item.get("security_code") or item.get("symbol") or ""): item for item in ps_payload.get("positions") or [] if isinstance(item, Mapping)}
    pm_members = {str(item.get("security_code") or item.get("symbol") or ""): item for item in pm_payload.get("positions") or [] if isinstance(item, Mapping)}
    refined_capital_lineage = _refined_capital_decision_lineage(
        business_date=business_date,
        pc_payload=pc_payload,
        policy_payload=policy_payload,
        ps_payload=ps_payload,
        plans=plans,
    )
    refined_by_symbol = {
        str(item.get("symbol") or ""): item
        for item in refined_capital_lineage.get("items") or []
        if isinstance(item, Mapping) and str(item.get("symbol") or "")
    }
    compact_items = []
    for plan in plans:
        symbol = str(plan.get("security_code") or "")
        if not symbol:
            continue
        pc_member = pc_members.get(symbol, {})
        ps_member = ps_members.get(symbol, {})
        pm_member = pm_members.get(symbol, {})
        compact_items.append(
            {
                "symbol": symbol,
                "runtime_planning_id": str(plan.get("planning_id") or ""),
                "planning_intent": str(plan.get("planning_intent") or ""),
                "order_side_intent": str(plan.get("order_side_intent") or ""),
                "pc_member_id": str(pc_member.get("member_id") or plan.get("portfolio_construction_reference") or ""),
                "pc_membership_intent": str(pc_member.get("membership_intent") or ""),
                "pc_weight_intent": str(pc_member.get("weight_intent") or ""),
                "target_weight": _float_or_none(pc_member.get("target_weight")),
                "canonical_marginal_capital_priority_index": _int_or_none(plan.get("canonical_marginal_capital_priority_index")),
                "marginal_capital_value_class": str(plan.get("marginal_capital_value_class") or ""),
                "pm_action": str(pm_member.get("action") or plan.get("source_pm_action") or ""),
                "pm_decision_id": str(pm_member.get("position_id") or plan.get("source_pm_decision_id") or ""),
                "reentry_semantic_eligibility": _compact_reentry_summary(pc_member),
                "canonical_add_competitor": _compact_add_competitor_summary(pc_payload, symbol=symbol),
                "position_sizing_decision": _compact_sizing_summary(ps_member, plan),
                "refined_capital_decision_lineage": dict(refined_by_symbol.get(symbol) or {}),
            }
        )
    envelope = {
        "schema_version": "runtime_authority_lineage.v1",
        "authority_type": "STRATEGY_AUTHORITY_LINEAGE",
        "business_date": business_date,
        "as_of": as_of,
        "field_classification": {
            "market_quality_state": "BUSINESS_DECISION_INPUT",
            "market_quality_reason_codes": "BUSINESS_DECISION_INPUT",
            "market_quality_as_of": "BUSINESS_DECISION_INPUT",
            "risk_pacing_intent": "AUTHORITATIVE_DECISION_RESULT",
            "risk_pacing_reason_codes": "AUTHORITATIVE_DECISION_RESULT",
            "risk_pacing_as_of": "AUTHORITATIVE_DECISION_RESULT",
            "capital_competition": "AUTHORITATIVE_DECISION_RESULT",
            "canonical_add_competitor": "AUTHORITATIVE_DECISION_RESULT",
            "reentry_semantic_eligibility": "AUTHORITATIVE_DECISION_RESULT",
            "final_no_deployable_opportunity": "AUTHORITATIVE_DECISION_RESULT",
            "canonical_sizing_evidence": "AUTHORITATIVE_DECISION_RESULT",
            "refined_capital_decision_lineage": "AUTHORITATIVE_DECISION_RESULT",
        },
        "source_artifacts": _compact_source_artifacts(source_artifacts),
        "source_hashes": _compact_source_hashes(source_hashes),
        "market_quality": _compact_market_quality_summary(policy_payload),
        "risk_pacing": _compact_risk_pacing_summary(policy_payload),
        "portfolio_construction": _compact_pc_summary(pc_payload),
        "position_sizing": _compact_position_sizing_payload_summary(ps_payload),
        "refined_capital_decision_lineage": refined_capital_lineage,
        "items": compact_items,
        "downstream_strategy_redecision_allowed": False,
        "full_upstream_artifact_duplicated": False,
        "same_business_decision_owner_count": 1,
        "downstream_risk_pacing_recomputation_count": 0,
        "downstream_opportunity_quality_recomputation_count": 0,
        "downstream_cash_competition_recomputation_count": 0,
        "downstream_capital_winner_recomputation_count": 0,
        "downstream_capital_reclassification_count": 0,
        "cash_winner_downstream_security_substitution_count": 0,
        "historical_outcome_lineage_input_count": 0,
        "paper_ledger_decision_input_count": 0,
        "audit_result_decision_input_count": 0,
    }
    envelope["lineage_hash"] = _lineage_hash(envelope)
    return envelope


def _attach_strategy_authority_lineage(plans: Sequence[Mapping[str, Any]], envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = {
        str(item.get("symbol") or ""): item
        for item in envelope.get("items") or []
        if isinstance(item, Mapping) and str(item.get("symbol") or "")
    }
    lineage_hash = str(envelope.get("lineage_hash") or "")
    attached = []
    for plan in plans:
        symbol = str(plan.get("security_code") or "")
        item_summary = dict(items.get(symbol) or {})
        refined_item = dict(item_summary.get("refined_capital_decision_lineage") or {})
        item_lineage = {
            "schema_version": "runtime_authority_lineage.item.v1",
            "lineage_hash": lineage_hash,
            "lineage_ref": "runtime_planning.strategy_authority_lineage",
            "business_date": str(envelope.get("business_date") or ""),
            "as_of": str(envelope.get("as_of") or ""),
            "symbol": symbol,
            "field_classification": dict(envelope.get("field_classification") or {}),
            "market_quality": dict(envelope.get("market_quality") or {}),
            "risk_pacing": dict(envelope.get("risk_pacing") or {}),
            "portfolio_construction": dict(envelope.get("portfolio_construction") or {}),
            "position_sizing": dict(envelope.get("position_sizing") or {}),
            "refined_capital_decision_lineage": refined_item,
            "item": item_summary,
            "source_hashes": list(envelope.get("source_hashes") or []),
            "downstream_strategy_redecision_allowed": False,
            "downstream_capital_reclassification_count": 0,
        }
        attached.append({**dict(plan), "strategy_authority_lineage": item_lineage})
    return attached


def _refined_capital_decision_lineage(
    *,
    business_date: str,
    pc_payload: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    ps_payload: Mapping[str, Any],
    plans: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    competition = pc_payload.get("capital_competition") if isinstance(pc_payload.get("capital_competition"), Mapping) else {}
    interaction = (
        competition.get("market_candidate_cash_interaction")
        if isinstance(competition.get("market_candidate_cash_interaction"), Mapping)
        else {}
    )
    cash_evidence = (
        competition.get("canonical_cash_competitor_evidence")
        if isinstance(competition.get("canonical_cash_competitor_evidence"), Mapping)
        else {}
    )
    refined_available = bool(interaction) or bool(cash_evidence)
    items = [
        _refined_capital_item_lineage(
            plan=plan,
            pc_payload=pc_payload,
            ps_payload=ps_payload,
            interaction=interaction,
            refined_available=refined_available,
            business_date=business_date,
        )
        for plan in plans
        if isinstance(plan, Mapping) and str(plan.get("security_code") or "")
    ]
    payload = {
        "schema_version": REFINED_CAPITAL_LINEAGE_SCHEMA_VERSION,
        "authority_type": "REFINED_CAPITAL_DECISION_LINEAGE",
        "producer": "strategy.runtime_planning._strategy_authority_lineage_envelope",
        "business_date": business_date,
        "market_quality_state": str(cash_evidence.get("market_quality_state") or policy_payload.get("market_quality_state") or ""),
        "market_quality_as_of": str(
            cash_evidence.get("market_quality_as_of")
            or policy_payload.get("market_quality_as_of")
            or policy_payload.get("as_of")
            or ""
        ),
        "market_quality_authority_hash": str(cash_evidence.get("market_quality_authority_hash") or ""),
        "risk_pacing_intent": str(cash_evidence.get("risk_pacing_intent") or policy_payload.get("risk_pacing_intent") or ""),
        "risk_pacing_as_of": str(
            cash_evidence.get("risk_pacing_as_of")
            or policy_payload.get("risk_pacing_as_of")
            or policy_payload.get("as_of")
            or ""
        ),
        "risk_pacing_authority_hash": str(
            cash_evidence.get("risk_pacing_authority_hash")
            or interaction.get("risk_pacing_authority_hash")
            or ""
        ),
        "cash_preference_semantic": str(cash_evidence.get("cash_preference_semantic") or ""),
        "cash_competitor_reason_codes": list(
            cash_evidence.get("reason_codes")
            or competition.get("cash_reason_codes")
            or []
        ),
        "cash_competitor_evidence_hash": str(
            cash_evidence.get("cash_competitor_evidence_hash")
            or interaction.get("cash_competitor_evidence_hash")
            or ""
        ),
        "market_candidate_cash_interaction_schema": str(interaction.get("schema_version") or ""),
        "capital_competition_winner_type": str(
            competition.get("capital_competition_winner_type")
            or interaction.get("capital_competition_winner_type")
            or ""
        ),
        "capital_competition_winner_symbol": str(
            competition.get("capital_competition_winner_symbol")
            or interaction.get("capital_competition_winner_symbol")
            or ""
        ),
        "capital_competition_winner_reason_codes": list(
            competition.get("capital_competition_winner_reason_codes")
            or interaction.get("winner_reason_codes")
            or []
        ),
        "canonical_deployment_set": _compact_canonical_deployment_set(competition),
        "position_sizing_consumed_canonical_deployment_set": _compact_deployment_set_consumption(ps_payload),
        "defeated_competitor_summary": _compact_defeated_competitors(
            competition.get("defeated_competitor_summary")
            or interaction.get("defeated_competitor_summary")
            or []
        ),
        "final_no_deployable_identity": dict(competition.get("final_no_deployable_opportunity_authority") or {}),
        "lineage_status": "AVAILABLE" if refined_available else "UNAVAILABLE_LEGACY_RECORD",
        "missing_refined_lineage_not_reconstructed_from_later_state": not refined_available,
        "same_business_decision_owner_count": 1,
        "strategy_business_decision_owner": "PORTFOLIO_CONSTRUCTION",
        "runtime_decision_owner_count": 0,
        "downstream_redecision_allowed": False,
        "downstream_risk_pacing_recomputation_count": 0,
        "downstream_opportunity_quality_recomputation_count": 0,
        "downstream_cash_competition_recomputation_count": 0,
        "downstream_capital_winner_recomputation_count": 0,
        "downstream_capital_reclassification_count": 0,
        "cash_winner_downstream_security_substitution_count": 0,
        "security_winner_quantity_source": "POSITION_SIZING",
        "lineage_persistence_is_decision_binding": False,
        "final_capital_winner_binds_before_discrete_sizing": bool(
            (_compact_canonical_deployment_set(competition)).get("final_capital_winner_binds_before_discrete_sizing")
        ),
        "future_input_count": 0,
        "historical_outcome_lineage_input_count": 0,
        "paper_ledger_decision_input_count": 0,
        "audit_result_decision_input_count": 0,
        "items": items,
    }
    payload["lineage_hash"] = _lineage_hash(payload)
    return payload


def _refined_capital_item_lineage(
    *,
    plan: Mapping[str, Any],
    pc_payload: Mapping[str, Any],
    ps_payload: Mapping[str, Any],
    interaction: Mapping[str, Any],
    refined_available: bool,
    business_date: str,
) -> dict[str, Any]:
    symbol = str(plan.get("security_code") or "")
    pc_member = _pc_member(pc_payload, symbol=symbol)
    ps_member = _ps_member(ps_payload, symbol=symbol)
    result = _interaction_result(interaction, symbol=symbol)
    competitor = _capital_competitor(pc_payload, symbol=symbol)
    opportunity_evidence = (
        competitor.get("opportunity_quality_evidence")
        if isinstance(competitor.get("opportunity_quality_evidence"), Mapping)
        else {}
    )
    sizing = _compact_sizing_summary(ps_member, plan)
    add = competitor.get("canonical_add_competitor") if isinstance(competitor.get("canonical_add_competitor"), Mapping) else {}
    payload = {
        "schema_version": REFINED_CAPITAL_LINEAGE_SCHEMA_VERSION,
        "lineage_scope": "ITEM",
        "business_date": business_date,
        "symbol": symbol,
        "planning_intent": str(plan.get("planning_intent") or ""),
        "order_side_intent": str(plan.get("order_side_intent") or ""),
        "lineage_status": "AVAILABLE" if refined_available else "UNAVAILABLE_LEGACY_RECORD",
        "missing_refined_lineage_not_reconstructed_from_later_state": not refined_available,
        "canonical_opportunity_quality_class": str(
            result.get("canonical_opportunity_quality_class")
            or competitor.get("canonical_opportunity_quality_class")
            or opportunity_evidence.get("canonical_opportunity_quality_class")
            or ""
        ),
        "opportunity_quality_reason_codes": list(
            result.get("reason_codes")
            or opportunity_evidence.get("opportunity_quality_reason_codes")
            or opportunity_evidence.get("reason_codes")
            or []
        ),
        "opportunity_quality_authority": str(opportunity_evidence.get("authority_type") or "OPPORTUNITY_QUALITY"),
        "opportunity_quality_evidence_hash": str(
            result.get("opportunity_quality_evidence_hash")
            or opportunity_evidence.get("opportunity_quality_hash")
            or ""
        ),
        "interaction_result": str(result.get("interaction_result") or ""),
        "binding_reason_codes": list(result.get("binding_reason_codes") or result.get("reason_codes") or []),
        "capital_competition_winner_type": str(interaction.get("capital_competition_winner_type") or ""),
        "capital_competition_winner_symbol": str(interaction.get("capital_competition_winner_symbol") or ""),
        "winner_loser": str(result.get("winner_loser") or ""),
        "defeated_competitor_summary": _compact_defeated_competitors(interaction.get("defeated_competitor_summary") or []),
        "add_binding": dict(add) if add else {"status": "NOT_APPLICABLE"},
        "reentry_binding": _compact_reentry_summary(pc_member),
        "lot_reconsideration_binding": _compact_lot_reconsideration(pc_payload, symbol=symbol),
        "sizing_evidence_identity": sizing,
        "canonical_deployment_set_sizing_eligibility": str(ps_member.get("canonical_deployment_set_sizing_eligibility") or ""),
        "final_capital_winner_binds_before_discrete_sizing": bool(ps_member.get("final_capital_winner_binds_before_discrete_sizing")),
        "security_winner_quantity_source": "POSITION_SIZING",
        "runtime_recomputed_capital_decision": False,
        "downstream_capital_reclassification_count": 0,
        "future_input_count": 0,
        "historical_outcome_lineage_input_count": 0,
        "paper_ledger_decision_input_count": 0,
        "audit_result_decision_input_count": 0,
    }
    payload["lineage_hash"] = _lineage_hash(payload)
    return payload


def _pc_member(pc_payload: Mapping[str, Any], *, symbol: str) -> Mapping[str, Any]:
    for item in pc_payload.get("portfolio_members") or []:
        if isinstance(item, Mapping) and str(item.get("security_code") or item.get("symbol") or "") == symbol:
            return item
    return {}


def _ps_member(ps_payload: Mapping[str, Any], *, symbol: str) -> Mapping[str, Any]:
    for item in ps_payload.get("positions") or []:
        if isinstance(item, Mapping) and str(item.get("security_code") or item.get("symbol") or "") == symbol:
            return item
    return {}


def _capital_competitor(pc_payload: Mapping[str, Any], *, symbol: str) -> Mapping[str, Any]:
    competition = pc_payload.get("capital_competition") if isinstance(pc_payload.get("capital_competition"), Mapping) else {}
    for item in competition.get("competitors") or []:
        if isinstance(item, Mapping) and str(item.get("symbol") or "") == symbol:
            return item
    return {}


def _interaction_result(interaction: Mapping[str, Any], *, symbol: str) -> Mapping[str, Any]:
    for item in interaction.get("interaction_results") or []:
        if isinstance(item, Mapping) and str(item.get("symbol") or "") == symbol:
            return item
    return {}


def _compact_defeated_competitors(items: Sequence[Any]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        compact.append(
            {
                "competitor_type": str(item.get("competitor_type") or ""),
                "symbol": str(item.get("symbol") or ""),
                "interaction_result": str(item.get("interaction_result") or ""),
                "reason_codes": list(item.get("reason_codes") or []),
            }
        )
    return compact


def _compact_lot_reconsideration(pc_payload: Mapping[str, Any], *, symbol: str) -> dict[str, Any]:
    evidence = pc_payload.get("lot_aware_reallocation_evidence") if isinstance(pc_payload.get("lot_aware_reallocation_evidence"), Mapping) else {}
    if not evidence:
        evidence = pc_payload.get("evidence") if isinstance(pc_payload.get("evidence"), Mapping) else {}
    binding = (
        evidence.get("lot_reconsideration_binding_integration")
        if isinstance(evidence.get("lot_reconsideration_binding_integration"), Mapping)
        else {}
    )
    skipped = next(
        (
            item
            for item in evidence.get("skipped") or []
            if isinstance(item, Mapping) and str(item.get("symbol") or "") == symbol
        ),
        {},
    )
    if not binding and not skipped:
        return {"status": "NOT_APPLICABLE"}
    competition = pc_payload.get("capital_competition") if isinstance(pc_payload.get("capital_competition"), Mapping) else {}
    return {
        "schema_version": str(binding.get("schema_version") or "portfolio_construction.lot_reconsideration_binding.v1"),
        "status": "AVAILABLE",
        "original_winner_symbol": symbol if skipped else "",
        "sizing_infeasibility_reason": str(skipped.get("reason") or skipped.get("blocked_reason") or ""),
        "final_winner_symbol": str(competition.get("capital_competition_winner_symbol") or ""),
        "final_winner_type": str(competition.get("capital_competition_winner_type") or ""),
        "position_sizing_quantity_owner": "POSITION_SIZING",
        "second_reconsideration_authority_count": int(binding.get("second_reconsideration_authority_count") or 0),
    }


def _compact_canonical_deployment_set(competition: Mapping[str, Any]) -> dict[str, Any]:
    deployment_set = competition.get("canonical_deployment_set") if isinstance(competition.get("canonical_deployment_set"), Mapping) else {}
    if not deployment_set:
        return {"status": "NOT_AVAILABLE"}
    return {
        "schema_version": str(deployment_set.get("schema_version") or ""),
        "owner": str(deployment_set.get("owner") or ""),
        "cardinality_contract": str(deployment_set.get("cardinality_contract") or ""),
        "final_winner_type": str(deployment_set.get("final_winner_type") or ""),
        "final_winner_symbol": str(deployment_set.get("final_winner_symbol") or ""),
        "selected_symbol_set": list(deployment_set.get("selected_symbol_set") or []),
        "deployment_security_count": int(deployment_set.get("deployment_security_count") or 0),
        "defeated_security_count": int(deployment_set.get("defeated_security_count") or 0),
        "deployment_set_hash": str(deployment_set.get("deployment_set_hash") or ""),
        "final_capital_winner_binds_before_discrete_sizing": bool(
            deployment_set.get("final_capital_winner_binds_before_discrete_sizing")
        ),
        "position_sizing_capital_winner_authority": bool(deployment_set.get("position_sizing_capital_winner_authority")),
        "runtime_planning_redecision_allowed": bool(deployment_set.get("runtime_planning_redecision_allowed")),
    }


def _compact_deployment_set_consumption(ps_payload: Mapping[str, Any]) -> dict[str, Any]:
    consumption = ps_payload.get("canonical_deployment_set_consumption")
    if not isinstance(consumption, Mapping):
        return {"status": "NOT_AVAILABLE"}
    return {
        "schema_version": str(consumption.get("schema_version") or ""),
        "status": str(consumption.get("status") or ""),
        "canonical_deployment_set_hash": str(consumption.get("canonical_deployment_set_hash") or ""),
        "selected_symbol_set": list(consumption.get("selected_symbol_set") or []),
        "defeated_security_evidence_row_count": int(consumption.get("defeated_security_evidence_row_count") or 0),
        "defeated_security_sizing_input_count": int(consumption.get("defeated_security_sizing_input_count") or 0),
        "defeated_security_positive_increment_count": int(consumption.get("defeated_security_positive_increment_count") or 0),
        "position_sizing_capital_winner_authority": bool(consumption.get("position_sizing_capital_winner_authority")),
        "downstream_cash_redecision_count": int(consumption.get("downstream_cash_redecision_count") or 0),
    }


def _compact_source_artifacts(source_artifacts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for item in source_artifacts:
        compact.append(
            {
                "role": str(item.get("role") or ""),
                "path": str(item.get("path") or ""),
                "status": str(item.get("status") or ""),
                "required": bool(item.get("required")),
            }
        )
    return compact


def _compact_source_hashes(source_hashes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": str(item.get("role") or ""),
            "path": str(item.get("path") or ""),
            "sha256": str(item.get("sha256") or ""),
        }
        for item in source_hashes
    ]


def _compact_market_quality_summary(policy_payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": "MARKET_CONTEXT",
        "state": str(policy_payload.get("market_quality_state") or ""),
        "reason_codes": list(policy_payload.get("market_quality_reason_codes") or []),
        "as_of": str(policy_payload.get("market_quality_as_of") or policy_payload.get("as_of") or ""),
        "business_date": str(policy_payload.get("business_date") or ""),
    }


def _compact_risk_pacing_summary(policy_payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": "PORTFOLIO_POLICY",
        "intent": str(policy_payload.get("risk_pacing_intent") or ""),
        "reason_codes": list(policy_payload.get("risk_pacing_reason_codes") or []),
        "as_of": str(policy_payload.get("risk_pacing_as_of") or policy_payload.get("as_of") or ""),
        "mode": str(policy_payload.get("risk_pacing_mode") or ""),
        "evidence_completeness": str(policy_payload.get("risk_pacing_evidence_completeness") or ""),
    }


def _compact_pc_summary(pc_payload: Mapping[str, Any]) -> dict[str, Any]:
    competition = pc_payload.get("capital_competition") if isinstance(pc_payload.get("capital_competition"), Mapping) else {}
    no_deployable = pc_payload.get("final_no_deployable_opportunity_authority")
    if not isinstance(no_deployable, Mapping):
        no_deployable = competition.get("final_no_deployable_opportunity_authority") if isinstance(competition.get("final_no_deployable_opportunity_authority"), Mapping) else {}
    return {
        "authority": "PORTFOLIO_CONSTRUCTION",
        "business_date": str(pc_payload.get("business_date") or ""),
        "as_of": str(pc_payload.get("as_of") or ""),
        "artifact_hash": str(pc_payload.get("artifact_hash") or ""),
        "capital_competition": {
            "authority": dict(competition.get("authority") or {}),
            "competitor_types": list(competition.get("competitor_types") or []),
            "final_no_deployable_opportunity": bool(competition.get("final_no_deployable_opportunity")),
            "final_no_deployable_opportunity_authority": dict(no_deployable),
        },
    }


def _compact_position_sizing_payload_summary(ps_payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": "POSITION_SIZING",
        "schema_version": str(ps_payload.get("schema_version") or ""),
        "business_date": str(ps_payload.get("business_date") or ""),
        "artifact_hash": str(ps_payload.get("artifact_hash") or ""),
    }


def _compact_reentry_summary(pc_member: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "reentry_semantic_eligibility",
        "reentry_semantic_state",
        "reentry_reason_codes",
        "entry_admission",
        "entry_admission_action",
    )
    summary = {key: pc_member.get(key) for key in keys if key in pc_member}
    return summary if summary else {"status": "NOT_APPLICABLE"}


def _compact_add_competitor_summary(pc_payload: Mapping[str, Any], *, symbol: str) -> dict[str, Any]:
    competition = pc_payload.get("capital_competition") if isinstance(pc_payload.get("capital_competition"), Mapping) else {}
    for competitor in competition.get("competitors") or []:
        if not isinstance(competitor, Mapping):
            continue
        if str(competitor.get("symbol") or "") != symbol:
            continue
        add = competitor.get("canonical_add_competitor")
        if isinstance(add, Mapping):
            return {
                "status": str(add.get("eligibility_state") or add.get("status") or ""),
                "reason_codes": list(add.get("reason_codes") or []),
                "competitor_type": str(competitor.get("competitor_type") or ""),
                "selected": bool(competitor.get("selected")),
            }
    return {"status": "NOT_APPLICABLE"}


def _compact_sizing_summary(ps_member: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    canonical = ps_member.get("canonical_sizing_evidence")
    if not isinstance(canonical, Mapping):
        canonical = ps_member.get("phase29_l19_lot_resolution") if isinstance(ps_member.get("phase29_l19_lot_resolution"), Mapping) else {}
    return {
        "authority": str(plan.get("quantity_authority") or "POSITION_SIZING"),
        "position_reference": str(ps_member.get("position_reference") or plan.get("quantity_reference") or ""),
        "target_quantity_candidate": _int_or_none(plan.get("target_quantity_candidate")),
        "quantity_delta_candidate": _int_or_none(plan.get("quantity_delta_candidate")),
        "planned_quantity": _int_or_none(plan.get("planned_quantity")),
        "quantity_status": str(plan.get("quantity_status") or ""),
        "canonical_sizing_evidence": {
            "evidence_class": str(canonical.get("evidence_class") or canonical.get("boundary_classification") or ""),
            "reason": str(canonical.get("reason") or canonical.get("blocked_reason") or canonical.get("lot_overshoot_reason") or ""),
            "lot_feasibility_status": str(canonical.get("lot_feasibility_status") or canonical.get("one_lot_feasibility_status") or ""),
            "final_allocated_quantity": canonical.get("final_allocated_quantity"),
            "executable_quantity_delta": canonical.get("executable_quantity_delta"),
        },
    }


def _lineage_hash(payload: Mapping[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "lineage_hash"}
    return "sha256:" + hashlib.sha256(json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sort_plans_by_canonical_marginal_priority(plans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(index, dict(plan)) for index, plan in enumerate(plans)]

    def key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
        index, plan = item
        side = str(plan.get("order_side_intent") or "").upper()
        intent = str(plan.get("planning_intent") or "").upper()
        priority = _int_or_none(plan.get("canonical_marginal_capital_priority_index"))
        if side == "BUY" and intent in {"BUY_NEW", "BUY_ADD"}:
            return (0, priority if priority is not None else 999999, index)
        return (1, index)

    sorted_items = sorted(indexed, key=key)
    ordered: list[dict[str, Any]] = []
    for order_index, (_, plan) in enumerate(sorted_items, start=1):
        plan["canonical_strategy_order_index"] = order_index
        plan["canonical_strategy_order_source"] = (
            "MARGINAL_CAPITAL_VALUE_AUTHORITY"
            if str(plan.get("order_side_intent") or "").upper() == "BUY" and plan.get("canonical_marginal_capital_priority_index") is not None
            else "STABLE_NON_BUY_OR_NO_PRIORITY_ORDER"
        )
        ordered.append(plan)
    return ordered


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
            reduce_semantic = str(sizing.get("reduce_execution_semantic") or "")
            if intent == "SELL_REDUCE" and reduce_semantic in REDUCE_INTENTIONAL_NO_ORDER_SEMANTICS:
                return (
                    "RESOLVED_ZERO_DELTA",
                    0,
                    quantity_delta,
                    reduce_semantic,
                    ["no_order_reduce_intentional_no_order", f"reduce_execution_semantic:{reduce_semantic}"],
                )
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


def _g63_runtime_binding_precheck(ps_payload: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    consumption = (
        ps_payload.get("g61_lot_aware_compatibility_consumption")
        if isinstance(ps_payload.get("g61_lot_aware_compatibility_consumption"), Mapping)
        else {}
    )
    base = {
        "schema_version": G63_RUNTIME_BINDING_SCHEMA_VERSION,
        "business_date": business_date,
        "owner": "RUNTIME_PLANNING",
        "position_sizing_quantity_owner": "POSITION_SIZING",
        "runtime_capital_priority_redecision": False,
        "cash_winner_redecision_runtime": False,
        "ps_authorized_quantity_reoptimized_by_runtime": False,
    }
    if not consumption:
        return {
            **base,
            "status": "NOT_AVAILABLE_LEGACY_COMPATIBILITY",
            "g61_compatibility_consumed_by_runtime": False,
            "reason_codes": ["G61_COMPATIBILITY_NOT_AVAILABLE_LEGACY_COMPATIBILITY"],
        }
    errors: list[str] = []
    if str(consumption.get("schema_version") or "") != "position_sizing.g61_lot_aware_compatibility_consumption.v1":
        errors.append("G61_PS_CONSUMPTION_SCHEMA_INVALID")
    status = str(consumption.get("status") or "")
    if status == "BLOCK":
        errors.append("G61_PS_CONSUMPTION_BLOCK")
    elif status not in {"PASS", "NOT_AVAILABLE_LEGACY_COMPATIBILITY"}:
        errors.append("G61_PS_CONSUMPTION_STATUS_INVALID")
    if str(consumption.get("business_date") or "") not in {"", business_date}:
        errors.append("G61_PS_CONSUMPTION_DATE_MISMATCH")
    if status == "PASS":
        if consumption.get("g61_compatibility_consumed_by_ps") is not True:
            errors.append("G61_COMPATIBILITY_NOT_CONSUMED_BY_PS")
        if consumption.get("lower_priority_implicit_promotion") is not False:
            errors.append("G61_LOWER_PRIORITY_IMPLICIT_PROMOTION_NOT_PROHIBITED")
        if consumption.get("pc_discrete_quantity_authority") is not False:
            errors.append("G61_PC_DISCRETE_QUANTITY_AUTHORITY_FORBIDDEN")
        if consumption.get("position_sizing_quantity_owner") != "POSITION_SIZING":
            errors.append("G61_POSITION_SIZING_QUANTITY_OWNER_INVALID")
        if consumption.get("position_sizing_recomputes_capital_priority") is not False:
            errors.append("G61_PS_CAPITAL_PRIORITY_REDECISION_FORBIDDEN")
    return {
        **base,
        "status": "BLOCK" if errors else ("PASS" if status == "PASS" else "NOT_AVAILABLE_LEGACY_COMPATIBILITY"),
        "g61_compatibility_consumed_by_runtime": not errors and status == "PASS",
        "g61_compatibility_consumption_status": status,
        "compatibility_hash": str(consumption.get("compatibility_hash") or ""),
        "allocation_count": int(consumption.get("allocation_count") or 0),
        "residual_capital_weight": _float_or_none(consumption.get("residual_capital_weight")) or 0.0,
        "lower_priority_rows_requiring_explicit_residual_resolution": int(
            consumption.get("lower_priority_rows_requiring_explicit_residual_resolution") or 0
        ),
        "reason_codes": sorted(set(errors or ["G61_PS_CONSUMPTION_ACCEPTED_BY_RUNTIME"])),
    }


def _g63_plan_binding_guard(
    *,
    code: str,
    intent: str,
    sizing: Mapping[str, Any],
    planned_quantity: int,
    quantity_delta: int | None,
) -> dict[str, Any]:
    compatibility = (
        sizing.get("g61_lot_aware_compatibility")
        if isinstance(sizing.get("g61_lot_aware_compatibility"), Mapping)
        else {}
    )
    consumed = bool(sizing.get("g61_lot_aware_compatibility_consumed_by_ps")) and bool(compatibility)
    lower_requires_resolution = bool(compatibility.get("lower_priority_execution_requires_explicit_residual_resolution"))
    buy_side = intent in {"BUY_NEW", "BUY_ADD"}
    positive_runtime_quantity = planned_quantity > 0 or (quantity_delta is not None and quantity_delta > 0)
    block = consumed and buy_side and positive_runtime_quantity and lower_requires_resolution
    return {
        "schema_version": G63_RUNTIME_BINDING_SCHEMA_VERSION,
        "symbol": code,
        "g61_compatibility_consumed_by_runtime": consumed,
        "g61_compatibility_state": str(compatibility.get("compatibility_state") or ""),
        "lower_priority_execution_requires_explicit_residual_resolution": lower_requires_resolution,
        "runtime_blocked_implicit_promotion": block,
        "lower_priority_implicit_promotion_runtime": False,
        "runtime_capital_priority_redecision": False,
        "cash_winner_redecision_runtime": False,
        "ps_authorized_quantity_reoptimized_by_runtime": False,
        "reason_codes": ["G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED"]
        if block
        else (["G61_COMPATIBILITY_BINDING_ACCEPTED_BY_RUNTIME"] if consumed else []),
    }


def _g63_runtime_executable_binding_summary(
    *,
    business_date: str,
    ps_payload: Mapping[str, Any],
    plans: Sequence[Mapping[str, Any]],
    precheck: Mapping[str, Any],
) -> dict[str, Any]:
    buy_plans = [
        plan
        for plan in plans
        if str(plan.get("planning_intent") or "") in {"BUY_NEW", "BUY_ADD"}
        and int(plan.get("planned_quantity") or 0) > 0
    ]
    add_plans = [plan for plan in buy_plans if str(plan.get("planning_intent") or "") == "BUY_ADD"]
    g61_plans = [plan for plan in plans if bool(plan.get("g61_lot_aware_compatibility_consumed_by_runtime"))]
    blocked_promotions = [
        plan
        for plan in plans
        if isinstance(plan.get("g63_runtime_binding"), Mapping)
        and (plan.get("g63_runtime_binding") or {}).get("runtime_blocked_implicit_promotion") is True
    ]
    errors: list[str] = []
    if precheck.get("status") == "BLOCK":
        errors.extend(str(item) for item in precheck.get("reason_codes") or [])
    if any(plan.get("runtime_capital_priority_redecision") is not False for plan in plans):
        errors.append("RUNTIME_CAPITAL_PRIORITY_REDECISION_DETECTED")
    if any(plan.get("lower_priority_implicit_promotion_runtime") is not False for plan in plans):
        errors.append("LOWER_PRIORITY_IMPLICIT_PROMOTION_RUNTIME_DETECTED")
    if any(plan.get("cash_winner_redecision_runtime") is not False for plan in plans):
        errors.append("CASH_WINNER_REDECISION_RUNTIME_DETECTED")
    if any(plan.get("ps_authorized_quantity_reoptimized_by_runtime") is not False for plan in plans):
        errors.append("PS_AUTHORIZED_QUANTITY_REOPTIMIZED_BY_RUNTIME")
    consumption = (
        ps_payload.get("g61_lot_aware_compatibility_consumption")
        if isinstance(ps_payload.get("g61_lot_aware_compatibility_consumption"), Mapping)
        else {}
    )
    return {
        "schema_version": G63_RUNTIME_BINDING_SCHEMA_VERSION,
        "business_date": business_date,
        "owner": "RUNTIME_PLANNING",
        "status": "BLOCK" if errors else "PASS",
        "pc_ps_runtime_executable_binding": "PASS" if not errors else "BLOCK",
        "ps_quantity_binds_runtime": True,
        "runtime_capital_priority_redecision": False,
        "lower_priority_implicit_promotion_runtime": False,
        "cash_winner_redecision_runtime": False,
        "ps_authorized_quantity_reoptimized_by_runtime": False,
        "g61_compatibility_consumed_by_runtime": precheck.get("g61_compatibility_consumed_by_runtime") is True,
        "runtime_buy_plan_count": len(buy_plans),
        "runtime_add_plan_count": len(add_plans),
        "multi_security_runtime_planning": len({str(plan.get("security_code") or "") for plan in buy_plans}) > 1,
        "add_runtime_binding": "PASS" if all(str(plan.get("planning_intent") or "") == "BUY_ADD" for plan in add_plans) else "FAIL",
        "implicit_promotion_blocked_plan_count": len(blocked_promotions),
        "residual_capital_explicit_through_runtime": bool(consumption.get("residual_capital_explicit_through_ps"))
        if consumption
        else False,
        "capital_conservation": dict(consumption.get("capital_conservation") or {}) if consumption else {},
        "future_input_count": 0,
        "historical_outcome_strategy_input_count": 0,
        "reason_codes": sorted(set(errors or ["PC_PS_RUNTIME_EXECUTABLE_BINDING_ACCEPTED"])),
    }


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
    reduce_semantic = str(sizing.get("reduce_execution_semantic") or "")
    if pm_action == "REDUCE" and quantity_delta == 0 and reduce_semantic in REDUCE_INTENTIONAL_NO_ORDER_SEMANTICS:
        return "SELL_REDUCE", ["pm_reduce_zero_delta_maps_to_intentional_no_order"]
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
            "opportunity_canonical_score_field": str(row.get("canonical_score_field") or payload.get("canonical_score_field") or ""),
            "opportunity_score_semantic_role": str(
                row.get("score_semantic_role")
                or row.get("semantic_role")
                or payload.get("score_semantic_role")
                or payload.get("semantic_role")
                or ""
            ),
            "opportunity_calibration_applied": row.get("calibration_applied")
            if isinstance(row.get("calibration_applied"), bool)
            else payload.get("calibration_applied"),
            "opportunity_economic_units_available": row.get("economic_units_available")
            if isinstance(row.get("economic_units_available"), bool)
            else payload.get("economic_units_available"),
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
                        "canonical_score_field": row.get("canonical_score_field") or payload.get("canonical_score_field"),
                        "score_semantic_role": row.get("score_semantic_role") or payload.get("score_semantic_role"),
                        "calibration_applied": row.get("calibration_applied")
                        if isinstance(row.get("calibration_applied"), bool)
                        else payload.get("calibration_applied"),
                        "economic_units_available": row.get("economic_units_available")
                        if isinstance(row.get("economic_units_available"), bool)
                        else payload.get("economic_units_available"),
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


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


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
