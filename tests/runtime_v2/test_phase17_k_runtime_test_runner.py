from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import pandas as pd


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
    _write_accepted_generation_authority(root, business_date="2026-07-06")
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


def _write_accepted_generation_authority(root: Path, *, business_date: str) -> None:
    generation_id = "phase26-step10r4-fixture-generation"
    generation_dir = root / "ai_lifecycle" / "generations" / generation_id
    generation_dir.mkdir(parents=True, exist_ok=True)
    candidate_model = generation_dir / "candidate_model.bin"
    opportunity_model = generation_dir / "opportunity_model.bin"
    candidate_model.write_bytes(b"phase26-step10r4-candidate-model")
    opportunity_model.write_bytes(b"phase26-step10r4-opportunity-model")
    manifest = {
        "schema_version": "runtime_v2_accepted_generation_manifest_v1",
        "generation_id": generation_id,
        "accepted_generation_id": generation_id,
        "status": "COMMITTED",
        "authority_decision": "business-date-bound Accepted Generation ledger",
        "accepted_at": f"{business_date}T00:00:00+00:00",
        "effective_from": f"{business_date}T00:00:00+00:00",
        "candidate_member": {
            "role": "candidate_model",
            "artifact_path": "candidate_model.bin",
            "model_hash": _sha256(candidate_model),
        },
        "opportunity_member": {
            "role": "opportunity_model",
            "artifact_path": "opportunity_model.bin",
            "model_hash": _sha256(opportunity_model),
        },
        "freshness_metadata": {
            "field_sources": {
                "candidate_training_cutoff": {"value": "2026-06-30"},
                "opportunity_training_cutoff": {"value": "2026-06-30"},
                "candidate_calibration_cutoff": {"value": "2026-06-30"},
                "opportunity_calibration_cutoff": {"value": "2026-06-30"},
                "validation_cutoff": {"value": "2026-06-30"},
            },
        },
        "runtime_baseline": {"source": "phase26_step10r4_test_fixture"},
    }
    manifest["aggregate_hash"] = _stable_hash(manifest)
    manifest_path = generation_dir / "accepted_generation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    pointer = {
        "schema_version": "runtime_v2_accepted_generation_pointer_v1",
        "transaction_state": "COMMITTED",
        "accepted_generation_id": generation_id,
        "bundle_manifest_path": str(Path("ai_lifecycle") / "generations" / generation_id / "accepted_generation_manifest.json"),
        "aggregate_hash": manifest["aggregate_hash"],
        "accepted_at": manifest["accepted_at"],
        "effective_from": manifest["effective_from"],
    }
    (root / "runtime_state" / "accepted_buy_ai_bundle.json").write_text(json.dumps(pointer, sort_keys=True), encoding="utf-8")
    history_dir = root / "ai_lifecycle" / "authority_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    (history_dir / "accepted_generation_history.jsonl").write_text(
        json.dumps(
            {
                "event": "ACCEPTED_GENERATION_COMMITTED",
                "generation_id": generation_id,
                "bundle_manifest_path": str(Path("ai_lifecycle") / "generations" / generation_id / "accepted_generation_manifest.json"),
                "accepted_at": manifest["accepted_at"],
                "effective_from": manifest["effective_from"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


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


def test_phase26_pf3f_runtime_cli_records_trace_without_fixed_timeout(tmp_path: Path) -> None:
    runner = load_runner()
    trace_path = tmp_path / "subprocess_trace.json"

    completed = runner.run_runtime_cli(
        [sys.executable, "-c", "print('trace-ok')"],
        cwd=tmp_path,
        trace_path=trace_path,
        context={"run_id": "timeout-test", "business_date": "2026-07-21", "job": "market_refresh"},
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == "trace-ok"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "COMPLETED"
    assert trace["timed_out"] is False
    assert trace["formal_stall_timeout_contract"] == "NOT_CONFIGURED"
    assert trace["stall_timeout_seconds"] is None
    assert trace["job"] == "market_refresh"
    assert trace["returncode"] == 0
    assert trace["pid"]
    assert trace["started_at"]
    assert trace["ended_at"]
    assert trace["elapsed_seconds"] >= 0


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


def test_phase26_pf3h_date_from_overrides_profile_start_for_business_day_window(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2022-07-01", "2022-07-04", "2022-07-05", "2026-07-06"])

    window = runner.resolve_business_window(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        business_days=3,
        start_date=None,
        date_from="2022-07-01",
        date_to=None,
    )

    assert window["requested_start_date"] == "2022-07-01"
    assert window["profile_start_date"] == "2026-07-06"
    assert window["selected_start_date"] == "2022-07-01"
    assert window["selection_authority"] == "cli_date_from"
    assert window["override_applied"] is True
    assert window["override_reason"] == "cli_date_from_defines_business_days_window_start"
    assert window["resolved_business_dates"] == ["2022-07-01", "2022-07-04", "2022-07-05"]


def test_phase26_pf3h_profile_start_remains_fallback_when_cli_start_absent(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08"])

    window = runner.resolve_business_window(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        business_days=3,
        start_date=None,
        date_from=None,
        date_to=None,
    )

    assert window["requested_start_date"] == "2026-07-06"
    assert window["profile_start_date"] == "2026-07-06"
    assert window["selected_start_date"] == "2026-07-06"
    assert window["selection_authority"] == "profile_window_date_from"
    assert window["override_applied"] is False
    assert window["override_reason"] == "profile_default_used_when_cli_start_absent"
    assert window["resolved_business_dates"] == ["2026-07-06", "2026-07-07", "2026-07-08"]


def _write_historical_calendar(root: Path, days: list[str]) -> None:
    target = root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar"
    target.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in days]).to_parquet(target / "data.parquet", index=False)
    (target / "validation.json").write_text(json.dumps({"status": "PASS", "reason": "calendar_authority_ready", "max_date": days[-1] if days else ""}), encoding="utf-8")


def _write_validated_calendar_overlay(root: Path, days: list[str]) -> None:
    run_root = root / "market_data_acquisition" / "runs" / "jquants-acquisition-test"
    calendar = run_root / "raw" / "jquants" / "trading_calendar"
    calendar.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": day, "HolDiv": "1"} for day in days]).to_parquet(calendar / "data.parquet", index=False)
    final_validation = {
        "status": "PASS",
        "future_date_count": 0,
        "normalized_inventory": {"duplicate_key_count": 0},
        "schema_comparison": {"status": "PASS", "runtime_merge_compatible": True},
        "jquants_lineage": {"status": "PASS"},
    }
    (run_root / "state.json").write_text(json.dumps({"status": "PASS", "acquisition_run_id": run_root.name, "final_validation": final_validation}), encoding="utf-8")
    (run_root / "plan.json").write_text(json.dumps({"status": "PASS", "acquisition_run_id": run_root.name}), encoding="utf-8")


def test_phase23_ag_plan_preserves_requested_window_when_calendar_is_partial(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15"])

    plan = runner.build_plan(
        profile=runner.load_profile("historical-extended-smoke"),
        runtime_root=root,
        evidence_root=tmp_path / "reports",
        business_days=10,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-window-partial",
    )

    assert plan["requested_business_days"] == 10
    assert plan["resolved_business_day_count"] == 8
    assert plan["window_resolution_status"] == "REVIEW_REQUIRED"
    assert plan["request_conformance_status"] == "NOT_PASS"
    assert plan["unresolved_requested_dates"] == ["2026-07-16", "2026-07-17"]


def test_phase26_pf3c_plan_returns_review_required_for_empty_resolved_window(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08"])

    payload = call_main(
        runner,
        [
            "plan",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(tmp_path / "reports"),
            "--start-date",
            "2026-07-20",
            "--business-days",
            "10",
        ],
        capsys,
    )

    assert payload["_exit_code"] == runner.EXIT_REVIEW_REQUIRED
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["plan_judgment"] == "PLAN_REVIEW_REQUIRED"
    assert payload["requested_start_date"] == "2026-07-20"
    assert payload["resolved_business_dates"] == []
    assert payload["business_dates"] == []
    assert payload["eligible_dates"] == []
    assert payload["first_eligible_start_date"] is None
    assert payload["operator_ready"] is False
    assert payload["source_readiness"]["blocked_dates"] == payload["unresolved_requested_dates"]
    assert payload["calendar_readiness"]["status"] == "REVIEW_REQUIRED"


def test_phase23_ag_plan_composes_validated_calendar_overlay_for_full_resolution(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15"])
    _write_validated_calendar_overlay(root, ["2026-07-16", "2026-07-17", "2026-07-20"])

    plan = runner.build_plan(
        profile=runner.load_profile("historical-extended-smoke"),
        runtime_root=root,
        evidence_root=tmp_path / "reports",
        business_days=10,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-window-overlay",
    )

    assert plan["requested_business_days"] == 10
    assert plan["resolved_business_day_count"] == 10
    assert plan["resolved_business_dates"][-2:] == ["2026-07-16", "2026-07-17"]
    assert plan["window_resolution_status"] == "PASS"
    assert plan["calendar_authority"]["overlay_count"] == 1


def test_phase23_ag_plan_ignores_unvalidated_calendar_overlay(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    _write_historical_calendar(root, ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15"])
    run_root = root / "market_data_acquisition" / "runs" / "unvalidated"
    calendar = run_root / "raw" / "jquants" / "trading_calendar"
    calendar.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": "2026-07-16", "HolDiv": "1"}, {"Date": "2026-07-17", "HolDiv": "1"}]).to_parquet(calendar / "data.parquet", index=False)

    plan = runner.build_plan(
        profile=runner.load_profile("historical-extended-smoke"),
        runtime_root=root,
        evidence_root=tmp_path / "reports",
        business_days=10,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-window-unvalidated",
    )

    assert plan["requested_business_days"] == 10
    assert plan["resolved_business_day_count"] == 8
    assert plan["window_resolution_status"] == "REVIEW_REQUIRED"
    assert plan["calendar_authority"]["overlay_count"] == 0


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


def test_fresh_run_accepts_auto_abandon_on_error_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--dry-run", "--auto-abandon-on-error"],
        capsys,
    )
    assert payload["status"] == "DRY_RUN"


def test_fresh_run_auto_abandon_writes_standard_abandonment_artifacts(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"
    run_id = "runtime-test-auto-abandon"
    run_dir = evidence_root / "runs" / run_id
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "HALT",
            "halted_at": {"business_date": "2026-07-06", "job": "submit", "exit_code": 20},
            "completed_business_days": [],
            "next_job": "submit",
        },
    )

    result = runner._maybe_auto_abandon_fresh_run(
        args=runner.argparse.Namespace(auto_abandon_on_error=True, auto_abandon_reason="test_auto_abandon"),
        profile={"profile_id": "historical-smoke"},
        runtime_root=root,
        evidence_root=evidence_root,
        run_id=run_id,
        final_status="HALT",
        exit_code=runner.EXIT_HALT,
    )

    abandonment = json.loads((run_dir / "abandonment.json").read_text(encoding="utf-8"))
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))
    assert result["performed"] is True
    assert result["reason"] == "halt_run_abandoned_after_fresh_run_error"
    assert abandonment["abandon_reason"] == "test_auto_abandon"
    assert abandonment["abandoned_by"] == "fresh-run"
    assert abandonment["resume_disabled"] is True
    assert final_summary["status"] == "ABANDONED"
    assert final_summary["broker_write"] is False


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


def test_phase23_d_halt_summary_propagates_manifest_reason_after_state_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    manifest_path = tmp_path / "runtime_manifest.json"

    def fake_run(command: list[str], *, cwd: Path):
        job = command[command.index("--job") + 1]
        business_date = command[command.index("--business-date") + 1]
        if job == "submit":
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "daily-runtime-fixture",
                        "business_date": business_date,
                        "job": job,
                        "exit_code": 20,
                        "final_state": "REVIEW_REQUIRED",
                        "reason": "historical_safety_temporal_authority_missing",
                        "data_readiness_review_reasons": ["historical_safety_temporal_authority_missing"],
                        "data_readiness_next_operator_action": "Refresh or inspect evidence: historical_safety_temporal_authority_missing",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 20, json.dumps({"exit_code": 20, "manifest": str(manifest_path)}), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        ["run", "--runtime-root", str(root), "--evidence-root", str(evidence), "--business-days", "1", "--start-date", "2026-07-06", "--confirm", CONFIRM_FLAG],
        capsys,
    )
    run_id = next((evidence / "runs").iterdir()).name
    run_dir = evidence / "runs" / run_id
    run_state = json.loads((run_dir / "run_state.json").read_text(encoding="utf-8"))
    status_payload = call_main(runner, ["status", "--runtime-root", str(root), "--evidence-root", str(evidence)], capsys)
    close_payload = call_main(runner, ["close", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id], capsys)
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))

    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert run_state["status"] == "HALT"
    assert run_state["halted_at"]["exit_code"] == 20
    assert run_state["halt_summary"]["status"] == "HALT"
    assert run_state["halt_summary"]["root_reason"] == "historical_safety_temporal_authority_missing"
    assert run_state["halt_summary"]["root_reason_code"] == "historical_safety_temporal_authority_missing"
    assert run_state["halt_summary"]["recommended_action"] == "Refresh or inspect evidence: historical_safety_temporal_authority_missing"
    assert status_payload["halt_summary"] == run_state["halt_summary"]
    assert close_payload["halt_summary"] == run_state["halt_summary"]
    assert final_summary["halt_summary"] == run_state["halt_summary"]


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
    historical_authority = runner.materialize_historical_evaluation_authority(
        run_dir=run_dir,
        runtime_root=root,
        profile=runner.load_profile("historical-smoke"),
        plan_payload=plan,
    )
    runner.write_json_atomic(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": "runtime-test-resume-fixture",
            "status": "HALT",
            "source_baseline": runner.source_baseline(root),
            "historical_evaluation_authority": historical_authority,
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
