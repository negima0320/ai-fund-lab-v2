"""Precomputable executable-membership guard consumers.

This module consumes already-produced item/symbol authorities before Pending
executable membership. It does not decide Strategy, quantity, cash, or Pending
review scope.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.guard_taxonomy import normalize_review_result


def evaluate_precomputable_executable_membership_guard(
    *,
    item: Any,
    business_date: str,
    runtime_mode: str,
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return PASS or REVIEW_REQUIRED for known pre-Pending item blockers."""

    symbol = str(getattr(item, "symbol", "") or "").strip()
    pending_item_id = str(getattr(item, "pending_item_id", "") or "").strip()
    side = str(getattr(item, "side", "") or "").strip().upper()
    base = {
        "precomputable_executable_membership_guard_status": "PASS",
        "precomputable_executable_membership_guard_reason": "",
        "precomputable_executable_membership_guard_source": "",
        "precomputable_executable_membership_guard_policy": "",
        "precomputable_executable_membership_guard_business_date": str(business_date or ""),
        "precomputable_executable_membership_guard_runtime_mode": str(runtime_mode or ""),
    }

    root = _runtime_root(runtime_root)
    if root is not None and str(runtime_mode or "").lower() == "historical":
        registry_path, unresolved_entry = _corporate_action_quarantine_reader()
        entry = unresolved_entry(root, symbol)
        if entry:
            reason = str(entry.get("reason") or "corporate_action_event_not_resolved")
            return _review(
                base=base,
                producer="historical_corporate_action_symbol_quarantine",
                reason=reason,
                violated_policy="historical_corporate_action_symbol_quarantine",
                violated_policy_source=str(registry_path(root)),
                affected_item_id=pending_item_id,
                side=side,
                extra={
                    "corporate_action_quarantine_status": str(entry.get("corporate_action_quarantine_status") or ""),
                    "corporate_action_quarantined_symbol": str(entry.get("corporate_action_quarantined_symbol") or symbol),
                    "corporate_action_quarantine_reason": reason,
                    "corporate_action_quarantine_scope": str(entry.get("corporate_action_quarantine_scope") or "SYMBOL_ONLY"),
                    "corporate_action_run_continuation_eligibility": str(
                        entry.get("corporate_action_run_continuation_eligibility") or ""
                    ),
                    "corporate_action_event_status": str(entry.get("event_status") or "IMPACT_DETECTED"),
                    "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
                    "corporate_action_adjustment_authority_reason": reason,
                    "corporate_action_reason_codes": ["corporate_action_event_not_resolved"],
                },
            )

    authority = _known_corporate_action_adjustment_authority(item)
    authority_status = str(authority.get("corporate_action_adjustment_authority_status") or "").upper()
    if authority_status and authority_status != "PASS":
        reason = str(
            authority.get("corporate_action_adjustment_authority_reason")
            or authority.get("reason")
            or "corporate_action_adjustment_authority_unresolved"
        )
        return _review(
            base=base,
            producer="corporate_action_adjustment_authority",
            reason=reason,
            violated_policy="corporate_action_adjustment_authority",
            violated_policy_source=str(authority.get("corporate_action_adjustment_authority_path") or ""),
            affected_item_id=pending_item_id,
            side=side,
            extra=dict(authority),
        )

    return base


def _review(
    *,
    base: Mapping[str, Any],
    producer: str,
    reason: str,
    violated_policy: str,
    violated_policy_source: str,
    affected_item_id: str,
    side: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    typed = normalize_review_result(
        producer=producer,
        reason=reason,
        status="REVIEW_REQUIRED",
        source_payload={"side": side, **dict(extra or {})},
        affected_item_ids=[affected_item_id] if affected_item_id else [],
    )
    typed = _item_scoped_corporate_action_guard(typed, side=side, affected_item_id=affected_item_id)
    return {
        **dict(base),
        **dict(extra or {}),
        "precomputable_executable_membership_guard_status": "REVIEW_REQUIRED",
        "precomputable_executable_membership_guard_reason": reason,
        "precomputable_executable_membership_guard_source": violated_policy_source,
        "precomputable_executable_membership_guard_policy": violated_policy,
        "status": "REVIEW_REQUIRED",
        "reason": reason,
        "violated_policy": violated_policy,
        "violated_policy_source": violated_policy_source,
        "guard_class": typed.get("guard_class"),
        "guard_code": typed.get("guard_code"),
        "scope": typed.get("scope"),
        "affected_side": typed.get("affected_side"),
        "affected_item_ids": typed.get("affected_item_ids"),
        "batch_blocking": typed.get("batch_blocking"),
        "recoverability": typed.get("recoverability"),
        "canonical_owner": typed.get("canonical_owner"),
        "consumer_action": typed.get("consumer_action"),
        "typed_guard": typed,
    }


def _item_scoped_corporate_action_guard(
    typed: Mapping[str, Any],
    *,
    side: str,
    affected_item_id: str,
) -> dict[str, Any]:
    guard = dict(typed)
    if side in {"BUY", "SELL"}:
        guard["affected_side"] = side
    if affected_item_id:
        guard["affected_item_ids"] = [affected_item_id]
    guard["scope"] = "ITEM"
    guard["batch_blocking"] = False
    guard["consumer_action"] = "FAIL_CLOSED_REVIEW_ITEM_ALLOW_UNAFFECTED_ITEMS"
    return guard


def _known_corporate_action_adjustment_authority(item: Any) -> dict[str, Any]:
    contexts: list[Mapping[str, Any]] = []
    for attr in ("quantity_contract", "listed_info"):
        value = getattr(item, attr, None)
        if isinstance(value, Mapping):
            contexts.append(value)
    for context in contexts:
        nested = context.get("corporate_action_adjustment_authority")
        if isinstance(nested, Mapping):
            return dict(nested)
        if "corporate_action_adjustment_authority_status" in context:
            return dict(context)
    return {}


def _runtime_root(value: Path | str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.name == "state.json" and path.parent.name == "persistent_ledger":
        return path.parent.parent
    return path


def _corporate_action_quarantine_reader():
    from ai_fund_lab_v2.runtime_v2.historical_support.corporate_action_quarantine import (
        registry_path,
        unresolved_entry,
    )

    return registry_path, unresolved_entry
