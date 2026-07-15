"""Runtime Data Readiness Gate for Runtime v2.

The gate is a read-only first layer before Morning, SELL Planning, Submit, or
Execution.  It aggregates authoritative evidence and writes one fixed readiness
artifact per business date.  Component-local validation remains authoritative
and is not replaced by this module.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.operations.market_calendar import resolve_operation_date
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    validate_feature_consumer_readiness,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    load_feature_date_contract,
    resolve_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.current_state.temporal import build_current_temporal_candidate
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import resolve_buy_ai_model_paths
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import _isolated_test_artifact_paths_allowed
from ai_fund_lab_v2.runtime_v2.position_management.producer import (
    validate_position_management_input_contract,
)
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision
from ai_fund_lab_v2.runtime_v2.human_review import (
    EXPECTED_ACTION_SCOPE,
    HIGH_RISK_REVIEW_ISSUE_CODE,
    HIGH_RISK_REVIEW_REASON,
    validate_human_review_artifact,
)
from ai_fund_lab_v2.runtime_v2.runtime_state import validate_runtime_operation_state


DATA_READINESS_SCHEMA_VERSION = "runtime_v2_data_readiness_v1"
FULL_MORNING_SCOPES = {"morning", "morning_full"}
REVIEW_ONLY_MORNING_SCOPE = "morning_sell_hold_review_only"
ALLOWED_READINESS_SCOPES = (
    "morning",
    "morning_full",
    REVIEW_ONLY_MORNING_SCOPE,
    "sell_planning",
    "submit",
    "execution",
    "current_valuation",
)


@dataclass(frozen=True)
class RuntimeDataReadinessResult:
    status: str
    reason: str
    artifact_path: str
    payload: dict[str, Any]

    @property
    def review_required(self) -> bool:
        return self.status == "REVIEW_REQUIRED"

    @property
    def halt_required(self) -> bool:
        return self.status == "HALT"

    def to_manifest_fields(self) -> dict[str, Any]:
        fields = {
            "data_readiness_status": self.status,
            "data_readiness_scope": self.payload.get("readiness_scope") or "",
            "data_readiness_artifact_path": self.artifact_path,
            "data_readiness_review_reasons": list(self.payload.get("review_reasons") or []),
            "data_readiness_halt_reasons": list(self.payload.get("halt_reasons") or []),
            "data_readiness_next_operator_action": self.payload.get("next_operator_action") or "",
        }
        for key in (
            "market_calendar_status",
            "market_data_status",
            "quote_status",
            "market_summary_status",
            "safety_market_input_status",
            "candidate_model_path",
            "candidate_model_status",
            "opportunity_model_path",
            "opportunity_model_status",
            "pending_slot_status",
            "pending_active",
            "runtime_core_production_baseline",
            "runtime_state_status",
            "runtime_state_reason",
            "runtime_state_artifact_path",
            "full_morning_readiness",
            "review_only_morning_readiness",
            "human_review_status",
            "human_review_artifact_path",
            "broker_environment",
            "broker_environment_production",
            "evidence_production_equivalent",
            "acceptance_production_equivalent",
            "runtime_execution_path",
            "component_reasons",
            "effective_component_statuses",
        ):
            fields[key] = self.payload.get(key)
        fields.update(_compat_manifest_fields(self.payload))
        return fields


def _compat_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose gate-stop evidence under existing producer manifest names."""

    if payload.get("overall_status") == "READY":
        return {}
    components = payload.get("components") or {}
    scope = str(payload.get("readiness_scope") or "")
    fields: dict[str, Any] = {}
    if scope == "morning":
        feature = components.get("feature") or {}
        fields.update(
            {
                "buy_ai_status": "REVIEW_REQUIRED",
                "buy_ai_reason": ",".join(payload.get("review_reasons") or ()) or "data_readiness_review_required",
                "candidate_schema_status": feature.get("candidate_schema_status") or "",
                "candidate_missing_columns": feature.get("candidate_missing_columns") or [],
                "candidate_review_required": (feature.get("candidate_schema_status") or "") != "READY",
                "candidate_review_reason": feature.get("reason") or "",
                "opportunity_schema_status": feature.get("opportunity_schema_status") or "",
                "opportunity_review_required": (feature.get("opportunity_schema_status") or "") != "READY",
                "opportunity_review_reason": feature.get("reason") or "",
            }
        )
    if scope == "sell_planning":
        pm = components.get("pm") or {}
        contract = pm.get("contract") or {}
        if pm.get("status") == "REVIEW_REQUIRED":
            fields.update(
                {
                    "pm_status": "REVIEW_REQUIRED",
                    "pm_reason": pm.get("reason") or "pm_input_contract_review_required",
                    "pm_input_schema_status": contract.get("pm_input_schema_status") or "REVIEW_REQUIRED",
                    "pm_current_source": contract.get("pm_current_source") or "",
                    "pm_current_as_of": contract.get("pm_current_as_of") or "",
                    "pm_current_freshness": contract.get("pm_current_freshness") or "",
                    "pm_feature_source": contract.get("pm_feature_source") or "",
                    "pm_feature_row_count": contract.get("pm_feature_row_count"),
                    "pm_feature_date": contract.get("pm_feature_date") or "",
                    "pm_opportunity_source": contract.get("pm_opportunity_source") or "",
                    "pm_opportunity_status": contract.get("pm_opportunity_status") or "",
                    "pm_missing_fields": contract.get("pm_missing_fields") or [],
                    "pm_missing_symbols": contract.get("pm_missing_symbols") or [],
                    "pm_derived_fields": contract.get("pm_derived_fields") or [],
                    "pm_defaulted_fields": contract.get("pm_defaulted_fields") or [],
                    "pm_review_required": True,
                    "pm_review_reason": contract.get("pm_review_reason") or pm.get("reason") or "",
                }
            )
    return fields


def _feature_date_contract_payload(
    *,
    operations_root: Path,
    business_date: str,
    explicit_feature_date: str | None,
) -> dict[str, Any]:
    contract = load_feature_date_contract(
        operations_root=operations_root,
        requested_feature_date=business_date,
    )
    if contract is None and explicit_feature_date:
        return {
            "status": "EXPLICIT",
            "reason": "explicit_feature_date_argument",
            "requested_feature_date": business_date,
            "selected_feature_date": explicit_feature_date,
            "contract_artifact_path": "",
            "contract_source": "explicit_cli_argument",
            "carryover_used": explicit_feature_date != business_date,
        }
    if contract is None:
        contract = resolve_feature_date_contract(
            operations_root=operations_root,
            requested_feature_date=business_date,
            persist_consumer_readiness=False,
        )
        payload = contract.to_payload()
        payload["contract_artifact_path"] = contract.contract_artifact_path
        payload["contract_source"] = "resolved_read_only_feature_date_contract"
        return payload
    payload = contract.to_payload()
    payload["contract_artifact_path"] = contract.contract_artifact_path
    payload["contract_source"] = "materialized_feature_date_contract"
    return payload


