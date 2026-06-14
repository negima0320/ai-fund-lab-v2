#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.opportunity_ai.ranking_quality_audit import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    run_opportunity_ranking_quality_audit,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase5-R Opportunity ranking quality audit.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    result = run_opportunity_ranking_quality_audit(output_dir=args.output_dir)
    print(f"status={result.metrics['status']}")
    print(f"readiness_status={result.metrics['readiness_status']}")
    print(f"promotion_ready={result.metrics['promotion_ready']}")
    print(f"strategy_count={result.metrics['strategy_count']}")
    print(f"best_ndcg20={result.metrics['best_strategy_by_test_ndcg20_risk_adjusted']}")
    return 0 if result.metrics.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
