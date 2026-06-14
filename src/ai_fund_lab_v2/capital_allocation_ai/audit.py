from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.capital_allocation_ai.schema import REQUIRED_AUDIT_FLAGS

PHASE = "Phase7-A-Audit"
COMPLETION_STATUS = "PHASE7A_CAPITAL_ALLOCATION_ENGINE_READY"
BLOCKED_STATUS = "PHASE7A_CAPITAL_ALLOCATION_ENGINE_BLOCKED"


def run_phase7a_capital_allocation_audit(
    *,
    summary_path: Path,
    audit_path: Path,
    output_path: Path,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    summary = read_json(summary_path)
    runtime_audit = read_json(audit_path)
    checks = {
        "summary_exists": summary_path.is_file(),
        "runtime_audit_exists": audit_path.is_file(),
        "decision_output_exists": output_path.is_file(),
        "broker_api_not_executed": runtime_audit.get("broker_api_executed") is False,
        "paper_trading_not_executed": runtime_audit.get("paper_trading_executed") is False,
        "order_not_executed": runtime_audit.get("order_executed") is False,
        "live_order_not_executed": runtime_audit.get("live_order_executed") is False,
        "tachibana_api_not_called": runtime_audit.get("tachibana_api_called") is False,
        "fixed_take_profit_disabled": runtime_audit.get("fixed_take_profit_enabled") is False,
        "phase6_single_exit_auto_sell_disabled": runtime_audit.get("phase6_single_exit_auto_sell_enabled") is False,
        "emergency_exit_enabled": runtime_audit.get("emergency_exit_enabled") is True,
        "replacement_requires_minimum_holding_days": runtime_audit.get("replacement_requires_minimum_holding_days") is True,
        "replacement_requires_edge_margin": runtime_audit.get("replacement_requires_edge_margin") is True,
        "replacement_requires_confirmation_days": runtime_audit.get("replacement_requires_confirmation_days") is True,
        "replacement_same_time_live_execution_disabled": runtime_audit.get("replacement_same_time_live_execution_enabled") is False,
        "replacement_requires_sell_fill_before_buy": runtime_audit.get("replacement_requires_sell_fill_before_buy") is True,
        "cash_buffer_applied": runtime_audit.get("cash_buffer_applied") is True,
        "max_position_weight_applied": runtime_audit.get("max_position_weight_applied") is True,
        "simple_top3_drop_replacement_disabled": runtime_audit.get("simple_top3_drop_replacement_enabled") is False,
        "kelly_disabled": runtime_audit.get("kelly_criterion_enabled") is False,
        "leverage_disabled": runtime_audit.get("leverage_enabled") is False,
        "margin_trading_disabled": runtime_audit.get("margin_trading_enabled") is False,
        "loss_averaging_disabled": runtime_audit.get("loss_averaging_enabled") is False,
    }
    missing_flags = [flag for flag in REQUIRED_AUDIT_FLAGS if flag not in runtime_audit]
    checks["required_audit_flags_present"] = not missing_flags
    completion_ok = all(checks.values())
    payload = {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": COMPLETION_STATUS if completion_ok else BLOCKED_STATUS,
        "ready_for_phase7b": bool(completion_ok),
        "checks": checks,
        "missing_required_audit_flags": missing_flags,
        "summary_path": str(summary_path),
        "runtime_audit_path": str(audit_path),
        "decision_output_path": str(output_path),
        "summary_readiness_status": summary.get("readiness_status"),
        "runtime_readiness_status": runtime_audit.get("readiness_status"),
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
    }
    write_json(output_path.parent / "phase7a_completion_audit.json", payload)
    return payload


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
