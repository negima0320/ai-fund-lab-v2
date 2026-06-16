from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.paper_trading.human_review_artifact import create_human_review_request
from ai_fund_lab_v2.paper_trading.initial_ledger import create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger
from ai_fund_lab_v2.paper_trading.pending_order_creator import (
    PENDING_ORDERS_BLOCKED,
    PENDING_ORDERS_CREATED,
    PENDING_ORDERS_SKIPPED,
    create_pending_orders_from_approved_review,
)


def test_pending_rejected_needs_change_do_not_create_orders(tmp_path: Path) -> None:
    ledger_path = _create_ledger(tmp_path)
    order_plan = _write_order_plan(tmp_path)
    review = create_human_review_request(
        order_plan_path=order_plan,
        decision_for="2026-06-15",
        virtual_order_date="2026-06-16",
        output_root=tmp_path / "review",
    )

    for status in ("pending", "rejected", "needs_change"):
        review_path = _with_review_status(Path(review.json_path), status, tmp_path / status)
        result = create_pending_orders_from_approved_review(
            ledger_path=ledger_path,
            order_plan_path=order_plan,
            human_review_path=review_path,
            runtime_dir=tmp_path / ".runtime",
        )
        assert result.status == PENDING_ORDERS_SKIPPED
        assert result.pending_order_created is False
        assert len(load_ledger(ledger_path).pending_orders) == 0


def test_approved_creates_pending_orders_without_fill(tmp_path: Path) -> None:
    ledger_path = _create_ledger(tmp_path)
    order_plan = _write_order_plan(tmp_path)
    review = create_human_review_request(
        order_plan_path=order_plan,
        decision_for="2026-06-15",
        virtual_order_date="2026-06-16",
        output_root=tmp_path / "review",
    )
    approved = _with_review_status(Path(review.json_path), "approved", tmp_path / "approved")

    result = create_pending_orders_from_approved_review(
        ledger_path=ledger_path,
        order_plan_path=order_plan,
        human_review_path=approved,
        runtime_dir=tmp_path / ".runtime",
    )
    ledger = load_ledger(tmp_path / ".runtime" / "phase9" / "ledger" / "latest.json")

    assert result.status == PENDING_ORDERS_CREATED
    assert result.pending_order_count == 1
    assert ledger.cash == Decimal("1000000")
    assert len(ledger.positions) == 0
    assert len(ledger.pending_orders) == 1
    assert ledger.pending_orders[0].status == "APPROVED"
    assert ledger.pending_orders[0].virtual_execution_date == "2026-06-16"
    assert result.prohibited_flags["virtual_fill_executed"] is False


def test_order_plan_invariant_enforced_before_pending_order_creation(tmp_path: Path) -> None:
    ledger_path = _create_ledger(tmp_path)
    order_plan = _write_order_plan(tmp_path, live_order_allowed=True)
    review_path = tmp_path / "approved.json"
    review_path.write_text(json.dumps({"review_status": "approved"}), encoding="utf-8")

    result = create_pending_orders_from_approved_review(
        ledger_path=ledger_path,
        order_plan_path=order_plan,
        human_review_path=review_path,
        runtime_dir=tmp_path / ".runtime",
    )

    assert result.status == PENDING_ORDERS_BLOCKED
    assert "order_plan_live_order_allowed_not_false" in result.blocked_reasons


def _create_ledger(tmp_path: Path) -> Path:
    result = create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=tmp_path / ".runtime" / "phase9" / "ledger",
        start_date="2026-06-16",
    )
    return Path(result.latest_path)


def _write_order_plan(tmp_path: Path, *, live_order_allowed: bool = False) -> Path:
    path = tmp_path / "order_plan.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "run1",
                "decision_for": "2026-06-15",
                "data_until": "2026-06-15",
                "virtual_execution_date": "2026-06-16",
                "executable": False,
                "live_order_allowed": live_order_allowed,
                "requires_human_review": True,
                "items": [
                    {
                        "order_id": "order1",
                        "code": "10010",
                        "side": "BUY",
                        "quantity": 100,
                        "planned_amount": "100000",
                        "reason": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _with_review_status(source: Path, status: str, output_dir: Path) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["review_status"] = status
    payload["reviewed_at"] = "2026-06-16T00:00:00+00:00"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path

