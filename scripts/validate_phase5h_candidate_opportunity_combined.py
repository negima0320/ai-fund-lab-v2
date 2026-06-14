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

from ai_fund_lab_v2.opportunity_ai.combined_validation import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    validate_candidate_opportunity_combined,
)
from ai_fund_lab_v2.opportunity_ai.quality_audit import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    DEFAULT_LATEST_INFERENCE_AUDIT_PATH,
    DEFAULT_LATEST_INFERENCE_PATH,
    DEFAULT_LATEST_INFERENCE_SUMMARY_PATH,
    DEFAULT_MODEL_PATH,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase5-H Candidate + Opportunity combined validation.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--latest-inference-path", default=str(DEFAULT_LATEST_INFERENCE_PATH))
    parser.add_argument("--latest-inference-summary-path", default=str(DEFAULT_LATEST_INFERENCE_SUMMARY_PATH))
    parser.add_argument("--latest-inference-audit-path", default=str(DEFAULT_LATEST_INFERENCE_AUDIT_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    result = validate_candidate_opportunity_combined(
        dataset_path=Path(args.dataset_path),
        model_path=Path(args.model_path),
        latest_inference_path=Path(args.latest_inference_path),
        latest_inference_summary_path=Path(args.latest_inference_summary_path),
        latest_inference_audit_path=Path(args.latest_inference_audit_path),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result.metrics, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.metrics.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
