from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.order_manager import HumanReviewApprovalRecord, OrderPlanItem, OrderPlanItemSide, create_order_plan

PHASE8E_SOURCE_PATHS = (
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager",
    REPO_ROOT / "scripts" / "audit_phase8e_order_plan_generator.py",
)


def _forbidden_tokens() -> tuple[str, ...]:
    return (
        "place" + "_order",
        "place" + "_combo" + "_order",
        "modify" + "_order",
        "cancel" + "_order",
        "unlock" + "_trade",
        "Open" + "D",
        "Open" + "Sec" + "Trade" + "Context",
        "f" + "utu",
        "raw" + "_payload",
        "acc" + "_id",
        "card" + "_num",
        "uni" + "_card" + "_num",
        "account" + "_number",
        "sec" + "ret",
    )


def run_audit() -> dict[str, object]:
    source_files = list(_iter_source_files(PHASE8E_SOURCE_PATHS))
    forbidden_hits = _find_tokens(source_files, _forbidden_tokens())
    paper_ledger_text = (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "paper_ledger.py").read_text(
        encoding="utf-8"
    )
    sell = OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.SELL, action="REPLACE_SELL_PLAN")
    buy = OrderPlanItem(
        issue_code="6758",
        side=OrderPlanItemSide.BUY,
        action="REPLACE_BUY_AFTER_FILL_PLAN",
        sell_first_group_id="g1",
        depends_on_fill_item_id=sell.item_id,
        requires_broker_snapshot_refresh=True,
    )
    locked_plan = create_order_plan(
        broker_snapshot_id="b",
        paper_ledger_id="p",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="", side=OrderPlanItemSide.NOOP, action="BLOCKED_BY_SAFETY"),),
        lock_state="locked",
    )
    approval = HumanReviewApprovalRecord(plan_id="plan", reviewer="reviewer", decision="approved")
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
    checks = {
        "phase8e_source_files_present": bool(source_files),
        "forbidden_tokens_absent": not forbidden_hits,
        "plan_safety_flags_fixed": locked_plan.executable is False
        and locked_plan.live_order_allowed is False
        and locked_plan.requires_human_review is True,
        "approval_does_not_allow_live_order": approval.approval_does_not_allow_live_order is True,
        "dependency_fields_present": buy.depends_on_fill_item_id == sell.item_id and buy.requires_broker_snapshot_refresh is True,
        "locked_plan_review_only": locked_plan.plan_status.value == "REVIEW_ONLY_LOCKED",
        "reconciliation_halt_status_defined": "REVIEW_ONLY_RECONCILIATION_HALT" in source_text,
        "paper_ledger_update_separate": '"order_manager" / "paper" / "ledgers"' in paper_ledger_text,
    }
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "forbidden_hits": forbidden_hits,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in source_files],
    }


def _iter_source_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(child for child in path.rglob("*.py") if child.is_file())


def _find_tokens(files: list[Path], tokens: tuple[str, ...]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        found = [token for token in tokens if _contains_token(text, token)]
        if found:
            hits[str(path.relative_to(REPO_ROOT))] = found
    return hits


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text) is not None


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
