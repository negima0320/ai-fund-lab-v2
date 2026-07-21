from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-summary-fixture"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _make_summary_fixture(
    runner,
    tmp_path: Path,
    *,
    negative_return: bool = True,
    missing_attribution: bool = False,
    lifecycle_mismatch: bool = False,
) -> tuple[Path, Path]:
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    business_days = ["2026-07-01"]
    pm_dir = root / "runtime_state" / "position_management" / "2026-07-01"
    sell_dir = root / "runtime_state" / "sell_pipeline" / "2026-07-01"
    morning_dir = root / "runtime_state" / "morning_pipeline" / "2026-07-01"
    pm_dir.mkdir(parents=True)
    sell_dir.mkdir(parents=True)
    morning_dir.mkdir(parents=True)
    _write_json(
        pm_dir / "position_management_decisions.json",
        {
            "business_date": "2026-07-01",
            "decisions": [
                {
                    "business_date": "2026-07-01",
                    "symbol": "11110",
                    "decision": "HOLD",
                    "runtime_action": "NO_SELL_ORDER",
                    "reason": "positive_expected_edge|downside_risk_contained",
                    "decision_id": "pm-hold",
                },
                {
                    "business_date": "2026-07-01",
                    "symbol": "22220",
                    "decision": "REDUCE",
                    "runtime_action": "SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING",
                    "reason": "peak_drawdown_warning",
                    "decision_id": "pm-reduce",
                },
                {
                    "business_date": "2026-07-01",
                    "symbol": "33330",
                    "decision": "EXIT",
                    "runtime_action": "SELL_FULL_POSITION",
                    "reason": "hard_stop_current_return|profit_retention_break",
                    "decision_id": "pm-exit",
                },
                {
                    "business_date": "2026-07-01",
                    "symbol": "44440",
                    "decision": "ADD",
                    "runtime_action": "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE",
                    "reason": "strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging; ADD is outside SELL Planning scope",
                    "decision_id": "pm-add",
                },
            ],
        },
    )
    _write_json(
        morning_dir / "order_plan.json",
        {"business_date": "2026-07-01", "items": [{"symbol": "22220", "side": "BUY", "quantity": 10.0}]},
    )
    sell_items = [] if lifecycle_mismatch else [
        {
            "symbol": "22220",
            "side": "SELL",
            "quantity": 5.0,
            "quantity_contract": {
                "source_decision": "REDUCE",
                "reduce_intensity": "MEDIUM",
                "position_quantity_before": 10.0,
                "sellable_quantity": 10.0,
                "target_reduce_ratio": 0.5,
                "expected_remaining_quantity": 5.0,
                "final_sell_quantity": 5.0,
                "quantity_contract_version": "runtime_v2_pm_reduce_quantity_v1",
                "status": "PASS",
            },
        },
        {
            "symbol": "33330",
            "side": "SELL",
            "quantity": 10.0,
            "quantity_contract": {
                "source_decision": "EXIT",
                "position_quantity_before": 10.0,
                "sellable_quantity": 10.0,
                "expected_remaining_quantity": 0.0,
                "final_sell_quantity": 10.0,
                "quantity_contract_version": "runtime_v2_pm_exit_full_quantity_v1",
                "status": "PASS",
            },
        },
    ]
    _write_json(sell_dir / "order_plan.json", {"business_date": "2026-07-01", "items": sell_items})
    orders = [
        {"record_type": "order", "dedup_key": "runtime_v2_submit:buy", "business_date": "2026-07-01", "pending_item_id": "buy-1", "side": "BUY", "symbol": "22220", "quantity": 10.0},
        {"record_type": "order", "dedup_key": "runtime_v2_submit:sell-r", "business_date": "2026-07-01", "pending_item_id": "sell-r", "side": "SELL", "symbol": "22220", "quantity": 5.0},
        {"record_type": "order", "dedup_key": "runtime_v2_submit:sell-e", "business_date": "2026-07-01", "pending_item_id": "sell-e", "side": "SELL", "symbol": "33330", "quantity": 10.0},
        {"record_type": "order", "dedup_key": "sha256:execution-equivalent", "business_date": "", "pending_item_id": "", "side": "SELL", "symbol": "22220", "quantity": 5.0},
    ]
    executions = [
        {"record_type": "execution", "business_date": "2026-07-01", "side": "BUY", "symbol": "22220", "filled_quantity": 10.0, "price": 10.0, "record_id": "buy-r"},
        {"record_type": "execution", "business_date": "2026-07-01", "side": "BUY", "symbol": "33330", "filled_quantity": 10.0, "price": 20.0, "record_id": "buy-e"},
        {"record_type": "execution", "business_date": "2026-07-01", "side": "SELL", "symbol": "22220", "filled_quantity": 5.0, "price": 8.0, "execution_id": "sell-r"},
        {"record_type": "execution", "business_date": "2026-07-01", "side": "SELL", "symbol": "33330", "filled_quantity": 10.0, "price": 25.0, "execution_id": "sell-e"},
    ]
    if missing_attribution:
        executions.append({"record_type": "execution", "business_date": "2026-07-01", "side": "SELL", "symbol": "99990", "filled_quantity": 1.0, "price": 1.0, "execution_id": "sell-unmatched"})
    _write_jsonl(root / "persistent_ledger" / "orders.jsonl", orders)
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", executions)
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "cash": 900.0,
            "market_value": 50.0 if negative_return else 150.0,
            "total_equity": 950.0 if negative_return else 1050.0,
            "realized_pnl": 40.0,
            "new_unrealized_pnl": 10.0,
            "positions": [
                {"symbol": "22220", "quantity": 5.0, "average_price": 10.0, "current_price": 10.0, "market_value": 50.0, "unrealized_pnl": 0.0, "valuation_as_of": "2026-07-01"}
            ],
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"schema_version": "1", "state": "EMPTY", "status": "EMPTY", "items": []})
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(root)})
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": business_days})
    _write_json(run_dir / "fresh_run_summary.json", {"schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "date_from": "2026-07-01", "date_to": "2026-07-01", "initial_cash": 1000.0, "external_effect_policy": {"broker_write": False, "external_delivery": False, "jquants_fetch": False, "tachibana_api": False}})
    _write_json(run_dir / "daily" / "2026-07-01" / "submit" / "external_effect_audit.json", {"status": "PASS"})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "status": "PASS", "final_judgment": "PASS", "final_state_hashes": runner.state_hashes(root)})
    return root, evidence_root


