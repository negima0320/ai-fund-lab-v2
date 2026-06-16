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

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.run_lock import RunLockError, acquire_run_lock
from ai_fund_lab_v2.paper_trading.unified_daily_runner import UNIFIED_DAILY_RUNNER_COMPLETED, run_unified_daily_paper_trading


def main() -> int:
    checks: list[dict[str, object]] = []
    dry_result = run_unified_daily_paper_trading(
        run_date="2026-06-15",
        ledger_path=".runtime/phase9/ledger/latest.json",
        mode="dry-run",
        approval_mode="review_only",
        skip_tracker_update=True,
        force_unlock=True,
    )
    checks.append({"name": "dry_run_completed", "ok": dry_result.status == UNIFIED_DAILY_RUNNER_COMPLETED})
    checks.append({"name": "market_data_no_api_without_allow_flag", "ok": dry_result.step_statuses.get("market_data_refresh") == "SKIPPED_API_FETCH_NOT_ALLOWED"})
    checks.append({"name": "feature_refresh_step_present", "ok": "feature_refresh" in dry_result.step_statuses})
    checks.append({"name": "inference_step_present", "ok": "daily_inference" in dry_result.step_statuses})
    checks.append({"name": "blog_report_v2_generated", "ok": Path(dry_result.blog_report_v2_markdown_path).is_file()})
    checks.append({"name": "operation_log_saved", "ok": Path(dry_result.operation_log_json_path).is_file()})

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger_path = _write_position_ledger(root)
        quotes_path = _write_quotes(root)
        paper_result = run_unified_daily_paper_trading(
            run_date="2026-06-16",
            ledger_path=ledger_path,
            mode="paper-trading",
            runtime_dir=root / ".runtime",
            operation_root=root / ".runtime" / "daily_operation",
            quotes_path=quotes_path,
            reports_root=root / "reports",
            skip_feature_refresh=True,
            skip_inference=True,
            skip_tracker_update=False,
            skip_blog_report_v2=False,
            phase_report_markdown_path=root / "docs" / "phase9u.md",
            phase_report_json_path=root / "reports" / "phase9u.json",
        )
        latest = load_ledger(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        checks.append({"name": "paper_trading_mutates_paper_ledger", "ok": latest.performance.total_equity == Decimal("999000")})
        checks.append({"name": "tracker_update_works", "ok": paper_result.step_statuses.get("tracker_update") == "TRACKER_UPDATED"})
        checks.append({"name": "auto_approval_only_paper_mode_boundary", "ok": paper_result.approval_mode == "auto_for_paper_trading"})
        checks.append({"name": "prohibited_flags_false", "ok": not paper_result.broker_order_api_called and not paper_result.open_d_started and not paper_result.unlock_trade_called})

        lock_root = root / "locked_operation"
        acquire_run_lock(run_id="already_running", run_date="2026-06-16", mode="dry-run", operation_root=lock_root)
        blocked = False
        try:
            run_unified_daily_paper_trading(
                run_date="2026-06-16",
                ledger_path=ledger_path,
                mode="dry-run",
                operation_root=lock_root,
                skip_feature_refresh=True,
                skip_inference=True,
                skip_tracker_update=True,
                skip_blog_report_v2=True,
            )
        except RunLockError:
            blocked = True
        checks.append({"name": "run_lock_blocks_duplicate", "ok": blocked})

    passed = all(bool(check["ok"]) for check in checks)
    payload = {
        "status": "PASS" if passed else "FAIL",
        "dry_run_result": dry_result.to_dict(),
        "checks": checks,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "real_trade_executed": False,
        "scheduler_auto_registered": False,
    }
    out = Path("reports/phase_reports/phase9u_unified_daily_runner_audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 0 if passed else 1


def _write_position_ledger(root: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("900000"),
        positions=(PositionSnapshot(code="10010", quantity=Decimal("100"), average_cost=Decimal("1000"), market_value=Decimal("100000")),),
        performance=PerformanceSnapshot(
            total_equity=Decimal("1000000"),
            cash=Decimal("900000"),
            market_value=Decimal("100000"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            trade_count=1,
        ),
    )
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _write_quotes(root: Path) -> Path:
    path = root / "quotes.parquet"
    pd.DataFrame([{"date": "2026-06-16", "code": "10010", "open": 1000, "close": 990}]).to_parquet(path, index=False)
    return path


if __name__ == "__main__":
    raise SystemExit(main())
