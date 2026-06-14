#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.opportunity_ai.market_sector_split_impact import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    run_market_sector_split_impact_audit,
)


def parse_years(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase5-P2 Market / Sector split impact audit.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", default="2021,2022,2023,2024,2025")
    parser.add_argument("--samples-per-year", type=int, default=1)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args(argv)

    result = run_market_sector_split_impact_audit(
        output_dir=args.output_dir,
        random_seed=args.seed,
        years=parse_years(args.years),
        samples_per_year=args.samples_per_year,
        top_n=args.top_n,
    )
    print(f"status={result.metrics['status']}")
    print(f"readiness_status={result.metrics['readiness_status']}")
    print(f"promotion_ready={result.metrics['promotion_ready']}")
    print(f"strategies={','.join(result.audit.get('strategies_evaluated', []))}")
    return 0 if result.metrics.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
