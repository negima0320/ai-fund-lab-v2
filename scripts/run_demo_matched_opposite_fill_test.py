#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_demo_matched_opposite_order_fill_test


def main() -> int:
    parser = build_parser("Run Demo matched opposite order fill test.")
    parser.add_argument("--execute-sell-order", action="store_true")
    parser.add_argument("--second-password-present", action="store_true")
    args = parser.parse_args()
    result = run_demo_matched_opposite_order_fill_test(
        trade_date=args.trade_date,
        root=Path(args.root),
        execute_sell_order=args.execute_sell_order,
        second_password_present=args.second_password_present,
    )
    print(result["status"])
    print(result["matched_opposite_order_result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
