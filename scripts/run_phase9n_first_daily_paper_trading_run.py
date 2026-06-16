from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.first_daily_run import run_first_daily_paper_trading_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-N first daily paper trading run.")
    parser.add_argument("--date", dest="decision_for", default="2026-06-15")
    parser.add_argument("--data-until", default="2026-06-15")
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--mode", choices=("review-only", "paper-trading"), default="review-only")
    parser.add_argument(
        "--approval-mode",
        choices=("manual_required", "auto_for_paper_trading", "review_only"),
        default="auto_for_paper_trading",
    )
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--feature-root", default=".runtime/phase9/features")
    parser.add_argument("--canonical-quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--human-review-path")
    args = parser.parse_args(argv)

    result = run_first_daily_paper_trading_run(
        decision_for=args.decision_for,
        data_until=args.data_until,
        ledger_path=args.ledger_path,
        mode=args.mode,
        runtime_dir=args.runtime_dir,
        reports_root=args.reports_root,
        feature_root=args.feature_root,
        canonical_quotes_path=args.canonical_quotes_path,
        human_review_path=args.human_review_path,
        approval_mode=args.approval_mode,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status in {"FIRST_RUN_READY_FOR_REVIEW", "FIRST_RUN_PENDING_ORDERS_CREATED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
