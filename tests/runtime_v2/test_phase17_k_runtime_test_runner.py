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
    spec = importlib.util.spec_from_file_location("runtime_test_script", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    (root / "artifact_registry" / "checkpoints").mkdir(parents=True)
    (root / "artifact_registry" / "index").mkdir(parents=True)
    (root / "operations" / "feature_date_contract").mkdir(parents=True)
    (root / "persistent_ledger" / "state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_current_temporal_v1", "environment": "historical", "cash": 12, "buying_power": 12, "positions": []}),
        encoding="utf-8",
    )
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        (root / "persistent_ledger" / name).write_text("", encoding="utf-8")
    (root / "pending_order_plan" / "pending_order_plan.json").write_text(
        json.dumps({"schema_version": "runtime_v2_pending_slot_v1", "status": "EMPTY", "state": "EMPTY", "active_pending": False}),
        encoding="utf-8",
    )
    (root / "runtime_state" / "current_state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_operation_state_v1", "runtime_mode": "historical", "environment": "historical", "state": "READY", "business_date": "2026-07-06"}),
        encoding="utf-8",
    )
    (root / "artifact_registry" / "checkpoints" / "latest.json").write_text(
        json.dumps({"checkpoint_hash": "checkpoint-a"}),
        encoding="utf-8",
    )
    (root / "artifact_registry" / "index" / "registry_index.json").write_text(
        json.dumps({"index_hash": "index-a"}),
        encoding="utf-8",
    )
    for business_date, selected in {
        "2026-07-06": "2026-07-06",
        "2026-07-07": "2026-07-07",
        "2026-07-08": "2026-07-08",
        "2026-07-09": "2026-07-08",
        "2026-07-10": "2026-07-10",
    }.items():
        (root / "operations" / "feature_date_contract" / f"{business_date}.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "requested_feature_date": business_date,
                    "selected_feature_date": selected,
                    "latest_available_market_date": selected,
                    "carryover_used": selected != business_date,
                    "generated_feature_artifacts": {
                        name: str(root / "operations" / "feature_artifacts" / selected / name)
                        for name in (
                            "candidate_features.parquet",
                            "opportunity_feature_input.parquet",
                            "position_feature_input.parquet",
                            "capital_policy_input.parquet",
                        )
                    },
                }
            ),
            encoding="utf-8",
        )
    return root


def call_main(module, args: list[str], capsys: pytest.CaptureFixture[str]) -> dict:
    exit_code = module.main(args + ["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    payload["_exit_code"] = exit_code
    return payload


def test_phase17_k_status_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")], capsys)
    after = runner.directory_hash(root)
    assert payload["status"] == "PASS"
    assert before == after


def test_phase20_h_run_status_matches_status_json_and_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    args = ["--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")]

    run_status = call_main(runner, ["run-status", *args], capsys)
    status = call_main(runner, ["status", *args], capsys)

    assert run_status["_exit_code"] == status["_exit_code"] == runner.EXIT_PASS
    assert run_status == status


def test_phase20_h_run_status_human_output_matches_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    args = ["--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")]

    assert runner.main(["run-status", *args]) == runner.EXIT_PASS
    run_status_output = capsys.readouterr().out
    assert runner.main(["status", *args]) == runner.EXIT_PASS
    status_output = capsys.readouterr().out

    assert run_status_output == status_output


