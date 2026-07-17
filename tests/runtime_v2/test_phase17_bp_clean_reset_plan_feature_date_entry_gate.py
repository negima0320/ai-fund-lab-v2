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
) -> None:
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


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
