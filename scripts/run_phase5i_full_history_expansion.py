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

from ai_fund_lab_v2.opportunity_ai.full_history_expansion import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    run_full_history_expansion,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase5-I full history expansion.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--mode", choices=("full", "sampled"), default="full")
    parser.add_argument("--max-dates", type=int, default=None)
    args = parser.parse_args(argv)

    result = run_full_history_expansion(
        output_dir=Path(args.output_dir),
        mode=args.mode,
        max_dates=args.max_dates,
    )
    print(json.dumps(result.metrics, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.metrics.get("status") in {"OK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
