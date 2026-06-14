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

from ai_fund_lab_v2.position_management_ai.calibration import (  # noqa: E402
    DEFAULT_ALIGNMENT_CSV_PATH,
    DEFAULT_ALIGNMENT_JSON_PATH,
    DEFAULT_AUDIT_PATH,
    DEFAULT_COMPARISON_PATH,
    DEFAULT_MISMATCH_CSV_PATH,
    DEFAULT_PHASE6C_DATASET_PATH,
    run_phase6e_baseline_calibration,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-E calibrated baseline alignment audit.")
    parser.add_argument("--dataset-path", default=str(DEFAULT_PHASE6C_DATASET_PATH))
    parser.add_argument("--alignment-csv-path", default=str(DEFAULT_ALIGNMENT_CSV_PATH))
    parser.add_argument("--alignment-json-path", default=str(DEFAULT_ALIGNMENT_JSON_PATH))
    parser.add_argument("--mismatch-csv-path", default=str(DEFAULT_MISMATCH_CSV_PATH))
    parser.add_argument("--audit-path", default=str(DEFAULT_AUDIT_PATH))
    parser.add_argument("--comparison-path", default=str(DEFAULT_COMPARISON_PATH))
    args = parser.parse_args(argv)

    result = run_phase6e_baseline_calibration(
        dataset_path=Path(args.dataset_path),
        alignment_csv_path=Path(args.alignment_csv_path),
        alignment_json_path=Path(args.alignment_json_path),
        mismatch_csv_path=Path(args.mismatch_csv_path),
        audit_path=Path(args.audit_path),
        comparison_path=Path(args.comparison_path),
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
