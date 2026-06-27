from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.paper_trading.approval_mode import AUTO_APPROVAL_REVIEW_STATUS, AUTO_FOR_PAPER_TRADING
from ai_fund_lab_v2.paper_trading.human_review_artifact import load_human_review
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.pending_order_dedup import pending_order_fingerprint, pending_order_legacy_fingerprint


PENDING_ORDERS_CREATED = "PENDING_ORDERS_CREATED"
PENDING_ORDERS_SKIPPED = "PENDING_ORDERS_SKIPPED"
PENDING_ORDERS_BLOCKED = "PENDING_ORDERS_BLOCKED"
PENDING_ORDERS_DEDUP_SKIPPED = "PENDING_ORDERS_DEDUP_SKIPPED"


@dataclass(frozen=True)
class PendingOrderCreationResult:
    status: str
    review_status: str
    pending_order_created: bool
    pending_order_count: int
    dedup_skipped_count: int = 0
    ledger_path: str = ""
    latest_path: str = ""
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    prohibited_flags: dict[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prohibited_flags"] = self.prohibited_flags or prohibited_flags()
        return payload


def create_pending_orders_from_approved_review(
    *,
    ledger_path: Path | str,
    order_plan_path: Path | str,
    human_review_path: Path | str,
    runtime_dir: Path | str = ".runtime",
) -> PendingOrderCreationResult:
    review = load_human_review(human_review_path)
    review_status = str(review.get("review_status") or "").lower()
    auto_approved = review_status == AUTO_APPROVAL_REVIEW_STATUS
    if auto_approved:
        blocked = _auto_approval_violations(review)
        if blocked:
            return PendingOrderCreationResult(
                status=PENDING_ORDERS_BLOCKED,
                review_status=review_status,
                pending_order_created=False,
                pending_order_count=0,
                ledger_path=str(ledger_path),
                blocked_reasons=tuple(blocked),
                prohibited_flags=prohibited_flags(),
            )
    if review_status not in {"approved", AUTO_APPROVAL_REVIEW_STATUS}:
        return PendingOrderCreationResult(
            status=PENDING_ORDERS_SKIPPED,
            review_status=review_status,
            pending_order_created=False,
            pending_order_count=0,
            ledger_path=str(ledger_path),
            latest_path=str(Path(runtime_dir) / "phase9" / "ledger" / "latest.json"),
            warnings=(f"review_status_{review_status}_no_pending_order",),
            prohibited_flags=prohibited_flags(),
        )
    order_plan = _load_order_plan(order_plan_path)
    blocked = _order_plan_invariant_violations(order_plan)
    if blocked:
        return PendingOrderCreationResult(
            status=PENDING_ORDERS_BLOCKED,
            review_status=review_status,
            pending_order_created=False,
            pending_order_count=0,
            ledger_path=str(ledger_path),
            blocked_reasons=tuple(blocked),
            prohibited_flags=prohibited_flags(),
        )
    items = [dict(item) for item in order_plan.get("items", []) if isinstance(item, dict)]
    ledger = load_ledger(ledger_path)
    existing_order_ids = {order.order_id for order in ledger.pending_orders}
    existing_fingerprints = {pending_order_fingerprint(order) for order in ledger.pending_orders}
    existing_legacy_fingerprints = {pending_order_legacy_fingerprint(order) for order in ledger.pending_orders}
    orders_list: list[PendingOrderState] = []
    dedup_skipped = 0
    for item in items:
        if not _is_order_side(item):
            continue
        if str(item.get("order_id") or "") in existing_order_ids:
            dedup_skipped += 1
            continue
        order = _pending_order_from_item(item, review=review, order_plan=order_plan)
        if pending_order_fingerprint(order) in existing_fingerprints or pending_order_legacy_fingerprint(order) in existing_legacy_fingerprints:
            dedup_skipped += 1
            continue
        orders_list.append(order)
        existing_fingerprints.add(pending_order_fingerprint(order))
        existing_legacy_fingerprints.add(pending_order_legacy_fingerprint(order))
    orders = tuple(orders_list)
    updated = PaperTradingLedger(
        cash=ledger.cash,
        positions=ledger.positions,
        pending_orders=ledger.pending_orders + orders,
        performance=ledger.performance,
        metadata=ledger.metadata,
    )
    written_path = write_ledger(updated, runtime_dir=runtime_dir)
    status = PENDING_ORDERS_CREATED if orders else (PENDING_ORDERS_DEDUP_SKIPPED if dedup_skipped else PENDING_ORDERS_SKIPPED)
    return PendingOrderCreationResult(
        status=status,
        review_status=review_status,
        pending_order_created=bool(orders),
        pending_order_count=len(orders),
        dedup_skipped_count=dedup_skipped,
        ledger_path=str(written_path),
        latest_path=str(Path(runtime_dir) / "phase9" / "ledger" / "latest.json"),
        warnings=() if dedup_skipped == 0 else (f"pending_order_dedup_skipped={dedup_skipped}",),
        prohibited_flags=prohibited_flags(),
    )


def prohibited_flags() -> dict[str, bool]:
    return {
        "broker_order_api_called": False,
        "moomoo_simulate_order_called": False,
        "tachibana_order_called": False,
        "open_d_started": False,
        "login_called": False,
        "logout_called": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _pending_order_from_item(item: dict[str, Any], *, review: dict[str, Any], order_plan: dict[str, Any]) -> PendingOrderState:
    return PendingOrderState(
        order_id=str(item.get("order_id") or ""),
        code=str(item.get("code") or item.get("issue_code") or ""),
        side=str(item.get("side") or "").upper(),
        quantity=_decimal(item.get("quantity") or item.get("planned_quantity")),
        status="APPROVED",
        planned_amount=_decimal(item.get("planned_amount")),
        virtual_order_date=str(review.get("virtual_order_date") or order_plan.get("virtual_order_date") or ""),
        virtual_execution_date=str(review.get("virtual_execution_date") or order_plan.get("virtual_execution_date") or review.get("virtual_order_date") or ""),
        decision_for=str(order_plan.get("decision_for") or review.get("decision_for") or ""),
        reason=str(item.get("reason") or item.get("short_reason") or ""),
        review_status=str(review.get("review_status") or ""),
    )


def _is_order_side(item: dict[str, Any]) -> bool:
    return str(item.get("side") or "").upper() in {"BUY", "SELL"}


def _load_order_plan(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("OrderPlan artifact must be a JSON object.")
    return payload


def _order_plan_invariant_violations(order_plan: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    if order_plan.get("executable") is not False:
        blocked.append("order_plan_executable_not_false")
    if order_plan.get("live_order_allowed") is not False:
        blocked.append("order_plan_live_order_allowed_not_false")
    if order_plan.get("requires_human_review") is not True:
        blocked.append("order_plan_requires_human_review_not_true")
    return blocked


def _auto_approval_violations(review: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    if review.get("approval_mode") != AUTO_FOR_PAPER_TRADING:
        blocked.append("auto_approval_mode_not_auto_for_paper_trading")
    if review.get("execution_mode") == "broker":
        blocked.append("auto_approval_blocked_in_broker_mode")
    if review.get("broker_order_api_called") is not False:
        blocked.append("auto_approval_broker_order_api_called_not_false")
    if review.get("live_order_allowed") is not False:
        blocked.append("auto_approval_live_order_allowed_not_false")
    if review.get("executable") is not False:
        blocked.append("auto_approval_executable_not_false")
    if review.get("virtual_fill_executed") is not False:
        blocked.append("auto_approval_virtual_fill_executed_not_false")
    return blocked


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
