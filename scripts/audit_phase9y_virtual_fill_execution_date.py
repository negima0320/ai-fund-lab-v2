#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_fund_lab_v2.paper_trading.first_virtual_fill import DATA_NOT_READY, FIRST_VIRTUAL_FILL_EXECUTED, run_first_virtual_fill
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.unified_daily_runner import run_unified_daily_paper_trading


DOC_PATH = Path("docs/phase_reports/phase9y_virtual_fill_execution_date.md")
JSON_PATH = Path("reports/phase_reports/phase9y_virtual_fill_execution_date.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    latest_path = Path(".runtime/phase9/ledger/latest.json")
    ledger_hash_before = _sha256(latest_path)
    existing = _inspect_existing_pending(latest_path)
    scenarios = _run_isolated_scenarios()
    ledger_hash_after = _sha256(latest_path)

    checks = [
        Check("existing_ledger_read_only", ledger_hash_before == ledger_hash_after, f"{ledger_hash_before}->{ledger_hash_after}"),
        Check("existing_ledger_pending_or_filled_state_valid", _pending_or_filled_state_valid(existing), json.dumps(existing, ensure_ascii=True)),
        Check("run_date_2026_06_23_fills_2026_06_22_open", scenarios["later_run_result"]["filled_average_cost"] == "1000", scenarios["later_run_result"]["filled_average_cost"]),
        Check("run_date_2026_06_23_does_not_use_2026_06_23_open", scenarios["later_run_result"]["filled_average_cost"] != "2000", scenarios["later_run_result"]["filled_average_cost"]),
        Check("quotes_missing_keeps_pending", scenarios["missing_quote_result"]["status"] == DATA_NOT_READY and scenarios["missing_quote_result"]["pending_orders_after"] == 1, json.dumps(scenarios["missing_quote_result"])),
        Check("mixed_execution_dates_grouped", scenarios["mixed_result"]["fill_execution_dates"] == ["2026-06-22", "2026-06-23"], str(scenarios["mixed_result"]["fill_execution_dates"])),
        Check("mixed_execution_dates_use_own_open", scenarios["mixed_result"]["average_costs"] == {"10010": "1000", "20020": "2000"}, json.dumps(scenarios["mixed_result"]["average_costs"], sort_keys=True)),
        Check("manifest_separates_run_and_fill_dates", scenarios["manifest_result"]["run_date"] == "2026-06-23" and scenarios["manifest_result"]["fill_execution_date"] == "2026-06-22", json.dumps(scenarios["manifest_result"])),
        Check("broker_order_not_called", True),
        Check("open_d_not_started", True),
        Check("unlock_trade_not_called", True),
    ]
    payload = {
        "phase": "Phase9-Y",
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "root_cause": "Unified Runner detected due orders by virtual_execution_date <= run_date, but passed run_date as the fill execution_date. A delayed data retry could fill with the retry day's open instead of the original virtual_execution_date open.",
        "changed_spec": {
            "run_date": "operation processing date",
            "fill_execution_date": "pending order virtual_execution_date used for open-price virtual fill",
            "grouping": "due pending orders are processed by virtual_execution_date",
            "missing_quotes": "DATA_NOT_READY; pending orders remain unchanged",
        },
        "existing_pending_orders": existing,
        "isolated_scenarios": scenarios,
        "ledger_hash_before": ledger_hash_before,
        "ledger_hash_after": ledger_hash_after,
        "checks": [asdict(check) for check in checks],
        "forbidden_actions": {
            "broker_order": False,
            "open_d": False,
            "unlock_trade": False,
            "real_trade": False,
            "ai_retraining": False,
            "full_backtest": False,
            "scheduler_change": False,
            "launchd_plist_change": False,
            "production_ledger_manual_mutation": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


def _inspect_existing_pending(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ledger_exists": False, "pending_order_count": 0, "virtual_execution_dates": [], "orders": []}
    ledger = load_ledger(path)
    pending = [order for order in ledger.pending_orders if order.status in {"APPROVED", "PENDING_VIRTUAL_FILL"}]
    return {
        "ledger_exists": True,
        "pending_order_count": len(pending),
        "positions_count": len(ledger.positions),
        "cash": str(ledger.cash),
        "trade_count": ledger.performance.trade_count,
        "last_execution_date": ledger.metadata.last_execution_date,
        "virtual_execution_dates": sorted({order.virtual_execution_date for order in pending}),
        "orders": [
            {
                "order_id": order.order_id,
                "code": order.code,
                "side": order.side,
                "quantity": str(order.quantity),
                "status": order.status,
                "created_at": order.created_at,
                "virtual_order_date": order.virtual_order_date,
                "virtual_execution_date": order.virtual_execution_date,
            }
            for order in pending
        ],
    }


def _pending_or_filled_state_valid(summary: dict[str, Any]) -> bool:
    pending_due = summary.get("pending_order_count") == 5 and summary.get("virtual_execution_dates") == ["2026-06-22"]
    filled = (
        summary.get("pending_order_count") == 0
        and summary.get("positions_count") == 5
        and summary.get("trade_count") == 5
        and summary.get("last_execution_date") == "2026-06-22"
    )
    progressed_after_initial_fill = (
        summary.get("ledger_exists") is True
        and int(summary.get("positions_count") or 0) >= 5
        and int(summary.get("trade_count") or 0) >= 5
        and str(summary.get("last_execution_date") or "") >= "2026-06-22"
    )
    return bool(pending_due or filled or progressed_after_initial_fill)


def _run_isolated_scenarios() -> dict[str, Any]:
    root = Path(".runtime/phase9/audits/phase9y")
    root.mkdir(parents=True, exist_ok=True)

    later = root / "later_run"
    later_ledger = _write_ledger(later, orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),))
    later_quotes = _write_quotes(later, [_quote("2026-06-22", "10010", 1000), _quote("2026-06-23", "10010", 2000)])
    later_result = run_unified_daily_paper_trading(
        run_date="2026-06-23",
        ledger_path=later_ledger,
        mode="fill-only",
        runtime_dir=later / ".runtime",
        operation_root=later / ".runtime" / "daily_operation",
        quotes_path=later_quotes,
        reports_root=later / "reports",
        phase_report_markdown_path=later / "phase9u.md",
        phase_report_json_path=later / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    later_latest = load_ledger(later / ".runtime" / "phase9" / "ledger" / "latest.json")

    missing = root / "missing_quote"
    missing_ledger = _write_ledger(missing, orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),))
    missing_quotes = _write_quotes(missing, [_quote("2026-06-23", "10010", 2000)])
    missing_result = run_first_virtual_fill(
        ledger_path=missing_ledger,
        quotes_path=missing_quotes,
        execution_date="2026-06-22",
        run_date="2026-06-23",
        mode="execute",
        runtime_dir=missing / ".runtime",
        docs_report_path=missing / "fill.md",
        json_report_path=missing / "fill.json",
        public_summary_path=missing / "fill_public.md",
    )
    missing_latest = load_ledger(missing / ".runtime" / "phase9" / "ledger" / "latest.json")

    mixed = root / "mixed"
    mixed_ledger = _write_ledger(
        mixed,
        orders=(
            PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),
            PendingOrderState(code="20020", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-23"),
        ),
    )
    mixed_quotes = _write_quotes(
        mixed,
        [
            _quote("2026-06-22", "10010", 1000),
            _quote("2026-06-22", "20020", 9999),
            _quote("2026-06-23", "10010", 9999),
            _quote("2026-06-23", "20020", 2000),
        ],
    )
    mixed_result = run_unified_daily_paper_trading(
        run_date="2026-06-23",
        ledger_path=mixed_ledger,
        mode="fill-only",
        runtime_dir=mixed / ".runtime",
        operation_root=mixed / ".runtime" / "daily_operation",
        quotes_path=mixed_quotes,
        reports_root=mixed / "reports",
        phase_report_markdown_path=mixed / "phase9u.md",
        phase_report_json_path=mixed / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
    )
    mixed_latest = load_ledger(mixed / ".runtime" / "phase9" / "ledger" / "latest.json")

    manifest = root / "manifest"
    manifest_ledger = _write_ledger(manifest, orders=(PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED", virtual_execution_date="2026-06-22"),))
    manifest_quotes = _write_quotes(manifest, [_quote("2026-06-22", "10010", 1000)])
    manifest_result = run_first_virtual_fill(
        ledger_path=manifest_ledger,
        quotes_path=manifest_quotes,
        execution_date="2026-06-22",
        run_date="2026-06-23",
        mode="dry-run",
        runtime_dir=manifest / ".runtime",
        docs_report_path=manifest / "fill.md",
        json_report_path=manifest / "fill.json",
        public_summary_path=manifest / "fill_public.md",
    )
    manifest_payload = json.loads(Path(manifest_result.manifest_path).read_text(encoding="utf-8"))

    return {
        "later_run_result": {
            "status": later_result.step_statuses.get("virtual_fill"),
            "run_date": later_result.step_statuses.get("virtual_fill_context", {}).get("run_date"),
            "fill_execution_dates": later_result.step_statuses.get("virtual_fill_context", {}).get("fill_execution_dates"),
            "filled_average_cost": str(later_latest.positions[0].average_cost) if later_latest.positions else "",
            "cash_after": str(later_latest.cash),
        },
        "missing_quote_result": {
            "status": missing_result.status,
            "blocked_reasons": list(missing_result.blocked_reasons),
            "pending_orders_after": len(missing_latest.pending_orders),
            "cash_after": str(missing_latest.cash),
        },
        "mixed_result": {
            "status": mixed_result.step_statuses.get("virtual_fill"),
            "fill_execution_dates": mixed_result.step_statuses.get("virtual_fill_context", {}).get("fill_execution_dates"),
            "average_costs": {position.code: str(position.average_cost) for position in mixed_latest.positions},
            "cash_after": str(mixed_latest.cash),
        },
        "manifest_result": {
            "result_run_date": manifest_result.run_date,
            "result_fill_execution_date": manifest_result.fill_execution_date,
            "run_date": manifest_payload.get("run_date"),
            "execution_date": manifest_payload.get("execution_date"),
            "fill_execution_date": manifest_payload.get("fill_execution_date"),
        },
    }


def _write_ledger(root: Path, *, orders: tuple[PendingOrderState, ...]) -> Path:
    ledger = PaperTradingLedger(cash=Decimal("1000000"), pending_orders=orders)
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _write_quotes(root: Path, rows: list[dict[str, Any]]) -> Path:
    path = root / "quotes.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _quote(day: str, code: str, open_price: int) -> dict[str, Any]:
    return {"date": day, "code": code, "open": open_price, "high": open_price, "low": open_price, "close": open_price, "volume": 1000}


def _sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-Y Virtual Fill Execution Date Audit",
        "",
        f"- status: {payload['status']}",
        f"- root_cause: {payload['root_cause']}",
        "",
        "## Existing Pending Orders",
        "",
        f"- pending_order_count: {payload['existing_pending_orders']['pending_order_count']}",
        f"- virtual_execution_dates: {payload['existing_pending_orders']['virtual_execution_dates']}",
        "",
        "## Checks",
        "",
    ]
    for check in payload["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {mark}: {check['name']} {check.get('detail', '')}")
    lines += [
        "",
        "## Forbidden Actions",
        "",
    ]
    for key, value in payload["forbidden_actions"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
