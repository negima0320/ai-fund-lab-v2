from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager.broker_snapshot_loader import load_latest_broker_snapshot_bundle
from ai_fund_lab_v2.order_manager.paper_ledger import PaperExecution, PaperLedger, PaperPosition
from ai_fund_lab_v2.order_manager.reconciliation import reconcile_broker_snapshot_with_paper


def _matching_paper_ledger(bundle) -> PaperLedger:
    return PaperLedger(
        cash=bundle.balance.cash_available,
        buying_power=bundle.balance.buying_power,
        positions=tuple(
            PaperPosition(issue_code=position.issue_code, issue_name=position.issue_name, quantity=position.quantity)
            for position in bundle.positions
        ),
        executions=tuple(
            PaperExecution(
                paper_execution_id=execution.execution_id,
                paper_order_id=execution.order_id,
                issue_code=execution.issue_code,
                side=execution.side,
                quantity=execution.quantity,
                price=execution.price,
                executed_at=execution.executed_at,
            )
            for execution in bundle.executions
        ),
        as_of=bundle.balance.as_of,
    )


def test_order_manager_reconciliation_ok_when_broker_and_paper_match(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    bundle = load_latest_broker_snapshot_bundle(tmp_path / ".runtime")
    paper = _matching_paper_ledger(bundle)

    result = reconcile_broker_snapshot_with_paper(bundle, paper)

    assert result.status == "OK"
    assert result.warning is False
    assert result.halt_candidate is False


def test_order_manager_reconciliation_detects_cash_and_position_mismatch(tmp_path: Path) -> None:
    write_moomoo_mock_snapshots(tmp_path / ".runtime")
    bundle = load_latest_broker_snapshot_bundle(tmp_path / ".runtime")
    paper = PaperLedger(
        cash=bundle.balance.cash_available - Decimal("1"),
        buying_power=bundle.balance.buying_power,
        positions=(PaperPosition(issue_code="7203", quantity=Decimal("1")),),
        as_of=bundle.balance.as_of,
    )

    result = reconcile_broker_snapshot_with_paper(bundle, paper)

    assert result.status == "HALT_CANDIDATE"
    assert result.warning is True
    assert result.halt_candidate is True
    assert {mismatch.mismatch_type for mismatch in result.mismatches} >= {
        "cash_mismatch",
        "position_quantity_mismatch",
    }

