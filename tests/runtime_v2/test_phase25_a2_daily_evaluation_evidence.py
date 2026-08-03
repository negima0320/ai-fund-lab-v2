from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.performance_evaluation import (
    DAILY_EVALUATION_EVIDENCE_SCHEMA_VERSION,
    build_daily_evaluation_evidence,
    validate_daily_evaluation_evidence,
)
from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-phase25-a2-fixture"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _prepare_run(runner, tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    day = "2026-07-02"

    _write_json(
        run_dir / "plan.json",
        {
            "schema_version": runner.PLAN_SCHEMA_VERSION,
            "run_id": RUN_ID,
            "profile_id": "historical-smoke",
            "runtime_root": str(runtime_root),
        },
    )
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": RUN_ID,
            "profile_id": "historical-smoke",
            "status": "COMPLETED",
            "completed_business_days": [day],
            "source_baseline": {"source_commit": "abc123", "source_dirty": False},
        },
    )
    _write_json(
        run_dir / "fresh_run_summary.json",
        {
            "schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION,
            "run_id": RUN_ID,
            "profile_id": "historical-smoke",
            "initial_cash": 1000000,
            "completed_days": [day],
        },
    )
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "status": "PASS"})
    _write_json(
        run_dir / "daily" / day / "current_valuation_refresh" / "current_valuation_manifest.json",
        {
            "artifact": {
                "candidate_current": {
                    "schema_version": "runtime_v2_current_temporal_v1",
                    "environment": "historical",
                    "runtime_evaluation_capital": 1000000,
                    "cash": 200000,
                    "buying_power": 200000,
                    "market_value": 850000,
                    "total_equity": 1050000,
                    "positions": [{"symbol": "11110"}, {"symbol": "22220"}],
                }
            }
        },
    )
    _write_json(
        run_dir / "daily" / day / "current_valuation_refresh" / "valuation_apply_evidence.json",
        {"status": "PASS"},
    )
    _write_json(
        run_dir / "daily" / day / "strategy" / "portfolio_policy.json",
        {"schema_version": "portfolio_policy.v1", "cash_reserve_ratio": 0.2},
    )
    _write_json(
        run_dir / "daily" / day / "strategy" / "position_sizing.json",
        {"schema_version": "position_sizing.v1", "aggregate_exposure_cap": 0.8},
    )
    _write_json(
        run_dir / "daily" / day / "strategy" / "runtime_planning.json",
        {
            "schema_version": "runtime_planning.v1",
            "plans": [
                {
                    "security_code": "11110",
                    "planning_intent": "BUY_NEW",
                    "order_side_intent": "BUY",
                    "planned_quantity": 100,
                    "opportunity_authority": {"opportunity_status": "PASS", "opportunity_eligibility": "BUY_ELIGIBLE"},
                },
                {
                    "security_code": "22220",
                    "planning_intent": "NO_ORDER",
                    "no_order_reason": "NO_ORDER_MINIMUM_NOTIONAL_UNMET",
                    "reason_codes": ["no_order_minimum_notional_unmet"],
                    "opportunity_authority": {"opportunity_status": "PASS", "opportunity_eligibility": "BUY_ELIGIBLE"},
                },
                {
                    "security_code": "33330",
                    "planning_intent": "NO_ACTION",
                    "planning_reason": "safety_constraint_triggered",
                    "opportunity_authority": {"opportunity_status": "PASS", "opportunity_eligibility": "BUY_ELIGIBLE"},
                },
            ],
        },
    )
    _write_json(
        run_dir / "daily" / day / "execution" / "submitted_order_authority.json",
        {"status": "PASS", "submit_action": "SUBMIT", "execution_references": [{"side": "BUY"}]},
    )
    _write_json(
        run_dir / "daily" / day / "execution" / "fills.json",
        {
            "schema_version": "runtime_fill_observability.v1",
            "run_id": RUN_ID,
            "business_date": day,
            "fills": [
                {"side": "BUY", "symbol": "11110", "quantity": 100, "execution_price": 1000, "gross_notional": {"value": 100000, "status": "DERIVABLE_EXACT"}}
            ],
        },
    )
    _write_json(
        run_dir / "daily" / day / "benchmark" / "benchmark_snapshot.json",
        {"schema_version": "benchmark_snapshot_observability.v1", "status": "MISSING", "benchmark_source": "NOT_CONFIRMED"},
    )
    return runtime_root, evidence_root, run_dir


