#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_market_refresh


def main() -> int:
    parser = build_parser("Run Operation market and feature refresh manifests.")
    parser.add_argument("--allow-api-fetch", action="store_true")
    parser.add_argument("--from-date", default="")
    parser.add_argument("--fetch-mode", default="per-date", choices=["range", "per-date"])
    args = parser.parse_args()
    result = run_market_refresh(
        trade_date=args.trade_date,
        root=Path(args.root),
        allow_api_fetch=args.allow_api_fetch,
        from_date=args.from_date or None,
        fetch_mode=args.fetch_mode,
    )
    print(result["status"])
    print(result["market_refresh_manifest_path"])
    return 0 if result["status"] in {"PASS", "SKIPPED_MARKET_CLOSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
