from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai import (  # noqa: E402
    adapt_daily_quotes_normalized,
    write_candidate_loader_contract_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Phase4-F Candidate real data loader contract with fixture data.")
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory for contract artifacts.")
    parser.add_argument("--as-of-date", default="2026-06-01", help="Adapter as_of_date.")
    parser.add_argument("--lookback-rows", type=int, default=80, help="Per-code lookback rows retained by the adapter.")
    args = parser.parse_args(argv)

    result = adapt_daily_quotes_normalized(
        _fixture_daily_quotes_normalized(args.as_of_date),
        as_of_date=args.as_of_date,
        lookback_rows=args.lookback_rows,
        input_source_path="fixture://phase4f/daily_quotes_normalized",
        input_manifest_path="fixture://phase4f/manifest",
    )
    paths = write_candidate_loader_contract_outputs(result.rows, audit=result.audit, runtime_dir=args.runtime_dir)
    summary = {
        "status": result.audit.status,
        "input_row_count": result.audit.input_row_count,
        "filtered_row_count": result.audit.filtered_row_count,
        "dropped_future_row_count": result.audit.dropped_future_row_count,
        "invalid_row_count": result.audit.invalid_row_count,
        "source_snapshot_id": result.audit.source_snapshot_id,
        "rows_path": str(paths["rows"]),
        "manifest_path": str(paths["manifest"]),
        "audit_path": str(paths["audit"]),
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.audit.status in {"OK", "WARNING"} else 1


def _fixture_daily_quotes_normalized(as_of_date: str) -> list[dict[str, object]]:
    return [
        {
            "Date": "2026-05-28",
            "Code": "72030",
            "Open": 1000,
            "High": 1030,
            "Low": 990,
            "Close": 1020,
            "Volume": 100_000,
            "PriceSource": "adjusted",
            "SchemaVersion": 2,
        },
        {
            "Date": as_of_date,
            "Code": "72030",
            "Open": 1020,
            "High": 1060,
            "Low": 1010,
            "Close": 1050,
            "Volume": 110_000,
            "PriceSource": "adjusted",
            "SchemaVersion": 2,
        },
        {
            "Date": "2026-06-02",
            "Code": "72030",
            "Open": 9999,
            "High": 9999,
            "Low": 9999,
            "Close": 9999,
            "Volume": 999_999,
            "PriceSource": "adjusted",
            "SchemaVersion": 2,
        },
    ]


if __name__ == "__main__":
    raise SystemExit(main())