def test_phase17_k_plan_is_read_only_and_uses_runtime_cli_sequence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(
        runner,
        ["plan", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--date-from", "2026-07-06", "--date-to", "2026-07-10"],
        capsys,
    )
    after = runner.directory_hash(root)
    assert payload["status"] == "PASS"
    assert before == after
    assert [job["job"] for job in payload["business_dates"][0]["jobs"]] == list(runner.JOB_SEQUENCE)
    assert payload["business_dates"][2]["feature_date"] == "2026-07-08"
    first_command = payload["business_dates"][0]["jobs"][0]["command"]
    assert "-m" in first_command
    assert runner.RUNTIME_CLI_MODULE in first_command


def test_phase17_k_backup_excludes_foundation_and_dry_run_no_mutation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--dry-run"], capsys)
    after = runner.directory_hash(root)
    assert payload["status"] == "PASS"
    assert before == after
    excluded = set(payload["excluded_prefixes"])
    assert "artifact_registry" in excluded
    assert "phase9/canonical_data" in excluded
    assert all(not item["path"].startswith("artifact_registry") for item in payload["targets"])


def test_phase17_k_reset_requires_valid_backup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    payload = call_main(runner, ["reset", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--dry-run"], capsys)
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE


def test_phase17_k_reset_initial_state_after_confirmed_backup(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    assert backup["status"] == "PASS"
    reset = call_main(runner, ["reset", "--runtime-root", str(root), "--evidence-root", str(evidence), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG], capsys)
    assert reset["status"] == "PASS"
    state = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    pending = json.loads((root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    assert state["cash"] == 1_000_000.0
    assert state["buying_power"] == 1_000_000.0
    assert state["positions"] == []
    assert pending["status"] == "EMPTY"
    assert (root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8") == ""


def test_phase20_o_reset_initial_state_separates_logical_date_from_wall_clock(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)

    reset = call_main(
        runner,
        [
            "reset",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--backup-id",
            backup["backup_id"],
            "--initial-position-state-date",
            "2026-06-15",
            "--initial-cash",
            "1000000",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )
    state = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))

    assert reset["status"] == "PASS"
    assert reset["initial_date_policy"] == "historical_fresh_run_first_business_date"
    assert reset["resolved_initial_position_state_date"] == "2026-06-15"
    assert state["business_date"] == "2026-06-15"
    assert state["as_of"] == "2026-06-15"
    assert state["position_state_as_of"] == "2026-06-15"
    assert state["current_position_status"] == "READY"
    assert state["current_positions_unknown"] is False
    assert state["current_state_confirmed_empty"] is True
    assert state["no_position"] is True
    assert state["no_position_reason"] == "runtime_test_initial_empty_portfolio"
    assert state["position_state_source"] == "runtime_test_reset"
    assert state["temporal_status"] == "READY"
    assert state["review_required"] is False
    assert state["cash"] == 1_000_000.0
    assert state["total_equity"] == 1_000_000.0
    assert state["created_at"] > "2026-06-15"
    assert state["reset_executed_at"] == state["created_at"]
    assert state["wall_clock_fields"]["created_at"] == state["created_at"]
    assert state["logical_time_fields"]["position_state_as_of"] == "2026-06-15"


def test_phase20_o_reset_invalid_initial_position_state_date_fails_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)

    reset = call_main(
        runner,
        [
            "reset",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--backup-id",
            backup["backup_id"],
            "--initial-position-state-date",
            "2026/06/15",
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )

    assert reset["status"] == "PRECONDITION_FAILURE"
    assert reset["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE


def test_phase17_k_reset_clears_historical_broker_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    broker_evidence = root / "runtime_state" / "historical_broker" / "2026-07-06" / "old-fill.json"
    broker_evidence.parent.mkdir(parents=True, exist_ok=True)
    broker_evidence.write_text(json.dumps({"status": "ACCEPTED"}), encoding="utf-8")
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    assert backup["status"] == "PASS"

    broker_evidence.write_text(json.dumps({"status": "STALE_ACCEPTED"}), encoding="utf-8")
    reset = call_main(runner, ["reset", "--runtime-root", str(root), "--evidence-root", str(evidence), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG], capsys)

    assert reset["status"] == "PASS"
    assert "runtime_state/historical_broker" in reset["reset_scope"]
    assert not (root / "runtime_state" / "historical_broker").exists()


def test_phase17_k_run_invokes_normal_runtime_cli_and_stops_on_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 30, "", "halt")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert backup["status"] == "PASS"
    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert commands
    assert commands[0][commands[0].index("-m") + 1] == runner.RUNTIME_CLI_MODULE


def test_phase17_k_run_marks_execution_success_when_runtime_cli_jobs_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )

    assert backup["status"] == "PASS"
    assert payload["status"] == "PASS"
    assert any("--job" in command and command[command.index("--job") + 1] == "execution" for command in commands)
    assert len(commands) == len(runner.JOB_SEQUENCE)


def test_phase20_u_run_halts_when_pm_artifact_halts_despite_cli_exit_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        job = command[command.index("--job") + 1]
        business_date = command[command.index("--business-date") + 1]
        if job == "sell_planning":
            pm_dir = root / "runtime_state" / "position_management" / business_date
            pm_dir.mkdir(parents=True)
            (pm_dir / "position_management_decisions.json").write_text(
                json.dumps(
                    {
                        "status": "HALT",
                        "reason": "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
                        "decisions": [],
                        "input_contract": {
                            "pm_input_schema_status": "HALT",
                            "pm_runtime_adapter_authority_status": "HALT",
                            "pm_runtime_adapter_authority_reason": "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
                        },
                    }
                ),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_id = next((evidence / "runs").iterdir()).name
    run_state = json.loads((evidence / "runs" / run_id / "run_state.json").read_text(encoding="utf-8"))
    pm_snapshot = json.loads((evidence / "runs" / run_id / "daily" / "2026-07-06" / "position_management" / "pm_decisions.json").read_text(encoding="utf-8"))

    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert run_state["status"] == "HALT"
    assert run_state["halted_at"]["runtime_test_job_status"] == "HALT_PM_POSITION_MANAGEMENT"
    assert pm_snapshot["source_status"] == "AVAILABLE"
    assert pm_snapshot["pm_status"] == "HALT"
    assert pm_snapshot["pm_authority_status"] == "HALT"
    assert pm_snapshot["pm_decision_count"] == 0
    assert [command[command.index("--job") + 1] for command in commands][-1] == "sell_planning"


def test_phase17_k_run_dry_run_never_executes_runtime_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)

    def forbidden_run(command: list[str], *, cwd: Path):
        raise AssertionError("runtime cli must not run in dry-run")

    monkeypatch.setattr(runner, "run_runtime_cli", forbidden_run)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--dry-run"], capsys)
    after = runner.directory_hash(root)
    assert payload["status"] == "DRY_RUN"
    assert payload["dry_run_no_mutation"] is True
    assert before == after


def test_phase17_k_resume_rejects_changed_source_baseline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "runtime-test-fixture"
    run_dir = evidence / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_state.json").write_text(
        json.dumps({"schema_version": "phase17_k_run_state_v1", "run_id": run_id, "status": "HALT", "source_baseline": {"source_commit": "different", "source_dirty": False, "registry_hash": "different"}}),
        encoding="utf-8",
    )
    payload = call_main(runner, ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id, "--dry-run"], capsys)
    assert payload["status"] == "PRECONDITION_FAILURE"


def test_phase17_k_resume_uses_fixed_plan_without_skipping_failed_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    plan = runner.build_plan(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        evidence_root=evidence,
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-resume-fixture",
    )
    run_dir = evidence / "runs" / "runtime-test-resume-fixture"
    runner.write_json_atomic(run_dir / "plan.json", plan)
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": "phase17_k_run_state_v1",
            "run_id": "runtime-test-resume-fixture",
            "status": "HALT",
            "source_baseline": runner.source_baseline(root),
            "completed_jobs": [
                {"business_date": "2026-07-06", "job": "market_refresh", "exit_code": 0},
                {"business_date": "2026-07-06", "job": "data_readiness", "exit_code": 30},
            ],
        },
    )
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["resume", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", "runtime-test-resume-fixture", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    assert payload["status"] == "PASS"
    assert commands[0][commands[0].index("--job") + 1] == "data_readiness"


def test_phase17_k_rollback_restores_full_resettable_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    backup = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    (root / "persistent_ledger" / "state.json").write_text(json.dumps({"schema_version": "changed", "cash": 0}), encoding="utf-8")
    payload = call_main(runner, ["rollback", "--runtime-root", str(root), "--evidence-root", str(evidence), "--backup-id", backup["backup_id"], "--confirm", CONFIRM_FLAG], capsys)
    restored = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert restored["cash"] == 12


def test_phase17_k_mode_rooted_path_and_production_profile_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    mode_rooted = root / "historical"
    payload = call_main(runner, ["status", "--runtime-root", str(mode_rooted), "--evidence-root", str(tmp_path / "reports")], capsys)
    assert payload["status"] == "INVALID_ARGUMENT"
    production_profile = tmp_path / "production_profile.json"
    profile = json.loads(Path("config/runtime_tests/historical_smoke_5bd.json").read_text(encoding="utf-8"))
    profile["profile_id"] = "production-fixture"
    profile["mode"] = "production"
    profile["runtime_root"] = str(root)
    production_profile.write_text(json.dumps(profile), encoding="utf-8")
    payload = call_main(runner, ["status", "--profile", str(production_profile), "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports")], capsys)
    assert payload["status"] == "HALT"