def evaluate_runtime_data_readiness(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    readiness_scope: str,
    feature_root: Path | str | None = None,
    feature_date: str | None = None,
    candidate_model_path: Path | str | None = None,
    opportunity_model_path: Path | str | None = None,
    pm_opportunity_path: Path | str | None = None,
    pm_feature_path: Path | str | None = None,
    allow_non_trading_day_demo: bool = False,
    broker_environment: str | None = None,
    runtime_test_evidence_root: Path | str | None = None,
    runtime_test_run_id: str | None = None,
    runtime_test_profile_id: str | None = None,
    broker_write: bool = False,
    external_delivery: bool = False,
    now: datetime | None = None,
) -> RuntimeDataReadinessResult:
    if readiness_scope not in ALLOWED_READINESS_SCOPES:
        raise ValueError(f"unsupported readiness scope: {readiness_scope}")
    root = Path(runtime_root)
    generated_at = _iso(now or datetime.now(timezone.utc))
    operations_root = Path(feature_root).parent if feature_root else root / "operations"
    feature_contract = _feature_date_contract_payload(
        operations_root=operations_root,
        business_date=business_date,
        explicit_feature_date=feature_date,
    )
    selected_feature_date = str(feature_contract.get("selected_feature_date") or feature_date or business_date)
    base_dir = root.parent if root.name == ".runtime" else Path(".")
    source_paths: dict[str, str] = {}
    missing_evidence: list[str] = []
    missing_columns: list[str] = []
    stale_artifacts: list[str] = []
    mismatched_dates: list[str] = []
    review_reasons: list[str] = []
    halt_reasons: list[str] = []
    component_reasons: dict[str, list[str]] = {
        "market": [],
        "quote": [],
        "broker": [],
        "safety": [],
        "feature": [],
        "candidate": [],
        "opportunity": [],
        "current": [],
        "pending": [],
        "runtime_environment": [],
        "runtime_state": [],
        "human_review": [],
    }
    review_only_scope_payload: dict[str, Any] = {
        "status": "NOT_REQUIRED",
        "reason": "",
        "missing_evidence": [],
        "stale_artifacts": [],
        "mismatched_fields": [],
        "source_paths": {},
    }

    calendar = resolve_operation_date(business_date, root=base_dir)
    business_day = bool(calendar.get("is_business_day"))
    market_open = not bool(calendar.get("market_closed"))
    override = bool(mode == "demo" and allow_non_trading_day_demo and not business_day and not market_open)
    market_payload = _market_readiness_payload(root=root, business_date=business_date, market_open=market_open, override=override)
    source_paths.update(market_payload["source_paths"])
    if market_payload["status"] == "REVIEW_REQUIRED":
        review_reasons.append(market_payload["reason"])
        component_reasons["market"].append(market_payload["reason"])
        missing_evidence.extend(market_payload["missing_evidence"])
    latest_market_date = str(calendar.get("latest_available_market_date") or "")
    previous_trading_date = str(calendar.get("previous_business_day") or "")
    expected_current_as_of = latest_market_date if override else business_date
    current_payload, current_status, current_reason, current_path = _read_json_object(
        root / "persistent_ledger" / "state.json",
        corrupt_status="HALT",
    )
    runtime_state_payload, _, _, runtime_state_path = _read_json_object(
        root / "runtime_state" / "current_state.json",
        corrupt_status="REVIEW_REQUIRED",
    )
    source_paths["current"] = str(current_path)
    actual_current_as_of = str(current_payload.get("as_of") or current_payload.get("business_date") or "")
    current_freshness = "FRESH"
    current_temporal_payload = _current_temporal_payload(
        root=root,
        business_date=business_date,
        current_payload=current_payload,
    )
    valuation_temporal_authority = _current_valuation_temporal_authority(
        readiness_scope=readiness_scope,
        business_date=business_date,
        previous_trading_date=previous_trading_date,
        valuation_as_of=str(current_temporal_payload.get("valuation_as_of") or ""),
    )
    if valuation_temporal_authority["status"] == "READY":
        current_temporal_payload["current_valuation_status"] = "READY"
    elif valuation_temporal_authority["status"] == "HALT":
        current_temporal_payload["current_valuation_status"] = "HALT"
    elif valuation_temporal_authority["status"] == "REVIEW_REQUIRED":
        current_temporal_payload["current_valuation_status"] = "REVIEW_REQUIRED"
    if current_status == "HALT":
        halt_reasons.append(current_reason)
        component_reasons["current"].append(current_reason)
    elif current_status != "READY":
        missing_evidence.append("current")
        review_reasons.append("current_missing")
        component_reasons["current"].append("current_missing")
    elif bool(current_payload.get("review_required")):
        review_reasons.append("current_review_required")
        component_reasons["current"].append("current_review_required")
    elif mode == "historical" and _historical_initial_current_ready(current_payload):
        actual_current_as_of = business_date
        current_temporal_payload["current_position_status"] = "READY"
        current_temporal_payload["current_valuation_status"] = "READY"
        current_temporal_payload["position_state_as_of"] = business_date
        current_temporal_payload["valuation_as_of"] = business_date
        current_temporal_payload["historical_temporal_authority"] = "historical_initial_state"
    elif current_temporal_payload["is_temporal_schema"]:
        if current_temporal_payload["current_position_status"] not in {"READY", "VALID_CARRYOVER"}:
            current_freshness = "STALE"
            stale_artifacts.append("current_position")
            review_reasons.append("current_position_not_ready")
            component_reasons["current"].append("current_position_not_ready")
        if valuation_temporal_authority["status"] == "HALT":
            current_freshness = "STALE"
            stale_artifacts.append("current_valuation")
            halt_reasons.append(valuation_temporal_authority["reason"])
            component_reasons["current"].append(valuation_temporal_authority["reason"])
        if current_temporal_payload["current_valuation_status"] not in {"READY", "VALID_CARRYOVER"}:
            current_freshness = "STALE"
            stale_artifacts.append("current_valuation")
            if valuation_temporal_authority["status"] != "HALT":
                review_reasons.append("current_valuation_not_ready")
                component_reasons["current"].append("current_valuation_not_ready")
    elif actual_current_as_of != expected_current_as_of:
        current_freshness = "STALE"
        stale_artifacts.append("current")
        review_reasons.append("current_stale")
        component_reasons["current"].append("current_stale")
    elif mode == "production" and override:
        halt_reasons.append("non_trading_day_demo_override_forbidden_in_production")

    feature_payload = _feature_readiness_payload(
        operations_root=operations_root,
        feature_date=selected_feature_date,
    )
    feature_payload["feature_date_contract"] = feature_contract
    feature_payload["selected_feature_date"] = selected_feature_date
    source_paths["feature_consumer_readiness"] = str(feature_payload.get("readiness_artifact_path") or "")
    feature_status = "READY" if feature_payload.get("consumer_ready") else "REVIEW_REQUIRED"
    if (
        _scope_requires_feature(readiness_scope)
        and mode == "historical"
        and feature_contract.get("contract_source") == "explicit_cli_argument"
    ):
        reason = "historical_feature_date_contract_missing"
        review_reasons.append(reason)
        component_reasons["feature"].append(reason)
    if _scope_requires_feature(readiness_scope) and feature_contract.get("status") not in {"PASS", "EXPLICIT"}:
        reason = str(feature_contract.get("reason") or "feature_date_contract_not_ready")
        review_reasons.append(reason)
        component_reasons["feature"].append(reason)
    if _scope_requires_feature(readiness_scope) and feature_status != "READY":
        reason = str(feature_payload.get("reason") or "feature_consumer_readiness_review_required")
        review_reasons.append(reason)
        component_reasons["feature"].append(reason)
        missing_columns.extend(feature_payload.get("candidate_missing_columns") or [])

    candidate_model_path_resolved, opportunity_model_path_resolved = resolve_buy_ai_model_paths(
        candidate_model_path=candidate_model_path,
        opportunity_model_path=opportunity_model_path,
        allow_isolated_test_paths=_isolated_test_artifact_paths_allowed(Path(runtime_root), candidate_model_path, opportunity_model_path, None),
    )
    candidate_status = _candidate_pre_inference_status(
        scope=readiness_scope,
        candidate_model_path=candidate_model_path_resolved,
        feature_payload=feature_payload,
    )
    if candidate_status["status"] == "REVIEW_REQUIRED":
        review_reasons.append(candidate_status["reason"])
        component_reasons["candidate"].append(candidate_status["reason"])
        missing_evidence.extend(candidate_status["missing_evidence"])
    elif candidate_status["status"] == "HALT":
        halt_reasons.append(candidate_status["reason"])
        component_reasons["candidate"].append(candidate_status["reason"])
    source_paths.update(candidate_status["source_paths"])

    opportunity_status = _opportunity_pre_inference_status(
        scope=readiness_scope,
        opportunity_model_path=opportunity_model_path_resolved,
        feature_payload=feature_payload,
    )
    if opportunity_status["status"] == "REVIEW_REQUIRED":
        review_reasons.append(opportunity_status["reason"])
        component_reasons["opportunity"].append(opportunity_status["reason"])
        missing_evidence.extend(opportunity_status["missing_evidence"])
    elif opportunity_status["status"] == "HALT":
        halt_reasons.append(opportunity_status["reason"])
        component_reasons["opportunity"].append(opportunity_status["reason"])
    source_paths.update(opportunity_status["source_paths"])

    pm_feature_path_resolved, pm_opportunity_path_resolved = _resolve_pm_input_paths_from_feature_contract(
        root=root,
        feature_contract=feature_contract,
        feature_date=selected_feature_date,
        explicit_pm_feature_path=pm_feature_path,
        explicit_pm_opportunity_path=pm_opportunity_path,
    )
    pm_payload = _pm_readiness_payload(
        scope=readiness_scope,
        current=current_payload,
        current_path=current_path,
        runtime_state=runtime_state_payload,
        runtime_state_path=runtime_state_path,
        business_date=business_date,
        feature_date=selected_feature_date,
        pm_opportunity_path=pm_opportunity_path_resolved,
        pm_feature_path=pm_feature_path_resolved,
    )
    if pm_payload["status"] == "REVIEW_REQUIRED":
        review_reasons.append(pm_payload["reason"])
        component_reasons["feature"].append(pm_payload["reason"])
        missing_evidence.extend(pm_payload["missing_evidence"])
        missing_columns.extend(pm_payload["missing_fields"])
        stale_artifacts.extend(pm_payload["stale_artifacts"])
    source_paths.update(pm_payload["source_paths"])

    broker_payload = _broker_readiness_payload(root=root, business_date=business_date, scope=readiness_scope)
    if broker_payload["status"] == "REVIEW_REQUIRED":
        review_reasons.append(broker_payload["reason"])
        component_reasons["broker"].append(broker_payload["reason"])
        missing_evidence.extend(broker_payload["missing_evidence"])
    source_paths.update(broker_payload["source_paths"])

    pending_payload = _pending_readiness_payload(
        root=root,
        business_date=business_date,
        mode=mode,
        runtime_test_run_id=runtime_test_run_id or "",
        runtime_test_profile_id=runtime_test_profile_id or "",
        runtime_test_evidence_root=str(runtime_test_evidence_root or ""),
    )
    if pending_payload["status"] == "REVIEW_REQUIRED":
        review_reasons.append(pending_payload["reason"])
        component_reasons["pending"].append(pending_payload["reason"])
        missing_evidence.extend(pending_payload["missing_evidence"])
        stale_artifacts.extend(pending_payload["stale_artifacts"])
        mismatched_dates.extend(pending_payload["mismatched_dates"])
    source_paths.update(pending_payload["source_paths"])

    safety_payload = _safety_readiness_payload(
        root=root,
        business_date=business_date,
        mode=mode,
        current_payload=current_payload,
        pending_payload=pending_payload,
        runtime_test_run_id=runtime_test_run_id or "",
        runtime_test_profile_id=runtime_test_profile_id or "",
        runtime_test_evidence_root=str(runtime_test_evidence_root or ""),
        broker_write=broker_write,
        external_delivery=external_delivery,
    )
    if safety_payload["status"] == "HALT":
        halt_reasons.append(safety_payload["reason"])
        component_reasons["safety"].append(safety_payload["reason"])
    elif safety_payload["status"] == "REVIEW_REQUIRED":
        review_reasons.append(safety_payload["reason"])
        component_reasons["safety"].append(safety_payload["reason"])
        missing_evidence.extend(safety_payload["missing_evidence"])
        stale_artifacts.extend(safety_payload["stale_artifacts"])
    dependency_payload = _safety_dependency_payload(safety_payload=safety_payload, broker_payload=broker_payload)
    if dependency_payload["broker_dependency_status"] == "REVIEW_REQUIRED":
        component_reasons["broker"].extend(dependency_payload["broker_reasons"])
        missing_evidence.extend(dependency_payload["missing_evidence"])
    effective_quote_status = _max_status(str(market_payload.get("quote_status") or "READY"), dependency_payload["quote_status"])
    if effective_quote_status == "REVIEW_REQUIRED":
        component_reasons["quote"].extend(dependency_payload["quote_reasons"])
        if market_payload.get("quote_reason"):
            component_reasons["quote"].append(str(market_payload["quote_reason"]))
        missing_evidence.extend(dependency_payload["missing_evidence"])
    source_paths.update(safety_payload["source_paths"])

    if readiness_scope == REVIEW_ONLY_MORNING_SCOPE:
        review_only_scope_payload = _review_only_morning_payload(
            root=root,
            business_date=business_date,
            mode=mode,
            feature_payload=feature_payload,
            broker_payload=broker_payload,
            safety_payload=safety_payload,
            now=now,
        )
        source_paths.update(review_only_scope_payload["source_paths"])
        if review_only_scope_payload["status"] == "READY":
            review_reasons = [
                reason for reason in review_reasons if str(reason).upper() != HIGH_RISK_REVIEW_REASON
            ]
            component_reasons["safety"] = [
                reason
                for reason in component_reasons["safety"]
                if str(reason).upper() != HIGH_RISK_REVIEW_REASON
            ]
        elif review_only_scope_payload["status"] == "REVIEW_REQUIRED":
            review_reasons.append(review_only_scope_payload["reason"])
            component_reasons["human_review"].append(review_only_scope_payload["reason"])
            missing_evidence.extend(review_only_scope_payload["missing_evidence"])
            stale_artifacts.extend(review_only_scope_payload["stale_artifacts"])
            mismatched_dates.extend(review_only_scope_payload.get("mismatched_fields") or [])

    runtime_state_payload = _runtime_state_readiness_payload(root=root, business_date=business_date, mode=mode)
    if runtime_state_payload["status"] == "HALT":
        halt_reasons.append(runtime_state_payload["reason"])
        component_reasons["runtime_state"].append(runtime_state_payload["reason"])
    elif runtime_state_payload["status"] == "REVIEW_REQUIRED":
        review_reasons.append(runtime_state_payload["reason"])
        component_reasons["runtime_state"].append(runtime_state_payload["reason"])
        missing_evidence.extend(runtime_state_payload["missing_evidence"])
        stale_artifacts.extend(runtime_state_payload["stale_artifacts"])
    source_paths.update(runtime_state_payload["source_paths"])

    environment_payload = _environment_readiness_payload(
        mode=mode,
        broker_environment=broker_environment or mode,
        notification_mode="payload-only",
        override=override,
        allow_override=allow_non_trading_day_demo,
        broker_write=broker_write,
        external_delivery=external_delivery,
    )
    if environment_payload["status"] == "HALT":
        halt_reasons.append(environment_payload["reason"])
        component_reasons["runtime_environment"].append(environment_payload["reason"])

    overall_status = "HALT" if halt_reasons else "REVIEW_REQUIRED" if review_reasons else "READY"
    market_effective_status = _max_status(
        market_payload["status"],
        effective_quote_status,
        dependency_payload["safety_market_input_status"],
    )
    broker_effective_status = _max_status(
        broker_payload["status"],
        dependency_payload["broker_dependency_status"],
    )
    effective_safety_status = safety_payload["status"]
    if readiness_scope == REVIEW_ONLY_MORNING_SCOPE and review_only_scope_payload["status"] == "READY":
        effective_safety_status = "READY_FOR_REVIEW_ONLY"
    effective_component_statuses = {
        "market": market_effective_status,
        "quote": effective_quote_status,
        "broker": broker_effective_status,
        "safety": effective_safety_status,
        "feature": feature_status,
        "candidate": candidate_status["status"],
        "opportunity": opportunity_status["status"],
        "current": "READY" if current_status == "READY" and current_freshness == "FRESH" else "REVIEW_REQUIRED",
        "pending": pending_payload["status"],
        "runtime_environment": environment_payload["status"],
        "runtime_state": runtime_state_payload["status"],
        "human_review": review_only_scope_payload["status"],
    }
    artifact_path = (
        Path(runtime_test_evidence_root) / "daily" / business_date / "data_readiness" / "data_readiness.json"
        if runtime_test_evidence_root
        else root / "runtime_state" / "data_readiness" / business_date / "data_readiness.json"
    )
    payload = {
        "schema_version": DATA_READINESS_SCHEMA_VERSION,
        "business_date": business_date,
        "generated_at": generated_at,
        "runtime_mode": mode,
        "readiness_scope": readiness_scope,
        "overall_status": overall_status,
        "review_required": overall_status == "REVIEW_REQUIRED",
        "halt_required": overall_status == "HALT",
        "market_calendar_status": "READY" if market_open or override else "REVIEW_REQUIRED",
        "market_data_status": market_payload["market_data_status"],
        "quote_status": effective_quote_status,
        "market_summary_status": market_payload["market_summary_status"],
        "safety_market_input_status": dependency_payload["safety_market_input_status"],
        "market_status": market_effective_status,
        "feature_status": feature_status,
        "selected_feature_date": selected_feature_date,
        "feature_date_contract": feature_contract,
        "candidate_status": candidate_status["status"],
        "opportunity_status": opportunity_status["status"],
        "candidate_model_path": candidate_status.get("candidate_model_path") or "",
        "candidate_model_status": candidate_status.get("candidate_model_status") or "",
        "opportunity_model_path": opportunity_status.get("opportunity_model_path") or "",
        "opportunity_model_status": opportunity_status.get("opportunity_model_status") or "",
        "pm_status": pm_payload["status"],
        "current_status": "READY" if current_status == "READY" and current_freshness == "FRESH" else "REVIEW_REQUIRED",
        "broker_direct_scope_status": broker_payload["direct_status"],
        "broker_safety_dependency_status": dependency_payload["broker_dependency_status"],
        "broker_effective_status": broker_effective_status,
        "broker_status": broker_effective_status,
        "safety_status": safety_payload["status"],
        "effective_safety_status": effective_safety_status,
        "human_review_status": review_only_scope_payload["status"],
        "human_review_artifact_path": review_only_scope_payload.get("artifact_path") or "",
        "full_morning_readiness": "NOT_APPLICABLE" if readiness_scope == REVIEW_ONLY_MORNING_SCOPE else overall_status,
        "review_only_morning_readiness": overall_status if readiness_scope == REVIEW_ONLY_MORNING_SCOPE else "NOT_APPLICABLE",
        "pending_status": pending_payload["status"],
        "pending_slot_status": pending_payload["slot_status"],
        "pending_active": pending_payload["active_pending"],
        "runtime_environment_status": environment_payload["status"],
        "runtime_state_status": runtime_state_payload["status"],
        "runtime_state_reason": runtime_state_payload["reason"],
        "runtime_state_artifact_path": runtime_state_payload["artifact_path"],
        "missing_columns": _unique(missing_columns),
        "missing_evidence": _unique(missing_evidence),
        "stale_artifacts": _unique(stale_artifacts),
        "mismatched_dates": _unique(mismatched_dates),
        "source_paths": {key: value for key, value in source_paths.items() if value},
        "review_reasons": _unique(review_reasons),
        "halt_reasons": _unique(halt_reasons),
        "next_operator_action": _next_operator_action(overall_status, review_reasons, halt_reasons),
        "current_expected_as_of": expected_current_as_of,
        "current_actual_as_of": actual_current_as_of,
        "current_valuation_expected_date": valuation_temporal_authority["expected_date"],
        "current_valuation_expected_date_policy": valuation_temporal_authority["expected_date_policy"],
        "current_valuation_previous_trading_date": previous_trading_date,
        "current_valuation_same_day_allowed": valuation_temporal_authority["same_day_allowed"],
        "current_valuation_previous_close_carry_allowed": valuation_temporal_authority["previous_close_carry_allowed"],
        "current_valuation_temporal_authority": valuation_temporal_authority["authority"],
        "current_valuation_temporal_reason": valuation_temporal_authority["reason"],
        "current_position_status": current_temporal_payload["current_position_status"],
        "current_valuation_status": current_temporal_payload["current_valuation_status"],
        "position_state_as_of": current_temporal_payload["position_state_as_of"],
        "valuation_as_of": current_temporal_payload["valuation_as_of"],
        "source_market_date": current_temporal_payload["source_market_date"],
        "current_legacy_as_of_used": current_temporal_payload["legacy_as_of_used"],
        "current_freshness_policy": "non_trading_day_demo_override_latest_expected_trading_date" if override else "business_date",
        "non_trading_day_demo_override": override,
        "runtime_core_production_baseline": True,
        "broker_environment": broker_environment or mode,
        "broker_environment_id": broker_environment or mode,
        "broker_environment_production": mode == "production",
        "evidence_production_equivalent": mode == "production" and not override,
        "acceptance_production_equivalent": mode == "production" and not override,
        "production_equivalent": mode == "production" and not override,
        "runtime_execution_path": "regular_runtime",
        "acceptance_scope": _acceptance_scope_for_mode(mode),
        "component_reasons": {key: _unique(value) for key, value in component_reasons.items()},
        "effective_component_statuses": effective_component_statuses,
        "components": {
            "market": market_payload,
            "feature": feature_payload,
            "candidate": candidate_status,
            "opportunity": opportunity_status,
            "pm": pm_payload,
            "broker": broker_payload,
            "safety_dependency": dependency_payload,
            "safety": safety_payload,
            "human_review": review_only_scope_payload,
            "runtime_state": runtime_state_payload,
            "pending": pending_payload,
            "runtime_environment": environment_payload,
        },
        "gate_does_not_generate_ai_decisions": True,
        "consumer_validation_remains_required": True,
    }
    _write_json(artifact_path, payload)
    return RuntimeDataReadinessResult(
        status=overall_status,
        reason=payload["next_operator_action"],
        artifact_path=str(artifact_path),
        payload=payload,
    )


