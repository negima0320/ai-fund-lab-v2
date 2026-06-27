#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger
from ai_fund_lab_v2.paper_trading.notifications.daily_notification_runner import (
    DISCORD_WEBHOOK_ENV,
    LINE_TO_ID_ENV,
    LINE_TOKEN_ENV,
    run_daily_notifications,
)


DOC_PATH = Path("docs/phase_reports/phase9aa_daily_notifications.md")
JSON_PATH = Path("reports/phase_reports/phase9aa_daily_notifications.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    fixture = _prepare_fixture(Path(".runtime/phase9/audits/phase9aa"))
    secrets = {
        LINE_TOKEN_ENV: "phase9aa-line-secret-token",
        LINE_TO_ID_ENV: "phase9aa-line-to-id",
        DISCORD_WEBHOOK_ENV: "https://discord.example/phase9aa-webhook-secret",
    }
    dry_run = run_daily_notifications(
        run_date="2026-06-22",
        runner_status="UNIFIED_DAILY_RUNNER_COMPLETED",
        ledger_path=fixture["ledger_path"],
        blog_report_markdown_path=fixture["blog_markdown_path"],
        blog_report_json_path=fixture["blog_json_path"],
        step_statuses={"virtual_fill_context": {"results": [{"filled_order_count": 5}]}},
        env=secrets,
        dry_run=True,
    )

    def fail_line(**_: Any):
        raise RuntimeError("line failed")

    def fail_discord(**_: Any):
        raise RuntimeError("discord failed")

    failure = run_daily_notifications(
        run_date="2026-06-22",
        runner_status="UNIFIED_DAILY_RUNNER_COMPLETED",
        ledger_path=fixture["ledger_path"],
        blog_report_markdown_path=fixture["blog_markdown_path"],
        blog_report_json_path=fixture["blog_json_path"],
        step_statuses={},
        env=secrets,
        line_sender=fail_line,
        discord_sender=fail_discord,
    )
    dry_run_payload = dry_run.to_dict()
    failure_payload = failure.to_dict()
    serialized = json.dumps({"dry_run": dry_run_payload, "failure": failure_payload}, ensure_ascii=False)
    command_results = {
        "pytest_paper_trading": _run_command(["python3", "-m", "pytest", "-q", "tests/paper_trading"]),
        "phase9v": _run_command(["python3", "scripts/audit_phase9v_score_saturation_fix.py"]),
        "phase9w": _run_command(["python3", "scripts/audit_phase9w_unified_runner_market_refresh_and_date_resolution.py"]),
        "phase9y": _run_command(["python3", "scripts/audit_phase9y_virtual_fill_execution_date.py"]),
        "phase9z": _run_command(["python3", "scripts/audit_phase9z_weekend_run_guard_pending_dedup.py"]),
        "phase9z3": _run_command(["python3", "scripts/audit_phase9z3_trading_calendar_refresh_before_business_day_guard.py"]),
        "phase9z4": _run_command(["python3", "scripts/audit_phase9z4_manifest_status_ledger_summary.py"]),
    }
    checks = [
        Check("line_dry_run_sent", dry_run.line_notification == "SENT", dry_run.line_notification),
        Check("discord_dry_run_sent", dry_run.discord_notification == "SENT", dry_run.discord_notification),
        Check("non_fatal_failure_line", failure.line_notification == "FAILED_NON_FATAL", failure.line_notification),
        Check("non_fatal_failure_discord", failure.discord_notification == "FAILED_NON_FATAL", failure.discord_notification),
        Check("secrets_redacted", all(value not in serialized for value in secrets.values()), ""),
        Check("summary_contains_counts", dry_run.summary.get("filled_order_count") == 5 and dry_run.summary.get("next_candidate_count") == 5, json.dumps(dry_run.summary, ensure_ascii=True)),
        *[
            Check(name, result["returncode"] == 0, result["summary"])
            for name, result in command_results.items()
        ],
    ]
    payload = {
        "phase": "Phase9-AA",
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "line_env": [LINE_TOKEN_ENV, LINE_TO_ID_ENV],
        "discord_env": [DISCORD_WEBHOOK_ENV],
        "dry_run_result": dry_run_payload,
        "failure_result": failure_payload,
        "checks": [asdict(check) for check in checks],
        "command_results": command_results,
        "forbidden_actions": {
            "broker_order": False,
            "open_d": False,
            "unlock_trade": False,
            "real_trade": False,
            "ai_retraining": False,
            "full_backtest": False,
            "scheduler_change": False,
            "launchd_plist_change": False,
            "ledger_change": False,
            "secret_committed": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


def _prepare_fixture(root: Path) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    ledger = PaperTradingLedger(
        cash=Decimal("182700"),
        positions=(PositionSnapshot(code="53670", quantity=Decimal("100"), average_cost=Decimal("1609"), market_value=Decimal("174400"), unrealized_pnl=Decimal("13500")),),
        performance=PerformanceSnapshot(
            total_equity=Decimal("1010400"),
            cash=Decimal("182700"),
            market_value=Decimal("827700"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("10400"),
            trade_count=5,
        ),
    )
    ledger_path = write_ledger(ledger, runtime_dir=root / ".runtime")
    blog_markdown = root / "2026-06-22_blog_report_v4.md"
    blog_json = root / "2026-06-22_blog_report_v4.json"
    blog_markdown.write_text("## 資産状況\n- 現在資産: 1,010,400円\n", encoding="utf-8")
    blog_json.write_text(json.dumps({"opportunity_top20": [{"code": f"{1000 + i}"} for i in range(5)]}), encoding="utf-8")
    return {"ledger_path": str(ledger_path), "blog_markdown_path": str(blog_markdown), "blog_json_path": str(blog_json)}


def _run_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    return {"command": command, "returncode": result.returncode, "summary": lines[-1] if lines else ""}


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-AA Daily Notification Integration",
        "",
        f"- status: {payload['status']}",
        f"- LINE env: {', '.join(payload['line_env'])}",
        f"- Discord env: {', '.join(payload['discord_env'])}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {check['name']}: {'PASS' if check['passed'] else 'FAIL'} {check['detail']}" for check in payload["checks"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
