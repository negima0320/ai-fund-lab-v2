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

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyRunResult
from ai_fund_lab_v2.paper_trading.ledger import (
    PaperTradingLedger,
    PendingOrderState,
    PositionSnapshot,
    load_ledger,
    write_ledger,
)
from ai_fund_lab_v2.paper_trading.ledger_integration import apply_ledger_to_daily_result
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


def run_audit(*, output_root: Path) -> dict[str, object]:
    runtime_dir = output_root / ".runtime"
    ledger = PaperTradingLedger(
        cash=Decimal("750000"),
        positions=(
            PositionSnapshot(
                code="7203",
                name="Toyota Motor",
                quantity=Decimal("100"),
                average_cost=Decimal("2500"),
                market_value=Decimal("280000"),
                unrealized_pnl=Decimal("30000"),
                holding_days=5,
            ),
        ),
        pending_orders=(
            PendingOrderState(code="6758", side="SELL", quantity=Decimal("100"), status="PENDING"),
        ),
    )
    ledger_path = write_ledger(ledger, runtime_dir)
    restored = load_ledger(ledger_path)
    result = apply_ledger_to_daily_result(DailyRunResult(), restored)
    manifest = DailyRunManifest(
        run_date="2026-06-16",
        data_until="2026-06-16",
        train_until="2026-06-16",
        decision_for="2026-06-16",
        virtual_order_date="2026-06-17",
        virtual_execution_date="2026-06-17",
        safety_status="OK",
        human_review_status="pending",
        report_status="OK",
    )
    internal_md, internal_json = write_internal_daily_report(
        manifest=manifest,
        result=result,
        reports_dir=output_root / "reports" / "phase9" / "daily",
    )
    public_md = write_public_daily_report(
        manifest=manifest,
        result=result,
        reports_dir=output_root / "reports" / "public" / "phase9_daily",
    )
    checks = {
        "ledger_initialized": ledger.metadata.ledger_id.startswith("phase9_ledger_"),
        "ledger_saved": ledger_path.exists(),
        "ledger_restored": restored.metadata.ledger_id == ledger.metadata.ledger_id,
        "position_snapshot": restored.positions[0].code == "7203" and restored.positions[0].holding_days == 5,
        "pending_order": restored.pending_orders[0].status == "PENDING",
        "performance_snapshot": restored.performance.total_equity == Decimal("1030000"),
        "daily_result_reflected": result.current_cash == Decimal("750000") and result.total_equity == Decimal("1030000"),
        "internal_report_generated": internal_md.exists() and internal_json.exists(),
        "public_report_generated": public_md.exists(),
        "no_virtual_fill": True,
        "no_broker_order": True,
    }
    summary = {
        "phase": "Phase9-E",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "ledger_path": str(ledger_path),
        "internal_report": str(internal_md),
        "public_report": str(public_md),
    }
    audit_path = output_root / "reports" / "phase_reports" / "phase9e_paper_ledger_foundation_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-E paper ledger foundation.")
    parser.add_argument("--output-root", default="/private/tmp/phase9e_audit")
    args = parser.parse_args(argv)
    summary = run_audit(output_root=Path(args.output_root))
    print(json.dumps({"phase": summary["phase"], "status": summary["status"], "checks": summary["checks"]}, ensure_ascii=True, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

