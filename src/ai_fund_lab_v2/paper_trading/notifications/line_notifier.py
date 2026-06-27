from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib import request


LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"
LINE_STATUS_SENT = "SENT"
LINE_STATUS_SKIPPED_NOT_CONFIGURED = "SKIPPED_NOT_CONFIGURED"
LINE_STATUS_FAILED_NON_FATAL = "FAILED_NON_FATAL"


@dataclass(frozen=True)
class LineNotificationResult:
    status: str
    dry_run: bool = False
    http_status: int | None = None
    message_preview: str = ""
    error_type: str = ""
    provider: str = "line"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_line_message(*, run_date: str, summary: dict[str, Any], blog_report_path: str) -> str:
    return "\n".join(
        [
            f"AI Fund Lab 日次結果 {run_date}",
            "",
            f"status: {summary.get('status_label', '')}",
            f"資産: {summary.get('total_equity_display', '')}",
            f"損益: {summary.get('pnl_display', '')} / {summary.get('pnl_rate_display', '')}",
            f"保有: {summary.get('positions_count', 0)}",
            f"pending: {summary.get('pending_orders_count', 0)}",
            f"本日約定: {summary.get('filled_order_count', 0)}",
            f"次回候補: {summary.get('next_candidate_count', 0)}",
            "",
            "Report:",
            blog_report_path,
        ]
    )


def send_line_notification(
    *,
    message: str,
    channel_access_token: str | None,
    to_id: str | None,
    dry_run: bool = False,
    transport: Callable[[str, dict[str, str], dict[str, Any]], int] | None = None,
) -> LineNotificationResult:
    if not channel_access_token or not to_id:
        return LineNotificationResult(status=LINE_STATUS_SKIPPED_NOT_CONFIGURED, dry_run=dry_run, message_preview=_preview(message))
    payload = {"to": to_id, "messages": [{"type": "text", "text": message}]}
    if dry_run:
        return LineNotificationResult(status=LINE_STATUS_SENT, dry_run=True, message_preview=_preview(message))
    try:
        post = transport or _post_json
        http_status = post(
            LINE_PUSH_ENDPOINT,
            {"Authorization": f"Bearer {channel_access_token}", "Content-Type": "application/json"},
            payload,
        )
    except Exception as exc:
        return LineNotificationResult(status=LINE_STATUS_FAILED_NON_FATAL, dry_run=False, message_preview=_preview(message), error_type=type(exc).__name__)
    return LineNotificationResult(status=LINE_STATUS_SENT, dry_run=False, http_status=http_status, message_preview=_preview(message))


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> int:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=10) as response:  # nosec B310 - URL is fixed LINE Messaging API endpoint.
        return int(response.status)


def _preview(message: str, limit: int = 160) -> str:
    text = message.replace("\r", "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."
