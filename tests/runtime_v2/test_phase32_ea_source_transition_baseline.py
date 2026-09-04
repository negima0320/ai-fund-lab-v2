from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"
CONFIRM_FLAG = "--yes-i-understand-this-mutates-trading-state"


def load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase32_ea", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def call_main(module, args: list[str], capsys: pytest.CaptureFixture[str]) -> dict:
    exit_code = module.main(args + ["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    payload["_exit_code"] = exit_code
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def make_runtime_root(tmp_path: Path, runner) -> Path:
    root = tmp_path / ".runtime"
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    (root / "artifact_registry" / "checkpoints").mkdir(parents=True)
    (root / "artifact_registry" / "index").mkdir(parents=True)
    write_json(
        root / "persistent_ledger" / "state.json",
        {"schema_version": "runtime_v2_current_temporal_v1", "environment": "historical", "cash": 1000, "positions": []},
    )
    write_json(
        root / "runtime_state" / "current_state.json",
        {"schema_version": "runtime_v2_operation_state_v1", "runtime_mode": "historical", "business_date": "2026-07-06"},
    )
    write_json(root / "pending_order_plan" / "pending_order_plan.json", {"schema_version": "runtime_v2_pending_slot_v1", "state": "EMPTY"})
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        append_jsonl(root / "persistent_ledger" / name, [])
    write_json(root / "artifact_registry" / "checkpoints" / "latest.json", {"checkpoint_hash": "checkpoint"})
    write_json(root / "artifact_registry" / "index" / "registry_index.json", {"index_hash": "index"})
    return root


def make_halted_run(
    tmp_path: Path,
    runner,
    *,
    old_baseline: dict,
    next_job: str = "2026-07-07:morning",
    status: str = "HALT",
    source_transitions: object | None = None,
) -> tuple[Path, str]:
    evidence = tmp_path / "reports"
    run_id = "runtime-test-source-transition-fixture"
    run_dir = evidence / "runs" / run_id
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "plan.json",
        {
            "schema_version": runner.PLAN_SCHEMA_VERSION,
            "run_id": run_id,
            "business_dates": [
                {"business_date": "2026-07-06", "jobs": [{"job": "market_refresh"}, {"job": "data_readiness"}]},
                {"business_date": "2026-07-07", "jobs": [{"job": "morning"}, {"job": "sell_planning"}, {"job": "submit"}]},
            ],
        },
    )
    (run_dir / "daily" / "2026-07-06" / "market_refresh").mkdir(parents=True)
    (run_dir / "daily" / "2026-07-06" / "data_readiness").mkdir(parents=True)
    business_date, _, job = next_job.partition(":")
    run_state = {
        "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": "historical-smoke",
        "status": status,
        "completed_business_days": ["2026-07-06"],
        "completed_jobs": [
            {"business_date": "2026-07-06", "job": "market_refresh", "exit_code": 0},
            {"business_date": "2026-07-06", "job": "data_readiness", "exit_code": 0},
            {"business_date": business_date, "job": job, "exit_code": 10},
        ],
        "next_job": next_job,
        "halted_at": {"business_date": business_date, "job": job, "exit_code": 10, "runtime_test_job_status": "REVIEW_REQUIRED"},
        "source_baseline": old_baseline,
        "historical_evaluation_authority": {},
    }
    if source_transitions is not None:
        run_state["source_transitions"] = source_transitions
    write_json(run_dir / "run_state.json", run_state)
    return evidence, run_id


def patch_baseline(monkeypatch: pytest.MonkeyPatch, runner, baseline: dict) -> None:
    monkeypatch.setattr(runner, "source_baseline", lambda runtime_root: dict(baseline))


def transition_args(root: Path, evidence: Path, run_id: str, *extra: str) -> list[str]:
    return [
        "transition-source-baseline",
        "--runtime-root",
        str(root),
        "--evidence-root",
        str(evidence),
        "--run-id",
        run_id,
        "--reason",
        "focused source transition fixture",
        "--operator",
        "pytest",
        *extra,
    ]


def test_phase32_ea_resume_rejects_unrecorded_source_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old)
    patch_baseline(monkeypatch, runner, new)

    payload = call_main(runner, ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--dry-run"], capsys)

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "baseline changed" in payload["error"]


def test_phase32_ea_transition_dry_run_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old)
    patch_baseline(monkeypatch, runner, new)
    before = runner.directory_hash(evidence / "runs" / run_id)

    payload = call_main(runner, transition_args(root, evidence, run_id, "--dry-run"), capsys)
    after = runner.directory_hash(evidence / "runs" / run_id)

    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert payload["changed_baseline_keys"] == ["source_commit"]
    assert payload["restart_point"]["next_job"] == "2026-07-07:morning"
    assert payload["target_retry_boundary_side_effect_proof"]["status"] == "PASS"
    assert before == after


