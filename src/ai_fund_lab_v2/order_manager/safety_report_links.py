from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.broker.models import utc_now_iso


def write_order_manager_safety_links(
    *,
    plan_id: str,
    runtime_dir: Path | str = ".runtime",
    order_plan_path: Path | str,
    reconciliation_id: str,
    paper_ledger_path: Path | str,
    dry_run_report_path: Path | str,
    safety_report_path: Path | str | None = None,
) -> Path:
    directory = Path(runtime_dir) / "order_manager" / "audit"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{plan_id}_safety_links.json"
    payload = {
        "link_type": "phase8g_order_manager_safety_links",
        "generated_at": utc_now_iso(),
        "plan_id": plan_id,
        "order_plan_path": str(order_plan_path),
        "reconciliation_id": reconciliation_id,
        "paper_ledger_dry_run_path": str(paper_ledger_path),
        "order_manager_dry_run_report_path": str(dry_run_report_path),
        "safety_dry_run_report_path": str(safety_report_path or _latest_safety_report(runtime_dir) or ""),
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(path.with_suffix(".md"), payload)
    return path


def _latest_safety_report(runtime_dir: Path | str) -> str:
    directory = Path(runtime_dir) / "safety" / "reports"
    if not directory.exists():
        return ""
    candidates = sorted(directory.glob("*"), key=lambda path: (path.stat().st_mtime, path.name))
    return str(candidates[-1]) if candidates else ""


def _write_markdown(path: Path, payload: dict[str, str]) -> None:
    lines = [
        "# Phase8-G Safety Report Links",
        "",
        f"- plan_id: {payload['plan_id']}",
        f"- order_plan_path: {payload['order_plan_path']}",
        f"- reconciliation_id: {payload['reconciliation_id']}",
        f"- paper_ledger_dry_run_path: {payload['paper_ledger_dry_run_path']}",
        f"- order_manager_dry_run_report_path: {payload['order_manager_dry_run_report_path']}",
        f"- safety_dry_run_report_path: {payload['safety_dry_run_report_path']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
