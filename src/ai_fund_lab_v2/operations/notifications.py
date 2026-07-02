from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib import request

from ai_fund_lab_v2.operations.io import OperationPaths, write_json


LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"
DISCORD_LIMIT = 2000

LINE_TOKEN_ENV_CANDIDATES = (
    "AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_MESSAGING_API_TOKEN",
)
LINE_TO_ENV_CANDIDATES = (
    "AIFUNDLAB_LINE_TO_ID",
    "LINE_USER_ID",
    "LINE_TO",
)
LINE_NOTIFY_TOKEN_ENV = "LINE_NOTIFY_TOKEN"
DISCORD_WEBHOOK_ENV_CANDIDATES = (
    "AIFUNDLAB_DISCORD_WEBHOOK_URL",
    "DISCORD_WEBHOOK_URL",
)


@dataclass(frozen=True)
class NotificationSendResult:
    provider: str
    config_present: bool
    send_attempted: bool
    send_executed: bool
    status: str
    dry_run: bool = False
    error_type: str = ""
    secret_saved: bool = False
    raw_request_saved: bool = False
    raw_response_saved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "config_present": self.config_present,
            "send_attempted": self.send_attempted,
            "send_executed": self.send_executed,
            "status": self.status,
            "dry_run": self.dry_run,
            "error_type": self.error_type,
            "secret_saved": self.secret_saved,
            "raw_request_saved": self.raw_request_saved,
            "raw_response_saved": self.raw_response_saved,
        }


def run_operation_notifications(
    *,
    trade_date: str,
    root: Path,
    report_refs: Mapping[str, Any],
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    line_transport: Callable[[str, dict[str, str], dict[str, Any]], int] | None = None,
    discord_transport: Callable[[str, dict[str, str], dict[str, Any]], int] | None = None,
) -> dict[str, Any]:
    active_env = env if env is not None else load_notification_env()
    message = build_operation_notification_message(trade_date=trade_date, report_refs=report_refs)
    line = send_line_operation_notification(
        message=message,
        env=active_env,
        dry_run=dry_run,
        transport=line_transport,
    )
    discord = send_discord_operation_notification(
        content=message,
        env=active_env,
        dry_run=dry_run,
        transport=discord_transport,
    )
    status = "PASS"
    if line.status == "FAILED_NON_FATAL" or discord.status == "FAILED_NON_FATAL":
        status = "FAILED_NON_FATAL"
    elif line.status == "SKIPPED_NOT_CONFIGURED" and discord.status == "SKIPPED_NOT_CONFIGURED":
        status = "SKIPPED_NOT_CONFIGURED"
    payload = {
        "artifact_type": "notification_result",
        "business_date": trade_date,
        "status": status,
        "notification_result_classification": status,
        "line": line.to_dict(),
        "discord": discord.to_dict(),
        "line_config_present": line.config_present,
        "line_send_attempted": line.send_attempted,
        "line_send_executed": line.send_executed,
        "discord_config_present": discord.config_present,
        "discord_send_attempted": discord.send_attempted,
        "discord_send_executed": discord.send_executed,
        "secret_saved": False,
        "raw_request_saved": False,
        "raw_response_saved": False,
    }
    output = OperationPaths(root).dated("notifications", trade_date, "notification_result.json")
    write_json(output, payload)
    return {**payload, "notification_result_path": str(output)}


def load_notification_env(dotenv_path: str | Path = ".env") -> dict[str, str]:
    values = _read_dotenv(dotenv_path)
    values.update(os.environ)
    return values


