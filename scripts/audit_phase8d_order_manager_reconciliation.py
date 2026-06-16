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

from ai_fund_lab_v2.order_manager import OrderPlan, OrderPlanItem, OrderPlanItemSide, create_order_plan

PHASE8D_SOURCE_PATHS = (
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager",
    REPO_ROOT / "scripts" / "audit_phase8d_order_manager_reconciliation.py",
)


def _forbidden_tokens() -> tuple[str, ...]:
    return (
        "place" + "_order",
        "place" + "_combo" + "_order",
        "modify" + "_order",
        "cancel" + "_order",
        "unlock" + "_trade",
        "Open" + "Sec" + "Trade" + "Context",
        "Open" + "D",
        "f" + "utu",
        "raw" + "_payload",
        "acc" + "_id",
        "card" + "_num",
        "uni" + "_card" + "_num",
        "account" + "_number",
        "sec" + "ret",
    )


def run_audit() -> dict[str, object]:
    source_files = list(_iter_source_files(PHASE8D_SOURCE_PATHS))
    forbidden_hits = _find_tokens(source_files, _forbidden_tokens())
    plan = OrderPlan(
        broker_snapshot_id="balance_mock",
        paper_ledger_id="paper_mock",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN"),),
    )
    locked_plan = create_order_plan(
        broker_snapshot_id="balance_mock",
        paper_ledger_id="paper_mock",
        policy_id="PHASE8_REVIEW_ONLY",
        items=(OrderPlanItem(issue_code="", side=OrderPlanItemSide.NOOP, action="BLOCKED_BY_SAFETY"),),
        lock_state="locked",
        blocked_reasons=("IGNORED_WHEN_LOCKED",),
    )
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
    checks = {
        "phase8d_source_files_present": bool(source_files),
        "forbidden_tokens_absent": not forbidden_hits,
        "order_plan_executable_false": plan.executable is False,
        "order_plan_live_order_allowed_false": plan.live_order_allowed is False,
        "order_plan_requires_human_review_true": plan.requires_human_review is True,
        "locked_plan_review_only": locked_plan.plan_status.value == "REVIEW_ONLY_LOCKED",
        "paper_ledger_path_separated": "order_manager\" / \"paper\" / \"ledgers" in source_text,
        "broker_snapshot_loader_reads_snapshots": "broker\" / \"snapshots" not in source_text
        and "BrokerRuntimePaths" in source_text,
        "human_report_mentions_no_live_execution": "Phase8では実発注しない" in source_text,
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
