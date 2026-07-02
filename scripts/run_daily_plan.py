#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_daily_plan


def main() -> int:
    parser = build_parser("Generate operation order plan.")
    parser.add_argument("--items-json", default="")
    parser.add_argument("--feature-source", action="append", default=[])
    args = parser.parse_args()
    items = json.loads(Path(args.items_json).read_text(encoding="utf-8")) if args.items_json else None
    result = run_daily_plan(
        trade_date=args.trade_date,
        root=Path(args.root),
        feature_sources=args.feature_source or None,
        plan_items=items,
    )
    print(result["status"])
    print(result["order_plan_path"])
    return 0 if result["status"] in {"PASS", "SKIPPED_MARKET_CLOSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