def _feature_readiness_payload(*, operations_root: Path, feature_date: str) -> dict[str, Any]:
    artifact = operations_root / "feature_consumer_readiness" / f"{feature_date}.json"
    if artifact.is_file():
        payload, status, reason, _ = _read_json_object(artifact)
        if status == "READY":
            return payload
        return {
            "status": "REVIEW_REQUIRED",
            "reason": reason,
            "consumer_ready": False,
            "readiness_artifact_path": str(artifact),
        }
    try:
        readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date=feature_date)
        payload = readiness.to_payload()
        payload["readiness_artifact_path"] = str(artifact)
        payload["evaluated_by_data_readiness_gate"] = True
        return payload
    except Exception as exc:  # pragma: no cover - corrupt parquet engines vary by platform
        return {
            "status": "REVIEW_REQUIRED",
            "reason": f"feature_consumer_readiness_error:{exc}",
            "consumer_ready": False,
            "readiness_artifact_path": str(artifact),
        }


def _runtime_state_readiness_payload(*, root: Path, business_date: str, mode: str) -> dict[str, Any]:
    result = validate_runtime_operation_state(
        runtime_root=root,
        business_date=business_date,
        mode=mode,
    )
    missing = list(result.missing_fields)
    stale = list(result.stale_fields)
    if result.status == "HALT":
        return {
            "status": "HALT",
            "reason": result.reason,
            "artifact_path": result.artifact_path,
            "missing_evidence": missing,
            "stale_artifacts": stale,
            "source_paths": {"runtime_state": result.artifact_path},
            "contract_role": result.payload.get("role") or "",
            "schema_version": result.payload.get("schema_version") or "",
        }
    if result.status != "READY":
        return {
            "status": "REVIEW_REQUIRED",
            "reason": result.reason,
            "artifact_path": result.artifact_path,
            "missing_evidence": missing,
            "stale_artifacts": stale or ["runtime_state"],
            "source_paths": {"runtime_state": result.artifact_path},
            "contract_role": result.payload.get("role") or "",
            "schema_version": result.payload.get("schema_version") or "",
        }
    return {
        "status": "READY",
        "reason": result.reason,
        "artifact_path": result.artifact_path,
        "missing_evidence": [],
        "stale_artifacts": [],
        "source_paths": {"runtime_state": result.artifact_path},
        "contract_role": result.payload.get("role") or "",
        "schema_version": result.payload.get("schema_version") or "",
        "state": result.payload.get("state") or "",
        "safety_state": result.payload.get("safety_state") or "",
        "generated_at": result.payload.get("generated_at") or "",
    }


