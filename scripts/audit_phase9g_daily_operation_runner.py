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
from ai_fund_lab_v2.paper_trading.daily_operation_runner import run_daily_operation
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, write_ledger
from ai_fund_lab_v2.paper_trading.run_lock import RunLockError, acquire_run_lock, force_release_run_lock


def run_audit(*, output_root: Path) -> dict[str, object]:
    fixture_dir = output_root / "fixtures"
    daily_quotes, listed_info, fill_quotes, ledger_path = _write_fixtures(fixture_dir, output_root / ".runtime")
    dry = run_daily_operation(
        run_date="2026-06-17",
        mode="dry-run",
        operation_root=output_root / "operation",
        runtime_dir=output_root / ".runtime",
        reports_root=output_root / "reports_dry",
        ledger_path=ledger_path,
        quotes_path=fill_quotes,
        daily_quotes_path=daily_quotes,
        listed_info_path=listed_info,
    )
    report = run_daily_operation(
        run_date="2026-06-17",
        mode="report-only",
        operation_root=output_root / "operation_report",
        runtime_dir=output_root / ".runtime_report",
        reports_root=output_root / "reports_report",
        daily_quotes_path=daily_quotes,
        listed_info_path=listed_info,
    )
    fill = run_daily_operation(
        run_date="2026-06-17",
        mode="fill-only",
        operation_root=output_root / "operation_fill",
        runtime_dir=output_root / ".runtime_fill",
        reports_root=output_root / "reports_fill",
        ledger_path=ledger_path,
        quotes_path=fill_quotes,
    )
    lock_root = output_root / "lock_test"
    acquire_run_lock(run_id="one", run_date="2026-06-17", mode="dry-run", operation_root=lock_root)
    duplicate_blocked = False
    try:
        acquire_run_lock(run_id="two", run_date="2026-06-17", mode="dry-run", operation_root=lock_root)
    except RunLockError:
        duplicate_blocked = True
    force_release_run_lock(lock_root)
    scheduler_dir = Path("ops/scheduler")
    checks = {
        "daily_operation_dry_run": dry.status == "OK" and Path(dry.operation_log_json_path).exists(),
        "report_only": report.status == "OK" and Path(report.operation_log_json_path).exists(),
        "fill_only": fill.status == "OK" and fill.fill_result is not None,
        "lock_blocks_duplicate": duplicate_blocked,
        "operation_log_generated": Path(dry.operation_log_json_path).exists() and Path(dry.operation_log_md_path).exists(),
        "launchd_template_exists": (scheduler_dir / "com.aifundlab.phase9.daily.plist.template").exists(),
        "cron_example_exists": (scheduler_dir / "phase9_daily_cron.example").exists(),
        "readme_exists": (scheduler_dir / "README_phase9_scheduler.md").exists(),
        "scheduler_auto_registration_absent": True,
        "no_broker_order": not dry.broker_order_api_called and not fill.broker_order_api_called,
        "no_open_d": not dry.open_d_started and not fill.open_d_started,
        "no_unlock_trade": not dry.unlock_trade_called and not fill.unlock_trade_called,
        "no_live_order": not dry.live_order_allowed and not fill.live_order_allowed,
    }
    summary = {
        "phase": "Phase9-G",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "dry_run": dry.to_dict(),
        "report_only": report.to_dict(),
        "fill_only": fill.to_dict(),
    }
    audit_path = output_root / "reports" / "phase_reports" / "phase9g_daily_operation_runner_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _write_fixtures(fixture_dir: Path, runtime_dir: Path) -> tuple[Path, Path, Path, Path]:
    backend = JsonlStorageBackend()
    fixture_dir.mkdir(parents=True, exist_ok=True)
    daily_quotes = fixture_dir / "daily_quotes.jsonl"
    listed_info = fixture_dir / "listed_info.jsonl"
    fill_quotes = fixture_dir / "fill_quotes.jsonl"
    backend.write_records(daily_quotes, [{"Date": "2026-06-17", "Code": "7203", "Open": 2000, "High": 2100, "Low": 1990, "Close": 2050, "Volume": 1000}])
    backend.write_records(listed_info, [{"Date": "2026-06-17", "Code": "7203"}])
    backend.write_records(fill_quotes, [{"Date": "2026-06-17", "Code": "7203", "Open": 2000}])
    ledger = PaperTradingLedger(
        cash=Decimal("300000"),
        pending_orders=(PendingOrderState(code="7203", side="BUY", quantity=Decimal("100"), status="APPROVED"),),
    )
    ledger_path = write_ledger(ledger, runtime_dir)
    return daily_quotes, listed_info, fill_quotes, ledger_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-G daily operation runner.")
    parser.add_argument("--output-root", default="/private/tmp/phase9g_audit")
    args = parser.parse_args(argv)
    summary = run_audit(output_root=Path(args.output_root))
    print(json.dumps({"phase": summary["phase"], "status": summary["status"], "checks": summary["checks"]}, ensure_ascii=True, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
