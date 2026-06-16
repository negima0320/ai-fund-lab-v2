from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.paper_ledger import PaperExecution, PaperLedger, PaperPosition, write_paper_ledger
from ai_fund_lab_v2.order_manager.paper_ledger_diff import diff_paper_ledgers, latest_two_paper_ledgers, write_paper_ledger_diff


def test_paper_ledger_diff_reports_cash_positions_and_executions(tmp_path: Path) -> None:
    before = PaperLedger(
        cash=Decimal("1000"),
        buying_power=Decimal("1000"),
        positions=(PaperPosition(issue_code="7203", quantity=Decimal("100")),),
        ledger_id="paper_before",
    )
    after = PaperLedger(
        cash=Decimal("500"),
        buying_power=Decimal("500"),
        positions=(PaperPosition(issue_code="6501", quantity=Decimal("100")),),
        executions=(
            PaperExecution(
                paper_execution_id="paper_exec_1",
                paper_order_id="item1",
                issue_code="6501",
                side="BUY",
                quantity=Decimal("100"),
                price=Decimal("5"),
                executed_at="2026-06-16T00:00:00+00:00",
            ),
        ),
        ledger_id="paper_after",
    )

    diff = diff_paper_ledgers(before, after, blocked_or_waiting_items=("buy_waiting",))

    assert diff.cash_delta == Decimal("-500")
    assert diff.position_deltas["7203"] == "-100"
    assert diff.position_deltas["6501"] == "100"
    assert diff.new_execution_ids == ("paper_exec_1",)
    assert diff.blocked_or_waiting_items == ("buy_waiting",)
    path = write_paper_ledger_diff(before, after, runtime_dir=tmp_path / ".runtime")
    assert path.exists()


def test_latest_two_paper_ledgers_reads_history(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    first = write_paper_ledger(PaperLedger(cash=Decimal("100"), buying_power=Decimal("100"), ledger_id="first"), runtime_dir)
    second = write_paper_ledger(PaperLedger(cash=Decimal("200"), buying_power=Decimal("200"), ledger_id="second"), runtime_dir)

    before, after = latest_two_paper_ledgers(runtime_dir)

    assert {before.ledger_id, after.ledger_id} == {"first", "second"}
    assert first.exists() and second.exists()
