from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.opportunity_ai.policy_finalization import finalize_opportunity_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize Phase5-K Opportunity ranking policy candidates.")
    parser.add_argument("--phase5j-dir", type=Path, default=Path("reports/opportunity_ai/phase5j"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/opportunity_ai/phase5k"))
    args = parser.parse_args()

    result = finalize_opportunity_policy(
        phase5j_dir=args.phase5j_dir,
        output_dir=args.output_dir,
    )
    print(f"readiness_status={result.summary['readiness_status']}")
    print(f"promotion_ready={result.summary['promotion_ready']}")
    print(f"policy_candidate_count={result.audit['policy_candidate_count']}")


if __name__ == "__main__":
    main()
