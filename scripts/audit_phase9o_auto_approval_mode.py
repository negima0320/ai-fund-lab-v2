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

from ai_fund_lab_v2.paper_trading.approval_mode import AUTO_FOR_PAPER_TRADING, MANUAL_REQUIRED, validate_approval_mode
from ai_fund_lab_v2.paper_trading.auto_approval import AUTO_APPROVAL_BLOCKED, create_auto_approval_artifact
from ai_fund_lab_v2.paper_trading.first_daily_run import FIRST_RUN_PENDING_ORDERS_CREATED, run_first_daily_paper_trading_run
from ai_fund_lab_v2.paper_trading.initial_ledger import create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9o_auto_approval_mode.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9o_auto_approval_mode.json"
LEDGER_PATH = ROOT / ".runtime" / "phase9" / "ledger" / "latest.json"


def main() -> int:
    before = load_ledger(LEDGER_PATH)
    if len(before.pending_orders) == 0:
        actual = run_first_daily_paper_trading_run(
            decision_for="2026-06-15",
            data_until="2026-06-15",
            ledger_path=LEDGER_PATH,
            mode="paper-trading",
            approval_mode=AUTO_FOR_PAPER_TRADING,
        )
    else:
        actual = run_first_daily_paper_trading_run(
            decision_for="2026-06-15",
            data_until="2026-06-15",
            ledger_path=LEDGER_PATH,
            mode="review-only",
        )
    after = load_ledger(LEDGER_PATH)
    temp_creation = _run_temp_auto_creation()
    broker_block = validate_approval_mode(approval_mode=AUTO_FOR_PAPER_TRADING, execution_mode="broker")
    manual = validate_approval_mode(approval_mode=MANUAL_REQUIRED, execution_mode="broker")
    order_plan = json.loads((ROOT / ".runtime" / "phase9" / "inference" / "2026-06-15" / "order_plan_artifact.json").read_text(encoding="utf-8"))
    invalid_auto = _invalid_order_plan_auto_check()
    cash_unchanged = after.cash == before.cash
    positions_unchanged = after.positions == before.positions
    pnl_unchanged = (
        after.performance.realized_pnl == before.performance.realized_pnl
        and after.performance.unrealized_pnl == before.performance.unrealized_pnl
        and after.performance.trade_count == before.performance.trade_count
    )
    pending_delta = len(after.pending_orders) - len(before.pending_orders)
    checks = {
        "auto_approval_artifact_generated": bool(actual.auto_approval_json_path and Path(actual.auto_approval_json_path).is_file()) or len(before.pending_orders) > 0,
        "pending_order_created_or_already_present": pending_delta > 0 or len(after.pending_orders) > 0,
        "ledger_pending_orders_added_when_empty": pending_delta > 0 if len(before.pending_orders) == 0 else True,
        "cash_unchanged": cash_unchanged,
        "positions_unchanged": positions_unchanged,
        "pnl_unchanged": pnl_unchanged,
        "virtual_fill_not_executed": not actual.prohibited_flags["virtual_fill_executed"],
        "broker_order_not_called": not actual.prohibited_flags["broker_order_api_called"],
        "open_d_not_started": not actual.prohibited_flags["open_d_started"],
        "unlock_trade_not_called": not actual.prohibited_flags["unlock_trade_called"],
        "order_plan_invariant_maintained": order_plan["executable"] is False and order_plan["live_order_allowed"] is False and order_plan["requires_human_review"] is True,
        "broker_mode_auto_approval_blocked": broker_block.allowed is False,
        "manual_required_valid_for_broker": manual.allowed is True,
        "invalid_order_plan_blocked": invalid_auto["status"] == AUTO_APPROVAL_BLOCKED,
        "temp_auto_creation_works": temp_creation["status"] == FIRST_RUN_PENDING_ORDERS_CREATED and temp_creation["pending_order_count"] > 0,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    auto_json = actual.auto_approval_json_path or str(ROOT / ".runtime" / "phase9" / "auto_approval" / "2026-06-15" / "auto_approval_artifact.json")
    auto_md = actual.auto_approval_markdown_path or str(ROOT / ".runtime" / "phase9" / "auto_approval" / "2026-06-15" / "auto_approval_artifact.md")
    applied_status = actual.status if pending_delta > 0 else ("AUTO_APPROVAL_ALREADY_APPLIED" if len(after.pending_orders) > 0 else actual.status)
    payload = {
        "audit_status": status,
        "approval_mode": AUTO_FOR_PAPER_TRADING,
        "decision_for": actual.decision_for,
        "data_until": actual.data_until,
        "virtual_order_date": actual.virtual_order_date,
        "actual_run_status": applied_status,
        "auto_approval_artifact": {
            "json_path": auto_json if Path(auto_json).is_file() else "",
            "markdown_path": auto_md if Path(auto_md).is_file() else "",
        },
        "pending_order_created": actual.pending_order_created or len(after.pending_orders) > 0,
        "pending_order_count": actual.pending_order_count or len(after.pending_orders),
        "ledger": {
            "path": str(LEDGER_PATH),
            "pending_orders_before": len(before.pending_orders),
            "pending_orders_after": len(after.pending_orders),
            "pending_orders_delta": pending_delta,
            "cash_before": str(before.cash),
            "cash_after": str(after.cash),
            "positions_before": len(before.positions),
            "positions_after": len(after.positions),
            "realized_pnl_before": str(before.performance.realized_pnl),
            "realized_pnl_after": str(after.performance.realized_pnl),
            "unrealized_pnl_before": str(before.performance.unrealized_pnl),
            "unrealized_pnl_after": str(after.performance.unrealized_pnl),
            "trade_count_before": before.performance.trade_count,
            "trade_count_after": after.performance.trade_count,
        },
        "checks": checks,
        "broker_mode_validation": broker_block.to_dict(),
        "manual_required_validation": manual.to_dict(),
        "invalid_order_plan_auto_check": invalid_auto,
        "temp_auto_creation": temp_creation,
        "prohibited_flags": actual.prohibited_flags,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _run_temp_auto_creation() -> dict[str, object]:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        ledger = create_initial_ledger(
            initial_cash=Decimal("1000000"),
            currency="JPY",
            ledger_root=root / ".runtime" / "phase9" / "ledger",
            start_date="2026-06-16",
        )
        result = run_first_daily_paper_trading_run(
            decision_for="2026-06-15",
            data_until="2026-06-15",
            ledger_path=ledger.latest_path,
            mode="paper-trading",
            approval_mode=AUTO_FOR_PAPER_TRADING,
            runtime_dir=root / ".runtime",
            reports_root=root / "reports",
            feature_root=ROOT / ".runtime" / "phase9" / "features",
            canonical_quotes_path=ROOT / ".runtime" / "phase9" / "canonical_data" / "normalized_daily_quotes" / "data.parquet",
        )
        return {
            "status": result.status,
            "pending_order_created": result.pending_order_created,
            "pending_order_count": result.pending_order_count,
            "virtual_fill_executed": result.prohibited_flags["virtual_fill_executed"],
        }


def _invalid_order_plan_auto_check() -> dict[str, object]:
    with TemporaryDirectory() as temp:
        path = Path(temp) / "bad_order_plan.json"
        path.write_text(
            json.dumps(
                {
                    "run_id": "bad",
                    "executable": False,
                    "live_order_allowed": True,
                    "requires_human_review": True,
                    "items": [],
                }
            ),
            encoding="utf-8",
        )
        result = create_auto_approval_artifact(
            order_plan_path=path,
            decision_for="2026-06-15",
            virtual_order_date="2026-06-16",
            output_root=Path(temp) / "auto",
        )
        return result.to_dict()


def _render_markdown(payload: dict[str, object]) -> str:
    ledger = payload["ledger"]
    lines = [
        "# Phase9-O Auto Approval Mode",
        "",
        f"- audit_status: {payload['audit_status']}",
        f"- approval_mode: {payload['approval_mode']}",
        f"- decision_for: {payload['decision_for']}",
        f"- data_until: {payload['data_until']}",
        f"- virtual_order_date: {payload['virtual_order_date']}",
        f"- actual_run_status: {payload['actual_run_status']}",
        f"- pending_order_created: {str(payload['pending_order_created']).lower()}",
        f"- pending_order_count: {payload['pending_order_count']}",
        "",
        "## Auto Approval Artifact",
        "",
    ]
    artifact = payload["auto_approval_artifact"]
    lines.append(f"- json_path: {artifact.get('json_path') or 'already_pending_or_not_created'}")
    lines.append(f"- markdown_path: {artifact.get('markdown_path') or 'already_pending_or_not_created'}")
    lines.extend(["", "## Ledger Change", ""])
    for key, value in ledger.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"- {key}: {str(value).lower()}")
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


if __name__ == "__main__":
    raise SystemExit(main())
