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

from ai_fund_lab_v2.position_management_ai.feature_builder import (  # noqa: E402
    DEFAULT_OUTPUT_CSV_PATH,
    DEFAULT_OUTPUT_JSON_PATH,
    run_phase6b_position_feature_dry_run,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-B Position Management feature dry-run.")
    parser.add_argument("--quote-path", default=None)
    parser.add_argument("--opportunity-path", default=None)
    parser.add_argument("--output-csv-path", default=str(DEFAULT_OUTPUT_CSV_PATH))
    parser.add_argument("--output-json-path", default=str(DEFAULT_OUTPUT_JSON_PATH))
    args = parser.parse_args(argv)

    result = run_phase6b_position_feature_dry_run(
        quote_path=Path(args.quote_path) if args.quote_path else None,
        opportunity_path=Path(args.opportunity_path) if args.opportunity_path else None,
        output_csv_path=Path(args.output_csv_path),
        output_json_path=Path(args.output_json_path),
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
