"""Pending composition helpers for the single canonical Pending authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import (
    build_approval_artifact,
    build_approval_request,
    build_approved_order_conditions,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingOrderPlan, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    build_pending_review_scope_authority,
    pending_scope_allows_sell_continuation,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import RuntimeCurrentExposure


INACTIVE_PENDING_STATES = {
    PendingPlanState.CONSUMED,
    PendingPlanState.EMPTY,
    PendingPlanState.EXPIRED,
    PendingPlanState.CANCELLED,
    PendingPlanState.SUPERSEDED,
    PendingPlanState.REJECTED,
    PendingPlanState.SUBMITTED,
}

COMMITTED_SELL_PENDING_STATES = {
    PendingPlanState.SUBMITTING,
    PendingPlanState.SUBMITTED,
    PendingPlanState.POST_SEND_UNKNOWN,
}


@dataclass(frozen=True)
class SellPendingReconciliationResult:
    pending: PendingOrderPlan
    status: str
    reason: str
    review_required: bool
    existing_pending: PendingOrderPlan | None
    existing_pending_hash: str
    evidence: dict


def read_active_buy_pending(
    *,
    runtime_root: Path,
    environment: str,
    business_date: str,
    target_session_date: str,
) -> tuple[PendingOrderPlan | None, str]:
    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    read_result = read_pending_order_plan_path(path=path, environment=environment)
    if not read_result.valid or read_result.plan is None:
        return None, read_result.classification
    plan = read_result.plan
    if plan.state in INACTIVE_PENDING_STATES:
        return None, f"inactive_state:{plan.state.value}"
    if plan.consume.consumed:
        return None, "consumed"
    if plan.plan_created_date != business_date or plan.target_session_date != target_session_date:
        return None, "date_mismatch"
    approved_ids = set(plan.approved_item_ids)
    buy_items = tuple(
        item
        for item in plan.items
        if item.side.upper() == "BUY" and item.pending_item_id in approved_ids and item.quantity > 0
    )
    if not buy_items:
        return None, "active_buy_missing"
    return plan, "PASS"


def compose_with_existing_buy_pending(
    *,
    existing_buy_pending: PendingOrderPlan | None,
    pending: PendingOrderPlan,
    artifact_dir: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    reason: str,
    planning_submit_feasibility_current: RuntimeCurrentExposure | None = None,
    planning_submit_feasibility_policy: CapitalDeploymentPolicy | None = None,
    accepted_generation_binding: dict | None = None,
) -> tuple[PendingOrderPlan, Path, Path, dict]:
    if existing_buy_pending is None:
        return pending, Path(pending.source_order_plan.path), Path(pending.approval.approval_path if pending.approval else ""), {
            "composition_model": "SINGLE_PENDING_NO_EXISTING_BUY",
            "composition_status": "NOT_REQUIRED",
            "preserved_existing_buy_pending": False,
            "composite_pending": False,
        }
    existing_buy_items = tuple(item for item in existing_buy_pending.items if item.side.upper() == "BUY")
    composed_items = _dedupe_items(existing_buy_items + pending.items)
    order_plan_id = f"order-plan-pending-composite-{business_date}-{_short_items_hash(composed_items)}"
    order_plan_path = artifact_dir / "pending_composition_order_plan.json"
    approval_path = artifact_dir / "pending_composition_approval_artifact.json"
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": order_plan_id,
        "environment": environment,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "PASS",
        "composition_model": "COMPOSITE_PENDING_PLAN",
        "composition_reason": reason,
        "source_buy_pending_plan_id": existing_buy_pending.pending_plan_id,
        "source_buy_pending_path": "pending_order_plan/pending_order_plan.json",
        "source_sell_order_plan_id": pending.source_order_plan.order_plan_id,
        "source_sell_order_plan_path": pending.source_order_plan.path,
        "items": [asdict(item) for item in composed_items],
    }
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    composed = promote_order_plan_to_pending(
        order_plan_id=order_plan_id,
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=composed_items,
    )
    composed = _attach_accepted_generation_binding(
        pending=composed,
        accepted_generation_binding=accepted_generation_binding,
    )
    approved_item_ids = tuple(item.pending_item_id for item in composed.items)
    request = build_approval_request(
        pending_plan=composed,
        business_date=business_date,
        expires_at=f"{business_date}T15:00:00+09:00",
    )
    approval = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=approved_item_ids,
            rejected_item_ids=(),
            reason="runtime v2 pending composition approval",
            operator="runtime_v2_pending_composition_job",
            decided_at=f"{business_date}T08:46:00+09:00",
            approved_order_conditions=build_approved_order_conditions(
                pending_items=composed.items,
                target_session_date=target_session_date,
            ),
        ),
    )
    approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
    composed = link_approval_to_pending(
        pending_plan=composed,
        approval_artifact=approval,
        planning_submit_feasibility_current=planning_submit_feasibility_current,
        planning_submit_feasibility_policy=planning_submit_feasibility_policy,
    )
    evidence = {
        "composition_model": "COMPOSITE_PENDING_PLAN",
        "composition_status": "PASS",
        "preserved_existing_buy_pending": True,
        "composite_pending": True,
        "pre_sell_buy_pending_count": len(existing_buy_items),
        "preservable_buy_count": len(existing_buy_items),
        "sell_count": sum(1 for item in pending.items if item.side.upper() == "SELL"),
        "composed_buy_count": sum(1 for item in composed.items if item.side.upper() == "BUY"),
        "composed_sell_count": sum(1 for item in composed.items if item.side.upper() == "SELL"),
        "dropped_buy_count": 0,
        "final_canonical_pending_count": len(composed.items),
        "pending_source_lineage": {
            "source_buy_pending_plan_id": existing_buy_pending.pending_plan_id,
            "source_buy_pending_path": "pending_order_plan/pending_order_plan.json",
            "source_sell_pending_plan_id": pending.pending_plan_id,
            "source_sell_order_plan_path": pending.source_order_plan.path,
            "composition_authority": "runtime_v2_pending_composition",
        },
        "planning_submit_feasibility_status": (
            (composed.planning_submit_feasibility or {}).get("status")
            if composed.planning_submit_feasibility
            else ""
        ),
        "source_buy_pending_plan_id": existing_buy_pending.pending_plan_id,
        "source_sell_pending_plan_id": pending.pending_plan_id,
        "composed_buy_item_count": sum(1 for item in composed.items if item.side.upper() == "BUY"),
        "composed_sell_item_count": sum(1 for item in composed.items if item.side.upper() == "SELL"),
        "composed_item_count": len(composed.items),
        "duplicate_pending_items_removed": len(existing_buy_items) + len(pending.items) - len(composed.items),
    }
    return composed, order_plan_path, approval_path, evidence


def compose_with_buy_item_scoped_review_pending(
    *,
    existing_review_pending: PendingOrderPlan | None,
    pending: PendingOrderPlan,
    artifact_dir: Path,
    business_date: str,
    target_session_date: str,
    environment: str,
    reason: str,
    planning_submit_feasibility_current: RuntimeCurrentExposure | None = None,
    planning_submit_feasibility_policy: CapitalDeploymentPolicy | None = None,
    accepted_generation_binding: dict | None = None,
) -> tuple[PendingOrderPlan, Path, Path, dict]:
    if not is_buy_item_scoped_review_sell_continuation_pending(
        existing_review_pending,
        business_date=business_date,
        target_session_date=target_session_date,
    ):
        return pending, Path(pending.source_order_plan.path), Path(pending.approval.approval_path if pending.approval else ""), {
            "composition_model": "BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION",
            "composition_status": "NOT_ELIGIBLE",
            "preserved_buy_review_pending": False,
            "composite_pending": False,
        }
    assert existing_review_pending is not None
    sell_items = tuple(item for item in pending.items if item.side.upper() == "SELL" and float(item.quantity or 0.0) > 0)
    if not sell_items:
        return pending, Path(pending.source_order_plan.path), Path(pending.approval.approval_path if pending.approval else ""), {
            "composition_model": "BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION",
            "composition_status": "NO_SELL_ITEMS",
            "preserved_buy_review_pending": False,
            "composite_pending": False,
        }

    existing_buy_items = tuple(item for item in existing_review_pending.items if item.side.upper() == "BUY")
    composed_items = _dedupe_items(existing_buy_items + sell_items)
    order_plan_id = f"order-plan-buy-review-sell-continuation-{business_date}-{_short_items_hash(composed_items)}"
    order_plan_path = artifact_dir / "buy_review_sell_continuation_order_plan.json"
    approval_path = artifact_dir / "buy_review_sell_continuation_approval_artifact.json"
    order_plan_payload = {
        "schema_version": "1",
        "order_plan_id": order_plan_id,
        "environment": environment,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "status": "PASS",
        "composition_model": "BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_COMPOSITE_PENDING_PLAN",
        "composition_reason": reason,
        "source_buy_review_pending_plan_id": existing_review_pending.pending_plan_id,
        "source_buy_review_pending_path": "pending_order_plan/pending_order_plan.json",
        "source_sell_order_plan_id": pending.source_order_plan.order_plan_id,
        "source_sell_order_plan_path": pending.source_order_plan.path,
        "items": [asdict(item) for item in composed_items],
    }
    order_plan_path.write_text(_json_dumps(order_plan_payload), encoding="utf-8")
    composed = promote_order_plan_to_pending(
        order_plan_id=order_plan_id,
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=_hash(order_plan_path.read_text(encoding="utf-8")),
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=target_session_date,
        target_session_date=target_session_date,
        items=composed_items,
        submit_policy_context=pending.submit_policy_context,
    )
    composed = _attach_accepted_generation_binding(
        pending=composed,
        accepted_generation_binding=accepted_generation_binding,
    )
    approved_existing_buy_item_ids = tuple(
        item_id for item_id in existing_review_pending.approved_buy_item_ids if item_id
    )
    approved_sell_item_ids = tuple(item.pending_item_id for item in sell_items)
    approved_item_ids = tuple((*approved_existing_buy_item_ids, *approved_sell_item_ids))
    request = build_approval_request(
        pending_plan=composed,
        business_date=business_date,
        expires_at=f"{business_date}T15:00:00+09:00",
    )
    approval = build_approval_artifact(
        request=request,
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=approved_item_ids,
            rejected_item_ids=(),
            reason="runtime v2 buy item scoped review sell continuation approval",
            operator="runtime_v2_pending_composition_job",
            decided_at=f"{business_date}T08:46:00+09:00",
            approved_order_conditions=build_approved_order_conditions(
                pending_items=tuple(
                    item for item in composed.items if item.pending_item_id in set(approved_item_ids)
                ),
                target_session_date=target_session_date,
            ),
        ),
    )
    approval_path.write_text(_json_dumps(_jsonable(approval)), encoding="utf-8")
    linked = link_approval_to_pending(
        pending_plan=composed,
        approval_artifact=approval,
        planning_submit_feasibility_current=planning_submit_feasibility_current,
        planning_submit_feasibility_policy=planning_submit_feasibility_policy,
    )
    review_by_id = {item.pending_item_id: item for item in existing_buy_items}
    restored_items = tuple(
        review_by_id[item.pending_item_id]
        if item.pending_item_id in review_by_id
        else item
        for item in linked.items
    )
    linked_policy_context = dict(linked.policy_context or {})
    linked_policy_context["buy_item_scoped_review_sell_continuation"] = {
        "status": "PASS",
        "source_buy_review_pending_plan_id": existing_review_pending.pending_plan_id,
        "source_sell_pending_plan_id": pending.pending_plan_id,
        "approved_buy_item_ids": list(approved_existing_buy_item_ids),
        "approved_sell_item_ids": list(approved_sell_item_ids),
        "review_required_buy_item_ids": list(existing_review_pending.review_required_buy_item_ids),
        "buy_batch_atomicity_preserved": True,
        "partial_buy_approval_implemented": bool(approved_existing_buy_item_ids),
        "sell_lane_planning_submit_feasibility": linked.planning_submit_feasibility or {},
        "buy_review_planning_submit_feasibility": existing_review_pending.planning_submit_feasibility or {},
    }
    composed = replace(
        linked,
        state=PendingPlanState.REVIEW_REQUIRED,
        items=restored_items,
        policy_context=linked_policy_context,
        approved_item_ids=approved_item_ids,
        buy_items_status=existing_review_pending.buy_items_status or "REVIEW_REQUIRED",
        sell_items_status="APPROVED",
        plan_overall_status="APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW",
        approved_buy_item_ids=approved_existing_buy_item_ids,
        approved_sell_item_ids=approved_sell_item_ids,
        review_required_buy_item_ids=existing_review_pending.review_required_buy_item_ids,
        review_required_sell_item_ids=(),
        review_scope=existing_review_pending.review_scope,
        review_scope_source=existing_review_pending.review_scope_source,
        review_scope_reason=existing_review_pending.review_scope_reason,
        sell_continuation_allowed=True,
    )
    evidence = {
        "composition_model": "BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_COMPOSITE_PENDING_PLAN",
        "composition_status": "PASS",
        "preserved_buy_review_pending": True,
        "preserved_existing_buy_pending": True,
        "composite_pending": True,
        "pre_sell_buy_pending_count": len(existing_buy_items),
        "preservable_buy_count": len(approved_existing_buy_item_ids),
        "sell_count": len(sell_items),
        "composed_buy_count": sum(1 for item in composed.items if item.side.upper() == "BUY"),
        "composed_sell_count": sum(1 for item in composed.items if item.side.upper() == "SELL"),
        "dropped_buy_count": 0,
        "final_canonical_pending_count": len(composed.items),
        "pending_source_lineage": {
            "source_buy_review_pending_plan_id": existing_review_pending.pending_plan_id,
            "source_buy_review_pending_path": "pending_order_plan/pending_order_plan.json",
            "source_sell_pending_plan_id": pending.pending_plan_id,
            "source_sell_order_plan_path": pending.source_order_plan.path,
            "composition_authority": "runtime_v2_buy_item_scoped_review_sell_continuation_composition",
        },
        "approved_sell_item_ids": list(approved_sell_item_ids),
        "approved_buy_item_ids": list(approved_existing_buy_item_ids),
        "review_required_buy_item_ids": list(composed.review_required_buy_item_ids),
        "source_buy_review_pending_plan_id": existing_review_pending.pending_plan_id,
        "source_sell_pending_plan_id": pending.pending_plan_id,
        "composed_buy_item_count": sum(1 for item in composed.items if item.side.upper() == "BUY"),
        "composed_sell_item_count": sum(1 for item in composed.items if item.side.upper() == "SELL"),
        "composed_item_count": len(composed.items),
        "buy_batch_atomicity_preserved": True,
        "partial_buy_approval_implemented": bool(approved_existing_buy_item_ids),
    }
    return composed, order_plan_path, approval_path, evidence


def is_buy_item_scoped_review_sell_continuation_pending(
    plan: PendingOrderPlan | None,
    *,
    business_date: str,
    target_session_date: str,
) -> bool:
    if plan is None:
        return False
    authority = build_pending_review_scope_authority(plan)
    return bool(
        not plan.consume.consumed
        and plan.plan_created_date == business_date
        and plan.target_session_date == target_session_date
        and pending_scope_allows_sell_continuation(
            authority,
            business_date=business_date,
            mode="",
            environment=plan.environment,
            readiness_scope="sell_planning",
        )
    )


def reconcile_with_existing_sell_pending(
    *,
    runtime_root: Path,
    pending: PendingOrderPlan,
    business_date: str,
    target_session_date: str,
    environment: str,
    artifact_dir: Path,
) -> SellPendingReconciliationResult:
    """Classify active same-symbol SELL pending before writing a replacement.

    This is intentionally scoped to the single current pending slot. It does not
    introduce a new executable authority; it only decides whether the new SELL
    candidate can safely preserve, reconcile, or fail-closed against the current
    pending plan.
    """

    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    existing_hash = _file_hash(path) if path.is_file() else ""
    read_result = read_pending_order_plan_path(path=path, environment=environment)
    base_evidence = {
        "reconciliation_model": "EXISTING_PLAN_SELL_RECONCILIATION",
        "existing_pending_path": str(path),
        "existing_pending_hash": existing_hash,
        "business_date": business_date,
        "target_session_date": target_session_date,
        "new_item_ids": [item.pending_item_id for item in pending.items if item.side.upper() == "SELL"],
        "reason_codes": [],
        "review_required": False,
        "resume_safe": True,
        "no_signal_overwrite_prevented": False,
        "opposite_side_preserved": False,
    }
    if not read_result.valid or read_result.plan is None:
        evidence = {
            **base_evidence,
            "classification": read_result.classification,
            "resolution_action": "NO_EXISTING_VALID_PENDING",
            "reason_codes": ["PENDING_SELL_NO_EXISTING_ACTIVE_PENDING"],
        }
        _write_reconciliation_evidence(artifact_dir, evidence)
        return SellPendingReconciliationResult(pending, "PASS", "", False, None, existing_hash, evidence)

    existing = read_result.plan
    existing_sell_items = tuple(
        item
        for item in existing.items
        if item.side.upper() == "SELL" and float(item.quantity or 0.0) > 0
    )
    new_sell_items = tuple(
        item
        for item in pending.items
        if item.side.upper() == "SELL" and float(item.quantity or 0.0) > 0
    )
    existing_buy_count = sum(1 for item in existing.items if item.side.upper() == "BUY")
    evidence = {
        **base_evidence,
        "existing_pending_plan_id": existing.pending_plan_id,
        "existing_pending_state": existing.state.value,
        "existing_pending_item_ids": [item.pending_item_id for item in existing.items],
        "existing_sell_item_ids": [item.pending_item_id for item in existing_sell_items],
        "existing_buy_item_count": existing_buy_count,
        "existing_sell_item_count": len(existing_sell_items),
        "classifications": [],
        "authority_merge_events": [],
        "preserved_item_ids": [],
        "replaced_item_ids": [],
        "superseded_item_ids": [],
        "new_item_ids": [],
        "quantity_before": {},
        "quantity_after": {},
        "reason_codes": [],
        "opposite_side_preserved": existing_buy_count > 0,
    }
    if existing.state in {PendingPlanState.EMPTY, PendingPlanState.CONSUMED, PendingPlanState.EXPIRED, PendingPlanState.CANCELLED, PendingPlanState.SUPERSEDED, PendingPlanState.REJECTED}:
        evidence.update(
            {
                "classification": f"inactive_state:{existing.state.value}",
                "resolution_action": "NO_ACTIVE_SELL_RECONCILIATION_REQUIRED",
                "reason_codes": ["PENDING_SELL_NO_EXISTING_ACTIVE_PENDING"],
            }
        )
        _write_reconciliation_evidence(artifact_dir, evidence)
        return SellPendingReconciliationResult(pending, "PASS", "", False, existing, existing_hash, evidence)

    resolved_by_id: dict[str, PendingOrderItem] = {
        item.pending_item_id: item
        for item in existing_sell_items
        if not any(_same_symbol(item.symbol, new_item.symbol) for new_item in new_sell_items)
    }
    consumed_existing_ids: set[str] = set()
    review_reasons: list[str] = []

    for new_item in new_sell_items:
        matches = tuple(
            item
            for item in existing_sell_items
            if _same_symbol(item.symbol, new_item.symbol)
        )
        if not matches:
            resolved_by_id[new_item.pending_item_id] = new_item
            evidence["classifications"].append(_classification_payload("NO_EXISTING_SAME_SYMBOL_SELL", None, new_item, "ADD_NEW_SELL_ITEM"))
            evidence["new_item_ids"].append(new_item.pending_item_id)
            continue
        if len(matches) > 1:
            reason = "PENDING_SELL_CONFLICTING_INTENT_REVIEW"
            review_reasons.append(reason)
            evidence["classifications"].append(
                _classification_payload("SAME_SYMBOL_CONFLICTING_INTENT", matches[0], new_item, "REVIEW_REQUIRED", reason)
            )
            continue
        existing_item = matches[0]
        classification, action, reason = _classify_sell_pair(
            existing_plan=existing,
            existing_item=existing_item,
            new_item=new_item,
            business_date=business_date,
            target_session_date=target_session_date,
        )
        classification_payload = _classification_payload(classification, existing_item, new_item, action, reason)
        evidence["quantity_before"][existing_item.pending_item_id] = existing_item.quantity
        evidence["quantity_after"][new_item.pending_item_id] = new_item.quantity
        if action == "REVIEW_REQUIRED":
            evidence["classifications"].append(classification_payload)
            review_reasons.append(reason or "PENDING_SELL_IDENTITY_UNKNOWN")
            continue
        if action == "PRESERVE_EXISTING":
            merged_item, merge_status, merge_reason, merge_evidence = _merge_required_authority_for_preserved_sell_item(
                existing_plan=existing,
                existing_item=existing_item,
                new_item=new_item,
                business_date=business_date,
                target_session_date=target_session_date,
                existing_pending_hash=existing_hash,
            )
            classification_payload["required_authority_merge"] = merge_evidence
            evidence["authority_merge_events"].append(merge_evidence)
            evidence["classifications"].append(classification_payload)
            if merge_status == "REVIEW_REQUIRED":
                review_reasons.append(merge_reason or "PENDING_SELL_REQUIRED_AUTHORITY_REVIEW")
                continue
            resolved_by_id[existing_item.pending_item_id] = merged_item
            consumed_existing_ids.add(existing_item.pending_item_id)
            evidence["preserved_item_ids"].append(existing_item.pending_item_id)
            evidence["reason_codes"].append(reason)
            continue
        if action == "REPLACE_WITH_NEW":
            evidence["classifications"].append(classification_payload)
            resolved_by_id.pop(existing_item.pending_item_id, None)
            resolved_by_id[new_item.pending_item_id] = new_item
            consumed_existing_ids.add(existing_item.pending_item_id)
            evidence["replaced_item_ids"].append(new_item.pending_item_id)
            evidence["superseded_item_ids"].append(existing_item.pending_item_id)
            evidence["reason_codes"].append(reason)
            continue

    if review_reasons:
        reason_codes = tuple(dict.fromkeys(review_reasons + ["PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED"]))
        evidence.update(
            {
                "classification": "REVIEW_REQUIRED",
                "resolution_action": "ORIGINAL_PENDING_PRESERVED",
                "reason_codes": list(reason_codes),
                "review_required": True,
                "resume_safe": False,
                "no_signal_overwrite_prevented": True,
            }
        )
        _write_reconciliation_evidence(artifact_dir, evidence)
        return SellPendingReconciliationResult(
            pending,
            "REVIEW_REQUIRED",
            ";".join(reason_codes),
            True,
            existing,
            existing_hash,
            evidence,
        )

    existing_buy_items = tuple(item for item in existing.items if item.side.upper() == "BUY")
    resolved_sell_items = tuple(resolved_by_id.values())
    resolved_items = _dedupe_items(resolved_sell_items + tuple(item for item in pending.items if item.side.upper() != "SELL"))
    reconciled = replace(pending, items=resolved_items)
    reason_codes = list(dict.fromkeys(code for code in evidence["reason_codes"] if code))
    evidence.update(
        {
            "classification": "PASS",
            "resolution_action": "SELL_PENDING_RECONCILED",
            "reason_codes": reason_codes or ["PENDING_SELL_NO_CONFLICT"],
            "review_required": False,
            "resolved_sell_item_ids": [item.pending_item_id for item in resolved_sell_items],
            "opposite_side_preserved": bool(existing_buy_items),
            "pending_plan_hash_before": existing_hash,
            "pending_plan_hash_after": _items_content_hash(resolved_items),
        }
    )
    _write_reconciliation_evidence(artifact_dir, evidence)
    return SellPendingReconciliationResult(reconciled, "PASS", "", False, existing, existing_hash, evidence)


def active_pending_snapshot(
    *,
    runtime_root: Path,
    environment: str,
    business_date: str,
    target_session_date: str,
) -> tuple[PendingOrderPlan | None, str, dict]:
    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    read_result = read_pending_order_plan_path(path=path, environment=environment)
    if not read_result.valid or read_result.plan is None:
        return None, read_result.classification, {"path": str(path), "valid": False}
    plan = read_result.plan
    active = plan.state not in INACTIVE_PENDING_STATES and not plan.consume.consumed
    same_date = plan.plan_created_date == business_date and plan.target_session_date == target_session_date
    snapshot = {
        "path": str(path),
        "valid": True,
        "read_classification": read_result.classification,
        "active": active,
        "same_date": same_date,
        "pending_plan_id": plan.pending_plan_id,
        "pending_plan_hash": _file_hash(path) if path.is_file() else "",
        "state": plan.state.value,
        "plan_created_date": plan.plan_created_date,
        "target_session_date": plan.target_session_date,
        "consume_consumed": bool(plan.consume.consumed),
        "approved_item_ids": list(plan.approved_item_ids),
        "approved_buy_item_ids": list(plan.approved_buy_item_ids),
        "approved_sell_item_ids": list(plan.approved_sell_item_ids),
        "item_ids": [item.pending_item_id for item in plan.items],
        "items": [
            {
                "pending_item_id": item.pending_item_id,
                "symbol": item.symbol,
                "side": item.side,
                "quantity": item.quantity,
                "approved": item.approved,
                "state": item.state,
                "approved_by_top_level": item.pending_item_id in set(plan.approved_item_ids),
            }
            for item in plan.items
        ],
        "buy_item_count": sum(1 for item in plan.items if item.side.upper() == "BUY"),
        "sell_item_count": sum(1 for item in plan.items if item.side.upper() == "SELL"),
        "approved_buy_item_count": sum(
            1
            for item in plan.items
            if item.side.upper() == "BUY" and item.pending_item_id in set(plan.approved_item_ids) and item.quantity > 0
        ),
        "approved_sell_item_count": sum(
            1
            for item in plan.items
            if item.side.upper() == "SELL" and item.pending_item_id in set(plan.approved_item_ids) and item.quantity > 0
        ),
    }
    if not active:
        return None, f"inactive_state:{plan.state.value}", snapshot
    if not same_date:
        return None, "date_mismatch", snapshot
    return plan, "PASS", snapshot


def _dedupe_items(items: tuple[PendingOrderItem, ...]) -> tuple[PendingOrderItem, ...]:
    seen: set[str] = set()
    deduped: list[PendingOrderItem] = []
    for item in items:
        if item.pending_item_id in seen:
            continue
        seen.add(item.pending_item_id)
        deduped.append(item)
    return tuple(deduped)


def _classify_sell_pair(
    *,
    existing_plan: PendingOrderPlan,
    existing_item: PendingOrderItem,
    new_item: PendingOrderItem,
    business_date: str,
    target_session_date: str,
) -> tuple[str, str, str]:
    if existing_plan.state in COMMITTED_SELL_PENDING_STATES:
        return "ALREADY_SUBMITTED", "REVIEW_REQUIRED", "PENDING_SELL_ALREADY_SUBMITTED_REVIEW"
    if _item_has_partial_fill_evidence(existing_item):
        return "PARTIALLY_FILLED", "REVIEW_REQUIRED", "PENDING_SELL_PARTIAL_FILL_REVIEW"
    if existing_plan.plan_created_date != business_date or existing_plan.target_session_date != target_session_date:
        return "CROSS_DAY_STALE_PENDING", "REVIEW_REQUIRED", "PENDING_SELL_STALE_EXPIRED"
    existing_generation = str(existing_item.accepted_generation_id or existing_plan.accepted_generation_id or "")
    new_generation = str(new_item.accepted_generation_id or "")
    if existing_generation and new_generation and existing_generation != new_generation:
        return "GENERATION_MISMATCH", "REVIEW_REQUIRED", "PENDING_SELL_GENERATION_MISMATCH"

    existing_intent = _sell_intent_class(existing_item)
    new_intent = _sell_intent_class(new_item)
    if existing_intent == "EXIT" and new_intent == "REDUCE":
        return "SAME_SYMBOL_COMPATIBLE_UPDATE", "PRESERVE_EXISTING", "PENDING_SELL_EXIT_PRESERVED_OVER_REDUCE"
    if existing_intent == "REDUCE" and new_intent == "EXIT":
        return "SAME_SYMBOL_COMPATIBLE_UPDATE", "REPLACE_WITH_NEW", "PENDING_SELL_REDUCE_UPGRADED_TO_EXIT"

    same_lineage = _same_decision_lineage(existing_item, new_item)
    equivalent_quantity = _equivalent_quantity(existing_item.quantity, new_item.quantity)
    if same_lineage and existing_intent == new_intent and equivalent_quantity:
        return "SAME_INTENT_DUPLICATE", "PRESERVE_EXISTING", "PENDING_SELL_IDEMPOTENT_DUPLICATE_PRESERVED"
    if _compatible_sell_lineage(existing_item, new_item) and equivalent_quantity:
        return "SAME_SYMBOL_COMPATIBLE_UPDATE", "PRESERVE_EXISTING", "PENDING_SELL_COMPATIBLE_UPDATE_MERGED"
    if not equivalent_quantity:
        return "SAME_SYMBOL_CONFLICTING_QUANTITY", "REVIEW_REQUIRED", "PENDING_SELL_CONFLICTING_QUANTITY_REVIEW"
    if existing_intent != new_intent and "SELL" not in {existing_intent, new_intent}:
        return "SAME_SYMBOL_CONFLICTING_INTENT", "REVIEW_REQUIRED", "PENDING_SELL_CONFLICTING_INTENT_REVIEW"
    return "UNKNOWN_IDENTITY", "REVIEW_REQUIRED", "PENDING_SELL_IDENTITY_UNKNOWN"


def _classification_payload(
    classification: str,
    existing_item: PendingOrderItem | None,
    new_item: PendingOrderItem | None,
    action: str,
    reason: str = "",
) -> dict:
    return {
        "identity_classification": classification,
        "conflict_classification": classification,
        "resolution_action": action,
        "reason_code": reason,
        "existing_pending_item_id": existing_item.pending_item_id if existing_item else "",
        "new_pending_item_id": new_item.pending_item_id if new_item else "",
        "symbol": (new_item.symbol if new_item else existing_item.symbol if existing_item else ""),
        "side": (new_item.side if new_item else existing_item.side if existing_item else ""),
        "existing_intent_class": _sell_intent_class(existing_item) if existing_item else "",
        "new_intent_class": _sell_intent_class(new_item) if new_item else "",
        "existing_quantity": existing_item.quantity if existing_item else None,
        "new_quantity": new_item.quantity if new_item else None,
        "existing_source_decision_id": existing_item.source_pm_decision_id if existing_item else "",
        "new_source_decision_id": new_item.source_pm_decision_id if new_item else "",
        "campaign_id": _campaign_id(existing_item) or _campaign_id(new_item),
        "accepted_generation_id": (
            str((new_item.accepted_generation_id if new_item else "") or (existing_item.accepted_generation_id if existing_item else ""))
        ),
    }


def _merge_required_authority_for_preserved_sell_item(
    *,
    existing_plan: PendingOrderPlan,
    existing_item: PendingOrderItem,
    new_item: PendingOrderItem,
    business_date: str,
    target_session_date: str,
    existing_pending_hash: str,
) -> tuple[PendingOrderItem, str, str, dict]:
    existing_hash_before = _item_content_hash(existing_item)
    existing_status = _listed_info_validation_status(existing_item.listed_info, symbol=existing_item.symbol)
    new_status = _listed_info_validation_status(new_item.listed_info, symbol=new_item.symbol)
    existing_authority_type = _listed_info_authority_type(existing_item.listed_info)
    new_authority_type = _listed_info_authority_type(new_item.listed_info)
    source_artifact = (
        new_item.planning_authority_source
        or new_item.policy_source
        or new_item.submit_policy_source
        or new_item.runtime_test_evidence_root
        or ""
    )
    evidence = {
        "authority_type": "SELL_PENDING_REQUIRED_AUTHORITY_MERGE",
        "authority_field": "listed_info",
        "existing_pending_item_id": existing_item.pending_item_id,
        "new_pending_item_id": new_item.pending_item_id,
        "listed_info_source": "new_compatible_sell_item" if new_item.listed_info else "",
        "listed_info_source_item_id": new_item.pending_item_id if new_item.listed_info else "",
        "listed_info_source_business_date": new_item.source_pm_business_date or business_date,
        "listed_info_source_artifact": source_artifact,
        "listed_info_source_hash": _hash(_json_dumps(_jsonable(new_item.listed_info))) if new_item.listed_info else "",
        "existing_listed_info_status": existing_status["status"],
        "existing_listed_info_reason": existing_status["reason"],
        "new_listed_info_status": new_status["status"],
        "new_listed_info_reason": new_status["reason"],
        "existing_authority_type": existing_authority_type,
        "new_authority_type": new_authority_type,
        "authority_precedence": "",
        "market_existing_value": _listed_info_field(existing_item.listed_info, "market"),
        "market_new_value": _listed_info_field(new_item.listed_info, "market"),
        "market_semantic_relation": "",
        "secondary_market_value": "",
        "secondary_authority_type": "",
        "canonical_authority_preserved": False,
        "core_identity_match_status": "",
        "merge_action": "",
        "validation_status": "",
        "conflict_status": "",
        "reason_code": "",
        "existing_item_hash_before": existing_hash_before,
        "existing_item_hash_after": existing_hash_before,
        "pending_plan_hash_before": existing_pending_hash,
        "pending_plan_hash_after": "",
        "identity_preserved": True,
        "compatible_sell_lineage": _compatible_sell_lineage(existing_item, new_item),
    }

    identity_reason = _authority_merge_identity_block_reason(
        existing_plan=existing_plan,
        existing_item=existing_item,
        new_item=new_item,
        business_date=business_date,
        target_session_date=target_session_date,
    )
    if identity_reason:
        evidence.update(
            {
                "merge_action": "REVIEW_REQUIRED",
                "validation_status": "REVIEW_REQUIRED",
                "conflict_status": "IDENTITY_OR_STATE_BLOCK",
                "reason_code": identity_reason,
            }
        )
        return existing_item, "REVIEW_REQUIRED", identity_reason, evidence

    existing_valid = existing_status["status"] == "VALID"
    new_valid = new_status["status"] == "VALID"
    if not existing_item.listed_info and not new_item.listed_info:
        reason = "PENDING_SELL_REQUIRED_AUTHORITY_LISTED_INFO_MISSING"
        evidence.update(
            {
                "merge_action": "REVIEW_REQUIRED_BOTH_NULL",
                "validation_status": "REVIEW_REQUIRED",
                "conflict_status": "BOTH_NULL",
                "reason_code": reason,
            }
        )
        return existing_item, "REVIEW_REQUIRED", reason, evidence
    if existing_item.listed_info and not existing_valid:
        reason = "PENDING_SELL_LISTED_INFO_AUTHORITY_INVALID"
        evidence.update(
            {
                "merge_action": "REVIEW_REQUIRED_EXISTING_INVALID",
                "validation_status": "REVIEW_REQUIRED",
                "conflict_status": "INVALID_EXISTING_AUTHORITY",
                "reason_code": reason,
            }
        )
        return existing_item, "REVIEW_REQUIRED", reason, evidence
    if not existing_item.listed_info:
        if not new_valid:
            reason = "PENDING_SELL_LISTED_INFO_AUTHORITY_INVALID"
            evidence.update(
                {
                    "merge_action": "REVIEW_REQUIRED_NEW_INVALID",
                    "validation_status": "REVIEW_REQUIRED",
                    "conflict_status": "INVALID_NEW_AUTHORITY",
                    "reason_code": reason,
                }
            )
            return existing_item, "REVIEW_REQUIRED", reason, evidence
        if not _listed_info_source_identifiable(new_item):
            reason = "PENDING_SELL_LISTED_INFO_SOURCE_UNKNOWN"
            evidence.update(
                {
                    "merge_action": "REVIEW_REQUIRED_SOURCE_UNKNOWN",
                    "validation_status": "REVIEW_REQUIRED",
                    "conflict_status": "SOURCE_UNKNOWN",
                    "reason_code": reason,
                }
            )
            return existing_item, "REVIEW_REQUIRED", reason, evidence
        merged = replace(existing_item, listed_info=dict(new_item.listed_info or {}))
        evidence.update(
            {
                "merge_action": "FILL_MISSING_FROM_NEW",
                "validation_status": "PASS",
                "conflict_status": "NO_CONFLICT",
                "reason_code": "PENDING_SELL_REQUIRED_AUTHORITY_LISTED_INFO_FILLED_FROM_COMPATIBLE_NEW",
                "existing_item_hash_after": _item_content_hash(merged),
                "pending_plan_hash_after": _item_content_hash(merged),
            }
        )
        return merged, "PASS", "", evidence
    if not new_item.listed_info:
        evidence.update(
            {
                "merge_action": "PRESERVE_EXISTING",
                "validation_status": "PASS",
                "conflict_status": "NO_CONFLICT_NEW_NULL",
                "reason_code": "PENDING_SELL_REQUIRED_AUTHORITY_LISTED_INFO_PRESERVED_EXISTING",
                "pending_plan_hash_after": existing_hash_before,
            }
        )
        return existing_item, "PASS", "", evidence
    if not new_valid:
        reason = "PENDING_SELL_LISTED_INFO_AUTHORITY_INVALID"
        evidence.update(
            {
                "merge_action": "REVIEW_REQUIRED_NEW_INVALID",
                "validation_status": "REVIEW_REQUIRED",
                "conflict_status": "INVALID_NEW_AUTHORITY",
                "reason_code": reason,
            }
        )
        return existing_item, "REVIEW_REQUIRED", reason, evidence
    if _equivalent_listed_info(existing_item.listed_info, new_item.listed_info):
        evidence.update(
            {
                "merge_action": "PRESERVE_EXISTING",
                "validation_status": "PASS",
                "conflict_status": "NO_CONFLICT_EQUIVALENT",
                "reason_code": "PENDING_SELL_REQUIRED_AUTHORITY_LISTED_INFO_PRESERVED_EXISTING",
                "pending_plan_hash_after": existing_hash_before,
                "core_identity_match_status": "PASS",
            }
        )
        return existing_item, "PASS", "", evidence
    precedence_resolution = _listed_info_authority_precedence_resolution(
        existing_item.listed_info,
        new_item.listed_info,
        existing_authority_type=existing_authority_type,
        new_authority_type=new_authority_type,
    )
    if precedence_resolution["status"] == "PASS":
        evidence.update(
            {
                "merge_action": "PRESERVE_EXISTING_CANONICAL",
                "validation_status": "PASS",
                "conflict_status": "NO_CONFLICT_AUTHORITY_PRECEDENCE",
                "reason_code": "PENDING_SELL_CANONICAL_LISTED_INFO_PRESERVED_OVER_BASIC_MARKET_METADATA",
                "pending_plan_hash_after": existing_hash_before,
                **precedence_resolution["evidence"],
            }
        )
        return existing_item, "PASS", "", evidence
    if precedence_resolution["reason"]:
        evidence.update(precedence_resolution["evidence"])
    reason = "PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT"
    evidence.update(
        {
            "merge_action": "REVIEW_REQUIRED_CONFLICT",
            "validation_status": "REVIEW_REQUIRED",
            "conflict_status": "CONFLICTING_LISTED_INFO",
            "reason_code": reason,
        }
    )
    return existing_item, "REVIEW_REQUIRED", reason, evidence


def _authority_merge_identity_block_reason(
    *,
    existing_plan: PendingOrderPlan,
    existing_item: PendingOrderItem,
    new_item: PendingOrderItem,
    business_date: str,
    target_session_date: str,
) -> str:
    if existing_plan.state in COMMITTED_SELL_PENDING_STATES:
        return "PENDING_SELL_ALREADY_SUBMITTED_REVIEW"
    if _item_has_partial_fill_evidence(existing_item):
        return "PENDING_SELL_PARTIAL_FILL_REVIEW"
    if existing_plan.plan_created_date != business_date or existing_plan.target_session_date != target_session_date:
        return "PENDING_SELL_STALE_EXPIRED"
    if not _same_symbol(existing_item.symbol, new_item.symbol):
        return "PENDING_SELL_LISTED_INFO_IDENTITY_MISMATCH"
    if existing_item.side.upper() != "SELL" or new_item.side.upper() != "SELL":
        return "PENDING_SELL_LISTED_INFO_SIDE_MISMATCH"
    if not _compatible_sell_lineage(existing_item, new_item):
        return "PENDING_SELL_LISTED_INFO_LINEAGE_MISMATCH"
    existing_generation = str(existing_item.accepted_generation_id or existing_plan.accepted_generation_id or "")
    new_generation = str(new_item.accepted_generation_id or "")
    if existing_generation and new_generation and existing_generation != new_generation:
        return "PENDING_SELL_GENERATION_MISMATCH"
    return ""


def _listed_info_validation_status(listed_info: dict | None, *, symbol: str) -> dict:
    if listed_info is None:
        return {"status": "MISSING", "reason": "listed_info_null"}
    if not isinstance(listed_info, dict):
        return {"status": "INVALID", "reason": "listed_info_not_object"}
    required = ("code", "market", "product_category", "security_type", "current_listed")
    missing = [key for key in required if key not in listed_info or listed_info.get(key) in ("", None)]
    if missing:
        return {"status": "INVALID", "reason": f"missing_required:{','.join(missing)}"}
    if str(listed_info.get("code") or "").strip() != str(symbol or "").strip():
        return {"status": "INVALID", "reason": "code_symbol_mismatch"}
    if listed_info.get("current_listed") is not True:
        return {"status": "INVALID", "reason": "current_listed_not_true"}
    return {"status": "VALID", "reason": "PASS"}


def _listed_info_source_identifiable(item: PendingOrderItem) -> bool:
    return bool(
        item.pending_item_id
        and (
            item.source_pm_decision_id
            or item.source_decision_type
            or item.planning_authority_source
            or item.policy_source
            or item.submit_policy_source
            or item.runtime_test_evidence_root
        )
    )


def _equivalent_listed_info(left: dict | None, right: dict | None) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    keys = ("code", "market", "product_category", "security_type", "current_listed")
    return all(str(left.get(key)).strip() == str(right.get(key)).strip() for key in keys)


def _listed_info_authority_precedence_resolution(
    existing: dict | None,
    new: dict | None,
    *,
    existing_authority_type: str,
    new_authority_type: str,
) -> dict:
    evidence = {
        "authority_precedence": "",
        "market_semantic_relation": "",
        "secondary_market_value": "",
        "secondary_authority_type": "",
        "canonical_authority_preserved": False,
        "core_identity_match_status": "",
    }
    if not isinstance(existing, dict) or not isinstance(new, dict):
        return {"status": "NO_MATCH", "reason": "listed_info_not_object", "evidence": evidence}
    core_fields = ("code", "product_category", "security_type", "current_listed")
    if not all(_listed_info_values_equal(existing.get(field), new.get(field)) for field in core_fields):
        evidence["core_identity_match_status"] = "MISMATCH"
        return {"status": "NO_MATCH", "reason": "core_identity_mismatch", "evidence": evidence}
    evidence["core_identity_match_status"] = "PASS"
    existing_market = _listed_info_field(existing, "market")
    new_market = _listed_info_field(new, "market")
    if existing_market == new_market:
        return {"status": "NO_MATCH", "reason": "", "evidence": evidence}
    if (
        existing_authority_type == "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
        and new_authority_type == "PM_BASIC_EXECUTION_METADATA"
    ):
        evidence.update(
            {
                "authority_precedence": "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY_OVER_PM_BASIC_EXECUTION_METADATA",
                "market_semantic_relation": "CANONICAL_MARKET_SEGMENT_VS_PM_EXCHANGE_METADATA",
                "secondary_market_value": new_market,
                "secondary_authority_type": new_authority_type,
                "canonical_authority_preserved": True,
            }
        )
        return {"status": "PASS", "reason": "", "evidence": evidence}
    if existing_authority_type == "UNKNOWN_AUTHORITY" or new_authority_type == "UNKNOWN_AUTHORITY":
        return {"status": "NO_MATCH", "reason": "unknown_authority", "evidence": evidence}
    if (
        existing_authority_type == "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
        and new_authority_type == "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
    ):
        return {"status": "NO_MATCH", "reason": "canonical_market_mismatch", "evidence": evidence}
    return {"status": "NO_MATCH", "reason": "market_authority_precedence_not_applicable", "evidence": evidence}


def _listed_info_authority_type(listed_info: dict | None) -> str:
    if not isinstance(listed_info, dict):
        return "UNKNOWN_AUTHORITY"
    authority = str(
        listed_info.get("listed_info_authority")
        or listed_info.get("authority")
        or listed_info.get("source_authority")
        or ""
    ).strip()
    if authority == "canonical_pit_listed_issues":
        return "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
    if (
        _listed_info_field(listed_info, "market") == "東証"
        and not authority
        and not listed_info.get("listed_info_source_hash")
        and not listed_info.get("listed_info_source_artifact")
    ):
        return "PM_BASIC_EXECUTION_METADATA"
    return "UNKNOWN_AUTHORITY"


def _listed_info_values_equal(left: object, right: object) -> bool:
    return str(left).strip() == str(right).strip()


def _listed_info_field(listed_info: dict | None, field: str) -> str:
    if not isinstance(listed_info, dict):
        return ""
    return str(listed_info.get(field) or "").strip()


def _sell_intent_class(item: PendingOrderItem | None) -> str:
    if item is None:
        return ""
    contract = item.quantity_contract or {}
    source = str(contract.get("source_decision") or item.source_decision_type or item.pending_item_id or "").upper()
    if "EXIT" in source:
        return "EXIT"
    if "REDUCE" in source or "PARTIAL" in source:
        return "REDUCE"
    if "SELL" in source:
        return "SELL"
    return ""


def _same_decision_lineage(existing_item: PendingOrderItem, new_item: PendingOrderItem) -> bool:
    existing_pm = str(existing_item.source_pm_decision_id or "")
    new_pm = str(new_item.source_pm_decision_id or "")
    if existing_pm and new_pm and existing_pm == new_pm:
        return True
    return existing_item.pending_item_id == new_item.pending_item_id


def _compatible_sell_lineage(existing_item: PendingOrderItem, new_item: PendingOrderItem) -> bool:
    if not _same_symbol(existing_item.symbol, new_item.symbol):
        return False
    if existing_item.side.upper() != "SELL" or new_item.side.upper() != "SELL":
        return False
    existing_campaign = _campaign_id(existing_item)
    new_campaign = _campaign_id(new_item)
    if existing_campaign and new_campaign and existing_campaign != new_campaign:
        return False
    existing_intent = _sell_intent_class(existing_item)
    new_intent = _sell_intent_class(new_item)
    return existing_intent in {"SELL", "REDUCE", "EXIT", ""} and new_intent in {"SELL", "REDUCE", "EXIT", ""}


def _campaign_id(item: PendingOrderItem | None) -> str:
    if item is None:
        return ""
    contract = item.quantity_contract or {}
    return str(contract.get("position_campaign_id") or contract.get("campaign_id") or "")


def _equivalent_quantity(left: float, right: float) -> bool:
    return abs(float(left or 0.0) - float(right or 0.0)) < 1e-9


def _item_has_partial_fill_evidence(item: PendingOrderItem) -> bool:
    markers = {
        str(item.state or "").upper(),
        str(item.batch_submit_status or "").upper(),
        str(item.feasibility_status or "").upper(),
    }
    return any("PARTIAL" in marker or "FILLED" in marker for marker in markers)


def _same_symbol(left: str, right: str) -> bool:
    return str(left).strip() == str(right).strip()


def _write_reconciliation_evidence(artifact_dir: Path, evidence: dict) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "pending_sell_reconciliation_evidence.json").write_text(
        _json_dumps(evidence),
        encoding="utf-8",
    )


def _short_items_hash(items: tuple[PendingOrderItem, ...]) -> str:
    payload = [
        {
            "pending_item_id": item.pending_item_id,
            "symbol": item.symbol,
            "side": item.side,
            "quantity": item.quantity,
        }
        for item in items
    ]
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()[:12]


def _item_content_hash(item: PendingOrderItem) -> str:
    return _hash(_json_dumps(_jsonable(asdict(item))))


def _items_content_hash(items: tuple[PendingOrderItem, ...]) -> str:
    return _hash(_json_dumps([_jsonable(asdict(item)) for item in items]))


def _hash(payload: str) -> str:
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    try:
        return _hash(path.read_text(encoding="utf-8"))
    except OSError:
        return ""


def _json_dumps(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _jsonable(value):
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _attach_accepted_generation_binding(
    *,
    pending: PendingOrderPlan,
    accepted_generation_binding: dict | None,
) -> PendingOrderPlan:
    if not accepted_generation_binding:
        return pending
    binding = dict(accepted_generation_binding)
    return replace(
        pending,
        accepted_generation_binding=binding,
        accepted_generation_id=str(binding.get("accepted_generation_id") or ""),
        accepted_generation_business_date=str(binding.get("accepted_generation_business_date") or ""),
        accepted_generation_binding_status=str(binding.get("generation_binding_status") or ""),
        items=tuple(
            replace(
                item,
                accepted_generation_id=str(binding.get("accepted_generation_id") or ""),
                accepted_generation_business_date=str(binding.get("accepted_generation_business_date") or ""),
                accepted_generation_binding_status=str(binding.get("generation_binding_status") or ""),
                accepted_generation_binding=binding,
            )
            for item in pending.items
        ),
    )
