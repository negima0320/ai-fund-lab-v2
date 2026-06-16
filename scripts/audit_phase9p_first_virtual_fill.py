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

from ai_fund_lab_v2.paper_trading.first_virtual_fill import (
    DATA_NOT_READY,
    FIRST_VIRTUAL_FILL_DRY_RUN,
    FIRST_VIRTUAL_FILL_EXECUTED,
    run_first_virtual_fill,
)
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9p_first_virtual_fill.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9p_first_virtual_fill.json"
LEDGER_PATH = ROOT / ".runtime" / "phase9" / "ledger" / "latest.json"
QUOTES_PATH = ROOT / ".runtime" / "phase9" / "canonical_data" / "normalized_daily_quotes" / "data.parquet"


def main() -> int:
    before_hash = _file_hash(LEDGER_PATH)
    actual = run_first_virtual_fill(
        ledger_path=LEDGER_PATH,
        quotes_path=QUOTES_PATH,
        execution_date="2026-06-16",
        mode="execute",
        runtime_dir=ROOT / ".runtime",
        docs_report_path=DOC_PATH,
        json_report_path=JSON_PATH,
    )
    after_hash = _file_hash(LEDGER_PATH)
    temp = _run_temp_fill_cases()
    checks = {
        "actual_missing_data_returns_data_not_ready": actual.status == DATA_NOT_READY,
        "actual_missing_data_ledger_unchanged": before_hash == after_hash and actual.ledger_latest_updated is False,
        "dry_run_ledger_unchanged_with_data": temp["dry_run_status"] == FIRST_VIRTUAL_FILL_DRY_RUN and temp["dry_run_latest_updated"] is False,
        "execute_updates_ledger_with_data": temp["execute_status"] == FIRST_VIRTUAL_FILL_EXECUTED and temp["execute_latest_updated"] is True,
        "execute_filled_or_no_fill_records_saved": temp["execution_record_saved"] is True,
        "cash_updates_when_filled": Decimal(str(temp["cash_after_execute"])) == Decimal("900000"),
        "position_created_when_filled": temp["positions_after_execute"] == 1,
        "pnl_snapshot_available": temp["realized_pnl_after_execute"] == "0",
        "pending_orders_updated": temp["pending_orders_after_execute"] == 0,
        "no_fill_reason_preserved": temp["no_fill_reason"] == "DAILY_QUOTE_MISSING",
        "broker_order_not_called": actual.prohibited_flags["broker_order_api_called"] is False,
        "open_d_not_started": actual.prohibited_flags["open_d_started"] is False,
        "unlock_trade_not_called": actual.prohibited_flags["unlock_trade_called"] is False,
        "real_trade_not_executed": actual.prohibited_flags["real_trade_executed"] is False,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = actual.to_dict()
    payload.update(
        {
            "audit_status": status,
            "checks": checks,
            "temp_data_ready_case": temp,
            "ledger_hash_before": before_hash,
            "ledger_hash_after": after_hash,
        }
    )
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _run_temp_fill_cases() -> dict[str, object]:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        quotes = _write_quotes(root)
        ledger_path = _write_pending_ledger(root, code="10010")
        dry_before = _file_hash(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        dry = run_first_virtual_fill(
            ledger_path=ledger_path,
            quotes_path=quotes,
            execution_date="2026-06-16",
            mode="dry-run",
            runtime_dir=root / ".runtime",
            docs_report_path=root / "dry.md",
            json_report_path=root / "dry.json",
        )
        dry_after = _file_hash(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        execute = run_first_virtual_fill(
            ledger_path=ledger_path,
            quotes_path=quotes,
            execution_date="2026-06-16",
            mode="execute",
            runtime_dir=root / ".runtime",
            docs_report_path=root / "execute.md",
            json_report_path=root / "execute.json",
        )
        latest = load_ledger(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        nofill_ledger_path = _write_pending_ledger(root, code="99990")
        nofill = run_first_virtual_fill(
            ledger_path=nofill_ledger_path,
            quotes_path=quotes,
            execution_date="2026-06-16",
            mode="execute",
            runtime_dir=root / ".runtime",
            docs_report_path=root / "nofill.md",
            json_report_path=root / "nofill.json",
        )
        nofill_latest = load_ledger(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        return {
            "dry_run_status": dry.status,
            "dry_run_latest_updated": dry.ledger_latest_updated,
            "dry_run_hash_unchanged": dry_before == dry_after,
            "execute_status": execute.status,
            "execute_latest_updated": execute.ledger_latest_updated,
            "execution_record_saved": Path(execute.execution_record_path).is_file(),
            "cash_after_execute": str(latest.cash),
            "positions_after_execute": len(latest.positions),
            "realized_pnl_after_execute": str(latest.performance.realized_pnl),
            "unrealized_pnl_after_execute": str(latest.performance.unrealized_pnl),
            "pending_orders_after_execute": len(latest.pending_orders),
            "no_fill_status": nofill.status,
            "no_fill_count": nofill.no_fill_order_count,
            "no_fill_reason": nofill_latest.pending_orders[0].no_fill_reason if nofill_latest.pending_orders else "",
        }


def _write_pending_ledger(root: Path, *, code: str) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        pending_orders=(PendingOrderState(code=code, side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _write_quotes(root: Path) -> Path:
    path = root / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": "2026-06-16", "code": "10010", "open": 1000.0, "high": 1010.0, "low": 990.0, "close": 1005.0, "volume": 1000},
        ]
    ).to_parquet(path, index=False)
    return path


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Phase9-P First Virtual Fill",
        "",
        f"- audit_status: {payload['audit_status']}",
        f"- status: {payload['status']}",
        f"- execution_date: {payload['execution_date']}",
        f"- data_readiness: {payload['data_readiness']}",
        f"- pending_orders_before: {payload['pending_orders_before']}",
        f"- filled_order_count: {payload['filled_order_count']}",
        f"- no_fill_order_count: {payload['no_fill_order_count']}",
        f"- cash_before: {payload['cash_before']}",
        f"- cash_after: {payload['cash_after']}",
        f"- positions_before: {payload['positions_before']}",
        f"- positions_after: {payload['positions_after']}",
        f"- ledger_latest_updated: {str(payload['ledger_latest_updated']).lower()}",
        "",
        "## Checks",
        "",
    ]
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Blocked Reasons",
            "",
        ]
    )
    blocked = payload.get("blocked_reasons", [])
    lines.extend([f"- {reason}" for reason in blocked] if blocked else ["- none"])
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
        ]
    )
    return "\n".join(lines)


def _file_hash(path: Path) -> str:
    return __import__("hashlib").sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


if __name__ == "__main__":
    raise SystemExit(main())
