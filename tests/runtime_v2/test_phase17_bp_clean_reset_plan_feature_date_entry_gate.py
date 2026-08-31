from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.data_readiness import _feature_date_contract_payload


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def test_phase17_bp_clean_reset_plan_uses_non_authority_schedule_expectation(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    before = _snapshot(runtime_root)

    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=5,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
    )
    runner.validate_plan_entry_gate(plan)

    after = _snapshot(runtime_root)
    assert before == after
    assert not (runtime_root / "operations" / "feature_date_contract").exists()
    day1, day4 = plan["business_dates"][0], plan["business_dates"][3]
    assert day1["feature_date"] == "2026-07-06"
    assert day1["feature_date_evidence"]["source"] == "runtime_test_plan_schedule_expectation"
    assert day1["feature_date_evidence"]["profile_value_used_as_authority"] is False
    assert day1["feature_date_evidence"]["contract_materialized"] is False
    assert day4["business_date"] == "2026-07-09"
    assert day4["feature_date"] == "2026-07-08"
    assert day4["carryover"] is True
    assert day4["feature_date_evidence"]["reason"] == "feature_date_contract_not_yet_materialized_plan_expectation_only"


def test_phase17_bp_existing_stale_contract_is_still_rejected(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-09",
        selected_feature_date="2026-07-09",
        status="PASS",
    )

    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=5,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan)
    assert exc.value.status == "PRECONDITION_FAILURE"
    assert "selected_matches_profile_expected" in str(exc.value)
    day4 = plan["business_dates"][3]["feature_date_evidence"]
    assert day4["source"] == "normal_feature_date_contract"
    assert day4["reason"] == "feature_date_authority_mismatch"


def test_phase17_bp_run_time_contract_mismatch_remains_fail_closed(tmp_path: Path) -> None:
    runtime_root = _make_clean_runtime_root(tmp_path)
    _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-09",
        selected_feature_date="2026-07-08",
        status="PASS",
    )

    payload = _feature_date_contract_payload(
        operations_root=runtime_root / "operations",
        business_date="2026-07-09",
        explicit_feature_date="2026-07-09",
    )

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["reason"] == "feature_date_authority_mismatch"
    assert payload["cli_feature_date_authority_status"] == "MISMATCH"


def test_phase24_ig_resume_uses_run_scoped_feature_contract_for_completed_day(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=3,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="phase24-ig-resume",
    )
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase24-ig-resume"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    _write_run_scoped_feature_contract(run_dir, "2026-07-07")
    run_state = {
        "completed_business_days": ["2026-07-06"],
        "halted_at": {"business_date": "2026-07-07", "job": "morning"},
        "next_job": "2026-07-07:morning",
    }

    runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=run_state, resume=True)


def test_phase24_ig_resume_fails_completed_day_missing_run_scoped_contract(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=2,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="phase24-ig-missing",
    )
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase24-ig-missing"
    run_state = {"completed_business_days": ["2026-07-06"], "next_job": "2026-07-07:morning"}

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=run_state, resume=True)

    assert exc.value.status == "PRECONDITION_FAILURE"
    assert "run_scoped_contract_authority_present" in str(exc.value)


def test_phase24_ig_resume_allows_future_plan_expectation_without_materialized_contract(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=3,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="phase24-ig-future",
    )
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase24-ig-future"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    _write_run_scoped_feature_contract(run_dir, "2026-07-07")
    run_state = {
        "completed_business_days": ["2026-07-06"],
        "halted_at": {"business_date": "2026-07-07", "job": "morning"},
        "next_job": "2026-07-07:morning",
    }

    runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=run_state, resume=True)


