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

from ai_fund_lab_v2.position_management_ai.historical_validation import (  # noqa: E402
    DEFAULT_ACTION_STATS_PATH,
    DEFAULT_COMPARISON_PATH,
    DEFAULT_LONG_FEATURE_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    DEFAULT_VALIDATION_CSV_PATH,
    DEFAULT_VALIDATION_JSON_PATH,
    run_phase6h_historical_validation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-H Position Management historical validation.")
    parser.add_argument("--opportunity-dataset-path", default=str(DEFAULT_OPPORTUNITY_DATASET_PATH))
    parser.add_argument("--opportunity-model-path", default=str(DEFAULT_OPPORTUNITY_MODEL_PATH))
    parser.add_argument("--long-feature-path", default=str(DEFAULT_LONG_FEATURE_PATH))
    parser.add_argument("--output-csv-path", default=str(DEFAULT_VALIDATION_CSV_PATH))
    parser.add_argument("--output-json-path", default=str(DEFAULT_VALIDATION_JSON_PATH))
    parser.add_argument("--comparison-path", default=str(DEFAULT_COMPARISON_PATH))
    parser.add_argument("--action-stats-path", default=str(DEFAULT_ACTION_STATS_PATH))
    parser.add_argument("--validation-year", type=int, default=2025)
    parser.add_argument("--max-target-dates", type=int, default=80)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args(argv)

    result = run_phase6h_historical_validation(
        opportunity_dataset_path=Path(args.opportunity_dataset_path),
        opportunity_model_path=Path(args.opportunity_model_path),
        long_feature_path=Path(args.long_feature_path),
        output_csv_path=Path(args.output_csv_path),
        output_json_path=Path(args.output_json_path),
        comparison_path=Path(args.comparison_path),
        action_stats_path=Path(args.action_stats_path),
        validation_year=args.validation_year,
        max_target_dates=args.max_target_dates,
        top_n=args.top_n,
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
