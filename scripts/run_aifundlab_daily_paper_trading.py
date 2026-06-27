from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo
from uuid import uuid4

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.market_data_refresh import JQuantsAPIFetcher
from ai_fund_lab_v2.paper_trading.operation_log import build_operation_log, write_operation_log
from ai_fund_lab_v2.paper_trading.unified_daily_runner import run_unified_daily_paper_trading

NON_BUSINESS_DAY_SKIPPED = "NON_BUSINESS_DAY_SKIPPED"
TRADING_CALENDAR_NOT_READY_BLOCKED = "TRADING_CALENDAR_NOT_READY_BLOCKED"
DEFAULT_TRADING_CALENDAR_PATH = ".runtime/data/raw/jquants/trading_calendar/data.parquet"
CALENDAR_NOT_READY_REASONS = {
    "TRADING_CALENDAR_MISSING",
    "TRADING_CALENDAR_UNREADABLE",
    "TRADING_CALENDAR_DATE_MISSING",
}


def main(argv: list[str] | None = None, *, now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AI Fund Lab daily paper trading operation.")
    parser.add_argument("--date", default=None, help="Optional manual run date. If omitted, the JST business date is used.")
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--mode", choices=("dry-run", "paper-trading", "report-only", "fill-only"), default="dry-run")
    parser.add_argument("--approval-mode", choices=("auto_for_paper_trading", "review_only", "manual_required"), default="auto_for_paper_trading")
    parser.add_argument("--allow-api-fetch", action="store_true")
    parser.add_argument("--skip-market-data-refresh", action="store_true")
    parser.add_argument("--skip-feature-refresh", action="store_true")
    parser.add_argument("--skip-inference", action="store_true")
    parser.add_argument("--skip-virtual-fill", action="store_true")
    parser.add_argument("--skip-tracker-update", action="store_true")
    parser.add_argument("--skip-blog-report-v2", action="store_true")
    parser.add_argument("--skip-notifications", action="store_true")
    parser.add_argument("--force-unlock", action="store_true")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--operation-root", default=".runtime/daily_operation")
    parser.add_argument("--quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--feature-root", default=".runtime/phase9/features")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--trading-calendar-path", default=DEFAULT_TRADING_CALENDAR_PATH)
    args = parser.parse_args(argv)
    target_date = _parse_date(args.date) if args.date else _jst_date(now)
    calendar_status = jquants_business_day_status(
        target_date,
        calendar_path=args.trading_calendar_path,
        fail_closed=True,
    )
    calendar_refresh_status: dict[str, Any] = {"attempted": False, "status": "NOT_REQUIRED"}
    guarded_calendar_modes = {"dry-run", "paper-trading"}
    if args.mode in guarded_calendar_modes and calendar_status["reason"] in CALENDAR_NOT_READY_REASONS:
        calendar_refresh_status = refresh_trading_calendar_for_guard(
            run_date=target_date.isoformat(),
            allow_api_fetch=args.allow_api_fetch,
            runtime_dir=args.runtime_dir,
            calendar_path=args.trading_calendar_path,
        )
        calendar_status = jquants_business_day_status(
            target_date,
            calendar_path=args.trading_calendar_path,
            fail_closed=True,
        )
    if args.mode in guarded_calendar_modes and not calendar_status["is_business_day"]:
        if calendar_status["reason"] in CALENDAR_NOT_READY_REASONS:
            result = write_trading_calendar_not_ready_block(
                mode=args.mode,
                operation_root=Path(args.operation_root),
                runtime_dir=Path(args.runtime_dir),
                ledger_path=args.ledger_path,
                now=now,
                run_date=target_date.isoformat(),
                calendar_status=calendar_status,
                calendar_refresh_status=calendar_refresh_status,
                trading_calendar_path=args.trading_calendar_path,
            )
        else:
            result = write_non_business_day_skip(
                mode=args.mode,
                operation_root=Path(args.operation_root),
                runtime_dir=Path(args.runtime_dir),
                ledger_path=args.ledger_path,
                now=now,
                run_date=target_date.isoformat(),
                calendar_status=calendar_status,
                calendar_refresh_status=calendar_refresh_status,
                trading_calendar_path=args.trading_calendar_path,
            )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    run_date = args.date or (resolve_jst_business_date(now=now) if now is not None else resolve_jst_business_date())
    result = run_unified_daily_paper_trading(
        run_date=run_date,
        ledger_path=args.ledger_path,
        mode=args.mode,
        approval_mode=args.approval_mode,
        allow_api_fetch=args.allow_api_fetch,
        skip_market_data_refresh=args.skip_market_data_refresh,
        skip_feature_refresh=args.skip_feature_refresh,
        skip_inference=args.skip_inference,
        skip_virtual_fill=args.skip_virtual_fill,
        skip_tracker_update=args.skip_tracker_update,
        skip_blog_report_v2=args.skip_blog_report_v2,
        skip_notifications=args.skip_notifications,
        force_unlock=args.force_unlock,
        runtime_dir=args.runtime_dir,
        operation_root=args.operation_root,
        quotes_path=args.quotes_path,
        feature_root=args.feature_root,
        reports_root=args.reports_root,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status != "UNIFIED_DAILY_RUNNER_BLOCKED" else 2


def resolve_jst_business_date(now: datetime | None = None) -> str:
    current = _jst_date(now)
    return previous_or_same_weekday(current).isoformat()


def is_non_business_day_jst(now: datetime | None = None, calendar_path: Path | str = DEFAULT_TRADING_CALENDAR_PATH) -> bool:
    return not is_business_day_jst(_jst_date(now), calendar_path=calendar_path)


def is_business_day_jst(value: date, calendar_path: Path | str = DEFAULT_TRADING_CALENDAR_PATH) -> bool:
    return bool(jquants_business_day_status(value, calendar_path=calendar_path, fail_closed=False)["is_business_day"])


def jquants_business_day_status(
    value: date,
    *,
    calendar_path: Path | str = DEFAULT_TRADING_CALENDAR_PATH,
    fail_closed: bool = True,
) -> dict[str, Any]:
    path = Path(calendar_path)
    payload: dict[str, Any] = {
        "date": value.isoformat(),
        "is_business_day": False,
        "calendar_path": str(path),
        "calendar_source": "jquants_trading_calendar",
        "hol_div": None,
        "reason": "",
        "warning": "",
    }
    if not path.is_file():
        payload["reason"] = "TRADING_CALENDAR_MISSING"
        payload["warning"] = "trading_calendar_missing_fail_closed" if fail_closed else "trading_calendar_missing_weekday_fallback"
        payload["is_business_day"] = False if fail_closed else value.weekday() < 5
        payload["calendar_source"] = "fail_closed" if fail_closed else "weekday_fallback"
        return payload
    try:
        frame = pd.read_parquet(path, columns=["Date", "HolDiv"])
    except Exception as exc:
        payload["reason"] = "TRADING_CALENDAR_UNREADABLE"
        payload["warning"] = f"trading_calendar_unreadable_fail_closed:{type(exc).__name__}" if fail_closed else f"trading_calendar_unreadable_weekday_fallback:{type(exc).__name__}"
        payload["is_business_day"] = False if fail_closed else value.weekday() < 5
        payload["calendar_source"] = "fail_closed" if fail_closed else "weekday_fallback"
        return payload
    rows = frame[frame["Date"].astype(str) == value.isoformat()]
    if rows.empty:
        payload["reason"] = "TRADING_CALENDAR_DATE_MISSING"
        payload["warning"] = "trading_calendar_target_date_missing_fail_closed" if fail_closed else "trading_calendar_target_date_missing_weekday_fallback"
        payload["is_business_day"] = False if fail_closed else value.weekday() < 5
        payload["calendar_source"] = "fail_closed" if fail_closed else "weekday_fallback"
        return payload
    hol_div = str(rows.iloc[-1]["HolDiv"])
    payload["hol_div"] = hol_div
    payload["is_business_day"] = hol_div == "1"
    payload["reason"] = "JQUANTS_BUSINESS_DAY" if hol_div == "1" else "JQUANTS_NON_BUSINESS_DAY"
    return payload


def refresh_trading_calendar_for_guard(
    *,
    run_date: str,
    allow_api_fetch: bool,
    runtime_dir: str | Path,
    calendar_path: str | Path = DEFAULT_TRADING_CALENDAR_PATH,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    if not allow_api_fetch:
        return {
            "attempted": False,
            "status": "API_FETCH_NOT_ALLOWED",
            "run_date": run_date,
            "blocked_reason": "allow_api_fetch_required_for_calendar_refresh",
        }
    path = Path(calendar_path)
    try:
        active_fetcher = fetcher or JQuantsAPIFetcher(runtime_dir=runtime_dir)
        records = active_fetcher.fetch_trading_calendar(from_date=run_date, to_date=run_date)
    except Exception as exc:
        return {
            "attempted": True,
            "status": "FETCH_FAILED",
            "run_date": run_date,
            "error_type": type(exc).__name__,
        }
    if not records:
        return {
            "attempted": True,
            "status": "NO_RECORDS_RETURNED",
            "run_date": run_date,
            "fetched_row_count": 0,
        }
    try:
        new_frame = pd.DataFrame(records)
        if "Date" not in new_frame.columns or "HolDiv" not in new_frame.columns:
            return {
                "attempted": True,
                "status": "FETCHED_SCHEMA_INVALID",
                "run_date": run_date,
                "fetched_row_count": len(new_frame),
            }
        if path.is_file():
            existing = pd.read_parquet(path)
            merged = pd.concat([existing, new_frame], ignore_index=True, sort=False)
        else:
            merged = new_frame
        merged["Date"] = merged["Date"].astype(str)
        merged = merged.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
        path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(path, index=False)
    except Exception as exc:
        return {
            "attempted": True,
            "status": "WRITE_FAILED",
            "run_date": run_date,
            "error_type": type(exc).__name__,
        }
    rows = merged[merged["Date"].astype(str) == run_date]
    return {
        "attempted": True,
        "status": "COMPLETED",
        "run_date": run_date,
        "fetched_row_count": len(records),
        "calendar_path": str(path),
        "hol_div": "" if rows.empty else str(rows.iloc[-1].get("HolDiv") or ""),
    }


def _jst_date(now: datetime | None = None) -> date:
    return now.astimezone(ZoneInfo("Asia/Tokyo")).date() if now else datetime.now(ZoneInfo("Asia/Tokyo")).date()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def previous_or_same_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def write_non_business_day_skip(
    *,
    mode: str,
    operation_root: Path,
    runtime_dir: Path,
    ledger_path: str,
    now: datetime | None = None,
    run_date: str | None = None,
    calendar_status: dict[str, Any] | None = None,
    calendar_refresh_status: dict[str, Any] | None = None,
    trading_calendar_path: str | Path = DEFAULT_TRADING_CALENDAR_PATH,
) -> dict[str, object]:
    current = _jst_date(now)
    run_date = run_date or current.isoformat()
    calendar_status = calendar_status or jquants_business_day_status(date.fromisoformat(run_date), calendar_path=trading_calendar_path, fail_closed=True)
    run_id = f"aifundlab_non_business_day_{run_date}_{uuid4().hex}"
    started_at = utc_now_iso()
    step_statuses = {
        "business_date_resolve": {
            "run_date": run_date,
            "is_business_day": False,
            "paper_trading_guard": NON_BUSINESS_DAY_SKIPPED,
            "calendar_status": calendar_status,
            "calendar_refresh_status": calendar_refresh_status or {"attempted": False},
        },
        "market_data_refresh": "SKIPPED_NON_BUSINESS_DAY",
        "feature_refresh": "SKIPPED_NON_BUSINESS_DAY",
        "virtual_fill": "SKIPPED_NON_BUSINESS_DAY",
        "ledger_valuation": "SKIPPED_NON_BUSINESS_DAY",
        "daily_inference": "SKIPPED_NON_BUSINESS_DAY",
        "auto_approval": "SKIPPED_NON_BUSINESS_DAY",
        "pending_order_creation": 0,
        "tracker_update": "SKIPPED_NON_BUSINESS_DAY",
        "blog_report_v2": "SKIPPED_NON_BUSINESS_DAY",
    }
    manifest_dir = operation_root / "runs" / run_date
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "unified_daily_run_manifest.json"
    payload = {
        "run_id": run_id,
        "run_date": run_date,
        "mode": mode,
        "status": NON_BUSINESS_DAY_SKIPPED,
        "step_statuses": step_statuses,
        "ledger_path": ledger_path,
        "created_at": utc_now_iso(),
        "prohibited_flags": {
            "broker_order_api_called": False,
            "open_d_started": False,
            "unlock_trade_called": False,
            "real_trade_executed": False,
            "model_retraining_executed": False,
            "full_backtest_executed": False,
            "scheduler_auto_registered": False,
            "paper_ledger_fill_executed": False,
            "virtual_fill_executed": False,
        },
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log = build_operation_log(
        run_id=run_id,
        date=run_date,
        mode=mode,
        started_at=started_at,
        status=NON_BUSINESS_DAY_SKIPPED,
        step_statuses=step_statuses,
        ledger_refs={"ledger_path": ledger_path},
        report_refs={"manifest": str(manifest_path)},
        warnings=("non_business_day_paper_trading_skipped",),
        blocked_reasons=(),
        prohibited_flags=payload["prohibited_flags"],
    )
    log_json, log_md = write_operation_log(log, operation_root)
    return {
        "status": NON_BUSINESS_DAY_SKIPPED,
        "run_id": run_id,
        "run_date": run_date,
        "mode": mode,
        "manifest_path": str(manifest_path),
        "operation_log_json_path": str(log_json),
        "operation_log_markdown_path": str(log_md),
        "ledger_path": ledger_path,
        "runtime_dir": str(runtime_dir),
        "step_statuses": step_statuses,
        "warnings": ["non_business_day_paper_trading_skipped"],
        "calendar_status": calendar_status,
        "calendar_refresh_status": calendar_refresh_status or {"attempted": False},
    }


def write_trading_calendar_not_ready_block(
    *,
    mode: str,
    operation_root: Path,
    runtime_dir: Path,
    ledger_path: str,
    now: datetime | None = None,
    run_date: str | None = None,
    calendar_status: dict[str, Any] | None = None,
    calendar_refresh_status: dict[str, Any] | None = None,
    trading_calendar_path: str | Path = DEFAULT_TRADING_CALENDAR_PATH,
) -> dict[str, object]:
    current = _jst_date(now)
    run_date = run_date or current.isoformat()
    calendar_status = calendar_status or jquants_business_day_status(date.fromisoformat(run_date), calendar_path=trading_calendar_path, fail_closed=True)
    run_id = f"aifundlab_calendar_not_ready_{run_date}_{uuid4().hex}"
    started_at = utc_now_iso()
    step_statuses = {
        "business_date_resolve": {
            "run_date": run_date,
            "is_business_day": False,
            "paper_trading_guard": TRADING_CALENDAR_NOT_READY_BLOCKED,
            "calendar_status": calendar_status,
            "calendar_refresh_status": calendar_refresh_status or {"attempted": False},
        },
        "market_data_refresh": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "feature_refresh": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "virtual_fill": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "ledger_valuation": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "daily_inference": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "auto_approval": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "pending_order_creation": 0,
        "tracker_update": "BLOCKED_TRADING_CALENDAR_NOT_READY",
        "blog_report_v2": "BLOCKED_TRADING_CALENDAR_NOT_READY",
    }
    manifest_dir = operation_root / "runs" / run_date
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "unified_daily_run_manifest.json"
    prohibited_flags = {
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "real_trade_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
    }
    payload = {
        "run_id": run_id,
        "run_date": run_date,
        "mode": mode,
        "status": TRADING_CALENDAR_NOT_READY_BLOCKED,
        "step_statuses": step_statuses,
        "ledger_path": ledger_path,
        "created_at": utc_now_iso(),
        "prohibited_flags": prohibited_flags,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log = build_operation_log(
        run_id=run_id,
        date=run_date,
        mode=mode,
        started_at=started_at,
        status=TRADING_CALENDAR_NOT_READY_BLOCKED,
        step_statuses=step_statuses,
        ledger_refs={"ledger_path": ledger_path},
        report_refs={"manifest": str(manifest_path)},
        warnings=("trading_calendar_not_ready_blocked",),
        blocked_reasons=("trading_calendar_not_ready",),
        prohibited_flags=prohibited_flags,
    )
    log_json, log_md = write_operation_log(log, operation_root)
    return {
        "status": TRADING_CALENDAR_NOT_READY_BLOCKED,
        "run_id": run_id,
        "run_date": run_date,
        "mode": mode,
        "manifest_path": str(manifest_path),
        "operation_log_json_path": str(log_json),
        "operation_log_markdown_path": str(log_md),
        "ledger_path": ledger_path,
        "runtime_dir": str(runtime_dir),
        "step_statuses": step_statuses,
        "warnings": ["trading_calendar_not_ready_blocked"],
        "blocked_reasons": ["trading_calendar_not_ready"],
        "calendar_status": calendar_status,
        "calendar_refresh_status": calendar_refresh_status or {"attempted": False},
    }


if __name__ == "__main__":
    raise SystemExit(main())
