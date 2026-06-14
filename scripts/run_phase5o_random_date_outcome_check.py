from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.opportunity_ai.random_date_outcome_check import run_random_date_outcome_check


def parse_years(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase5-O random date Opportunity outcome check.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", type=parse_years, default=parse_years("2021,2022,2023,2024,2025"))
    parser.add_argument("--samples-per-year", type=int, default=1)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/opportunity_ai/phase5o"))
    parser.add_argument("--doc-path", type=Path, default=Path("docs/phase_reports/phase5o_random_date_opportunity_outcome_check.md"))
    args = parser.parse_args()

    result = run_random_date_outcome_check(
        seed=args.seed,
        years=args.years,
        samples_per_year=args.samples_per_year,
        top_n=args.top_n,
        output_dir=args.output_dir,
        doc_path=args.doc_path,
    )
    print(f"status={result.summary['status']}")
    print(f"sampled_target_dates={result.summary['sampled_target_dates']}")
    print(f"initial_conclusion={result.summary['initial_conclusion']}")


if __name__ == "__main__":
    main()
