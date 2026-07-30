from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _parse_args, _validate_rehearsal_args, main


def test_phase23_q_scheduler_argument_contract_accepts_production_demo_and_historical(tmp_path: Path) -> None:
    demo = _parse_args(["--mode", "demo", "--job", "market_refresh", "--business-date", "2026-07-06"])
    production = _parse_args(["--mode", "production", "--job", "market_refresh", "--business-date", "2026-07-06"])
    historical = _parse_args(
        [
            "--mode",
            "historical",
            "--job",
            "market_refresh",
            "--business-date",
            "2026-07-06",
            "--evaluation-time",
            "2026-07-06T08:00:00+09:00",
            "--broker-environment",
            "historical_simulated",
        ]
    )

    _validate_rehearsal_args(demo)
    _validate_rehearsal_args(production)
    _validate_rehearsal_args(historical)


def test_phase23_q_historical_scheduler_rejects_external_fetch() -> None:
    args = _parse_args(
        [
            "--mode",
            "historical",
            "--job",
            "market_refresh",
            "--business-date",
            "2026-07-06",
            "--evaluation-time",
            "2026-07-06T08:00:00+09:00",
            "--broker-environment",
            "historical_simulated",
            "--market-refresh-allow-api-fetch",
            "true",
        ]
    )

    with pytest.raises(ValueError, match="market-refresh-allow-api-fetch false"):
        _validate_rehearsal_args(args)


def test_phase23_q_historical_market_refresh_reaches_common_pipeline_without_demo_only_block(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir(parents=True)
    business_date = "2026-07-06"

    exit_code = main(
        [
            "--mode",
            "historical",
            "--job",
            "market_refresh",
            "--business-date",
            business_date,
            "--evaluation-time",
            f"{business_date}T08:00:00+09:00",
            "--broker-environment",
            "historical_simulated",
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--feature-root",
            str(runtime_root / "operations" / "feature_artifacts"),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--runtime-test-run-id",
            "phase23q-short-validation",
            "--runtime-test-profile-id",
            "historical-smoke",
            "--runtime-test-evidence-root",
            str(tmp_path / "reports" / "runtime_tests" / "runs" / "phase23q-short-validation"),
        ]
    )

    manifest_path = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))[-1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    market_stage = next(stage for stage in manifest["stages"] if stage["name"] == "runtime_v2_market_refresh_pipeline")
    details = market_stage["details"]

    assert exit_code == 10
    assert manifest["exit_code"] == 10
    assert manifest["final_state"] == "BLOCKED"
    assert "Runtime v2 daily scheduler rehearsal allows --mode demo only" not in json.dumps(manifest)
    assert details["allow_api_fetch"] is False
    assert details["jquants_api_fetch_executed"] is False
    assert details["historical_asof_status"] == "HALT"
    assert details["historical_asof_reason"] == "historical_asof_authority_invalid"
    assert "historical_asof_authority_invalid" in details["blocked_reasons"]
    assert manifest["broker_write"] is False
    assert manifest["external_delivery"] is False


def test_phase23_q_unsupported_simulation_mode_still_rejected() -> None:
    args = _parse_args(["--mode", "simulation", "--job", "market_refresh"])

    with pytest.raises(ValueError, match="use --mode historical"):
        _validate_rehearsal_args(args)
