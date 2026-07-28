from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

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
RUNTIME_CONSUMER_ELIGIBILITY = "NOT_ELIGIBLE"
QUANTITY_AUTHORITY = "PHASE22_J_OR_DOWNSTREAM"

PLANNING_INTENTS = {"BUY_NEW", "BUY_ADD", "SELL_REDUCE", "SELL_EXIT", "NO_ACTION", "UNRESOLVED"}
ORDER_SIDE_INTENTS = {"BUY", "SELL", "NONE", "UNRESOLVED"}
PENDING_ELIGIBILITIES = {"CANDIDATE_ONLY", "NOT_REQUIRED", "REVIEW_REQUIRED", "BLOCKED"}
QUANTITY_STATUSES = {"UNRESOLVED", "NOT_REQUIRED"}
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
    as_of: str | None = None,
) -> RuntimePlanningProducerResult:
    payload, evidence = build_runtime_planning_payload(
        business_date=business_date,
        portfolio_construction_artifact_path=portfolio_construction_artifact_path,
        capital_deployment_artifact_path=capital_deployment_artifact_path,
        portfolio_policy_artifact_path=portfolio_policy_artifact_path,
        position_management_artifact_path=position_management_artifact_path,
        current_portfolio_summary=current_portfolio_summary,
        current_cash_summary=current_cash_summary,
        current_position_summary=current_position_summary,
        pending_summary=pending_summary,
        planning_config_summary=planning_config_summary,
        as_of=as_of,
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
    as_of: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_iso_date(business_date, field="business_date")
    as_of = as_of or f"{business_date}T00:00:00+00:00"
    _validate_rfc3339_timestamp(as_of, field="as_of")

    construction_result = capital_deployment.validate_portfolio_construction_compatibility(
        portfolio_construction_artifact_path,
        requested_business_date=business_date,
        production_use_requested=True,
    )
    deployment_result = validate_capital_deployment_compatibility(
        capital_deployment_artifact_path,
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

    producer_status = "PASS"
    source_status = "VALID"
    reason_codes: list[str] = []
    upstream_statuses = [
        construction_result["status"],
        deployment_result["status"],
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
        "planning_config": planning_config_summary.to_dict(requested_business_date=business_date),
    }
    for name, summary in (
        ("current_portfolio", current_portfolio_summary),
        ("current_cash", current_cash_summary),
        ("current_position", current_position_summary),
        ("pending", pending_summary),
        ("planning_config", planning_config_summary),
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
    plans, mapping_reasons = _build_plans(
        business_date=business_date,
        pc_payload=pc_payload,
        cd_payload=cd_payload,
        pm_payload=pm_payload,
        current_position_rows=current_position_summary.rows,
        pending_rows=pending_summary.rows,
        source_hash_seed=_source_hash_seed(
            portfolio_construction_artifact_path,
            capital_deployment_artifact_path,
            portfolio_policy_artifact_path,
            position_management_artifact_path,
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
    elif any(reason.startswith(("planning_conflict_review", "unresolved_mapping", "quantity_unresolved", "existing_pending_conflict")) for reason in mapping_reasons) and producer_status != "BLOCK":
        producer_status = "REVIEW_REQUIRED"

    feature_date = min(
        [
            value
            for value in (
                construction_result.get("feature_date"),
                deployment_result.get("feature_date"),
                policy_result.get("feature_date"),
                pm_result.get("feature_date"),
                current_portfolio_summary.feature_date,
                current_cash_summary.feature_date,
                current_position_summary.feature_date,
                pending_summary.feature_date,
                planning_config_summary.feature_date,
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
            planning_config_summary.feature_date,
        )
    )
    if future_leakage_used:
        producer_status = "BLOCK"
        reason_codes.append("future_current_or_pending_date_detected")

    source_artifacts = [
        {"role": "portfolio_construction", "path": str(portfolio_construction_artifact_path or ""), "required": True, "status": construction_result["status"]},
        {"role": "capital_deployment", "path": str(capital_deployment_artifact_path or ""), "required": True, "status": deployment_result["status"]},
        {"role": "portfolio_policy", "path": str(portfolio_policy_artifact_path or ""), "required": True, "status": policy_result["status"]},
        {"role": "position_management", "path": str(position_management_artifact_path or ""), "required": True, "status": pm_result["status"]},
        {"role": "current_portfolio", "path": current_portfolio_summary.source_ref, "required": True, "status": current_portfolio_summary.status},
        {"role": "current_cash", "path": current_cash_summary.source_ref, "required": True, "status": current_cash_summary.status},
        {"role": "current_position", "path": current_position_summary.source_ref, "required": True, "status": current_position_summary.status},
        {"role": "pending", "path": pending_summary.source_ref, "required": True, "status": pending_summary.status},
        {"role": "planning_config", "path": planning_config_summary.source_ref, "required": True, "status": planning_config_summary.status},
    ]
    source_hashes = _source_hashes(
        portfolio_construction_artifact_path,
        capital_deployment_artifact_path,
        portfolio_policy_artifact_path,
        position_management_artifact_path,
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
        "pending_writer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_morning_planning_changed": False,
        "existing_add_planning_changed": False,
        "existing_sell_planning_changed": False,
        "pending_changed": False,
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
        errors.append("phase22_g_runtime_consumer_eligibility_must_be_not_eligible")
    for field in (
        "concrete_allocation_decided",
        "concrete_quantity_decided",
        "lot_rounding_decided",
        "pending_written",
        "submit_generated",
        "production_consumer_connected",
        "pending_writer_connected",
        "runtime_switch_performed",
        "existing_morning_planning_changed",
        "existing_add_planning_changed",
        "existing_sell_planning_changed",
        "pending_changed",
        "approval_changed",
        "submit_changed",
        "execution_changed",
    ):
        if payload.get(field) is not False:
            errors.append(f"phase22_g_field_must_be_false:{field}")
    if payload.get("legacy_authority_active") is not True:
        errors.append("phase22_g_legacy_authority_must_remain_active")
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
    if payload.get("runtime_consumer_eligibility") != "NOT_ELIGIBLE":
        raise RuntimePlanningConsumerError("Phase22-G Runtime Planning must remain NOT_ELIGIBLE")
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
        "runtime_planning_production_consumer_connected": False,
        "pending_written": False,
        "submit_generated": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "existing_morning_planning_changed": False,
        "existing_add_planning_changed": False,
        "existing_sell_planning_changed": False,
        "pending_changed": False,
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
    current_position_rows: tuple[Mapping[str, Any], ...],
    pending_rows: tuple[Mapping[str, Any], ...],
    source_hash_seed: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    pc_members = {str(item.get("security_code") or ""): item for item in pc_payload.get("portfolio_members") or [] if str(item.get("security_code") or "")}
    cd_members = {str(item.get("security_code") or ""): item for item in cd_payload.get("members") or [] if str(item.get("security_code") or "")}
    pm_positions = {str(item.get("security_code") or ""): item for item in pm_payload.get("positions") or [] if str(item.get("security_code") or "")}
    current_codes = {str(row.get("security_code") or row.get("symbol") or "") for row in current_position_rows}
    pending_codes = {str(row.get("security_code") or row.get("symbol") or "") for row in pending_rows}
    codes = sorted((set(pc_members) | set(cd_members) | set(pm_positions)) - {""})
    plans: list[dict[str, Any]] = []
    reasons: list[str] = []
    seen_intents: dict[str, set[str]] = {}
    for code in codes:
        pc_member = pc_members.get(code, {})
        cd_member = cd_members.get(code, {})
        pm_position = pm_positions.get(code, {})
        intent, intent_reasons = _resolve_intent(code, pc_member, cd_member, pm_position)
        reasons.extend(intent_reasons)
        if intent == "NO_ACTION" and str(pc_member.get("membership_intent") or "") == "EXCLUDE":
            continue
        side = "BUY" if intent in {"BUY_NEW", "BUY_ADD"} else ("SELL" if intent in {"SELL_REDUCE", "SELL_EXIT"} else ("NONE" if intent == "NO_ACTION" else "UNRESOLVED"))
        quantity_required = intent in {"BUY_NEW", "BUY_ADD", "SELL_REDUCE", "SELL_EXIT"}
        quantity_status = "UNRESOLVED" if quantity_required else "NOT_REQUIRED"
        pending_eligibility = "CANDIDATE_ONLY" if quantity_required else ("NOT_REQUIRED" if intent == "NO_ACTION" else "REVIEW_REQUIRED")
        plan_reasons = list(dict.fromkeys(intent_reasons))
        if quantity_required:
            plan_reasons.append("quantity_unresolved_by_phase22_g")
            reasons.append(f"quantity_unresolved:{code}")
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
            "quantity_authority": QUANTITY_AUTHORITY if quantity_required else "",
            "quantity_status": quantity_status,
            "quantity_reference": "downstream_runtime_quantity_authority" if quantity_required else "",
            "pending_eligibility": pending_eligibility,
            "pending_candidate_contract": {
                "pending_candidate_generated": False,
                "pending_writer_connected": False,
                "submit_allowed": False,
                "broker_write_allowed": False,
            },
            "confidence": float(pm_position.get("confidence") or pc_member.get("confidence") or 0.0),
            "uncertainty": str(pm_position.get("uncertainty") or pc_member.get("uncertainty") or "UPSTREAM_REVIEW_REQUIRED"),
            "reason_codes": sorted(set(plan_reasons)),
        }
        plans.append(plan)
    for code, intents in seen_intents.items():
        if {"BUY_NEW", "BUY_ADD"} <= intents:
            reasons.append(f"planning_conflict_block:buy_new_buy_add:{code}")
        if intents & {"BUY_NEW", "BUY_ADD"} and intents & {"SELL_REDUCE", "SELL_EXIT"}:
            reasons.append(f"planning_conflict_block:buy_sell:{code}")
        if {"SELL_REDUCE", "SELL_EXIT"} <= intents:
            reasons.append(f"planning_conflict_block:reduce_exit:{code}")
    return plans, sorted(set(reasons))


def _resolve_intent(
    code: str,
    pc_member: Mapping[str, Any],
    cd_member: Mapping[str, Any],
    pm_position: Mapping[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    pm_action = str(pm_position.get("action") or "").upper()
    membership = str(pc_member.get("membership_intent") or "").upper()
    allocation = str(cd_member.get("allocation_posture") or "").upper()
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
        if allocation == "WITHHOLD":
            return "UNRESOLVED", ["capital_deployment_withhold_blocks_buy_new"]
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
        "pending_eligibility",
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
        if plan.get("quantity_authority") != QUANTITY_AUTHORITY:
            errors.append(f"invalid_quantity_authority:{index}")
        if plan.get("quantity_status") != "UNRESOLVED":
            errors.append(f"quantity_required_must_remain_unresolved:{index}")
    elif plan.get("quantity_required") is False:
        if plan.get("quantity_authority") not in {"", None}:
            errors.append(f"quantity_authority_forbidden_when_not_required:{index}")
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


def _source_hashes(
    portfolio_construction_artifact_path: Path | str | None,
    capital_deployment_artifact_path: Path | str | None,
    portfolio_policy_artifact_path: Path | str | None,
    position_management_artifact_path: Path | str | None,
    current_portfolio_summary: RuntimePlanningSourceSummary,
    current_cash_summary: RuntimePlanningSourceSummary,
    current_position_summary: RuntimePlanningSourceSummary,
    pending_summary: RuntimePlanningSourceSummary,
    planning_config_summary: RuntimePlanningSourceSummary,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for role, path in (
        ("portfolio_construction", portfolio_construction_artifact_path),
        ("capital_deployment", capital_deployment_artifact_path),
        ("portfolio_policy", portfolio_policy_artifact_path),
        ("position_management", position_management_artifact_path),
    ):
        items.append({"role": role, "path": str(path or ""), "sha256": sha256_file(path) if path and Path(path).is_file() else ""})
    for role, summary in (
        ("current_portfolio", current_portfolio_summary),
        ("current_cash", current_cash_summary),
        ("current_position", current_position_summary),
        ("pending", pending_summary),
        ("planning_config", planning_config_summary),
    ):
        items.append({"role": role, "path": summary.source_ref, "sha256": _strip_sha256(summary.source_hash)})
    return items


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
