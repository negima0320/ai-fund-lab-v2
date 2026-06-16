#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.moomoo.snapshot_sync import write_moomoo_mock_snapshots
from ai_fund_lab_v2.order_manager import (
    HumanReviewApprovalRecord,
    OrderPlanItem,
    OrderPlanItemSide,
    PaperLedger,
    PaperPosition,
    create_order_plan,
    run_order_manager_dry_run,
    write_paper_ledger,
)
from ai_fund_lab_v2.order_manager.phase7_artifact_loader import Phase7ArtifactLoadError, load_phase7_artifact_connection


PHASE8G_SOURCE_PATHS = (
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager",
    REPO_ROOT / "scripts" / "run_phase8g_order_manager_dry_run.py",
    REPO_ROOT / "scripts" / "generate_phase8g_review_queue.py",
    REPO_ROOT / "scripts" / "diff_phase8g_paper_ledger_history.py",
    REPO_ROOT / "scripts" / "audit_phase8g_end_to_end_no_live_order.py",
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
    source_files = list(_iter_source_files(PHASE8G_SOURCE_PATHS))
    forbidden_hits = _find_tokens(source_files, _forbidden_tokens())
    plan = create_order_plan(
        broker_snapshot_id="broker_snapshot_test",
        paper_ledger_id="paper_ledger_test",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN", quantity=Decimal("100")),),
    )
    approval = HumanReviewApprovalRecord(plan_id=plan.plan_id, reviewer="audit", decision="approved")
    dry_run_generated = _generate_minimal_end_to_end_report()
    checks = {
        "phase8g_source_files_present": bool(source_files),
        "forbidden_tokens_absent": not forbidden_hits,
        "orchestration_cli_no_external_connection_tokens": _orchestrator_has_no_external_tokens(),
        "smoke_without_explicit_flag_skipped": _smoke_without_explicit_flag_skipped(),
        "plan_safety_flags_fixed": plan.executable is False
        and plan.live_order_allowed is False
        and plan.requires_human_review is True,
        "approval_does_not_allow_live_order": approval.approval_does_not_allow_live_order is True,
        "paper_ledger_and_broker_paths_separate": '"order_manager" / "paper" / "ledgers"'
        in (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "paper_ledger.py").read_text(encoding="utf-8"),
        "phase7_artifact_missing_fail_closed": _phase7_missing_artifact_fails_closed(),
        "reconciliation_halt_status_defined": "REVIEW_ONLY_RECONCILIATION_HALT"
        in (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "schema.py").read_text(encoding="utf-8"),
        "locked_status_defined": "REVIEW_ONLY_LOCKED"
        in (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "schema.py").read_text(encoding="utf-8"),
        "end_to_end_report_generated": dry_run_generated,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "forbidden_hits": forbidden_hits,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in source_files],
    }


def _generate_minimal_end_to_end_report() -> bool:
    runtime_dir = REPO_ROOT / ".runtime" / "phase8g_audit_tmp"
    reports_dir = runtime_dir / "reports"
    write_moomoo_mock_snapshots(runtime_dir)
    ledger = PaperLedger(
        cash=Decimal("1000000"),
        buying_power=Decimal("1000000"),
        positions=(PaperPosition(issue_code="7203", quantity=Decimal("100")),),
    )
    ledger_path = write_paper_ledger(ledger, runtime_dir)
    try:
        result = run_order_manager_dry_run(
            runtime_dir=runtime_dir,
            reports_dir=reports_dir,
            repo_root=REPO_ROOT,
            paper_ledger_path=ledger_path,
        )
    except Exception:
        return False
    return Path(result.dry_run_report_json_path).exists() and Path(result.stored_plan_path).exists()


def _phase7_missing_artifact_fails_closed() -> bool:
    try:
        load_phase7_artifact_connection(REPO_ROOT / ".runtime" / "phase8g_missing_artifact")
    except Phase7ArtifactLoadError:
        return True
    return False


def _smoke_without_explicit_flag_skipped() -> bool:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "smoke_moomoo_readonly_phase8c.py"),
            "--runtime-dir",
            "/private/tmp/phase8g-audit-smoke-runtime",
            "--reports-dir",
            "/private/tmp/phase8g-audit-smoke-reports",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return payload.get("status") == "SKIPPED" and payload.get("executed") is False


def _orchestrator_has_no_external_tokens() -> bool:
    text = (REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager" / "dry_run_orchestrator.py").read_text(
        encoding="utf-8"
    )
    return not _find_tokens_in_text(text, _forbidden_tokens())


def _iter_source_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(child for child in path.rglob("*.py") if child.is_file())


def _find_tokens(files: list[Path], tokens: tuple[str, ...]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in files:
        found = _find_tokens_in_text(path.read_text(encoding="utf-8"), tokens)
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