def _current_temporal_payload(*, root: Path, business_date: str, current_payload: dict[str, Any]) -> dict[str, Any]:
    is_temporal = bool(current_payload.get("temporal_schema_version"))
    if not current_payload:
        return {
            "is_temporal_schema": False,
            "current_position_status": "MISSING",
            "current_valuation_status": "MISSING",
            "position_state_as_of": "",
            "valuation_as_of": "",
            "source_market_date": "",
            "legacy_as_of_used": False,
        }
    try:
        candidate, metadata, _, _ = build_current_temporal_candidate(
            runtime_root=root,
            business_date=business_date,
            current_payload=current_payload,
        )
    except Exception:
        return {
            "is_temporal_schema": is_temporal,
            "current_position_status": "REVIEW_REQUIRED",
            "current_valuation_status": "REVIEW_REQUIRED",
            "position_state_as_of": "",
            "valuation_as_of": "",
            "source_market_date": "",
            "legacy_as_of_used": True,
        }
    return {
        "is_temporal_schema": is_temporal,
        "current_position_status": candidate.get("current_position_status") or "REVIEW_REQUIRED",
        "current_valuation_status": candidate.get("current_valuation_status") or "REVIEW_REQUIRED",
        "position_state_as_of": candidate.get("position_state_as_of") or "",
        "valuation_as_of": candidate.get("valuation_as_of") or "",
        "source_market_date": candidate.get("source_market_date") or "",
        "legacy_as_of_used": metadata.legacy_as_of_used,
    }


def _current_valuation_temporal_authority(
    *,
    readiness_scope: str,
    business_date: str,
    previous_trading_date: str,
    valuation_as_of: str,
) -> dict[str, Any]:
    morning_scope = readiness_scope in {*FULL_MORNING_SCOPES, REVIEW_ONLY_MORNING_SCOPE, "sell_planning"}
    if not valuation_as_of:
        return {
            "status": "REVIEW_REQUIRED",
            "expected_date": previous_trading_date if morning_scope else business_date,
            "expected_date_policy": "morning_previous_close_or_same_day" if morning_scope else "business_date_close",
            "same_day_allowed": morning_scope,
            "previous_close_carry_allowed": False,
            "authority": "missing_current_valuation",
            "reason": "current_valuation_evidence_missing",
        }
    actual = valuation_as_of[:10]
    if actual > business_date:
        return {
            "status": "HALT",
            "expected_date": previous_trading_date if morning_scope else business_date,
            "expected_date_policy": "morning_previous_close_or_same_day" if morning_scope else "business_date_close",
            "same_day_allowed": morning_scope,
            "previous_close_carry_allowed": False,
            "authority": "future_current_valuation_rejected",
            "reason": "current_valuation_future_date",
        }
    if morning_scope:
        if actual == business_date:
            return {
                "status": "READY",
                "expected_date": business_date,
                "expected_date_policy": "morning_previous_close_or_same_day",
                "same_day_allowed": True,
                "previous_close_carry_allowed": False,
                "authority": "current_valuation_same_day_refresh",
                "reason": "same_day_current_valuation_refresh_available",
            }
        if previous_trading_date and actual == previous_trading_date:
            return {
                "status": "READY",
                "expected_date": previous_trading_date,
                "expected_date_policy": "morning_previous_close_or_same_day",
                "same_day_allowed": True,
                "previous_close_carry_allowed": True,
                "authority": "current_valuation_previous_trading_day_close",
                "reason": "previous_trading_day_close_is_latest_available_at_morning_evaluation",
            }
        return {
            "status": "REVIEW_REQUIRED",
            "expected_date": previous_trading_date,
            "expected_date_policy": "morning_previous_close_or_same_day",
            "same_day_allowed": True,
            "previous_close_carry_allowed": False,
            "authority": "stale_current_valuation",
            "reason": "current_valuation_older_than_previous_trading_day",
        }
    if actual == business_date:
        return {
            "status": "READY",
            "expected_date": business_date,
            "expected_date_policy": "business_date_close",
            "same_day_allowed": True,
            "previous_close_carry_allowed": False,
            "authority": "current_valuation_business_date_close",
            "reason": "business_date_current_valuation_ready",
        }
    return {
        "status": "REVIEW_REQUIRED",
        "expected_date": business_date,
        "expected_date_policy": "business_date_close",
        "same_day_allowed": False,
        "previous_close_carry_allowed": False,
        "authority": "stale_current_valuation",
        "reason": "current_valuation_not_business_date_close",
    }