def test_phase19_bv_summarize_known_pass_run_json_schema_and_distribution(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)
    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["schema_version"] == "runtime_test_summary_v1"
    assert payload["runtime_judgment"] == "PASS"
    assert payload["performance_judgment"] == "NEGATIVE_RETURN_OBSERVED"
    assert payload["strategy_judgment"] == "NOT_EVALUATED"
    assert payload["pm_decisions"]["decision_distribution"] == {"ADD": 1, "EXIT": 1, "HOLD": 1, "REDUCE": 1}
    assert payload["reduce_exit"]["sell_plan_source_decision_distribution"] == {"EXIT": 1, "REDUCE": 1}
    assert payload["trading"]["submitted_order_distribution"] == {"BUY": 1, "SELL": 2}
    assert payload["trading"]["submitted_order_double_count_prevention"]["ignored_execution_equivalent_order_records"] == 1
    assert payload["trading"]["execution_distribution"] == {"BUY": 2, "SELL": 2}
    assert len(payload["current_positions"]) == 1
    assert len(payload["trade_attribution"]) == 2
    assert payload["lifecycle_consistency"]["status"] == "PASS"
    assert payload["external_effects"]["historical_external_effects_disabled"] is True


def test_phase19_bv_summarize_unknown_run_fails_precondition(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    payload = call_main(runner, ["summarize", "--run-id", "missing-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports" / "runtime_tests")], capsys)
    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
    assert payload["status"] == "PRECONDITION_FAILURE"


