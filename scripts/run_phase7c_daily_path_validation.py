#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.capital_allocation_ai.phase7c_daily_path_validation import run_phase7c_daily_path_validation, to_jsonable  # noqa: E402


def main() -> None:
    result = run_phase7c_daily_path_validation()
    print(json.dumps(to_jsonable(result["summary"]), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
