from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.order_manager.paper_ledger import PaperLedger, load_paper_ledger, paper_ledger_directory


@dataclass(frozen=True)
class PaperLedgerDiff:
    before_ledger_id: str
    after_ledger_id: str
    cash_delta: Decimal
    buying_power_delta: Decimal
    position_deltas: dict[str, str]
    new_execution_ids: tuple[str, ...]
    removed_execution_ids: tuple[str, ...]
    blocked_or_waiting_items: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_ledger_id": self.before_ledger_id,
            "after_ledger_id": self.after_ledger_id,
            "cash_delta": str(self.cash_delta),
            "buying_power_delta": str(self.buying_power_delta),
            "position_deltas": self.position_deltas,
            "new_execution_ids": list(self.new_execution_ids),
            "removed_execution_ids": list(self.removed_execution_ids),
            "blocked_or_waiting_items": list(self.blocked_or_waiting_items),
            "broker_snapshot_compared": False,
        }


def diff_paper_ledgers(before: PaperLedger, after: PaperLedger, blocked_or_waiting_items: tuple[str, ...] = ()) -> PaperLedgerDiff:
    before_positions = {position.issue_code: position.quantity for position in before.positions}
    after_positions = {position.issue_code: position.quantity for position in after.positions}
    position_deltas = {
        issue_code: str(after_positions.get(issue_code, Decimal("0")) - before_positions.get(issue_code, Decimal("0")))
        for issue_code in sorted(set(before_positions) | set(after_positions))
        if after_positions.get(issue_code, Decimal("0")) != before_positions.get(issue_code, Decimal("0"))
    }
    before_exec = {execution.paper_execution_id for execution in before.executions}
    after_exec = {execution.paper_execution_id for execution in after.executions}
    return PaperLedgerDiff(
        before_ledger_id=before.ledger_id,
        after_ledger_id=after.ledger_id,
        cash_delta=after.cash - before.cash,
        buying_power_delta=after.buying_power - before.buying_power,
        position_deltas=position_deltas,
        new_execution_ids=tuple(sorted(after_exec - before_exec)),
        removed_execution_ids=tuple(sorted(before_exec - after_exec)),
        blocked_or_waiting_items=blocked_or_waiting_items,
    )


def latest_two_paper_ledgers(runtime_dir: Path | str = ".runtime") -> tuple[PaperLedger, PaperLedger]:
    directory = paper_ledger_directory(runtime_dir)
    candidates = sorted(directory.glob("*.json"), key=lambda path: (path.stat().st_mtime, path.name))
    if len(candidates) < 2:
        raise RuntimeError("At least two paper ledger files are required for diff.")
    return load_paper_ledger(candidates[-2]), load_paper_ledger(candidates[-1])


def write_paper_ledger_diff(
    before: PaperLedger,
    after: PaperLedger,
    *,
    runtime_dir: Path | str = ".runtime",
    blocked_or_waiting_items: tuple[str, ...] = (),
) -> Path:
    diff = diff_paper_ledgers(before, after, blocked_or_waiting_items)
    path = Path(runtime_dir) / "order_manager" / "paper" / "diffs" / f"{before.ledger_id}__{after.ledger_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diff.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diff Phase8 paper ledger history.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--before")
    parser.add_argument("--after")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.before and args.after:
        before, after = load_paper_ledger(Path(args.before)), load_paper_ledger(Path(args.after))
    else:
        before, after = latest_two_paper_ledgers(args.runtime_dir)
    print(write_paper_ledger_diff(before, after, runtime_dir=args.runtime_dir))
    return 0