def test_phase19_bv_summarize_human_output_contains_required_sections(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)
    exit_code = runner.main(["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)])
    captured = capsys.readouterr()
    assert exit_code == runner.EXIT_PASS
    for section in [
        "Run Summary",
        "External Effect Summary",
        "Performance Summary",
        "PM Decision Summary",
        "BUY / SELL Summary",
        "REDUCE / EXIT Summary",
        "Trade Attribution",
        "Current Positions",
        "Lifecycle Consistency",
        "Review / Block Summary",
        "Operator Judgment",
    ]:
        assert section in captured.out


def test_phase19_bv_trade_attribution_unavailable_is_review_required(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path, missing_attribution=True)
    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    assert payload["_exit_code"] == runner.EXIT_REVIEW_REQUIRED
    assert any(finding["reason"] == "REVIEW_REQUIRED_TRADE_LEVEL_REALIZED_PNL_NOT_TRACEABLE" for finding in payload["findings"])


def test_phase19_bv_lifecycle_mismatch_is_review_required(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path, lifecycle_mismatch=True)
    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    assert payload["_exit_code"] == runner.EXIT_REVIEW_REQUIRED
    assert payload["lifecycle_consistency"]["status"] == "REVIEW_REQUIRED"
    assert any(finding["reason"] == "LIFECYCLE_CONSISTENCY_REVIEW_REQUIRED" for finding in payload["findings"])


def test_phase19_bv_write_evidence_is_summary_only_and_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)
    before = runner.directory_hash(root)
    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--write-evidence"], capsys)
    after = runner.directory_hash(root)
    assert payload["_exit_code"] == runner.EXIT_PASS
    assert before == after
    evidence_path = Path(payload["evidence_path"])
    assert evidence_path.parent == evidence_root / "summaries"
    assert (evidence_path / "summary.json").exists()
    assert (evidence_path / "summary.txt").exists()


def test_phase19_by_summarize_excludes_shared_sell_plans_outside_run_period(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    for date_key in ["2026-06-18", "2026-06-19", "2026-06-22", "2026-06-30"]:
        _write_json(
            root / "runtime_state" / "sell_pipeline" / date_key / "order_plan.json",
            {
                "business_date": date_key,
                "items": [
                    {
                        "business_date": date_key,
                        "side": "SELL",
                        "symbol": "11110",
                        "quantity": 10,
                        "quantity_contract": {"source_decision": "EXIT"},
                    }
                ],
            },
        )
    _write_json(root / "runtime_state" / "morning_pipeline" / "2026-07-14" / "order_plan.json", {"business_date": "2026-07-14", "items": [{"business_date": "2026-07-14", "side": "BUY", "symbol": "22220", "quantity": 1}]})
    _write_jsonl(root / "persistent_ledger" / "orders.jsonl", [{"record_type": "order", "dedup_key": "runtime_v2_submit:buy", "business_date": "2026-07-14", "pending_item_id": "buy-1", "side": "BUY", "symbol": "22220", "quantity": 1}])
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", [{"record_type": "execution", "business_date": "2026-07-14", "side": "BUY", "symbol": "22220", "filled_quantity": 1, "price": 100, "record_id": "buy-1"}])
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 900.0, "market_value": 100.0, "total_equity": 1000.0, "positions": [{"symbol": "22220", "quantity": 1}]})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "items": []})
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(root)})
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": ["2026-07-14"]})
    _write_json(run_dir / "fresh_run_summary.json", {"schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "date_from": "2026-07-14", "date_to": "2026-07-14", "initial_cash": 1000.0, "external_effect_policy": {"broker_write": False, "external_delivery": False, "jquants_fetch": False, "tachibana_api": False}})
    _write_json(run_dir / "daily" / "2026-07-14" / "sell_planning" / "position_management_evidence.json", {"status": "NO_POSITION", "pm_decision_count": 0, "pm_hold_count": 0, "pm_add_count": 0, "pm_reduce_count": 0, "pm_exit_count": 0, "runtime_test_run_id": RUN_ID})
    _write_json(run_dir / "daily" / "2026-07-14" / "sell_planning" / "sell_planning_manifest.json", {"manifest": {"business_date": "2026-07-14", "pm_decision_count": 0, "pm_reduce_count": 0, "pm_exit_count": 0, "runtime_test_run_id": RUN_ID, "runtime_test_evidence_root": str(run_dir)}})
    _write_json(run_dir / "daily" / "2026-07-14" / "submit" / "external_effect_audit.json", {"status": "PASS"})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "status": "PASS", "final_judgment": "PASS", "final_state_hashes": runner.state_hashes(root)})

    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["runtime_judgment"] == "PASS"
    assert payload["pm_decisions"]["decision_count"] == 0
    assert payload["reduce_exit"]["sell_plan_source_decision_distribution"] == {}
    assert payload["trading"]["sell_plan_count"] == 0
    assert payload["trading"]["submitted_order_distribution"] == {"BUY": 1}
    assert payload["trading"]["execution_distribution"] == {"BUY": 1}
    assert payload["lifecycle_consistency"]["checks"]["SELL_PLAN_TO_SUBMIT"] is True


def test_phase19_by_summarize_missing_in_period_sell_linkage_is_review_required(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path, lifecycle_mismatch=True)

    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    assert payload["_exit_code"] == runner.EXIT_REVIEW_REQUIRED
    assert payload["pm_decisions"]["exit_count"] == 1
    assert payload["pm_decisions"]["reduce_count"] == 1
    assert payload["trading"]["sell_plan_count"] == 0
    assert payload["lifecycle_consistency"]["checks"]["PM_EXIT_TO_SELL_PLAN"] is False
    assert payload["lifecycle_consistency"]["status"] == "REVIEW_REQUIRED"
