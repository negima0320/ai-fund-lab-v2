from __future__ import annotations

from decimal import Decimal
from typing import Any


def calculate_phase9_kpis(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(entries)
    if not entries:
        return {
            "progress": "0/30",
            "pipeline_success_rate": "0.00",
            "data_readiness_rate": "0.00",
            "report_generation_rate": "0.00",
            "ledger_integrity": "UNKNOWN",
            "no_broker_order_violation": "UNKNOWN",
            "paper_total_equity": "0",
            "cumulative_return": "0",
            "trade_count": 0,
            "pending_order_count": 0,
            "position_count": 0,
        }
    success = sum(1 for entry in entries if str(entry.get("status", "")).upper() not in {"FAILED", "NOT_READY"})
    data_ready = sum(1 for entry in entries if bool(entry.get("data_ready", True)))
    reports = sum(1 for entry in entries if bool(entry.get("report_generated", True)))
    latest = entries[-1]
    initial_equity = _decimal(entries[0].get("paper_total_equity"))
    latest_equity = _decimal(latest.get("paper_total_equity"))
    cumulative = Decimal("0") if initial_equity <= 0 else (latest_equity - initial_equity) / initial_equity
    return {
        "progress": f"{total}/30",
        "pipeline_success_rate": _rate(success, total),
        "data_readiness_rate": _rate(data_ready, total),
        "report_generation_rate": _rate(reports, total),
        "ledger_integrity": "OK" if all(entry.get("ledger_integrity", "OK") == "OK" for entry in entries) else "CHECK_REQUIRED",
        "no_broker_order_violation": "OK" if all(not bool(entry.get("broker_order_api_called", False)) for entry in entries) else "VIOLATION",
        "paper_total_equity": str(latest_equity),
        "cumulative_return": str(cumulative),
        "trade_count": int(latest.get("trade_count") or 0),
        "pending_order_count": int(latest.get("pending_order_count") or 0),
        "position_count": int(latest.get("positions") or latest.get("position_count") or 0),
    }


def _rate(count: int, total: int) -> str:
    if total <= 0:
        return "0.00"
    return f"{count / total:.4f}"


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))

