from __future__ import annotations

import argparse
from pathlib import Path

from ai_fund_lab_v2.order_manager.dependency_validator import validate_sell_first_buy_after_fill
from ai_fund_lab_v2.order_manager.order_plan_history import load_order_plan_by_id
from ai_fund_lab_v2.order_manager.paper_ledger import load_paper_ledger, write_paper_ledger
from ai_fund_lab_v2.order_manager.paper_ledger_update import apply_order_plan_to_paper_ledger


class PaperLedgerCliError(RuntimeError):
    pass


def apply_saved_plan_to_paper_ledger(
    *,
    plan_id: str,
    paper_ledger_path: Path,
    runtime_dir: Path | str = ".runtime",
) -> Path:
    plan = load_order_plan_by_id(plan_id, runtime_dir)
    validation = validate_sell_first_buy_after_fill(plan)
    if not validation.valid:
        raise PaperLedgerCliError("; ".join(validation.errors))
    ledger = load_paper_ledger(paper_ledger_path)
    updated = apply_order_plan_to_paper_ledger(plan, ledger)
    return write_paper_ledger(updated, runtime_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply a saved Phase8 OrderPlan to paper ledger dry-run.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--paper-ledger-path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = apply_saved_plan_to_paper_ledger(
        plan_id=args.plan_id,
        paper_ledger_path=Path(args.paper_ledger_path),
        runtime_dir=args.runtime_dir,
    )
    print(path)
    return 0
