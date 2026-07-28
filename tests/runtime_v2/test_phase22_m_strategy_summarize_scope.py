from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-strategy-summary-fixture"
BUSINESS_DATE = "2026-07-01"


def test_phase22_m_runtime_test_summarize_strategy_scope(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    _write_json(root / "persistent_ledger" / "state.json", {"schema_version": "runtime_v2_current_temporal_v1", "cash": 1000.0, "total_equity": 1000.0, "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"schema_version": "1", "state": "EMPTY", "status": "EMPTY", "items": []})
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(root)})
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": [BUSINESS_DATE]})
    _write_json(run_dir / "fresh_run_summary.json", {"schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "date_from": BUSINESS_DATE, "date_to": BUSINESS_DATE, "initial_cash": 1000.0, "external_effect_policy": {"broker_write": False, "external_delivery": False, "jquants_fetch": False, "tachibana_api": False}})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "status": "PASS", "final_judgment": "PASS", "final_state_hashes": runner.state_hashes(root)})
    _write_strategy_artifacts(root)

    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "strategy"], capsys)

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["scope"] == "strategy"
    assert "strategy" in payload["available_scopes"]
    assert payload["strategy_scope"]["schema_version"] == "strategy_decision_trace.v1"
    assert payload["strategy_scope"]["status"] == "PASS"
    assert payload["strategy_scope"]["trace"]["runtime_switch_performed"] is False
    assert payload["strategy_scope"]["trace"]["outcome_boundary"]["strategy_input_allowed"] is False
    assert payload["strategy_judgment"] == "PASS"


def _write_strategy_artifacts(root: Path) -> None:
    for kind in (
        "market_context",
        "corporate_event",
        "portfolio_policy",
        "dynamic_position_count",
        "dynamic_cash_exposure",
        "portfolio_construction",
        "position_sizing",
        "position_management",
        "runtime_planning",
    ):
        payload = _payload(kind)
        source = root / "strategy_artifacts" / kind / BUSINESS_DATE / "source.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(kind, encoding="utf-8")
        payload.update(
            {
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "artifact_lifecycle_status": "DRAFT",
                "source_authority_status": "VALID",
                "producer_result_status": "PASS",
                "runtime_consumer_eligibility": "NOT_ELIGIBLE",
                "source_artifacts": [{"role": kind, "path": str(source), "required": True, "status": "PASS"}],
                "source_hashes": [{"role": kind, "path": str(source), "sha256": _file_hash(source)}],
                "reason_codes": [],
            }
        )
        payload["artifact_hash"] = _payload_hash(payload)
        _write_json(root / "strategy_artifacts" / kind / BUSINESS_DATE / f"{kind}.json", payload)


def _payload(kind: str) -> dict:
    if kind == "market_context":
        return {"schema_version": "strategy_market_context.v1", "producer_version": "phase22_l", "trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "NORMAL"}
    if kind == "dynamic_position_count":
        return {"schema_version": "dynamic_position_count.v1", "producer_version": "phase22_h", "target_position_count": 1}
    if kind == "dynamic_cash_exposure":
        return {"schema_version": "dynamic_cash_exposure.v1", "producer_version": "phase22_i", "target_cash_ratio": 0.2, "target_gross_exposure_ratio": 0.8}
    if kind == "portfolio_construction":
        return {"schema_version": "portfolio_construction.v1", "producer_version": "phase22_e", "portfolio_members": [{"security_code": "1001", "membership_intent": "ADD_CANDIDATE"}]}
    if kind == "position_sizing":
        return {"schema_version": "position_sizing.v1", "producer_version": "phase22_j", "total_target_weight": 0.8, "positions": [{"security_code": "1001", "target_weight": 0.8, "target_notional": 800000}]}
    if kind == "position_management":
        return {"schema_version": "position_management.v1", "producer_version": "phase22_k", "positions": [{"security_code": "1001", "action": "ADD", "intensity": "MEDIUM"}]}
    if kind == "runtime_planning":
        return {"schema_version": "runtime_planning.v1", "producer_version": "phase22_g", "planning_intents": [{"security_code": "1001", "planning_intent": "BUY_NEW", "order_side_intent": "BUY"}]}
    return {"schema_version": f"{kind}.v1", "producer_version": "phase22_m_fixture"}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _payload_hash(payload: dict) -> str:
    import hashlib

    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
