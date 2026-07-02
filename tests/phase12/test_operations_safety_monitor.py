from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_safety_monitor


def test_safety_monitor_market_stress_is_non_blocking_review(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_safety_monitor(trade_date="2026-06-29", root=tmp_path, market_stress=True)

    assert result["status"] == "PASS"
    assert result["safety_state"] == "NON_BLOCKING_REVIEW"
    assert result["non_blocking_review"] is True
    assert result["auto_sell"] is False
    assert result["line_send_executed"] is False


def test_safety_monitor_system_fault_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")

    result = run_safety_monitor(trade_date="2026-06-29", root=tmp_path, system_faults=["broker_divergence"])

    assert result["status"] == "BLOCK"
    assert result["safety_state"] == "SYSTEM_EMERGENCY_STOP"
    assert result["auto_sell"] is False
    assert result["line_send_executed"] is False
