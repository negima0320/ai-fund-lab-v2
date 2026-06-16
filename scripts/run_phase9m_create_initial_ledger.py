from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.initial_ledger import INITIAL_LEDGER_CREATED, create_initial_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Phase9 initial paper trading ledger.")
    parser.add_argument("--initial-cash", required=True)
    parser.add_argument("--currency", default="JPY")
    parser.add_argument("--ledger-root", default=".runtime/phase9/ledger")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    result = create_initial_ledger(
        initial_cash=Decimal(args.initial_cash),
        currency=args.currency,
        ledger_root=args.ledger_root,
        start_date=args.start_date,
        overwrite=args.overwrite,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=True, sort_keys=True))
    return 0 if result.status == INITIAL_LEDGER_CREATED else 2


if __name__ == "__main__":
    raise SystemExit(main())

