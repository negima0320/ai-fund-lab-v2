from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support import (
    HistoricalInitialStateConfig,
    build_reset_plan,
    collect_regression_baseline,
    evaluate_historical_runtime_entry_gates,
    validate_reset_plan,
)


def test_phase17_b1_reset_plan_uses_normal_runtime_root_and_excludes_foundation(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    (runtime_root / "persistent_ledger").mkdir(parents=True)
    (runtime_root / "pending_order_plan").mkdir(parents=True)
    (runtime_root / "runtime_state").mkdir(parents=True)
    (runtime_root / "persistent_ledger" / "state.json").write_text("{}", encoding="utf-8")
    (runtime_root / "pending_order_plan" / "pending_order_plan.json").write_text("{}", encoding="utf-8")
    (runtime_root / "runtime_state" / "current_state.json").write_text("{}", encoding="utf-8")

    plan = build_reset_plan(
        runtime_root=runtime_root,
        environment_id="phase17-b1-test",
        run_id="run-test",
        git_commit="abc123",
        runtime_version="runtime_v2",
        initial_state=HistoricalInitialStateConfig(),
    )
    validation = validate_reset_plan(plan)

    assert validation["status"] == "PASS"
    target_paths = {target["path"] for target in plan["targets"]}
    assert "persistent_ledger/state.json" in target_paths
    assert "artifact_registry" not in target_paths
    assert plan["execution_status"] == "PLAN_ONLY_NOT_EXECUTED"


def test_phase17_b1_reset_plan_halts_on_reset_excluded_target(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    plan = build_reset_plan(
        runtime_root=runtime_root,
        environment_id="phase17-b1-test",
        run_id="run-test",
        git_commit="abc123",
        runtime_version="runtime_v2",
    )
    plan["targets"].append({"path": "artifact_registry/events/registry_events.jsonl"})

    validation = validate_reset_plan(plan)

    assert validation["status"] == "HALT"
    assert any("reset-excluded" in error for error in validation["errors"])


def test_phase17_b1_baseline_collects_read_only_refs() -> None:
    baseline = collect_regression_baseline(runtime_root=".runtime", repo_root=".")

    assert baseline["collection_mode"] == "READ_ONLY"
    assert baseline["files"]["registry_event_log"]["exists"] is True
    assert baseline["registry"]["accepted_sets"]
    assert baseline["pm_adapter_authority"]["classification"] in {"PASS", "ARTIFACT_AUTHORITY_GAP"}


def test_phase17_b1_gate_evaluation_does_not_allow_5bd_when_entry_gates_block() -> None:
    evaluation = evaluate_historical_runtime_entry_gates(runtime_root=".runtime", repo_root=".")
    gates = {gate["gate"]: gate for gate in evaluation["entry_gates"]}

    assert evaluation["five_bd_started"] is False
    assert evaluation["five_bd_start_allowed"] is False
    assert gates["NORMAL_MAINLINE_READY"]["status"] == "DESIGN_CHANGE_REQUIRED"
    assert gates["PM_ADAPTER_AUTHORITY_READY"]["classification"] == "ARTIFACT_AUTHORITY_GAP"
