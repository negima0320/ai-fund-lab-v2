from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.business_day_tracker import update_business_day_tracker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update Phase9 30 business day tracker.")
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--business-day-index", type=int, required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--decision-for", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--allow-duplicate", action="store_true")
    parser.add_argument("--day1-first-fill", action="store_true")
    args = parser.parse_args(argv)
    overrides = {}
    if args.day1_first_fill:
        overrides = {
            "paper_total_equity": "1000000",
            "cash": "283330.0",
            "market_value": "716670.0",
            "realized_pnl": "0",
            "unrealized_pnl": "0",
            "positions": 5,
            "trade_count": 5,
            "pending_order_count": 0,
        }
    result = update_business_day_tracker(
        ledger_path=args.ledger_path,
        business_day_index=args.business_day_index,
        run_date=args.run_date,
        decision_for=args.decision_for,
        status=args.status,
        allow_duplicate=args.allow_duplicate,
        overrides=overrides,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status != "TRACKER_DUPLICATE_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
