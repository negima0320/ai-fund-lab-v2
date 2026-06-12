#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import build_full_range_dry_run_summary  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan Candidate feature full-range dry-run chunks without feature generation.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("auto", "jsonl", "parquet"), default="auto")
    parser.add_argument("--max-codes-per-chunk", type=int, default=500)
    parser.add_argument("--data-source-type", choices=("mock", "real_runtime", "skipped"), default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = build_full_range_dry_run_summary(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        max_codes_per_chunk=args.max_codes_per_chunk,
        data_source_type=args.data_source_type,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] in {"OK", "SKIPPED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
