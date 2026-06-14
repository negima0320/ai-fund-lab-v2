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

from ai_fund_lab_v2.opportunity_ai.training import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    DEFAULT_MODEL_DIR,
    DEFAULT_REPORT_DIR,
    train_opportunity_model,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Phase5-E Opportunity AI expected-edge model.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args(argv)

    result = train_opportunity_model(
        dataset_path=Path(args.dataset_path),
        model_dir=Path(args.model_dir),
        report_dir=Path(args.report_dir),
    )
    print(json.dumps(result.metrics, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.metrics.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
