from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.operations.notifications import run_operation_notifications


def _report_refs() -> dict[str, object]:
    return {
        "market_status": "OPEN",
        "buy_item_count": 2,
        "sell_item_count": 1,
        "current_operation_statuses": {
            "submit": "PASS",
            "safety_monitor": "PASS",
            "reconcile": "PASS",
            "operation_audit": "PASS",
        },
        "paths": {"public_report": ".runtime/operations/reports/2026-06-30/public_report.md"},
        "broker_readonly_status": {"environment": "demo"},
        "missed_jobs": [],
    }


def test_operation_notifications_skip_when_not_configured(tmp_path: Path) -> None:
    result = run_operation_notifications(trade_date="2026-06-30", root=tmp_path, report_refs=_report_refs(), env={})

    assert result["status"] == "SKIPPED_NOT_CONFIGURED"
    assert result["line"]["config_present"] is False
    assert result["line"]["send_executed"] is False
    assert result["discord"]["config_present"] is False
    assert result["discord"]["send_executed"] is False
    artifact = json.loads(Path(result["notification_result_path"]).read_text(encoding="utf-8"))
    assert artifact["secret_saved"] is False
    assert "secret-token" not in json.dumps(artifact)


def test_operation_notifications_call_transports_without_saving_secrets(tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    def fake_post(url: str, headers: dict[str, str], payload: dict[str, object]) -> int:
        calls.append((url, json.dumps(headers, ensure_ascii=True), payload))
        return 200

    env = {
        "AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN": "secret-token",
        "AIFUNDLAB_LINE_TO_ID": "secret-user",
        "AIFUNDLAB_DISCORD_WEBHOOK_URL": "https://discord.example/secret-webhook",
    }
    result = run_operation_notifications(
        trade_date="2026-06-30",
        root=tmp_path,
        report_refs=_report_refs(),
        env=env,
        line_transport=fake_post,
        discord_transport=fake_post,
    )

    assert result["status"] == "PASS"
    assert result["line"]["send_executed"] is True
    assert result["discord"]["send_executed"] is True
    assert len(calls) == 2
    artifact_text = Path(result["notification_result_path"]).read_text(encoding="utf-8")
    assert "secret-token" not in artifact_text
    assert "secret-user" not in artifact_text
    assert "secret-webhook" not in artifact_text
    assert "raw_response" in artifact_text


def test_daily_report_cli_returns_zero_when_report_generated(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["TACHIBANA_API_ENV"] = "demo"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_daily_report.py",
            "--trade-date",
            "2026-06-30",
            "--root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0
    assert (tmp_path / "daily_report_refs" / "2026-06-30" / "daily_report_refs.json").exists()
