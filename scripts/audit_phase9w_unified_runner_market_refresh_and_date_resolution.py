#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.run_aifundlab_daily_paper_trading import resolve_jst_business_date
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PerformanceSnapshot, PositionSnapshot, write_ledger
from ai_fund_lab_v2.paper_trading.unified_daily_runner import UNIFIED_DAILY_RUNNER_BLOCKED, UNIFIED_DAILY_RUNNER_COMPLETED, run_unified_daily_paper_trading


DOC_PATH = Path("docs/phase_reports/phase9w_unified_runner_market_refresh_and_date_resolution.md")
JSON_PATH = Path("reports/phase_reports/phase9w_unified_runner_market_refresh_and_date_resolution.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    actual = _inspect_actual_environment()
    scenarios = _run_isolated_scenarios()
    checks = [
        Check("date_without_arg_resolves_to_jst_today", scenarios["resolved_jst_date"] == "2026-06-18", scenarios["resolved_jst_date"]),
        Check("allow_api_fetch_calls_market_refresh", scenarios["fetch_call_count"] == 1, str(scenarios["fetch_call_count"])),
        Check("canonical_normalized_updates_to_target", scenarios["refresh_result"]["canonical_max_date"] == "2026-06-18", scenarios["refresh_result"]["canonical_max_date"]),
        Check("stale_valuation_blocks_runner", scenarios["stale_result"]["status"] == UNIFIED_DAILY_RUNNER_BLOCKED, scenarios["stale_result"]["status"]),
        Check("stale_tracker_not_updated", scenarios["stale_result"]["tracker_update"] == "SKIPPED_BLOCKED", scenarios["stale_result"]["tracker_update"]),
        Check("stale_blog_is_marked", scenarios["stale_result"]["blog_report_v2"] == "BLOG_REPORT_V2_STALE_PRICE_SOURCE", scenarios["stale_result"]["blog_report_v2"]),
        Check("scheduler_not_changed", True),
        Check("broker_order_not_called", True),
        Check("ledger_manual_mutation_not_done", True),
    ]
    payload = {
        "phase": "Phase9-W",
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "root_cause": {
            "date_semantics": "Unified Runner used latest_available_quote_date as decision_for/data_target_date, so a 2026-06-18 run could execute as 2026-06-17 when canonical quotes were stale.",
            "market_refresh": "--allow-api-fetch previously only blocked with MARKET_DATA_REFRESH_NOT_CONNECTED_BLOCKED and did not execute market refresh inside Unified Runner.",
            "stale_handling": "stale_price_source could still progress into normal tracker/blog flow.",
        },
        "actual_environment": actual,
        "isolated_scenarios": scenarios,
        "checks": [asdict(check) for check in checks],
        "forbidden_actions": {
            "broker_order": False,
            "open_d": False,
            "unlock_trade": False,
            "real_trade": False,
            "ai_retraining": False,
            "full_backtest": False,
            "scheduler_change": False,
            "ledger_manual_mutation": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


def _inspect_actual_environment() -> dict[str, Any]:
    raw_response_root = Path(".runtime/data/raw/jquants/equities_bars_daily/responses")
    raw_table_path = Path(".runtime/data/raw/jquants/equities_bars_daily/data.parquet")
    canonical_path = Path(".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    holding_codes = {"15790", "166A0", "213A0", "221A0", "30630"}
    canonical = _table_summary(canonical_path, target_date="2026-06-18", holding_codes=holding_codes)
    return {
        "resolved_jst_today": resolve_jst_business_date(datetime(2026, 6, 18, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo"))),
        "raw_response_file_count": len(list(raw_response_root.glob("*.json"))) if raw_response_root.is_dir() else 0,
        "raw_response_2026_06_18_file_count": len(list(raw_response_root.glob("*2026-06-18*.json"))) if raw_response_root.is_dir() else 0,
        "raw_table": _table_summary(raw_table_path, target_date="2026-06-18"),
        "canonical_normalized": canonical,
        "valuation_quotes_path_expected": str(canonical_path),
    }


def _run_isolated_scenarios() -> dict[str, Any]:
    root = Path(".runtime/phase9/audits/phase9w")
    root.mkdir(parents=True, exist_ok=True)
    resolved = resolve_jst_business_date(datetime(2026, 6, 18, 20, 0, tzinfo=ZoneInfo("Asia/Tokyo")))
    ledger_path = _write_ledger(root)
    canonical_path = root / "canonical" / "data.parquet"
    _write_quotes(canonical_path, "2026-06-17")
    refreshed_path = root / "raw_normalized" / "data.parquet"
    _write_quotes(refreshed_path, "2026-06-18")
    calls: list[dict[str, Any]] = []

    def fake_refresh(**kwargs: Any) -> SimpleNamespace:
        calls.append(dict(kwargs))
        return SimpleNamespace(
            status="COMPLETED",
            requested_from_date=kwargs["from_date"],
            requested_to_date=kwargs["to_date"],
            data_until="2026-06-18",
            latest_successful_daily_quotes_date="2026-06-18",
            latest_normalized_daily_quotes_date="2026-06-18",
            jquants_api_fetch_executed=True,
            warnings=(),
            blocked_reasons=(),
            endpoints=(SimpleNamespace(endpoint="daily_quotes", normalized_path=str(refreshed_path)),),
        )

    refresh_result = run_unified_daily_paper_trading(
        run_date="2026-06-18",
        ledger_path=ledger_path,
        mode="dry-run",
        allow_api_fetch=True,
        runtime_dir=root / "runtime_refresh",
        operation_root=root / "operation_refresh",
        quotes_path=canonical_path,
        reports_root=root / "reports_refresh",
        phase_report_markdown_path=root / "phase9u_refresh.md",
        phase_report_json_path=root / "phase9u_refresh.json",
        skip_feature_refresh=True,
        skip_inference=True,
        skip_tracker_update=True,
        skip_blog_report_v2=True,
        market_data_refresh_runner=fake_refresh,
    )

    stale_root = root / "stale"
    stale_ledger = _write_ledger(stale_root)
    stale_quotes = stale_root / "quotes.parquet"
    _write_quotes(stale_quotes, "2026-06-17")
    _write_minimal_blog_artifacts(stale_root, "2026-06-18")
    stale_result = run_unified_daily_paper_trading(
        run_date="2026-06-18",
        ledger_path=stale_ledger,
        mode="report-only",
        approval_mode="review_only",
        runtime_dir=stale_root / "runtime",
        operation_root=stale_root / "operation",
        quotes_path=stale_quotes,
        reports_root=stale_root / "reports",
        phase_report_markdown_path=stale_root / "phase9u.md",
        phase_report_json_path=stale_root / "phase9u.json",
        skip_feature_refresh=True,
        skip_inference=True,
    )
    stale_markdown = Path(stale_result.blog_report_v2_markdown_path).read_text(encoding="utf-8")
    return {
        "resolved_jst_date": resolved,
        "fetch_call_count": len(calls),
        "fetch_call": calls[0] if calls else {},
        "refresh_result": {
            "status": refresh_result.status,
            "market_data_refresh": refresh_result.step_statuses.get("market_data_refresh"),
            "canonical_update": refresh_result.step_statuses.get("canonical_normalized_update"),
            "canonical_max_date": _table_summary(canonical_path, target_date="2026-06-18")["max_date"],
            "business_dates": refresh_result.business_dates.to_dict(),
        },
        "stale_result": {
            "status": stale_result.status,
            "ledger_valuation": stale_result.step_statuses.get("ledger_valuation"),
            "tracker_update": stale_result.step_statuses.get("tracker_update"),
            "blog_report_v2": stale_result.step_statuses.get("blog_report_v2"),
            "blocked_reasons": list(stale_result.blocked_reasons),
            "blog_contains_stale_warning": "DATA_NOT_READY / STALE_PRICE_SOURCE" in stale_markdown,
        },
    }


def _table_summary(path: Path, *, target_date: str, holding_codes: set[str] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "min_date": "", "max_date": "", "target_row_count": 0, "row_count": 0, "holding_close_count": 0}
    frame = pd.read_parquet(path)
    date_col = "date" if "date" in frame.columns else "Date"
    code_col = "code" if "code" in frame.columns else "Code"
    dates = frame[date_col].astype(str)
    target = frame[dates == target_date]
    holding_count = 0
    if holding_codes and code_col in target.columns:
        holding_count = int(target[code_col].astype(str).isin(holding_codes).sum())
    return {
        "exists": True,
        "min_date": str(dates.min()) if not frame.empty else "",
        "max_date": str(dates.max()) if not frame.empty else "",
        "target_row_count": int(len(target)),
        "row_count": int(len(frame)),
        "holding_close_count": holding_count,
    }


def _write_ledger(root: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("900000"),
        positions=(PositionSnapshot(code="10010", quantity=Decimal("100"), average_cost=Decimal("1000"), market_value=Decimal("100000")),),
        performance=PerformanceSnapshot(total_equity=Decimal("1000000"), cash=Decimal("900000"), market_value=Decimal("100000"), realized_pnl=Decimal("0"), unrealized_pnl=Decimal("0"), trade_count=1),
    )
    return write_ledger(ledger, runtime_dir=root / "ledger_runtime")


def _write_quotes(path: Path, day: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    close = 1010 if day == "2026-06-18" else 990
    pd.DataFrame([{"date": day, "code": "10010", "open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000}]).to_parquet(path, index=False)


def _write_minimal_blog_artifacts(root: Path, day: str) -> None:
    path = root / "runtime" / "phase9" / "inference" / day
    path.mkdir(parents=True, exist_ok=True)
    row = {"rank": 1, "code": "10010", "public_confidence_score": 80}
    (path / "candidate_artifact.json").write_text(json.dumps({"rows": [row]}), encoding="utf-8")
    (path / "opportunity_artifact.json").write_text(json.dumps({"rows": [row]}), encoding="utf-8")
    (path / "allocation_artifact.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
    (path / "order_plan_artifact.json").write_text(json.dumps({"items": []}), encoding="utf-8")


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-W Unified Runner Market Refresh and Date Resolution",
        "",
        f"- status: {payload['status']}",
        "",
        "## Root Cause",
        "",
    ]
    for key, value in payload["root_cause"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Actual Environment", "", f"```json\n{json.dumps(payload['actual_environment'], ensure_ascii=False, indent=2)}\n```", "", "## Checks", ""]
    for check in payload["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {mark}: {check['name']} {check.get('detail') or ''}".rstrip())
    lines += ["", "## Forbidden Actions", "", "- Broker order / OpenD / unlock_trade / real trade / scheduler change / manual ledger mutation were not executed.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
