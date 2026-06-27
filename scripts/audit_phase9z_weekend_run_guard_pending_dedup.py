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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import scripts.run_aifundlab_daily_paper_trading as cli
from ai_fund_lab_v2.paper_trading.human_review_artifact import create_human_review_request
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.pending_order_creator import PENDING_ORDERS_DEDUP_SKIPPED, create_pending_orders_from_approved_review


DOC_PATH = Path("docs/phase_reports/phase9z_weekend_run_guard_pending_dedup.md")
JSON_PATH = Path("reports/phase_reports/phase9z_weekend_run_guard_pending_dedup.json")
RECOVERY_JSON = Path("reports/phase_reports/phase9z_pending_order_dedup_recovery.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    recovery = _load_json(RECOVERY_JSON)
    current = _current_ledger_summary()
    isolated = _run_isolated_checks()
    pytest_result = _run_command(["python3", "-m", "pytest", "-q", "tests/paper_trading"])
    phase9v = _run_command(["python3", "scripts/audit_phase9v_score_saturation_fix.py"])
    phase9w = _run_command(["python3", "scripts/audit_phase9w_unified_runner_market_refresh_and_date_resolution.py"])
    phase9y = _run_command(["python3", "scripts/audit_phase9y_virtual_fill_execution_date.py"])

    checks = [
        Check("recovery_before_pending_10", recovery.get("before_pending_count") == 10, str(recovery.get("before_pending_count"))),
        Check("recovery_after_pending_5", recovery.get("after_pending_count") == 5, str(recovery.get("after_pending_count"))),
        Check("recovery_removed_5", recovery.get("removed_count") == 5, str(recovery.get("removed_count"))),
        Check("backup_exists", bool(recovery.get("backup_path")) and Path(str(recovery.get("backup_path"))).is_file(), str(recovery.get("backup_path"))),
        Check("current_state_valid_after_recovery_or_fill", _current_state_valid_after_recovery_or_fill(current), json.dumps(current, ensure_ascii=True)),
        Check("non_business_day_guard_skips", isolated["weekend_guard"]["status"] == cli.NON_BUSINESS_DAY_SKIPPED, isolated["weekend_guard"]["status"]),
        Check("weekend_guard_does_not_round_to_friday", isolated["weekend_guard"]["run_date"] == "2026-06-20", isolated["weekend_guard"]["run_date"]),
        Check("holiday_guard_skips", isolated["holiday_guard"]["status"] == cli.NON_BUSINESS_DAY_SKIPPED, isolated["holiday_guard"]["status"]),
        Check("holiday_guard_uses_jquants_calendar", isolated["holiday_guard"]["calendar_status"].get("hol_div") == "0", json.dumps(isolated["holiday_guard"].get("calendar_status"))),
        Check("calendar_missing_fail_closed", isolated["calendar_missing_guard"]["calendar_status"].get("reason") == "TRADING_CALENDAR_MISSING", json.dumps(isolated["calendar_missing_guard"].get("calendar_status"))),
        Check("business_day_after_holiday_not_skipped", isolated["business_day_after_holiday"]["status"] == "FAKE_UNIFIED_RUNNER_COMPLETED", isolated["business_day_after_holiday"]["status"]),
        Check("same_decision_for_dedup", isolated["same_decision_for"]["dedup_status"] == PENDING_ORDERS_DEDUP_SKIPPED and isolated["same_decision_for"]["pending_count_after_second"] == 5, json.dumps(isolated["same_decision_for"])),
        Check("pytest_paper_trading_pass", pytest_result["returncode"] == 0, pytest_result["summary"]),
        Check("phase9v_audit_pass", phase9v["returncode"] == 0, phase9v["summary"]),
        Check("phase9w_audit_pass", phase9w["returncode"] == 0, phase9w["summary"]),
        Check("phase9y_audit_pass", phase9y["returncode"] == 0, phase9y["summary"]),
    ]
    payload = {
        "phase": "Phase9-Z",
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "root_cause": "launchd ran on Saturday, CLI rounded no-date paper-trading execution to the previous weekday, and pending order creation only deduped by order_id, so regenerated order_ids duplicated the same planned buys.",
        "recovery": recovery,
        "current_ledger": current,
        "isolated_checks": isolated,
        "command_results": {
            "pytest": pytest_result,
            "phase9v": phase9v,
            "phase9w": phase9w,
            "phase9y": phase9y,
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
            "positions_change": False,
            "cash_change": False,
            "virtual_fill_execution": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


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
            {
                "order_id": order.order_id,
                "code": order.code,
                "side": order.side,
                "quantity": str(order.quantity),
                "virtual_execution_date": order.virtual_execution_date,
                "created_at": order.created_at,
            }
            for order in ledger.pending_orders
        ],
    }


def _current_state_valid_after_recovery_or_fill(current: dict[str, Any]) -> bool:
    after_recovery_before_fill = (
        current["pending_order_count"] == 5
        and current["cash"] == "1000000"
        and current["positions_count"] == 0
        and current["trade_count"] == 0
        and current["virtual_execution_dates"] == ["2026-06-22"]
    )
    after_fill = (
        current["pending_order_count"] == 0
        and current["cash"] == "182700.0"
        and current["positions_count"] == 5
        and current["trade_count"] == 5
        and current["last_execution_date"] == "2026-06-22"
    )
    progressed_without_pending_duplication = (
        int(current.get("positions_count") or 0) >= 5
        and int(current.get("trade_count") or 0) >= 5
        and str(current.get("last_execution_date") or "") >= "2026-06-22"
        and _pending_fingerprints_unique(current.get("pending_orders") or [])
    )
    return bool(after_recovery_before_fill or after_fill or progressed_without_pending_duplication)


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


def _run_isolated_checks() -> dict[str, Any]:
    root = Path(".runtime/phase9/audits/phase9z")
    root.mkdir(parents=True, exist_ok=True)
    weekend_root = root / "weekend"
    ledger_path = _write_ledger(weekend_root, orders=())
    weekend_calendar = _write_calendar(weekend_root, [{"Date": "2026-06-20", "HolDiv": "0"}])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli.main(
            [
                "--mode",
                "paper-trading",
                "--ledger-path",
                str(ledger_path),
                "--operation-root",
                str(weekend_root / ".runtime" / "daily_operation"),
                "--runtime-dir",
                str(weekend_root / ".runtime"),
                "--trading-calendar-path",
                str(weekend_calendar),
            ],
            now=datetime(2026, 6, 20, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
    weekend_payload = json.loads(buf.getvalue())

    holiday_root = root / "holiday"
    holiday_ledger = _write_ledger(holiday_root, orders=())
    holiday_calendar = _write_calendar(holiday_root, [{"Date": "2026-09-21", "HolDiv": "0"}, {"Date": "2026-09-24", "HolDiv": "1"}])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli.main(
            [
                "--mode",
                "paper-trading",
                "--ledger-path",
                str(holiday_ledger),
                "--operation-root",
                str(holiday_root / ".runtime" / "daily_operation"),
                "--runtime-dir",
                str(holiday_root / ".runtime"),
                "--trading-calendar-path",
                str(holiday_calendar),
            ],
            now=datetime(2026, 9, 21, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
    holiday_payload = json.loads(buf.getvalue())

    missing_root = root / "calendar_missing"
    missing_ledger = _write_ledger(missing_root, orders=())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cli.main(
            [
                "--mode",
                "paper-trading",
                "--ledger-path",
                str(missing_ledger),
                "--operation-root",
                str(missing_root / ".runtime" / "daily_operation"),
                "--runtime-dir",
                str(missing_root / ".runtime"),
                "--trading-calendar-path",
                str(missing_root / "missing.parquet"),
            ],
            now=datetime(2026, 9, 24, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
    missing_payload = json.loads(buf.getvalue())

    business_root = root / "business_day_after_holiday"
    business_ledger = _write_ledger(business_root, orders=())
    original_runner = cli.run_unified_daily_paper_trading

    class _FakeResult:
        status = "FAKE_UNIFIED_RUNNER_COMPLETED"

        def to_dict(self) -> dict[str, Any]:
            return {"status": self.status, "run_date": "2026-09-24", "step_statuses": {"pending_order_creation": 0}}

    def _fake_runner(**_: Any) -> _FakeResult:
        return _FakeResult()

    try:
        cli.run_unified_daily_paper_trading = _fake_runner
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(
                [
                    "--mode",
                    "paper-trading",
                    "--ledger-path",
                    str(business_ledger),
                    "--operation-root",
                    str(business_root / ".runtime" / "daily_operation"),
                    "--runtime-dir",
                    str(business_root / ".runtime"),
                    "--trading-calendar-path",
                    str(holiday_calendar),
                ],
                now=datetime(2026, 9, 24, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            )
        business_payload = json.loads(buf.getvalue())
    finally:
        cli.run_unified_daily_paper_trading = original_runner

    dedup_root = root / "same_decision"
    dedup_ledger = _write_ledger(dedup_root, orders=())
    order_plan = _write_order_plan(dedup_root)
    review = create_human_review_request(order_plan_path=order_plan, decision_for="2026-06-19", virtual_order_date="2026-06-22", output_root=dedup_root / "review")
    approved = _with_review_status(Path(review.json_path), dedup_root / "approved.json")
    first = create_pending_orders_from_approved_review(ledger_path=dedup_ledger, order_plan_path=order_plan, human_review_path=approved, runtime_dir=dedup_root / ".runtime")
    second = create_pending_orders_from_approved_review(ledger_path=dedup_root / ".runtime" / "phase9" / "ledger" / "latest.json", order_plan_path=order_plan, human_review_path=approved, runtime_dir=dedup_root / ".runtime")
    latest = load_ledger(dedup_root / ".runtime" / "phase9" / "ledger" / "latest.json")
    return {
        "weekend_guard": weekend_payload,
        "holiday_guard": holiday_payload,
        "calendar_missing_guard": missing_payload,
        "business_day_after_holiday": business_payload,
        "same_decision_for": {
            "first_status": first.status,
            "first_pending_count": first.pending_order_count,
            "dedup_status": second.status,
            "dedup_skipped_count": second.dedup_skipped_count,
            "pending_count_after_second": len(latest.pending_orders),
        },
    }


def _write_ledger(root: Path, *, orders: tuple[PendingOrderState, ...]) -> Path:
    ledger = PaperTradingLedger(cash=Decimal("1000000"), pending_orders=orders)
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _write_order_plan(root: Path) -> Path:
    path = root / "order_plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "decision_for": "2026-06-19",
        "virtual_execution_date": "2026-06-22",
        "executable": False,
        "live_order_allowed": False,
        "requires_human_review": True,
        "items": [
            {"order_id": f"order_{code}", "code": code, "side": "BUY", "quantity": qty, "planned_amount": amount, "reason": "audit"}
            for code, qty, amount in (("53670", 100, 160900), ("69660", 100, 120000), ("63360", 100, 194800), ("72450", 100, 149100), ("32370", 2100, 197400))
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_calendar(root: Path, rows: list[dict[str, str]]) -> Path:
    path = root / "calendar.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _with_review_status(source: Path, target: Path) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["review_status"] = "approved"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def _run_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    return {
        "command": command,
        "returncode": result.returncode,
        "summary": lines[-1] if lines else "",
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-Z Weekend Run Guard + Pending Order Dedup Recovery",
        "",
        f"- status: {payload['status']}",
        f"- root_cause: {payload['root_cause']}",
        "",
        "## Recovery",
        "",
        f"- before_pending_count: {payload['recovery'].get('before_pending_count')}",
        f"- after_pending_count: {payload['recovery'].get('after_pending_count')}",
        f"- removed_count: {payload['recovery'].get('removed_count')}",
        f"- backup_path: {payload['recovery'].get('backup_path')}",
        "",
        "## Checks",
        "",
    ]
    for check in payload["checks"]:
        lines.append(f"- {'PASS' if check['passed'] else 'FAIL'}: {check['name']} {check.get('detail', '')}")
    lines += ["", "## Forbidden Actions", ""]
    for key, value in payload["forbidden_actions"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
