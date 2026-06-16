from decimal import Decimal
from pathlib import Path

from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, PaperPosition, load_paper_ledger, write_paper_ledger


def test_paper_ledger_writes_under_order_manager_paper_path(tmp_path: Path) -> None:
    ledger = PaperLedger(
        cash=Decimal("1200000"),
        buying_power=Decimal("1150000"),
        positions=(PaperPosition(issue_code="7203", issue_name="TOYOTA", quantity=Decimal("100")),),
    )

    path = write_paper_ledger(ledger, tmp_path / ".runtime")
    loaded = load_paper_ledger(path)

    assert path.parent == tmp_path / ".runtime" / "order_manager" / "paper" / "ledgers"
    assert loaded.source == "paper"
    assert loaded.ledger_id == ledger.ledger_id
    assert loaded.positions[0].issue_code == "7203"

