from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, load_ledger
from ai_fund_lab_v2.paper_trading.phase9_kpi import calculate_phase9_kpis


TRACKER_UPDATED = "TRACKER_UPDATED"
TRACKER_DUPLICATE_BLOCKED = "TRACKER_DUPLICATE_BLOCKED"


@dataclass(frozen=True)
class TrackerUpdateResult:
    status: str
    tracker_json_path: str
    tracker_markdown_path: str
    report_json_path: str
    report_markdown_path: str
    business_day_index: int
    run_date: str
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    scheduler_auto_registered: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def update_business_day_tracker(
    *,
    ledger: PaperTradingLedger | None = None,
    ledger_path: Path | str | None = None,
    business_day_index: int,
    run_date: str,
    decision_for: str,
    status: str,
    tracker_root: Path | str = ".runtime/phase9/tracker",
    report_root: Path | str = "reports/phase9/tracker",
    allow_duplicate: bool = False,
    overrides: dict[str, Any] | None = None,
) -> TrackerUpdateResult:
    if ledger is None:
        if ledger_path is None:
            raise ValueError("ledger or ledger_path is required")
        ledger = load_ledger(ledger_path)
    tracker_json = Path(tracker_root) / "phase9_30bd_tracker.json"
    tracker_md = Path(tracker_root) / "phase9_30bd_tracker.md"
    report_json = Path(report_root) / "phase9_30bd_tracker_report.json"
    report_md = Path(report_root) / "phase9_30bd_tracker_report.md"
    tracker = _load_tracker(tracker_json)
    entries = list(tracker.get("entries", []))
    duplicate = any(int(entry.get("business_day_index") or 0) == business_day_index or entry.get("run_date") == run_date for entry in entries)
    if duplicate and not allow_duplicate:
        result = TrackerUpdateResult(
            status=TRACKER_DUPLICATE_BLOCKED,
            tracker_json_path=str(tracker_json),
            tracker_markdown_path=str(tracker_md),
            report_json_path=str(report_json),
            report_markdown_path=str(report_md),
            business_day_index=business_day_index,
            run_date=run_date,
            blocked_reasons=("tracker_day_already_registered",),
        )
        _write_tracker_outputs(tracker=tracker, tracker_json=tracker_json, tracker_md=tracker_md, report_json=report_json, report_md=report_md)
        return result
    entry = _entry_from_ledger(
        ledger,
        business_day_index=business_day_index,
        run_date=run_date,
        decision_for=decision_for,
        status=status,
        overrides=overrides or {},
    )
    entries.append(entry)
    tracker = {
        "schema_version": "phase9.30bd_tracker.v1",
        "created_at": tracker.get("created_at") or utc_now_iso(),
        "updated_at": utc_now_iso(),
        "target_business_days": 30,
        "entries": sorted(entries, key=lambda item: int(item.get("business_day_index") or 0)),
    }
    tracker["kpis"] = calculate_phase9_kpis(tracker["entries"])
    _write_tracker_outputs(tracker=tracker, tracker_json=tracker_json, tracker_md=tracker_md, report_json=report_json, report_md=report_md)
    return TrackerUpdateResult(
        status=TRACKER_UPDATED,
        tracker_json_path=str(tracker_json),
        tracker_markdown_path=str(tracker_md),
        report_json_path=str(report_json),
        report_markdown_path=str(report_md),
        business_day_index=business_day_index,
        run_date=run_date,
    )


def _entry_from_ledger(
    ledger: PaperTradingLedger,
    *,
    business_day_index: int,
    run_date: str,
    decision_for: str,
    status: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    performance = ledger.performance
    entry = {
        "business_day_index": business_day_index,
        "run_date": run_date,
        "decision_for": decision_for,
        "status": status,
        "paper_total_equity": str(performance.total_equity),
        "cash": str(ledger.cash),
        "market_value": str(performance.market_value),
        "realized_pnl": str(performance.realized_pnl),
        "unrealized_pnl": str(performance.unrealized_pnl),
        "positions": len(ledger.positions),
        "trade_count": performance.trade_count,
        "pending_order_count": len(ledger.pending_orders),
        "data_ready": True,
        "report_generated": True,
        "ledger_integrity": "OK",
        "broker_order_api_called": False,
        "created_at": utc_now_iso(),
    }
    entry.update(overrides)
    return entry


def _load_tracker(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"entries": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"entries": []}
    payload.setdefault("entries", [])
    return payload


def _write_tracker_outputs(*, tracker: dict[str, Any], tracker_json: Path, tracker_md: Path, report_json: Path, report_md: Path) -> None:
    for path in (tracker_json, tracker_md, report_json, report_md):
        path.parent.mkdir(parents=True, exist_ok=True)
    tracker_json.write_text(json.dumps(tracker, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tracker_md.write_text(_render_tracker_markdown(tracker), encoding="utf-8")
    report_json.write_text(json.dumps(tracker, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md.write_text(_render_tracker_markdown(tracker), encoding="utf-8")


def _render_tracker_markdown(tracker: dict[str, Any]) -> str:
    kpis = tracker.get("kpis") or calculate_phase9_kpis(list(tracker.get("entries", [])))
    lines = [
        "# Phase9 30 Business Day Tracker",
        "",
        f"- progress: {kpis.get('progress')}",
        f"- paper_total_equity: {kpis.get('paper_total_equity')}",
        f"- cumulative_return: {kpis.get('cumulative_return')}",
        f"- trade_count: {kpis.get('trade_count')}",
        f"- pending_order_count: {kpis.get('pending_order_count')}",
        f"- position_count: {kpis.get('position_count')}",
        f"- no_broker_order_violation: {kpis.get('no_broker_order_violation')}",
        "",
        "## Entries",
        "",
    ]
    for entry in tracker.get("entries", []):
        lines.append(
            "- "
            f"day={entry.get('business_day_index')}"
            f" run_date={entry.get('run_date')}"
            f" status={entry.get('status')}"
            f" equity={entry.get('paper_total_equity')}"
            f" cash={entry.get('cash')}"
            f" market_value={entry.get('market_value')}"
            f" unrealized_pnl={entry.get('unrealized_pnl')}"
        )
    return "\n".join(lines) + "\n"

