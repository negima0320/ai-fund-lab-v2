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

from ai_fund_lab_v2.position_management_ai.realdata_dry_run import (  # noqa: E402
    DEFAULT_ALIGNMENT_OUTPUT_PATH,
    DEFAULT_AUDIT_OUTPUT_PATH,
    DEFAULT_FEATURE_OUTPUT_PATH,
    DEFAULT_LABEL_OUTPUT_PATH,
    DEFAULT_QUOTE_PATH,
    run_phase6f_realdata_position_dry_run,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-F small real-data Position Management dry-run.")
    parser.add_argument("--quote-path", default=str(DEFAULT_QUOTE_PATH))
    parser.add_argument("--feature-output-path", default=str(DEFAULT_FEATURE_OUTPUT_PATH))
    parser.add_argument("--label-output-path", default=str(DEFAULT_LABEL_OUTPUT_PATH))
    parser.add_argument("--alignment-output-path", default=str(DEFAULT_ALIGNMENT_OUTPUT_PATH))
    parser.add_argument("--audit-output-path", default=str(DEFAULT_AUDIT_OUTPUT_PATH))
    parser.add_argument("--max-codes", type=int, default=12)
    parser.add_argument("--max-target-dates", type=int, default=3)
    args = parser.parse_args(argv)

    result = run_phase6f_realdata_position_dry_run(
        quote_path=Path(args.quote_path),
        feature_output_path=Path(args.feature_output_path),
        label_output_path=Path(args.label_output_path),
        alignment_output_path=Path(args.alignment_output_path),
        audit_output_path=Path(args.audit_output_path),
        max_codes=args.max_codes,
        max_target_dates=args.max_target_dates,
    )
    print(json.dumps(result.audit, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.audit.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
