from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import read_daily_quotes_normalized_small_range, write_dry_run_summary  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-G real normalized data small-range dry-run.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory.")
    parser.add_argument("--as-of-date", default=None, help="Requested as_of_date. Defaults to latest normalized date.")
    parser.add_argument("--lookback-business-days", type=int, default=60, help="Business-day lookback window.")
    parser.add_argument("--max-codes", type=int, default=10, help="Maximum codes to include.")
    parser.add_argument("--max-rows", type=int, default=1000, help="Maximum source rows to include.")
    parser.add_argument("--input-format", default="auto", choices=("auto", "jsonl", "parquet"), help="Input format.")
    parser.add_argument("--report-dir", default="reports/candidate_ai", help="Dry-run summary report directory.")
    args = parser.parse_args(argv)

    result = read_daily_quotes_normalized_small_range(
        runtime_dir=args.runtime_dir,
        as_of_date=args.as_of_date,
        lookback_business_days=args.lookback_business_days,
        max_codes=args.max_codes,
        max_rows=args.max_rows,
        input_format=args.input_format,
    )
    report_path = write_dry_run_summary(result, report_dir=args.report_dir)
    payload = result.to_dict()
    payload["report_path"] = str(report_path)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
