#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_fund_lab_v2.paper_trading.ledger import LedgerMetadata, PaperTradingLedger, ledger_summary_metadata, load_ledger


DOC_PATH = Path("docs/phase_reports/phase9z4_manifest_status_ledger_summary.md")
JSON_PATH = Path("reports/phase_reports/phase9z4_manifest_status_ledger_summary.json")
LEDGER_PATH = Path(".runtime/phase9/ledger/latest.json")
MANIFEST_PATH = Path(".runtime/daily_operation/runs/2026-06-22/unified_daily_run_manifest.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    before_ledger_raw = _read_json(LEDGER_PATH)
    before_manifest_raw = _read_json(MANIFEST_PATH)
    backup_path = _backup_ledger()
    ledger_repair = _repair_latest_ledger_summary()
    manifest_repair = _repair_manifest_status()
    after_ledger_raw = _read_json(LEDGER_PATH)
    after_manifest_raw = _read_json(MANIFEST_PATH)

    command_results = {
        "pytest_paper_trading": _run_command(["python3", "-m", "pytest", "-q", "tests/paper_trading"]),
        "phase9v": _run_command(["python3", "scripts/audit_phase9v_score_saturation_fix.py"]),
        "phase9w": _run_command(["python3", "scripts/audit_phase9w_unified_runner_market_refresh_and_date_resolution.py"]),
        "phase9y": _run_command(["python3", "scripts/audit_phase9y_virtual_fill_execution_date.py"]),
        "phase9z": _run_command(["python3", "scripts/audit_phase9z_weekend_run_guard_pending_dedup.py"]),
        "phase9z3": _run_command(["python3", "scripts/audit_phase9z3_trading_calendar_refresh_before_business_day_guard.py"]),
    }

    summary = after_ledger_raw.get("summary") or {}
    positions_count = len(after_ledger_raw.get("positions", []))
    pending_orders_count = len(after_ledger_raw.get("pending_orders", []))
    position_unrealized = sum(Decimal(str(item.get("unrealized_pnl") or "0")) for item in after_ledger_raw.get("positions", []) if isinstance(item, dict))
    market_value = sum(Decimal(str(item.get("market_value") or "0")) for item in after_ledger_raw.get("positions", []) if isinstance(item, dict))
    cash = Decimal(str(after_ledger_raw.get("cash") or "0"))
    checks = [
        Check("manifest_status_present", after_manifest_raw.get("status") == "UNIFIED_DAILY_RUNNER_COMPLETED", str(after_manifest_raw.get("status"))),
        Check("ledger_summary_present", isinstance(summary, dict) and bool(summary), json.dumps(summary, ensure_ascii=True)),
        Check("top_level_trade_count_present", isinstance(after_ledger_raw.get("trade_count"), int) and after_ledger_raw.get("trade_count") >= 0, str(after_ledger_raw.get("trade_count"))),
        Check("top_level_realized_pnl_present", after_ledger_raw.get("realized_pnl") is not None, str(after_ledger_raw.get("realized_pnl"))),
        Check("top_level_unrealized_pnl_matches_positions", Decimal(str(after_ledger_raw.get("unrealized_pnl") or "0")) == position_unrealized, f"{after_ledger_raw.get('unrealized_pnl')} vs {position_unrealized}"),
        Check("top_level_market_value_matches_positions", Decimal(str(after_ledger_raw.get("market_value") or "0")) == market_value, f"{after_ledger_raw.get('market_value')} vs {market_value}"),
        Check("top_level_total_equity_matches_cash_market_value", Decimal(str(after_ledger_raw.get("total_equity") or "0")) == cash + market_value, f"{after_ledger_raw.get('total_equity')} vs {cash + market_value}"),
        Check("positions_count_matches_positions", after_ledger_raw.get("positions_count") == positions_count, str(after_ledger_raw.get("positions_count"))),
        Check("pending_orders_count_matches_pending_orders", after_ledger_raw.get("pending_orders_count") == pending_orders_count, str(after_ledger_raw.get("pending_orders_count"))),
        Check("last_execution_date_present", str(after_ledger_raw.get("last_execution_date") or "") >= "2026-06-22", str(after_ledger_raw.get("last_execution_date"))),
        Check("last_valuation_date_present", str(after_ledger_raw.get("last_valuation_date") or "") >= "2026-06-22", str(after_ledger_raw.get("last_valuation_date"))),
        Check("cash_unchanged", before_ledger_raw.get("cash") == after_ledger_raw.get("cash"), f"{before_ledger_raw.get('cash')} -> {after_ledger_raw.get('cash')}"),
        Check("positions_unchanged", before_ledger_raw.get("positions") == after_ledger_raw.get("positions"), ""),
        Check("pending_orders_unchanged", before_ledger_raw.get("pending_orders") == after_ledger_raw.get("pending_orders"), ""),
        *[
            Check(name, result["returncode"] == 0, result["summary"])
            for name, result in command_results.items()
        ],
    ]
    payload = {
        "phase": "Phase9-Z4",
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "root_cause": {
            "manifest": "Unified runner wrote step statuses but did not include top-level status in unified_daily_run_manifest.json.",
            "ledger": "Ledger performance metrics existed under performance, but compatibility top-level summary fields and last execution/valuation metadata were not serialized.",
        },
        "backup_path": str(backup_path),
        "manifest_status": {"before": before_manifest_raw.get("status"), "after": after_manifest_raw.get("status"), **manifest_repair},
        "ledger_summary": {"before": _summary_view(before_ledger_raw), "after": _summary_view(after_ledger_raw), **ledger_repair},
        "checks": [asdict(check) for check in checks],
        "command_results": command_results,
        "forbidden_actions": {
            "broker_order": False,
            "open_d": False,
            "unlock_trade": False,
            "real_trade": False,
            "ai_retraining": False,
            "full_backtest": False,
            "scheduler_change": False,
            "launchd_plist_change": False,
            "positions_changed": before_ledger_raw.get("positions") != after_ledger_raw.get("positions"),
            "cash_changed": before_ledger_raw.get("cash") != after_ledger_raw.get("cash"),
            "pending_orders_changed": before_ledger_raw.get("pending_orders") != after_ledger_raw.get("pending_orders"),
            "virtual_fill_rerun": False,
        },
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "markdown": str(DOC_PATH), "json": str(JSON_PATH), "backup_path": str(backup_path)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


def _backup_ledger() -> Path:
    if not LEDGER_PATH.is_file():
        raise FileNotFoundError(str(LEDGER_PATH))
    stamp = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d_%H%M%S")
    backup = LEDGER_PATH.parent / "backups" / f"phase9z4_before_summary_metadata_fix_{stamp}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LEDGER_PATH, backup)
    return backup


def _repair_latest_ledger_summary() -> dict[str, Any]:
    ledger = load_ledger(LEDGER_PATH)
    last_execution_date = ledger.metadata.last_execution_date or _infer_last_execution_date()
    position_dates = [position.last_valuation_date for position in ledger.positions if position.last_valuation_date]
    last_valuation_date = ledger.metadata.last_valuation_date or (max(position_dates) if position_dates else "")
    metadata = replace(
        ledger.metadata,
        last_execution_date=last_execution_date,
        last_valuation_date=last_valuation_date,
        virtual_fill_executed=ledger.metadata.virtual_fill_executed or bool(last_execution_date),
    )
    repaired = PaperTradingLedger(
        cash=ledger.cash,
        positions=ledger.positions,
        pending_orders=ledger.pending_orders,
        performance=ledger.performance,
        metadata=metadata,
    )
    payload = repaired.to_dict()
    LEDGER_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"last_execution_date_inferred": last_execution_date, "last_valuation_date_inferred": last_valuation_date, "summary": ledger_summary_metadata(repaired)}


def _repair_manifest_status() -> dict[str, Any]:
    payload = _read_json(MANIFEST_PATH)
    before = payload.get("status")
    if not before:
        payload["status"] = "UNIFIED_DAILY_RUNNER_BLOCKED" if payload.get("blocked_reasons") else "UNIFIED_DAILY_RUNNER_COMPLETED"
        MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"patched": not bool(before)}


