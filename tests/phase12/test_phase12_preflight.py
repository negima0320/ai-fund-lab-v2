from __future__ import annotations

from ai_fund_lab_v2.operations.operations import run_preflight


def test_preflight_rejects_invalid_runtime_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "invalid")
    result = run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])

    assert result["status"] == "BLOCK"
    assert "TACHIBANA_API_ENV_invalid" in result["reasons"]


def test_preflight_writes_redacted_artifact_without_required_env_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    result = run_preflight(trade_date="2026-06-29", root=tmp_path, required_env=[])

    assert result["status"] == "PASS"
    artifact = tmp_path / "preflight" / "2026-06-29" / "preflight_result.json"
    assert artifact.exists()
    assert result["required_env"]["values_printed"] is False