def test_phase25_a2_builds_daily_evaluation_evidence_with_opportunity_pipeline(tmp_path: Path) -> None:
    runner = load_runner()
    _, _, run_dir = _prepare_run(runner, tmp_path)

    payload = build_daily_evaluation_evidence(run_id=RUN_ID, run_dir=run_dir, business_date="2026-07-02")
    validation = validate_daily_evaluation_evidence(payload)

    assert validation["status"] == "PASS"
    assert payload["schema_version"] == DAILY_EVALUATION_EVIDENCE_SCHEMA_VERSION
    assert payload["capital"]["cash"]["value"] == 200000
    assert payload["capital"]["total_equity"]["value"] == 1050000
    assert payload["capital"]["cash_ratio"]["value"] == 200000 / 1050000
    assert payload["capital"]["gross_exposure_ratio"]["value"] == 850000 / 1050000
    assert payload["opportunity_utilization"]["generated_opportunity_count"] == {"value": 3, "status": "AVAILABLE"}
    assert payload["opportunity_utilization"]["eligible_opportunity_count"] == {"value": 3, "status": "DERIVED"}
    assert payload["opportunity_utilization"]["planned_buy_count"] == {"value": 1, "status": "DERIVED"}
    assert payload["opportunity_utilization"]["submitted_buy_count"] == {"value": 1, "status": "DERIVED"}
    assert payload["opportunity_utilization"]["executed_buy_count"] == {"value": 1, "status": "DERIVED"}
    reject_counts = payload["opportunity_utilization"]["reject_reason_counts"]
    assert reject_counts["capital_constraint_count"]["value"] == 1
    assert reject_counts["safety_constraint_count"]["value"] == 1
    assert reject_counts["planning_rejection_count"]["value"] == 2
    assert reject_counts["unknown_constraint_count"]["value"] == 0
    assert payload["benchmark"]["status"] == "MISSING"


def test_phase25_a2_materializes_daily_evidence_from_runtime_test_cli(tmp_path: Path, capsys) -> None:
    runner = load_runner()
    runtime_root, evidence_root, _ = _prepare_run(runner, tmp_path)
    output_root = tmp_path / "reports" / "performance_evaluations"

    result = call_main(
        runner,
        [
            "daily-evidence",
            "--run-id",
            RUN_ID,
            "--runtime-root",
            str(runtime_root),
            "--evidence-root",
            str(evidence_root),
            "--performance-evidence-root",
            str(output_root),
            "--json",
        ],
        capsys,
    )

    output_path = output_root / RUN_ID / "daily" / "2026-07-02" / "daily_evaluation_evidence.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["read_only_runtime"] is True
    assert result["strategy_mutation"] is False
    assert result["runtime_mutation"] is False
    assert payload["schema_validation"]["status"] == "PASS"


def test_phase25_a2_uses_not_observable_without_guessing_missing_opportunity_sources(tmp_path: Path) -> None:
    runner = load_runner()
    _, _, run_dir = _prepare_run(runner, tmp_path)
    planning_path = run_dir / "daily" / "2026-07-02" / "strategy" / "runtime_planning.json"
    planning_path.unlink()

    payload = build_daily_evaluation_evidence(run_id=RUN_ID, run_dir=run_dir, business_date="2026-07-02")

    assert payload["opportunity_utilization"]["status"] == "NOT_OBSERVABLE"
    assert payload["opportunity_utilization"]["generated_opportunity_count"] == {"value": "NOT_OBSERVABLE", "status": "NOT_OBSERVABLE"}
    assert payload["opportunity_utilization"]["reject_reason_counts"]["unknown_constraint_count"] == {"value": "NOT_OBSERVABLE", "status": "NOT_OBSERVABLE"}
