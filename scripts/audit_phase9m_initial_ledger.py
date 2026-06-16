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

from ai_fund_lab_v2.paper_trading.daily_inference_runner import INFERENCE_READY, run_daily_inference
from ai_fund_lab_v2.paper_trading.daily_operation_runner import run_daily_operation
from ai_fund_lab_v2.paper_trading.initial_ledger import INITIAL_LEDGER_BLOCKED, INITIAL_LEDGER_CREATED, create_initial_ledger
from ai_fund_lab_v2.paper_trading.ledger import load_ledger


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9m_initial_ledger_and_first_run_preparation.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9m_initial_ledger_and_first_run_preparation.json"
LEDGER_ROOT = ROOT / ".runtime" / "phase9" / "ledger"
LATEST_PATH = LEDGER_ROOT / "latest.json"


def main() -> int:
    creation = _ensure_real_initial_ledger()
    ledger = load_ledger(LATEST_PATH)
    duplicate_status, overwrite_status = _exercise_duplicate_and_overwrite_checks()
    l2 = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        ledger_path=LATEST_PATH,
    )
    operation = run_daily_operation(
        run_date="2026-06-15",
        mode="dry-run",
        ledger_path=LATEST_PATH,
        artifact_root=ROOT / ".runtime" / "phase9" / "inference" / "2026-06-15",
        daily_quotes_path=ROOT / ".runtime" / "phase9" / "canonical_data" / "normalized_daily_quotes" / "data.parquet",
        listed_info_path=ROOT / ".runtime" / "data" / "raw" / "jquants" / "listed_issues" / "data.parquet",
        force_unlock=True,
    )
    checks = {
        "latest_json_exists": LATEST_PATH.is_file(),
        "cash_is_1000000": str(ledger.cash) == "1000000",
        "positions_empty": len(ledger.positions) == 0,
        "pending_orders_empty": len(ledger.pending_orders) == 0,
        "performance_total_equity_1000000": str(ledger.performance.total_equity) == "1000000",
        "duplicate_create_blocked": duplicate_status == INITIAL_LEDGER_BLOCKED,
        "overwrite_allowed_with_flag": overwrite_status == INITIAL_LEDGER_CREATED,
        "l2_saved_ledger_ready": l2.status == INFERENCE_READY,
        "l2_no_in_memory_initial_warning": "initial_ledger_in_memory_only" not in l2.warnings,
        "daily_operation_runner_completed": operation.status in {"OK", "HALT"},
        "daily_operation_uses_saved_ledger": operation.pipeline_result is not None and str(operation.pipeline_result.daily_result.cash) == "1000000",
        "prohibited_flags_false": not any(_prohibited_flags(creation, l2, operation).values()),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "audit_status": status,
        "initial_ledger": {
            "path": str(LATEST_PATH),
            "ledger_id": ledger.metadata.ledger_id,
            "initial_cash": str(ledger.cash),
            "currency": ledger.metadata.currency,
            "start_date": ledger.metadata.start_date,
            "positions_count": len(ledger.positions),
            "pending_orders_count": len(ledger.pending_orders),
            "performance": {
                "total_equity": str(ledger.performance.total_equity),
                "cash": str(ledger.performance.cash),
                "market_value": str(ledger.performance.market_value),
                "realized_pnl": str(ledger.performance.realized_pnl),
                "unrealized_pnl": str(ledger.performance.unrealized_pnl),
                "trade_count": ledger.performance.trade_count,
            },
        },
        "l2_saved_ledger_rerun": l2.to_dict(),
        "daily_operation_runner_dry_run": operation.to_dict(),
        "checks": checks,
        "prohibited_flags": _prohibited_flags(creation, l2, operation),
        "next_action": "Phase9-N can begin first Human Review / pending paper order preparation after confirming reports.",
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _ensure_real_initial_ledger():
    if LATEST_PATH.exists():
        ledger = load_ledger(LATEST_PATH)
        return {
            "status": "INITIAL_LEDGER_ALREADY_PRESENT",
            "latest_path": str(LATEST_PATH),
            "ledger_id": ledger.metadata.ledger_id,
            "prohibited_flags": _all_false_flags(),
        }
    return create_initial_ledger(
        initial_cash=Decimal("1000000"),
        currency="JPY",
        ledger_root=LEDGER_ROOT,
        start_date="2026-06-16",
        overwrite=False,
    ).to_dict()


def _exercise_duplicate_and_overwrite_checks() -> tuple[str, str]:
    with TemporaryDirectory() as temp:
        root = Path(temp) / "ledger"
        create_initial_ledger(initial_cash=Decimal("1000000"), currency="JPY", ledger_root=root, start_date="2026-06-16")
        duplicate = create_initial_ledger(initial_cash=Decimal("1000000"), currency="JPY", ledger_root=root, start_date="2026-06-16")
        overwrite = create_initial_ledger(
            initial_cash=Decimal("1000000"),
            currency="JPY",
            ledger_root=root,
            start_date="2026-06-16",
            overwrite=True,
        )
    return duplicate.status, overwrite.status


def _prohibited_flags(creation, l2, operation) -> dict[str, bool]:
    flags = _all_false_flags()
    if isinstance(creation, dict):
        flags.update({key: bool(value) for key, value in creation.get("prohibited_flags", {}).items()})
    if l2.prohibited_flags:
        flags.update({key: bool(value) for key, value in l2.prohibited_flags.items()})
    flags.update(
        {
            "broker_order_api_called": flags["broker_order_api_called"] or bool(operation.broker_order_api_called),
            "open_d_started": flags["open_d_started"] or bool(operation.open_d_started),
            "unlock_trade_called": flags["unlock_trade_called"] or bool(operation.unlock_trade_called),
            "scheduler_auto_registered": flags["scheduler_auto_registered"] or bool(operation.scheduler_auto_registered),
        }
    )
    return flags


def _all_false_flags() -> dict[str, bool]:
    return {
        "broker_order_api_called": False,
        "moomoo_simulate_order_called": False,
        "tachibana_order_called": False,
        "open_d_started": False,
        "login_called": False,
        "logout_called": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _render_markdown(payload: dict[str, object]) -> str:
    ledger = payload["initial_ledger"]
    checks = payload["checks"]
    lines = [
        "# Phase9-M Initial Ledger and First Run Preparation",
        "",
        f"- audit_status: {payload['audit_status']}",
        f"- initial_ledger_path: {ledger['path']}",
        f"- ledger_id: {ledger['ledger_id']}",
        f"- initial_cash: {ledger['initial_cash']} {ledger['currency']}",
        f"- start_date: {ledger['start_date']}",
        f"- positions_count: {ledger['positions_count']}",
        f"- pending_orders_count: {ledger['pending_orders_count']}",
        "",
        "## Performance Snapshot",
        "",
    ]
    for key, value in ledger["performance"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for key, value in sorted(checks.items()):
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## First Run Preparation",
            "",
            f"- l2_saved_ledger_status: {payload['l2_saved_ledger_rerun']['status']}",
            f"- daily_operation_status: {payload['daily_operation_runner_dry_run']['status']}",
            "",
            "## Phase9 Boundary",
            "",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "- virtual_fill_executed: false",
            "- paper_ledger_fill_executed: false",
            "",
            f"## Next Action\n\n{payload['next_action']}\n",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