def _resolve_pm_input_paths_from_feature_contract(
    *,
    root: Path,
    feature_contract: dict[str, Any],
    feature_date: str,
    explicit_pm_feature_path: Path | str | None,
    explicit_pm_opportunity_path: Path | str | None,
) -> tuple[Path | str | None, Path | str | None]:
    generated = dict(feature_contract.get("generated_feature_artifacts") or {})
    pm_feature = explicit_pm_feature_path or generated.get("position_feature_input.parquet") or None
    pm_opportunity = (
        explicit_pm_opportunity_path
        or root / "runtime_state" / "buy_ai" / feature_date / "opportunity_rankings.json"
    )
    return pm_feature, pm_opportunity


def _market_readiness_payload(*, root: Path, business_date: str, market_open: bool, override: bool) -> dict[str, Any]:
    path = _resolve_market_evidence_path(root=root, business_date=business_date)
    payload, status, reason, _ = _read_json_object(path)
    if not market_open and not override:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "market_calendar_closed",
            "market_data_status": "NOT_REQUIRED",
            "quote_status": "NOT_REQUIRED",
            "quote_reason": "",
            "market_summary_status": "NOT_REQUIRED",
            "missing_evidence": [],
            "source_paths": {"market_evidence": str(path)},
        }
    if status != "READY":
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "market_evidence_missing",
            "market_data_status": "REVIEW_REQUIRED",
            "quote_status": "REVIEW_REQUIRED",
            "quote_reason": "market_evidence_missing",
            "market_summary_status": "REVIEW_REQUIRED",
            "missing_evidence": ["market_evidence"],
            "source_paths": {"market_evidence": str(path)},
        }
    runtime_date = str(payload.get("runtime_business_date") or payload.get("business_date") or "")
    market_date = str(payload.get("market_date") or payload.get("as_of") or runtime_date)
    if runtime_date and runtime_date != business_date:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "market_evidence_date_mismatch",
            "market_data_status": "REVIEW_REQUIRED",
            "quote_status": "REVIEW_REQUIRED",
            "quote_reason": "market_evidence_date_mismatch",
            "market_summary_status": "REVIEW_REQUIRED",
            "missing_evidence": [],
            "source_paths": {"market_evidence": str(path)},
        }
    market_status = str(payload.get("market_status") or payload.get("status") or "READY")
    quote_status = str(payload.get("quote_status") or "READY")
    if market_status in {"DATA_NOT_YET_AVAILABLE", "STALE", "REVIEW_REQUIRED", "HALT"}:
        return {
            "status": "REVIEW_REQUIRED" if market_status != "HALT" else "HALT",
            "reason": str(payload.get("temporal_evidence", {}).get("reason") or payload.get("reason") or market_status.lower()),
            "market_data_status": market_status,
            "quote_status": quote_status if quote_status != "READY" else market_status,
            "quote_reason": str(payload.get("reason") or market_status.lower()),
            "market_summary_status": "READY" if payload.get("market_summary") else "REVIEW_REQUIRED",
            "missing_evidence": [] if market_status in {"DATA_NOT_YET_AVAILABLE", "STALE"} else ["market_evidence"],
            "source_paths": {"market_evidence": str(path)},
            "market_date": market_date,
            "latest_expected_trading_date": payload.get("latest_expected_trading_date") or "",
            "latest_available_market_date": payload.get("latest_available_market_date") or "",
            "market_freshness_status": payload.get("market_freshness_status") or market_status,
        }
    summary_ready = bool(payload.get("market_summary") or payload.get("summary") or payload.get("quote_count"))
    ready_statuses = {"READY", "VALID_CARRYOVER"}
    effective_status = "READY" if market_status in ready_statuses and summary_ready else "REVIEW_REQUIRED"
    return {
        "status": effective_status,
        "reason": "market_evidence_ready" if summary_ready else "market_summary_missing",
        "market_data_status": market_status,
        "quote_status": quote_status,
        "quote_reason": "" if quote_status in {"READY", "NOT_REQUIRED"} else "quote_evidence_not_ready",
        "market_summary_status": "READY" if summary_ready else "REVIEW_REQUIRED",
        "missing_evidence": [] if summary_ready else ["market_summary"],
        "source_paths": {"market_evidence": str(path)},
        "market_date": market_date,
        "latest_expected_trading_date": payload.get("latest_expected_trading_date") or "",
        "latest_available_market_date": payload.get("latest_available_market_date") or "",
        "market_freshness_status": payload.get("market_freshness_status") or market_status,
    }


def _resolve_market_evidence_path(*, root: Path, business_date: str) -> Path:
    direct = root / "runtime_state" / "market" / business_date / "market_evidence.json"
    if direct.is_file():
        return direct
    latest = root / "runtime_state" / "market" / "latest.json"
    payload, status, _, _ = _read_json_object(latest)
    if status == "READY":
        candidate = Path(str(payload.get("artifact_path") or ""))
        if candidate.is_file():
            return candidate
    return direct


def _candidate_pre_inference_status(
    *,
    scope: str,
    candidate_model_path: Path | str | None,
    feature_payload: dict[str, Any],
) -> dict[str, Any]:
    source = str(candidate_model_path or "")
    if scope not in FULL_MORNING_SCOPES:
        return {"status": "NOT_REQUIRED", "reason": "", "missing_evidence": [], "source_paths": {"candidate_model": source}, "candidate_model_path": source, "candidate_model_status": "NOT_REQUIRED"}
    model = _model_artifact_status(path=Path(source), model_kind="candidate")
    missing: list[str] = []
    if model["status"] == "REVIEW_REQUIRED":
        missing.append("candidate_model")
    if model["status"] == "HALT":
        return {
            "status": "HALT",
            "reason": model["reason"],
            "missing_evidence": [],
            "source_paths": {"candidate_model": source},
            "candidate_model_path": source,
            "candidate_model_status": "HALT",
            "model_version": model["model_version"],
            "feature_columns_available": model["feature_columns_available"],
        }
    if feature_payload.get("candidate_schema_status") != "READY":
        missing.append("candidate_feature_schema")
    return {
        "status": "REVIEW_REQUIRED" if missing else "PRE_INFERENCE_READY",
        "reason": "candidate_pre_inference_not_ready" if missing else "candidate_pre_inference_ready",
        "missing_evidence": missing,
        "source_paths": {"candidate_model": source},
        "candidate_model_path": source,
        "candidate_model_status": model["status"],
        "model_version": model["model_version"],
        "feature_columns_available": model["feature_columns_available"],
    }


def _opportunity_pre_inference_status(
    *,
    scope: str,
    opportunity_model_path: Path | str | None,
    feature_payload: dict[str, Any],
) -> dict[str, Any]:
    source = str(opportunity_model_path or "")
    if scope not in FULL_MORNING_SCOPES:
        return {"status": "NOT_REQUIRED", "reason": "", "missing_evidence": [], "source_paths": {"opportunity_model": source}, "opportunity_model_path": source, "opportunity_model_status": "NOT_REQUIRED"}
    model = _model_artifact_status(path=Path(source), model_kind="opportunity")
    missing: list[str] = []
    if model["status"] == "REVIEW_REQUIRED":
        missing.append("opportunity_model")
    if model["status"] == "HALT":
        return {
            "status": "HALT",
            "reason": model["reason"],
            "missing_evidence": [],
            "source_paths": {"opportunity_model": source},
            "opportunity_model_path": source,
            "opportunity_model_status": "HALT",
            "model_version": model["model_version"],
            "feature_columns_available": model["feature_columns_available"],
        }
    if feature_payload.get("opportunity_schema_status") != "READY":
        missing.append("opportunity_feature_schema")
    return {
        "status": "REVIEW_REQUIRED" if missing else "PRE_INFERENCE_READY",
        "reason": "opportunity_pre_inference_not_ready" if missing else "opportunity_pre_inference_ready",
        "missing_evidence": missing,
        "source_paths": {"opportunity_model": source},
        "opportunity_model_path": source,
        "opportunity_model_status": model["status"],
        "model_version": model["model_version"],
        "feature_columns_available": model["feature_columns_available"],
    }


def _model_artifact_status(*, path: Path, model_kind: str) -> dict[str, Any]:
    if not str(path) or not path.is_file():
        return {
            "status": "REVIEW_REQUIRED",
            "reason": f"{model_kind}_model_artifact_missing",
            "model_version": "",
            "feature_columns_available": False,
        }
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except Exception as exc:
        return {
            "status": "HALT",
            "reason": f"{model_kind}_model_artifact_unreadable:{type(exc).__name__}",
            "model_version": "",
            "feature_columns_available": False,
        }
    if not isinstance(payload, dict):
        return {
            "status": "HALT",
            "reason": f"{model_kind}_model_artifact_invalid_payload",
            "model_version": "",
            "feature_columns_available": False,
        }
    if payload.get("model") is None:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": f"{model_kind}_model_object_missing",
            "model_version": str(payload.get("model_version") or "unknown"),
            "feature_columns_available": bool(payload.get("feature_columns")),
        }
    if not payload.get("feature_columns"):
        return {
            "status": "REVIEW_REQUIRED",
            "reason": f"{model_kind}_model_feature_columns_missing",
            "model_version": str(payload.get("model_version") or "unknown"),
            "feature_columns_available": False,
        }
    return {
        "status": "READY",
        "reason": f"{model_kind}_model_ready",
        "model_version": str(payload.get("model_version") or "unknown"),
        "feature_columns_available": True,
    }


