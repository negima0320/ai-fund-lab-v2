from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.business_day_tracker import update_business_day_tracker
from ai_fund_lab_v2.paper_trading.daily_performance_report import write_daily_performance_reports
from ai_fund_lab_v2.paper_trading.ledger import load_ledger
from ai_fund_lab_v2.paper_trading.ledger_valuation import update_ledger_valuation_from_files


DAILY_CONTINUATION_COMPLETED = "DAILY_CONTINUATION_COMPLETED"
DAILY_CONTINUATION_BLOCKED = "DAILY_CONTINUATION_BLOCKED"


@dataclass(frozen=True)
class DailyContinuationResult:
    status: str
    run_date: str
    mode: str
    approval_mode: str
    ledger_path: str
    valuation_status: str
    ledger_latest_updated: bool
    position_management_input_count: int
    pending_order_count_before: int
    pending_order_count_after: int
    created_pending_order_count: int
    tracker_status: str = ""
    tracker_path: str = ""
    performance_report_json_path: str = ""
    performance_report_markdown_path: str = ""
    public_performance_summary_path: str = ""
    continuation_report_path: str = ""
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    virtual_fill_executed: bool = False
    scheduler_auto_registered: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def run_daily_continuation(
    *,
    run_date: str,
    ledger_path: Path | str,
    quotes_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
    mode: str = "paper-trading",
    approval_mode: str = "auto_for_paper_trading",
    runtime_dir: Path | str = ".runtime",
    update_tracker: bool = False,
    business_day_index: int | None = None,
    docs_report_path: Path | str = "docs/phase_reports/phase9s_daily_operation_continuation.md",
    json_report_path: Path | str = "reports/phase_reports/phase9s_daily_operation_continuation.json",
) -> DailyContinuationResult:
    if mode not in {"dry-run", "paper-trading", "report-only"}:
        raise ValueError(f"Unsupported Phase9-S continuation mode: {mode}")
    ledger_before = load_ledger(ledger_path)
    pending_before = len(ledger_before.pending_orders)
    dry_run = mode in {"dry-run", "report-only"}
    valuation = update_ledger_valuation_from_files(
        ledger_path=ledger_path,
        quotes_path=quotes_path,
        valuation_date=run_date,
        runtime_dir=runtime_dir,
        dry_run=dry_run,
    )
    ledger_after = load_ledger(Path(runtime_dir) / "phase9" / "ledger" / "latest.json") if valuation.ledger_latest_updated else load_ledger(valuation.ledger_after_path)
    warnings = list(valuation.warnings)
    warnings.append("phase9s_no_virtual_fill_until_next_business_day")
    if not _features_ready_for_date(run_date):
        warnings.append(f"feature_artifacts_missing_for_{run_date}; inference_and_new_pending_orders_skipped")
    report_paths = write_daily_performance_reports(
        run_date=run_date,
        ledger_before=ledger_before,
        ledger_after=ledger_after,
        valuation_result=valuation,
        warnings=warnings,
    )
    tracker_status = ""
    tracker_path = ""
    if update_tracker:
        tracker_index = business_day_index or _next_tracker_index(Path(runtime_dir) / "phase9" / "tracker" / "phase9_30bd_tracker.json")
        tracker = update_business_day_tracker(
            ledger=ledger_after,
            business_day_index=tracker_index,
            run_date=run_date,
            decision_for=run_date,
            status="DAILY_VALUATION_DONE",
        )
        tracker_status = tracker.status
        tracker_path = tracker.tracker_json_path
        if tracker.blocked_reasons:
            warnings.extend(tracker.blocked_reasons)
    result = DailyContinuationResult(
        status=DAILY_CONTINUATION_COMPLETED if not valuation.blocked_reasons else DAILY_CONTINUATION_BLOCKED,
        run_date=run_date,
        mode=mode,
        approval_mode=approval_mode,
        ledger_path=str(ledger_path),
        valuation_status=valuation.status,
        ledger_latest_updated=valuation.ledger_latest_updated,
        position_management_input_count=len(ledger_after.positions),
        pending_order_count_before=pending_before,
        pending_order_count_after=len(ledger_after.pending_orders),
        created_pending_order_count=0,
        tracker_status=tracker_status,
        tracker_path=tracker_path,
        performance_report_json_path=report_paths["internal_json"],
        performance_report_markdown_path=report_paths["internal_markdown"],
        public_performance_summary_path=report_paths["public_markdown"],
        warnings=tuple(warnings),
        blocked_reasons=valuation.blocked_reasons,
    )
    report_path = Path(json_report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = Path(docs_report_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_continuation_markdown(result), encoding="utf-8")
    return DailyContinuationResult(**{**result.to_dict(), "continuation_report_path": str(report_path)})


def _features_ready_for_date(run_date: str) -> bool:
    candidates = [
        Path("reports/phase9/artifacts") / run_date,
        Path(".runtime/phase9/artifacts") / run_date,
        Path(".runtime/phase9/features") / run_date,
    ]
    return any(path.exists() for path in candidates)


def _next_tracker_index(tracker_path: Path) -> int:
    if not tracker_path.is_file():
        return 1
    payload = json.loads(tracker_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else []
    if not entries:
        return 1
    return max(int(entry.get("business_day_index") or 0) for entry in entries) + 1


def _render_continuation_markdown(result: DailyContinuationResult) -> str:
    lines = [
        "# Phase9-S Daily Operation Continuation",
        "",
        f"- status: {result.status}",
        f"- run_date: {result.run_date}",
        f"- mode: {result.mode}",
        f"- valuation_status: {result.valuation_status}",
        f"- ledger_latest_updated: {result.ledger_latest_updated}",
        f"- position_management_input_count: {result.position_management_input_count}",
        f"- pending_order_count_before: {result.pending_order_count_before}",
        f"- pending_order_count_after: {result.pending_order_count_after}",
        f"- created_pending_order_count: {result.created_pending_order_count}",
        f"- tracker_status: {result.tracker_status}",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines) + "\n"
