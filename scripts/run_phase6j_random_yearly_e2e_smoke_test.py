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

from ai_fund_lab_v2.end_to_end.random_yearly_smoke_test import (  # noqa: E402
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    DEFAULT_OUTPUT_CSV_PATH,
    DEFAULT_OUTPUT_JSON_PATH,
    DEFAULT_SUMMARY_PATH,
    SEED,
    run_phase6j_random_yearly_e2e_smoke_test,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-J random yearly end-to-end smoke test.")
    parser.add_argument("--candidate-path", default=str(DEFAULT_CANDIDATE_PATH))
    parser.add_argument("--opportunity-dataset-path", default=str(DEFAULT_OPPORTUNITY_DATASET_PATH))
    parser.add_argument("--opportunity-model-path", default=str(DEFAULT_OPPORTUNITY_MODEL_PATH))
    parser.add_argument("--label-path", default=str(DEFAULT_LABEL_PATH))
    parser.add_argument("--output-csv-path", default=str(DEFAULT_OUTPUT_CSV_PATH))
    parser.add_argument("--output-json-path", default=str(DEFAULT_OUTPUT_JSON_PATH))
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)

    result = run_phase6j_random_yearly_e2e_smoke_test(
        candidate_path=Path(args.candidate_path),
        opportunity_dataset_path=Path(args.opportunity_dataset_path),
        opportunity_model_path=Path(args.opportunity_model_path),
        label_path=Path(args.label_path),
        output_csv_path=Path(args.output_csv_path),
        output_json_path=Path(args.output_json_path),
        summary_path=Path(args.summary_path),
        seed=args.seed,
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary["completion_status"] != "PHASE6J_E2E_SMOKE_TEST_FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
