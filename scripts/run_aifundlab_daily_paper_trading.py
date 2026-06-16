from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.unified_daily_runner import run_unified_daily_paper_trading


def main(argv: list[str] | None = None) -> int:
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
    parser.add_argument("--force-unlock", action="store_true")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--operation-root", default=".runtime/daily_operation")
    parser.add_argument("--quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--feature-root", default=".runtime/phase9/features")
    parser.add_argument("--reports-root", default="reports")
    args = parser.parse_args(argv)
    run_date = args.date or resolve_jst_business_date()
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
    current = now.astimezone(ZoneInfo("Asia/Tokyo")).date() if now else datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return previous_or_same_weekday(current).isoformat()


def previous_or_same_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


if __name__ == "__main__":
    raise SystemExit(main())