def test_phase32_be_failed_data_readiness_resume_discovers_market_refresh_feature_contract(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=2,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="phase32-be-market-refresh-authority",
    )
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-market-refresh-authority"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    contract_path = _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-07",
        selected_feature_date="2026-07-07",
        status="PASS",
    )
    _write_market_refresh_manifest(
        run_dir,
        business_date="2026-07-07",
        contract_path=contract_path,
        selected_feature_date="2026-07-07",
        run_id="phase32-be-market-refresh-authority",
    )
    run_state = {
        "completed_business_days": ["2026-07-06"],
        "halted_at": {"business_date": "2026-07-07", "job": "data_readiness"},
        "next_job": "2026-07-07:data_readiness",
    }

    runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=run_state, resume=True)
    evidence = runner._run_scoped_feature_date_contract_evidence(run_dir=run_dir, business_date="2026-07-07")
    assert evidence["feature_date_authority_source"] == "normal_feature_date_contract"
    assert evidence["source"] == "runtime_test_run_scoped_market_refresh"
    assert evidence["selected_feature_date"] == "2026-07-07"
    assert evidence["status"] == "PASS"
    assert evidence["runtime_test_run_binding_status"] == "PASS"


def test_phase32_be_failed_data_readiness_resume_plan_expectation_only_still_fails(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    plan = runner.build_plan(
        profile=profile,
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=2,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id="phase32-be-plan-only",
    )
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-plan-only"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    run_state = {
        "completed_business_days": ["2026-07-06"],
        "halted_at": {"business_date": "2026-07-07", "job": "data_readiness"},
        "next_job": "2026-07-07:data_readiness",
    }

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=run_state, resume=True)

    assert exc.value.status == "PRECONDITION_FAILURE"
    assert "run_scoped_contract_authority_present" in str(exc.value)
    assert "feature_date_contract_not_yet_materialized_plan_expectation_only" in str(exc.value)


def test_phase32_be_failed_data_readiness_resume_missing_materialized_contract_fails(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    profile = _historical_profile()
    plan = _phase32_be_plan(runner, runtime_root, tmp_path, run_id="phase32-be-missing-contract")
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-missing-contract"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    _write_market_refresh_manifest(
        run_dir,
        business_date="2026-07-07",
        contract_path=tmp_path / "missing-feature-date-contract.json",
        selected_feature_date="2026-07-07",
        run_id="phase32-be-missing-contract",
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=_failed_data_readiness_state(), resume=True)

    assert "run_scoped_contract_authority_present" in str(exc.value)


def test_phase32_be_failed_data_readiness_resume_non_pass_contract_fails(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    plan = _phase32_be_plan(runner, runtime_root, tmp_path, run_id="phase32-be-non-pass")
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-non-pass"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    contract_path = _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-07",
        selected_feature_date="2026-07-07",
        status="REVIEW_REQUIRED",
    )
    _write_market_refresh_manifest(
        run_dir,
        business_date="2026-07-07",
        contract_path=contract_path,
        selected_feature_date="2026-07-07",
        run_id="phase32-be-non-pass",
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=_failed_data_readiness_state(), resume=True)

    assert "run_scoped_status_pass" in str(exc.value)


def test_phase32_be_failed_data_readiness_resume_selected_mismatch_fails(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    plan = _phase32_be_plan(runner, runtime_root, tmp_path, run_id="phase32-be-selected-mismatch")
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-selected-mismatch"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    contract_path = _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-07",
        selected_feature_date="2026-07-06",
        status="PASS",
    )
    _write_market_refresh_manifest(
        run_dir,
        business_date="2026-07-07",
        contract_path=contract_path,
        selected_feature_date="2026-07-06",
        run_id="phase32-be-selected-mismatch",
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=_failed_data_readiness_state(), resume=True)

    assert "run_scoped_selected_matches_plan" in str(exc.value)


def test_phase32_be_failed_data_readiness_resume_future_selected_date_fails(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    plan = _phase32_be_plan(runner, runtime_root, tmp_path, run_id="phase32-be-future")
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-future"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    contract_path = _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-07",
        selected_feature_date="2026-07-08",
        status="PASS",
    )
    _write_market_refresh_manifest(
        run_dir,
        business_date="2026-07-07",
        contract_path=contract_path,
        selected_feature_date="2026-07-08",
        run_id="phase32-be-future",
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=_failed_data_readiness_state(), resume=True)

    assert "run_scoped_selected_not_future" in str(exc.value)


