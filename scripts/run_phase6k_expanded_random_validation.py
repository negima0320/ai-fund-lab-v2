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

from ai_fund_lab_v2.end_to_end.expanded_random_validation import (  # noqa: E402
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    DEFAULT_OUTPUT_CSV_PATH,
    DEFAULT_OUTPUT_JSON_PATH,
    DEFAULT_RISK_GUARD_PATH,
    DEFAULT_TAIL_DILUTION_PATH,
    DEFAULT_TOPN_PATH,
    DEFAULT_YEARLY_SUMMARY_PATH,
    SEED,
    run_phase6k_expanded_random_validation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-K expanded random historical validation.")
    parser.add_argument("--candidate-path", default=str(DEFAULT_CANDIDATE_PATH))
    parser.add_argument("--opportunity-dataset-path", default=str(DEFAULT_OPPORTUNITY_DATASET_PATH))
    parser.add_argument("--opportunity-model-path", default=str(DEFAULT_OPPORTUNITY_MODEL_PATH))
    parser.add_argument("--label-path", default=str(DEFAULT_LABEL_PATH))
    parser.add_argument("--output-csv-path", default=str(DEFAULT_OUTPUT_CSV_PATH))
    parser.add_argument("--output-json-path", default=str(DEFAULT_OUTPUT_JSON_PATH))
    parser.add_argument("--yearly-summary-path", default=str(DEFAULT_YEARLY_SUMMARY_PATH))
    parser.add_argument("--topn-path", default=str(DEFAULT_TOPN_PATH))
    parser.add_argument("--risk-guard-path", default=str(DEFAULT_RISK_GUARD_PATH))
    parser.add_argument("--tail-dilution-path", default=str(DEFAULT_TAIL_DILUTION_PATH))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dates-per-year", type=int, default=5)
    args = parser.parse_args(argv)

    result = run_phase6k_expanded_random_validation(
        candidate_path=Path(args.candidate_path),
        opportunity_dataset_path=Path(args.opportunity_dataset_path),
        opportunity_model_path=Path(args.opportunity_model_path),
        label_path=Path(args.label_path),
        output_csv_path=Path(args.output_csv_path),
        output_json_path=Path(args.output_json_path),
        yearly_summary_path=Path(args.yearly_summary_path),
        topn_path=Path(args.topn_path),
        risk_guard_path=Path(args.risk_guard_path),
        tail_dilution_path=Path(args.tail_dilution_path),
        seed=args.seed,
        dates_per_year=args.dates_per_year,
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary["completion_status"] != "PHASE6K_EXPANDED_VALIDATION_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
