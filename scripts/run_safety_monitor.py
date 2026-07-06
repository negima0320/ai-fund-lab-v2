#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_safety_monitor


def main() -> int:
    parser = build_parser("Run Operation safety monitor.")
    args = parser.parse_args()
    result = run_safety_monitor(trade_date=args.trade_date, root=Path(args.root))
    print(result["status"])
    print(result["safety_monitor_result_path"])
    return 0 if Path(result["safety_monitor_result_path"]).exists() else 2


if __name__ == "__main__":
    raise SystemExit(main())
