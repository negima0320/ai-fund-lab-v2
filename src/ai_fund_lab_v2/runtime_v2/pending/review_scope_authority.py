"""Canonical Pending review-scope authority.

This module owns Pending item-set and review-scope semantics only. It does not
compute cash, quantity, cap, broker, safety, or valuation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderPlan, PendingPlanState


CONTRACT_ID = "pending_review_scope_authority"
CONTRACT_VERSION = "phase30_ak9r27_v1"
BUY_ITEM_SCOPED_REVIEW = "BUY_ITEM_SCOPED_REVIEW"
TRUE_BATCH_CASH_FAILURE = "TRUE_BATCH_CASH_FAILURE"
REVIEWED_SELL_PRESENT = "REVIEWED_SELL_PRESENT"
MALFORMED_PENDING_SCOPE = "MALFORMED_PENDING_SCOPE"


@dataclass(frozen=True)
class PendingReviewScopeAuthority:
    contract_id: str
    contract_version: str
    source_pending_plan_id: str
    authority_provenance: dict[str, Any]
    structural_validity: str
    malformed_reasons: tuple[str, ...]
    lifecycle_state: str
    review_scope: str
    target_session_date: str
    plan_created_date: str
    executable_item_ids: tuple[str, ...]
    executable_buy_item_ids: tuple[str, ...]
    executable_sell_item_ids: tuple[str, ...]
    reviewed_item_ids: tuple[str, ...]
    reviewed_buy_item_ids: tuple[str, ...]
    reviewed_sell_item_ids: tuple[str, ...]
    terminal_item_ids: tuple[str, ...]
    expired_item_ids: tuple[str, ...]
    approved_review_sets_disjoint: bool
    batch_blocked: bool
    batch_block_reason: str
    partial_submit_allowed: bool
    sell_continuation_allowed: bool
    reviewed_items_must_not_submit: bool
    consumer_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "source_pending_plan_id": self.source_pending_plan_id,
            "authority_provenance": dict(self.authority_provenance),
            "structural_validity": self.structural_validity,
            "malformed_reasons": list(self.malformed_reasons),
            "lifecycle_state": self.lifecycle_state,
            "review_scope": self.review_scope,
            "target_session_date": self.target_session_date,
            "plan_created_date": self.plan_created_date,
            "executable_item_ids": list(self.executable_item_ids),
            "executable_buy_item_ids": list(self.executable_buy_item_ids),
            "executable_sell_item_ids": list(self.executable_sell_item_ids),
            "reviewed_item_ids": list(self.reviewed_item_ids),
            "reviewed_buy_item_ids": list(self.reviewed_buy_item_ids),
            "reviewed_sell_item_ids": list(self.reviewed_sell_item_ids),
            "terminal_item_ids": list(self.terminal_item_ids),
            "expired_item_ids": list(self.expired_item_ids),
            "approved_review_sets_disjoint": self.approved_review_sets_disjoint,
            "batch_blocked": self.batch_blocked,
            "batch_block_reason": self.batch_block_reason,
            "partial_submit_allowed": self.partial_submit_allowed,
            "sell_continuation_allowed": self.sell_continuation_allowed,
            "reviewed_items_must_not_submit": self.reviewed_items_must_not_submit,
            "consumer_notes": list(self.consumer_notes),
            "scope_narrow": True,
            "owns_cash_authority": False,
            "owns_quantity_authority": False,
            "owns_strategy_cap": False,
            "owns_safety_hard_cap": False,
            "owns_broker_feasibility": False,
            "owns_valuation": False,
        }


def build_pending_review_scope_authority(
    pending: PendingOrderPlan | Mapping[str, Any],
    *,
    slot_status: str = "",
    active_pending: bool | None = None,
) -> PendingReviewScopeAuthority:
    payload = _payload_from_pending(pending)
    state = str(slot_status or payload.get("state") or payload.get("status") or "").upper()
    if not state and isinstance(pending, PendingOrderPlan):
        state = pending.state.value
    if active_pending is None:
        active_pending = bool(payload.get("active_pending", state != "EMPTY"))
    plan_id = str(payload.get("pending_plan_id") or payload.get("order_plan_id") or "")
    items = tuple(item for item in payload.get("items") or () if isinstance(item, Mapping))
    item_ids = tuple(str(item.get("pending_item_id") or "") for item in items if str(item.get("pending_item_id") or ""))
    by_id = {str(item.get("pending_item_id") or ""): item for item in items if str(item.get("pending_item_id") or "")}

    approved_ids = _ids(payload.get("approved_item_ids"))
    approved_buy_ids = _ids(payload.get("approved_buy_item_ids"))
    approved_sell_ids = _ids(payload.get("approved_sell_item_ids"))
    reviewed_buy_ids = _ids(payload.get("review_required_buy_item_ids"))
    reviewed_sell_ids = _ids(payload.get("review_required_sell_item_ids"))
    reviewed_ids = _stable_unique(reviewed_buy_ids + reviewed_sell_ids)
    approved_review_disjoint = not bool(set(approved_ids) & set(reviewed_ids))

    malformed: list[str] = []
    if state and state != "EMPTY" and not plan_id:
        malformed.append("pending_plan_id_missing")
    if any(item_id not in item_ids for item_id in approved_ids + reviewed_ids):
        malformed.append("item_id_set_unknown")
    for item_id in approved_ids:
        item = by_id.get(item_id)
        if item and item.get("approved") is False:
            malformed.append("approved_item_flag_false")
        if item and str(item.get("state") or "").upper() not in {"CREATED", "APPROVED", "PASS", "READY", "CONSUMED"}:
            malformed.append("approved_item_state_invalid")
    for item_id in reviewed_ids:
        item = by_id.get(item_id)
        if item and item.get("approved") is True:
            malformed.append("reviewed_item_flag_true")
        if item and str(item.get("state") or "").upper() != "REVIEW_REQUIRED":
            malformed.append("reviewed_item_state_invalid")
    if set(approved_buy_ids) & set(reviewed_buy_ids):
        malformed.append("approved_buy_review_overlap")
    if set(approved_sell_ids) & set(reviewed_sell_ids):
        malformed.append("approved_sell_review_overlap")
    if not approved_review_disjoint:
        malformed.append("approved_review_overlap")
    if reviewed_sell_ids:
        batch_block_reason = REVIEWED_SELL_PRESENT
    else:
        batch_block_reason = _batch_block_reason(payload)
    feasibility_by_id = _feasibility_by_id(payload.get("planning_submit_feasibility"))
    executable_ids: list[str] = []
    if state == PendingPlanState.APPROVED.value:
        executable_ids = [item_id for item_id in approved_ids if item_id in by_id]
    elif (
        state == PendingPlanState.REVIEW_REQUIRED.value
        and str(payload.get("review_scope") or "") == BUY_ITEM_SCOPED_REVIEW
        and approved_review_disjoint
        and not reviewed_sell_ids
        and batch_block_reason == ""
    ):
        executable_ids = [
            item_id
            for item_id in approved_ids
            if item_id in by_id and _feasibility_pass_or_absent(feasibility_by_id, item_id)
        ]
    terminal_ids = tuple(
        item_id
        for item_id, item in by_id.items()
        if str(item.get("state") or "").upper() in {"CONSUMED", "EXPIRED", "CANCELLED", "SUPERSEDED"}
    )
    expired_ids = tuple(
        item_id for item_id, item in by_id.items() if str(item.get("state") or "").upper() == "EXPIRED"
    )
    executable_ids = _stable_unique(tuple(executable_ids))
    executable_buy_ids = tuple(item_id for item_id in executable_ids if str(by_id.get(item_id, {}).get("side") or "").upper() == "BUY")
    executable_sell_ids = tuple(item_id for item_id in executable_ids if str(by_id.get(item_id, {}).get("side") or "").upper() == "SELL")
    structural_validity = "PASS" if not malformed else "REVIEW_REQUIRED"
    partial_submit_allowed = bool(
        structural_validity == "PASS"
        and state == PendingPlanState.REVIEW_REQUIRED.value
        and str(payload.get("review_scope") or "") == BUY_ITEM_SCOPED_REVIEW
        and bool(executable_ids)
        and bool(reviewed_buy_ids)
        and not reviewed_sell_ids
        and approved_review_disjoint
        and batch_block_reason == ""
    )
    sell_continuation_allowed = bool(
        payload.get("sell_continuation_allowed")
        and str(payload.get("review_scope") or "") == BUY_ITEM_SCOPED_REVIEW
        and not reviewed_sell_ids
        and approved_review_disjoint
        and batch_block_reason == ""
    )
    batch_blocked = bool(structural_validity != "PASS" or reviewed_sell_ids or batch_block_reason)
    if structural_validity != "PASS" and not batch_block_reason:
        batch_block_reason = MALFORMED_PENDING_SCOPE
    return PendingReviewScopeAuthority(
        contract_id=CONTRACT_ID,
        contract_version=CONTRACT_VERSION,
        source_pending_plan_id=plan_id,
        authority_provenance={
            "producer": "pending_review_scope_authority",
            "source_review_scope": str(payload.get("review_scope") or ""),
            "source_review_scope_source": str(payload.get("review_scope_source") or ""),
            "active_pending": bool(active_pending),
        },
        structural_validity=structural_validity,
        malformed_reasons=tuple(sorted(set(malformed))),
        lifecycle_state=state,
        review_scope=str(payload.get("review_scope") or ""),
        target_session_date=str(payload.get("target_session_date") or ""),
        plan_created_date=str(payload.get("plan_created_date") or ""),
        executable_item_ids=executable_ids,
        executable_buy_item_ids=executable_buy_ids,
        executable_sell_item_ids=executable_sell_ids,
        reviewed_item_ids=reviewed_ids,
        reviewed_buy_item_ids=reviewed_buy_ids,
        reviewed_sell_item_ids=reviewed_sell_ids,
        terminal_item_ids=terminal_ids,
        expired_item_ids=expired_ids,
        approved_review_sets_disjoint=approved_review_disjoint,
        batch_blocked=batch_blocked,
        batch_block_reason=batch_block_reason,
        partial_submit_allowed=partial_submit_allowed,
        sell_continuation_allowed=sell_continuation_allowed,
        reviewed_items_must_not_submit=bool(reviewed_ids),
    )


def pending_scope_allows_partial_submit(authority: PendingReviewScopeAuthority) -> bool:
    return bool(authority.partial_submit_allowed and authority.executable_item_ids and not authority.batch_blocked)


def pending_scope_allows_sell_continuation(
    authority: PendingReviewScopeAuthority,
    *,
    business_date: str,
    mode: str,
    environment: str,
    readiness_scope: str,
) -> bool:
    if readiness_scope not in {"sell_planning", "submit"}:
        return False
    if mode and environment and environment != mode:
        return False
    return bool(
        authority.lifecycle_state == PendingPlanState.REVIEW_REQUIRED.value
        and authority.review_scope == BUY_ITEM_SCOPED_REVIEW
        and authority.target_session_date == business_date
        and authority.sell_continuation_allowed
        and authority.reviewed_buy_item_ids
        and not authority.reviewed_sell_item_ids
        and not authority.batch_blocked
    )


def pending_scope_allows_current_valuation_residual(
    authority: PendingReviewScopeAuthority,
    *,
    business_date: str,
    mode: str,
    environment: str,
) -> bool:
    if mode and environment and environment != mode:
        return False
    return bool(
        authority.lifecycle_state == PendingPlanState.REVIEW_REQUIRED.value
        and authority.review_scope == BUY_ITEM_SCOPED_REVIEW
        and authority.target_session_date == business_date
        and authority.reviewed_buy_item_ids
        and not authority.reviewed_sell_item_ids
        and not authority.batch_blocked
    )


def pending_scope_no_submission_terminal_authority(authority: PendingReviewScopeAuthority) -> bool:
    return bool(
        authority.lifecycle_state == PendingPlanState.REVIEW_REQUIRED.value
        and authority.review_scope == BUY_ITEM_SCOPED_REVIEW
        and authority.reviewed_buy_item_ids
        and not authority.executable_item_ids
        and not authority.reviewed_sell_item_ids
        and not authority.batch_blocked
    )


def _payload_from_pending(pending: PendingOrderPlan | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(pending, PendingOrderPlan):
        return {
            "pending_plan_id": pending.pending_plan_id,
            "state": pending.state.value,
            "environment": pending.environment,
            "plan_created_date": pending.plan_created_date,
            "target_session_date": pending.target_session_date,
            "approved_item_ids": list(pending.approved_item_ids),
            "approved_buy_item_ids": list(pending.approved_buy_item_ids),
            "approved_sell_item_ids": list(pending.approved_sell_item_ids),
            "review_required_buy_item_ids": list(pending.review_required_buy_item_ids),
            "review_required_sell_item_ids": list(pending.review_required_sell_item_ids),
            "review_scope": pending.review_scope,
            "review_scope_source": pending.review_scope_source,
            "review_scope_reason": pending.review_scope_reason,
            "sell_continuation_allowed": pending.sell_continuation_allowed,
            "planning_submit_feasibility": pending.planning_submit_feasibility or {},
            "items": [
                {
                    "pending_item_id": item.pending_item_id,
                    "side": item.side,
                    "state": item.state,
                    "approved": item.approved,
                    "batch_submit_status": item.batch_submit_status,
                }
                for item in pending.items
            ],
        }
    return dict(pending)


def _ids(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in value or () if str(item))


def _stable_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return tuple(out)


def _feasibility_by_id(feasibility: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(feasibility, Mapping):
        return {}
    return {
        str(item.get("pending_item_id") or ""): item
        for item in feasibility.get("items") or ()
        if isinstance(item, Mapping) and str(item.get("pending_item_id") or "")
    }


def _feasibility_pass_or_absent(feasibility_by_id: dict[str, Mapping[str, Any]], item_id: str) -> bool:
    item = feasibility_by_id.get(item_id)
    return item is None or str(item.get("status") or "") == "PASS"


def _batch_block_reason(payload: Mapping[str, Any]) -> str:
    feasibility = payload.get("planning_submit_feasibility")
    if not isinstance(feasibility, Mapping):
        return ""
    reviewed_ids = set(_ids(payload.get("review_required_buy_item_ids")) + _ids(payload.get("review_required_sell_item_ids")))
    for item in feasibility.get("items") or ():
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("pending_item_id") or "")
        if item_id not in reviewed_ids:
            continue
        violated_policy = str(item.get("violated_policy") or "")
        if violated_policy == "aggregate_cash":
            return TRUE_BATCH_CASH_FAILURE
        if not violated_policy or violated_policy.endswith("_missing") or not str(item.get("violated_policy_source") or ""):
            return "AUTHORITY_UNKNOWN_REVIEW"
    return ""