def build_operation_notification_message(*, trade_date: str, report_refs: Mapping[str, Any]) -> str:
    summary_text = str(report_refs.get("notification_summary_text") or "").strip()
    if summary_text:
        return summary_text
    statuses = report_refs.get("current_operation_statuses") or report_refs.get("operation_statuses") or {}
    paths = report_refs.get("paths") or {}
    demo_mode = str(report_refs.get("broker_readonly_status", {}).get("environment") or report_refs.get("environment") or "")
    lines = [
        "AI Fund Lab Daily Report",
        f"business_date: {trade_date}",
        f"Market Status: {report_refs.get('market_status', 'UNKNOWN')}",
        f"BUY count: {report_refs.get('buy_item_count', 0)}",
        f"SELL count: {report_refs.get('sell_item_count', 0)}",
        f"Submit status: {statuses.get('submit', 'UNKNOWN')}",
        f"Safety status: {statuses.get('safety_monitor', 'UNKNOWN')}",
        f"Reconcile status: {statuses.get('reconcile', 'UNKNOWN')}",
        f"Audit status: {statuses.get('operation_audit', 'UNKNOWN')}",
        f"Report path: {paths.get('public_report', '')}",
        f"Mode: {demo_mode or 'runtime_config'}",
        "Production order: disabled",
    ]
    missed = report_refs.get("missed_jobs") or []
    if missed:
        lines.append(f"Missed jobs: {len(missed)}")
    return "\n".join(lines)


def send_line_operation_notification(
    *,
    message: str,
    env: Mapping[str, str],
    dry_run: bool = False,
    transport: Callable[[str, dict[str, str], dict[str, Any]], int] | None = None,
) -> NotificationSendResult:
    token = _first_present(env, LINE_TOKEN_ENV_CANDIDATES)
    to_id = _first_present(env, LINE_TO_ENV_CANDIDATES)
    config_present = bool(token and to_id)
    if not config_present:
        return NotificationSendResult(
            provider="line",
            config_present=False,
            send_attempted=False,
            send_executed=False,
            status="SKIPPED_NOT_CONFIGURED",
            dry_run=dry_run,
        )
    if dry_run:
        return NotificationSendResult(provider="line", config_present=True, send_attempted=True, send_executed=True, status="PASS", dry_run=True)
    payload = {"to": to_id, "messages": [{"type": "text", "text": message}]}
    try:
        post = transport or _post_json
        post(LINE_PUSH_ENDPOINT, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, payload)
    except Exception as exc:
        return NotificationSendResult(
            provider="line",
            config_present=True,
            send_attempted=True,
            send_executed=False,
            status="FAILED_NON_FATAL",
            error_type=type(exc).__name__,
        )
    return NotificationSendResult(provider="line", config_present=True, send_attempted=True, send_executed=True, status="PASS")


def send_discord_operation_notification(
    *,
    content: str,
    env: Mapping[str, str],
    dry_run: bool = False,
    transport: Callable[[str, dict[str, str], dict[str, Any]], int] | None = None,
) -> NotificationSendResult:
    webhook_url = _first_present(env, DISCORD_WEBHOOK_ENV_CANDIDATES)
    config_present = bool(webhook_url)
    if not config_present:
        return NotificationSendResult(
            provider="discord",
            config_present=False,
            send_attempted=False,
            send_executed=False,
            status="SKIPPED_NOT_CONFIGURED",
            dry_run=dry_run,
        )
    if dry_run:
        return NotificationSendResult(provider="discord", config_present=True, send_attempted=True, send_executed=True, status="PASS", dry_run=True)
    try:
        post = transport or _post_json
        post(webhook_url, {"Content-Type": "application/json", "User-Agent": "AI-Fund-Lab/operations-notifier"}, {"content": content[:DISCORD_LIMIT]})
    except Exception as exc:
        return NotificationSendResult(
            provider="discord",
            config_present=True,
            send_attempted=True,
            send_executed=False,
            status="FAILED_NON_FATAL",
            error_type=type(exc).__name__,
        )
    return NotificationSendResult(provider="discord", config_present=True, send_attempted=True, send_executed=True, status="PASS")


def _first_present(env: Mapping[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(env.get(key) or "").strip()
        if value:
            return value
    return ""


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
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> int:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=10) as response:  # nosec B310 - notification URLs are fixed/configured at the final send boundary.
        return int(response.status)
