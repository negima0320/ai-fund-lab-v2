from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.daily_continuation import run_daily_continuation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-S daily operation continuation.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--mode", choices=("dry-run", "paper-trading", "report-only"), default="paper-trading")
    parser.add_argument("--approval-mode", default="auto_for_paper_trading")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--update-tracker", action="store_true")
    parser.add_argument("--business-day-index", type=int, default=None)
    args = parser.parse_args(argv)
    result = run_daily_continuation(
        run_date=args.date,
        ledger_path=args.ledger_path,
        quotes_path=args.quotes_path,
        mode=args.mode,
        approval_mode=args.approval_mode,
        runtime_dir=args.runtime_dir,
        update_tracker=args.update_tracker,
        business_day_index=args.business_day_index,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status != "DAILY_CONTINUATION_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
