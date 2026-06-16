from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.first_virtual_fill import run_first_virtual_fill


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-P first virtual fill.")
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--execution-date", default="2026-06-16")
    parser.add_argument("--quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--mode", choices=("dry-run", "execute"), default="dry-run")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--markdown-report-path", default="docs/phase_reports/phase9p_first_virtual_fill.md")
    parser.add_argument("--json-report-path", default="reports/phase_reports/phase9p_first_virtual_fill.json")
    parser.add_argument("--public-summary-path", default=None)
    args = parser.parse_args(argv)
    result = run_first_virtual_fill(
        ledger_path=args.ledger_path,
        quotes_path=args.quotes_path,
        execution_date=args.execution_date,
        mode=args.mode,
        runtime_dir=args.runtime_dir,
        docs_report_path=args.markdown_report_path,
        json_report_path=args.json_report_path,
        public_summary_path=args.public_summary_path,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status != "FIRST_VIRTUAL_FILL_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
