#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_daily_report


def main() -> int:
    parser = build_parser("Generate Operation daily reports.")
    parser.add_argument("--send-notifications", action="store_true")
    args = parser.parse_args()
    result = run_daily_report(trade_date=args.trade_date, root=Path(args.root), send_notifications=args.send_notifications)
    print(result["status"])
    print(result["daily_report_refs_path"])
    return 0 if Path(result["daily_report_refs_path"]).exists() else 2


if __name__ == "__main__":
    raise SystemExit(main())