def _pm_readiness_payload(
    *,
    scope: str,
    current: dict[str, Any],
    current_path: Path,
    runtime_state: dict[str, Any] | None,
    runtime_state_path: Path | None,
    business_date: str,
    feature_date: str,
    pm_opportunity_path: Path | str | None,
    pm_feature_path: Path | str | None,
) -> dict[str, Any]:
    if scope == REVIEW_ONLY_MORNING_SCOPE:
        feature_payload = _feature_readiness_payload(
            operations_root=current_path.parents[1] / "operations",
            feature_date=feature_date,
        )
        pm_status = str(feature_payload.get("pm_schema_status") or "")
        return {
            "status": "READY" if pm_status == "READY" else "REVIEW_REQUIRED",
            "reason": "pm_feature_consumer_ready_for_review_only"
            if pm_status == "READY"
            else "pm_feature_consumer_not_ready_for_review_only",
            "missing_evidence": [] if pm_status == "READY" else ["pm_feature"],
            "missing_fields": list(feature_payload.get("pm_missing_columns") or []),
            "stale_artifacts": [],
            "source_paths": {"pm_feature": str(feature_payload.get("readiness_artifact_path") or "")},
            "contract": {
                "pm_input_schema_status": pm_status or "REVIEW_REQUIRED",
                "pm_feature_date": feature_date,
                "pm_review_reason": "pm_feature_consumer_ready_for_review_only"
                if pm_status == "READY"
                else "pm_feature_consumer_not_ready_for_review_only",
            },
        }
    if scope != "sell_planning":
        return {"status": "NOT_REQUIRED", "reason": "", "missing_evidence": [], "missing_fields": [], "stale_artifacts": [], "source_paths": {}}
    contract = validate_position_management_input_contract(
        current=current,
        current_path=current_path,
        runtime_state=runtime_state,
        runtime_state_path=runtime_state_path,
        business_date=business_date,
        feature_date=feature_date,
        opportunity_path=pm_opportunity_path,
        feature_path=pm_feature_path,
    )
    missing_evidence = []
    if "pm_feature_source" in contract.get("pm_missing_fields", []):
        missing_evidence.append("pm_feature")
    if "pm_opportunity_source" in contract.get("pm_missing_fields", []):
        missing_evidence.append("pm_opportunity")
    return {
        "status": "READY" if contract.get("pm_input_schema_status") == "READY" else "REVIEW_REQUIRED",
        "reason": contract.get("pm_review_reason") or "pm_input_ready",
        "missing_evidence": missing_evidence,
        "missing_fields": list(contract.get("pm_missing_fields") or []),
        "stale_artifacts": list(contract.get("pm_stale_artifacts") or []),
        "source_paths": {
            "pm_feature": str(pm_feature_path or ""),
            "pm_opportunity": str(pm_opportunity_path or ""),
        },
        "contract": contract,
    }


def _broker_readiness_payload(*, root: Path, business_date: str, scope: str) -> dict[str, Any]:
    required = scope in {"sell_planning", "submit", "execution", REVIEW_ONLY_MORNING_SCOPE}
    candidates = _broker_snapshot_candidates(root=root, business_date=business_date)
    existing = [path for path in candidates if path.is_file()]
    if not required:
        if not existing:
            return {"status": "NOT_REQUIRED", "direct_status": "NOT_REQUIRED", "reason": "", "missing_evidence": [], "source_paths": {"broker_snapshot": ""}}
        payload, status, reason, path = _read_json_object(existing[0])
        if status != "READY":
            return {"status": "REVIEW_REQUIRED", "direct_status": "NOT_REQUIRED", "reason": reason, "missing_evidence": ["broker_snapshot"], "source_paths": {"broker_snapshot": str(path)}}
        broker_review_reason = _broker_contract_review_reason(payload)
        if broker_review_reason:
            return {
                "status": "REVIEW_REQUIRED",
                "direct_status": "NOT_REQUIRED",
                "reason": broker_review_reason,
                "missing_evidence": [],
                "source_paths": {"broker_snapshot": str(path)},
            }
        return {"status": "READY", "direct_status": "NOT_REQUIRED", "reason": "", "missing_evidence": [], "source_paths": {"broker_snapshot": str(path)}}
    if not existing:
        return {"status": "REVIEW_REQUIRED", "direct_status": "REVIEW_REQUIRED", "reason": "broker_readonly_snapshot_missing", "missing_evidence": ["broker_snapshot"], "source_paths": {}}
    payload, status, reason, path = _read_json_object(existing[0])
    if status != "READY":
        return {"status": "REVIEW_REQUIRED", "direct_status": "REVIEW_REQUIRED", "reason": reason, "missing_evidence": ["broker_snapshot"], "source_paths": {"broker_snapshot": str(path)}}
    broker_review_reason = _broker_contract_review_reason(payload)
    review_required = bool(payload.get("review_required")) or bool(broker_review_reason)
    return {
        "status": "REVIEW_REQUIRED" if review_required else "READY",
        "direct_status": "REVIEW_REQUIRED" if review_required else "READY",
        "reason": broker_review_reason or ("broker_snapshot_review_required" if review_required else "broker_snapshot_ready"),
        "missing_evidence": [],
        "source_paths": {"broker_snapshot": str(path)},
    }


def _broker_snapshot_candidates(*, root: Path, business_date: str) -> list[Path]:
    runtime_state_candidates = sorted(
        (root / "runtime_state" / "broker_readonly" / business_date).glob("*.json"),
        key=lambda path: path.stat().st_mtime if path.is_file() else 0,
        reverse=True,
    )
    legacy_candidates = sorted(
        (root / "broker" / "snapshots" / "positions").glob("*.json"),
        key=lambda path: path.stat().st_mtime if path.is_file() else 0,
        reverse=True,
    )
    return [*runtime_state_candidates, *legacy_candidates]


def _broker_contract_review_reason(payload: dict[str, Any]) -> str:
    authenticity = str(payload.get("authenticity_status") or "")
    alignment = str(payload.get("account_alignment_status") or "")
    if not authenticity and not alignment:
        return ""
    if authenticity and authenticity != "READY":
        return "broker_snapshot_authenticity_review_required"
    if alignment in {"MISMATCH", "UNKNOWN"}:
        return "broker_account_alignment_review_required"
    return ""


def _safety_readiness_payload(
    *,
    root: Path,
    business_date: str,
    mode: str,
    current_payload: dict[str, Any],
    pending_payload: dict[str, Any],
    runtime_test_run_id: str,
    runtime_test_profile_id: str,
    runtime_test_evidence_root: str,
    broker_write: bool,
    external_delivery: bool,
) -> dict[str, Any]:
    decision = load_runtime_safety_decision(runtime_root=root, business_date=business_date, mode=mode)
    source_paths = {"safety_decision": decision.artifact_path}
    missing = ["safety_decision"] if decision.safety_status == "SAFETY_MISSING" else []
    stale: list[str] = []
    if mode == "historical" and (
        decision.safety_status == "SAFETY_MISSING" or decision.business_date != business_date
    ):
        if (
            not broker_write
            and not external_delivery
            and _historical_initial_current_ready(current_payload)
            and _pending_payload_empty(pending_payload)
        ):
            return {
                "status": "READY",
                "reason": "historical_neutral_no_event_safety_ready",
                "missing_evidence": [],
                "stale_artifacts": [],
                "source_paths": {"safety_decision": ""},
                "ignored_latest_safety_decision": decision.artifact_path,
                "historical_safety_temporal_authority": "historical_initial_no_external_effect",
            }
        pending_authority = _historical_pending_safety_authority(
            pending_payload=pending_payload,
            business_date=business_date,
            runtime_test_run_id=runtime_test_run_id,
            runtime_test_profile_id=runtime_test_profile_id,
            runtime_test_evidence_root=runtime_test_evidence_root,
        )
        if (
            not broker_write
            and not external_delivery
            and pending_authority["status"] == "READY"
        ):
            return {
                "status": "READY",
                "reason": "historical_neutral_no_event_safety_ready",
                "missing_evidence": [],
                "stale_artifacts": [],
                "source_paths": {"safety_decision": str(pending_payload.get("source_paths", {}).get("pending") or "")},
                "ignored_latest_safety_decision": decision.artifact_path,
                "historical_safety_temporal_authority": "historical_initial_no_external_effect",
                "pending_safety_authority": pending_authority,
            }
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "historical_safety_temporal_authority_missing",
            "missing_evidence": ["historical_safety_temporal_authority"],
            "stale_artifacts": ["safety"] if decision.artifact_path else [],
            "source_paths": source_paths,
        }
    if decision.safety_status != "PASS":
        return {"status": "REVIEW_REQUIRED", "reason": decision.reason or decision.safety_status, "missing_evidence": missing, "stale_artifacts": stale, "source_paths": source_paths}
    if decision.business_date != business_date:
        return {"status": "REVIEW_REQUIRED", "reason": "safety_business_date_mismatch", "missing_evidence": [], "stale_artifacts": ["safety"], "source_paths": source_paths}
    if _date_part(decision.expires_at) and _date_part(decision.expires_at) < business_date:
        stale.append("safety")
        return {"status": "REVIEW_REQUIRED", "reason": "safety_expired", "missing_evidence": [], "stale_artifacts": stale, "source_paths": source_paths}
    if decision.halt_runtime or decision.emergency_stop or decision.decision == "HALT":
        return {"status": "HALT", "reason": decision.reason or "safety_halt", "missing_evidence": [], "stale_artifacts": [], "source_paths": source_paths}
    if decision.decision != "ALLOW" or decision.review_required or decision.block_buy or decision.block_sell or decision.block_submit:
        return {"status": "REVIEW_REQUIRED", "reason": decision.reason or "safety_not_allow", "missing_evidence": [], "stale_artifacts": [], "source_paths": source_paths}
    return {"status": "READY", "reason": "safety_allow", "missing_evidence": [], "stale_artifacts": [], "source_paths": source_paths}


