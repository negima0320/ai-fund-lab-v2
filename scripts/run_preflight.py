#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_preflight


def main() -> int:
    parser = build_parser("Run operation preflight.")
    parser.add_argument("--refresh-broker-readonly", action="store_true")
    args = parser.parse_args()
    result = run_preflight(trade_date=args.trade_date, root=Path(args.root), refresh_broker_readonly=args.refresh_broker_readonly)
    print(result["status"])
    print(result["artifact_path"])
    return 0 if result["status"] in {"PASS", "REVIEW_REQUIRED", "PASS_MARKET_CLOSED_READONLY_ONLY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
