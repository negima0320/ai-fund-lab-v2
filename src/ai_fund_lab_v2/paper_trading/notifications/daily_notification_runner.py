from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Mapping

from ai_fund_lab_v2.paper_trading.ledger import load_ledger
from ai_fund_lab_v2.paper_trading.notifications.discord_notifier import (
    DiscordNotificationResult,
    build_discord_content,
    read_blog_markdown,
    send_discord_notification,
)
from ai_fund_lab_v2.paper_trading.notifications.line_notifier import (
    LineNotificationResult,
    build_line_message,
    send_line_notification,
)


DAILY_NOTIFICATION_SENT = "SENT"
DAILY_NOTIFICATION_SKIPPED_NOT_CONFIGURED = "SKIPPED_NOT_CONFIGURED"
DAILY_NOTIFICATION_FAILED_NON_FATAL = "FAILED_NON_FATAL"

LINE_TOKEN_ENV = "AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN"
LINE_TO_ID_ENV = "AIFUNDLAB_LINE_TO_ID"
DISCORD_WEBHOOK_ENV = "AIFUNDLAB_DISCORD_WEBHOOK_URL"


@dataclass(frozen=True)
class DailyNotificationResult:
    line_notification: str
    discord_notification: str
    summary: dict[str, Any]
    line: dict[str, Any]
    discord: dict[str, Any]
    secrets_redacted: bool = True
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    real_trade_executed: bool = False
    virtual_fill_executed: bool = False
    model_retraining_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_daily_notifications(
    *,
    run_date: str,
    runner_status: str,
    ledger_path: str | Path,
    blog_report_markdown_path: str = "",
    blog_report_json_path: str = "",
    step_statuses: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    dry_run: bool = False,
    line_sender: Callable[..., LineNotificationResult] | None = None,
    discord_sender: Callable[..., DiscordNotificationResult] | None = None,
) -> DailyNotificationResult:
    active_env = env if env is not None else load_notification_env()
    steps = dict(step_statuses or {})
    summary = build_daily_notification_summary(
        run_date=run_date,
        runner_status=runner_status,
        ledger_path=ledger_path,
        blog_report_json_path=blog_report_json_path,
        step_statuses=steps,
    )
    line_message = build_line_message(run_date=run_date, summary=summary, blog_report_path=str(blog_report_markdown_path))
    discord_content = build_discord_content(
        run_date=run_date,
        summary=summary,
        blog_report_path=str(blog_report_markdown_path),
        blog_markdown=read_blog_markdown(blog_report_markdown_path) if blog_report_markdown_path else "",
    )
    line_result = _safe_line_send(
        line_sender=line_sender,
        message=line_message,
        token=active_env.get(LINE_TOKEN_ENV),
        to_id=active_env.get(LINE_TO_ID_ENV),
        dry_run=dry_run,
    )
    discord_result = _safe_discord_send(
        discord_sender=discord_sender,
        content=discord_content,
        webhook_url=active_env.get(DISCORD_WEBHOOK_ENV),
        dry_run=dry_run,
    )
    return DailyNotificationResult(
        line_notification=line_result.status,
        discord_notification=discord_result.status,
        summary=summary,
        line=_redacted(line_result.to_dict(), active_env),
        discord=_redacted(discord_result.to_dict(), active_env),
    )


def load_notification_env(dotenv_path: str | Path = ".env") -> dict[str, str]:
    dotenv_values = _read_dotenv(dotenv_path)
    active_env = dict(dotenv_values)
    active_env.update(os.environ)
    return active_env


def _read_dotenv(dotenv_path: str | Path) -> dict[str, str]:
    path = Path(dotenv_path)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def build_daily_notification_summary(
    *,
    run_date: str,
    runner_status: str,
    ledger_path: str | Path,
    blog_report_json_path: str = "",
    step_statuses: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ledger = load_ledger(ledger_path)
    performance = ledger.performance
    initial_cash = ledger.metadata.initial_cash if ledger.metadata.initial_cash else Decimal("1000000")
    pnl = performance.total_equity - initial_cash
    pnl_rate = Decimal("0") if initial_cash == 0 else pnl / initial_cash * Decimal("100")
    blog_payload = _read_json(blog_report_json_path)
    opportunity_count = len(blog_payload.get("opportunity_top20", [])[:5]) if isinstance(blog_payload, dict) else 0
    return {
        "run_date": run_date,
        "runner_status": runner_status,
        "status_label": _status_label(runner_status),
        "total_equity": str(performance.total_equity),
        "total_equity_display": _yen(performance.total_equity),
        "pnl": str(pnl),
        "pnl_display": _signed_yen(pnl),
        "pnl_rate": str(pnl_rate),
        "pnl_rate_display": _signed_percent(pnl_rate),
        "positions_count": len(ledger.positions),
        "pending_orders_count": len(ledger.pending_orders),
        "filled_order_count": _filled_order_count(dict(step_statuses or {})),
        "next_candidate_count": opportunity_count,
    }


def _safe_line_send(
    *,
    line_sender: Callable[..., LineNotificationResult] | None,
    message: str,
    token: str | None,
    to_id: str | None,
    dry_run: bool,
) -> LineNotificationResult:
    try:
        sender = line_sender or send_line_notification
        return sender(message=message, channel_access_token=token, to_id=to_id, dry_run=dry_run)
    except Exception as exc:
        return LineNotificationResult(status=DAILY_NOTIFICATION_FAILED_NON_FATAL, dry_run=dry_run, message_preview="", error_type=type(exc).__name__)


def _safe_discord_send(
    *,
    discord_sender: Callable[..., DiscordNotificationResult] | None,
    content: str,
    webhook_url: str | None,
    dry_run: bool,
) -> DiscordNotificationResult:
    try:
        sender = discord_sender or send_discord_notification
        return sender(content=content, webhook_url=webhook_url, dry_run=dry_run)
    except Exception as exc:
        return DiscordNotificationResult(status=DAILY_NOTIFICATION_FAILED_NON_FATAL, dry_run=dry_run, content_preview="", error_type=type(exc).__name__)


def _filled_order_count(step_statuses: dict[str, Any]) -> int:
    context = step_statuses.get("virtual_fill_context") or {}
    if not isinstance(context, dict):
        return 0
    results = context.get("results") or []
    if not isinstance(results, list):
        return 0
    return sum(int(item.get("filled_order_count") or 0) for item in results if isinstance(item, dict))


def _status_label(status: str) -> str:
    if status.endswith("COMPLETED"):
        return "COMPLETED"
    if status.endswith("BLOCKED"):
        return "BLOCKED"
    return status


def _read_json(path: str | Path) -> dict[str, Any]:
    if not path:
        return {}
    target = Path(path)
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _redacted(payload: dict[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False)
    for key in (LINE_TOKEN_ENV, LINE_TO_ID_ENV, DISCORD_WEBHOOK_ENV):
        value = env.get(key)
        if value:
            text = text.replace(value, "***REDACTED***")
    return json.loads(text)


def _yen(value: Decimal) -> str:
    return f"{int(value):,}円"


def _signed_yen(value: Decimal) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{int(value):,}円"


def _signed_percent(value: Decimal) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value.quantize(Decimal('0.01'))}%"
