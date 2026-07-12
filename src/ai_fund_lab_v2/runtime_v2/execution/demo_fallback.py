"""Demo-only execution-equivalent fallback authority for Runtime v2."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


FALLBACK_CONTRACT_ID = "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1"


@dataclass(frozen=True)
class DemoExecutionFallbackAuthority:
    contract_id: str
    issue_code: str
    side: str
    quantity: float
    execution_price: float
    valuation_price: float
    request_hash: str
    broker_order_hash: str
    broker_order_hash_short: str
    broker_order_ref_hash_normalized: str
    source_path: str
    evidence_refs: tuple[str, ...]
    production_equivalent: bool = False
    execution_equivalent: bool = True
    authority_status: str = "PASS"

    def applies_to(self, order: Any, *, orders_count: int) -> bool:
        order_hash = str(getattr(order, "order_ref_hash", "") or "")
        return (
            self.authority_status == "PASS"
            and orders_count == 1
            and str(getattr(order, "symbol", "") or "") == self.issue_code
            and str(getattr(order, "side", "") or "").upper() == self.side
            and float(getattr(order, "filled_quantity", 0.0) or 0.0) == self.quantity
            and float(getattr(order, "remaining_quantity", 0.0) or 0.0) == 0.0
            and str(getattr(order, "order_status", "") or "") == "filled"
            and order_hash
            in {
                self.broker_order_hash_short,
                self.broker_order_hash,
                self.broker_order_ref_hash_normalized,
            }
        )


def load_demo_execution_fallback_authority(
    path: Path | str | None,
    *,
    mode: str,
) -> DemoExecutionFallbackAuthority | None:
    if path is None:
        return None
    if mode == "production":
        raise ValueError("demo execution fallback authority is prohibited in production mode")
    if mode != "demo":
        raise ValueError("demo execution fallback authority requires demo mode")

    authority_path = Path(path)
    payload = json.loads(authority_path.read_text(encoding="utf-8"))
    contract = payload.get("demo_fallback_contract") or {}
    scenario = payload.get("scenario") or {}
    decision = payload.get("evidence_authority_decision") or {}
    position_auth = payload.get("position_difference_authority") or {}
    price_auth = payload.get("price_authority") or {}
    broker_evidence = payload.get("broker_evidence") or {}
    broker_response = broker_evidence.get("broker_response") or {}
    browser = broker_evidence.get("browser_confirmation") or {}

    if str(contract.get("contract_id") or "") != FALLBACK_CONTRACT_ID:
        raise ValueError("unsupported demo execution fallback contract")
    if bool(contract.get("production_applicable")):
        raise ValueError("demo execution fallback contract cannot be production applicable")
    if str(decision.get("final_judgment") or "") != "EXECUTION_EQUIVALENT_READY_DEMO_ONLY":
        raise ValueError("demo execution fallback authority is not accepted")
    if str(position_auth.get("authority_status") or "") != "PASS":
        raise ValueError("demo execution fallback position authority is not PASS")

    broker_order_hash = str(broker_response.get("broker_order_id_hash") or "")
    short_hash = "order_" + broker_order_hash.split(":", 1)[-1][:16] if broker_order_hash.startswith("sha256:") else broker_order_hash
    execution_price = _float(((price_auth.get("execution_price") or {}).get("value")) or browser.get("execution_price"))
    valuation_price = _float(((price_auth.get("valuation_price") or {}).get("value")) or 0.0)

    return DemoExecutionFallbackAuthority(
        contract_id=FALLBACK_CONTRACT_ID,
        issue_code=str(scenario.get("issue_code") or ""),
        side=str(scenario.get("side") or "").upper(),
        quantity=_float(scenario.get("quantity")),
        execution_price=execution_price,
        valuation_price=valuation_price,
        request_hash=str(scenario.get("request_hash") or ""),
        broker_order_hash=broker_order_hash,
        broker_order_hash_short=short_hash,
        broker_order_ref_hash_normalized=_hash_ref(short_hash),
        source_path=str(authority_path),
        evidence_refs=(
            FALLBACK_CONTRACT_ID,
            "CLMOrderList",
            "CLMGenbutuKabuList",
            "CLMZanKaiSummary",
            "CLMZanKaiKanougaku",
            "operator_browser_confirmation",
        ),
    )


def fallback_policy_summary(authority: DemoExecutionFallbackAuthority | None) -> dict[str, Any]:
    if authority is None:
        return {
            "contract_id": "",
            "used": False,
            "production_equivalent": True,
            "execution_equivalent": False,
        }
    return {
        "contract_id": authority.contract_id,
        "used": True,
        "production_equivalent": authority.production_equivalent,
        "execution_equivalent": authority.execution_equivalent,
        "issue_code": authority.issue_code,
        "side": authority.side,
        "quantity": authority.quantity,
        "execution_price": authority.execution_price,
        "valuation_price": authority.valuation_price,
        "request_hash": authority.request_hash,
        "broker_order_hash": authority.broker_order_hash,
        "broker_order_ref_hash_normalized": authority.broker_order_ref_hash_normalized,
        "source_path": authority.source_path,
    }


def any_fallback_match(
    authority: DemoExecutionFallbackAuthority | None,
    orders: Iterable[Any],
) -> bool:
    orders_tuple = tuple(orders)
    if authority is None:
        return False
    return any(authority.applies_to(order, orders_count=len(orders_tuple)) for order in orders_tuple)


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _hash_ref(value: object) -> str:
    encoded = json.dumps(str(value), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
