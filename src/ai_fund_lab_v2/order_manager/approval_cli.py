from __future__ import annotations

import argparse
from pathlib import Path

from ai_fund_lab_v2.order_manager.approval_record import HumanReviewApprovalRecord, write_approval_record
from ai_fund_lab_v2.order_manager.order_plan_history import load_order_plan_by_id


class ApprovalCliError(RuntimeError):
    pass


def create_approval_record_for_plan(
    *,
    plan_id: str,
    reviewer: str,
    decision: str,
    comment: str = "",
    runtime_dir: Path | str = ".runtime",
) -> Path:
    plan = load_order_plan_by_id(plan_id, runtime_dir)
    if plan.executable is not False or plan.live_order_allowed is not False or plan.requires_human_review is not True:
        raise ApprovalCliError("Unsafe OrderPlan cannot be reviewed in Phase8.")
    record = HumanReviewApprovalRecord(
        plan_id=plan.plan_id,
        reviewer=reviewer,
        decision=decision,
        comment=comment,
        approval_does_not_allow_live_order=True,
    )
    return write_approval_record(record, runtime_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a Phase8 human review approval record.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", required=True, choices=("approved", "rejected", "needs_change"))
    parser.add_argument("--comment", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = create_approval_record_for_plan(
        plan_id=args.plan_id,
        reviewer=args.reviewer,
        decision=args.decision,
        comment=args.comment,
        runtime_dir=args.runtime_dir,
    )
    print(path)
    return 0
