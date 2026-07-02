#!/usr/bin/env python3
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.operations.operations import build_parser, run_approval_prepare


def main() -> int:
    parser = build_parser("Prepare operation approval artifacts.")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--auto-demo-approval", action="store_true")
    parser.add_argument("--approver-label", default="")
    parser.add_argument("--max-notional", default=None)
    args = parser.parse_args()
    result = run_approval_prepare(
        trade_date=args.trade_date,
        root=Path(args.root),
        approve=args.approve,
        auto_demo_approval=args.auto_demo_approval,
        approver_label=args.approver_label,
        max_notional=Decimal(args.max_notional) if args.max_notional is not None else None,
    )
    print(result["status"])
    print(result["approval_artifact_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
