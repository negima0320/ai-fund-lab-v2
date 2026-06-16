from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.daily_operation_runner import run_daily_operation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-G daily operation.")
    parser.add_argument("--date", dest="run_date", required=True)
    parser.add_argument("--mode", choices=("dry-run", "paper-trading", "report-only", "fill-only"), default="dry-run")
    parser.add_argument("--output-root", default=".runtime/phase9")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--ledger-path")
    parser.add_argument("--artifact-root")
    parser.add_argument("--quotes-path")
    parser.add_argument("--daily-quotes-path")
    parser.add_argument("--listed-info-path")
    parser.add_argument("--force-unlock", action="store_true")
    args = parser.parse_args(argv)
    result = run_daily_operation(
        run_date=args.run_date,
        mode=args.mode,
        operation_root=args.output_root,
        runtime_dir=args.runtime_dir,
        reports_root=args.reports_root,
        ledger_path=Path(args.ledger_path) if args.ledger_path else None,
        artifact_root=Path(args.artifact_root) if args.artifact_root else None,
        quotes_path=Path(args.quotes_path) if args.quotes_path else None,
        daily_quotes_path=Path(args.daily_quotes_path) if args.daily_quotes_path else None,
        listed_info_path=Path(args.listed_info_path) if args.listed_info_path else None,
        force_unlock=args.force_unlock,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

