from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.pending_virtual_fill_data_refresh import (
    check_pending_virtual_fill_readiness,
    update_canonical_normalized_for_date,
    write_phase9q_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update Phase9 canonical normalized daily_quotes for a pending virtual fill date.")
    parser.add_argument("--target-date", default="2026-06-16")
    parser.add_argument("--canonical-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--source-normalized-path", default=".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet")
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup-existing", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args(argv)

    canonical = update_canonical_normalized_for_date(
        target_date=args.target_date,
        canonical_path=args.canonical_path,
        source_normalized_path=args.source_normalized_path,
        execute=args.execute,
        backup_existing=args.backup_existing,
    )
    readiness = check_pending_virtual_fill_readiness(
        target_date=args.target_date,
        ledger_path=args.ledger_path,
        quotes_path=args.canonical_path,
    )
    payload = write_phase9q_report(
        target_date=args.target_date,
        fetch_status="NOT_EXECUTED_BY_PHASE9Q_CANONICAL_UPDATE",
        canonical_update=canonical,
        readiness=readiness,
    )
    print(json.dumps({"judgment": payload["judgment"], "json": "reports/phase_reports/phase9q_market_data_refresh_for_pending_virtual_fill.json"}, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