def test_phase32_be_failed_data_readiness_resume_cross_run_market_refresh_fails(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    plan = _phase32_be_plan(runner, runtime_root, tmp_path, run_id="phase32-be-current-run")
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32-be-current-run"
    _write_run_scoped_feature_contract(run_dir, "2026-07-06")
    contract_path = _write_feature_date_contract(
        runtime_root,
        business_date="2026-07-07",
        selected_feature_date="2026-07-07",
        status="PASS",
    )
    _write_market_refresh_manifest(
        run_dir,
        business_date="2026-07-07",
        contract_path=contract_path,
        selected_feature_date="2026-07-07",
        run_id="phase32-be-stale-other-run",
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.validate_plan_entry_gate(plan, run_dir=run_dir, run_state=_failed_data_readiness_state(), resume=True)

    assert "run_scoped_run_binding_current" in str(exc.value)


def _load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase17_bp", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _historical_profile() -> dict:
    return json.loads(Path("config/runtime_tests/historical_smoke_5bd.json").read_text(encoding="utf-8"))


def _make_clean_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(root / "persistent_ledger" / "state.json", {"business_date": "", "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "active_pending": False})
    _write_json(root / "runtime_state" / "current_state.json", {"business_date": "", "state": "READY"})
    return root


def _write_feature_date_contract(
    runtime_root: Path,
    *,
    business_date: str,
    selected_feature_date: str,
    status: str,
) -> Path:
    path = runtime_root / "operations" / "feature_date_contract" / f"{business_date}.json"
    _write_json(
        path,
        {
            "status": status,
            "reason": "fixture",
            "requested_feature_date": business_date,
            "selected_feature_date": selected_feature_date,
            "latest_available_market_date": selected_feature_date,
            "carryover_used": selected_feature_date != business_date,
            "freshness_limit_business_days": 1,
            "generated_feature_artifacts": {},
            "missing_feature_artifacts": [],
            "requested_missing_feature_artifacts": [],
            "contract_artifact_path": str(path),
        },
    )
    return path


def _write_run_scoped_feature_contract(run_dir: Path, business_date: str) -> None:
    _write_json(
        run_dir / "daily" / business_date / "data_readiness" / "data_readiness.json",
        {
            "business_date": business_date,
            "feature_date_contract": {
                "status": "PASS",
                "requested_feature_date": business_date,
                "selected_feature_date": business_date,
                "contract_artifact_path": f".runtime/operations/feature_date_contract/{business_date}.json",
                "contract_source": "materialized_feature_date_contract",
                "feature_date_authority_source": "normal_feature_date_contract",
            },
        },
    )


def _phase32_be_plan(runner, runtime_root: Path, tmp_path: Path, *, run_id: str) -> dict:
    return runner.build_plan(
        profile=_historical_profile(),
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports",
        business_days=2,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id=run_id,
    )


def _failed_data_readiness_state() -> dict:
    return {
        "completed_business_days": ["2026-07-06"],
        "halted_at": {"business_date": "2026-07-07", "job": "data_readiness"},
        "next_job": "2026-07-07:data_readiness",
    }


def _write_market_refresh_manifest(
    run_dir: Path,
    *,
    business_date: str,
    contract_path: Path,
    selected_feature_date: str,
    run_id: str,
) -> None:
    _write_json(
        run_dir / "daily" / business_date / "market_refresh" / "runtime_manifest.json",
        {
            "job": "market_refresh",
            "business_date": business_date,
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            "runtime_test_run_id": run_id,
            "runtime_test_profile_id": "historical-smoke",
            "runtime_test_evidence_root": str(run_dir),
            "stages": [
                {
                    "name": "runtime_v2_market_refresh_pipeline",
                    "status": "PASS",
                    "details": {
                        "business_date": business_date,
                        "requested_feature_date": business_date,
                        "selected_feature_date": selected_feature_date,
                        "feature_date_contract_path": str(contract_path),
                        "feature_refresh_status": "FEATURES_READY",
                        "missing_feature_artifacts": [],
                        "requested_missing_feature_artifacts": [],
                    },
                }
            ],
        },
    )


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
