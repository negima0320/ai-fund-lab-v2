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

from ai_fund_lab_v2.opportunity_ai.inference import (  # noqa: E402
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_FEATURE_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TRAINING_METRICS_PATH,
    run_opportunity_inference,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase5-F Opportunity AI inference for latest Candidate Top50.")
    parser.add_argument("--candidate-path", default=str(DEFAULT_CANDIDATE_PATH))
    parser.add_argument("--feature-path", default=str(DEFAULT_FEATURE_PATH))
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--training-metrics-path", default=str(DEFAULT_TRAINING_METRICS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    result = run_opportunity_inference(
        candidate_path=Path(args.candidate_path),
        feature_path=Path(args.feature_path),
        model_path=Path(args.model_path),
        training_metrics_path=Path(args.training_metrics_path),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
