from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.performance_evaluation import (
    CAPITAL_TRACE_SCHEMA_VERSION,
    build_capital_efficiency_trace,
    validate_capital_efficiency_trace,
)
from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-phase25-a3-fixture"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _prepare_run(runner, tmp_path: Path, *, with_planning: bool = True) -> tuple[Path, Path, Path]:
    runtime_root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    day = "2026-07-02"
    _write_json(
        tmp_path / "configs" / "runtime_v2" / "capital_deployment.json",
        {
            "policy_version": "capital_deployment_v1",
            "evaluation_capital": 1000000,
            "max_exposure": 850000,
            "target_investment_ratio": 0.85,
        },
    )
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(runtime_root)})
    _write_json(
        run_dir / "run_state.json",
        {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": [day]},
    )
    _write_json(run_dir / "fresh_run_summary.json", {"schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "initial_cash": 1000000, "completed_days": [day]})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "status": "PASS"})
    _write_json(
        run_dir / "daily" / day / "current_valuation_refresh" / "current_valuation_manifest.json",
        {
            "artifact": {
                "candidate_current": {
                    "environment": "historical",
                    "runtime_evaluation_capital": 1000000,
                    "cash": 200000,
                    "buying_power": 200000,
                    "market_value": 850000,
                    "total_equity": 1050000,
                    "positions": [{"symbol": "11110"}],
                }
            }
        },
    )
    _write_json(run_dir / "daily" / day / "current_valuation_refresh" / "valuation_apply_evidence.json", {"status": "PASS"})
    _write_json(run_dir / "daily" / day / "strategy" / "portfolio_policy.json", {"cash_reserve_ratio": 0.2})
    _write_json(
        run_dir / "daily" / day / "strategy" / "position_sizing.json",
        {
            "portfolio_total_equity": 1050000,
            "aggregate_exposure_cap": 0.8,
            "positions": [
                {
                    "symbol": "11110",
                    "opportunity_row_id": "opp-11110",
                    "target_weight": 0.1,
                    "target_notional": 105000,
                    "incremental_buy_notional": 105000,
                    "reference_price": 1000,
                    "target_quantity_candidate": 100,
                    "quantity_delta_candidate": 100,
                },
                {
                    "symbol": "22220",
                    "opportunity_row_id": "opp-22220",
                    "target_weight": 0.0,
                    "target_notional": 0,
                    "incremental_buy_notional": 0,
                    "reference_price": 1000,
                    "target_quantity_candidate": 0,
                    "quantity_delta_candidate": 0,
                    "sizing_reason": "no_order_minimum_notional_unmet",
                },
            ],
        },
    )
    _write_json(
        run_dir / "daily" / day / "strategy" / "portfolio_construction.json",
        {
            "portfolio_members": [
                {"symbol": "11110", "target_membership": True, "opportunity_row_id": "opp-11110"},
                {"symbol": "22220", "target_membership": False, "opportunity_row_id": "opp-22220", "membership_reason": "member_not_selected"},
            ]
        },
    )
    if with_planning:
        _write_json(
            run_dir / "daily" / day / "strategy" / "runtime_planning.json",
            {
                "plans": [
                    {
                        "security_code": "11110",
                        "planning_intent": "BUY_NEW",
                        "planned_quantity": 100,
                        "opportunity_row_id": "opp-11110",
                        "opportunity_authority": {"opportunity_status": "PASS", "opportunity_eligibility": "BUY_ELIGIBLE"},
                    },
                    {
                        "security_code": "22220",
                        "planning_intent": "NO_ORDER",
                        "planned_quantity": 0,
                        "no_order_reason": "NO_ORDER_MINIMUM_NOTIONAL_UNMET",
                        "reason_codes": ["no_order_minimum_notional_unmet"],
                        "opportunity_row_id": "opp-22220",
                        "opportunity_authority": {"opportunity_status": "PASS", "opportunity_eligibility": "BUY_ELIGIBLE"},
                    },
                ]
            },
        )
    _write_json(run_dir / "daily" / day / "execution" / "submitted_order_authority.json", {"submit_action": "NO_ACTION", "submitted_order_count": 0})
    _write_json(run_dir / "daily" / day / "execution" / "fills.json", {"schema_version": "runtime_fill_observability.v1", "run_id": RUN_ID, "business_date": day, "fills": []})
    return runtime_root, evidence_root, run_dir


def test_phase25_a3_traces_dynamic_sizing_base_fixed_cap_and_avoids_confirmation(tmp_path: Path, monkeypatch) -> None:
    runner = load_runner()
    _, _, run_dir = _prepare_run(runner, tmp_path)
    monkeypatch.chdir(tmp_path)

    trace = build_capital_efficiency_trace(run_id=RUN_ID, run_dir=run_dir, business_date="2026-07-02", repo_root=tmp_path)

    assert validate_capital_efficiency_trace(trace)["status"] == "PASS"
    assert trace["schema_version"] == CAPITAL_TRACE_SCHEMA_VERSION
    assert trace["capital_authority_trace"]["position_sizing_capital_base"]["value"] == 1050000
    assert trace["capital_authority_trace"]["position_sizing_capital_base_matches_current_total_equity"]["value"] is True
    assert trace["capital_authority_trace"]["capital_deployment_evaluation_capital"]["value"] == 1000000
    assert trace["capital_authority_trace"]["capital_deployment_max_exposure"]["value"] == 850000
    assert trace["compound_reinvestment"]["status"] == "COMPOUND_REINVESTMENT_AMBIGUOUS"
    rejected = next(row for row in trace["symbol_traces"] if row["symbol"] == "22220")
    assert rejected["primary_binding_constraint"] == "MIN_NOTIONAL"
    assert rejected["binding_constraint_status"] == "AVAILABLE"


def test_phase25_a3_missing_planning_is_not_observable_and_not_guessed(tmp_path: Path, monkeypatch) -> None:
    runner = load_runner()
    _, _, run_dir = _prepare_run(runner, tmp_path, with_planning=False)
    monkeypatch.chdir(tmp_path)

    trace = build_capital_efficiency_trace(run_id=RUN_ID, run_dir=run_dir, business_date="2026-07-02", repo_root=tmp_path)

    assert trace["opportunity_pipeline"]["counts"]["planned_buy_count"]["status"] == "NOT_OBSERVABLE"
    assert all(row["binding_constraint_status"] in {"AVAILABLE", "NOT_OBSERVABLE"} for row in trace["symbol_traces"])
    assert trace["compound_reinvestment"]["status"] != "COMPOUND_REINVESTMENT_CONFIRMED"


def test_phase25_a3_cli_materializes_json_and_is_deterministic(tmp_path: Path, capsys) -> None:
    runner = load_runner()
    runtime_root, evidence_root, _ = _prepare_run(runner, tmp_path)
    output_root = tmp_path / "reports" / "performance_evaluations"

    args = [
        "capital-trace",
        "--run-id",
        RUN_ID,
        "--business-date",
        "2026-07-02",
        "--runtime-root",
        str(runtime_root),
        "--evidence-root",
        str(evidence_root),
        "--performance-evidence-root",
        str(output_root),
        "--json",
    ]
    first = call_main(runner, args, capsys)
    path = output_root / RUN_ID / "daily" / "2026-07-02" / "capital_efficiency_trace.json"
    first_payload = json.loads(path.read_text(encoding="utf-8"))
    second = call_main(runner, args, capsys)
    second_payload = json.loads(path.read_text(encoding="utf-8"))

    assert first["status"] == "PASS"
    assert second["status"] == "PASS"
    assert first_payload == second_payload
    assert first_payload["schema_validation"]["status"] == "PASS"
    assert first_payload["source_artifact_refs"]
    assert first_payload["temporal_safety"]["runtime_evidence_mutated"] is False
