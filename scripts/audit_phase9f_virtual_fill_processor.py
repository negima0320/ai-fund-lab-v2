from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_store.storage_backends import JsonlStorageBackend
from ai_fund_lab_v2.paper_trading.daily_run_result import DailyRunResult
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, PositionSnapshot, load_latest_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.ledger_integration import apply_virtual_fill_to_daily_result
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import process_virtual_fills


def run_audit(*, output_root: Path) -> dict[str, object]:
    runtime_dir = output_root / ".runtime"
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        positions=(PositionSnapshot(code="6758", name="Sony Group", quantity=Decimal("200"), average_cost=Decimal("1000"), market_value=Decimal("200000")),),
        pending_orders=(
            PendingOrderState(order_id="sell_ok", code="6758", side="SELL", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(order_id="buy_ok", code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(order_id="buy_missing", code="9999", side="BUY", quantity=Decimal("100"), status="APPROVED"),
        ),
    )
    write_ledger(ledger, runtime_dir)
    quotes = [
        {"Date": "2026-06-17", "Code": "6758", "Open": 1200},
        {"Date": "2026-06-17", "Code": "7203", "Open": 2000},
    ]
    result = process_virtual_fills(
        ledger=ledger,
        quote_rows=quotes,
        execution_date="2026-06-17",
        runtime_dir=runtime_dir,
        output_root=output_root,
        dry_run=True,
    )
    daily = apply_virtual_fill_to_daily_result(DailyRunResult(), result)
    manifest = DailyRunManifest(
        run_date="2026-06-17",
        data_until="2026-06-17",
        train_until="2026-06-16",
        decision_for="2026-06-16",
        virtual_order_date="2026-06-17",
        virtual_execution_date="2026-06-17",
        safety_status="OK",
        human_review_status="approved",
        report_status="OK",
    )
    internal_md, internal_json = write_internal_daily_report(manifest=manifest, result=daily, reports_dir=output_root / "reports" / "phase9" / "daily")
    public_md = write_public_daily_report(manifest=manifest, result=daily, reports_dir=output_root / "reports" / "public" / "phase9_daily")
    latest = load_latest_ledger(runtime_dir)
    checks = {
        "buy_fill": any(record.code == "7203" and record.status == "FILLED" for record in result.executions),
        "sell_fill": any(record.code == "6758" and record.status == "FILLED" for record in result.executions),
        "average_cost_updated": result.ledger_after.positions[-1].average_cost == Decimal("2000"),
        "realized_pnl_updated": result.ledger_after.performance.realized_pnl == Decimal("20000"),
        "cash_updated": result.ledger_after.cash == Decimal("920000"),
        "position_updated": any(position.code == "6758" and position.quantity == Decimal("100") for position in result.ledger_after.positions),
        "no_fill_reason": any(record.no_fill_reason == "DAILY_QUOTE_MISSING" for record in result.no_fill_orders),
        "ledger_before_after_diff": Path(result.ledger_before_path).exists() and Path(result.ledger_after_path).exists() and Path(result.ledger_diff_path).exists(),
        "dry_run_latest_not_overwritten": latest is not None and latest.cash == Decimal("1000000"),
        "reports_generated": internal_md.exists() and internal_json.exists() and public_md.exists(),
        "no_broker_order_api": not result.broker_order_api_called,
        "no_open_d": not result.open_d_started,
        "no_unlock_trade": not result.unlock_trade_called,
    }
    summary = {
        "phase": "Phase9-F",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "result": result.to_dict(),
        "internal_report": str(internal_md),
        "public_report": str(public_md),
    }
    audit_path = output_root / "reports" / "phase_reports" / "phase9f_virtual_fill_processor_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-F virtual fill processor.")
    parser.add_argument("--output-root", default="/private/tmp/phase9f_audit")
    args = parser.parse_args(argv)
    summary = run_audit(output_root=Path(args.output_root))
    print(json.dumps({"phase": summary["phase"], "status": summary["status"], "checks": summary["checks"]}, ensure_ascii=True, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

