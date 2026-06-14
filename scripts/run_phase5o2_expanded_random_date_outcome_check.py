#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.opportunity_ai.expanded_random_outcome_check import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    run_expanded_random_date_outcome_check,
)


def parse_years(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase5-O2 expanded random date outcome check.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", default="2021,2022,2023,2024,2025")
    parser.add_argument("--samples-per-year", type=int, default=10)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args(argv)

    result = run_expanded_random_date_outcome_check(
        output_dir=args.output_dir,
        seed=args.seed,
        years=parse_years(args.years),
        samples_per_year=args.samples_per_year,
        top_n=args.top_n,
    )
    print(f"status={result.summary['status']}")
    print(f"sampled_target_date_count={result.summary.get('sampled_target_date_count')}")
    print(f"leakage_status={result.summary.get('leakage_status')}")
    print(f"win_counts_20bd={result.summary.get('win_counts_20bd')}")
    print(f"promotion_ready={result.summary.get('promotion_ready')}")
    return 0 if result.summary.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
