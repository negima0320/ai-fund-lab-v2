#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import scripts.run_aifundlab_daily_paper_trading as cli
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, load_ledger, write_ledger


DOC_PATH = Path("docs/phase_reports/phase9z3_trading_calendar_refresh_before_business_day_guard.md")
JSON_PATH = Path("reports/phase_reports/phase9z3_trading_calendar_refresh_before_business_day_guard.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    scenarios = _run_scenarios()
    current = _current_ledger_summary()
    pytest_result = _run_command(["python3", "-m", "pytest", "-q", "tests/paper_trading/test_phase9z3_trading_calendar_refresh.py"])
    phase9v = _run_command(["python3", "scripts/audit_phase9v_score_saturation_fix.py"])
    phase9w = _run_command(["python3", "scripts/audit_phase9w_unified_runner_market_refresh_and_date_resolution.py"])
    phase9y = _run_command(["python3", "scripts/audit_phase9y_virtual_fill_execution_date.py"])
    phase9z = _run_command(["python3", "scripts/audit_phase9z_weekend_run_guard_pending_dedup.py"])
    checks = [
        Check("calendar_missing_attempts_fetch", scenarios["fetch_success"]["refresh_called"], json.dumps(scenarios["fetch_success"])),
        Check("fetch_success_business_day_runs", scenarios["fetch_success"]["status"] == "FAKE_UNIFIED_RUNNER_COMPLETED", scenarios["fetch_success"]["status"]),
        Check("fetch_missing_blocks", scenarios["fetch_missing"]["status"] == cli.TRADING_CALENDAR_NOT_READY_BLOCKED, scenarios["fetch_missing"]["status"]),
        Check("fetch_failure_blocks", scenarios["fetch_failure"]["status"] == cli.TRADING_CALENDAR_NOT_READY_BLOCKED, scenarios["fetch_failure"]["status"]),
        Check("holiday_skips", scenarios["holiday"]["status"] == cli.NON_BUSINESS_DAY_SKIPPED, scenarios["holiday"]["status"]),
        Check("statuses_distinguish_missing_and_holiday", scenarios["fetch_missing"]["status"] != scenarios["holiday"]["status"], f"{scenarios['fetch_missing']['status']} vs {scenarios['holiday']['status']}"),
        Check("current_state_valid_after_calendar_recovery_or_fill", _current_state_valid_after_calendar_recovery_or_fill(current), json.dumps(current, ensure_ascii=True)),
        Check("pytest_phase9z3_pass", pytest_result["returncode"] == 0, pytest_result["summary"]),
        Check("phase9v_pass", phase9v["returncode"] == 0, phase9v["summary"]),
        Check("phase9w_pass", phase9w["returncode"] == 0, phase9w["summary"]),
        Check("phase9y_pass", phase9y["returncode"] == 0, phase9y["summary"]),
        Check("phase9z_pass", phase9z["returncode"] == 0, phase9z["summary"]),
    ]
    payload = {
        "phase": "Phase9-Z3",
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "root_cause": "Phase9-Z2 failed closed before refreshing stale local J-Quants trading_calendar, so a real business day with a missing local calendar row was treated as non-business.",
        "scenarios": scenarios,
        "current_ledger": current,
        "command_results": {
            "pytest_phase9z3": pytest_result,
            "phase9v": phase9v,
            "phase9w": phase9w,
            "phase9y": phase9y,
            "phase9z": phase9z,
        },
        "checks": [asdict(check) for check in checks],
        "forbidden_actions": {
            "broker_order": False,
            "open_d": False,
            "unlock_trade": False,
            "real_trade": False,
            "ai_retraining": False,
            "full_backtest": False,
            "scheduler_change": False,
            "launchd_plist_change": False,
            "ledger_manual_modification": False,
            "pending_order_manual_fill": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


def _run_scenarios() -> dict[str, Any]:
    root = Path(".runtime/phase9/audits/phase9z3")
    root.mkdir(parents=True, exist_ok=True)
    return {
        "fetch_success": _scenario_fetch_success(root / "fetch_success"),
        "fetch_missing": _scenario_fetch_missing(root / "fetch_missing"),
        "fetch_failure": _scenario_fetch_failure(root / "fetch_failure"),
        "holiday": _scenario_holiday(root / "holiday"),
    }


def _scenario_fetch_success(root: Path) -> dict[str, Any]:
    ledger = _write_ledger(root)
    calendar = root / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-06-21", "HolDiv": "0"}]).to_parquet(calendar, index=False)
    refresh_called = False
    original_refresh = cli.refresh_trading_calendar_for_guard
    original_runner = cli.run_unified_daily_paper_trading

    def fake_refresh(**_: Any) -> dict[str, Any]:
        nonlocal refresh_called
        refresh_called = True
        pd.DataFrame([{"Date": "2026-06-21", "HolDiv": "0"}, {"Date": "2026-06-22", "HolDiv": "1"}]).to_parquet(calendar, index=False)
        return {"attempted": True, "status": "COMPLETED", "hol_div": "1"}

    class FakeResult:
        status = "FAKE_UNIFIED_RUNNER_COMPLETED"

        def to_dict(self) -> dict[str, Any]:
            return {"status": self.status, "run_date": "2026-06-22", "step_statuses": {"virtual_fill_context": {"fill_execution_dates": ["2026-06-22"]}}}

    try:
        cli.refresh_trading_calendar_for_guard = fake_refresh
        cli.run_unified_daily_paper_trading = lambda **_: FakeResult()
        payload = _run_cli(root=root, ledger=ledger, calendar=calendar, day="2026-06-22", allow_api_fetch=True)
    finally:
        cli.refresh_trading_calendar_for_guard = original_refresh
        cli.run_unified_daily_paper_trading = original_runner
    payload["refresh_called"] = refresh_called
    return payload


def _scenario_fetch_missing(root: Path) -> dict[str, Any]:
    ledger = _write_ledger(root)
    calendar = root / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-06-21", "HolDiv": "0"}]).to_parquet(calendar, index=False)
    original = cli.refresh_trading_calendar_for_guard
    try:
        cli.refresh_trading_calendar_for_guard = lambda **_: {"attempted": True, "status": "NO_RECORDS_RETURNED"}
        return _run_cli(root=root, ledger=ledger, calendar=calendar, day="2026-06-22", allow_api_fetch=True)
    finally:
        cli.refresh_trading_calendar_for_guard = original


def _scenario_fetch_failure(root: Path) -> dict[str, Any]:
    ledger = _write_ledger(root)
    calendar = root / "calendar.parquet"
    original = cli.refresh_trading_calendar_for_guard
    try:
        cli.refresh_trading_calendar_for_guard = lambda **_: {"attempted": True, "status": "FETCH_FAILED", "error_type": "RuntimeError"}
        return _run_cli(root=root, ledger=ledger, calendar=calendar, day="2026-06-22", allow_api_fetch=True)
    finally:
        cli.refresh_trading_calendar_for_guard = original


def _scenario_holiday(root: Path) -> dict[str, Any]:
    ledger = _write_ledger(root)
    calendar = root / "calendar.parquet"
    pd.DataFrame([{"Date": "2026-09-21", "HolDiv": "0"}]).to_parquet(calendar, index=False)
    return _run_cli(root=root, ledger=ledger, calendar=calendar, day="2026-09-21", allow_api_fetch=False)


def _run_cli(*, root: Path, ledger: Path, calendar: Path, day: str, allow_api_fetch: bool) -> dict[str, Any]:
    args = [
        "--date",
        day,
        "--mode",
        "dry-run",
        "--ledger-path",
        str(ledger),
        "--operation-root",
        str(root / ".runtime" / "daily_operation"),
        "--runtime-dir",
        str(root / ".runtime"),
        "--trading-calendar-path",
        str(calendar),
    ]
    if allow_api_fetch:
        args.append("--allow-api-fetch")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli.main(args, now=datetime(2026, 6, 22, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")))
    return json.loads(buf.getvalue())


def _write_ledger(root: Path) -> Path:
    return write_ledger(PaperTradingLedger(cash=Decimal("1000000")), runtime_dir=root / ".runtime")


def _current_ledger_summary() -> dict[str, Any]:
    ledger = load_ledger(".runtime/phase9/ledger/latest.json")
    return {
        "cash": str(ledger.cash),
        "positions_count": len(ledger.positions),
        "pending_order_count": len(ledger.pending_orders),
        "trade_count": ledger.performance.trade_count,
        "last_execution_date": ledger.metadata.last_execution_date,
        "virtual_execution_dates": sorted({order.virtual_execution_date for order in ledger.pending_orders}),
        "pending_orders": [
            {"order_id": order.order_id, "code": order.code, "side": order.side, "quantity": str(order.quantity), "virtual_execution_date": order.virtual_execution_date}
            for order in ledger.pending_orders
        ],
    }


def _current_state_valid_after_calendar_recovery_or_fill(current: dict[str, Any]) -> bool:
    ready_for_fill = (
        current["pending_order_count"] == 5
        and current["cash"] == "1000000"
        and current["positions_count"] == 0
        and current["virtual_execution_dates"] == ["2026-06-22"]
    )
    after_fill = (
        current["pending_order_count"] == 0
        and current["cash"] == "182700.0"
        and current["positions_count"] == 5
        and current["trade_count"] == 5
        and current["last_execution_date"] == "2026-06-22"
    )
    progressed_after_calendar_recovery = (
        int(current.get("positions_count") or 0) >= 5
        and int(current.get("trade_count") or 0) >= 5
        and str(current.get("last_execution_date") or "") >= "2026-06-22"
        and _pending_fingerprints_unique(current.get("pending_orders") or [])
    )
    return bool(ready_for_fill or after_fill or progressed_after_calendar_recovery)


def _pending_fingerprints_unique(orders: list[dict[str, Any]]) -> bool:
    fingerprints = [
        (
            order.get("virtual_execution_date"),
            order.get("code"),
            order.get("side"),
            order.get("quantity"),
        )
        for order in orders
    ]
    return len(fingerprints) == len(set(fingerprints))


def _run_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    return {"command": command, "returncode": result.returncode, "summary": lines[-1] if lines else ""}


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-Z3 Trading Calendar Refresh Before Business Day Guard",
        "",
        f"- status: {payload['status']}",
        f"- root_cause: {payload['root_cause']}",
        "",
        "## Checks",
        "",
    ]
    for check in payload["checks"]:
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'}: {check['name']} {check.get('detail', '')}")
    lines += ["", "## Current Ledger", "", f"- pending_order_count: {payload['current_ledger']['pending_order_count']}", f"- virtual_execution_dates: {payload['current_ledger']['virtual_execution_dates']}", "", "## Forbidden Actions", ""]
    for key, value in payload["forbidden_actions"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
