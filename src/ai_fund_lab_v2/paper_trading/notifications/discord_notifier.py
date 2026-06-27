from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib import request


DISCORD_STATUS_SENT = "SENT"
DISCORD_STATUS_SKIPPED_NOT_CONFIGURED = "SKIPPED_NOT_CONFIGURED"
DISCORD_STATUS_FAILED_NON_FATAL = "FAILED_NON_FATAL"
DISCORD_LIMIT = 2000


@dataclass(frozen=True)
class DiscordNotificationResult:
    status: str
    dry_run: bool = False
    http_status: int | None = None
    content_preview: str = ""
    error_type: str = ""
    provider: str = "discord"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_discord_content(*, run_date: str, summary: dict[str, Any], blog_report_path: str, blog_markdown: str = "") -> str:
    header = "\n".join(
        [
            f"AI Fund Lab 日次レポート {run_date}",
            f"status: {summary.get('status_label', '')}",
            f"資産: {summary.get('total_equity_display', '')}",
            f"損益: {summary.get('pnl_display', '')} / {summary.get('pnl_rate_display', '')}",
            f"Report: {blog_report_path}",
        ]
    )
    if not blog_markdown:
        return header
    excerpt = blog_markdown.strip()
    content = f"{header}\n\n{excerpt}"
    if len(content) <= DISCORD_LIMIT:
        return content
    return f"{header}\n\n{excerpt[: max(0, DISCORD_LIMIT - len(header) - 10)]}..."


def send_discord_notification(
    *,
    content: str,
    webhook_url: str | None,
    dry_run: bool = False,
    transport: Callable[[str, dict[str, str], dict[str, Any]], int] | None = None,
) -> DiscordNotificationResult:
    if not webhook_url:
        return DiscordNotificationResult(status=DISCORD_STATUS_SKIPPED_NOT_CONFIGURED, dry_run=dry_run, content_preview=_preview(content))
    payload = {"content": content[:DISCORD_LIMIT]}
    if dry_run:
        return DiscordNotificationResult(status=DISCORD_STATUS_SENT, dry_run=True, content_preview=_preview(content))
    try:
        post = transport or _post_json
        http_status = post(webhook_url, {"Content-Type": "application/json", "User-Agent": "AI-Fund-Lab/phase9-notifier"}, payload)
    except Exception as exc:
        return DiscordNotificationResult(status=DISCORD_STATUS_FAILED_NON_FATAL, dry_run=False, content_preview=_preview(content), error_type=type(exc).__name__)
    return DiscordNotificationResult(status=DISCORD_STATUS_SENT, dry_run=False, http_status=http_status, content_preview=_preview(content))


def read_blog_markdown(path: str | Path, *, max_chars: int = 1500) -> str:
    target = Path(path)
    if not target.is_file():
        return ""
    return target.read_text(encoding="utf-8")[:max_chars]


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> int:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=10) as response:  # nosec B310 - user-provided Discord webhook URL.
        return int(response.status)


def _preview(content: str, limit: int = 160) -> str:
    text = content.replace("\r", "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."
