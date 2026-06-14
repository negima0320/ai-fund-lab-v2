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

from ai_fund_lab_v2.end_to_end.top3_policy_validation import (  # noqa: E402
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_COMPARISON_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    DEFAULT_OUTPUT_CSV_PATH,
    DEFAULT_OUTPUT_JSON_PATH,
    DEFAULT_RECOMMENDATION_PATH,
    DEFAULT_RISK_POLICY_PATH,
    DEFAULT_YEARLY_TOP3_PATH,
    PHASE6L_TOP3_POLICY_NOT_VALIDATED,
    SEED,
    run_phase6l_top3_policy_validation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-L Top3 buy policy validation.")
    parser.add_argument("--candidate-path", default=str(DEFAULT_CANDIDATE_PATH))
    parser.add_argument("--opportunity-dataset-path", default=str(DEFAULT_OPPORTUNITY_DATASET_PATH))
    parser.add_argument("--opportunity-model-path", default=str(DEFAULT_OPPORTUNITY_MODEL_PATH))
    parser.add_argument("--label-path", default=str(DEFAULT_LABEL_PATH))
    parser.add_argument("--output-csv-path", default=str(DEFAULT_OUTPUT_CSV_PATH))
    parser.add_argument("--output-json-path", default=str(DEFAULT_OUTPUT_JSON_PATH))
    parser.add_argument("--comparison-path", default=str(DEFAULT_COMPARISON_PATH))
    parser.add_argument("--yearly-top3-path", default=str(DEFAULT_YEARLY_TOP3_PATH))
    parser.add_argument("--risk-policy-path", default=str(DEFAULT_RISK_POLICY_PATH))
    parser.add_argument("--recommendation-path", default=str(DEFAULT_RECOMMENDATION_PATH))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dates-per-year", type=int, default=5)
    args = parser.parse_args(argv)

    result = run_phase6l_top3_policy_validation(
        candidate_path=Path(args.candidate_path),
        opportunity_dataset_path=Path(args.opportunity_dataset_path),
        opportunity_model_path=Path(args.opportunity_model_path),
        label_path=Path(args.label_path),
        output_csv_path=Path(args.output_csv_path),
        output_json_path=Path(args.output_json_path),
        comparison_path=Path(args.comparison_path),
        yearly_top3_path=Path(args.yearly_top3_path),
        risk_policy_path=Path(args.risk_policy_path),
        recommendation_path=Path(args.recommendation_path),
        seed=args.seed,
        dates_per_year=args.dates_per_year,
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if result.summary["completion_status"] == PHASE6L_TOP3_POLICY_NOT_VALIDATED else 0


if __name__ == "__main__":
    raise SystemExit(main())
