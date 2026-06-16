import json
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager.allocation_decision_loader import load_allocation_decision_set
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import load_latest_broker_snapshot_bundle
from ai_fund_lab_v2.order_manager.order_plan_generator import generate_order_plan
from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, PaperPosition
from ai_fund_lab_v2.order_manager.paper_ledger_update import apply_order_plan_to_paper_ledger
from ai_fund_lab_v2.order_manager.reconciliation import reconcile_broker_snapshot_with_paper


def test_paper_ledger_update_applies_sell_before_dependent_buy(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    bundle = load_latest_broker_snapshot_bundle(tmp_path / ".runtime")
    paper = PaperLedger(
        cash=bundle.balance.cash_available,
        buying_power=bundle.balance.buying_power,
        positions=tuple(PaperPosition(issue_code=p.issue_code, issue_name=p.issue_name, quantity=p.quantity) for p in bundle.positions),
        as_of=bundle.balance.as_of,
    )
    allocation_path = tmp_path / "allocation.json"
    allocation_path.write_text(
        json.dumps(
            {
                "decisions": [
                    {"issue_code": "7203", "side": "SELL", "quantity": 100, "estimated_price": "2600", "replacement_group_id": "r1"},
                    {"issue_code": "6501", "side": "BUY", "quantity": 100, "estimated_price": "3000", "replacement_group_id": "r1"},
                ]
            }
        ),
        encoding="utf-8",
    )
    plan = generate_order_plan(
        allocation=load_allocation_decision_set(allocation_path),
        broker=bundle,
        paper=paper,
        reconciliation=reconcile_broker_snapshot_with_paper(bundle, paper),
        runtime_dir=tmp_path / ".runtime",
    )

    updated = apply_order_plan_to_paper_ledger(plan, paper)

    quantities = {position.issue_code: position.quantity for position in updated.positions}
    assert quantities.get("7203", 0) == 0
    assert quantities["6501"] == 100
    assert len(updated.executions) == 2

