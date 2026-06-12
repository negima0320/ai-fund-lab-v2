from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402
from ai_fund_lab_v2.safety import build_mock_portfolio_state_from_broker_state, run_safety_dry_run  # noqa: E402
from ai_fund_lab_v2.safety.snapshot_loader import load_broker_state_from_snapshot_files  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run mock-only safety dry-run from broker snapshot JSON files.")
    parser.add_argument(
        "--broker-snapshot",
        action="append",
        required=True,
        help="Broker snapshot JSON file. Pass balance, positions, and orders snapshots as repeated arguments.",
    )
    parser.add_argument("--runtime-dir", default=".runtime", help="Runtime directory for safety report/lock/audit outputs.")
    parser.add_argument(
        "--mock-mismatch",
        choices=("none", "position_quantity"),
        default="none",
        help="Mock-only mismatch injection for dry-run verification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    broker_state = load_broker_state_from_snapshot_files([Path(path) for path in args.broker_snapshot])
    portfolio_state = build_mock_portfolio_state_from_broker_state(broker_state)
    if args.mock_mismatch == "position_quantity" and portfolio_state.positions:
        first = portfolio_state.positions[0]
        portfolio_state = replace(portfolio_state, positions=(replace(first, quantity=first.quantity - 1),) + portfolio_state.positions[1:])
    result = run_safety_dry_run(broker_state, portfolio_state, runtime_dir=args.runtime_dir)
    payload = sanitize_mapping(
        {
            "status": result.report.status.value,
            "issue_count": result.report.issue_count,
            "trading_locked": result.report.trading_locked,
            "report_path": str(result.report_path),
            "lock_path": str(result.lock_path),
            "audit_path": str(result.audit_path),
        }
    )
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 1 if result.report.status.value == "HALT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
