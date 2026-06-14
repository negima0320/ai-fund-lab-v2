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

from ai_fund_lab_v2.position_management_ai.danger_only_exit_validation import (  # noqa: E402
    DEFAULT_ACTION_STATS_PATH,
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_LONG_FEATURE_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    DEFAULT_OUTPUT_CSV_PATH,
    DEFAULT_OUTPUT_JSON_PATH,
    DEFAULT_SUMMARY_PATH,
    DEFAULT_YEARLY_SUMMARY_PATH,
    SEED,
    run_phase6n_danger_only_exit_validation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-N Danger-Only Exit validation.")
    parser.add_argument("--candidate-path", default=str(DEFAULT_CANDIDATE_PATH))
    parser.add_argument("--opportunity-dataset-path", default=str(DEFAULT_OPPORTUNITY_DATASET_PATH))
    parser.add_argument("--opportunity-model-path", default=str(DEFAULT_OPPORTUNITY_MODEL_PATH))
    parser.add_argument("--label-path", default=str(DEFAULT_LABEL_PATH))
    parser.add_argument("--long-feature-path", default=str(DEFAULT_LONG_FEATURE_PATH))
    parser.add_argument("--output-csv-path", default=str(DEFAULT_OUTPUT_CSV_PATH))
    parser.add_argument("--output-json-path", default=str(DEFAULT_OUTPUT_JSON_PATH))
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--yearly-summary-path", default=str(DEFAULT_YEARLY_SUMMARY_PATH))
    parser.add_argument("--action-stats-path", default=str(DEFAULT_ACTION_STATS_PATH))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dates-per-year", type=int, default=5)
    args = parser.parse_args(argv)

    result = run_phase6n_danger_only_exit_validation(
        candidate_path=Path(args.candidate_path),
        opportunity_dataset_path=Path(args.opportunity_dataset_path),
        opportunity_model_path=Path(args.opportunity_model_path),
        label_path=Path(args.label_path),
        long_feature_path=Path(args.long_feature_path),
        output_csv_path=Path(args.output_csv_path),
        output_json_path=Path(args.output_json_path),
        summary_path=Path(args.summary_path),
        yearly_summary_path=Path(args.yearly_summary_path),
        action_stats_path=Path(args.action_stats_path),
        seed=args.seed,
        dates_per_year=args.dates_per_year,
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
