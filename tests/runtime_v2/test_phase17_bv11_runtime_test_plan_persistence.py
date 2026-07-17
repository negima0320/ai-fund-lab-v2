from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


def test_phase17_bv11_historical_smoke_plan_persists_without_write_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    runtime_root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"

    payload = call_main(
        runner,
        [
            "plan",
            "--profile",
            "historical-smoke",
            "--runtime-root",
            str(runtime_root),
            "--evidence-root",
            str(evidence_root),
        ],
        capsys,
    )

    plan_path = evidence_root / "runs" / payload["run_id"] / "plan.json"
    persisted = json.loads(plan_path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert plan_path.is_file()
    assert payload["plan_persistence"]["status"] == "PASS"
    assert payload["plan_persistence"]["exists"] is True
    assert payload["plan_persistence"]["read_back_valid"] is True
    assert persisted["run_id"] == payload["run_id"]
    assert persisted["profile_id"] == "historical-smoke"
    assert persisted["plan_persistence"]["artifact_hash"] == payload["plan_persistence"]["artifact_hash"]


def test_phase17_bv11_historical_extended_smoke_plan_persists_and_exact_run_id_loads(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    runtime_root = make_runtime_root(tmp_path)
    state_path = runtime_root / "runtime_state" / "current_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["business_date"] = "2026-06-29"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    _write_feature_contract(runtime_root, business_date="2026-07-08", selected_feature_date="2026-07-07")
    evidence_root = tmp_path / "reports"

    payload = call_main(
        runner,
        [
            "plan",
            "--profile",
            "historical-extended-smoke",
            "--runtime-root",
            str(runtime_root),
            "--evidence-root",
            str(evidence_root),
        ],
        capsys,
    )

    loaded = runner.load_plan_for_run(evidence_root=evidence_root, run_id=payload["run_id"])
    assert payload["status"] == "PASS"
    assert payload["requested_start_date"] == runner.load_profile("historical-extended-smoke")["window"]["date_from"]
    assert payload["business_dates"][0]["business_date"] == "2026-06-29"
    assert payload["business_dates"][-1]["business_date"] == "2026-07-10"
    assert loaded["run_id"] == payload["run_id"]
    assert loaded["profile_id"] == "historical-extended-smoke"
    assert loaded["plan_persistence"]["status"] == "PASS"


def test_phase17_bv11_two_plan_invocations_persist_distinct_run_ids(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    runtime_root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"

    first = call_main(
        runner,
        ["plan", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root)],
        capsys,
    )
    second = call_main(
        runner,
        ["plan", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root)],
        capsys,
    )

    assert first["run_id"] != second["run_id"]
    assert (evidence_root / "runs" / first["run_id"] / "plan.json").is_file()
    assert (evidence_root / "runs" / second["run_id"] / "plan.json").is_file()


def test_phase17_bv11_plan_write_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    runtime_root = make_runtime_root(tmp_path)

    def fail_write(*_args, **_kwargs):
        raise OSError("fixture write failure")

    monkeypatch.setattr(runner, "write_json_atomic", fail_write)
    payload = call_main(
        runner,
        ["plan", "--runtime-root", str(runtime_root), "--evidence-root", str(tmp_path / "reports")],
        capsys,
    )

    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert "runtime test plan persistence failed" in payload["error"]


def test_phase17_bv11_plan_readback_mismatch_fails_validation(tmp_path: Path) -> None:
    runner = load_runner()
    runtime_root = make_runtime_root(tmp_path)
    plan = runner.build_plan(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="runtime-test-bv11",
    )
    actual = json.loads(json.dumps(plan))
    actual["run_id"] = "runtime-test-other"

    result = runner.validate_persisted_plan(
        expected=plan,
        actual=actual,
        expected_run_id="runtime-test-bv11",
        expected_profile_id="historical-smoke",
        plan_path=tmp_path / "reports" / "runs" / "runtime-test-bv11" / "plan.json",
    )

    assert result["status"] == "FAIL"
    assert result["run_id_matches"] is False


def _write_feature_contract(runtime_root: Path, *, business_date: str, selected_feature_date: str) -> None:
    path = runtime_root / "operations" / "feature_date_contract" / f"{business_date}.json"
    path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "requested_feature_date": business_date,
                "selected_feature_date": selected_feature_date,
                "latest_available_market_date": selected_feature_date,
                "carryover_used": selected_feature_date != business_date,
                "generated_feature_artifacts": {},
            }
        ),
        encoding="utf-8",
    )
