"""Runtime guard taxonomy and typed review normalization.

The taxonomy classifies REVIEW_REQUIRED / blocking evidence for consumers.  It
does not decide cash, quantity, Strategy allocation, Pending scope, or temporal
authority; canonical producers continue to own those decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


CONTRACT_ID = "runtime_guard_taxonomy"
CONTRACT_VERSION = "phase30_ak9r29_v1"

MARKET_PORTFOLIO_SAFETY = "MARKET_PORTFOLIO_SAFETY"
EXECUTION_SAFETY = "EXECUTION_SAFETY"
DATA_INTEGRITY_SAFETY = "DATA_INTEGRITY_SAFETY"
INTERNAL_SYSTEM_CONSISTENCY = "INTERNAL_SYSTEM_CONSISTENCY"
ITEM_SCOPED_REVIEW = "ITEM_SCOPED_REVIEW"
BATCH_LEVEL_FAILURE = "BATCH_LEVEL_FAILURE"

SCOPE_ITEM = "ITEM"
SCOPE_SIDE = "SIDE"
SCOPE_BATCH = "BATCH"
SCOPE_PORTFOLIO = "PORTFOLIO"
SCOPE_DATA = "DATA"
SCOPE_SYSTEM = "SYSTEM"

SIDE_BUY = "BUY"
SIDE_SELL = "SELL"
SIDE_BOTH = "BOTH"
SIDE_NONE = "NONE"

SAME_STAGE_RETRYABLE = "SAME_STAGE_RETRYABLE"
NEXT_SESSION_REEVALUATE = "NEXT_SESSION_REEVALUATE"
MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
TERMINAL_FOR_ITEM = "TERMINAL_FOR_ITEM"
SYSTEM_DEFECT_REPAIR_REQUIRED = "SYSTEM_DEFECT_REPAIR_REQUIRED"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class TypedReviewResult:
    guard_class: str
    guard_code: str
    scope: str
    affected_side: str
    affected_item_ids: tuple[str, ...]
    batch_blocking: bool
    recoverability: str
    system_defect: bool
    canonical_owner: str
    authority_provenance: dict[str, Any]
    diagnostic_reason: str
    consumer_action: str
    producer: str = ""
    status: str = "REVIEW_REQUIRED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": CONTRACT_ID,
            "contract_version": CONTRACT_VERSION,
            "producer": self.producer,
            "status": self.status,
            "guard_class": self.guard_class,
            "guard_code": self.guard_code,
            "scope": self.scope,
            "affected_side": self.affected_side,
            "affected_item_ids": list(self.affected_item_ids),
            "batch_blocking": self.batch_blocking,
            "recoverability": self.recoverability,
            "system_defect": self.system_defect,
            "canonical_owner": self.canonical_owner,
            "authority_provenance": dict(self.authority_provenance),
            "diagnostic_reason": self.diagnostic_reason,
            "consumer_action": self.consumer_action,
        }


def normalize_review_result(
    *,
    producer: str,
    reason: str,
    status: str = "REVIEW_REQUIRED",
    source_payload: Mapping[str, Any] | None = None,
    affected_item_ids: Sequence[str] = (),
) -> dict[str, Any]:
    payload = source_payload or {}
    reason_text = str(reason or "")
    reason_key = reason_text.lower()
    producer_key = str(producer or "").lower()
    item_ids = tuple(str(item_id) for item_id in affected_item_ids if str(item_id))

    guard_class = DATA_INTEGRITY_SAFETY
    guard_code = _guard_code(reason_text)
    scope = SCOPE_DATA
    affected_side = SIDE_NONE
    batch_blocking = True
    recoverability = MANUAL_REVIEW_REQUIRED
    system_defect = False
    canonical_owner = _canonical_owner(producer)
    consumer_action = "FAIL_CLOSED_REVIEW"

    if _matches(reason_key, "cash", "buying_power", "reserved_notional", "insufficient"):
        guard_class = EXECUTION_SAFETY
        guard_code = _specific_code(reason_key, default=guard_code, mapping={
            "buying_power": "INSUFFICIENT_BUYING_POWER",
            "cash": "INSUFFICIENT_CASH",
            "reserved_notional": "INSUFFICIENT_RESERVED_CASH",
        })
        scope = SCOPE_ITEM if item_ids else SCOPE_BATCH
        affected_side = SIDE_BUY
        batch_blocking = "aggregate" in reason_key or not item_ids
        recoverability = NEXT_SESSION_REEVALUATE
    elif _matches(reason_key, "broker", "sell available", "sell_available", "available_quantity"):
        guard_class = EXECUTION_SAFETY
        guard_code = "BROKER_SELL_AVAILABILITY_UNKNOWN" if "missing" in reason_key or "unknown" in reason_key else guard_code
        scope = SCOPE_SIDE
        affected_side = SIDE_SELL
        recoverability = SAME_STAGE_RETRYABLE if "missing" in reason_key or "unknown" in reason_key else MANUAL_REVIEW_REQUIRED
    elif _matches(reason_key, "quantity", "lot", "discrete"):
        guard_class = EXECUTION_SAFETY
        guard_code = _specific_code(reason_key, default=guard_code, mapping={
            "quantity mismatch": "QUANTITY_MISMATCH",
            "quantity_mismatch": "QUANTITY_MISMATCH",
            "lot": "LOT_INFEASIBLE",
            "discrete": "DISCRETE_QUANTITY_AUTHORITY_REVIEW",
        })
        scope = SCOPE_ITEM if item_ids else SCOPE_SYSTEM if "authority" in reason_key else SCOPE_BATCH
        affected_side = _side_from_text(reason_key)
        system_defect = "authority" in reason_key and ("missing" in reason_key or "handoff" in reason_key)
        guard_class = INTERNAL_SYSTEM_CONSISTENCY if system_defect else guard_class
        recoverability = SYSTEM_DEFECT_REPAIR_REQUIRED if system_defect else MANUAL_REVIEW_REQUIRED
    elif _matches(reason_key, "hard_cap", "safety hard", "concentration", "exposure", "risk"):
        guard_class = MARKET_PORTFOLIO_SAFETY
        guard_code = _specific_code(reason_key, default=guard_code, mapping={
            "hard_cap": "SAFETY_HARD_CAP",
            "concentration": "CONCENTRATION_LIMIT",
            "exposure": "EXPOSURE_LIMIT",
            "risk": "PORTFOLIO_RISK_REVIEW",
        })
        scope = SCOPE_PORTFOLIO
        affected_side = SIDE_BOTH
        recoverability = NEXT_SESSION_REEVALUATE
    elif _matches(reason_key, "quote", "valuation", "corporate_action", "stale", "temporal", "date_mismatch", "future", "basis", "malformed"):
        guard_class = DATA_INTEGRITY_SAFETY
        guard_code = _specific_code(reason_key, default=guard_code, mapping={
            "quote": "QUOTE_UNAVAILABLE",
            "valuation": "VALUATION_DATA_NOT_READY",
            "corporate_action": "CORPORATE_ACTION_UNRESOLVED",
            "stale": "STALE_DATA",
            "temporal": "TEMPORAL_MISMATCH",
            "date_mismatch": "TEMPORAL_MISMATCH",
            "future": "FUTURE_DATA_REJECTED",
            "basis": "BASIS_INTEGRITY_REVIEW",
            "malformed": "MALFORMED_AUTHORITY",
        })
        scope = SCOPE_DATA
        recoverability = SAME_STAGE_RETRYABLE if "missing" in reason_key else MANUAL_REVIEW_REQUIRED
    elif _matches(reason_key, "buy_item_scoped_review", "item_scoped", "item review"):
        guard_class = ITEM_SCOPED_REVIEW
        guard_code = "BUY_ITEM_SCOPED_REVIEW"
        scope = SCOPE_ITEM
        affected_side = SIDE_BUY if "buy" in reason_key else _side_from_text(reason_key)
        batch_blocking = False
        recoverability = NEXT_SESSION_REEVALUATE
        consumer_action = "ALLOW_APPROVED_ITEMS_FAIL_CLOSED_REVIEWED_ITEMS"
    elif _matches(reason_key, "pending_review_required", "review_required"):
        guard_class = ITEM_SCOPED_REVIEW if _pending_scope_item_scoped(payload) else BATCH_LEVEL_FAILURE
        guard_code = "PENDING_ITEM_SCOPED_REVIEW" if guard_class == ITEM_SCOPED_REVIEW else "PENDING_BATCH_REVIEW_REQUIRED"
        scope = SCOPE_ITEM if guard_class == ITEM_SCOPED_REVIEW else SCOPE_BATCH
        affected_side = SIDE_BUY if guard_class == ITEM_SCOPED_REVIEW else SIDE_BOTH
        batch_blocking = guard_class != ITEM_SCOPED_REVIEW
        recoverability = NEXT_SESSION_REEVALUATE if guard_class == ITEM_SCOPED_REVIEW else MANUAL_REVIEW_REQUIRED
    elif _matches(reason_key, "authority_missing", "authority missing", "schema mismatch", "handoff", "orchestration", "unsupported lifecycle", "source_conflict"):
        guard_class = INTERNAL_SYSTEM_CONSISTENCY
        guard_code = _specific_code(reason_key, default=guard_code, mapping={
            "authority_missing": "CANONICAL_AUTHORITY_MISSING",
            "authority missing": "CANONICAL_AUTHORITY_MISSING",
            "schema mismatch": "PRODUCER_CONSUMER_SCHEMA_MISMATCH",
            "handoff": "AUTHORITY_HANDOFF_DEFECT",
            "orchestration": "ORCHESTRATION_ORDER_DEFECT",
            "unsupported lifecycle": "UNSUPPORTED_LIFECYCLE_SHAPE",
            "source_conflict": "SOURCE_AUTHORITY_CONFLICT",
        })
        scope = SCOPE_SYSTEM
        affected_side = SIDE_NONE
        system_defect = True
        recoverability = SYSTEM_DEFECT_REPAIR_REQUIRED
    elif _matches(producer_key, "candidate", "pm", "pc"):
        guard_class = MARKET_PORTFOLIO_SAFETY
        scope = SCOPE_ITEM if "candidate" in producer_key or "pm" in producer_key else SCOPE_PORTFOLIO
        affected_side = SIDE_BUY
        batch_blocking = False
        recoverability = NEXT_SESSION_REEVALUATE
    elif _matches(producer_key, "system", "runtime_state"):
        guard_class = INTERNAL_SYSTEM_CONSISTENCY
        scope = SCOPE_SYSTEM
        system_defect = True
        recoverability = SYSTEM_DEFECT_REPAIR_REQUIRED

    if _pending_scope_reviewed_sell(payload) or "reviewed sell" in reason_key:
        guard_class = BATCH_LEVEL_FAILURE
        guard_code = "REVIEWED_SELL_BATCH_BLOCK"
        scope = SCOPE_BATCH
        affected_side = SIDE_SELL
        batch_blocking = True
        recoverability = MANUAL_REVIEW_REQUIRED
        system_defect = False

    if guard_class == INTERNAL_SYSTEM_CONSISTENCY:
        system_defect = True
        consumer_action = "FAIL_CLOSED_SYSTEM_REPAIR_REQUIRED"
    elif batch_blocking:
        consumer_action = "FAIL_CLOSED_BATCH_REVIEW"

    authority_provenance = {
        "producer": "runtime_guard_taxonomy",
        "contract_version": CONTRACT_VERSION,
        "source_producer": producer,
        "source_status": status,
        "source_reason": reason_text,
        "pending_review_scope_contract_id": str(payload.get("pending_review_scope_contract_id") or ""),
        "historical_safety_temporal_contract_id": str(payload.get("contract_id") or ""),
    }
    return TypedReviewResult(
        guard_class=guard_class,
        guard_code=guard_code,
        scope=scope,
        affected_side=affected_side,
        affected_item_ids=item_ids or _affected_item_ids_from_payload(payload),
        batch_blocking=batch_blocking,
        recoverability=recoverability,
        system_defect=system_defect,
        canonical_owner=canonical_owner,
        authority_provenance=authority_provenance,
        diagnostic_reason=reason_text,
        consumer_action=consumer_action,
        producer=producer,
        status=status,
    ).to_dict()


def normalize_component_review_results(
    *,
    component_reasons: Mapping[str, Sequence[str]],
    components: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for component, reasons in component_reasons.items():
        source_payload = components.get(component) or {}
        for reason in reasons:
            if not str(reason):
                continue
            normalized.append(
                normalize_review_result(
                    producer=component,
                    reason=str(reason),
                    source_payload=source_payload,
                )
            )
    return _dedupe(normalized)


def taxonomy_consumer_summary(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result_list = [dict(item) for item in results]
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "review_guard_count": len(result_list),
        "guard_classes": sorted({str(item.get("guard_class") or "") for item in result_list if item.get("guard_class")}),
        "guard_codes": sorted({str(item.get("guard_code") or "") for item in result_list if item.get("guard_code")}),
        "system_defect_count": sum(1 for item in result_list if item.get("system_defect")),
        "batch_blocking_count": sum(1 for item in result_list if item.get("batch_blocking")),
        "item_scoped_count": sum(1 for item in result_list if item.get("scope") == SCOPE_ITEM),
        "business_semantic_reason_string_dependency": False,
    }


def _matches(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _guard_code(reason: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in str(reason).strip().upper())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized or "REVIEW_REQUIRED"


def _specific_code(reason_key: str, *, default: str, mapping: Mapping[str, str]) -> str:
    for needle, code in mapping.items():
        if needle in reason_key:
            return code
    return default


def _side_from_text(text: str) -> str:
    has_buy = "buy" in text
    has_sell = "sell" in text
    if has_buy and has_sell:
        return SIDE_BOTH
    if has_buy:
        return SIDE_BUY
    if has_sell:
        return SIDE_SELL
    return SIDE_NONE


def _canonical_owner(producer: str) -> str:
    key = str(producer or "").lower()
    if "candidate" in key:
        return "Candidate quality"
    if key in {"pm", "position_management"} or "pm" in key:
        return "Position Management"
    if key in {"pc", "portfolio_construction"}:
        return "Portfolio Construction"
    if "position_sizing" in key or key == "ps":
        return "Position Sizing Authority"
    if "pending" in key:
        return "Pending lifecycle / PendingReviewScopeAuthority"
    if "submit" in key:
        return "Submit guard / Planning Submit Feasibility"
    if "broker" in key or "execution" in key:
        return "Broker / Execution"
    if "valuation" in key or "quote" in key:
        return "Current Valuation"
    if "corporate" in key:
        return "Corporate Action authority"
    if "safety" in key:
        return "Runtime Safety / Historical Safety temporal authority"
    if "market" in key or "feature" in key or "data" in key:
        return "Data Readiness"
    if "runtime" in key or "system" in key:
        return "Runtime state / orchestration"
    return "Runtime guard producer"


def _pending_scope_item_scoped(payload: Mapping[str, Any]) -> bool:
    return str(payload.get("review_scope") or "") == "BUY_ITEM_SCOPED_REVIEW" or bool(
        payload.get("pending_scope_compatible") and payload.get("review_scope") == "BUY_ITEM_SCOPED_REVIEW"
    )


def _pending_scope_reviewed_sell(payload: Mapping[str, Any]) -> bool:
    return bool(payload.get("review_required_sell_item_ids") or payload.get("reviewed_sell_item_ids"))


def _affected_item_ids_from_payload(payload: Mapping[str, Any]) -> tuple[str, ...]:
    ids: list[str] = []
    for key in (
        "affected_item_ids",
        "review_required_buy_item_ids",
        "review_required_sell_item_ids",
        "reviewed_item_ids",
        "reviewed_buy_item_ids",
        "reviewed_sell_item_ids",
    ):
        ids.extend(str(item) for item in payload.get(key) or () if str(item))
    return tuple(dict.fromkeys(ids))


def _dedupe(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in results:
        key = (
            str(item.get("producer") or ""),
            str(item.get("guard_code") or ""),
            str(item.get("diagnostic_reason") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(item))
    return deduped
