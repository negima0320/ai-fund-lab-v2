from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.opportunity_ai.design_compliance import run_design_compliance_review


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase5-M Opportunity AI design compliance review.")
    parser.add_argument("--dataset-path", type=Path, default=Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet"))
    parser.add_argument("--model-path", type=Path, default=Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/opportunity_ai/phase5m"))
    args = parser.parse_args()

    result = run_design_compliance_review(
        dataset_path=args.dataset_path,
        model_path=args.model_path,
        output_dir=args.output_dir,
    )
    print(f"readiness_status={result.review['readiness_status']}")
    print(f"promotion_ready={result.review['promotion_ready']}")
    print(f"actual_feature_count={result.review['actual_feature_count']}")


if __name__ == "__main__":
    main()
