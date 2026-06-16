from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.daily_pipeline_runner import run_daily_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-C daily pipeline skeleton.")
    parser.add_argument("--date", dest="run_date")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--daily-quotes-path")
    parser.add_argument("--listed-info-path")
    parser.add_argument("--artifact-root")
    parser.add_argument("--candidate-artifact")
    parser.add_argument("--opportunity-artifact")
    parser.add_argument("--position-artifact")
    parser.add_argument("--allocation-artifact")
    parser.add_argument("--order-plan-artifact")
    parser.add_argument("--ledger-path")
    parser.add_argument("--dry-run", action="store_true", help="Kept for Phase9 command compatibility; no live operation is performed.")
    args = parser.parse_args(argv)
    result = run_daily_pipeline(
        run_date=args.run_date,
        runtime_dir=args.runtime_dir,
        reports_root=args.reports_root,
        daily_quotes_path=Path(args.daily_quotes_path) if args.daily_quotes_path else None,
        listed_info_path=Path(args.listed_info_path) if args.listed_info_path else None,
        artifact_root=Path(args.artifact_root) if args.artifact_root else None,
        candidate_artifact=Path(args.candidate_artifact) if args.candidate_artifact else None,
        opportunity_artifact=Path(args.opportunity_artifact) if args.opportunity_artifact else None,
        position_artifact=Path(args.position_artifact) if args.position_artifact else None,
        allocation_artifact=Path(args.allocation_artifact) if args.allocation_artifact else None,
        order_plan_artifact=Path(args.order_plan_artifact) if args.order_plan_artifact else None,
        use_artifacts=bool(args.artifact_root or args.candidate_artifact or args.opportunity_artifact or args.position_artifact or args.allocation_artifact or args.order_plan_artifact),
        ledger_path=Path(args.ledger_path) if args.ledger_path else None,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
