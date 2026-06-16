#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.order_manager.dry_run_report import write_dry_run_report
from ai_fund_lab_v2.order_manager.order_plan_history import load_order_plan_by_id
from ai_fund_lab_v2.order_manager.paper_ledger import load_paper_ledger
from ai_fund_lab_v2.order_manager.reconciliation import OrderManagerReconciliationResult
from ai_fund_lab_v2.safety.lock_state_resolver import resolve_current_lock_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Phase8-F Order Manager dry-run report.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--reports-dir", default="reports/phase_reports")
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--reconciliation-path", required=True)
    parser.add_argument("--paper-ledger-path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_order_plan_by_id(args.plan_id, args.runtime_dir)
    reconciliation = _load_reconciliation(Path(args.reconciliation_path))
    paper = load_paper_ledger(Path(args.paper_ledger_path)) if args.paper_ledger_path else None
    paths = write_dry_run_report(
        order_plan=plan,
        reconciliation=reconciliation,
        safety_state=resolve_current_lock_state(args.runtime_dir),
        paper_ledger=paper,
        runtime_dir=args.runtime_dir,
        reports_dir=args.reports_dir,
    )
    for path in paths:
        print(path)
    return 0


def _load_reconciliation(path: Path) -> OrderManagerReconciliationResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return OrderManagerReconciliationResult(
        broker_snapshot_id=str(payload.get("broker_snapshot_id", "")),
        paper_ledger_id=str(payload.get("paper_ledger_id", "")),
        status=str(payload.get("status", "UNKNOWN")),
        safety_status=str(payload.get("safety_status", "UNKNOWN")),
        warning=bool(payload.get("warning", True)),
        halt_candidate=bool(payload.get("halt_candidate", True)),
        summary=str(payload.get("summary", "")),
        generated_at=str(payload.get("generated_at", "")),
        reconciliation_id=str(payload.get("reconciliation_id", "")),
    )


if __name__ == "__main__":
    raise SystemExit(main())
