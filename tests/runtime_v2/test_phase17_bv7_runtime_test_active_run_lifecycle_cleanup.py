from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def test_phase17_bv7_closed_halt_run_is_not_active_in_status(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports/runtime_tests"
    _write_run(
        evidence_root,
        run_id="runtime-test-historical-smoke-closed",
        profile_id="historical-smoke",
        status="HALT",
        next_job="2026-06-29:market_refresh",
        closed=True,
    )

    result = runner.status(
        profile=_historical_profile("historical-smoke"),
        runtime_root=runtime_root,
        evidence_root=evidence_root,
    )

    assert result.payload["active_test_run"] == ""
    assert result.payload["run_status"] == "IDLE"
    assert result.payload["next_job"] == ""
    assert (evidence_root / "runs/runtime-test-historical-smoke-closed/run_state.json").exists()
    assert (evidence_root / "runs/runtime-test-historical-smoke-closed/final_summary.json").exists()


def test_phase17_bv7_profile_status_does_not_select_other_profile_halt_run(tmp_path: Path) -> None:
    runner = _load_runner()
    evidence_root = tmp_path / "reports/runtime_tests"
    _write_run(
        evidence_root,
        run_id="runtime-test-historical-smoke-open",
        profile_id="historical-smoke",
        status="HALT",
        next_job="2026-06-29:market_refresh",
        closed=False,
    )

    active = runner.active_run_for_profile(evidence_root, profile_id="historical-extended-smoke")

    assert active == {}


def test_phase17_bv7_same_profile_unclosed_halt_remains_resumable_candidate(tmp_path: Path) -> None:
    runner = _load_runner()
    evidence_root = tmp_path / "reports/runtime_tests"
    _write_run(
        evidence_root,
        run_id="runtime-test-historical-extended-smoke-open",
        profile_id="historical-extended-smoke",
        status="HALT",
        next_job="2021-07-16:market_refresh",
        closed=False,
    )

    active = runner.active_run_for_profile(evidence_root, profile_id="historical-extended-smoke")

    assert active["run_id"] == "runtime-test-historical-extended-smoke-open"
    assert active["next_job"] == "2021-07-16:market_refresh"


def test_phase17_bv7_resume_rejects_closed_run_before_mutation(tmp_path: Path) -> None:
    runner = _load_runner()
    runtime_root = _make_clean_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports/runtime_tests"
    run_id = "runtime-test-historical-smoke-closed"
    _write_run(
        evidence_root,
        run_id=run_id,
        profile_id="historical-smoke",
        status="HALT",
        next_job="2026-06-29:market_refresh",
        closed=True,
    )

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.resume_command(
            argparse.Namespace(run_id=run_id, dry_run=True),
            profile=_historical_profile("historical-smoke"),
            runtime_root=runtime_root,
            evidence_root=evidence_root,
        )

    assert exc.value.status == "PRECONDITION_FAILURE"
    assert exc.value.exit_code == runner.EXIT_PRECONDITION_FAILURE
    assert "run is closed" in str(exc.value)


def _load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase17_bv7", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _historical_profile(profile_id: str) -> dict:
    return {
        "profile_id": profile_id,
        "mode": "historical",
        "runtime_root": ".runtime",
        "external_effect_policy": {
            "external_delivery": False,
            "jquants_fetch": False,
            "broker_write": False,
            "tachibana_api": False,
        },
    }


def _make_clean_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(root / "persistent_ledger" / "state.json", {"business_date": "", "cash": 1000000, "buying_power": 1000000, "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "active_pending": False})
    _write_json(root / "runtime_state" / "current_state.json", {"business_date": "", "environment": "historical", "state": "READY"})
    _write_json(root / "artifact_registry" / "checkpoints" / "latest.json", {"schema_version": "test"})
    for name in ("orders.jsonl", "executions.jsonl", "positions.jsonl", "cash.jsonl", "events.jsonl"):
        path = root / "persistent_ledger" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return root


def _write_run(
    evidence_root: Path,
    *,
    run_id: str,
    profile_id: str,
    status: str,
    next_job: str,
    closed: bool,
) -> None:
    run_dir = evidence_root / "runs" / run_id
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": "runtime_test_run_state_v1",
            "run_id": run_id,
            "profile_id": profile_id,
            "status": status,
            "completed_business_days": [],
            "completed_jobs": [],
            "next_job": next_job,
            "source_baseline": {},
        },
    )
    if closed:
        _write_json(
            run_dir / "final_summary.json",
            {
                "schema_version": "runtime_test_final_summary_v1",
                "run_id": run_id,
                "profile_id": profile_id,
                "status": "PASS",
                "closed_at": "2026-07-16T06:18:10Z",
            },
        )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
