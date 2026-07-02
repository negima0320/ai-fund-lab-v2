#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_demo_special_fill_simulation


NO_OP_BLOCKS = {
    "demo_special_fill_simulation_not_enabled",
    "existing_buy_waiting_order_not_found",
    "broker_issue_code_not_9000_series",
    "broker_confirmed_executions_present",
    "broker_confirmed_positions_present",
    "demo_special_fill_already_simulated_for_same_order",
    "MARKET_CLOSED",
}


def main() -> int:
    parser = build_parser("Run Demo special fill simulation for 9000-series non-fill rule.")
    parser.add_argument("--enable-simulation", action="store_true")
    args = parser.parse_args()
    result = run_demo_special_fill_simulation(
        trade_date=args.trade_date,
        root=Path(args.root),
        demo_special_fill_simulation_enabled=args.enable_simulation,
    )
    print(result["status"])
    print(result["demo_special_fill_simulation_result_path"])
    blocks = set(result.get("blocks", []))
    if result["status"] in {"PASS", "SKIPPED_MARKET_CLOSED"} or (blocks and blocks <= NO_OP_BLOCKS):
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
