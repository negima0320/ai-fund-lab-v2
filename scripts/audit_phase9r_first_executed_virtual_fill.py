from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.first_virtual_fill import FIRST_VIRTUAL_FILL_DRY_RUN, FIRST_VIRTUAL_FILL_EXECUTED, run_first_virtual_fill
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9r_first_executed_virtual_fill.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9r_first_executed_virtual_fill.json"
LEDGER_PATH = ROOT / ".runtime" / "phase9" / "ledger" / "latest.json"
SNAPSHOT_DIR = ROOT / ".runtime" / "phase9" / "ledger_runs" / "2026-06-16_first_virtual_fill"
EXECUTION_PATH = ROOT / ".runtime" / "phase9" / "ledger" / "executions" / "2026-06-16_executions.json"


def main() -> int:
    report = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    ledger = load_ledger(LEDGER_PATH)
    temp = _run_temp_audit_cases()
    positions = [
        {
            "code": position.code,
            "quantity": str(position.quantity),
            "average_cost": str(position.average_cost),
            "market_value": str(position.market_value),
            "unrealized_pnl": str(position.unrealized_pnl),
        }
        for position in ledger.positions
    ]
    expected_cash = Decimal("283330.0")
    expected_average_costs = {
        "15790": Decimal("846.8"),
        "166A0": Decimal("1091.0"),
        "213A0": Decimal("544.7"),
        "221A0": Decimal("1538.0"),
        "30630": Decimal("1210.0"),
    }
    actual_average_costs = {position.code: position.average_cost for position in ledger.positions}
    checks = {
        "dry_run_latest_not_updated_temp": temp["dry_run_status"] == FIRST_VIRTUAL_FILL_DRY_RUN and temp["dry_run_latest_updated"] is False,
        "execute_latest_updated_reported": report["ledger_latest_updated"] is True,
        "pending_order_5_processed": report["pending_orders_before"] == 5,
        "filled_no_fill_reported": report["filled_order_count"] == 5 and report["no_fill_order_count"] == 0,
        "cash_decreased_correctly": ledger.cash == expected_cash,
        "positions_created": len(ledger.positions) == 5,
        "average_cost_matches_open_price": actual_average_costs == expected_average_costs,
        "execution_record_saved": EXECUTION_PATH.is_file(),
        "ledger_snapshots_saved": all((SNAPSHOT_DIR / name).is_file() for name in ("ledger_before.json", "ledger_after.json", "ledger_diff.json", "virtual_fill_manifest.json")),
        "pending_orders_cleared": len(ledger.pending_orders) == 0,
        "performance_trade_count_5": ledger.performance.trade_count == 5,
        "realized_pnl_zero": ledger.performance.realized_pnl == Decimal("0"),
        "unrealized_pnl_zero": ledger.performance.unrealized_pnl == Decimal("0.0"),
        "no_fill_preserved_temp": temp["no_fill_reason"] == "CASH_INSUFFICIENT",
        "broker_order_not_called": report["prohibited_flags"]["broker_order_api_called"] is False,
        "open_d_not_started": report["prohibited_flags"]["open_d_started"] is False,
        "unlock_trade_not_called": report["prohibited_flags"]["unlock_trade_called"] is False,
        "real_trade_not_executed": report["prohibited_flags"]["real_trade_executed"] is False,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        **report,
        "audit_status": status,
        "checks": checks,
        "position_list": positions,
        "ledger_latest": {
            "cash": str(ledger.cash),
            "positions_count": len(ledger.positions),
            "pending_orders_count": len(ledger.pending_orders),
            "realized_pnl": str(ledger.performance.realized_pnl),
            "unrealized_pnl": str(ledger.performance.unrealized_pnl),
            "trade_count": ledger.performance.trade_count,
        },
        "temp_audit_cases": temp,
        "next_action": "Proceed to Phase9-S daily report/tracker update for the first filled trading day.",
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _run_temp_audit_cases() -> dict[str, object]:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        ledger_path = _write_phase9r_ledger(root, cash=Decimal("1000000"))
        quotes_path = _write_phase9r_quotes(root)
        dry = run_first_virtual_fill(
            ledger_path=ledger_path,
            quotes_path=quotes_path,
            execution_date="2026-06-16",
            mode="dry-run",
            runtime_dir=root / ".runtime",
            docs_report_path=root / "dry.md",
            json_report_path=root / "dry.json",
        )
        execute = run_first_virtual_fill(
            ledger_path=ledger_path,
            quotes_path=quotes_path,
            execution_date="2026-06-16",
            mode="execute",
            runtime_dir=root / ".runtime",
            docs_report_path=root / "execute.md",
            json_report_path=root / "execute.json",
        )
        nofill_ledger_path = _write_phase9r_ledger(root / "nofill", cash=Decimal("1000"))
        nofill = run_first_virtual_fill(
            ledger_path=nofill_ledger_path,
            quotes_path=quotes_path,
            execution_date="2026-06-16",
            mode="execute",
            runtime_dir=root / "nofill" / ".runtime",
            docs_report_path=root / "nofill.md",
            json_report_path=root / "nofill.json",
        )
        nofill_latest = load_ledger(root / "nofill" / ".runtime" / "phase9" / "ledger" / "latest.json")
        return {
            "dry_run_status": dry.status,
            "dry_run_latest_updated": dry.ledger_latest_updated,
            "execute_status": execute.status,
            "execute_latest_updated": execute.ledger_latest_updated,
            "execute_filled_count": execute.filled_order_count,
            "no_fill_count": nofill.no_fill_order_count,
            "no_fill_reason": nofill_latest.pending_orders[0].no_fill_reason if nofill_latest.pending_orders else "",
        }


def _write_phase9r_ledger(root: Path, *, cash: Decimal) -> Path:
    ledger = PaperTradingLedger(
        cash=cash,
        pending_orders=(
            PendingOrderState(code="15790", side="BUY", quantity=Decimal("200"), status="APPROVED"),
            PendingOrderState(code="166A0", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="213A0", side="BUY", quantity=Decimal("300"), status="APPROVED"),
            PendingOrderState(code="221A0", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="30630", side="BUY", quantity=Decimal("100"), status="APPROVED"),
        ),
    )
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _write_phase9r_quotes(root: Path) -> Path:
    path = root / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": "2026-06-16", "code": "15790", "open": 846.8},
            {"date": "2026-06-16", "code": "166A0", "open": 1091.0},
            {"date": "2026-06-16", "code": "213A0", "open": 544.7},
            {"date": "2026-06-16", "code": "221A0", "open": 1538.0},
            {"date": "2026-06-16", "code": "30630", "open": 1210.0},
        ]
    ).to_parquet(path, index=False)
    return path


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Phase9-R First Executed Virtual Fill",
        "",
        f"- audit_status: {payload['audit_status']}",
        f"- status: {payload['status']}",
        f"- execution_date: {payload['execution_date']}",
        f"- pending_orders_before: {payload['pending_orders_before']}",
        f"- filled_order_count: {payload['filled_order_count']}",
        f"- no_fill_order_count: {payload['no_fill_order_count']}",
        f"- cash_before: {payload['cash_before']}",
        f"- cash_after: {payload['cash_after']}",
        f"- positions_before: {payload['positions_before']}",
        f"- positions_after: {payload['positions_after']}",
        f"- realized_pnl: {payload['realized_pnl']}",
        f"- unrealized_pnl: {payload['unrealized_pnl']}",
        f"- trade_count: {payload['ledger_latest']['trade_count']}",
        f"- ledger_latest_updated: {str(payload['ledger_latest_updated']).lower()}",
        "",
        "## Position List",
        "",
    ]
    for position in payload["position_list"]:
        lines.append(
            "- "
            f"{position['code']}"
            f" qty={position['quantity']}"
            f" avg={position['average_cost']}"
            f" market_value={position['market_value']}"
            f" unrealized_pnl={position['unrealized_pnl']}"
        )
    lines.extend(
        [
            "",
            "## Paths",
            "",
            f"- ledger_snapshot_dir: {payload['ledger_snapshot_dir']}",
            f"- execution_record_path: {payload['execution_record_path']}",
            "",
            "## Checks",
            "",
        ]
    )
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "- real_trade_executed: false",
            "",
            "## Next Action",
            "",
            payload["next_action"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

