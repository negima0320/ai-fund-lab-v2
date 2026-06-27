from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger
from ai_fund_lab_v2.paper_trading.notifications.daily_notification_runner import (
    DISCORD_WEBHOOK_ENV,
    LINE_TO_ID_ENV,
    LINE_TOKEN_ENV,
    DAILY_NOTIFICATION_FAILED_NON_FATAL,
    DAILY_NOTIFICATION_SENT,
    DAILY_NOTIFICATION_SKIPPED_NOT_CONFIGURED,
    load_notification_env,
    run_daily_notifications,
)
from ai_fund_lab_v2.paper_trading.notifications.discord_notifier import build_discord_content, send_discord_notification
from ai_fund_lab_v2.paper_trading.notifications.line_notifier import build_line_message, send_line_notification
from ai_fund_lab_v2.paper_trading.unified_daily_runner import UNIFIED_DAILY_RUNNER_COMPLETED, run_unified_daily_paper_trading


def test_env_unset_skips_notifications(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)

    result = run_daily_notifications(
        run_date="2026-06-22",
        runner_status=UNIFIED_DAILY_RUNNER_COMPLETED,
        ledger_path=ledger_path,
        env={},
    )

    assert result.line_notification == DAILY_NOTIFICATION_SKIPPED_NOT_CONFIGURED
    assert result.discord_notification == DAILY_NOTIFICATION_SKIPPED_NOT_CONFIGURED


def test_notification_env_can_load_local_dotenv(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN=line-token-from-dotenv",
                "AIFUNDLAB_LINE_TO_ID=line-to-id-from-dotenv",
                "AIFUNDLAB_DISCORD_WEBHOOK_URL=https://discord.example/dotenv-webhook",
            ]
        ),
        encoding="utf-8",
    )

    env = load_notification_env()

    assert env[LINE_TOKEN_ENV] == "line-token-from-dotenv"
    assert env[LINE_TO_ID_ENV] == "line-to-id-from-dotenv"
    assert env[DISCORD_WEBHOOK_ENV] == "https://discord.example/dotenv-webhook"


def test_line_payload_generation_and_secret_redaction(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    calls: list[dict[str, object]] = []

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> int:
        calls.append({"url": url, "headers": headers, "payload": payload})
        return 200

    summary = run_daily_notifications(
        run_date="2026-06-22",
        runner_status=UNIFIED_DAILY_RUNNER_COMPLETED,
        ledger_path=ledger_path,
        blog_report_markdown_path="reports/public/phase9_daily/2026-06-22_blog_report_v4.md",
        step_statuses={"virtual_fill_context": {"results": [{"filled_order_count": 5}]}},
        env={LINE_TOKEN_ENV: "line-secret-token", LINE_TO_ID_ENV: "line-to-id"},
        line_sender=lambda **kwargs: send_line_notification(**kwargs, transport=fake_transport),
    )
    text = json.dumps(summary.to_dict(), ensure_ascii=False)

    assert summary.line_notification == DAILY_NOTIFICATION_SENT
    assert "AI Fund Lab 日次結果 2026-06-22" in calls[0]["payload"]["messages"][0]["text"]
    assert "本日約定: 5" in calls[0]["payload"]["messages"][0]["text"]
    assert "line-secret-token" not in text
    assert "line-to-id" not in text


def test_discord_payload_generation_and_secret_redaction(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> int:
        calls.append({"url": url, "headers": headers, "payload": payload})
        return 204

    content = build_discord_content(
        run_date="2026-06-22",
        summary={"status_label": "COMPLETED", "total_equity_display": "1,010,400円", "pnl_display": "+10,400円", "pnl_rate_display": "+1.04%"},
        blog_report_path="reports/public/phase9_daily/2026-06-22_blog_report_v4.md",
        blog_markdown="## 資産状況\n- 現在資産: 1,010,400円",
    )
    result = send_discord_notification(content=content, webhook_url="https://discord.example/webhook-secret", transport=fake_transport)
    text = json.dumps(result.to_dict(), ensure_ascii=False)

    assert result.status == DAILY_NOTIFICATION_SENT
    assert calls[0]["payload"]["content"].startswith("AI Fund Lab 日次レポート 2026-06-22")
    assert "reports/public/phase9_daily/2026-06-22_blog_report_v4.md" in calls[0]["payload"]["content"]
    assert "webhook-secret" not in text


def test_notification_failure_is_non_fatal_to_unified_runner(tmp_path: Path) -> None:
    ledger_path = _write_ledger(tmp_path)
    quotes_path = _write_quotes(tmp_path)

    def failing_notification_runner(**kwargs: object) -> dict[str, object]:
        raise RuntimeError("notification transport down")

    result = run_unified_daily_paper_trading(
        run_date="2026-06-22",
        ledger_path=ledger_path,
        mode="dry-run",
        runtime_dir=tmp_path / ".runtime",
        operation_root=tmp_path / ".runtime" / "daily_operation",
        quotes_path=quotes_path,
        reports_root=tmp_path / "reports",
        phase_report_markdown_path=tmp_path / "phase9u.md",
        phase_report_json_path=tmp_path / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
        notification_runner=failing_notification_runner,
    )

    assert result.status == UNIFIED_DAILY_RUNNER_COMPLETED
    assert result.step_statuses["line_notification"] == DAILY_NOTIFICATION_FAILED_NON_FATAL
    assert result.step_statuses["discord_notification"] == DAILY_NOTIFICATION_FAILED_NON_FATAL


def test_build_line_message_is_short_and_contains_report_path() -> None:
    message = build_line_message(
        run_date="2026-06-22",
        summary={
            "status_label": "COMPLETED",
            "total_equity_display": "1,010,400円",
            "pnl_display": "+10,400円",
            "pnl_rate_display": "+1.04%",
            "positions_count": 5,
            "pending_orders_count": 0,
            "filled_order_count": 5,
            "next_candidate_count": 5,
        },
        blog_report_path="reports/public/phase9_daily/2026-06-22_blog_report_v4.md",
    )

    assert "status: COMPLETED" in message
    assert "資産: 1,010,400円" in message
    assert "reports/public/phase9_daily/2026-06-22_blog_report_v4.md" in message
    assert len(message) < 500


def _write_ledger(tmp_path: Path) -> Path:
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
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")


def _write_quotes(tmp_path: Path) -> Path:
    path = tmp_path / "quotes.parquet"
    pd.DataFrame([{"date": "2026-06-22", "code": "53670", "open": 1609, "close": 1744}]).to_parquet(path, index=False)
    return path
