from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.opportunity_ai.model_calibration import run_model_improvement_calibration


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase5-J Opportunity model improvement/calibration.")
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet"),
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl"),
    )
    parser.add_argument(
        "--phase5i-metrics-path",
        type=Path,
        default=Path("reports/opportunity_ai/phase5i/full_history_combined_validation_metrics.json"),
    )
    parser.add_argument(
        "--phase5i-audit-path",
        type=Path,
        default=Path("reports/opportunity_ai/phase5i/full_history_audit.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/opportunity_ai/phase5j"))
    args = parser.parse_args()

    result = run_model_improvement_calibration(
        dataset_path=args.dataset_path,
        model_path=args.model_path,
        phase5i_metrics_path=args.phase5i_metrics_path,
        phase5i_audit_path=args.phase5i_audit_path,
        output_dir=args.output_dir,
    )
    print(f"readiness_status={result.metrics['readiness_status']}")
    print(f"promotion_ready={result.metrics['promotion_ready']}")
    print(f"recommended_policy={result.recommended_policy.get('policy_name')}")


if __name__ == "__main__":
    main()
