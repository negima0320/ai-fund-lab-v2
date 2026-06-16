#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.order_manager import OrderPlanItem, OrderPlanItemSide, create_order_plan
from ai_fund_lab_v2.order_manager.approval_record import HumanReviewApprovalRecord
from ai_fund_lab_v2.order_manager.order_plan_history import sanitized_order_plan_summary
from ai_fund_lab_v2.order_manager.order_plan_store import write_order_plan
from ai_fund_lab_v2.order_manager.phase7_artifact_loader import Phase7ArtifactLoadError, load_phase7_artifact_connection


PHASE8F_SOURCE_PATHS = (
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager",
    REPO_ROOT / "scripts" / "create_phase8f_approval_record.py",
    REPO_ROOT / "scripts" / "apply_phase8f_paper_ledger_dry_run.py",
    REPO_ROOT / "scripts" / "generate_phase8f_order_manager_dry_run_report.py",
    REPO_ROOT / "scripts" / "audit_phase8f_order_manager_dry_run_workflow.py",
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
    source_files = list(_iter_source_files(PHASE8F_SOURCE_PATHS))
    forbidden_hits = _find_tokens(source_files, _forbidden_tokens())
    plan = create_order_plan(
        broker_snapshot_id="broker_snapshot_test",
        paper_ledger_id="paper_ledger_test",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100")),),
    )
    runtime_dir = REPO_ROOT / ".runtime" / "phase8f_audit_tmp"
    plan_path = write_order_plan(plan, runtime_dir)
    stored = json.loads(plan_path.read_text(encoding="utf-8"))
    approval = HumanReviewApprovalRecord(plan_id=plan.plan_id, reviewer="audit", decision="approved")
    summary = sanitized_order_plan_summary(plan)
    missing_artifact_fail_closed = _phase7_missing_artifact_fails_closed()
    order_plan_store_text = (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "order_plan_store.py").read_text(
        encoding="utf-8"
    )
    paper_text = (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "paper_ledger.py").read_text(encoding="utf-8")
    checks = {
        "phase8f_source_files_present": bool(source_files),
        "forbidden_tokens_absent": not forbidden_hits,
        "plan_safety_flags_fixed": plan.executable is False
        and plan.live_order_allowed is False
        and plan.requires_human_review is True,
        "approval_does_not_allow_live_order": approval.approval_does_not_allow_live_order is True,
        "paper_ledger_and_broker_paths_separate": '"order_manager" / "paper" / "ledgers"' in paper_text,
        "order_plan_store_forces_safety_flags": 'payload["executable"] = False' in order_plan_store_text
        and 'payload["live_order_allowed"] = False' in order_plan_store_text
        and 'payload["requires_human_review"] = True' in order_plan_store_text,
        "stored_plan_required_fields": all(
            key in stored for key in ("plan_id", "generated_at", "schema_version", "source", "status")
        ),
        "history_summary_sanitized": not _find_tokens_in_text(json.dumps(summary, ensure_ascii=False), _forbidden_tokens()),
        "phase7_artifact_missing_fail_closed": missing_artifact_fail_closed,
    }
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "forbidden_hits": forbidden_hits,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in source_files],
    }


def _phase7_missing_artifact_fails_closed() -> bool:
    try:
        load_phase7_artifact_connection(REPO_ROOT / ".runtime" / "phase8f_missing_artifact")
    except Phase7ArtifactLoadError:
        return True
    return False


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
        found = _find_tokens_in_text(text, tokens)
        if found:
            hits[str(path.relative_to(REPO_ROOT))] = found
    return hits


def _find_tokens_in_text(text: str, tokens: tuple[str, ...]) -> list[str]:
    return [token for token in tokens if re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text)]


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
