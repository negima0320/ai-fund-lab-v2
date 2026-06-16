import json
from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager.allocation_decision_loader import load_allocation_decision_set
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import load_latest_broker_snapshot_bundle
from ai_fund_lab_v2.order_manager.order_plan_generator import generate_order_plan
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, PaperPosition
from ai_fund_lab_v2.order_manager.reconciliation import reconcile_broker_snapshot_with_paper


def _bundle_and_paper(tmp_path: Path):
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    bundle = load_latest_broker_snapshot_bundle(tmp_path / ".runtime")
    paper = PaperLedger(
        cash=bundle.balance.cash_available,
        buying_power=bundle.balance.buying_power,
        positions=tuple(PaperPosition(issue_code=p.issue_code, issue_name=p.issue_name, quantity=p.quantity) for p in bundle.positions),
        as_of=bundle.balance.as_of,
    )
    return bundle, paper


def test_order_plan_generator_creates_buy_sell_hold_with_dependency(tmp_path: Path) -> None:
    bundle, paper = _bundle_and_paper(tmp_path)
    allocation_path = tmp_path / "allocation.json"
    allocation_path.write_text(
        json.dumps(
            {
                "policy_id": "CAP5",
                "decisions": [
                    {
                        "decision_id": "sell1",
                        "issue_code": "7203",
                        "side": "SELL",
                        "quantity": 100,
                        "estimated_price": "2600",
                        "replacement_group_id": "r1",
                    },
                    {
                        "decision_id": "buy1",
                        "issue_code": "6501",
                        "side": "BUY",
                        "quantity": 100,
                        "estimated_price": "3000",
                        "replacement_group_id": "r1",
                    },
                    {"decision_id": "hold1", "issue_code": "6758", "side": "HOLD", "quantity": 100, "estimated_price": "13100"},
                ],
            }
        ),
        encoding="utf-8",
    )
    allocation = load_allocation_decision_set(allocation_path)
    reconciliation = reconcile_broker_snapshot_with_paper(bundle, paper)

    plan = generate_order_plan(
        allocation=allocation,
        broker=bundle,
        paper=paper,
        reconciliation=reconciliation,
        runtime_dir=tmp_path / ".runtime",
    )

    assert plan.plan_status.value == "READY_FOR_REVIEW"
    assert plan.executable is False
    assert {item.side.value for item in plan.items} == {"BUY", "SELL", "HOLD"}
    buy = next(item for item in plan.items if item.side.value == "BUY")
    sell = next(item for item in plan.items if item.side.value == "SELL")
    assert buy.depends_on_fill_item_id == sell.item_id
    assert buy.requires_broker_snapshot_refresh is True


def test_order_plan_generator_reconciliation_halt_is_review_only(tmp_path: Path) -> None:
    bundle, paper = _bundle_and_paper(tmp_path)
    bad_paper = PaperLedger(cash=Decimal("1"), buying_power=Decimal("1"), as_of=bundle.balance.as_of)
    reconciliation = reconcile_broker_snapshot_with_paper(bundle, bad_paper)
    allocation_path = tmp_path / "allocation.json"
    allocation_path.write_text(json.dumps({"decisions": [{"issue_code": "7203", "side": "HOLD", "quantity": 100, "estimated_price": "1"}]}), encoding="utf-8")

    plan = generate_order_plan(
        allocation=load_allocation_decision_set(allocation_path),
        broker=bundle,
        paper=bad_paper,
        reconciliation=reconciliation,
        runtime_dir=tmp_path / ".runtime",
    )

    assert plan.plan_status.value == "REVIEW_ONLY_RECONCILIATION_HALT"
    assert plan.items[0].action == "BLOCKED_BY_BROKER_MISMATCH"


def test_order_plan_generator_locked_is_review_only(tmp_path: Path) -> None:
    bundle, paper = _bundle_and_paper(tmp_path)
    reconciliation = reconcile_broker_snapshot_with_paper(bundle, paper)
    lock_dir = tmp_path / ".runtime" / "safety" / "locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / "lock.json").write_text(json.dumps({"is_locked": True, "status": "LOCKED"}), encoding="utf-8")
    allocation_path = tmp_path / "allocation.json"
    allocation_path.write_text(json.dumps({"decisions": [{"issue_code": "7203", "side": "HOLD", "quantity": 100, "estimated_price": "1"}]}), encoding="utf-8")

    plan = generate_order_plan(
        allocation=load_allocation_decision_set(allocation_path),
        broker=bundle,
        paper=paper,
        reconciliation=reconciliation,
        runtime_dir=tmp_path / ".runtime",
    )

    assert plan.plan_status.value == "REVIEW_ONLY_LOCKED"
    assert plan.executable is False

