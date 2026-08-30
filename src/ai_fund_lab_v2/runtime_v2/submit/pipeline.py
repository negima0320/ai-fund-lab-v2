"""Runtime v2 submit pipeline for the regular submit job."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from ai_fund_lab_v2.broker.issue_code_normalizer import (
    BrokerIssueCodeNormalizationError,
    normalize_broker_issue_code,
)
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.corporate_action_adjustment import (
    evaluate_corporate_action_adjustment_authority,
    materialize_corporate_action_adjustment_authority,
)
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import evaluate_opportunity_buy_eligibility
from ai_fund_lab_v2.runtime_v2.historical_support.corporate_action_quarantine import (
    quarantine_fields,
    registry_path as corporate_action_quarantine_registry_path,
    unresolved_entry as unresolved_corporate_action_quarantine_entry,
)
from ai_fund_lab_v2.runtime_v2.guard_taxonomy import normalize_review_result
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerOrderRecord
from ai_fund_lab_v2.runtime_v2.ledger.writer import ledger_record_to_payload
from ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility import evaluate_buy_eligibility
from ai_fund_lab_v2.runtime_v2.pending.consume import consume_pending_plan
from ai_fund_lab_v2.runtime_v2.pending.models import PendingConsumeInfo, PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.composition import is_buy_item_scoped_review_sell_continuation_pending
from ai_fund_lab_v2.runtime_v2.pending.no_order_authority import validate_materialized_no_order_authority
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    build_pending_review_scope_authority,
    pending_scope_allows_partial_submit,
    pending_scope_no_submission_terminal_authority,
)
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    CapitalDeploymentPolicy,
    CapitalDeploymentPolicyError,
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
    missing_policy_manifest_fields,
)
from ai_fund_lab_v2.runtime_v2.provenance import pending_item_provenance
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    HistoricalSubmitAdapter,
    historical_corporate_action_event_evidence,
)
from ai_fund_lab_v2.runtime_v2.safety_decision import (
    RuntimeSafetyDecision,
    load_runtime_safety_decision,
    safety_allows_action,
)
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import (
    is_mode_rooted_runtime_root,
    reject_mode_rooted_runtime_root,
)
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    RuntimeCurrentExposure,
    evaluate_buy_item_submit_feasibility,
    evaluate_planning_submit_feasibility,
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.submit.models import (
    RuntimeV2SubmitCommand,
    RuntimeV2SubmitResult,
    SubmitEnvironmentGuardContext,
)

DEMO_BASE_URL = "https://demo-kabuka.e-shiten.jp/e_api_v4r9"
PROD_BASE_URL = "https://kabuka.e-shiten.jp/e_api_v4r9"
EXECUTION_AUTHORITY_UNAVAILABLE_REASON = "EXECUTION_AUTHORITY_UNAVAILABLE"
EXECUTION_AUTHORITY_UNAVAILABLE_FEASIBILITY_STATUS = "NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE"
NOT_EXECUTABLE_ITEM_STATE = "NOT_EXECUTABLE"


class RuntimeV2SubmitAdapter(Protocol):
    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...


@dataclass(frozen=True)
class BrokerAvailableQuantityEvidence:
    checked: bool
    source: str
    quantity: float | None = None
    symbol: str = ""
    issue_code: str = ""
    snapshot_path: str = ""
    snapshot_at: str = ""
    review_required: bool = True
    production_equivalent: bool = False
    total_quantity: float | None = None
    restricted_quantity: float | None = None
    account_type: str = ""
    reason: str = ""


@dataclass(frozen=True)
class SubmitItemResult:
    pending_item_id: str
    symbol: str
    side: str
    quantity: float
    preflight_status: str
    submit_status: str
    submitted: bool
    accepted: bool
    rejected: bool
    unknown: bool
    blocked: bool
    review_required: bool
    broker_order_id_hash: str
    ledger_order_record_id: str
    reason: str
    issue_code_normalization: dict[str, Any]
    response_classification: dict[str, Any]
    configuration_diagnostic: dict[str, Any]
    next_action: str
    guard_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExistingSubmittedItemRecord:
    pending_item_id: str
    symbol: str
    side: str
    quantity: float
    order_id: str
    ledger_order_record_id: str
    source: str
    evidence_path: str = ""


@dataclass(frozen=True)
class SubmitPipelineResult:
    status: str
    reason: str
    pending_plan_id: str
    pending_path: str
    orders_ledger_path: str
    demo_submit_executed: bool
    submitted_count: int
    accepted_count: int
    rejected_count: int
    unknown_count: int
    blocked_count: int
    pending_consumed: bool
    submitted_order_ids: tuple[str, ...]
    ledger_order_record_ids: tuple[str, ...]
    submitted_symbols: tuple[str, ...]
    item_results: tuple[SubmitItemResult, ...]
    pending_read_valid: bool = False
    pending_classification: str = ""
    pending_active: bool | None = None
    pending_plan_present: bool = False
    pending_item_count: int = 0
    no_action_reason: str = ""
    no_order_authority_status: str = ""
    no_order_authority_reason: str = ""
    no_order_authority_evidence: dict[str, Any] = field(default_factory=dict)
    submit_action: str = "UNKNOWN"
    review_required: bool = False
    halt_required: bool = False
    raw_request_saved: bool = False
    raw_response_saved: bool = False
    secret_saved: bool = False
    submit_guard_policy: dict[str, Any] = field(default_factory=dict)
    submit_policy_consistency: dict[str, Any] = field(default_factory=dict)
    submit_guard_item_evidence: tuple[dict[str, Any], ...] = ()

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["item_results"] = [asdict(item) for item in self.item_results]
        payload["submitted_order_ids"] = list(self.submitted_order_ids)
        payload["ledger_order_record_ids"] = list(self.ledger_order_record_ids)
        payload["submitted_symbols"] = list(self.submitted_symbols)
        payload["submit_guard_item_evidence"] = list(self.submit_guard_item_evidence)
        return payload


def run_submit_pipeline(
    *,
    runtime_root: Path | str,
    business_date: str,
    mode: str,
    submit_enabled: bool,
    job: str,
    settings: Any | None = None,
    adapter: RuntimeV2SubmitAdapter | None = None,
    environment_context: SubmitEnvironmentGuardContext | None = None,
    capital_deployment_policy_path: Path | str | None = None,
    capital_deployment_policy: CapitalDeploymentPolicy | None = None,
    safety_decision: RuntimeSafetyDecision | None = None,
    now: datetime | None = None,
) -> SubmitPipelineResult:
    """Submit all approved Pending items through the Runtime v2 submit path."""

    runtime_root_path = Path(runtime_root)
    timestamp = _iso(now)
    try:
        _reject_mode_rooted_runtime_root(runtime_root_path)
    except ValueError as exc:
        return _blocked_result(reason=str(exc), runtime_root=runtime_root_path, status="HALT")
    if job != "submit" or not submit_enabled:
        return _blocked_result(
            reason="submit-enabled true is required and allowed only for submit job",
            runtime_root=runtime_root_path,
        )
    if mode == "historical":
        if not isinstance(adapter, HistoricalSubmitAdapter):
            return _blocked_result(
                reason="historical submit requires HistoricalSubmitAdapter from environment composition",
                runtime_root=runtime_root_path,
                status="HALT",
            )
    elif mode != "demo":
        return _blocked_result(reason="production submit is prohibited in Phase14-E17", runtime_root=runtime_root_path)
    policy, policy_manifest, policy_error = _resolve_capital_deployment_policy(
        capital_deployment_policy=capital_deployment_policy,
        capital_deployment_policy_path=capital_deployment_policy_path,
    )
    if policy is None:
        return _blocked_result(
            reason=policy_error or "capital deployment policy missing",
            runtime_root=runtime_root_path,
            status="REVIEW_REQUIRED",
            submit_guard_policy=policy_manifest,
        )

    if mode == "historical":
        settings_environment = "historical"
        base_url_is_demo = False
        base_url_is_production = False
    else:
        settings = settings or _load_broker_settings()
        settings_environment = settings.environment
        base_url = settings.base_url.rstrip("/")
        base_url_is_demo = base_url == DEMO_BASE_URL
        base_url_is_production = base_url == PROD_BASE_URL
    pending_read = read_pending_order_plan_path(
        path=runtime_root_path / "pending_order_plan" / "pending_order_plan.json",
        environment=mode,
    )
    if not pending_read.valid:
        return _blocked_result(
            reason="pending current is missing or invalid: " + ",".join(pending_read.errors),
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
            pending_read_valid=pending_read.valid,
            pending_classification=pending_read.classification,
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            pending_plan_present=pending_read.plan is not None,
            pending_item_count=_payload_item_count(pending_read.payload),
            no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
        )
    if pending_read.classification == "EMPTY":
        empty_reason = _validate_empty_pending_payload(
            pending_read.payload,
            business_date=business_date,
            environment=mode,
            runtime_root=runtime_root_path,
        )
        if empty_reason:
            return _blocked_result(
                reason=empty_reason,
                runtime_root=runtime_root_path,
                pending_path=str(pending_read.path),
                pending_read_valid=pending_read.valid,
                pending_classification=pending_read.classification,
                pending_active=_payload_bool(pending_read.payload, "active_pending"),
                pending_plan_present=pending_read.plan is not None,
                pending_item_count=_payload_item_count(pending_read.payload),
                no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
                status="REVIEW_REQUIRED",
            )
        return _empty_pending_result(
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
            payload=pending_read.payload,
        )
    if pending_read.plan is None:
        return _blocked_result(
            reason="pending current is missing or invalid: active pending plan missing",
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
            pending_read_valid=pending_read.valid,
            pending_classification=pending_read.classification,
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            pending_plan_present=False,
            pending_item_count=_payload_item_count(pending_read.payload),
            no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
        )
    pending = pending_read.plan
    if pending.state == PendingPlanState.EMPTY:
        no_order_reason, no_order_evidence = _validate_authorized_no_order(
            pending=pending,
            runtime_root=runtime_root_path,
            business_date=business_date,
            environment=mode,
        )
        if no_order_reason:
            return _blocked_result(
                reason=no_order_reason,
                runtime_root=runtime_root_path,
                pending_path=str(pending_read.path),
                status="REVIEW_REQUIRED",
                pending_read_valid=pending_read.valid,
                pending_classification=pending_read.classification,
                pending_active=_payload_bool(pending_read.payload, "active_pending"),
                pending_plan_present=True,
                pending_item_count=len(pending.items),
                no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
                no_order_authority_status="REVIEW_REQUIRED",
                no_order_authority_reason=no_order_reason,
                no_order_authority_evidence=no_order_evidence,
            )
        return _authorized_no_order_result(
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
            pending=pending,
            evidence=no_order_evidence,
            pending_read_valid=pending_read.valid,
            pending_classification=pending_read.classification,
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
        )
    if _is_buy_item_scoped_review_no_submission_pending(pending, business_date=business_date):
        return _buy_item_scoped_review_no_submission_result(
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
            pending=pending,
            pending_read_valid=pending_read.valid,
            pending_classification=pending_read.classification,
            pending_active=_payload_bool(pending_read.payload, "active_pending"),
            no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
        )
    guard_reason = _pending_submit_guard(pending, business_date=business_date)
    if guard_reason:
        return _blocked_result(reason=guard_reason, runtime_root=runtime_root_path, pending_path=str(pending_read.path))

    approval = _approval_from_pending(pending)
    policy_consistency = _policy_consistency_evidence(
        pending=pending,
        approval=approval,
        active_policy=policy,
    )
    if policy_consistency["policy_consistency_status"] != "PASS":
        return _blocked_result(
            reason=str(policy_consistency["policy_mismatch_reason"]),
            runtime_root=runtime_root_path,
            pending_path=str(pending_read.path),
            status="REVIEW_REQUIRED",
            submit_guard_policy=_submit_guard_policy_manifest(policy),
            submit_policy_consistency=policy_consistency,
        )
    existing_dedup_keys = _existing_order_dedup_keys(runtime_root_path / "persistent_ledger" / "orders.jsonl")
    current_state = _current_state_summary(
        runtime_root_path / "persistent_ledger" / "state.json",
        business_date=business_date,
    )
    current_positions = dict(current_state["positions"])
    broker_available_positions = _load_broker_available_quantity_snapshot(runtime_root_path)
    runtime_safety_decision = safety_decision or load_runtime_safety_decision(
        runtime_root=runtime_root_path,
        business_date=business_date,
        mode=mode,
    )
    submit_adapter = adapter if mode == "historical" else adapter or _build_tachibana_demo_submit_adapter(settings)
    guard_context = environment_context or _default_environment_context(
        mode=mode,
        pending_environment=mode,
        adapter=submit_adapter,
        broker_write=mode == "demo",
        business_date=business_date,
        now=timestamp,
    )
    item_results: list[SubmitItemResult] = []
    ledger_records: list[LedgerOrderRecord] = []
    item_scoped_review_evidence = _buy_item_scoped_review_partial_submission_evidence(pending)
    item_scoped_partial_submit = bool(item_scoped_review_evidence)
    existing_submitted_items = _existing_submitted_item_records(
        runtime_root_path,
        pending=pending,
        business_date=business_date,
    )
    reviewed_item_results = _reviewed_buy_item_results(pending, item_scoped_review_evidence=item_scoped_review_evidence)
    approved_items = tuple(
        item
        for approved_item_id in pending.approved_item_ids
        for item in pending.items
        if item.pending_item_id == approved_item_id
    )
    aggregate_feasibility = evaluate_planning_submit_feasibility(
        items=approved_items,
        policy=policy,
        current=RuntimeCurrentExposure(
            cash=current_state["cash"],
            buying_power=current_state["buying_power"],
            current_exposure=float(current_state["current_exposure"]),
            current_total_equity=current_state.get("current_total_equity"),
            active_deployment_capital=current_state.get("active_deployment_capital"),
            selected_capital_source=str(current_state.get("selected_capital_source") or "current_state.total_equity"),
            capital_fallback_used=bool(current_state.get("capital_fallback_used", False)),
            initial_or_bootstrap_capital=current_state.get("initial_or_bootstrap_capital"),
            positions=dict(current_state["positions"]),
            position_market_values=dict(current_state.get("position_market_values") or {}),
            current_position_source=str(current_state["current_position_source"]),
        ),
        authority_source="submit_guard_canonical_evidence_revalidation",
        business_date=business_date,
        runtime_mode=mode,
    )
    aggregate_by_item_id = {
        str(item.get("pending_item_id") or ""): item
        for item in aggregate_feasibility.evidence.get("items") or ()
        if isinstance(item, dict)
    }
    for approved_item_id in pending.approved_item_ids:
        item = next(item for item in pending.items if item.pending_item_id == approved_item_id)
        existing_submitted = existing_submitted_items.get(item.pending_item_id)
        if existing_submitted is not None:
            item_results.append(
                SubmitItemResult(
                    pending_item_id=item.pending_item_id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    preflight_status="RECONCILED",
                    submit_status="ACCEPTED",
                    submitted=True,
                    accepted=True,
                    rejected=False,
                    unknown=False,
                    blocked=False,
                    review_required=False,
                    broker_order_id_hash=existing_submitted.order_id,
                    ledger_order_record_id=existing_submitted.ledger_order_record_id,
                    reason="existing_item_submission_reconciled",
                    issue_code_normalization={},
                    response_classification={
                        "business_classification": "EXISTING_ITEM_SUBMISSION_RECONCILED",
                        "source": existing_submitted.source,
                        "evidence_path": existing_submitted.evidence_path,
                    },
                    configuration_diagnostic={},
                    next_action="no_resubmit_for_reconciled_item",
                    guard_evidence={
                        "authority_type": "PENDING_ITEM_EXISTING_SUBMISSION_RECONCILIATION",
                        "status": "PASS",
                        "idempotency_authority": "pending_item_existing_submission_reconciliation",
                        "idempotency_status": "PASS_RECONCILED_EXISTING_SUBMISSION",
                        "reconciliation_precedes_revalidation": True,
                        "skipped_sell_available_quantity_guard": item.side.upper() == "SELL",
                        "skipped_broker_preflight": True,
                        "skipped_adapter_submit": True,
                        "existing_order_id": existing_submitted.order_id,
                        "existing_ledger_order_record_id": existing_submitted.ledger_order_record_id,
                        "existing_submission_source": existing_submitted.source,
                        "existing_submission_evidence_path": existing_submitted.evidence_path,
                        "pending_plan_id": pending.pending_plan_id,
                        "pending_item_id": item.pending_item_id,
                        "symbol": item.symbol,
                        "side": item.side,
                        "quantity": item.quantity,
                        "guard_decision": "PASS",
                        "guard_reason": "existing_item_submission_reconciled_before_revalidation",
                        "manual_review_required": False,
                    },
                )
            )
            continue
        sell_position_quantity = current_positions.get(str(item.symbol).strip()) if item.side == "SELL" else None
        broker_available_evidence = (
            _broker_available_quantity_evidence(item=item, snapshot=broker_available_positions)
            if item.side == "SELL" and mode != "historical"
            else _historical_available_quantity_evidence(
                runtime_root=runtime_root_path,
                item=item,
                current_quantity=sell_position_quantity,
            )
            if item.side == "SELL"
            else BrokerAvailableQuantityEvidence(checked=False, source="")
        )
        corporate_action_event_evidence = _materialize_corporate_action_authority_for_item(
            runtime_root=runtime_root_path,
            business_date=business_date,
            mode=mode,
            adapter=submit_adapter,
            item=item,
            current_quantity=sell_position_quantity,
            broker_available_quantity=broker_available_evidence.quantity,
        )
        guard_evidence = _submit_guard_item_evidence(
            item=item,
            pending_plan=pending,
            runtime_root=runtime_root_path,
            business_date=business_date,
            mode=mode,
            policy=policy,
            current_state=current_state,
            broker_position_quantity=sell_position_quantity,
            broker_available_quantity=broker_available_evidence.quantity,
            broker_available_quantity_evidence=broker_available_evidence,
            safety_decision=runtime_safety_decision,
            feasibility_evidence=aggregate_by_item_id.get(item.pending_item_id),
            corporate_action_event_evidence=corporate_action_event_evidence,
        )
        guard_evidence["aggregate_submit_feasibility"] = aggregate_feasibility.evidence
        aggregate_item = aggregate_by_item_id.get(item.pending_item_id) or {}
        if str(aggregate_item.get("status") or "") != "PASS":
            guard_evidence = _blocked_guard_evidence(
                evidence=guard_evidence,
                reason=str(aggregate_item.get("reason") or aggregate_feasibility.reason),
                violated_policy=str(aggregate_item.get("violated_policy") or "aggregate_submit_feasibility"),
                violated_policy_source=str(
                    aggregate_item.get("violated_policy_source") or "submit_guard_canonical_evidence_revalidation"
                ),
                should_have_been_blocked_at_planning=True,
            )
        if guard_evidence["guard_decision"] == "BLOCKED":
            item_results.append(
                SubmitItemResult(
                    pending_item_id=item.pending_item_id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    preflight_status="BLOCKED",
                    submit_status="NOT_SUBMITTED",
                    submitted=False,
                    accepted=False,
                    rejected=False,
                    unknown=False,
                    blocked=True,
                    review_required=bool(guard_evidence["manual_review_required"]),
                    broker_order_id_hash="",
                    ledger_order_record_id="",
                    reason=str(guard_evidence["guard_reason"]),
                    issue_code_normalization={},
                    response_classification={},
                    configuration_diagnostic={},
                    next_action="",
                    guard_evidence=guard_evidence,
                )
            )
            continue
        preflight_dedup_keys = set(existing_dedup_keys)
        if item_scoped_partial_submit:
            preflight_dedup_keys.discard(pending.pending_plan_id)
        preflight = run_submit_preflight(
            pending_plan=pending,
            approval_artifact=approval,
            approved_item_id=approved_item_id,
            existing_order_dedup_keys=preflight_dedup_keys,
            environment=settings_environment,
            base_url_is_demo=base_url_is_demo,
            base_url_is_production=base_url_is_production,
            live_order_allowed=True,
            broker_position_quantity=sell_position_quantity,
            broker_available_quantity=broker_available_evidence.quantity,
            source_current_path="pending_order_plan/pending_order_plan.json",
            broker_capability=get_broker_capability(mode),
            environment_context=guard_context,
        )
        if not preflight.allowed or preflight.command is None:
            guard_evidence = {
                **guard_evidence,
                "guard_decision": "BLOCKED",
                "guard_reason": preflight.reason,
                "blocked_at_submit_reason": preflight.reason,
                "violated_policy": guard_evidence.get("violated_policy") or "submit_preflight",
                "violated_policy_source": guard_evidence.get("violated_policy_source") or "runtime_v2_submit_preflight",
            }
            item_results.append(
                SubmitItemResult(
                    pending_item_id=item.pending_item_id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    preflight_status="BLOCKED",
                    submit_status="NOT_SUBMITTED",
                    submitted=False,
                    accepted=False,
                    rejected=False,
                    unknown=False,
                    blocked=True,
                    review_required=False,
                    broker_order_id_hash="",
                    ledger_order_record_id="",
                    reason=preflight.reason,
                    issue_code_normalization={},
                    response_classification={},
                    configuration_diagnostic={},
                    next_action="",
                    guard_evidence=guard_evidence,
                )
            )
            continue
        adapter_preflight = submit_adapter.preflight(preflight.command)
        if adapter_preflight.blocked or adapter_preflight.status not in {"DRY_RUN_READY", "ACCEPTED"}:
            if _is_execution_authority_unavailable_preflight_result(adapter_preflight):
                terminal_evidence = _execution_authority_unavailable_terminal_evidence(
                    item=item,
                    pending=pending,
                    adapter_preflight=adapter_preflight,
                    guard_evidence=guard_evidence,
                )
                item_results.append(
                    SubmitItemResult(
                        pending_item_id=item.pending_item_id,
                        symbol=item.symbol,
                        side=item.side,
                        quantity=item.quantity,
                        preflight_status=NOT_EXECUTABLE_ITEM_STATE,
                        submit_status="NOT_SUBMITTED",
                        submitted=False,
                        accepted=False,
                        rejected=False,
                        unknown=False,
                        blocked=False,
                        review_required=False,
                        broker_order_id_hash="",
                        ledger_order_record_id="",
                        reason=EXECUTION_AUTHORITY_UNAVAILABLE_REASON,
                        issue_code_normalization=dict(adapter_preflight.issue_code_normalization),
                        response_classification=dict(adapter_preflight.response_classification),
                        configuration_diagnostic=dict(adapter_preflight.configuration_diagnostic),
                        next_action="next_business_day_fresh_pit_re_evaluation",
                        guard_evidence=terminal_evidence,
                    )
                )
                continue
            item_results.append(
                SubmitItemResult(
                    pending_item_id=item.pending_item_id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    preflight_status=adapter_preflight.status,
                    submit_status="NOT_SUBMITTED",
                    submitted=False,
                    accepted=False,
                    rejected=False,
                    unknown=False,
                    blocked=True,
                    review_required=adapter_preflight.review_required,
                    broker_order_id_hash="",
                    ledger_order_record_id="",
                    reason=adapter_preflight.reason,
                    issue_code_normalization=dict(adapter_preflight.issue_code_normalization),
                    response_classification=dict(adapter_preflight.response_classification),
                    configuration_diagnostic=dict(adapter_preflight.configuration_diagnostic),
                    next_action=adapter_preflight.next_action,
                    guard_evidence=guard_evidence,
                )
            )
            continue
        submit_result = submit_adapter.submit(preflight.command)
        broker_order_id = submit_result.broker_order_id_hash or _synthetic_order_id(preflight.command.command_id)
        ledger_record = _ledger_order_record(
            pending=pending,
            command=preflight.command,
            submit_result=submit_result,
            broker_order_id=broker_order_id,
            created_at=timestamp,
        )
        if submit_result.submitted:
            ledger_records.append(ledger_record)
        item_results.append(
            SubmitItemResult(
                pending_item_id=item.pending_item_id,
                symbol=item.symbol,
                side=item.side,
                quantity=item.quantity,
                preflight_status="PASS",
                submit_status=submit_result.status,
                submitted=submit_result.submitted,
                accepted=submit_result.accepted,
                rejected=submit_result.submitted and not submit_result.accepted and not submit_result.post_send_unknown,
                unknown=submit_result.post_send_unknown or submit_result.status == "UNKNOWN",
                blocked=submit_result.blocked,
                review_required=submit_result.review_required,
                broker_order_id_hash=broker_order_id if submit_result.submitted else "",
                ledger_order_record_id=ledger_record.record_id if submit_result.submitted else "",
                reason=submit_result.reason,
                issue_code_normalization=dict(submit_result.issue_code_normalization),
                response_classification=dict(submit_result.response_classification),
                configuration_diagnostic=dict(submit_result.configuration_diagnostic),
                next_action=submit_result.next_action,
                guard_evidence=guard_evidence,
            )
        )

    item_results.extend(reviewed_item_results)
    orders_path = runtime_root_path / "persistent_ledger" / "orders.jsonl"
    unsubmitted_review_present = any(result.review_required and not result.submitted for result in item_results)
    terminal_non_executable_present = any(_is_terminal_non_executable_result(result) for result in item_results)
    submitted_order_ids = tuple(result.broker_order_id_hash for result in item_results if result.submitted)
    ledger_order_record_ids = tuple(result.ledger_order_record_id for result in item_results if result.submitted)
    aggregate_terminal_noop = _submit_aggregate_terminal_noop_authority(
        pending=pending,
        item_results=tuple(item_results),
        item_scoped_review_evidence=item_scoped_review_evidence,
    )
    if submitted_order_ids:
        _append_ledger_order_records(orders_path, ledger_records)
        if any(result.unknown for result in item_results):
            pending = _mark_pending_partial_submit_terminal(
                _pending_with_accepted_items_consumed(
                    replace(pending, state=PendingPlanState.POST_SEND_UNKNOWN, updated_at=timestamp),
                    item_results=item_results,
                ),
                item_results=item_results,
                submitted_order_ids=submitted_order_ids,
                ledger_order_record_ids=ledger_order_record_ids,
            )
        elif any(result.rejected or result.blocked for result in item_results):
            pending = _mark_pending_partial_submit_terminal(
                _pending_with_accepted_items_consumed(
                    replace(pending, state=PendingPlanState.REVIEW_REQUIRED, updated_at=timestamp),
                    item_results=item_results,
                ),
                item_results=item_results,
                submitted_order_ids=submitted_order_ids,
                ledger_order_record_ids=ledger_order_record_ids,
            )
        elif unsubmitted_review_present:
            consumed_item_ids = {result.pending_item_id for result in item_results if result.accepted}
            pending = _mark_pending_partial_submit_terminal(
                _pending_with_terminal_non_executable_items(
                    replace(
                        pending,
                        items=tuple(
                            replace(item, state="CONSUMED") if item.pending_item_id in consumed_item_ids else item
                            for item in pending.items
                        ),
                        state=PendingPlanState.REVIEW_REQUIRED,
                        updated_at=timestamp,
                    ),
                    item_results=item_results,
                ),
                item_results=item_results,
                submitted_order_ids=submitted_order_ids,
                ledger_order_record_ids=ledger_order_record_ids,
            )
        elif terminal_non_executable_present:
            consumed_item_ids = {result.pending_item_id for result in item_results if result.accepted}
            pending = _mark_pending_partial_submit_terminal(
                _pending_with_terminal_non_executable_items(
                    replace(
                        pending,
                        items=tuple(
                            replace(item, state="CONSUMED") if item.pending_item_id in consumed_item_ids else item
                            for item in pending.items
                        ),
                        state=PendingPlanState.REVIEW_REQUIRED,
                        updated_at=timestamp,
                    ),
                    item_results=item_results,
                ),
                item_results=item_results,
                submitted_order_ids=submitted_order_ids,
                ledger_order_record_ids=ledger_order_record_ids,
            )
        else:
            consumed_item_ids = {result.pending_item_id for result in item_results if result.accepted}
            pending = replace(
                pending,
                items=tuple(
                    replace(item, state="CONSUMED") if item.pending_item_id in consumed_item_ids else item
                    for item in pending.items
                ),
            )
            pending = replace(pending, state=PendingPlanState.SUBMITTED, updated_at=timestamp)
            pending = consume_pending_plan(
                pending,
                consume_reason=_consume_reason(item_results),
                submitted_order_ids=submitted_order_ids,
                ledger_order_record_ids=ledger_order_record_ids,
            )
        write_pending_order_plan(Path(pending_read.path), pending)
    elif aggregate_terminal_noop["status"] == "PASS":
        pending = _mark_pending_partial_submit_terminal(
            _pending_with_terminal_non_executable_items(pending, item_results=item_results),
            item_results=item_results,
            submitted_order_ids=(),
            ledger_order_record_ids=(),
        )
        write_pending_order_plan(Path(pending_read.path), pending)

    submitted_count = sum(1 for result in item_results if result.submitted)
    accepted_count = sum(1 for result in item_results if result.accepted)
    unknown_count = sum(1 for result in item_results if result.unknown)
    blocked_count = sum(1 for result in item_results if result.blocked)
    rejected_count = sum(1 for result in item_results if result.rejected)
    status = "PASS"
    reason = "submitted"
    if submitted_count == 0:
        if any(result.guard_evidence.get("safety_guard_status") == "HALT" for result in item_results):
            status = "HALT"
            reason = "safety halt runtime"
        elif aggregate_terminal_noop["status"] == "PASS":
            status = "PASS"
            reason = "zero_submission_terminal_noop_continuation"
        elif any(result.review_required for result in item_results):
            status = "REVIEW_REQUIRED"
            if any(
                result.guard_evidence.get("submit_aggregate_status") == "REVIEW_REQUIRED"
                for result in item_results
            ):
                reason = "submit aggregate feasibility failed before broker boundary"
            else:
                reason = "submit blocked before broker boundary; manual review required"
        else:
            status = "BLOCKED"
            reason = "no pending items were submitted"
    elif unknown_count or rejected_count or blocked_count:
        status = "REVIEW_REQUIRED"
        reason = "submit completed with rejected/unknown/blocked items"
    elif unsubmitted_review_present and terminal_non_executable_present:
        reason = "submitted_with_reviewed_and_terminal_non_executable_items_not_submitted"
    elif unsubmitted_review_present:
        reason = "submitted_with_reviewed_buy_items_not_submitted"
    elif terminal_non_executable_present:
        reason = "submitted_with_terminal_non_executable_items_not_submitted"

    return SubmitPipelineResult(
        status=status,
        reason=reason,
        pending_plan_id=pending.pending_plan_id,
        pending_path=str(pending_read.path),
        orders_ledger_path=str(orders_path),
        demo_submit_executed=submitted_count > 0 and mode == "demo",
        submitted_count=submitted_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        unknown_count=unknown_count,
        blocked_count=blocked_count,
        pending_consumed=bool(getattr(pending.consume, "consumed", False)),
        submitted_order_ids=tuple(result.broker_order_id_hash for result in item_results if result.submitted),
        ledger_order_record_ids=tuple(result.ledger_order_record_id for result in item_results if result.submitted),
        submitted_symbols=tuple(result.symbol for result in item_results if result.submitted),
        item_results=tuple(item_results),
        pending_read_valid=pending_read.valid,
        pending_classification=pending_read.classification,
        pending_active=_payload_bool(pending_read.payload, "active_pending"),
        pending_plan_present=True,
        pending_item_count=len(pending.items),
        no_action_reason=_payload_text(pending_read.payload, "no_action_reason"),
        submit_action="SUBMIT" if submitted_count else "NO_SUBMIT_ATTEMPTED",
        review_required=status == "REVIEW_REQUIRED",
        halt_required=status == "HALT",
        submit_guard_policy=_submit_guard_policy_manifest(policy),
        submit_policy_consistency=policy_consistency,
        no_order_authority_status=item_scoped_review_evidence.get("status", ""),
        no_order_authority_reason=item_scoped_review_evidence.get("reason", ""),
        no_order_authority_evidence={
            **item_scoped_review_evidence,
            "submit_aggregate_terminal_noop_authority": aggregate_terminal_noop,
        }
        if aggregate_terminal_noop["status"] == "PASS"
        else item_scoped_review_evidence,
        submit_guard_item_evidence=tuple(result.guard_evidence for result in item_results),
    )


def _empty_pending_result(
    *,
    runtime_root: Path,
    pending_path: str,
    payload: Mapping[str, Any] | None,
) -> SubmitPipelineResult:
    return SubmitPipelineResult(
        status="PASS",
        reason="pending_empty_no_action",
        pending_plan_id=_payload_text(payload, "pending_plan_id"),
        pending_path=pending_path,
        orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
        demo_submit_executed=False,
        submitted_count=0,
        accepted_count=0,
        rejected_count=0,
        unknown_count=0,
        blocked_count=0,
        pending_consumed=False,
        submitted_order_ids=(),
        ledger_order_record_ids=(),
        submitted_symbols=(),
        item_results=(),
        pending_read_valid=True,
        pending_classification="EMPTY",
        pending_active=False,
        pending_plan_present=False,
        pending_item_count=0,
        no_action_reason=_payload_text(payload, "no_action_reason") or "no_active_pending_orders",
        no_order_authority_status="PASS",
        no_order_authority_reason="authorized_no_order_empty_container",
        no_order_authority_evidence={
            "authority_type": "EMPTY_CONTAINER_NO_ACTIVE_PENDING",
            "status": "PASS",
            "state": str((payload or {}).get("state") or (payload or {}).get("status") or ""),
        },
        submit_action="NO_ACTION",
        review_required=False,
        halt_required=False,
    )


def _validate_empty_pending_payload(
    payload: Mapping[str, Any] | None,
    *,
    business_date: str,
    environment: str,
    runtime_root: Path,
) -> str:
    _ = environment, runtime_root
    if not isinstance(payload, Mapping):
        return "pending EMPTY classification payload missing"
    if bool(payload.get("active_pending", True)):
        return "pending EMPTY classification active_pending contradiction"
    if str(payload.get("state") or payload.get("status") or "").upper() != "EMPTY":
        return "pending EMPTY classification state mismatch"
    items = payload.get("items")
    if items not in (None, []) and not (isinstance(items, tuple) and not items):
        return "pending EMPTY classification requires empty items"
    approved_item_ids = payload.get("approved_item_ids")
    if approved_item_ids not in (None, []) and approved_item_ids != ():
        return "pending EMPTY classification approved item ids must be empty"
    authority = payload.get("no_order_authority")
    if not isinstance(authority, Mapping):
        return "pending EMPTY no_order_authority missing"
    return validate_materialized_no_order_authority(
        payload,
        runtime_root=runtime_root,
        business_date=business_date,
        environment=environment,
    )


def _authorized_no_order_result(
    *,
    runtime_root: Path,
    pending_path: str,
    pending: PendingOrderPlan,
    evidence: dict[str, Any],
    pending_read_valid: bool,
    pending_classification: str,
    pending_active: bool | None,
    no_action_reason: str,
) -> SubmitPipelineResult:
    return SubmitPipelineResult(
        status="PASS",
        reason="NO_ORDER_AUTHORIZED",
        pending_plan_id=pending.pending_plan_id,
        pending_path=pending_path,
        orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
        demo_submit_executed=False,
        submitted_count=0,
        accepted_count=0,
        rejected_count=0,
        unknown_count=0,
        blocked_count=0,
        pending_consumed=False,
        submitted_order_ids=(),
        ledger_order_record_ids=(),
        submitted_symbols=(),
        item_results=(),
        pending_read_valid=pending_read_valid,
        pending_classification=pending_classification,
        pending_active=pending_active,
        pending_plan_present=True,
        pending_item_count=0,
        no_action_reason=no_action_reason or "strategy_planning_no_order_authorized",
        no_order_authority_status="PASS",
        no_order_authority_reason="strategy_planning_no_order_authorized",
        no_order_authority_evidence=evidence,
        submit_action="NO_SUBMISSION_REQUIRED",
        review_required=False,
        halt_required=False,
    )


def _buy_item_scoped_review_no_submission_result(
    *,
    runtime_root: Path,
    pending_path: str,
    pending: PendingOrderPlan,
    pending_read_valid: bool,
    pending_classification: str,
    pending_active: bool | None,
    no_action_reason: str,
) -> SubmitPipelineResult:
    evidence = _buy_item_scoped_review_no_submission_evidence(pending)
    return SubmitPipelineResult(
        status="PASS",
        reason="BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION_REQUIRED",
        pending_plan_id=pending.pending_plan_id,
        pending_path=pending_path,
        orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
        demo_submit_executed=False,
        submitted_count=0,
        accepted_count=0,
        rejected_count=0,
        unknown_count=0,
        blocked_count=0,
        pending_consumed=False,
        submitted_order_ids=(),
        ledger_order_record_ids=(),
        submitted_symbols=(),
        item_results=(),
        pending_read_valid=pending_read_valid,
        pending_classification=pending_classification,
        pending_active=pending_active,
        pending_plan_present=True,
        pending_item_count=len(pending.items),
        no_action_reason=no_action_reason or "buy_item_scoped_review_no_approved_items",
        no_order_authority_status="PASS",
        no_order_authority_reason="buy_item_scoped_review_no_approved_items",
        no_order_authority_evidence=evidence,
        submit_action="NO_SUBMISSION_REQUIRED",
        review_required=False,
        halt_required=False,
    )


def _is_buy_item_scoped_review_no_submission_pending(pending: PendingOrderPlan, *, business_date: str) -> bool:
    if not is_buy_item_scoped_review_sell_continuation_pending(
        pending,
        business_date=business_date,
        target_session_date=business_date,
    ):
        return False
    authority = build_pending_review_scope_authority(pending)
    if not pending_scope_no_submission_terminal_authority(authority):
        return False
    if pending.approved_item_ids or pending.approved_buy_item_ids or pending.approved_sell_item_ids:
        return False
    if any(item.approved for item in pending.items):
        return False
    return True


def _buy_item_scoped_review_no_submission_evidence(pending: PendingOrderPlan) -> dict[str, Any]:
    return {
        "authority_type": "BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION",
        "status": "PASS",
        "pending_plan_id": pending.pending_plan_id,
        "state": pending.state.value,
        "review_scope": pending.review_scope,
        "review_scope_reason": pending.review_scope_reason,
        "sell_continuation_allowed": bool(pending.sell_continuation_allowed),
        "approved_item_ids": list(pending.approved_item_ids),
        "approved_buy_item_ids": list(pending.approved_buy_item_ids),
        "approved_sell_item_ids": list(pending.approved_sell_item_ids),
        "review_required_buy_item_ids": list(pending.review_required_buy_item_ids),
        "review_required_sell_item_ids": list(pending.review_required_sell_item_ids),
        "buy_batch_atomicity_preserved": True,
        "partial_buy_submit_allowed": False,
        "reviewed_buy_submitted": False,
        "submitted_count": 0,
        "item_count": len(pending.items),
        "items": [
            {
                "pending_item_id": item.pending_item_id,
                "symbol": item.symbol,
                "side": item.side,
                "quantity": item.quantity,
                "approved": item.approved,
                "state": item.state,
                "feasibility_status": item.feasibility_status,
                "batch_submit_status": item.batch_submit_status,
                "item_review_reason": item.item_review_reason,
            }
            for item in pending.items
        ],
    }


def _validate_authorized_no_order(
    *,
    pending: PendingOrderPlan,
    runtime_root: Path,
    business_date: str,
    environment: str,
) -> tuple[str, dict[str, Any]]:
    evidence: dict[str, Any] = {
        "authority_type": "AUTHORIZED_NO_ORDER",
        "status": "REVIEW_REQUIRED",
        "pending_plan_id": pending.pending_plan_id,
        "pending_state": pending.state.value,
        "pending_item_count": len(pending.items),
        "pending_approved_item_count": len(pending.approved_item_ids),
        "business_date": business_date,
    }
    if pending.environment != environment:
        return "authorized no-order pending environment mismatch", evidence
    if pending.target_session_date != business_date:
        return "authorized no-order pending target_session_date mismatch", evidence
    if pending.plan_created_date != business_date:
        return "authorized no-order pending plan_created_date mismatch", evidence
    if pending.approval is not None:
        return "authorized no-order pending approval link must be absent", evidence
    if pending.items:
        return "authorized no-order pending items must be empty", evidence
    if pending.approved_item_ids:
        return "authorized no-order approved item ids must be empty", evidence
    if pending.consume.consumed:
        return "authorized no-order consumed pending cannot submit", evidence
    order_plan_path = _resolve_runtime_authority_path(runtime_root, pending.source_order_plan.path)
    evidence["order_plan_path"] = str(order_plan_path)
    if not order_plan_path.is_file():
        return "authorized no-order order plan missing", evidence
    order_plan_hash = _file_sha256(order_plan_path)
    evidence["order_plan_hash"] = order_plan_hash
    evidence["pending_source_order_plan_hash"] = pending.source_order_plan.artifact_hash
    if pending.source_order_plan.artifact_hash != order_plan_hash:
        return "authorized no-order order plan hash mismatch", evidence
    try:
        order_plan = json.loads(order_plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "authorized no-order order plan invalid json", evidence
    approval_path = order_plan_path.with_name("approval_artifact.json")
    evidence["approval_artifact_path"] = str(approval_path)
    if not approval_path.is_file():
        return "authorized no-order approval artifact missing", evidence
    approval_hash = _file_sha256(approval_path)
    evidence["approval_artifact_hash"] = approval_hash
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "authorized no-order approval artifact invalid json", evidence
    runtime_planning_path = _resolve_runtime_authority_path(runtime_root, str(order_plan.get("strategy_artifact_path") or ""))
    position_sizing_path = _resolve_runtime_authority_path(runtime_root, str(order_plan.get("position_sizing_artifact_path") or ""))
    evidence.update(
        {
            "order_plan_status": str(order_plan.get("status") or ""),
            "order_plan_business_date": str(order_plan.get("business_date") or ""),
            "order_plan_target_session_date": str(order_plan.get("target_session_date") or ""),
            "planning_consumer_eligibility": str(order_plan.get("planning_consumer_eligibility") or ""),
            "approval_status": str(approval.get("status") or ""),
            "approval_business_date": str(approval.get("business_date") or ""),
            "approval_order_plan_hash": str(approval.get("order_plan_hash") or ""),
            "approval_pending_plan_id": str(approval.get("pending_plan_id") or ""),
            "runtime_planning_path": str(runtime_planning_path),
            "position_sizing_path": str(position_sizing_path),
        }
    )
    if str(order_plan.get("status") or "") != "NO_ORDER_AUTHORIZED":
        return "authorized no-order order plan status mismatch", evidence
    if str(order_plan.get("planning_consumer_eligibility") or "") != "NO_ORDER_AUTHORIZED":
        return "authorized no-order planning consumer eligibility mismatch", evidence
    if str(order_plan.get("business_date") or "") != business_date:
        return "authorized no-order order plan business_date mismatch", evidence
    if str(order_plan.get("target_session_date") or "") != business_date:
        return "authorized no-order order plan target_session_date mismatch", evidence
    if str(order_plan.get("order_plan_id") or "") != pending.source_order_plan.order_plan_id:
        return "authorized no-order order_plan_id mismatch", evidence
    if order_plan.get("items") not in ([], ()):
        return "authorized no-order order plan items must be empty", evidence
    if bool(order_plan.get("broker_write_performed")):
        return "authorized no-order broker_write_performed must be false", evidence
    if bool(order_plan.get("production_decision_allowed")):
        return "authorized no-order production_decision_allowed must be false", evidence
    if bool(order_plan.get("silent_fallback_used")) or bool(order_plan.get("latest_fallback_used")):
        return "authorized no-order fallback flag must be false", evidence
    if str(approval.get("status") or "") != "NO_ORDER_AUTHORIZED":
        return "authorized no-order approval status mismatch", evidence
    if str(approval.get("business_date") or "") != business_date:
        return "authorized no-order approval business_date mismatch", evidence
    if str(approval.get("target_session_date") or business_date) != business_date:
        return "authorized no-order approval target_session_date mismatch", evidence
    if str(approval.get("pending_plan_id") or pending.pending_plan_id) != pending.pending_plan_id:
        return "authorized no-order approval pending_plan_id mismatch", evidence
    if str(approval.get("order_plan_id") or "") != pending.source_order_plan.order_plan_id:
        return "authorized no-order approval order_plan_id mismatch", evidence
    if str(approval.get("order_plan_hash") or "") != order_plan_hash:
        return "authorized no-order approval order_plan_hash mismatch", evidence
    if int(approval.get("pending_item_count") or 0) != 0:
        return "authorized no-order approval pending_item_count must be zero", evidence
    if int(approval.get("quantity_unresolved_count") or 0) != 0:
        return "authorized no-order quantity unresolved count must be zero", evidence
    if int(approval.get("review_required_quantity_count") or 0) != 0:
        return "authorized no-order review required quantity count must be zero", evidence
    runtime_planning_hash = _file_sha256(runtime_planning_path) if runtime_planning_path.is_file() else ""
    position_sizing_hash = _file_sha256(position_sizing_path) if position_sizing_path.is_file() else ""
    evidence["runtime_planning_hash"] = runtime_planning_hash
    evidence["position_sizing_hash"] = position_sizing_hash
    if str(approval.get("runtime_planning_hash") or runtime_planning_hash) != runtime_planning_hash:
        return "authorized no-order runtime planning hash mismatch", evidence
    if str(approval.get("position_sizing_hash") or position_sizing_hash) != position_sizing_hash:
        return "authorized no-order position sizing hash mismatch", evidence
    if runtime_planning_path.is_file():
        runtime_planning = json.loads(runtime_planning_path.read_text(encoding="utf-8"))
        evidence["runtime_planning_status"] = str(runtime_planning.get("producer_result_status") or "")
        evidence["runtime_planning_quantity_unresolved_count"] = _count_runtime_planning_quantity_unresolved(runtime_planning)
        evidence["runtime_planning_review_required_quantity_count"] = _count_runtime_planning_review_required_quantity(runtime_planning)
        if str(runtime_planning.get("business_date") or "") != business_date:
            return "authorized no-order runtime planning business_date mismatch", evidence
        if str(runtime_planning.get("producer_result_status") or "") != "PASS":
            return "authorized no-order runtime planning status mismatch", evidence
        if evidence["runtime_planning_quantity_unresolved_count"] != 0:
            return "authorized no-order runtime planning quantity unresolved", evidence
        if evidence["runtime_planning_review_required_quantity_count"] != 0:
            return "authorized no-order runtime planning review quantity unresolved", evidence
    else:
        return "authorized no-order runtime planning artifact missing", evidence
    evidence["status"] = "PASS"
    return "", evidence


def _count_runtime_planning_quantity_unresolved(payload: Mapping[str, Any]) -> int:
    plans = payload.get("plans")
    if not isinstance(plans, list):
        return 0
    return sum(1 for plan in plans if isinstance(plan, Mapping) and str(plan.get("quantity_status") or "").startswith("REVIEW_REQUIRED"))


def _count_runtime_planning_review_required_quantity(payload: Mapping[str, Any]) -> int:
    plans = payload.get("plans")
    if not isinstance(plans, list):
        return 0
    return sum(1 for plan in plans if isinstance(plan, Mapping) and bool(plan.get("quantity_required")) and not plan.get("planned_quantity"))


def _resolve_runtime_authority_path(runtime_root: Path, raw_path: str) -> Path:
    if not raw_path:
        return Path("")
    path = Path(raw_path)
    if path.is_absolute() or path.exists():
        return path
    candidate = runtime_root / path
    if candidate.exists():
        return candidate
    parts = path.parts
    if parts and parts[0] == runtime_root.name:
        stripped = Path(*parts[1:])
        candidate = runtime_root / stripped
        if candidate.exists():
            return candidate
    return path


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payload_text(payload: Mapping[str, Any] | None, key: str) -> str:
    if not isinstance(payload, Mapping):
        return ""
    return str(payload.get(key) or "")


def _payload_bool(payload: Mapping[str, Any] | None, key: str) -> bool | None:
    if not isinstance(payload, Mapping) or key not in payload:
        return None
    return bool(payload.get(key))


def _payload_item_count(payload: Mapping[str, Any] | None) -> int:
    if not isinstance(payload, Mapping):
        return 0
    items = payload.get("items")
    return len(items) if isinstance(items, list) else 0


def _buy_item_scoped_review_partial_submission_evidence(pending: PendingOrderPlan) -> dict[str, Any]:
    scope_authority = build_pending_review_scope_authority(pending)
    if not pending_scope_allows_partial_submit(scope_authority):
        return {}
    approved_ids = set(scope_authority.executable_item_ids)
    reviewed_ids = set(scope_authority.reviewed_buy_item_ids)
    reviewed_items = tuple(item for item in pending.items if item.pending_item_id in reviewed_ids)
    submitted_items = tuple(item for item in pending.items if item.pending_item_id in approved_ids)
    return {
        "authority_type": "BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION",
        "status": "PASS",
        "reason": "pass_buy_items_submit_review_buy_items_deferred",
        "pending_plan_id": pending.pending_plan_id,
        "review_scope": scope_authority.review_scope,
        "review_scope_reason": pending.review_scope_reason,
        "pending_review_scope_authority": scope_authority.to_dict(),
        "item_review_does_not_escalate_to_batch_failure": True,
        "true_batch_failure_atomicity_preserved": True,
        "partial_pass_buy_submission_allowed": True,
        "reviewed_buy_submitted": False,
        "reviewed_item_count": len(reviewed_items),
        "submitted_candidate_count": len(submitted_items),
        "review_required_buy_item_ids": list(scope_authority.reviewed_buy_item_ids),
        "approved_item_ids": list(scope_authority.executable_item_ids),
        "items": [
            {
                "pending_item_id": item.pending_item_id,
                "symbol": item.symbol,
                "side": item.side,
                "quantity": item.quantity,
                "feasibility_status": item.feasibility_status,
                "batch_submit_status": item.batch_submit_status,
                "item_review_reason": item.item_review_reason,
                "submitted": item.pending_item_id in approved_ids,
                "not_submitted_reason": "item_scoped_review_required"
                if item.pending_item_id in reviewed_ids
                else "",
                "blocked_other_items": False if item.pending_item_id in reviewed_ids else None,
                "batch_membership": "active_pending_buy_item_scoped_review_batch",
            }
            for item in pending.items
            if item.pending_item_id in reviewed_ids or item.pending_item_id in approved_ids
        ],
    }


def _reviewed_buy_item_results(
    pending: PendingOrderPlan,
    *,
    item_scoped_review_evidence: Mapping[str, Any],
) -> list[SubmitItemResult]:
    if not item_scoped_review_evidence:
        return []
    reviewed_ids = set(pending.review_required_buy_item_ids)
    results: list[SubmitItemResult] = []
    for item in pending.items:
        if item.pending_item_id not in reviewed_ids:
            continue
        reason = item.item_review_reason or pending.review_scope_reason or "buy_item_scoped_review_required"
        results.append(
            SubmitItemResult(
                pending_item_id=item.pending_item_id,
                symbol=item.symbol,
                side=item.side,
                quantity=item.quantity,
                preflight_status="REVIEW_REQUIRED",
                submit_status="NOT_SUBMITTED",
                submitted=False,
                accepted=False,
                rejected=False,
                unknown=False,
                blocked=False,
                review_required=True,
                broker_order_id_hash="",
                ledger_order_record_id="",
                reason=reason,
                issue_code_normalization={},
                response_classification={},
                configuration_diagnostic={},
                next_action="defer until item authority is repaired or refreshed",
                guard_evidence={
                    "authority_type": "BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED",
                    "status": "PASS",
                    "symbol": item.symbol,
                    "side": item.side,
                    "quantity": item.quantity,
                    "pending_item_id": item.pending_item_id,
                    "review_authority": pending.review_scope_source,
                    "review_scope": pending.review_scope,
                    "review_reason": reason,
                    "not_submitted_reason": "item_scoped_review_required",
                    "batch_membership": "active_pending_buy_item_scoped_review_batch",
                    "blocked_other_items": False,
                },
            )
        )
    return results


def _pending_submit_guard(pending: PendingOrderPlan, *, business_date: str) -> str:
    if pending.state in {
        PendingPlanState.SUBMITTING,
        PendingPlanState.SUBMITTED,
        PendingPlanState.POST_SEND_UNKNOWN,
        PendingPlanState.CONSUMED,
        PendingPlanState.BLOCKED,
    }:
        return f"dangerous pending state blocked: {pending.state.value}"
    scope_authority = build_pending_review_scope_authority(pending)
    if pending.state == PendingPlanState.REVIEW_REQUIRED and not pending_scope_allows_partial_submit(scope_authority):
        return f"dangerous pending state blocked: {pending.state.value}"
    if pending.state not in {PendingPlanState.APPROVED, PendingPlanState.REVIEW_REQUIRED}:
        return "pending state is not APPROVED"
    if pending.target_session_date != business_date:
        return "pending target_session_date mismatch"
    if pending.approval is None:
        return "pending approval link missing"
    if pending.approval.approval_status != "APPROVED":
        return "pending approval is not APPROVED"
    if pending.consume.consumed:
        return "consumed pending cannot be submitted"
    if set(pending.approved_item_ids) != {item.pending_item_id for item in pending.items if item.approved}:
        return "approved item ids mismatch"
    if pending.state == PendingPlanState.REVIEW_REQUIRED:
        reviewed_ids = set(pending.review_required_buy_item_ids) | set(pending.review_required_sell_item_ids)
        if any(item_id in reviewed_ids for item_id in pending.approved_item_ids):
            return "review required item cannot be approved for submit"
    return ""


def _default_environment_context(
    *,
    mode: str,
    pending_environment: str,
    adapter: RuntimeV2SubmitAdapter,
    broker_write: bool,
    business_date: str,
    now: str,
) -> SubmitEnvironmentGuardContext:
    if mode == "historical" and isinstance(adapter, HistoricalSubmitAdapter):
        diagnostic = adapter.diagnostic()
        return SubmitEnvironmentGuardContext(
            runtime_environment="historical",
            pending_environment=pending_environment,
            run_type="HISTORICAL",
            broker_environment=str(diagnostic.get("broker_environment") or "historical_simulated"),
            adapter_type=type(adapter).__name__,
            broker_write=False,
            external_delivery=False,
            business_date=business_date,
            evaluation_time=str(diagnostic.get("evaluation_time") or now),
            production_acceptance=False,
        )
    if mode == "demo":
        return SubmitEnvironmentGuardContext(
            runtime_environment="demo",
            pending_environment=pending_environment,
            run_type="DEMO",
            broker_environment="tachibana_demo",
            adapter_type="DemoSubmitAdapter",
            broker_write=broker_write,
            external_delivery=False,
            business_date=business_date,
            evaluation_time=now,
            production_acceptance=False,
        )
    return SubmitEnvironmentGuardContext(
        runtime_environment=mode,
        pending_environment=pending_environment,
        run_type=mode.upper(),
        broker_environment="tachibana_production" if mode == "production" else "",
        adapter_type=type(adapter).__name__,
        broker_write=broker_write,
        external_delivery=False,
        business_date=business_date,
        evaluation_time=now,
        production_acceptance=False,
    )


def _approval_from_pending(pending: PendingOrderPlan) -> ApprovalArtifact:
    if pending.approval is None:
        raise ValueError("pending approval link missing")
    return ApprovalArtifact(
        approval_id=pending.approval.approval_path.rsplit("/", 1)[-1] or "pending-linked-approval",
        approval_request_id=f"request-{pending.pending_plan_id}",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus(pending.approval.approval_status),
        approved_item_ids=pending.approval.approved_item_ids,
        rejected_item_ids=(),
        approval_hash=pending.approval.approval_hash,
        approved_at=pending.updated_at,
        expires_at=pending.approval.approval_expires_at,
        review_required=False,
        reason="approval reconstructed from Pending Current link",
        policy_version=pending.approval.policy_version,
        policy_source=pending.approval.policy_source,
        pending_policy_hash=pending.approval.pending_policy_hash,
        planning_authority_version=pending.approval.planning_authority_version,
        planning_authority_source=pending.approval.planning_authority_source,
        planning_authority_hash=pending.approval.planning_authority_hash,
        submit_policy_version=pending.approval.submit_policy_version,
        submit_policy_source=pending.approval.submit_policy_source,
        submit_policy_hash=pending.approval.submit_policy_hash,
        safety_decision_id=pending.approval.safety_decision_id,
        safety_policy_version=pending.approval.safety_policy_version,
        approved_order_conditions=pending.approval.approved_order_conditions,
    )


def _policy_consistency_evidence(
    *,
    pending: PendingOrderPlan,
    approval: ApprovalArtifact,
    active_policy: CapitalDeploymentPolicy,
) -> dict[str, Any]:
    active_hash = capital_deployment_policy_hash(active_policy)
    evidence = {
        "policy_consistency_status": "PASS",
        "pending_policy_version": pending.policy_version,
        "pending_policy_source": pending.policy_source,
        "pending_policy_hash": pending.pending_policy_hash,
        "planning_authority_version": pending.planning_authority_version,
        "planning_authority_source": pending.planning_authority_source,
        "planning_authority_hash": pending.planning_authority_hash,
        "approval_planning_authority_version": approval.planning_authority_version,
        "approval_planning_authority_source": approval.planning_authority_source,
        "approval_planning_authority_hash": approval.planning_authority_hash,
        "pending_submit_policy_version": pending.submit_policy_version,
        "pending_submit_policy_source": pending.submit_policy_source,
        "pending_submit_policy_hash": pending.submit_policy_hash,
        "approval_submit_policy_version": approval.submit_policy_version,
        "approval_submit_policy_source": approval.submit_policy_source,
        "approval_submit_policy_hash": approval.submit_policy_hash,
        "approval_policy_version": approval.policy_version,
        "approval_policy_source": approval.policy_source,
        "approval_pending_policy_hash": approval.pending_policy_hash,
        "active_policy_version": active_policy.policy_version,
        "active_policy_source": active_policy.policy_source,
        "active_policy_hash": active_hash,
        "comparison_authority": "submit_policy_authority",
        "policy_mismatch_reason": "",
        "policy_mismatch_manual_review_required": False,
    }
    missing_reason = _missing_policy_evidence_reason(pending=pending, approval=approval, active_hash=active_hash)
    if missing_reason:
        evidence.update(
            {
                "policy_consistency_status": "REVIEW_REQUIRED",
                "policy_mismatch_reason": missing_reason,
                "policy_mismatch_manual_review_required": True,
            }
        )
        return evidence
    mismatches = []
    if pending.submit_policy_version != active_policy.policy_version:
        mismatches.append("pending_submit_policy_version")
    if pending.submit_policy_source != active_policy.policy_source:
        mismatches.append("pending_submit_policy_source")
    if pending.submit_policy_hash != active_hash:
        mismatches.append("pending_submit_policy_hash")
    if approval.submit_policy_version != pending.submit_policy_version:
        mismatches.append("approval_submit_policy_version")
    if approval.submit_policy_source != pending.submit_policy_source:
        mismatches.append("approval_submit_policy_source")
    if approval.submit_policy_hash != pending.submit_policy_hash:
        mismatches.append("approval_submit_policy_hash")
    if mismatches:
        evidence.update(
            {
                "policy_consistency_status": "REVIEW_REQUIRED",
                "policy_mismatch_reason": "policy_mismatch:" + ",".join(mismatches),
                "policy_mismatch_manual_review_required": True,
            }
        )
    return evidence


def _missing_policy_evidence_reason(
    *,
    pending: PendingOrderPlan,
    approval: ApprovalArtifact,
    active_hash: str,
) -> str:
    if not pending.submit_policy_version or not pending.submit_policy_source or not pending.submit_policy_hash:
        return "missing_submit_policy_evidence"
    if not approval.submit_policy_version or not approval.submit_policy_source or not approval.submit_policy_hash:
        return "missing_approval_submit_policy_evidence"
    if not pending.planning_authority_version or not pending.planning_authority_source:
        return "missing_planning_lineage_evidence"
    if not active_hash:
        return "active_policy_hash_missing"
    return ""


def _ledger_order_record(
    *,
    pending: PendingOrderPlan,
    command: RuntimeV2SubmitCommand,
    submit_result: RuntimeV2SubmitResult,
    broker_order_id: str,
    created_at: str,
) -> LedgerOrderRecord:
    record_id = "ledger-order-submit-" + _short_hash(command.command_id)
    pending_item = next((item for item in pending.items if item.pending_item_id == command.pending_item_id), None)
    provenance = (
        pending_item_provenance(pending_item)
        if pending_item is not None
        else {
            "source_decision_id": command.source_decision_id,
            "source_decision_type": command.source_decision_type,
            "source_pm_decision_id": command.source_pm_decision_id,
            "order_plan_item_id": command.order_plan_item_id,
            "position_campaign_id": command.position_campaign_id,
            "campaign_id": command.campaign_id,
        }
    )
    return LedgerOrderRecord(
        record_id=record_id,
        record_type="order",
        schema_version="1",
        environment=command.environment,
        source="runtime_v2_submit_pipeline",
        created_at=created_at,
        dedup_key=f"runtime_v2_submit:{command.command_id}",
        review_required=submit_result.review_required,
        production_equivalent=command.environment == "production",
        order_id=broker_order_id,
        business_date=pending.target_session_date,
        pending_plan_id=pending.pending_plan_id,
        pending_item_id=command.pending_item_id,
        side=command.side,
        symbol=command.symbol,
        quantity=command.quantity,
        status=submit_result.status,
        issue_code_normalization=dict(submit_result.issue_code_normalization),
        response_classification=dict(submit_result.response_classification),
        source_decision_id=str(provenance["source_decision_id"]),
        source_decision_type=str(provenance["source_decision_type"]),
        source_pm_decision_id=str(provenance["source_pm_decision_id"]),
        source_pm_business_date=str(pending_item.source_pm_business_date if pending_item is not None else ""),
        source_position_symbol=str(pending_item.source_position_symbol if pending_item is not None else ""),
        order_plan_item_id=str(provenance["order_plan_item_id"]),
        position_campaign_id=str(provenance["position_campaign_id"]),
        campaign_id=str(provenance["campaign_id"]),
        add_candidate_signal=bool(pending_item.add_candidate_signal if pending_item is not None else False),
        capital_allocation_status=str(pending_item.capital_allocation_status if pending_item is not None else ""),
        capital_allocation_reason=str(pending_item.capital_allocation_reason if pending_item is not None else ""),
        strategy_authority_lineage=(
            dict(pending_item.strategy_authority_lineage)
            if pending_item is not None and isinstance(pending_item.strategy_authority_lineage, Mapping)
            else dict(command.strategy_authority_lineage or {})
        ),
        strategy_authority_lineage_hash=str(
            pending_item.strategy_authority_lineage_hash
            if pending_item is not None and pending_item.strategy_authority_lineage_hash
            else command.strategy_authority_lineage_hash
        ),
    )


def _append_ledger_order_records(path: Path, records: list[LedgerOrderRecord]) -> None:
    if _is_mode_rooted_runtime_path(path):
        raise ValueError("Ledger writer does not write mode-rooted runtime paths")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = _existing_order_dedup_keys(path)
    lines = []
    for record in records:
        if record.dedup_key in existing_keys:
            continue
        lines.append(json.dumps(ledger_record_to_payload(record), sort_keys=True))
        existing_keys.add(record.dedup_key)
    if not lines:
        return
    with path.open("a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\n")


def _mark_pending_partial_submit_terminal(
    pending: PendingOrderPlan,
    *,
    item_results: list[SubmitItemResult],
    submitted_order_ids: tuple[str, ...],
    ledger_order_record_ids: tuple[str, ...],
) -> PendingOrderPlan:
    return replace(
        pending,
        consume=PendingConsumeInfo(
            consumed=False,
            consume_reason=_consume_reason(item_results),
            consumed_at="",
            submitted_order_ids=_unique_non_empty(submitted_order_ids),
            ledger_order_record_ids=_unique_non_empty(ledger_order_record_ids),
        ),
    )


def _pending_with_accepted_items_consumed(
    pending: PendingOrderPlan,
    *,
    item_results: list[SubmitItemResult],
) -> PendingOrderPlan:
    consumed_item_ids = {result.pending_item_id for result in item_results if result.accepted}
    if not consumed_item_ids:
        return pending
    return replace(
        pending,
        items=tuple(
            replace(item, state="CONSUMED") if item.pending_item_id in consumed_item_ids else item
            for item in pending.items
        ),
    )


def _pending_with_terminal_non_executable_items(
    pending: PendingOrderPlan,
    *,
    item_results: list[SubmitItemResult],
) -> PendingOrderPlan:
    terminal_results = {
        result.pending_item_id: result for result in item_results if _is_terminal_non_executable_result(result)
    }
    if not terminal_results:
        return pending
    items = []
    for item in pending.items:
        result = terminal_results.get(item.pending_item_id)
        if result is None:
            items.append(item)
            continue
        items.append(
            replace(
                item,
                approved=False,
                state=NOT_EXECUTABLE_ITEM_STATE,
                feasibility_status=str(
                    result.guard_evidence.get("execution_feasibility_status")
                    or result.guard_evidence.get("feasibility_status")
                    or EXECUTION_AUTHORITY_UNAVAILABLE_FEASIBILITY_STATUS
                ),
                batch_submit_status=NOT_EXECUTABLE_ITEM_STATE,
                item_review_reason=str(
                    result.guard_evidence.get("terminal_reason")
                    or result.guard_evidence.get("guard_reason")
                    or result.reason
                    or NOT_EXECUTABLE_ITEM_STATE
                ),
            )
        )
    terminal_ids = set(terminal_results)
    return replace(
        pending,
        approved_item_ids=tuple(item_id for item_id in pending.approved_item_ids if item_id not in terminal_ids),
        approved_buy_item_ids=tuple(item_id for item_id in pending.approved_buy_item_ids if item_id not in terminal_ids),
        approved_sell_item_ids=tuple(item_id for item_id in pending.approved_sell_item_ids if item_id not in terminal_ids),
        items=tuple(items),
    )


def _submit_aggregate_terminal_noop_authority(
    *,
    pending: PendingOrderPlan,
    item_results: tuple[SubmitItemResult, ...],
    item_scoped_review_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    pending_with_terminal_items = _pending_with_terminal_non_executable_items(pending, item_results=list(item_results))
    scope_authority = build_pending_review_scope_authority(pending_with_terminal_items)
    item_classes = {
        result.pending_item_id: _submit_aggregate_item_class(
            result,
            item_scoped_review_evidence=item_scoped_review_evidence,
        )
        for result in item_results
    }
    counts = {
        "submitted_or_reconciled": sum(1 for item_class in item_classes.values() if item_class == "SUBMITTED_OR_RECONCILED"),
        "terminal_not_executable": sum(1 for item_class in item_classes.values() if item_class == "TERMINAL_NOT_EXECUTABLE"),
        "deferred_item_scoped_review": sum(
            1 for item_class in item_classes.values() if item_class == "DEFERRED_ITEM_SCOPED_REVIEW"
        ),
        "blocked": sum(1 for item_class in item_classes.values() if item_class == "BLOCKED"),
        "rejected": sum(1 for item_class in item_classes.values() if item_class == "REJECTED"),
        "unknown_or_ambiguous": sum(1 for item_class in item_classes.values() if item_class == "UNKNOWN_OR_AMBIGUOUS"),
        "retryable_executable": sum(1 for item_class in item_classes.values() if item_class == "RETRYABLE_EXECUTABLE"),
    }
    checks = {
        "items_present": bool(item_results),
        "all_items_have_known_dispositions": bool(item_results)
        and all(item_class != "UNKNOWN_OR_AMBIGUOUS" for item_class in item_classes.values()),
        "blocked_absent": counts["blocked"] == 0,
        "rejected_absent": counts["rejected"] == 0,
        "unknown_or_ambiguous_absent": counts["unknown_or_ambiguous"] == 0,
        "retryable_executable_absent": counts["retryable_executable"] == 0,
        "item_scoped_reviews_deferred_by_authority": _deferred_item_scoped_reviews_safe(
            item_results,
            item_scoped_review_evidence=item_scoped_review_evidence,
        ),
        "terminal_not_executable_items_safety_qualified": all(
            _is_terminal_non_executable_result(result)
            for result in item_results
            if item_classes.get(result.pending_item_id) == "TERMINAL_NOT_EXECUTABLE"
        ),
        "pending_review_scope_structural_valid": scope_authority.structural_validity == "PASS",
        "pending_review_scope_not_batch_blocked": not scope_authority.batch_blocked,
        "pending_review_scope_no_executable_items_after_terminalization": not scope_authority.executable_item_ids,
        "pending_review_scope_no_non_terminal_items_after_terminalization": not scope_authority.non_terminal_item_ids,
        "reviewed_sell_absent": not scope_authority.reviewed_sell_item_ids,
    }
    status = "PASS" if all(checks.values()) else "NOT_APPLICABLE"
    return {
        "authority_type": "SUBMIT_AGGREGATE_TERMINAL_NOOP_CONTINUATION",
        "status": status,
        "reason": (
            "zero_submission_terminal_noop_continuation"
            if status == "PASS"
            else "submit_aggregate_terminal_noop_not_applicable"
        ),
        "classification_authority": "SubmitItemResult + PendingReviewScopeAuthority",
        "pending_plan_id": pending.pending_plan_id,
        "pending_review_scope_authority": scope_authority.to_dict(),
        "item_classes": item_classes,
        "counts": counts,
        "submitted_count": sum(1 for result in item_results if result.submitted),
        "accepted_count": sum(1 for result in item_results if result.accepted),
        "known_safe_terminal_or_deferred_count": (
            counts["submitted_or_reconciled"]
            + counts["terminal_not_executable"]
            + counts["deferred_item_scoped_review"]
        ),
        "checks": checks,
        "zero_submission_safe_terminal_pass_supported": True,
        "fake_submission_created": False,
        "fake_execution_created": False,
        "fake_cash_mutation": False,
        "fake_position_mutation": False,
        "corporate_action_safety_changed": False,
        "same_day_retry_prevented_for_terminal_items": all(
            result.guard_evidence.get("retry_eligible_same_day") is False
            for result in item_results
            if item_classes.get(result.pending_item_id) == "TERMINAL_NOT_EXECUTABLE"
        ),
    }


def _submit_aggregate_item_class(
    result: SubmitItemResult,
    *,
    item_scoped_review_evidence: Mapping[str, Any],
) -> str:
    if result.submitted or result.accepted:
        return "SUBMITTED_OR_RECONCILED"
    if result.blocked:
        return "BLOCKED"
    if result.rejected:
        return "REJECTED"
    if result.unknown:
        return "UNKNOWN_OR_AMBIGUOUS"
    if _is_terminal_non_executable_result(result):
        return "TERMINAL_NOT_EXECUTABLE"
    if _is_deferred_item_scoped_review_result(result, item_scoped_review_evidence=item_scoped_review_evidence):
        return "DEFERRED_ITEM_SCOPED_REVIEW"
    if not result.submitted and not result.review_required and str(result.preflight_status or "").upper() in {
        "PASS",
        "APPROVED",
        "READY",
        "DRY_RUN_READY",
    }:
        return "RETRYABLE_EXECUTABLE"
    return "UNKNOWN_OR_AMBIGUOUS"


def _deferred_item_scoped_reviews_safe(
    item_results: tuple[SubmitItemResult, ...],
    *,
    item_scoped_review_evidence: Mapping[str, Any],
) -> bool:
    reviewed_results = tuple(result for result in item_results if result.review_required and not result.submitted)
    if not reviewed_results:
        return True
    return all(
        _is_deferred_item_scoped_review_result(result, item_scoped_review_evidence=item_scoped_review_evidence)
        for result in reviewed_results
    )


def _is_deferred_item_scoped_review_result(
    result: SubmitItemResult,
    *,
    item_scoped_review_evidence: Mapping[str, Any],
) -> bool:
    reviewed_ids = set(str(item_id) for item_id in item_scoped_review_evidence.get("review_required_buy_item_ids") or ())
    return bool(
        result.review_required
        and not result.submitted
        and not result.accepted
        and not result.blocked
        and not result.unknown
        and not result.rejected
        and result.pending_item_id in reviewed_ids
        and str(result.guard_evidence.get("authority_type") or "") == "BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED"
        and str(result.guard_evidence.get("review_scope") or "") == "BUY_ITEM_SCOPED_REVIEW"
        and str(item_scoped_review_evidence.get("status") or "") == "PASS"
        and bool(item_scoped_review_evidence.get("item_review_does_not_escalate_to_batch_failure"))
        and not bool(result.guard_evidence.get("blocked_other_items"))
    )


def _is_terminal_non_executable_result(result: SubmitItemResult) -> bool:
    evidence = result.guard_evidence
    feasibility_status = str(evidence.get("execution_feasibility_status") or evidence.get("feasibility_status") or "")
    side_effect_absent = all(
        not bool(evidence.get(field))
        for field in (
            "adapter_submit_called",
            "order_created",
            "broker_side_effect_created",
            "ledger_order_created",
            "position_mutated",
            "cash_mutated",
            "realized_pnl_mutated",
        )
    )
    return (
        not result.submitted
        and not result.accepted
        and not result.blocked
        and not result.unknown
        and not result.rejected
        and not result.review_required
        and str(result.preflight_status or "").upper() == NOT_EXECUTABLE_ITEM_STATE
        and str(evidence.get("status") or "") == "PASS"
        and str(evidence.get("authority_type") or "").endswith("_TERMINAL")
        and feasibility_status.startswith("NOT_EXECUTABLE")
        and side_effect_absent
    )


def _is_execution_authority_unavailable_preflight_result(result: RuntimeV2SubmitResult) -> bool:
    if result.submitted or result.accepted or result.post_send_unknown or result.broker_api_called:
        return False
    if result.status not in {"HALT", "BLOCKED", "REVIEW_REQUIRED"}:
        return False
    reason = str(result.reason or "")
    classification_reason = str((result.response_classification or {}).get("reason") or "")
    diagnostic_reason = str((result.configuration_diagnostic or {}).get("reason") or "")
    combined = " ".join(part.lower() for part in (reason, classification_reason, diagnostic_reason) if part)
    if not combined:
        return False
    authority_unavailable_markers = (
        "execution_authority_unavailable",
        "missing or non-unique target session ohlcv row",
        "canonical same-day execution authority unavailable",
        "execution price authority unavailable",
    )
    ambiguity_markers = (
        "conflict",
        "ambiguous",
        "duplicate",
        "post_send_unknown",
        "partial mutation",
        "identity mismatch",
    )
    return any(marker in combined for marker in authority_unavailable_markers) and not any(
        marker in combined for marker in ambiguity_markers
    )


def _execution_authority_unavailable_terminal_evidence(
    *,
    item: Any,
    pending: PendingOrderPlan,
    adapter_preflight: RuntimeV2SubmitResult,
    guard_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **dict(guard_evidence),
        "authority_type": "ITEM_EXECUTION_AUTHORITY_UNAVAILABLE_TERMINAL",
        "status": "PASS",
        "pending_plan_id": pending.pending_plan_id,
        "pending_item_id": item.pending_item_id,
        "symbol": item.symbol,
        "side": item.side,
        "planned_quantity": item.quantity,
        "quantity": item.quantity,
        "strategy_runtime_planning_intent": item.source_decision_type or str(item.side or "").upper(),
        "execution_feasibility_status": EXECUTION_AUTHORITY_UNAVAILABLE_FEASIBILITY_STATUS,
        "terminal_reason": EXECUTION_AUTHORITY_UNAVAILABLE_REASON,
        "execution_authority_source": "submit_adapter_preflight",
        "authority_resolution_status": "UNAVAILABLE",
        "adapter_preflight_status": adapter_preflight.status,
        "adapter_preflight_reason": adapter_preflight.reason,
        "adapter_submit_called": False,
        "order_created": False,
        "broker_side_effect_created": False,
        "ledger_order_created": False,
        "position_mutated": False,
        "cash_mutated": False,
        "realized_pnl_mutated": False,
        "retry_eligible_same_day": False,
        "next_day_re_evaluation_required": True,
        "future_information_used": False,
        "fallback_price_used": False,
        "previous_close_execution_fallback_used": False,
        "broker_write": False,
        "guard_decision": NOT_EXECUTABLE_ITEM_STATE,
        "guard_reason": EXECUTION_AUTHORITY_UNAVAILABLE_REASON,
        "manual_review_required": False,
    }


def _existing_submitted_item_records(
    runtime_root: Path,
    *,
    pending: PendingOrderPlan,
    business_date: str,
) -> dict[str, ExistingSubmittedItemRecord]:
    records = _existing_submitted_item_records_from_ledger(
        runtime_root / "persistent_ledger" / "orders.jsonl",
        pending=pending,
        business_date=business_date,
    )
    broker_records = _existing_submitted_item_records_from_historical_broker(
        runtime_root / "runtime_state" / "historical_broker" / business_date,
        pending=pending,
        business_date=business_date,
    )
    for item_id, broker_record in broker_records.items():
        records.setdefault(item_id, broker_record)
    return records


def _existing_submitted_item_records_from_ledger(
    path: Path,
    *,
    pending: PendingOrderPlan,
    business_date: str,
) -> dict[str, ExistingSubmittedItemRecord]:
    if not path.exists():
        return {}
    records: dict[str, ExistingSubmittedItemRecord] = {}
    items_by_id = {item.pending_item_id: item for item in pending.items}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(payload.get("pending_plan_id") or "") != pending.pending_plan_id:
            continue
        item_id = str(payload.get("pending_item_id") or "")
        item = items_by_id.get(item_id)
        if item is None:
            continue
        if str(payload.get("business_date") or business_date) != business_date:
            continue
        if str(payload.get("status") or "").upper() != "ACCEPTED":
            continue
        if not _submitted_item_payload_matches_pending_item(payload, item):
            continue
        order_id = str(payload.get("order_id") or "")
        if not order_id:
            continue
        records[item_id] = ExistingSubmittedItemRecord(
            pending_item_id=item_id,
            symbol=str(payload.get("symbol") or ""),
            side=str(payload.get("side") or ""),
            quantity=_float(payload.get("quantity")),
            order_id=order_id,
            ledger_order_record_id=str(payload.get("ledger_record_id") or payload.get("record_id") or ""),
            source="persistent_ledger.orders",
            evidence_path=str(path),
        )
    return records


def _existing_submitted_item_records_from_historical_broker(
    directory: Path,
    *,
    pending: PendingOrderPlan,
    business_date: str,
) -> dict[str, ExistingSubmittedItemRecord]:
    if not directory.exists():
        return {}
    records: dict[str, ExistingSubmittedItemRecord] = {}
    items_by_id = {item.pending_item_id: item for item in pending.items}
    for path in sorted(directory.glob("*.json")):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if str(payload.get("pending_plan_id") or "") != pending.pending_plan_id:
            continue
        item_id = str(payload.get("pending_item_id") or "")
        item = items_by_id.get(item_id)
        if item is None:
            continue
        if str(payload.get("target_session_date") or payload.get("fill_date") or business_date) != business_date:
            continue
        if str(payload.get("status") or "").upper() != "ACCEPTED":
            continue
        if not _submitted_item_payload_matches_pending_item(payload, item):
            continue
        order_id = str(payload.get("order_identity") or "")
        if not order_id:
            continue
        records[item_id] = ExistingSubmittedItemRecord(
            pending_item_id=item_id,
            symbol=str(payload.get("symbol") or ""),
            side=str(payload.get("side") or ""),
            quantity=_float(payload.get("quantity")),
            order_id=order_id,
            ledger_order_record_id="",
            source="runtime_state.historical_broker",
            evidence_path=str(path),
        )
    return records


def _submitted_item_payload_matches_pending_item(payload: Mapping[str, Any], item: Any) -> bool:
    if str(payload.get("side") or "").upper() != str(item.side).upper():
        return False
    if str(payload.get("symbol") or "") and str(payload.get("symbol") or "") != str(item.symbol):
        return False
    try:
        if float(payload.get("quantity")) != float(item.quantity):
            return False
    except (TypeError, ValueError):
        return False
    return True


def _existing_order_dedup_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("dedup_key"):
            keys.add(str(payload["dedup_key"]))
        if payload.get("pending_plan_id"):
            keys.add(str(payload["pending_plan_id"]))
    return keys


def _unique_non_empty(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)


def _current_position_quantities(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    quantities: dict[str, float] = {}
    for position in payload.get("positions") or ():
        symbol = str(position.get("symbol") or position.get("issue_code") or "").strip()
        if not symbol:
            continue
        quantities[symbol] = quantities.get(symbol, 0.0) + _float(position.get("quantity"))
    return quantities


def _current_state_summary(path: Path, *, business_date: str = "") -> dict[str, Any]:
    return load_runtime_current_exposure(path, business_date=business_date).to_payload()


def _load_broker_available_quantity_snapshot(runtime_root: Path) -> dict[str, Any]:
    snapshot_dir = runtime_root / "broker" / "snapshots" / "positions"
    snapshot_path = _latest_broker_positions_snapshot_path(snapshot_dir)
    if snapshot_path is None:
        return {
            "status": "MISSING",
            "source": "missing",
            "snapshot_path": "",
            "snapshot_at": "",
            "records": (),
            "review_required": True,
            "production_equivalent": False,
            "reason": "broker positions readonly snapshot missing",
        }
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "INVALID",
            "source": "invalid",
            "snapshot_path": str(snapshot_path),
            "snapshot_at": "",
            "records": (),
            "review_required": True,
            "production_equivalent": False,
            "reason": "broker positions readonly snapshot invalid json",
        }
    records = tuple(_broker_position_records(payload))
    source = str(payload.get("source") or "broker_readonly")
    snapshot_at = str(payload.get("as_of") or payload.get("created_at") or payload.get("generated_at") or "")
    return {
        "status": "PASS" if records else "EMPTY",
        "source": source,
        "snapshot_path": str(snapshot_path),
        "snapshot_at": snapshot_at,
        "records": records,
        "review_required": bool(payload.get("review_required", False)),
        "production_equivalent": bool(payload.get("production_equivalent", source == "broker_readonly")),
        "reason": "" if records else "broker positions readonly snapshot empty",
    }


def _latest_broker_positions_snapshot_path(snapshot_dir: Path) -> Path | None:
    if not snapshot_dir.exists():
        return None
    candidates = [
        path
        for path in snapshot_dir.glob("*.json")
        if path.is_file() and not path.name.endswith(".manifest.json")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _broker_position_records(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    records = payload.get("records")
    if isinstance(records, list):
        return tuple(record for record in records if isinstance(record, dict))
    positions = payload.get("positions")
    if isinstance(positions, list):
        return tuple(position for position in positions if isinstance(position, dict))
    return ()


def _broker_available_quantity_evidence(
    *,
    item: Any,
    snapshot: dict[str, Any],
) -> BrokerAvailableQuantityEvidence:
    normalized = _broker_issue_code_for_item(item)
    if normalized.get("status") != "PASS":
        return BrokerAvailableQuantityEvidence(
            checked=False,
            source=str(snapshot.get("source") or "missing"),
            symbol=str(item.symbol),
            issue_code="",
            snapshot_path=str(snapshot.get("snapshot_path") or ""),
            snapshot_at=str(snapshot.get("snapshot_at") or ""),
            review_required=True,
            production_equivalent=bool(snapshot.get("production_equivalent", False)),
            reason="broker issue code normalization failed: " + str(normalized.get("reason") or ""),
        )
    broker_issue_code = str(normalized["broker_issue_code"])
    if snapshot.get("status") != "PASS":
        return BrokerAvailableQuantityEvidence(
            checked=False,
            source="missing",
            symbol=str(item.symbol),
            issue_code=broker_issue_code,
            snapshot_path=str(snapshot.get("snapshot_path") or ""),
            snapshot_at=str(snapshot.get("snapshot_at") or ""),
            review_required=True,
            production_equivalent=bool(snapshot.get("production_equivalent", False)),
            reason=str(snapshot.get("reason") or "broker positions readonly snapshot missing"),
        )
    matching = [
        record
        for record in snapshot.get("records", ())
        if _record_issue_code(record) == broker_issue_code
    ]
    if not matching:
        return BrokerAvailableQuantityEvidence(
            checked=False,
            source="missing",
            symbol=str(item.symbol),
            issue_code=broker_issue_code,
            snapshot_path=str(snapshot.get("snapshot_path") or ""),
            snapshot_at=str(snapshot.get("snapshot_at") or ""),
            review_required=True,
            production_equivalent=bool(snapshot.get("production_equivalent", False)),
            reason="broker positions readonly record missing for symbol",
        )
    total_quantity = sum(_float(record.get("quantity")) for record in matching)
    available_values = [_optional_float(record.get("available_quantity")) for record in matching]
    if any(value is None for value in available_values):
        return BrokerAvailableQuantityEvidence(
            checked=False,
            source="missing",
            symbol=str(item.symbol),
            issue_code=broker_issue_code,
            snapshot_path=str(snapshot.get("snapshot_path") or ""),
            snapshot_at=_record_snapshot_at(matching, snapshot),
            review_required=True,
            production_equivalent=bool(snapshot.get("production_equivalent", False)),
            total_quantity=total_quantity,
            restricted_quantity=None,
            account_type=_record_account_type(matching),
            reason="broker available quantity missing in readonly record",
        )
    available_quantity = sum(float(value or 0.0) for value in available_values)
    review_required = bool(snapshot.get("review_required", False)) or any(
        bool(record.get("review_required", False)) for record in matching
    )
    production_equivalent = bool(snapshot.get("production_equivalent", False)) and all(
        bool(record.get("production_equivalent", True)) for record in matching
    )
    return BrokerAvailableQuantityEvidence(
        checked=not review_required,
        source="broker_readonly",
        quantity=available_quantity,
        symbol=str(item.symbol),
        issue_code=broker_issue_code,
        snapshot_path=str(snapshot.get("snapshot_path") or ""),
        snapshot_at=_record_snapshot_at(matching, snapshot),
        review_required=review_required,
        production_equivalent=production_equivalent,
        total_quantity=total_quantity,
        restricted_quantity=max(total_quantity - available_quantity, 0.0),
        account_type=_record_account_type(matching),
        reason="broker_readonly_available_quantity_confirmed",
    )


def _historical_available_quantity_evidence(
    *,
    runtime_root: Path,
    item: Any,
    current_quantity: float | None,
) -> BrokerAvailableQuantityEvidence:
    normalized = _broker_issue_code_for_item(item)
    if normalized.get("status") != "PASS":
        return BrokerAvailableQuantityEvidence(
            checked=False,
            source="historical_simulated_broker_authority",
            symbol=str(item.symbol),
            reason=str(normalized.get("reason") or "issue code normalization failed"),
        )
    if current_quantity is None:
        return BrokerAvailableQuantityEvidence(
            checked=False,
            source="historical_simulated_broker_authority",
            symbol=str(item.symbol),
            issue_code=str(normalized["broker_issue_code"]),
            review_required=False,
            production_equivalent=False,
            reason="historical current quantity missing",
        )
    restricted_quantity = _historical_restricted_sell_quantity(
        runtime_root=runtime_root,
        symbol=str(item.symbol),
    )
    available_quantity = max(float(current_quantity) - restricted_quantity, 0.0)
    return BrokerAvailableQuantityEvidence(
        checked=True,
        source="historical_simulated_broker_authority",
        quantity=available_quantity,
        symbol=str(item.symbol),
        issue_code=str(normalized["broker_issue_code"]),
        review_required=False,
        production_equivalent=False,
        total_quantity=float(current_quantity),
        restricted_quantity=restricted_quantity,
        reason="historical simulated broker authority confirmed from runtime-owned Current and open SELL order ledger",
    )


def _historical_restricted_sell_quantity(*, runtime_root: Path, symbol: str) -> float:
    normalized_symbol = str(symbol).strip()
    sell_order_quantity = 0.0
    sell_execution_quantity = 0.0
    for record in _read_jsonl_records(runtime_root / "persistent_ledger" / "orders.jsonl"):
        if str(record.get("environment") or "") != "historical":
            continue
        if str(record.get("side") or "").upper() != "SELL":
            continue
        if str(record.get("symbol") or "").strip() != normalized_symbol:
            continue
        if not _is_historical_open_sell_order(record):
            continue
        sell_order_quantity += _float(record.get("quantity"))
    for record in _read_jsonl_records(runtime_root / "persistent_ledger" / "executions.jsonl"):
        if str(record.get("environment") or record.get("mode") or "") != "historical":
            continue
        if str(record.get("side") or "").upper() != "SELL":
            continue
        if str(record.get("symbol") or record.get("broker_issue_code") or "").strip() != normalized_symbol:
            continue
        if str(record.get("execution_status") or "").lower() not in {"filled", "partial_fill", "partially_filled"}:
            continue
        sell_execution_quantity += _float(record.get("filled_quantity") or record.get("quantity"))
    return max(sell_order_quantity - sell_execution_quantity, 0.0)


def _is_historical_open_sell_order(record: Mapping[str, Any]) -> bool:
    status = str(record.get("status") or record.get("order_status") or "").strip().upper()
    if status in {
        "REJECTED",
        "CANCELLED",
        "CANCELED",
        "FILLED",
        "FILL",
        "FULL_FILL",
        "FULLY_FILLED",
        "DONE",
    }:
        return False
    source = str(record.get("source") or "").strip()
    if source == "runtime_v2_execution_readonly_simulation":
        return False
    return True


def _read_jsonl_records(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.is_file():
        return ()
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return tuple(records)


def _broker_issue_code_for_item(item: Any) -> dict[str, Any]:
    try:
        normalized = normalize_broker_issue_code(item.symbol, listed_info=item.listed_info)
    except BrokerIssueCodeNormalizationError as exc:
        return {"status": "BLOCKED", "reason": str(exc)}
    return {"status": "PASS", "broker_issue_code": normalized.broker_issue_code}


def _record_issue_code(record: dict[str, Any]) -> str:
    return str(record.get("issue_code") or record.get("symbol") or record.get("position_key") or "").strip()


def _record_snapshot_at(records: list[dict[str, Any]], snapshot: dict[str, Any]) -> str:
    for record in records:
        value = record.get("as_of") or record.get("updated_at")
        if value:
            return str(value)
    return str(snapshot.get("snapshot_at") or "")


def _record_account_type(records: list[dict[str, Any]]) -> str:
    account_types = sorted({str(record.get("account_type") or "") for record in records if record.get("account_type")})
    return ",".join(account_types)


def _resolve_capital_deployment_policy(
    *,
    capital_deployment_policy: CapitalDeploymentPolicy | None,
    capital_deployment_policy_path: Path | str | None,
) -> tuple[CapitalDeploymentPolicy | None, dict[str, Any], str]:
    if capital_deployment_policy is not None:
        return capital_deployment_policy, _submit_guard_policy_manifest(capital_deployment_policy), ""
    if capital_deployment_policy_path is None:
        manifest = missing_policy_manifest_fields(
            None,
            reason="POLICY_MISSING:capital deployment policy is required for submit",
        )
        return None, manifest, str(manifest["policy_validation_status"])
    try:
        policy = load_capital_deployment_policy(capital_deployment_policy_path)
    except CapitalDeploymentPolicyError as exc:
        manifest = missing_policy_manifest_fields(capital_deployment_policy_path, reason="POLICY_MISSING:" + str(exc))
        return None, manifest, str(manifest["policy_validation_status"])
    return policy, _submit_guard_policy_manifest(policy), ""


def _submit_guard_policy_manifest(policy: CapitalDeploymentPolicy) -> dict[str, Any]:
    manifest = policy.to_manifest_fields()
    manifest.update(
        {
            "guard_policy_version": "submit_guard_policy_v1",
            "active_amount_policy": "buy_sell_separated_capital_deployment_policy",
            "policy_source": policy.policy_source,
            "policy_version": policy.policy_version,
            "active_policy_hash": capital_deployment_policy_hash(policy),
            "max_positions": policy.max_positions,
            "configured_legacy_max_positions": policy.max_positions,
            "legacy_position_count_config_used": False,
        }
    )
    return manifest


def _submit_guard_item_evidence(
    *,
    item: Any,
    pending_plan: Any,
    runtime_root: Path,
    business_date: str,
    mode: str,
    policy: CapitalDeploymentPolicy,
    current_state: dict[str, Any],
    broker_position_quantity: float | None,
    broker_available_quantity: float | None,
    broker_available_quantity_evidence: BrokerAvailableQuantityEvidence,
    safety_decision: RuntimeSafetyDecision,
    feasibility_evidence: Mapping[str, Any] | None = None,
    corporate_action_event_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    side = str(item.side).upper()
    estimated_amount = float(item.estimated_amount)
    reserved_notional = float(getattr(item, "reserved_notional", None) or estimated_amount)
    evidence = {
        "guard_policy_version": "submit_guard_policy_v1",
        "submit_authority_source": "pending_approval_planning_materialized_evidence",
        "submit_authority_winner": "canonical_quantity_contract_revalidated_at_submit",
        "submit_scope": "item",
        "submit_aggregate_status": "",
        "submit_item_status": "PASS",
        "planning_evidence_source": "pending_item.quantity_contract",
        "approval_evidence_source": "approval.approved_order_conditions",
        "submit_fallback_used": False,
        "buy_sell_submit_independence_preserved": True,
        "runtime_mode": mode,
        "business_date": business_date,
        "selected_current_source": current_state.get("selected_current_source"),
        "selected_cash_source": current_state.get("selected_cash_source"),
        "selected_positions_source": current_state.get("selected_positions_source"),
        "selected_valuation_source": current_state.get("selected_valuation_source"),
        "selected_projection_source": current_state.get("selected_projection_source"),
        "current_authority_winner": current_state.get("current_authority_winner"),
        "current_source_business_date": current_state.get("current_source_business_date"),
        "current_source_generation": current_state.get("current_source_generation"),
        "current_authority_status": current_state.get("current_authority_status"),
        "current_authority_reason": current_state.get("current_authority_reason"),
        "source_conflict_detected": current_state.get("source_conflict_detected"),
        "source_selection_reason": current_state.get("source_selection_reason"),
        "legacy_current_used": bool(current_state.get("legacy_current_used", False)),
        "current_fallback_used": bool(current_state.get("current_fallback_used", False)),
        "runtime_evaluation_capital_used_as_current": bool(
            current_state.get("runtime_evaluation_capital_used_as_current", False)
        ),
        "active_amount_policy": "buy_sell_separated_capital_deployment_policy",
        "policy_source": policy.policy_source,
        "policy_version": policy.policy_version,
        "side": side,
        "pending_item_id": item.pending_item_id,
        "symbol": item.symbol,
        "quantity": float(item.quantity),
        "estimated_amount": estimated_amount,
        "capital_allocation_amount": estimated_amount,
        "reference_price": getattr(item, "reference_price", None) or getattr(item, "estimated_price", None),
        "reservation_price": getattr(item, "reservation_price", None) or getattr(item, "estimated_price", None),
        "reservation_price_authority": dict(getattr(item, "reservation_price_authority", None) or {}),
        "reservation_reason": str(getattr(item, "reservation_reason", "") or ""),
        "reserved_notional": reserved_notional,
        "quantity_contract": dict(getattr(item, "quantity_contract", None) or {}),
        "max_buy_order_amount": policy.max_buy_order_amount,
        "max_sell_liquidation_amount": policy.max_sell_liquidation_amount,
        "max_positions": policy.max_positions,
        "configured_legacy_max_positions": policy.max_positions,
        "legacy_position_count_config_used": False,
        "position_count_fallback_used": False,
        "notional_guard_source": "",
        "quantity_guard_source": "",
        "current_position_source": current_state["current_position_source"],
        "selected_capital_source": current_state.get("selected_capital_source"),
        "selected_capital_value": current_state.get("active_deployment_capital"),
        "capital_authority_winner": "current_total_equity",
        "active_deployment_capital": current_state.get("active_deployment_capital"),
        "initial_or_bootstrap_capital": current_state.get("initial_or_bootstrap_capital"),
        "current_total_equity": current_state.get("current_total_equity"),
        "legacy_capital_config_used": False,
        "capital_fallback_used": bool(current_state.get("capital_fallback_used", False)),
        "current_quantity": broker_position_quantity,
        "sell_quantity": float(item.quantity) if side == "SELL" else None,
        "sell_quantity_guard_status": "",
        "broker_available_quantity_checked": False,
        "broker_available_quantity_source": broker_available_quantity_evidence.source,
        "broker_available_quantity": broker_available_quantity,
        "broker_available_quantity_symbol": broker_available_quantity_evidence.symbol,
        "broker_available_quantity_issue_code": broker_available_quantity_evidence.issue_code,
        "broker_available_quantity_snapshot_path": broker_available_quantity_evidence.snapshot_path,
        "broker_available_quantity_snapshot_at": broker_available_quantity_evidence.snapshot_at,
        "broker_available_quantity_review_required": broker_available_quantity_evidence.review_required,
        "broker_available_quantity_production_equivalent": broker_available_quantity_evidence.production_equivalent,
        "broker_total_quantity": broker_available_quantity_evidence.total_quantity,
        "broker_restricted_quantity": broker_available_quantity_evidence.restricted_quantity,
        "broker_available_quantity_account_type": broker_available_quantity_evidence.account_type,
        "broker_available_quantity_reason": broker_available_quantity_evidence.reason,
        "safety_decision_id": safety_decision.safety_decision_id,
        "safety_policy_version": safety_decision.safety_policy_version,
        "safety_source": safety_decision.safety_source,
        "safety_decision": safety_decision.decision,
        "safety_reason": safety_decision.reason,
        "pending_safety_decision_id": getattr(item, "safety_decision_id", ""),
        "pending_safety_policy_version": getattr(item, "safety_policy_version", ""),
        "pending_safety_source": getattr(item, "safety_source", ""),
        "pending_safety_decision": getattr(item, "safety_decision", ""),
        "pending_safety_reason": getattr(item, "safety_reason", ""),
        "safety_block_buy": safety_decision.block_buy,
        "safety_block_sell": safety_decision.block_sell,
        "safety_block_submit": safety_decision.block_submit,
        "safety_halt_runtime": safety_decision.halt_runtime,
        "safety_emergency_stop": safety_decision.emergency_stop,
        "safety_guard_status": "",
        "guard_decision": "PASS",
        "guard_reason": "approved_by_submit_guard_policy",
        "manual_review_required": False,
        "violated_policy": "",
        "violated_policy_source": "",
        "should_have_been_blocked_at_planning": False,
        "blocked_at_submit_reason": "",
    }
    generation_evidence = _submit_generation_binding_evidence(
        item=item,
        pending_plan=pending_plan,
        business_date=business_date,
        mode=mode,
    )
    evidence.update(generation_evidence)
    if generation_evidence["submit_generation_binding_status"] != "PASS":
        return _blocked_guard_evidence(
            evidence=evidence,
            reason=str(generation_evidence["submit_generation_binding_reason"]),
            violated_policy="accepted_generation_binding",
            violated_policy_source=str(generation_evidence["submit_generation_binding_source"]),
            should_have_been_blocked_at_planning=True,
        )
    if feasibility_evidence:
        evidence.update(_submit_feasibility_evidence_fields(feasibility_evidence))
        evidence["submit_aggregate_status"] = str(feasibility_evidence.get("status") or "")
    if mode == "historical":
        quarantine_entry = unresolved_corporate_action_quarantine_entry(runtime_root, item.symbol)
        if quarantine_entry:
            reason = str(quarantine_entry.get("reason") or "corporate_action_event_not_resolved")
            event_status = str(quarantine_entry.get("event_status") or "IMPACT_DETECTED")
            evidence.update(quarantine_fields(symbol=str(item.symbol), reason=reason))
            evidence.update(
                {
                    "corporate_action_event_status": event_status,
                    "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
                    "corporate_action_adjustment_authority_reason": reason,
                    "corporate_action_reason_codes": ["corporate_action_event_not_resolved"],
                    "quantity_reconciliation_status": "REVIEW_REQUIRED",
                    "price_reconciliation_status": "REVIEW_REQUIRED",
                    "already_applied_status": "UNKNOWN",
                }
            )
            return _blocked_guard_evidence(
                evidence=evidence,
                reason=reason,
                violated_policy="historical_corporate_action_symbol_quarantine",
                violated_policy_source=str(corporate_action_quarantine_registry_path(runtime_root)),
                should_have_been_blocked_at_planning=True,
            )
    corporate_action_authority = evaluate_corporate_action_adjustment_authority(
        runtime_root=runtime_root,
        business_date=business_date,
        symbol=item.symbol,
        side=side,
        submit_quantity=float(item.quantity),
        pending_quantity=float(item.quantity),
        current_quantity=broker_position_quantity,
        broker_available_quantity=broker_available_quantity,
        event_evidence=corporate_action_event_evidence,
    )
    evidence.update(_corporate_action_adjustment_evidence_fields(corporate_action_authority))
    if corporate_action_authority["corporate_action_adjustment_authority_status"] != "PASS":
        return _blocked_guard_evidence(
            evidence=evidence,
            reason=str(corporate_action_authority["corporate_action_adjustment_authority_reason"]),
            violated_policy="corporate_action_adjustment_authority",
            violated_policy_source=str(corporate_action_authority["corporate_action_adjustment_authority_path"]),
            should_have_been_blocked_at_planning=True,
        )
    if side == "BUY":
        evidence.update(
            {
                "broker_available_quantity_source": "not_applicable_buy",
                "broker_available_quantity": None,
                "broker_available_quantity_symbol": str(item.symbol),
                "broker_available_quantity_issue_code": "",
                "broker_available_quantity_snapshot_path": "",
                "broker_available_quantity_snapshot_at": "",
                "broker_available_quantity_review_required": False,
                "broker_available_quantity_production_equivalent": False,
                "broker_total_quantity": None,
                "broker_restricted_quantity": None,
                "broker_available_quantity_account_type": "",
                "broker_available_quantity_reason": "broker available quantity is sell-only authority",
            }
        )
    safety_allowed, safety_status, safety_reason = safety_allows_action(
        safety_decision,
        action="submit",
        side=side,
    )
    evidence["safety_guard_status"] = safety_status
    if not safety_allowed:
        return _blocked_guard_evidence(
            evidence=evidence,
            reason=safety_reason,
            violated_policy="safety_operation_guard",
            violated_policy_source=safety_decision.safety_source or safety_decision.artifact_path,
        )
    if side == "BUY":
        buy_eligibility = evaluate_buy_eligibility(
            symbol=item.symbol,
            business_date=business_date,
            mode=mode,
            listed_info=item.listed_info,
            runtime_root=runtime_root,
            authority_source="pending_item_listed_info",
        )
        evidence.update(_buy_eligibility_evidence_fields(buy_eligibility.to_payload()))
        if not buy_eligibility.eligible:
            return _blocked_guard_evidence(
                evidence=evidence,
                reason=buy_eligibility.reason_code,
                violated_policy="buy_market_status_eligibility",
                violated_policy_source=buy_eligibility.authority_source or buy_eligibility.authority_path,
                should_have_been_blocked_at_planning=True,
            )
        opportunity_eligibility = _submit_opportunity_buy_eligibility(
            item=item,
            business_date=business_date,
        )
        evidence.update(_opportunity_buy_eligibility_evidence_fields(opportunity_eligibility.to_payload()))
        if not opportunity_eligibility.eligible:
            return _blocked_guard_evidence(
                evidence=evidence,
                reason=opportunity_eligibility.reason_code,
                violated_policy="opportunity_buy_eligibility",
                violated_policy_source=opportunity_eligibility.opportunity_artifact_path,
                should_have_been_blocked_at_planning=True,
            )
        return _buy_guard_evidence(evidence=evidence, policy=policy, current_state=current_state)
    if side == "SELL":
        return _sell_guard_evidence(
            evidence=evidence,
            policy=policy,
            item=item,
            broker_position_quantity=broker_position_quantity,
            broker_available_quantity=broker_available_quantity,
        )
    return _blocked_guard_evidence(
        evidence=evidence,
        reason="unsupported side",
        violated_policy="supported_side",
        violated_policy_source="runtime_v2_submit_guard",
    )


def _materialize_corporate_action_authority_for_item(
    *,
    runtime_root: Path,
    business_date: str,
    mode: str,
    adapter: RuntimeV2SubmitAdapter,
    item: Any,
    current_quantity: float | None,
    broker_available_quantity: float | None,
) -> dict[str, Any] | None:
    if mode != "historical" or not isinstance(adapter, HistoricalSubmitAdapter):
        return None
    event = historical_corporate_action_event_evidence(
        raw_ohlcv_path=adapter.raw_ohlcv_path,
        business_date=business_date,
        symbol=str(item.symbol),
    )
    materialize_corporate_action_adjustment_authority(
        runtime_root=runtime_root,
        business_date=business_date,
        symbol=str(item.symbol),
        event_evidence=event,
        current_quantity=current_quantity,
        broker_available_quantity=broker_available_quantity,
        pending_quantity=float(item.quantity),
        submit_quantity=float(item.quantity),
    )
    return event


def _corporate_action_adjustment_evidence_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "corporate_action_event_status": str(payload.get("corporate_action_event_status") or ""),
        "corporate_action_event_type": str(payload.get("corporate_action_event_type") or ""),
        "corporate_action_effective_date": str(payload.get("corporate_action_effective_date") or ""),
        "corporate_action_adjustment_factor": payload.get("corporate_action_adjustment_factor"),
        "corporate_action_adjustment_authority_path": str(payload.get("corporate_action_adjustment_authority_path") or ""),
        "corporate_action_adjustment_authority_hash": str(payload.get("corporate_action_adjustment_authority_hash") or ""),
        "corporate_action_adjustment_authority_status": str(payload.get("corporate_action_adjustment_authority_status") or ""),
        "corporate_action_adjustment_authority_reason": str(payload.get("corporate_action_adjustment_authority_reason") or ""),
        "ledger_quantity_before": payload.get("ledger_quantity_before"),
        "ledger_quantity_after": payload.get("ledger_quantity_after"),
        "corporate_action_current_quantity": payload.get("current_quantity"),
        "corporate_action_broker_available_quantity": payload.get("broker_available_quantity"),
        "corporate_action_pending_quantity": payload.get("pending_quantity"),
        "corporate_action_submit_quantity": payload.get("submit_quantity"),
        "quantity_reconciliation_status": str(payload.get("quantity_reconciliation_status") or ""),
        "price_reconciliation_status": str(payload.get("price_reconciliation_status") or ""),
        "already_applied_status": str(payload.get("already_applied_status") or ""),
        "double_adjustment_detected": bool(payload.get("double_adjustment_detected")),
        "pit_validation_status": str(payload.get("pit_validation_status") or ""),
        "future_data_used": bool(payload.get("future_data_used")),
        "corporate_action_reason_codes": list(payload.get("reason_codes") or []),
    }


def _buy_eligibility_evidence_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "buy_eligibility_schema_version": str(payload.get("schema_version") or ""),
        "buy_eligibility_status": str(payload.get("status") or ""),
        "buy_eligibility": str(payload.get("buy_eligibility") or ""),
        "buy_eligibility_reason_code": str(payload.get("reason_code") or ""),
        "buy_eligibility_reason": str(payload.get("reason") or ""),
        "buy_eligibility_authority_source": str(payload.get("authority_source") or ""),
        "buy_eligibility_authority_path": str(payload.get("authority_path") or ""),
        "buy_eligibility_authority_hash": str(payload.get("authority_hash") or ""),
        "buy_eligibility_authority_as_of": str(payload.get("authority_as_of") or ""),
        "buy_eligibility_authority_type": str(payload.get("authority_type") or ""),
        "buy_eligibility_current_listed": payload.get("current_listed"),
        "buy_eligibility_market_status": str(payload.get("market_status") or ""),
        "buy_eligibility_listing_status": str(payload.get("listing_status") or ""),
        "buy_eligibility_special_supervision_status": str(payload.get("special_supervision_status") or ""),
        "buy_eligibility_delisting_date": str(payload.get("delisting_date") or ""),
        "buy_eligibility_point_in_time": bool(payload.get("point_in_time")),
        "buy_eligibility_future_authority_used": bool(payload.get("future_authority_used")),
        "buy_eligibility_missing_authority": bool(payload.get("missing_authority")),
        "buy_eligibility_stale_authority": bool(payload.get("stale_authority")),
    }


def _submit_opportunity_buy_eligibility(*, item: Any, business_date: str):
    listed_info = item.listed_info if isinstance(item.listed_info, Mapping) else {}
    opportunity_artifact_path = str(listed_info.get("opportunity_artifact_path") or "")
    feature_date = str(
        listed_info.get("opportunity_feature_date")
        or getattr(item, "price_as_of", "")
        or business_date
    )
    row = {
        "symbol": item.symbol,
        "business_date": str(listed_info.get("opportunity_business_date") or business_date),
        "feature_date": feature_date,
        "opportunity_authority": listed_info.get("opportunity_authority"),
        "opportunity_row_id": listed_info.get("opportunity_row_id"),
        "runtime_opportunity_score": listed_info.get("runtime_opportunity_score"),
        "expected_edge_score": listed_info.get("opportunity_expected_edge_score"),
        "expected_return": listed_info.get("opportunity_expected_return"),
        "no_buy_reason": listed_info.get("opportunity_no_buy_reason"),
        "buy_rank": listed_info.get("opportunity_buy_rank"),
        "canonical_score_field": listed_info.get("opportunity_canonical_score_field") or "runtime_opportunity_score",
        "score_semantic_role": listed_info.get("opportunity_score_semantic_role"),
        "calibration_applied": listed_info.get("opportunity_calibration_applied"),
        "economic_units_available": listed_info.get("opportunity_economic_units_available"),
        "expected_edge_score_semantic_role": listed_info.get("expected_edge_score_semantic_role"),
        "expected_return_semantic_role": listed_info.get("expected_return_semantic_role"),
    }
    return evaluate_opportunity_buy_eligibility(
        symbol=item.symbol,
        business_date=business_date,
        feature_date=feature_date,
        opportunity_artifact_path=opportunity_artifact_path or None,
        opportunity_row=row if listed_info else None,
        expected_artifact_hash=str(listed_info.get("opportunity_artifact_hash") or ""),
        require_row_identity=bool(opportunity_artifact_path),
        excluded_at_stage="submit_guard",
    )


def _opportunity_buy_eligibility_evidence_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "opportunity_buy_eligibility_schema_version": str(payload.get("schema_version") or ""),
        "opportunity_buy_eligibility_status": str(payload.get("status") or ""),
        "opportunity_buy_eligibility": str(payload.get("buy_eligibility") or ""),
        "opportunity_buy_eligibility_reason_code": str(payload.get("reason_code") or ""),
        "opportunity_buy_eligibility_reason": str(payload.get("reason") or ""),
        "opportunity_expected_edge_score": payload.get("expected_edge_score"),
        "opportunity_expected_return": payload.get("expected_return"),
        "runtime_opportunity_score": payload.get("runtime_opportunity_score"),
        "opportunity_no_buy_reason": str(payload.get("no_buy_reason") or ""),
        "opportunity_buy_rank": payload.get("buy_rank"),
        "opportunity_canonical_score_field": str(payload.get("canonical_score_field") or ""),
        "opportunity_score_semantic_role": str(payload.get("score_semantic_role") or ""),
        "opportunity_calibration_applied": bool(payload.get("calibration_applied")),
        "opportunity_economic_units_available": bool(payload.get("economic_units_available")),
        "opportunity_absolute_economic_gate_applicable": bool(payload.get("absolute_economic_gate_applicable")),
        "opportunity_relative_competition_eligible": bool(payload.get("relative_competition_eligible")),
        "expected_edge_score_semantic_role": str(payload.get("expected_edge_score_semantic_role") or ""),
        "expected_return_semantic_role": str(payload.get("expected_return_semantic_role") or ""),
        "opportunity_artifact_path": str(payload.get("opportunity_artifact_path") or ""),
        "opportunity_artifact_hash": str(payload.get("opportunity_artifact_hash") or ""),
        "opportunity_row_id": str(payload.get("opportunity_row_id") or ""),
        "opportunity_authority": str(payload.get("opportunity_authority") or ""),
        "opportunity_business_date": str(payload.get("business_date") or ""),
        "opportunity_feature_date": str(payload.get("feature_date") or ""),
        "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
    }


def _buy_guard_evidence(
    *,
    evidence: dict[str, Any],
    policy: CapitalDeploymentPolicy,
    current_state: dict[str, Any],
) -> dict[str, Any]:
    estimated_amount = float(evidence["estimated_amount"])
    evidence["notional_guard_source"] = policy.buy_notional_policy
    evidence["quantity_guard_source"] = "broker_lot_size_and_pending_quantity"
    feasibility = evaluate_buy_item_submit_feasibility(
        item=type("SubmitGuardItem", (), {
            "pending_item_id": evidence["pending_item_id"],
            "symbol": evidence["symbol"],
            "quantity": evidence["quantity"],
            "estimated_amount": estimated_amount,
            "estimated_price": evidence.get("reference_price") or 0.0,
            "reference_price": evidence.get("reference_price"),
            "reservation_price": evidence.get("reservation_price"),
            "reservation_price_authority": evidence.get("reservation_price_authority"),
            "reservation_reason": evidence.get("reservation_reason"),
            "reserved_notional": evidence.get("reserved_notional"),
            "quantity_contract": evidence.get("quantity_contract") if isinstance(evidence.get("quantity_contract"), Mapping) else evidence,
        })(),
        policy=policy,
        current=RuntimeCurrentExposure(
            cash=current_state["cash"],
            buying_power=current_state["buying_power"],
            current_exposure=float(current_state["current_exposure"]),
            current_total_equity=current_state.get("current_total_equity"),
            active_deployment_capital=current_state.get("active_deployment_capital"),
            selected_capital_source=str(current_state.get("selected_capital_source") or "current_state.total_equity"),
            capital_fallback_used=bool(current_state.get("capital_fallback_used", False)),
            initial_or_bootstrap_capital=current_state.get("initial_or_bootstrap_capital"),
            positions=dict(current_state["positions"]),
            position_market_values=dict(current_state.get("position_market_values") or {}),
            current_position_source=str(current_state["current_position_source"]),
        ),
        authority_source="submit_guard_item_canonical_evidence_revalidation",
        business_date=str(evidence.get("opportunity_business_date") or ""),
        runtime_mode=str(current_state.get("environment") or ""),
    )
    if feasibility["status"] == "PASS":
        evidence.update(_submit_feasibility_evidence_fields(feasibility))
        return evidence
    evidence.update(_submit_feasibility_evidence_fields(feasibility))
    return _blocked_guard_evidence(
        evidence=evidence,
        reason=str(feasibility["reason"]),
        violated_policy=str(feasibility["violated_policy"]),
        violated_policy_source=str(feasibility["violated_policy_source"]),
        should_have_been_blocked_at_planning=True,
    )


def _submit_feasibility_evidence_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "submit_feasibility_authority_source": str(payload.get("authority_source") or ""),
        "submit_feasibility_sequence_index": payload.get("sequence_index"),
        "selected_current_source": payload.get("selected_current_source"),
        "selected_cash_source": payload.get("selected_cash_source"),
        "selected_positions_source": payload.get("selected_positions_source"),
        "selected_valuation_source": payload.get("selected_valuation_source"),
        "selected_projection_source": payload.get("selected_projection_source"),
        "current_authority_winner": payload.get("current_authority_winner"),
        "current_source_business_date": payload.get("current_source_business_date"),
        "current_source_generation": payload.get("current_source_generation"),
        "current_authority_status": payload.get("current_authority_status"),
        "current_authority_reason": payload.get("current_authority_reason"),
        "source_conflict_detected": payload.get("source_conflict_detected"),
        "source_selection_reason": payload.get("source_selection_reason"),
        "legacy_current_used": payload.get("legacy_current_used"),
        "current_fallback_used": payload.get("current_fallback_used"),
        "runtime_evaluation_capital_used_as_current": payload.get("runtime_evaluation_capital_used_as_current"),
        "cash": payload.get("cash"),
        "buying_power": payload.get("buying_power"),
        "current_exposure": payload.get("current_exposure"),
        "selected_capital_source": payload.get("selected_capital_source"),
        "selected_capital_value": payload.get("selected_capital_value"),
        "capital_authority_winner": payload.get("capital_authority_winner"),
        "active_deployment_capital": payload.get("active_deployment_capital"),
        "initial_or_bootstrap_capital": payload.get("initial_or_bootstrap_capital"),
        "current_total_equity": payload.get("current_total_equity"),
        "legacy_capital_config_used": payload.get("legacy_capital_config_used"),
        "capital_fallback_used": payload.get("capital_fallback_used"),
        "selected_runtime_exposure_limit": payload.get("selected_runtime_exposure_limit"),
        "planning_budget": payload.get("planning_budget"),
        "remaining_exposure_capacity": payload.get("remaining_exposure_capacity") or payload.get("remaining_exposure"),
        "position_sizing_authority": payload.get("position_sizing_authority"),
        "portfolio_policy_source": payload.get("portfolio_policy_source"),
        "portfolio_policy_authority_winner": payload.get("portfolio_policy_authority_winner"),
        "position_sizing_source": payload.get("position_sizing_source"),
        "position_sizing_authority_winner": payload.get("position_sizing_authority_winner"),
        "position_sizing_authority_status": payload.get("position_sizing_authority_status"),
        "position_sizing_authority_reason": payload.get("position_sizing_authority_reason"),
        "strategy_requested_position_weight": payload.get("strategy_requested_position_weight"),
        "selected_position_weight": payload.get("selected_position_weight"),
        "strategy_requested_position_amount": payload.get("strategy_requested_position_amount"),
        "selected_position_amount": payload.get("selected_position_amount"),
        "remaining_add_capacity": payload.get("remaining_add_capacity"),
        "lot_adjusted_quantity": payload.get("lot_adjusted_quantity"),
        "lot_adjusted_notional": payload.get("lot_adjusted_notional"),
        "position_sizing_binding_constraint": payload.get("position_sizing_binding_constraint"),
        "position_sizing_fallback_used": payload.get("position_sizing_fallback_used"),
        "legacy_position_sizing_used": payload.get("legacy_position_sizing_used"),
        "position_sizing_authority_source": payload.get("position_sizing_authority_source"),
        "position_sizing_authority_hash": payload.get("position_sizing_authority_hash"),
        "remaining_exposure": payload.get("remaining_exposure"),
        "strategy_requested_cash_ratio": payload.get("strategy_requested_cash_ratio"),
        "selected_dynamic_cash_ratio": payload.get("selected_dynamic_cash_ratio"),
        "strategy_requested_exposure_ratio": payload.get("strategy_requested_exposure_ratio"),
        "selected_dynamic_exposure_ratio": payload.get("selected_dynamic_exposure_ratio"),
        "current_cash": payload.get("current_cash"),
        "current_market_value": payload.get("current_market_value"),
        "target_exposure_amount": payload.get("target_exposure_amount"),
        "safety_exposure_limit": payload.get("safety_exposure_limit"),
        "cash_exposure_authority_winner": payload.get("cash_exposure_authority_winner"),
        "cash_exposure_binding_constraint": payload.get("cash_exposure_binding_constraint"),
        "legacy_cash_config_used": payload.get("legacy_cash_config_used"),
        "legacy_exposure_config_used": payload.get("legacy_exposure_config_used"),
        "cash_exposure_fallback_used": payload.get("cash_exposure_fallback_used"),
        "cash_exposure_authority": payload.get("cash_exposure_authority"),
        "active_max_positions": payload.get("active_max_positions"),
        "configured_legacy_max_positions": payload.get("configured_legacy_max_positions"),
        "legacy_runtime_max_positions": payload.get("legacy_runtime_max_positions"),
        "strategy_requested_position_count": payload.get("strategy_requested_position_count"),
        "selected_dynamic_position_count": payload.get("selected_dynamic_position_count"),
        "available_position_slots": payload.get("available_position_slots"),
        "safety_hard_maximum": payload.get("safety_hard_maximum"),
        "position_count_authority_winner": payload.get("position_count_authority_winner"),
        "position_count_binding_constraint": payload.get("position_count_binding_constraint"),
        "legacy_position_count_config_used": payload.get("legacy_position_count_config_used"),
        "position_count_fallback_used": payload.get("position_count_fallback_used"),
        "position_count_authority": payload.get("position_count_authority"),
        "current_position_count": payload.get("current_position_count"),
        "creates_new_position": payload.get("creates_new_position"),
        "post_position_count": payload.get("post_position_count"),
        "post_buy_cash": payload.get("post_buy_cash"),
        "post_buy_buying_power": payload.get("post_buy_buying_power"),
        "post_buy_exposure": payload.get("post_buy_exposure"),
    }


def _submit_generation_binding_evidence(
    *,
    item: Any,
    pending_plan: Any,
    business_date: str,
    mode: str,
) -> dict[str, Any]:
    approval = getattr(pending_plan, "approval", None)
    side = str(getattr(item, "side", "") or "").upper()
    pending_binding = getattr(pending_plan, "accepted_generation_binding", None)
    item_binding = getattr(item, "accepted_generation_binding", None)
    approval_binding = getattr(approval, "accepted_generation_binding", None) if approval is not None else None
    pending_generation_id = str(getattr(pending_plan, "accepted_generation_id", "") or "")
    item_generation_id = str(getattr(item, "accepted_generation_id", "") or "")
    approval_generation_id = str(getattr(approval, "accepted_generation_id", "") or "") if approval is not None else ""
    pending_business_date = str(getattr(pending_plan, "accepted_generation_business_date", "") or "")
    item_business_date = str(getattr(item, "accepted_generation_business_date", "") or "")
    approval_business_date = str(getattr(approval, "accepted_generation_business_date", "") or "") if approval is not None else ""
    statuses = {
        "pending": str(getattr(pending_plan, "accepted_generation_binding_status", "") or ""),
        "item": str(getattr(item, "accepted_generation_binding_status", "") or ""),
        "approval": str(getattr(approval, "accepted_generation_binding_status", "") or "") if approval is not None else "",
    }
    ids = [value for value in (pending_generation_id, item_generation_id, approval_generation_id) if value]
    dates = [value for value in (pending_business_date, item_business_date, approval_business_date) if value]
    fallback_flags = _generation_fallback_flags(pending_binding, item_binding, approval_binding)
    historical_separation = _historical_evaluation_authority_separation_evidence(
        pending_binding=pending_binding,
        item_binding=item_binding,
        approval_binding=approval_binding,
        business_date=business_date,
        mode=mode,
    )
    reasons: list[str] = []
    if not pending_generation_id or not item_generation_id or not approval_generation_id:
        reasons.append("accepted_generation_binding_missing")
    if len(set(ids)) > 1:
        reasons.append("accepted_generation_id_mismatch")
    if (len(set(dates)) > 1 or any(date and date != business_date for date in dates)) and historical_separation["status"] != "PASS":
        reasons.append("accepted_generation_business_date_mismatch")
    for source, status in statuses.items():
        if status and status != "PASS":
            reasons.append(f"{source}_accepted_generation_binding_not_pass")
    if any(fallback_flags.values()):
        reasons.append("accepted_generation_old_path_fallback_flag")
    sell_not_required = side == "SELL" and (
        "accepted_generation_binding_missing" in reasons
        or str(statuses.get("item") or "") in {"", "NOT_REQUIRED"}
    )
    status = "PASS" if not reasons or sell_not_required else "BLOCKED"
    return {
        "submit_generation_binding_status": status,
        "submit_generation_binding_reason": (
            "SELL_NOT_REQUIRED"
            if sell_not_required
            else "" if status == "PASS" else ",".join(sorted(set(reasons)))
        ),
        "submit_generation_binding_source": "pending_plan.accepted_generation_binding",
        "planning_generation_id": item_generation_id,
        "pending_generation_id": pending_generation_id,
        "approval_generation_id": approval_generation_id,
        "submit_generation_id": pending_generation_id,
        "pending_generation_business_date": pending_business_date,
        "approval_generation_business_date": approval_business_date,
        "item_generation_business_date": item_business_date,
        "requested_business_date": business_date,
        "runtime_mode": mode,
        "accepted_generation_pending_binding": dict(pending_binding or {}) if isinstance(pending_binding, Mapping) else {},
        "accepted_generation_item_binding": dict(item_binding or {}) if isinstance(item_binding, Mapping) else {},
        "accepted_generation_approval_binding": dict(approval_binding or {}) if isinstance(approval_binding, Mapping) else {},
        "historical_evaluation_authority_separation": historical_separation,
        "accepted_generation_business_date_classification": "legacy_read_only_metadata_when_historical_evaluation_authority_separation_passes",
        "selected_business_date_classification": "legacy_read_only_metadata_when_historical_evaluation_authority_separation_passes",
        "business_date_conflict_classification": "legacy_read_only_metadata_not_active_submit_guard_when_historical_evaluation_authority_separation_passes",
        **fallback_flags,
    }


def _generation_fallback_flags(*bindings: Any) -> dict[str, bool]:
    keys = (
        "latest_fallback_used",
        "shared_state_fallback_used",
        "default_generation_used",
        "legacy_component_fallback_used",
        "promotion_candidate_fallback_used",
        "manual_model_path_used",
    )
    return {
        key: any(bool(binding.get(key)) for binding in bindings if isinstance(binding, Mapping))
        for key in keys
    }


def _historical_evaluation_authority_separation_evidence(
    *,
    pending_binding: Any,
    item_binding: Any,
    approval_binding: Any,
    business_date: str,
    mode: str,
) -> dict[str, Any]:
    bindings = {
        "pending": pending_binding,
        "item": item_binding,
        "approval": approval_binding,
    }
    reasons: list[str] = []
    if mode != "historical":
        reasons.append("runtime_mode_not_historical")
    for name, binding in bindings.items():
        if not isinstance(binding, Mapping):
            reasons.append(f"{name}_authority_context_missing")
    mapping_bindings = {name: binding for name, binding in bindings.items() if isinstance(binding, Mapping)}
    if len(mapping_bindings) != 3:
        return {
            "status": "NOT_APPLICABLE" if mode != "historical" else "REVIEW_REQUIRED",
            "reason": ",".join(sorted(set(reasons))) or "historical_authority_context_missing",
            "canonical_evaluation_authority": "evaluation_authority_time",
            "canonical_market_pit_authority": "market_as_of_business_date",
        }

    common_fields = (
        "accepted_generation_id",
        "aggregate_hash",
        "manifest_content_hash",
        "run_authority_hash",
        "temporal_authority_source",
        "temporal_authority_winner",
        "evaluation_authority_time",
        "market_as_of_business_date",
        "historical_evaluation_authority_path",
    )
    for field in common_fields:
        values = {str(binding.get(field) or "") for binding in mapping_bindings.values()}
        if "" in values:
            reasons.append(f"{field}_missing")
        if len(values) > 1:
            reasons.append(f"{field}_mismatch")

    for name, binding in mapping_bindings.items():
        if str(binding.get("generation_binding_status") or "") != "PASS":
            reasons.append(f"{name}_generation_binding_not_pass")
        if str(binding.get("temporal_binding_status") or "") != "PASS":
            reasons.append(f"{name}_temporal_binding_not_pass")
        if str(binding.get("requested_business_date") or "") != business_date:
            reasons.append(f"{name}_requested_business_date_mismatch")
        if str(binding.get("market_as_of_business_date") or "") != business_date:
            reasons.append(f"{name}_market_as_of_business_date_mismatch")
        if _bool_binding(binding.get("business_date_temporal_comparison_applied")) is not False:
            reasons.append(f"{name}_business_date_temporal_comparison_applied_invalid")
        if _bool_binding(binding.get("evaluation_authority_time_temporal_comparison_applied")) is not True:
            reasons.append(f"{name}_evaluation_authority_time_temporal_comparison_applied_invalid")
        if str(binding.get("historical_business_date_acceptance_comparison") or "") != "NOT_APPLIED_TO_ACCEPTED_GENERATION":
            reasons.append(f"{name}_historical_business_date_acceptance_comparison_invalid")
        if str(binding.get("temporal_authority_source") or "") != "evaluation_authority_time":
            reasons.append(f"{name}_temporal_authority_source_invalid")
        if str(binding.get("temporal_authority_winner") or "") != "run_start_fixed_accepted_generation":
            reasons.append(f"{name}_temporal_authority_winner_invalid")
        if _generation_fallback_flags(binding).values() and any(_generation_fallback_flags(binding).values()):
            reasons.append(f"{name}_old_path_fallback_flag")
        authority_context = binding.get("authority_context")
        if not isinstance(authority_context, Mapping):
            reasons.append(f"{name}_authority_context_missing")
            continue
        evaluation_authority = authority_context.get("evaluation_authority")
        market_authority = authority_context.get("market_as_of_authority")
        if not isinstance(evaluation_authority, Mapping):
            reasons.append(f"{name}_evaluation_authority_context_missing")
        else:
            if str(evaluation_authority.get("generation_id") or "") != str(binding.get("accepted_generation_id") or ""):
                reasons.append(f"{name}_authority_context_generation_id_mismatch")
            authority_time = str(evaluation_authority.get("authority_time") or evaluation_authority.get("fixed_at") or "")
            if authority_time != str(binding.get("evaluation_authority_time") or ""):
                reasons.append(f"{name}_authority_context_evaluation_time_mismatch")
        if not isinstance(market_authority, Mapping):
            reasons.append(f"{name}_market_as_of_authority_context_missing")
        elif str(market_authority.get("business_date") or "") != business_date:
            reasons.append(f"{name}_market_as_of_authority_business_date_mismatch")

    status = "PASS" if not reasons else "REVIEW_REQUIRED"
    first = next(iter(mapping_bindings.values()))
    return {
        "status": status,
        "reason": "" if status == "PASS" else ",".join(sorted(set(reasons))),
        "canonical_evaluation_authority": "evaluation_authority_time",
        "canonical_market_pit_authority": "market_as_of_business_date",
        "evaluation_authority_time": str(first.get("evaluation_authority_time") or ""),
        "market_as_of_business_date": str(first.get("market_as_of_business_date") or ""),
        "historical_evaluation_authority_path": str(first.get("historical_evaluation_authority_path") or ""),
        "run_authority_hash": str(first.get("run_authority_hash") or ""),
        "manifest_content_hash": str(first.get("manifest_content_hash") or ""),
        "aggregate_hash": str(first.get("aggregate_hash") or ""),
    }


def _bool_binding(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _sell_guard_evidence(
    *,
    evidence: dict[str, Any],
    policy: CapitalDeploymentPolicy,
    item: Any,
    broker_position_quantity: float | None,
    broker_available_quantity: float | None,
) -> dict[str, Any]:
    evidence["notional_guard_source"] = policy.sell_liquidation_policy
    evidence["quantity_guard_source"] = "current_owned_quantity_and_broker_available_quantity"
    evidence["broker_available_quantity_checked"] = evidence["broker_available_quantity_source"] in {
        "broker_readonly",
        "historical_simulated_broker_authority",
    }
    evidence["manual_review_required"] = evidence["broker_available_quantity_review_required"]
    if broker_position_quantity is None:
        evidence["sell_quantity_guard_status"] = "CURRENT_MISSING"
        return _blocked_guard_evidence(
            evidence=evidence,
            reason="sell current position quantity missing",
            violated_policy="sell_current_position_quantity",
            violated_policy_source="persistent_ledger/state.json",
            should_have_been_blocked_at_planning=True,
        )
    if float(item.quantity) > float(broker_position_quantity):
        evidence["sell_quantity_guard_status"] = "CURRENT_INSUFFICIENT"
        return _blocked_guard_evidence(
            evidence=evidence,
            reason="sell quantity exceeds Current quantity",
            violated_policy="sell_current_position_quantity",
            violated_policy_source="persistent_ledger/state.json",
            should_have_been_blocked_at_planning=True,
        )
    if broker_available_quantity is None:
        evidence["sell_quantity_guard_status"] = "BROKER_AVAILABLE_MISSING"
        return _blocked_guard_evidence(
            evidence=evidence,
            reason="sell broker available quantity missing",
            violated_policy="broker_available_quantity",
            violated_policy_source=evidence["broker_available_quantity_source"],
        )
    if not evidence["broker_available_quantity_checked"]:
        evidence["sell_quantity_guard_status"] = "BROKER_AVAILABLE_NOT_READONLY"
        return _blocked_guard_evidence(
            evidence=evidence,
            reason="sell broker available quantity not confirmed by Broker ReadOnly evidence",
            violated_policy="broker_available_quantity",
            violated_policy_source=evidence["broker_available_quantity_source"],
        )
    if float(item.quantity) > float(broker_available_quantity):
        evidence["sell_quantity_guard_status"] = "BROKER_AVAILABLE_INSUFFICIENT"
        return _blocked_guard_evidence(
            evidence=evidence,
            reason="sell quantity exceeds broker available quantity",
            violated_policy="broker_available_quantity",
            violated_policy_source=evidence["broker_available_quantity_source"],
        )
    if policy.max_sell_liquidation_amount is not None and float(item.estimated_amount) > policy.max_sell_liquidation_amount:
        evidence["sell_quantity_guard_status"] = "POLICY_NOTIONAL_BLOCKED"
        return _blocked_guard_evidence(
            evidence=evidence,
            reason="estimated amount exceeds max_sell_liquidation_amount",
            violated_policy="max_sell_liquidation_amount",
            violated_policy_source=policy.policy_source,
        )
    evidence["sell_quantity_guard_status"] = "PASS"
    return evidence


def _blocked_guard_evidence(
    *,
    evidence: dict[str, Any],
    reason: str,
    violated_policy: str,
    violated_policy_source: str,
    should_have_been_blocked_at_planning: bool = False,
) -> dict[str, Any]:
    typed_guard = normalize_review_result(
        producer=violated_policy or "runtime_v2_submit_guard",
        reason=reason,
        status="REVIEW_REQUIRED",
        source_payload=evidence,
        affected_item_ids=[str(evidence.get("pending_item_id") or "")]
        if str(evidence.get("pending_item_id") or "")
        else [],
    )
    typed_guard = _submit_item_typed_guard_overrides(
        typed_guard,
        evidence=evidence,
        violated_policy=violated_policy,
    )
    evidence.update(
        {
            "guard_decision": "BLOCKED",
            "guard_reason": reason,
            "manual_review_required": True,
            "submit_item_status": "REVIEW_REQUIRED",
            "violated_policy": violated_policy,
            "violated_policy_source": violated_policy_source,
            "should_have_been_blocked_at_planning": should_have_been_blocked_at_planning,
            "blocked_at_submit_reason": reason,
            "guard_class": typed_guard.get("guard_class"),
            "guard_code": typed_guard.get("guard_code"),
            "scope": typed_guard.get("scope"),
            "affected_side": typed_guard.get("affected_side"),
            "affected_item_ids": typed_guard.get("affected_item_ids"),
            "batch_blocking": typed_guard.get("batch_blocking"),
            "recoverability": typed_guard.get("recoverability"),
            "canonical_owner": typed_guard.get("canonical_owner"),
            "consumer_action": typed_guard.get("consumer_action"),
            "typed_guard": typed_guard,
        }
    )
    return evidence


def _submit_item_typed_guard_overrides(
    typed_guard: dict[str, Any],
    *,
    evidence: Mapping[str, Any],
    violated_policy: str,
) -> dict[str, Any]:
    guard = dict(typed_guard)
    side = str(evidence.get("side") or "").upper()
    pending_item_id = str(evidence.get("pending_item_id") or "")
    if side in {"BUY", "SELL"} and guard.get("affected_side") in {"", "NONE", None}:
        guard["affected_side"] = side
    if pending_item_id and not guard.get("affected_item_ids"):
        guard["affected_item_ids"] = [pending_item_id]
    if violated_policy in {
        "historical_corporate_action_symbol_quarantine",
        "corporate_action_adjustment_authority",
    }:
        if side in {"BUY", "SELL"}:
            guard["affected_side"] = side
        if pending_item_id:
            guard["affected_item_ids"] = [pending_item_id]
        guard["scope"] = "ITEM"
        guard["batch_blocking"] = False
        guard["consumer_action"] = "FAIL_CLOSED_REVIEW_ITEM_ALLOW_UNAFFECTED_ITEMS"
    return guard


def _blocked_result(
    *,
    reason: str,
    runtime_root: Path,
    pending_path: str = "",
    status: str = "BLOCKED",
    submit_guard_policy: dict[str, Any] | None = None,
    submit_policy_consistency: dict[str, Any] | None = None,
    pending_read_valid: bool = False,
    pending_classification: str = "",
    pending_active: bool | None = None,
    pending_plan_present: bool = False,
    pending_item_count: int = 0,
    no_action_reason: str = "",
    no_order_authority_status: str = "",
    no_order_authority_reason: str = "",
    no_order_authority_evidence: dict[str, Any] | None = None,
) -> SubmitPipelineResult:
    return SubmitPipelineResult(
        status=status,
        reason=reason,
        pending_plan_id="",
        pending_path=pending_path or str(runtime_root / "pending_order_plan" / "pending_order_plan.json"),
        orders_ledger_path=str(runtime_root / "persistent_ledger" / "orders.jsonl"),
        demo_submit_executed=False,
        submitted_count=0,
        accepted_count=0,
        rejected_count=0,
        unknown_count=0,
        blocked_count=0,
        pending_consumed=False,
        submitted_order_ids=(),
        ledger_order_record_ids=(),
        submitted_symbols=(),
        item_results=(),
        pending_read_valid=pending_read_valid,
        pending_classification=pending_classification,
        pending_active=pending_active,
        pending_plan_present=pending_plan_present,
        pending_item_count=pending_item_count,
        no_action_reason=no_action_reason,
        no_order_authority_status=no_order_authority_status,
        no_order_authority_reason=no_order_authority_reason,
        no_order_authority_evidence=no_order_authority_evidence or {},
        submit_action="BLOCKED",
        review_required=status == "REVIEW_REQUIRED",
        halt_required=status == "HALT",
        submit_guard_policy=submit_guard_policy or {},
        submit_policy_consistency=submit_policy_consistency or {},
        submit_guard_item_evidence=(),
    )


def _consume_reason(results: list[SubmitItemResult]) -> str:
    if any(result.unknown for result in results):
        return "runtime_v2 submit attempted with POST_SEND_UNKNOWN; automatic resubmit forbidden"
    if any(result.rejected or result.blocked for result in results):
        return "runtime_v2 submit attempted with partial failure; automatic resubmit forbidden"
    return "runtime_v2 submit accepted; automatic resubmit forbidden"


def _synthetic_order_id(command_id: str) -> str:
    return "sha256:" + hashlib.sha256(f"submitted:{command_id}".encode("utf-8")).hexdigest()


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value: datetime | None) -> str:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    reject_mode_rooted_runtime_root(root)


def _is_mode_rooted_runtime_path(path: Path) -> bool:
    return is_mode_rooted_runtime_root(path)


def _load_broker_settings() -> Any:
    module_name = "ai_fund_lab_v2." + "broker.settings"
    return importlib.import_module(module_name).load_broker_settings()


def _build_tachibana_demo_submit_adapter(settings: Any) -> RuntimeV2SubmitAdapter:
    module_name = "ai_fund_lab_v2." + "broker.runtime_v2_demo_submit_adapter"
    adapter_cls = importlib.import_module(module_name).RuntimeV2TachibanaDemoSubmitAdapter
    return adapter_cls(settings=settings, dry_run=False)
