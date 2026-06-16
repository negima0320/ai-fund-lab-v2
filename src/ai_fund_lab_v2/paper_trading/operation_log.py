from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso


@dataclass(frozen=True)
class OperationLog:
    run_id: str
    date: str
    mode: str
    started_at: str
    finished_at: str
    status: str
    step_statuses: dict[str, Any] = field(default_factory=dict)
    artifact_refs: dict[str, str] = field(default_factory=dict)
    ledger_refs: dict[str, str] = field(default_factory=dict)
    report_refs: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    prohibited_flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def operation_log_dir(operation_root: Path | str = ".runtime/phase9") -> Path:
    return Path(operation_root) / "operation_logs"


def write_operation_log(log: OperationLog, operation_root: Path | str = ".runtime/phase9") -> tuple[Path, Path]:
    directory = operation_log_dir(operation_root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{log.date}_operation_log.json"
    md_path = directory / f"{log.date}_operation_log.md"
    json_path.write_text(json.dumps(log.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_operation_log_markdown(log), encoding="utf-8")
    return json_path, md_path


def render_operation_log_markdown(log: OperationLog) -> str:
    lines = [
        "# Phase9 Daily Operation Log",
        "",
        f"- run_id: {log.run_id}",
        f"- date: {log.date}",
        f"- mode: {log.mode}",
        f"- started_at: {log.started_at}",
        f"- finished_at: {log.finished_at}",
        f"- status: {log.status}",
        "",
        "## Step Statuses",
        "",
    ]
    if log.step_statuses:
        for key, value in log.step_statuses.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    lines.extend(["", "## Reports", ""])
    for key, value in log.report_refs.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Ledger", ""])
    for key, value in log.ledger_refs.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Prohibited Flags", ""])
    for key, value in log.prohibited_flags.items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines) + "\n"


def build_operation_log(
    *,
    run_id: str,
    date: str,
    mode: str,
    started_at: str,
    status: str,
    step_statuses: dict[str, Any] | None = None,
    artifact_refs: dict[str, str] | None = None,
    ledger_refs: dict[str, str] | None = None,
    report_refs: dict[str, str] | None = None,
    warnings: tuple[str, ...] = (),
    blocked_reasons: tuple[str, ...] = (),
    prohibited_flags: dict[str, bool] | None = None,
) -> OperationLog:
    return OperationLog(
        run_id=run_id,
        date=date,
        mode=mode,
        started_at=started_at,
        finished_at=utc_now_iso(),
        status=status,
        step_statuses=step_statuses or {},
        artifact_refs=artifact_refs or {},
        ledger_refs=ledger_refs or {},
        report_refs=report_refs or {},
        warnings=warnings,
        blocked_reasons=blocked_reasons,
        prohibited_flags=prohibited_flags
        or {
            "broker_order_api_called": False,
            "open_d_started": False,
            "unlock_trade_called": False,
            "live_order_allowed": False,
            "scheduler_auto_registered": False,
        },
    )

