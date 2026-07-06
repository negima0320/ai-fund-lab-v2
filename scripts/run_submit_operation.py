#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_submit_operation


def main() -> int:
    parser = build_parser("Submit operation orders through the common runtime entry.")
    parser.add_argument("--execute-demo-order", action="store_true", help="Requests live order execution only when TACHIBANA_API_ENV=demo; production remains blocked.")
    parser.add_argument("--second-password-present", action="store_true")
    args = parser.parse_args()
    result = run_submit_operation(
        trade_date=args.trade_date,
        root=Path(args.root),
        execute_order=args.execute_demo_order,
        second_password_present=args.second_password_present,
    )
    print(result["status"])
    print(result["submitted_orders_path"])
    return 0 if Path(result["submitted_orders_path"]).exists() and result.get("production_order_submitted") is not True else 2


if __name__ == "__main__":
    raise SystemExit(main())
