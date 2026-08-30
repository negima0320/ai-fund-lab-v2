"""Runtime provenance helpers for order lifecycle identity fields."""

from __future__ import annotations

from typing import Any, Mapping


MISSING_TEXT = {"", "MISSING", "UNKNOWN", "NONE", "NULL"}


def clean_text(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.upper() in MISSING_TEXT else text


def first_text(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def nested_text(payload: Mapping[str, Any] | None, *path: str) -> str:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return ""
        current = current.get(key)
    return clean_text(current)


def pending_item_provenance(item: Any) -> dict[str, str]:
    contract = getattr(item, "quantity_contract", None)
    contract = contract if isinstance(contract, Mapping) else {}
    source_decision_id = first_text(
        getattr(item, "source_decision_id", ""),
        contract.get("source_decision_id"),
        contract.get("source_planning_id"),
        getattr(item, "source_pm_decision_id", ""),
        getattr(item, "planning_authority_source", ""),
        getattr(item, "pending_item_id", ""),
    )
    source_decision_type = first_text(
        getattr(item, "source_decision_type", ""),
        contract.get("source_decision"),
        contract.get("planning_intent"),
        getattr(item, "side", ""),
    )
    order_plan_item_id = first_text(
        getattr(item, "order_plan_item_id", ""),
        contract.get("order_plan_item_id"),
        contract.get("source_planning_id"),
        getattr(item, "pending_item_id", ""),
    )
    position_campaign_id = first_text(
        getattr(item, "position_campaign_id", ""),
        contract.get("position_campaign_id"),
        contract.get("campaign_id"),
    )
    return {
        "source_decision_id": source_decision_id,
        "source_decision_type": source_decision_type,
        "source_pm_decision_id": first_text(getattr(item, "source_pm_decision_id", ""), contract.get("source_pm_decision_id")),
        "order_plan_item_id": order_plan_item_id,
        "position_campaign_id": position_campaign_id,
        "campaign_id": position_campaign_id,
    }


def validate_pending_item_provenance(item: Any) -> tuple[str, ...]:
    contract = getattr(item, "quantity_contract", None)
    if not isinstance(contract, Mapping):
        return ()
    mismatches: list[str] = []
    for field, contract_fields in (
        ("source_decision_id", ("source_decision_id", "source_planning_id")),
        ("order_plan_item_id", ("order_plan_item_id",)),
        ("position_campaign_id", ("position_campaign_id", "campaign_id")),
    ):
        item_value = clean_text(getattr(item, field, ""))
        contract_values = {clean_text(contract.get(key)) for key in contract_fields}
        contract_values.discard("")
        if item_value and contract_values and item_value not in contract_values:
            mismatches.append(field)
    return tuple(mismatches)