def _infer_last_execution_date() -> str:
    executions = Path(".runtime/phase9/ledger/executions")
    dates: list[str] = []
    for path in executions.glob("*_executions.json"):
        try:
            payload = _read_json(path)
        except Exception:
            continue
        for record in payload.get("records", []):
            if isinstance(record, dict) and str(record.get("status") or "").upper() == "FILLED":
                fill_date = str(record.get("fill_date") or payload.get("execution_date") or "")
                if fill_date:
                    dates.append(fill_date)
    return max(dates) if dates else ""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_view(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "trade_count",
        "realized_pnl",
        "unrealized_pnl",
        "total_equity",
        "cash",
        "market_value",
        "positions_count",
        "pending_orders_count",
        "last_execution_date",
        "last_valuation_date",
    )
    return {key: payload.get(key) for key in keys}


def _run_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    return {"command": command, "returncode": result.returncode, "summary": lines[-1] if lines else ""}


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-Z4 Manifest Status / Ledger Summary Metadata",
        "",
        f"- status: {payload['status']}",
        f"- backup_path: {payload['backup_path']}",
        "",
        "## Manifest",
        "",
        f"- before: {payload['manifest_status']['before']}",
        f"- after: {payload['manifest_status']['after']}",
        "",
        "## Ledger Summary",
        "",
        f"- before: `{json.dumps(payload['ledger_summary']['before'], ensure_ascii=False)}`",
        f"- after: `{json.dumps(payload['ledger_summary']['after'], ensure_ascii=False)}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {check['name']}: {'PASS' if check['passed'] else 'FAIL'} {check['detail']}" for check in payload["checks"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
