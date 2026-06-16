from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.virtual_fill_processor import process_virtual_fills_from_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase9-F virtual fill processor.")
    parser.add_argument("--ledger-path", required=True)
    parser.add_argument("--quotes-path", required=True)
    parser.add_argument("--execution-date", required=True)
    parser.add_argument("--output-root", default=".runtime")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = process_virtual_fills_from_files(
        ledger_path=Path(args.ledger_path),
        quotes_path=Path(args.quotes_path),
        execution_date=args.execution_date,
        runtime_dir=args.runtime_dir,
        output_root=args.output_root,
        dry_run=args.dry_run,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

