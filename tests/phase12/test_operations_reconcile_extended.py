from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_reconcile, run_safety_monitor


def test_reconcile_classifies_system_emergency_stop_from_safety_monitor(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    run_safety_monitor(trade_date="2026-06-29", root=tmp_path, system_faults=["position_mismatch"])

    result = run_reconcile(trade_date="2026-06-29", root=tmp_path)

    assert result["status"] == "SYSTEM_EMERGENCY_STOP"
    assert "safety_monitor" in result["targets"]
    assert "broker_orders" in result["targets"]
    assert "executions" in result["targets"]
    assert "positions" in result["targets"]
    assert "ledger" in result["targets"]
