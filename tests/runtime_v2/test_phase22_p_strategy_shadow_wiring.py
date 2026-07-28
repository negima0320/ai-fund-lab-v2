from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.shadow_runtime import (
    generate_strategy_shadow_for_day,
    strategy_shadow_job_descriptor,
    validate_run_strategy_shadow,
)


def test_phase22_p_strategy_shadow_descriptor_is_shadow_only(tmp_path: Path) -> None:
    descriptor = strategy_shadow_job_descriptor(run_dir=tmp_path / "run", business_date="2026-07-06")

    assert descriptor["job"] == "strategy_shadow_generation"
    assert descriptor["execution_order"] == "after_daily_runtime_jobs"
    assert descriptor["active_runtime_consumer_eligibility"] == "NO"
    assert descriptor["runtime_switch_performed"] is False
    assert "read_only" in descriptor["mutation_policy"]


def test_phase22_p_strategy_shadow_generation_preserves_runtime_authority(tmp_path: Path) -> None:
    runtime_root = Path(".runtime")
    run_dir = tmp_path / "runs" / "phase22p-unit"
    run_dir.mkdir(parents=True)
    (run_dir / "plan.json").write_text(
        json.dumps(
            {
                "schema_version": "runtime_test_plan_v1",
                "run_id": "phase22p-unit",
                "profile_id": "historical-smoke",
                "runtime_root": str(runtime_root),
                "business_dates": [{"business_date": "2022-09-15", "feature_date": "2022-09-15", "jobs": []}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = generate_strategy_shadow_for_day(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id="phase22p-unit",
        profile_id="historical-smoke",
        business_date="2022-09-15",
        feature_date="2022-09-15",
    )

    assert summary["artifact_count"] == 11
    assert summary["runtime_mutation_performed"] is False
    assert summary["broker_connection_performed"] is False
    assert summary["broker_write_performed"] is False
    assert summary["active_runtime_consumer_eligibility"] == "NO"
    assert (run_dir / "daily" / "2022-09-15" / "strategy" / "input_manifest.json").is_file()
    assert (run_dir / "daily" / "2022-09-15" / "strategy" / "strategy_decision_trace.json").is_file()

    validation = validate_run_strategy_shadow(run_dir=run_dir, business_date="2022-09-15")
    assert validation["structural_validity"] == "PASS"
    assert validation["policy_acceptance"] == "NOT_REQUESTED"
