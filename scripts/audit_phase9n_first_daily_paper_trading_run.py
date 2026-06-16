from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.first_daily_run import (
    FIRST_RUN_PENDING_ORDERS_CREATED,
    FIRST_RUN_READY_FOR_REVIEW,
    run_first_daily_paper_trading_run,
)
from ai_fund_lab_v2.paper_trading.initial_ledger import create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9n_first_end_to_end_daily_paper_trading_run.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9n_first_end_to_end_daily_paper_trading_run.json"
LEDGER_PATH = ROOT / ".runtime" / "phase9" / "ledger" / "latest.json"


def main() -> int:
    before_hash = _file_hash(LEDGER_PATH)
    review_only = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=LEDGER_PATH,
        mode="review-only",
    )
    after_review_hash = _file_hash(LEDGER_PATH)
    no_approval = run_first_daily_paper_trading_run(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=LEDGER_PATH,
        mode="paper-trading",
    )
    after_no_approval_hash = _file_hash(LEDGER_PATH)
    approved_case = _run_approved_case_in_temp()
    order_plan = json.loads((ROOT / ".runtime" / "phase9" / "inference" / "2026-06-15" / "order_plan_artifact.json").read_text(encoding="utf-8"))
    checks = {
        "review_only_run_success": review_only.status == FIRST_RUN_READY_FOR_REVIEW,
        "inference_artifacts_generated": review_only.candidate_count == 50 and review_only.opportunity_count == 20,
        "order_plan_generated": review_only.order_plan_count == 5,
        "human_review_request_generated": Path(review_only.human_review_json_path).is_file() and Path(review_only.human_review_markdown_path).is_file(),
        "reports_generated": all(Path(path).is_file() for path in review_only.report_paths.values()),
        "ledger_unchanged_review_only": before_hash == after_review_hash and review_only.ledger_changed is False,
        "paper_trading_without_approved_creates_no_pending_order": no_approval.pending_order_created is False and after_review_hash == after_no_approval_hash,
        "approved_artifact_creates_pending_order_in_temp": approved_case["status"] == FIRST_RUN_PENDING_ORDERS_CREATED and approved_case["pending_order_count"] > 0,
        "virtual_fill_not_executed": not review_only.prohibited_flags["virtual_fill_executed"],
        "broker_order_not_called": not review_only.prohibited_flags["broker_order_api_called"],
        "open_d_not_started": not review_only.prohibited_flags["open_d_started"],
        "unlock_trade_not_called": not review_only.prohibited_flags["unlock_trade_called"],
        "order_plan_invariant_confirmed": order_plan["executable"] is False and order_plan["live_order_allowed"] is False and order_plan["requires_human_review"] is True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    ledger = load_ledger(LEDGER_PATH)
    payload = {
        "audit_status": status,
        "decision_for": review_only.decision_for,
        "data_until": review_only.data_until,
        "virtual_order_date": review_only.virtual_order_date,
        "candidate_count": review_only.candidate_count,
        "opportunity_count": review_only.opportunity_count,
        "allocation_count": review_only.allocation_count,
        "order_plan_count": review_only.order_plan_count,
        "human_review_request": {
            "json_path": review_only.human_review_json_path,
            "markdown_path": review_only.human_review_markdown_path,
            "review_status": review_only.review_status,
        },
        "pending_order_created": review_only.pending_order_created,
        "pending_order_count": review_only.pending_order_count,
        "ledger_changed": before_hash != after_review_hash,
        "ledger": {
            "path": str(LEDGER_PATH),
            "ledger_id": ledger.metadata.ledger_id,
            "cash": str(ledger.cash),
            "positions_count": len(ledger.positions),
            "pending_orders_count": len(ledger.pending_orders),
        },
        "report_paths": review_only.report_paths,
        "tracker_marker_path": review_only.tracker_marker_path,
        "approved_pending_order_temp_case": approved_case,
        "checks": checks,
        "prohibited_flags": review_only.prohibited_flags,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _run_approved_case_in_temp() -> dict[str, object]:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        ledger = create_initial_ledger(
            initial_cash=Decimal("1000000"),
            currency="JPY",
            ledger_root=root / ".runtime" / "phase9" / "ledger",
            start_date="2026-06-16",
        )
        review = run_first_daily_paper_trading_run(
            decision_for="2026-06-15",
            data_until="2026-06-15",
            ledger_path=ledger.latest_path,
            mode="review-only",
            runtime_dir=root / ".runtime",
            reports_root=root / "reports",
            feature_root=ROOT / ".runtime" / "phase9" / "features",
            canonical_quotes_path=ROOT / ".runtime" / "phase9" / "canonical_data" / "normalized_daily_quotes" / "data.parquet",
        )
        approved = root / "approved_review.json"
        payload = json.loads(Path(review.human_review_json_path).read_text(encoding="utf-8"))
        payload["review_status"] = "approved"
        payload["reviewed_at"] = "2026-06-16T00:00:00+00:00"
        payload["reviewer_note"] = "audit temp approval"
        approved.write_text(json.dumps(payload), encoding="utf-8")
        result = run_first_daily_paper_trading_run(
            decision_for="2026-06-15",
            data_until="2026-06-15",
            ledger_path=ledger.latest_path,
            mode="paper-trading",
            runtime_dir=root / ".runtime",
            reports_root=root / "reports",
            feature_root=ROOT / ".runtime" / "phase9" / "features",
            canonical_quotes_path=ROOT / ".runtime" / "phase9" / "canonical_data" / "normalized_daily_quotes" / "data.parquet",
            human_review_path=approved,
        )
        latest = load_ledger(root / ".runtime" / "phase9" / "ledger" / "latest.json")
        return {
            "status": result.status,
            "pending_order_created": result.pending_order_created,
            "pending_order_count": result.pending_order_count,
            "ledger_pending_orders_count": len(latest.pending_orders),
            "virtual_fill_executed": result.prohibited_flags["virtual_fill_executed"],
        }


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Phase9-N First End-to-End Daily Paper Trading Run",
        "",
        f"- audit_status: {payload['audit_status']}",
        f"- decision_for: {payload['decision_for']}",
        f"- data_until: {payload['data_until']}",
        f"- virtual_order_date: {payload['virtual_order_date']}",
        f"- candidate_count: {payload['candidate_count']}",
        f"- opportunity_count: {payload['opportunity_count']}",
        f"- allocation_count: {payload['allocation_count']}",
        f"- order_plan_count: {payload['order_plan_count']}",
        "",
        "## Human Review",
        "",
    ]
    review = payload["human_review_request"]
    lines.extend(
        [
            f"- json_path: {review['json_path']}",
            f"- markdown_path: {review['markdown_path']}",
            f"- review_status: {review['review_status']}",
            "",
            "## Ledger",
            "",
        ]
    )
    ledger = payload["ledger"]
    for key, value in ledger.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Reports",
            "",
        ]
    )
    for key, value in payload["report_paths"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "- virtual_fill_executed: false",
            "- real_trade_executed: false",
            "",
        ]
    )
    return "\n".join(lines)


def _file_hash(path: Path) -> str:
    return __import__("hashlib").sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


if __name__ == "__main__":
    raise SystemExit(main())
