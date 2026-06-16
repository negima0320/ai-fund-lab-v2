#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.training_dataset_candidate import build_training_dataset_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase9-L1 training dataset candidates without training.")
    parser.add_argument("--normalized-daily-quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--listed-info-path", default=".runtime/data/raw/jquants/listed_issues/data.parquet")
    parser.add_argument("--trading-calendar-path", default=".runtime/data/raw/jquants/trading_calendar/data.parquet")
    parser.add_argument("--data-until", default="2026-06-15")
    parser.add_argument("--safe-train-until", default="2026-05-18")
    parser.add_argument("--train-until", default="2026-05-18")
    parser.add_argument("--label-horizon", type=int, default=20)
    parser.add_argument("--output-root", default=".runtime/phase9/training_dataset_candidates")
    args = parser.parse_args()
    result = build_training_dataset_candidates(
        normalized_daily_quotes_path=args.normalized_daily_quotes_path,
        listed_info_path=args.listed_info_path,
        trading_calendar_path=args.trading_calendar_path,
        data_until=args.data_until,
        safe_train_until=args.safe_train_until,
        train_until=args.train_until,
        label_horizon=args.label_horizon,
        output_root=args.output_root,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.status == "TRAINING_DATASETS_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
