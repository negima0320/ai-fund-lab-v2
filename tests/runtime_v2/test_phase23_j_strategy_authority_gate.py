from __future__ import annotations

import json
from pathlib import Path

from scripts.runtime_test import (
    EXIT_PASS,
    _close_authority_classification,
    _strategy_acceptance_gate_status,
    _strategy_planning_authority_run_summary,
)


def test_phase23_j_strategy_authority_missing_blocks_acceptance_pass(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2026-07-01"])

    summary = _strategy_planning_authority_run_summary(run_dir)
    gate = _strategy_acceptance_gate_status(
        strategy_shadow={"strategy_shadow_judgment": "PASS"},
        strategy_authority=summary,
    )

    assert summary["status"] == "REVIEW_REQUIRED"
    assert summary["called_dates"] == []
    assert summary["missing_dates"] == ["2026-07-01"]
    assert summary["active_runtime_consumer_eligibility"] == "NO"
    assert summary["legacy_formal_planning_authority_active"] is True
    assert gate == "REVIEW_REQUIRED"


def test_phase23_j_strategy_authority_called_passes_gate_when_shadow_passes(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2026-07-01"])
    evidence = run_dir / "daily" / "2026-07-01" / "morning" / "strategy_planning_authority_evidence.json"
    _write_json(
        evidence,
        {
            "name": "phase23_i_strategy_planning_authority_pipeline",
            "status": "PASS",
            "details": {
                "status": "PASS",
                "planning_consumer_eligibility": "ELIGIBLE",
                "strategy_artifact_eligibility": "ELIGIBLE_FOR_PLANNING_AUTHORITY",
                "pending_item_count": 1,
                "broker_write_performed": False,
                "runtime_switch_performed": False,
                "legacy_formal_planning_authority_active": False,
            },
        },
    )

    summary = _strategy_planning_authority_run_summary(run_dir)
    gate = _strategy_acceptance_gate_status(
        strategy_shadow={"strategy_shadow_judgment": "PASS"},
        strategy_authority=summary,
    )

    assert summary["status"] == "PASS"
    assert summary["called_dates"] == ["2026-07-01"]
    assert summary["missing_dates"] == []
    assert summary["active_runtime_consumer_eligibility"] == "YES"
    assert summary["legacy_formal_planning_authority_active"] is False
    assert gate == "PASS"


def test_phase23_j_strategy_shadow_block_blocks_acceptance_even_if_runtime_completed(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2026-07-01"])
    evidence = run_dir / "daily" / "2026-07-01" / "morning" / "strategy_planning_authority_evidence.json"
    _write_json(
        evidence,
        {
            "status": "PASS",
            "details": {
                "status": "PASS",
                "planning_consumer_eligibility": "ELIGIBLE",
                "broker_write_performed": False,
                "runtime_switch_performed": False,
                "legacy_formal_planning_authority_active": False,
            },
        },
    )

    summary = _strategy_planning_authority_run_summary(run_dir)
    gate = _strategy_acceptance_gate_status(
        strategy_shadow={"strategy_shadow_judgment": "BLOCK"},
        strategy_authority=summary,
    )

    assert summary["status"] == "PASS"
    assert gate == "BLOCK"


def test_phase23_bu_non_mutating_strategy_shadow_review_does_not_block_operational_close(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2022-07-14"])
    evidence = run_dir / "daily" / "2022-07-14" / "morning" / "strategy_planning_authority_evidence.json"
    _write_json(
        evidence,
        {
            "status": "PASS",
            "details": {
                "status": "PASS",
                "planning_consumer_eligibility": "ELIGIBLE",
                "broker_write_performed": False,
                "runtime_switch_performed": False,
                "legacy_formal_planning_authority_active": False,
            },
        },
    )

    strategy_authority = _strategy_planning_authority_run_summary(run_dir)
    strategy_shadow = {
        "strategy_shadow_judgment": "REVIEW_REQUIRED",
        "review_required_dates": ["2022-07-14"],
        "blocked_dates": [],
        "missing_dates": [],
        "broker_write_performed": False,
        "runtime_switch_performed": False,
        "runtime_mutation_performed": False,
        "shadow_consumer_eligibility": "REVIEW_REQUIRED",
        "active_runtime_consumer_eligibility": "NO",
        "strategy_planning_authority_consumer_called": False,
        "daily_summaries": [
            {
                "business_date": "2022-07-14",
                "strategy_shadow_judgment": "REVIEW_REQUIRED",
                "active_runtime_consumer_eligibility": "NO",
                "strategy_planning_authority_consumer_called": False,
                "reason_codes": ["existing_pending_conflict:23880"],
            }
        ],
    }

    gate = _strategy_acceptance_gate_status(
        strategy_shadow=strategy_shadow,
        strategy_authority=strategy_authority,
    )
    close_authority = _close_authority_classification(
        validation_exit_code=EXIT_PASS,
        run_state_status="COMPLETED",
        pm_fatal={},
        strategy_shadow=strategy_shadow,
        strategy_authority=strategy_authority,
        historical_authority_validation={"status": "PASS"},
    )

    assert gate == "PASS"
    assert close_authority["trading_state_judgment"] == "PASS"
    assert close_authority["accounting_state_judgment"] == "PASS"
    assert close_authority["runtime_execution_judgment"] == "PASS"
    assert close_authority["production_planning_judgment"] == "PASS"
    assert close_authority["strategy_shadow_judgment"] == "REVIEW_REQUIRED"
    assert close_authority["strategy_shadow_review_required"] is True
    assert close_authority["strategy_shadow_close_classification"] == "NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING"
    assert close_authority["final_runtime_judgment"] == "PASS"
    assert close_authority["operational_status"] == "PASS"
    assert close_authority["strategy_review_status"] == "REVIEW_REQUIRED"


def test_phase23_bu_strategy_shadow_review_marked_production_consumer_remains_blocking(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2022-07-14"])
    evidence = run_dir / "daily" / "2022-07-14" / "morning" / "strategy_planning_authority_evidence.json"
    _write_json(
        evidence,
        {
            "status": "PASS",
            "details": {
                "status": "PASS",
                "planning_consumer_eligibility": "ELIGIBLE",
                "broker_write_performed": False,
                "runtime_switch_performed": False,
                "legacy_formal_planning_authority_active": False,
            },
        },
    )

    close_authority = _close_authority_classification(
        validation_exit_code=EXIT_PASS,
        run_state_status="COMPLETED",
        pm_fatal={},
        strategy_shadow={
            "strategy_shadow_judgment": "REVIEW_REQUIRED",
            "active_runtime_consumer_eligibility": "YES",
            "strategy_planning_authority_consumer_called": True,
            "broker_write_performed": False,
            "runtime_switch_performed": False,
            "runtime_mutation_performed": False,
        },
        strategy_authority=_strategy_planning_authority_run_summary(run_dir),
        historical_authority_validation={"status": "PASS"},
    )

    assert close_authority["strategy_shadow_close_classification"] == "BLOCKING_STRATEGY_SHADOW_PRODUCTION_CONSUMER_CONFLICT"
    assert close_authority["final_runtime_judgment"] == "BLOCK"


def test_phase23_bu_production_planning_review_still_blocks_operational_pass(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2022-07-14"])
    close_authority = _close_authority_classification(
        validation_exit_code=EXIT_PASS,
        run_state_status="COMPLETED",
        pm_fatal={},
        strategy_shadow={"strategy_shadow_judgment": "PASS"},
        strategy_authority=_strategy_planning_authority_run_summary(run_dir),
        historical_authority_validation={"status": "PASS"},
    )

    assert close_authority["production_planning_judgment"] == "REVIEW_REQUIRED"
    assert close_authority["final_runtime_judgment"] == "REVIEW_REQUIRED"


def test_phase23_bu_trading_validation_failure_still_blocks_operational_pass(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, ["2022-07-14"])
    evidence = run_dir / "daily" / "2022-07-14" / "morning" / "strategy_planning_authority_evidence.json"
    _write_json(
        evidence,
        {
            "status": "PASS",
            "details": {
                "status": "PASS",
                "planning_consumer_eligibility": "ELIGIBLE",
                "broker_write_performed": False,
                "runtime_switch_performed": False,
                "legacy_formal_planning_authority_active": False,
            },
        },
    )

    close_authority = _close_authority_classification(
        validation_exit_code=10,
        run_state_status="COMPLETED",
        pm_fatal={},
        strategy_shadow={"strategy_shadow_judgment": "REVIEW_REQUIRED", "review_required_dates": ["2022-07-14"]},
        strategy_authority=_strategy_planning_authority_run_summary(run_dir),
        historical_authority_validation={"status": "PASS"},
    )

    assert close_authority["trading_state_judgment"] == "REVIEW_REQUIRED"
    assert close_authority["final_runtime_judgment"] == "REVIEW_REQUIRED"


def _run_dir(tmp_path: Path, dates: list[str]) -> Path:
    run_dir = tmp_path / "run"
    _write_json(
        run_dir / "plan.json",
        {"business_dates": [{"business_date": date} for date in dates]},
    )
    return run_dir


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