def test_phase32_ea_successful_transition_preserves_completed_and_retry_boundary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old)
    patch_baseline(monkeypatch, runner, new)
    run_dir = evidence / "runs" / run_id
    completed_before = runner.directory_hash(run_dir / "daily" / "2026-07-06")

    payload = call_main(runner, transition_args(root, evidence, run_id, "--confirm", CONFIRM_FLAG), capsys)
    updated = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    completed_after = runner.directory_hash(run_dir / "daily" / "2026-07-06")

    assert payload["status"] == "PASS"
    assert payload["transition_created"] is True
    assert updated["source_baseline"]["source_commit"] == "new"
    assert updated["next_job"] == "2026-07-07:morning"
    assert updated["completed_business_days"] == ["2026-07-06"]
    assert completed_before == completed_after
    assert len(updated["source_transitions"]) == 1
    assert Path(payload["source_transition_artifact"]["artifact_path"]).exists()
    assert updated["source_generation_count"] == 2
    assert updated["single_source_generation_run"] is False
    assert updated["source_transition_present"] is True


def test_phase32_ea_transition_is_idempotent_for_already_current_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    current = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=current, source_transitions=[{"transition_id": "prior"}])
    patch_baseline(monkeypatch, runner, current)

    payload = call_main(runner, transition_args(root, evidence, run_id, "--confirm", CONFIRM_FLAG), capsys)
    updated = json.loads((evidence / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert payload["idempotent_already_current"] is True
    assert payload["transition_created"] is False
    assert updated["source_transitions"] == [{"transition_id": "prior"}]


def test_phase32_ea_transition_rejects_stale_expected_old_baseline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old)
    patch_baseline(monkeypatch, runner, new)

    payload = call_main(runner, transition_args(root, evidence, run_id, "--dry-run", "--expected-old-source-commit", "other"), capsys)

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "stale expected old source_commit" in payload["reason"]


def test_phase32_ea_transition_rejects_registry_or_accepted_authority_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry-old", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry-new", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old)
    patch_baseline(monkeypatch, runner, new)

    payload = call_main(runner, transition_args(root, evidence, run_id, "--dry-run"), capsys)

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["authority_changed_keys"] == ["registry_hash"]


def test_phase32_ea_transition_rejects_malformed_history(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old, source_transitions={"bad": "shape"})
    patch_baseline(monkeypatch, runner, new)

    payload = call_main(runner, transition_args(root, evidence, run_id, "--dry-run"), capsys)

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert "malformed source_transitions" in payload["reason"]


def test_phase32_ea_transition_rejects_unsafe_submit_execution_boundary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old, next_job="2026-07-07:submit")
    (evidence / "runs" / run_id / "daily" / "2026-07-07" / "execution").mkdir(parents=True)
    patch_baseline(monkeypatch, runner, new)

    payload = call_main(runner, transition_args(root, evidence, run_id, "--dry-run"), capsys)

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["target_retry_boundary_side_effect_proof"]["status"] == "PRECONDITION_FAILURE"


def test_phase32_ea_resume_dry_run_accepts_after_transition(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, runner)
    old = {"source_commit": "old", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    new = {"source_commit": "new", "source_dirty": False, "registry_hash": "registry", "accepted_artifact_hash": "accepted"}
    evidence, run_id = make_halted_run(tmp_path, runner, old_baseline=old)
    patch_baseline(monkeypatch, runner, new)
    call_main(runner, transition_args(root, evidence, run_id, "--confirm", CONFIRM_FLAG), capsys)

    payload = call_main(runner, ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--dry-run"], capsys)

    assert payload["status"] == "DRY_RUN"
    assert payload["resume_allowed"] is True
