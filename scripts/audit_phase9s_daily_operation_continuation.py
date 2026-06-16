from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys
import tempfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.business_day_tracker import TRACKER_DUPLICATE_BLOCKED, TRACKER_UPDATED, update_business_day_tracker
from ai_fund_lab_v2.paper_trading.daily_continuation import DAILY_CONTINUATION_COMPLETED, run_daily_continuation
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, load_ledger, write_ledger


def main() -> int:
    checks: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger_path = _write_ledger(root)
        quotes_path = _write_quotes(root)
        tracker = update_business_day_tracker(
            ledger_path=ledger_path,
            business_day_index=1,
            run_date="2026-06-16",
            decision_for="2026-06-15",
            status="FIRST_VIRTUAL_FILL_DONE",
            tracker_root=root / ".runtime" / "phase9" / "tracker",
            report_root=root / "reports" / "phase9" / "tracker",
            overrides={
                "paper_total_equity": "1000000",
                "cash": "283330.0",
                "market_value": "716670.0",
                "realized_pnl": "0",
                "unrealized_pnl": "0",
                "positions": 5,
                "trade_count": 5,
            },
        )
        checks.append({"name": "tracker_day1_append", "ok": tracker.status == TRACKER_UPDATED})
        duplicate = update_business_day_tracker(
            ledger_path=ledger_path,
            business_day_index=1,
            run_date="2026-06-16",
            decision_for="2026-06-15",
            status="FIRST_VIRTUAL_FILL_DONE",
            tracker_root=root / ".runtime" / "phase9" / "tracker",
            report_root=root / "reports" / "phase9" / "tracker",
        )
        checks.append({"name": "tracker_duplicate_block", "ok": duplicate.status == TRACKER_DUPLICATE_BLOCKED})
        result = run_daily_continuation(
            run_date="2026-06-16",
            ledger_path=ledger_path,
            quotes_path=quotes_path,
            mode="paper-trading",
            runtime_dir=root / ".runtime",
            update_tracker=False,
            docs_report_path=root / "docs" / "phase9s.md",
            json_report_path=root / "reports" / "phase9s.json",
        )
        latest = load_ledger(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        checks.append({"name": "daily_continuation_completed", "ok": result.status == DAILY_CONTINUATION_COMPLETED})
        checks.append({"name": "ledger_valuation_updated", "ok": latest.performance.total_equity == Decimal("993140.0")})
        checks.append({"name": "performance_report_written", "ok": Path(result.performance_report_json_path).is_file()})
        checks.append({"name": "position_management_input_count", "ok": result.position_management_input_count == 5})
        checks.append({"name": "pending_not_created_without_features", "ok": result.created_pending_order_count == 0})
        checks.append({"name": "no_virtual_fill", "ok": result.virtual_fill_executed is False})
        checks.append({"name": "broker_safety_flags", "ok": not result.broker_order_api_called and not result.open_d_started and not result.unlock_trade_called})
    passed = all(bool(check["ok"]) for check in checks)
    payload = {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "virtual_fill_executed": False,
        "scheduler_auto_registered": False,
    }
    out = Path("reports/phase_reports/phase9s_daily_operation_continuation_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 0 if passed else 1


def _write_ledger(root: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("283330.0"),
        positions=(
            PositionSnapshot(code="15790", quantity=Decimal("200"), average_cost=Decimal("846.8"), market_value=Decimal("169360.0")),
            PositionSnapshot(code="166A0", quantity=Decimal("100"), average_cost=Decimal("1091.0"), market_value=Decimal("109100.0")),
            PositionSnapshot(code="213A0", quantity=Decimal("300"), average_cost=Decimal("544.7"), market_value=Decimal("163410.0")),
            PositionSnapshot(code="221A0", quantity=Decimal("100"), average_cost=Decimal("1538.0"), market_value=Decimal("153800.0")),
            PositionSnapshot(code="30630", quantity=Decimal("100"), average_cost=Decimal("1210.0"), market_value=Decimal("121000.0")),
        ),
        performance=PerformanceSnapshot(
            total_equity=Decimal("1000000.0"),
            cash=Decimal("283330.0"),
            market_value=Decimal("716670.0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            trade_count=5,
        ),
    )
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _write_quotes(root: Path) -> Path:
    path = root / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": "2026-06-16", "code": "15790", "close": 845.8},
            {"date": "2026-06-16", "code": "166A0", "close": 1112.0},
            {"date": "2026-06-16", "code": "213A0", "close": 542.5},
            {"date": "2026-06-16", "code": "221A0", "close": 1530.0},
            {"date": "2026-06-16", "code": "30630", "close": 1137.0},
        ]
    ).to_parquet(path, index=False)
    return path


if __name__ == "__main__":
    raise SystemExit(main())
