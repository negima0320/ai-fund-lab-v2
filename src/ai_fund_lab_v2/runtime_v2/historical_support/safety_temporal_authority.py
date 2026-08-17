"""Historical Safety temporal authority.

This module owns the shared Historical Safety / temporal binding semantics
used by Runtime Data Readiness consumers.  It consumes the canonical Pending
review-scope authority and deliberately avoids cash, quantity, Strategy, PM,
PC, PS, broker, and valuation decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    build_pending_review_scope_authority,
    pending_scope_allows_current_valuation_residual,
    pending_scope_allows_sell_continuation,
)
from ai_fund_lab_v2.runtime_v2.pending.safety_authority import (
    HISTORICAL_NEUTRAL_SAFETY_AUTHORITY,
    HISTORICAL_NEUTRAL_SAFETY_DECISIONS,
    HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
    HISTORICAL_NEUTRAL_SAFETY_SOURCE,
)


CONTRACT_ID = "historical_safety_temporal_authority"
CONTRACT_VERSION = "phase30_ak9r28_v1"
HISTORICAL_DAILY_NEUTRAL_SAFETY_AUTHORITY_TYPE = "HISTORICAL_DAILY_NEUTRAL"
HISTORICAL_PENDING_SAFETY_AUTHORITY_TYPE = "HISTORICAL_PENDING_SAFETY_CONTEXT"


@dataclass(frozen=True)
class HistoricalSafetyTemporalAuthorityResult:
    """Canonical shared Historical Safety temporal authority result."""

    status: str
    reason: str
    business_date: str
    target_session_date: str
    safety_business_date: str
    pending_review_scope_contract_id: str
    pending_scope_compatible: bool
    historical_safety_status: str
    temporal_status: str
    malformed_reasons: tuple[str, ...]
    mismatch_fields: tuple[str, ...]
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": CONTRACT_ID,
            "contract_version": CONTRACT_VERSION,
            "authority_status": self.status,
            "authority_reason": self.reason,
            "business_date": self.business_date,
            "target_session_date": self.target_session_date,
            "safety_business_date": self.safety_business_date,
            "pending_review_scope_contract_id": self.pending_review_scope_contract_id,
            "pending_scope_compatible": self.pending_scope_compatible,
            "historical_safety_status": self.historical_safety_status,
            "temporal_status": self.temporal_status,
            "malformed_reasons": list(self.malformed_reasons),
            "mismatch_fields": list(self.mismatch_fields),
            **dict(self.payload),
        }


def evaluate_historical_daily_neutral_safety_authority(
    *,
    business_date: str,
    mode: str,
    broker_environment: str,
    current_payload: dict[str, Any],
    pending_payload: dict[str, Any],
    readiness_scope: str,
    runtime_test_run_id: str,
    runtime_test_profile_id: str,
    runtime_test_evidence_root: str,
    broker_write: bool,
    external_delivery: bool,
    previous_empty_pending_present: bool,
) -> dict[str, Any]:
    del current_payload
    mismatched: list[str] = []
    missing: list[str] = []
    if mode != "historical":
        mismatched.append("runtime_mode")
    if broker_environment != "historical_simulated":
        mismatched.append("broker_environment")
    if broker_write:
        mismatched.append("broker_write")
    if external_delivery:
        mismatched.append("external_delivery")
    if not runtime_test_run_id:
        missing.append("runtime_test_run_id")
    if not runtime_test_profile_id:
        missing.append("runtime_test_profile_id")
    if not runtime_test_evidence_root:
        missing.append("runtime_test_evidence_root")

    pending_compatibility = pending_allows_daily_neutral_safety(
        pending_payload=pending_payload,
        business_date=business_date,
        readiness_scope=readiness_scope,
    )
    if not pending_compatibility:
        mismatched.append("pending_lifecycle_state")

    pending_retry = same_day_failed_attempt_pending_retry_ineligible(
        pending_payload=pending_payload,
        business_date=business_date,
    )
    status = "READY" if not mismatched and not missing else "REVIEW_REQUIRED"
    reason = (
        "historical_daily_neutral_safety_authority_ready"
        if status == "READY"
        else "historical_daily_neutral_safety_authority_not_available"
    )
    result = HistoricalSafetyTemporalAuthorityResult(
        status=status,
        reason=reason,
        business_date=business_date,
        target_session_date=_target_session_date(pending_payload),
        safety_business_date=business_date,
        pending_review_scope_contract_id=_pending_review_scope_contract_id(pending_payload),
        pending_scope_compatible=pending_compatibility,
        historical_safety_status=status,
        temporal_status="PASS" if not mismatched else "REVIEW_REQUIRED",
        malformed_reasons=(),
        mismatch_fields=tuple(sorted(set(mismatched))),
        payload={
            "missing_evidence": missing,
            "stale_artifacts": [],
            "mismatched_fields": sorted(set(mismatched)),
            "safety_authority_type": HISTORICAL_DAILY_NEUTRAL_SAFETY_AUTHORITY_TYPE,
            "safety_authority_business_date": business_date,
            "safety_authority_source": HISTORICAL_NEUTRAL_SAFETY_SOURCE,
            "safety_authority_policy_version": HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
            "safety_authority": HISTORICAL_NEUTRAL_SAFETY_AUTHORITY,
            "safety_decision": "NEUTRAL",
            "safety_policy_version": HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
            "safety_source": HISTORICAL_NEUTRAL_SAFETY_SOURCE,
            "historical_neutral_authority_generated_or_resolved": status == "READY",
            "previous_empty_pending_present": previous_empty_pending_present,
            "previous_empty_pending_ignored_as_safety_authority": previous_empty_pending_present,
            "broker_write": bool(broker_write),
            "external_delivery": bool(external_delivery),
            "broker_environment": broker_environment,
            "runtime_test_run_id": runtime_test_run_id,
            "runtime_test_profile_id": runtime_test_profile_id,
            "runtime_test_evidence_root": runtime_test_evidence_root,
            "failed_attempt_pending_retry": pending_retry,
            "pending_artifact_retry_eligibility": pending_retry["pending_artifact_retry_eligibility"],
            "pending_artifact_authority_eligibility": pending_retry["pending_artifact_authority_eligibility"],
            "failed_attempt_artifact_quarantined": pending_retry["failed_attempt_artifact_quarantined"],
            "historical_neutral_safety_resolution_status": status,
            "historical_neutral_safety_resolution_reason": reason,
            "authority_provenance": {
                "producer": CONTRACT_ID,
                "contract_version": CONTRACT_VERSION,
                "pending_review_scope_contract_id": _pending_review_scope_contract_id(pending_payload),
            },
        },
    )
    output = result.to_dict()
    output["status"] = output.pop("authority_status")
    output["reason"] = output.pop("authority_reason")
    return output


def evaluate_historical_pending_safety_authority(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
    readiness_scope: str,
    runtime_test_run_id: str,
    runtime_test_profile_id: str,
    runtime_test_evidence_root: str,
) -> dict[str, Any]:
    payload = dict(pending_payload.get("payload") or {})
    safety_context = dict(payload.get("safety_context") or {})
    approval = dict(payload.get("approval") or {})
    state = _pending_state(pending_payload)
    active_pending = _active_pending(pending_payload, state=state)
    consumed = bool((payload.get("consume") or {}).get("consumed")) or state == "CONSUMED"
    target_session_date = str(payload.get("target_session_date") or "")
    no_action_terminal = bool(state == "EMPTY" and not active_pending and not (payload.get("items") or ()))
    consumed_prior_session = bool(consumed and target_session_date and target_session_date < business_date)
    expected_safety_business_date = target_session_date if consumed_prior_session else business_date
    pending_scope = build_pending_review_scope_authority(
        payload,
        slot_status=state,
        active_pending=active_pending,
    )
    mismatched: list[str] = []
    buy_item_scoped_sell_continuation = pending_scope_sell_continuation_adapter_ready(
        pending_payload=pending_payload,
        business_date=business_date,
        mode="historical",
        readiness_scope=readiness_scope,
    )
    post_submit_residual_buy_review_current_valuation = bool(
        readiness_scope == "current_valuation"
        and pending_scope_current_valuation_adapter_ready(
            pending_payload=pending_payload,
            business_date=business_date,
            mode="historical",
        )
    )
    pending_retry = same_day_failed_attempt_pending_retry_ineligible(
        pending_payload=pending_payload,
        business_date=business_date,
    )
    if historical_no_action_terminal_without_safety_binding_required(
        pending_payload=pending_payload,
        business_date=business_date,
        no_action_terminal=no_action_terminal,
        consumed=consumed,
        buy_item_scoped_sell_continuation=buy_item_scoped_sell_continuation,
        pending_retry=pending_retry,
    ):
        return {
            **_base_pending_authority_payload(
                status="READY",
                reason="historical_no_action_pending_safety_authority_ready",
                mismatched_fields=[],
                safety_context=safety_context,
                state=state,
                consumed=consumed,
                no_action_terminal=no_action_terminal,
                target_session_date=target_session_date,
                expected_safety_business_date=expected_safety_business_date,
                consumed_prior_session=consumed_prior_session,
                buy_item_scoped_sell_continuation=buy_item_scoped_sell_continuation,
                post_submit_residual_buy_review_current_valuation=post_submit_residual_buy_review_current_valuation,
                payload=payload,
                pending_retry=pending_retry,
                pending_scope_contract_id=pending_scope.contract_id,
                pending_scope_compatible=True,
            ),
            "empty_terminal_contract": "EMPTY_NO_ACTION_TERMINAL_NO_SAFETY_BINDING_REQUIRED",
        }

    if (
        state not in {"APPROVED", "CONSUMED"}
        and not consumed
        and not no_action_terminal
        and not buy_item_scoped_sell_continuation
        and not post_submit_residual_buy_review_current_valuation
        and not pending_retry["retry_input_ineligible"]
    ):
        mismatched.append("pending_lifecycle_state")

    expected = {
        "safety_authority": HISTORICAL_NEUTRAL_SAFETY_AUTHORITY,
        "safety_policy_version": HISTORICAL_NEUTRAL_SAFETY_POLICY_VERSION,
        "safety_source": HISTORICAL_NEUTRAL_SAFETY_SOURCE,
        "safety_business_date": expected_safety_business_date,
    }
    requires_decision_id = bool(
        (state == "APPROVED" and active_pending and not consumed)
        or buy_item_scoped_sell_continuation
        or post_submit_residual_buy_review_current_valuation
    )
    if requires_decision_id:
        expected["safety_decision_id"] = f"historical-neutral-safety:{expected_safety_business_date}"
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
    actual_decision = str(safety_context.get("safety_decision") or "").upper()
    if actual_decision not in HISTORICAL_NEUTRAL_SAFETY_DECISIONS:
        mismatched.append("safety_context.safety_decision")
    mismatched.extend(
        historical_pending_item_safety_mismatches(
            items=payload.get("items") or (),
            expected=expected,
            expected_safety_business_date=expected_safety_business_date,
            require_decision_id=requires_decision_id,
        )
    )
    if not consumed_prior_session and target_session_date != business_date:
        mismatched.append("target_session_date")
    if consumed_prior_session and target_session_date > business_date:
        mismatched.append("target_session_date")
    if str(payload.get("environment") or "") != "historical":
        mismatched.append("environment")
    if pending_scope.structural_validity != "PASS":
        mismatched.extend(f"pending_scope.{reason}" for reason in pending_scope.malformed_reasons)

    explicit_safety_id_present = bool(payload.get("safety_decision_id") or approval.get("safety_decision_id"))
    if explicit_safety_id_present and not mismatched:
        return {
            "status": "READY",
            "reason": "explicit_safety_decision_id_present",
            "mismatched_fields": [],
            "authority": str(safety_context.get("safety_authority") or ""),
            "contract_id": CONTRACT_ID,
            "contract_version": CONTRACT_VERSION,
            "pending_review_scope_contract_id": pending_scope.contract_id,
            "pending_scope_compatible": True,
            "authority_provenance": {"producer": CONTRACT_ID, "contract_version": CONTRACT_VERSION},
        }

    status = "READY" if not mismatched else "REVIEW_REQUIRED"
    reason = (
        "historical_consumed_pending_safety_authority_carry_forward"
        if status == "READY" and consumed_prior_session
        else "historical_no_action_pending_safety_authority_ready"
        if status == "READY" and no_action_terminal
        else "historical_post_submit_residual_buy_review_current_valuation_ready"
        if status == "READY" and post_submit_residual_buy_review_current_valuation
        else "historical_pending_safety_authority_ready"
        if status == "READY"
        else "historical_pending_safety_authority_mismatch"
    )
    return _base_pending_authority_payload(
        status=status,
        reason=reason,
        mismatched_fields=sorted(set(mismatched)),
        safety_context=safety_context,
        state=state,
        consumed=consumed,
        no_action_terminal=no_action_terminal,
        target_session_date=target_session_date,
        expected_safety_business_date=expected_safety_business_date,
        consumed_prior_session=consumed_prior_session,
        buy_item_scoped_sell_continuation=buy_item_scoped_sell_continuation,
        post_submit_residual_buy_review_current_valuation=post_submit_residual_buy_review_current_valuation,
        payload=payload,
        pending_retry=pending_retry,
        pending_scope_contract_id=pending_scope.contract_id,
        pending_scope_compatible=status == "READY",
    )


def pending_allows_daily_neutral_safety(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
    readiness_scope: str = "",
) -> bool:
    payload = dict(pending_payload.get("payload") or {})
    state = _pending_state(pending_payload)
    active_pending = _active_pending(pending_payload, state=state)
    items = payload.get("items") or ()
    target_session_date = str(payload.get("target_session_date") or "")
    consumed = bool((payload.get("consume") or {}).get("consumed")) or state == "CONSUMED"
    if pending_scope_sell_continuation_adapter_ready(
        pending_payload=pending_payload,
        business_date=business_date,
        mode="historical",
        readiness_scope=readiness_scope,
    ):
        return True
    if same_day_failed_attempt_pending_retry_ineligible(
        pending_payload=pending_payload,
        business_date=business_date,
    )["retry_input_ineligible"]:
        return True
    if state in {"APPROVED", "PENDING_APPROVAL", "SUBMITTED", "ACTIVE", "CONSUMED"} or active_pending or consumed:
        return False
    if state == "EMPTY" and not active_pending and not items:
        return not target_session_date or target_session_date <= business_date
    return False


def same_day_failed_attempt_pending_retry_ineligible(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
) -> dict[str, Any]:
    payload = dict(pending_payload.get("payload") or {})
    state = _pending_state(pending_payload)
    target_session_date = str(payload.get("target_session_date") or "")
    source_order_plan = dict(payload.get("source_order_plan") or {})
    source_order_plan_id = str(source_order_plan.get("order_plan_id") or "")
    source_order_plan_path = str(source_order_plan.get("path") or "")
    safety_context = payload.get("safety_context") if isinstance(payload.get("safety_context"), dict) else {}
    planning_context = (
        payload.get("planning_lineage_context")
        if isinstance(payload.get("planning_lineage_context"), dict)
        else {}
    )
    planning_authority_complete = bool(
        payload.get("planning_authority_hash")
        and payload.get("planning_authority_source")
        and payload.get("planning_authority_version")
    ) or bool(
        planning_context.get("planning_authority_hash")
        and planning_context.get("planning_authority_source")
        and planning_context.get("planning_authority_version")
    )
    safety_context_complete = bool(
        safety_context.get("safety_authority")
        and safety_context.get("safety_decision")
        and safety_context.get("safety_policy_version")
        and safety_context.get("safety_source")
        and safety_context.get("safety_business_date")
    )
    items = payload.get("items") or ()
    review_scope = str(payload.get("review_scope") or "")
    sell_continuation_allowed = bool(payload.get("sell_continuation_allowed"))
    producer_matches_retry_target = bool(
        target_session_date == business_date
        and (
            source_order_plan_id == f"strategy-review-{business_date}"
            or f"/strategy_planning/{business_date}/" in source_order_plan_path
            or f"strategy_planning/{business_date}/" in source_order_plan_path
        )
    )
    empty_unscoped_same_day_strategy_attempt = bool(
        state in {"BLOCKED", "REVIEW_REQUIRED"}
        and target_session_date == business_date
        and not items
        and producer_matches_retry_target
        and review_scope != "BUY_ITEM_SCOPED_REVIEW"
        and not sell_continuation_allowed
    )
    incomplete_blocked_failed_attempt = bool(
        state == "BLOCKED"
        and empty_unscoped_same_day_strategy_attempt
        and not safety_context_complete
        and not planning_authority_complete
    )
    review_required_empty_unscoped_failed_attempt = bool(
        state == "REVIEW_REQUIRED"
        and empty_unscoped_same_day_strategy_attempt
        and (
            source_order_plan_id.startswith("strategy-plan-")
            or source_order_plan_id == f"strategy-review-{business_date}"
        )
    )
    retry_input_ineligible = bool(incomplete_blocked_failed_attempt or review_required_empty_unscoped_failed_attempt)
    reason = (
        "failed_attempt_pending_retry_input_ineligible"
        if retry_input_ineligible
        else "pending_retry_input_eligible_or_not_failed_attempt"
    )
    return {
        "pending_artifact_present": bool(payload),
        "pending_artifact_producer_business_date": business_date if producer_matches_retry_target else "",
        "pending_artifact_producer_job": "morning" if producer_matches_retry_target else "",
        "pending_artifact_producer_attempt_id": str(payload.get("producer_attempt_id") or ""),
        "pending_artifact_attempt_status": state,
        "pending_artifact_commit_status": "NOT_COMMITTED" if retry_input_ineligible else "",
        "pending_artifact_retry_eligibility": "RETRY_INPUT_INELIGIBLE"
        if retry_input_ineligible
        else "NOT_CLASSIFIED_INELIGIBLE",
        "pending_artifact_authority_eligibility": "AUTHORITY_INELIGIBLE"
        if retry_input_ineligible
        else "AUTHORITY_ELIGIBILITY_NOT_OVERRIDDEN",
        "pending_restore_performed": False,
        "pending_restore_source": "",
        "pending_restore_before_hash": "",
        "pending_restore_after_hash": "",
        "failed_attempt_artifact_quarantined": retry_input_ineligible,
        "reason": reason,
        "retry_input_ineligible": retry_input_ineligible,
        "safety_context_complete": safety_context_complete,
        "planning_authority_complete": planning_authority_complete,
        "source_order_plan_id": source_order_plan_id,
        "source_order_plan_path": source_order_plan_path,
        "review_scope": review_scope,
        "sell_continuation_allowed": sell_continuation_allowed,
        "empty_unscoped_same_day_strategy_attempt": empty_unscoped_same_day_strategy_attempt,
        "incomplete_blocked_failed_attempt": incomplete_blocked_failed_attempt,
        "review_required_empty_unscoped_failed_attempt": review_required_empty_unscoped_failed_attempt,
    }


def historical_no_action_terminal_without_safety_binding_required(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
    no_action_terminal: bool,
    consumed: bool,
    buy_item_scoped_sell_continuation: bool,
    pending_retry: dict[str, Any],
) -> bool:
    payload = dict(pending_payload.get("payload") or {})
    state = _pending_state(pending_payload)
    active_pending = _active_pending(pending_payload, state=state)
    if not no_action_terminal or active_pending or consumed:
        return False
    if buy_item_scoped_sell_continuation or bool(payload.get("sell_continuation_allowed")):
        return False
    if pending_retry["retry_input_ineligible"]:
        return False
    if pending_retry["incomplete_blocked_failed_attempt"] or pending_retry["review_required_empty_unscoped_failed_attempt"]:
        return False
    return pending_allows_daily_neutral_safety(
        pending_payload=pending_payload,
        business_date=business_date,
        readiness_scope="",
    )


def pending_scope_sell_continuation_adapter_ready(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
    mode: str,
    readiness_scope: str = "",
) -> bool:
    payload = dict(pending_payload.get("payload") or {})
    state = _pending_state(pending_payload)
    authority = build_pending_review_scope_authority(
        payload,
        slot_status=state,
        active_pending=_active_pending(pending_payload, state=state),
    )
    return pending_scope_allows_sell_continuation(
        authority,
        business_date=business_date,
        mode=mode,
        environment=str(payload.get("environment") or ""),
        readiness_scope=readiness_scope,
    )


def pending_scope_current_valuation_adapter_ready(
    *,
    pending_payload: dict[str, Any],
    business_date: str,
    mode: str,
) -> bool:
    payload = dict(pending_payload.get("payload") or {})
    state = _pending_state(pending_payload)
    authority = build_pending_review_scope_authority(
        payload,
        slot_status=state,
        active_pending=_active_pending(pending_payload, state=state),
    )
    if not pending_scope_allows_current_valuation_residual(
        authority,
        business_date=business_date,
        mode=mode,
        environment=str(payload.get("environment") or ""),
    ):
        return False
    item_payloads = tuple(item for item in payload.get("items") or () if isinstance(item, dict))
    by_id = {str(item.get("pending_item_id") or ""): item for item in item_payloads}
    for item_id in authority.executable_buy_item_ids + authority.executable_sell_item_ids:
        item = by_id.get(item_id)
        if not item or str(item.get("state") or "").upper() != "CONSUMED":
            return False
    for item_id in authority.reviewed_buy_item_ids:
        item = by_id.get(item_id)
        if not item or str(item.get("state") or "").upper() != "REVIEW_REQUIRED":
            return False
        if item.get("approved") is True:
            return False
        if str(item.get("batch_submit_status") or "") != "ITEM_REVIEW_REQUIRED":
            return False
    return True


def historical_pending_item_safety_mismatches(
    *,
    items: Any,
    expected: dict[str, str],
    expected_safety_business_date: str,
    require_decision_id: bool,
) -> list[str]:
    mismatched: list[str] = []
    if not isinstance(items, list):
        return mismatched
    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            mismatched.append(f"items[{index}]")
            continue
        item = dict(raw_item)
        expected_fields = dict(expected)
        expected_fields["temporal_authority_business_date"] = expected_safety_business_date
        if require_decision_id:
            expected_fields["safety_decision_id"] = f"historical-neutral-safety:{expected_safety_business_date}"
        for field, expected_value in expected_fields.items():
            actual = str(item.get(field) or "")
            if actual != str(expected_value):
                mismatched.append(f"items[{index}].{field}")
        actual_decision = str(item.get("safety_decision") or "").upper()
        if actual_decision not in HISTORICAL_NEUTRAL_SAFETY_DECISIONS:
            mismatched.append(f"items[{index}].safety_decision")
    return mismatched


def _base_pending_authority_payload(
    *,
    status: str,
    reason: str,
    mismatched_fields: list[str],
    safety_context: dict[str, Any],
    state: str,
    consumed: bool,
    no_action_terminal: bool,
    target_session_date: str,
    expected_safety_business_date: str,
    consumed_prior_session: bool,
    buy_item_scoped_sell_continuation: bool,
    post_submit_residual_buy_review_current_valuation: bool,
    payload: dict[str, Any],
    pending_retry: dict[str, Any],
    pending_scope_contract_id: str,
    pending_scope_compatible: bool,
) -> dict[str, Any]:
    result = HistoricalSafetyTemporalAuthorityResult(
        status=status,
        reason=reason,
        business_date=expected_safety_business_date,
        target_session_date=target_session_date,
        safety_business_date=expected_safety_business_date,
        pending_review_scope_contract_id=pending_scope_contract_id,
        pending_scope_compatible=pending_scope_compatible,
        historical_safety_status=status,
        temporal_status="PASS" if not mismatched_fields else "REVIEW_REQUIRED",
        malformed_reasons=(),
        mismatch_fields=tuple(mismatched_fields),
        payload={
            "mismatched_fields": list(mismatched_fields),
            "authority": str(safety_context.get("safety_authority") or ""),
            "pending_lifecycle_state": state,
            "pending_consumed": consumed,
            "no_action_terminal": no_action_terminal,
            "target_session_date": target_session_date,
            "safety_business_date_expected": expected_safety_business_date,
            "consumed_prior_session_carry_forward": consumed_prior_session,
            "buy_item_scoped_sell_continuation_ready": buy_item_scoped_sell_continuation,
            "post_submit_residual_buy_review_current_valuation_ready": post_submit_residual_buy_review_current_valuation,
            "review_scope": str(payload.get("review_scope") or ""),
            "sell_continuation_allowed": bool(payload.get("sell_continuation_allowed")),
            "safety_context": safety_context,
            "failed_attempt_pending_retry": pending_retry,
            "authority_provenance": {
                "producer": CONTRACT_ID,
                "contract_version": CONTRACT_VERSION,
                "pending_review_scope_contract_id": pending_scope_contract_id,
                "pending_scope_compatible": pending_scope_compatible,
            },
        },
    )
    output = result.to_dict()
    output["status"] = output.pop("authority_status")
    output["reason"] = output.pop("authority_reason")
    return output


def _pending_state(pending_payload: dict[str, Any]) -> str:
    payload = dict(pending_payload.get("payload") or {})
    return str(pending_payload.get("slot_status") or payload.get("state") or payload.get("status") or "").upper()


def _active_pending(pending_payload: dict[str, Any], *, state: str) -> bool:
    payload = dict(pending_payload.get("payload") or {})
    return bool(pending_payload.get("active_pending", payload.get("active_pending", state != "EMPTY")))


def _target_session_date(pending_payload: dict[str, Any]) -> str:
    payload = dict(pending_payload.get("payload") or {})
    return str(payload.get("target_session_date") or "")


def _pending_review_scope_contract_id(pending_payload: dict[str, Any]) -> str:
    payload = dict(pending_payload.get("payload") or {})
    state = _pending_state(pending_payload)
    return build_pending_review_scope_authority(
        payload,
        slot_status=state,
        active_pending=_active_pending(pending_payload, state=state),
    ).contract_id