def _safety_dependency_payload(*, safety_payload: dict[str, Any], broker_payload: dict[str, Any]) -> dict[str, Any]:
    reason = str(safety_payload.get("reason") or "")
    reason_upper = reason.upper()
    quote_reasons = []
    broker_reasons = []
    missing_evidence = []
    if "QUOTE_MISSING" in reason_upper or "QUOTE" in reason_upper and safety_payload.get("status") == "REVIEW_REQUIRED":
        quote_reasons.append("safety_requires_quote_evidence")
        missing_evidence.append("quote_evidence")
    if "BROKER_SNAPSHOT_MISSING" in reason_upper or "POSITION_WITHOUT_BROKER_SNAPSHOT" in reason_upper:
        broker_reasons.append("safety_requires_broker_snapshot")
        missing_evidence.append("broker_snapshot")
    broker_dependency_status = "REVIEW_REQUIRED" if broker_reasons else "READY"
    quote_status = "REVIEW_REQUIRED" if quote_reasons else "READY"
    if broker_payload.get("status") == "READY" and not broker_reasons:
        broker_dependency_status = "READY"
    return {
        "broker_dependency_status": broker_dependency_status,
        "broker_reasons": broker_reasons,
        "quote_status": quote_status,
        "quote_reasons": quote_reasons,
        "safety_market_input_status": _max_status(quote_status, broker_dependency_status),
        "missing_evidence": missing_evidence,
    }


def _review_only_morning_payload(
    *,
    root: Path,
    business_date: str,
    mode: str,
    feature_payload: dict[str, Any],
    broker_payload: dict[str, Any],
    safety_payload: dict[str, Any],
    now: datetime | None,
) -> dict[str, Any]:
    decision = load_runtime_safety_decision(runtime_root=root, business_date=business_date, mode=mode)
    permissions = {str(key): str(value).upper() for key, value in (decision.action_permissions or {}).items()}
    mismatched: list[str] = []
    for key, expected in EXPECTED_ACTION_SCOPE.items():
        if permissions.get(key) != expected:
            mismatched.append(f"action_permissions.{key}")
    feature_ready = bool(feature_payload.get("consumer_ready")) and str(feature_payload.get("pm_schema_status") or "") == "READY"
    if not feature_ready:
        mismatched.append("pm_feature_consumer_readiness")
    if broker_payload.get("status") != "READY":
        mismatched.append("broker_readonly")
    if safety_payload.get("status") != "REVIEW_REQUIRED" or str(safety_payload.get("reason") or "").upper() != HIGH_RISK_REVIEW_REASON:
        mismatched.append("safety_high_risk_review")
    validation = validate_human_review_artifact(
        runtime_root=root,
        business_date=business_date,
        issue_code=HIGH_RISK_REVIEW_ISSUE_CODE,
        now=now,
    )
    source_paths = {
        "human_review": validation.artifact_path,
        "safety_decision": decision.artifact_path,
    }
    if validation.status != "READY":
        mismatched.append("human_review_artifact")
        mismatched.extend(validation.mismatched_fields)
    if mismatched:
        return {
            "status": "REVIEW_REQUIRED",
            "reason": validation.reason if validation.status != "READY" else "review_only_scope_contract_mismatch",
            "artifact_path": validation.artifact_path,
            "missing_evidence": list(validation.missing_evidence),
            "stale_artifacts": list(validation.stale_artifacts),
            "mismatched_fields": _unique(mismatched),
            "source_paths": source_paths,
            "safety_action_permissions": permissions,
            "human_review_validation": validation.payload,
        }
    return {
        "status": "READY",
        "reason": "morning_sell_hold_review_only_ready",
        "artifact_path": validation.artifact_path,
        "missing_evidence": [],
        "stale_artifacts": [],
        "mismatched_fields": [],
        "source_paths": source_paths,
        "safety_action_permissions": permissions,
        "human_review_validation": validation.payload,
    }


def _pending_readiness_payload(
    *,
    root: Path,
    business_date: str,
    mode: str,
    runtime_test_run_id: str,
    runtime_test_profile_id: str,
    runtime_test_evidence_root: str,
) -> dict[str, Any]:
    path = root / "pending_order_plan" / "pending_order_plan.json"
    payload, status, reason, _ = _read_json_object(path)
    if status != "READY":
        return {"status": "REVIEW_REQUIRED", "reason": "pending_slot_missing", "missing_evidence": ["pending_slot"], "stale_artifacts": [], "mismatched_dates": [], "source_paths": {"pending": str(path)}, "slot_status": "MISSING", "active_pending": False}
    state = str(payload.get("state") or payload.get("status") or "").upper()
    active_pending = bool(payload.get("active_pending", state != "EMPTY"))
    pending_environment = str(payload.get("environment") or "")
    if pending_environment and pending_environment != mode and (active_pending or state != "EMPTY"):
        return {
            "status": "REVIEW_REQUIRED",
            "reason": "pending_environment_mismatch",
            "missing_evidence": [],
            "stale_artifacts": ["pending"],
            "mismatched_dates": [],
            "mismatched_fields": ["pending.environment"],
            "source_paths": {"pending": str(path)},
            "slot_status": state or "PRESENT",
            "active_pending": active_pending,
            "payload": payload,
        }
    safety_authority = _historical_pending_safety_authority(
        pending_payload={"payload": payload, "source_paths": {"pending": str(path)}, "slot_status": state, "active_pending": active_pending},
        business_date=business_date,
        runtime_test_run_id=runtime_test_run_id,
        runtime_test_profile_id=runtime_test_profile_id,
        runtime_test_evidence_root=runtime_test_evidence_root,
    )
    if state == "EMPTY" and not active_pending:
        return {"status": "READY", "reason": "pending_slot_empty", "missing_evidence": [], "stale_artifacts": [], "mismatched_dates": [], "source_paths": {"pending": str(path)}, "slot_status": "EMPTY", "active_pending": False, "payload": payload, "historical_pending_safety_authority": safety_authority}
    target_date = str(payload.get("target_session_date") or "")
    approval = payload.get("approval") or {}
    consumed = bool((payload.get("consume") or {}).get("consumed")) or state == "CONSUMED"
    if state == "REVIEW_REQUIRED":
        return {"status": "REVIEW_REQUIRED", "reason": str(payload.get("review_reason") or "pending_review_required"), "missing_evidence": [], "stale_artifacts": [], "mismatched_dates": [], "source_paths": {"pending": str(path)}, "slot_status": state, "active_pending": active_pending}
    if state == "APPROVED" and target_date and target_date != business_date:
        return {"status": "REVIEW_REQUIRED", "reason": "stale_approved_pending_exists", "missing_evidence": [], "stale_artifacts": ["pending"], "mismatched_dates": ["pending.target_session_date"], "source_paths": {"pending": str(path)}, "slot_status": state, "active_pending": active_pending}
    if state == "APPROVED" and not consumed and (not payload.get("pending_policy_hash") and not approval.get("pending_policy_hash")):
        return {"status": "REVIEW_REQUIRED", "reason": "pending_policy_hash_missing", "missing_evidence": ["pending_policy_hash"], "stale_artifacts": [], "mismatched_dates": [], "source_paths": {"pending": str(path)}, "slot_status": state, "active_pending": active_pending}
    if state == "APPROVED" and not consumed and (not payload.get("safety_decision_id") and not approval.get("safety_decision_id")):
        if mode == "historical" and safety_authority["status"] == "READY":
            return {
                "status": "READY",
                "reason": "pending_lifecycle_ready",
                "missing_evidence": [],
                "stale_artifacts": [],
                "mismatched_dates": [],
                "source_paths": {"pending": str(path)},
                "slot_status": state,
                "active_pending": active_pending,
                "payload": payload,
                "historical_pending_safety_authority": safety_authority,
            }
        return {"status": "REVIEW_REQUIRED", "reason": "pending_safety_evidence_missing", "missing_evidence": ["pending_safety_evidence"], "stale_artifacts": [], "mismatched_dates": [], "source_paths": {"pending": str(path)}, "slot_status": state, "active_pending": active_pending, "payload": payload, "historical_pending_safety_authority": safety_authority}
    return {"status": "READY", "reason": "pending_lifecycle_ready", "missing_evidence": [], "stale_artifacts": [], "mismatched_dates": [], "source_paths": {"pending": str(path)}, "slot_status": state or "PRESENT", "active_pending": active_pending, "payload": payload, "historical_pending_safety_authority": safety_authority}


