from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.daily_inference_runner import run_daily_inference


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-L2 daily inference with existing model/policy artifacts.")
    parser.add_argument("--decision-for", default="2026-06-15")
    parser.add_argument("--data-until", default="2026-06-15")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--feature-root", default=".runtime/phase9/features")
    parser.add_argument("--canonical-quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--ledger-path")
    parser.add_argument("--allow-initial-ledger", action="store_true")
    parser.add_argument("--initial-cash", default="1000000")
    args = parser.parse_args(argv)

    result = run_daily_inference(
        decision_for=args.decision_for,
        data_until=args.data_until,
        runtime_dir=args.runtime_dir,
        reports_root=args.reports_root,
        feature_root=args.feature_root,
        canonical_quotes_path=args.canonical_quotes_path,
        ledger_path=Path(args.ledger_path) if args.ledger_path else None,
        allow_initial_ledger=args.allow_initial_ledger,
        initial_cash=Decimal(args.initial_cash),
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status == "INFERENCE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())