def _historical_pending_safety_authority(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
    runtime_test_run_id: str,
    runtime_test_profile_id: str,
    runtime_test_evidence_root: str,
) -> dict[str, Any]:
    payload = dict(pending_payload.get("payload") or {})
    safety_context = dict(payload.get("safety_context") or {})
    approval = dict(payload.get("approval") or {})
    state = str(pending_payload.get("slot_status") or payload.get("state") or payload.get("status") or "").upper()
    active_pending = bool(pending_payload.get("active_pending", payload.get("active_pending", state != "EMPTY")))
    consumed = bool((payload.get("consume") or {}).get("consumed")) or state == "CONSUMED"
    target_session_date = str(payload.get("target_session_date") or "")
    no_action_terminal = bool(state == "EMPTY" and not active_pending and not (payload.get("items") or ()))
    consumed_prior_session = bool(consumed and target_session_date and target_session_date < business_date)
    expected_safety_business_date = target_session_date if consumed_prior_session else business_date
    mismatched: list[str] = []
    if state not in {"APPROVED", "CONSUMED"} and not consumed and not no_action_terminal:
        mismatched.append("pending_lifecycle_state")
    expected = {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision": "ALLOW",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_business_date": expected_safety_business_date,
    }
    if runtime_test_run_id or safety_context.get("runtime_test_run_id"):
        expected["runtime_test_run_id"] = runtime_test_run_id
    if runtime_test_profile_id or safety_context.get("runtime_test_profile_id"):
        expected["runtime_test_profile_id"] = runtime_test_profile_id
    if runtime_test_evidence_root or safety_context.get("runtime_test_evidence_root"):
        expected["runtime_test_evidence_root"] = runtime_test_evidence_root
    for field, expected_value in expected.items():
        actual = str(safety_context.get(field) or "")
        if actual != str(expected_value):
            mismatched.append(f"safety_context.{field}")
    if not consumed_prior_session and target_session_date != business_date:
        mismatched.append("target_session_date")
    if consumed_prior_session and target_session_date > business_date:
        mismatched.append("target_session_date")
    if str(payload.get("environment") or "") != "historical":
        mismatched.append("environment")
    explicit_safety_id_present = bool(payload.get("safety_decision_id") or approval.get("safety_decision_id"))
    if explicit_safety_id_present and not mismatched:
        return {
            "status": "READY",
            "reason": "explicit_safety_decision_id_present",
            "mismatched_fields": [],
            "authority": str(safety_context.get("safety_authority") or ""),
        }
    status = "READY" if not mismatched else "REVIEW_REQUIRED"
    return {
        "status": status,
        "reason": "historical_consumed_pending_safety_authority_carry_forward"
        if status == "READY" and consumed_prior_session
        else "historical_no_action_pending_safety_authority_ready"
        if status == "READY" and no_action_terminal
        else "historical_pending_safety_authority_ready"
        if status == "READY"
        else "historical_pending_safety_authority_mismatch",
        "mismatched_fields": sorted(set(mismatched)),
        "authority": str(safety_context.get("safety_authority") or ""),
        "pending_lifecycle_state": state,
        "pending_consumed": consumed,
        "no_action_terminal": no_action_terminal,
        "target_session_date": target_session_date,
        "safety_business_date_expected": expected_safety_business_date,
        "consumed_prior_session_carry_forward": consumed_prior_session,
        "safety_context": safety_context,
    }


def _environment_readiness_payload(
    *,
    mode: str,
    broker_environment: str,
    notification_mode: str,
    override: bool,
    allow_override: bool,
    broker_write: bool,
    external_delivery: bool,
) -> dict[str, Any]:
    if mode == "production" and allow_override:
        return {"status": "HALT", "reason": "non_trading_day_demo_override_forbidden_in_production"}
    if mode == "production":
        if broker_environment not in {"tachibana_production", "production"}:
            return {"status": "HALT", "reason": "production_broker_environment_required"}
        if notification_mode != "payload-only" and not external_delivery:
            return {"status": "HALT", "reason": "notification_mode_inconsistent"}
        return {
            "status": "READY",
            "reason": "production_runtime_environment_ready",
            "non_trading_day_demo_override": override,
            "acceptance_scope": "production_operation",
            "production_equivalent": True,
            "broker_write": bool(broker_write),
            "external_delivery": bool(external_delivery),
        }
    if mode == "historical":
        if broker_environment != "historical_simulated":
            return {"status": "HALT", "reason": "historical_broker_environment_required"}
        if broker_write or external_delivery:
            return {"status": "HALT", "reason": "historical_external_effect_forbidden"}
        if notification_mode != "payload-only":
            return {"status": "HALT", "reason": "notification_real_send_not_allowed"}
        return {
            "status": "READY",
            "reason": "historical_replay_environment_ready",
            "non_trading_day_demo_override": override,
            "acceptance_scope": "historical_replay",
            "historical_replay": True,
            "broker_write": False,
            "external_delivery": False,
        }
    if mode != "demo":
        return {"status": "HALT", "reason": "runtime_acceptance_requires_demo_mode"}
    if notification_mode != "payload-only":
        return {"status": "HALT", "reason": "notification_real_send_not_allowed"}
    return {"status": "READY", "reason": "runtime_environment_ready", "non_trading_day_demo_override": override}


def _historical_initial_current_ready(current_payload: dict[str, Any]) -> bool:
    if not current_payload:
        return False
    if bool(current_payload.get("review_required")):
        return False
    if bool(current_payload.get("current_positions_unknown")):
        return False
    positions = current_payload.get("positions") or []
    if positions:
        return False
    return bool(current_payload.get("current_state_confirmed_empty", True))


def _pending_payload_empty(pending_payload: dict[str, Any]) -> bool:
    if not pending_payload:
        return False
    slot_status = str(pending_payload.get("slot_status") or pending_payload.get("state") or "").upper()
    if slot_status == "CONSUMED":
        return True
    return not bool(pending_payload.get("active_pending")) and slot_status in {"EMPTY", "CONSUMED", "NOT_REQUIRED", "READY"}


def _acceptance_scope_for_mode(mode: str) -> str:
    if mode == "production":
        return "production_operation"
    if mode == "historical":
        return "historical_replay"
    return "demo_acceptance_only"


def _read_json_object(path: Path, *, corrupt_status: str = "REVIEW_REQUIRED") -> tuple[dict[str, Any], str, str, Path]:
    if not path.is_file():
        return {}, "MISSING", f"{path.name} missing", path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, corrupt_status, f"{path.name} invalid json: {exc.msg}", path
    if not isinstance(payload, dict):
        return {}, corrupt_status, f"{path.name} must be a JSON object", path
    return payload, "READY", "", path


def _scope_requires_feature(scope: str) -> bool:
    return scope in {*FULL_MORNING_SCOPES, REVIEW_ONLY_MORNING_SCOPE}


def _next_operator_action(status: str, review_reasons: list[str], halt_reasons: list[str]) -> str:
    if status == "HALT":
        return "Stop Runtime and inspect: " + ", ".join(_unique(halt_reasons))
    if status == "REVIEW_REQUIRED":
        if "stale_approved_pending_exists" in review_reasons:
            return "run pending_lifecycle"
        if "possible_unknown_submit_outcome" in review_reasons:
            return "review broker/submit evidence"
        return "Refresh or inspect evidence: " + ", ".join(_unique(review_reasons))
    return "Proceed to requested Runtime step."


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _unique(values: list[str]) -> list[str]:
    return sorted({str(value) for value in values if str(value)})


def _max_status(*statuses: str) -> str:
    precedence = {
        "HALT": 9,
        "REVIEW_REQUIRED": 8,
        "EXPIRED": 7,
        "STALE": 6,
        "DATE_MISMATCH": 5,
        "MISSING": 4,
        "DATA_NOT_YET_AVAILABLE": 3,
        "VALID_CARRYOVER": 2,
        "READY": 1,
        "NOT_REQUIRED": 0,
        "": -1,
    }
    normalized = [str(status or "").upper() for status in statuses]
    return max(normalized, key=lambda status: precedence.get(status, 0)) if normalized else ""


def _previous_calendar_day(value: str) -> str:
    return (date.fromisoformat(value) - date.resolution).isoformat()


def _date_part(value: str) -> str:
    if not value:
        return ""
    return value[:10]


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
