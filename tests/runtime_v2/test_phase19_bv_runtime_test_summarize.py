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
    assert payload["summary_scope_schema_version"] == "runtime_test_summary_v2"
    assert payload["scope"] == "full"
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


def test_phase20_h_summarize_scope_parser_and_json_sections(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)

    expectations = {
        "overview": ("overview", "performance_scope", "positions_scope", "lifecycle_scope"),
        "performance": ("performance_scope", "overview", "positions_scope", "lifecycle_scope"),
        "positions": ("positions_scope", "overview", "performance_scope", "lifecycle_scope"),
        "lifecycle": ("lifecycle_scope", "overview", "performance_scope", "positions_scope"),
        "full": ("overview", "performance_scope", "positions_scope", "lifecycle_scope"),
    }
    for scope, keys in expectations.items():
        payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", scope], capsys)
        assert payload["_exit_code"] == runner.EXIT_PASS
        assert payload["scope"] == scope
        selected = keys[0]
        assert payload[selected] is not None
        if scope != "full":
            for omitted in keys[1:]:
                assert payload[omitted] is None
        assert payload["run"]["event_collection_authority"] == "RUN_SCOPED_EVIDENCE_WITH_COMPLETED_BUSINESS_DAY_FILTER"
        assert payload["authority"]["shared_runtime_event_authority"] == "PROHIBITED"


def test_phase20_h_summarize_scope_human_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)
    expected_titles = {
        "overview": "Run Overview",
        "performance": "Performance Summary",
        "positions": "Position Campaign Summary",
        "lifecycle": "Position Lifecycle Summary",
        "full": "Run Summary",
    }
    for scope, title in expected_titles.items():
        exit_code = runner.main(["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", scope])
        captured = capsys.readouterr()
        assert exit_code == runner.EXIT_PASS
        assert title in captured.out
    assert "POST_HOC_ATTRIBUTION_ONLY" in call_main(
        runner,
        ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "lifecycle"],
        capsys,
    )["lifecycle_scope"]["post_hoc_policy"]


def test_phase20_h_summarize_write_evidence_records_scope(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)

    payload = call_main(
        runner,
        ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "performance", "--write-evidence"],
        capsys,
    )

    evidence = json.loads((Path(payload["evidence_path"]) / "summary.json").read_text(encoding="utf-8"))
    assert evidence["scope"] == "performance"
    assert evidence["performance_scope"] is not None
    assert evidence["overview"] is None
    assert evidence["contract_versions"]["performance_metric_contract"] == "phase20_b_performance_metric_contract.v1"


def test_phase20_h_missing_performance_metrics_are_explicit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _make_summary_fixture(runner, tmp_path)

    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "performance"], capsys)

    metrics = payload["performance_scope"]["metrics"]
    assert metrics["Benchmark"]["status"] == "MISSING"
    assert metrics["Sector"]["status"] == "MISSING"
    assert metrics["Daily Equity Curve"]["status"] == "NOT_AVAILABLE"


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
    assert "PM REDUCE Lifecycle" in captured.out
    assert "executable=" in captured.out
    assert "non_executable=" in captured.out
    assert "unresolved=" in captured.out


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


def _phase20_p_lifecycle_payload(runner, *, pm_reduce_records: list[dict], reduce_plans: list[dict], non_executable: list[dict], exit_count: int = 0, exit_plan_count: int = 0) -> dict:
    pm_records = [
        {
            "business_date": row.get("business_date", "2026-07-01"),
            "symbol": row.get("symbol", "22220"),
            "decision": "REDUCE",
            "decision_id": row.get("decision_id", f"pm-reduce-{idx}"),
            "position_campaign_id": row.get("position_campaign_id", f"pc-{idx}"),
        }
        for idx, row in enumerate(pm_reduce_records, start=1)
    ]
    return runner._summarize_lifecycle(
        pm={"reduce_count": len(pm_records), "exit_count": exit_count, "decision_records": pm_records},
        trading={
            "sell_plan_count": len(reduce_plans) + exit_plan_count,
            "submitted_order_distribution": {"SELL": len(reduce_plans) + exit_plan_count},
            "execution_distribution": {"SELL": len(reduce_plans) + exit_plan_count},
        },
        reduce_exit={
            "reduce_sell_plan_count": len(reduce_plans),
            "exit_sell_plan_count": exit_plan_count,
            "items": reduce_plans,
            "non_executable_items": non_executable,
        },
        current_state={"positions": []},
        pending_state={"state": "EMPTY", "items": []},
    )


def _phase20_p_reduce_plan(*, symbol: str, business_date: str = "2026-07-01", decision_id: str = "") -> dict:
    return {
        "business_date": business_date,
        "symbol": symbol,
        "source_decision": "REDUCE",
        "source_decision_id": decision_id,
        "quantity": 100.0,
    }


def _phase20_p_non_executable_reduce(*, symbol: str, business_date: str = "2026-07-01", decision_id: str = "", reason: str = "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY", after: float = 300.0) -> dict:
    return {
        "business_date": business_date,
        "symbol": symbol,
        "source_decision": "REDUCE",
        "source_decision_id": decision_id,
        "execution_feasibility_status": "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
        "reason": reason,
        "status": "NOT_EXECUTABLE",
        "effective_action": "NO_SELL_ORDER",
        "pending_order_generated": False,
        "runtime_continuation_status": "PASS",
        "position_lifecycle_event": "REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY",
        "position_quantity_before": 300.0,
        "position_quantity_after": after,
        "expected_remaining_quantity": 300.0,
        "final_sell_quantity": 0.0,
        "rounded_executable_quantity": 0.0,
    }


def test_phase20_p_reduce_lifecycle_all_executable_passes() -> None:
    runner = load_runner()
    lifecycle = _phase20_p_lifecycle_payload(
        runner,
        pm_reduce_records=[{"symbol": "11110", "decision_id": "pm-r1"}, {"symbol": "22220", "decision_id": "pm-r2"}],
        reduce_plans=[_phase20_p_reduce_plan(symbol="11110", decision_id="pm-r1"), _phase20_p_reduce_plan(symbol="22220", decision_id="pm-r2")],
        non_executable=[],
        exit_count=1,
        exit_plan_count=1,
    )
    assert lifecycle["status"] == "PASS"
    assert lifecycle["executable_reduce_sell_plan_count"] == 2
    assert lifecycle["non_executable_reduce_terminal_count"] == 0
    assert lifecycle["checks"]["PM_EXIT_TO_SELL_PLAN"] is True
    assert lifecycle["checks"]["SELL_PLAN_TO_SUBMIT"] is True
    assert lifecycle["checks"]["SELL_SUBMIT_TO_EXECUTION"] is True


def test_phase20_p_reduce_lifecycle_mixed_executable_and_terminal_passes() -> None:
    runner = load_runner()
    pm_records = [{"symbol": f"{idx}1110", "decision_id": f"pm-r{idx}"} for idx in range(1, 11)]
    plans = [_phase20_p_reduce_plan(symbol=f"{idx}1110", decision_id=f"pm-r{idx}") for idx in range(1, 7)]
    terminals = [_phase20_p_non_executable_reduce(symbol=f"{idx}1110", decision_id=f"pm-r{idx}") for idx in range(7, 11)]
    lifecycle = _phase20_p_lifecycle_payload(runner, pm_reduce_records=pm_records, reduce_plans=plans, non_executable=terminals)
    assert lifecycle["status"] == "PASS"
    assert lifecycle["pm_reduce_count"] == 10
    assert lifecycle["executable_reduce_sell_plan_count"] == 6
    assert lifecycle["non_executable_reduce_terminal_count"] == 4
    assert lifecycle["unresolved_reduce_count"] == 0
    assert lifecycle["conflicting_reduce_count"] == 0


def test_phase20_p_reduce_lifecycle_missing_outcome_is_review_required() -> None:
    runner = load_runner()
    lifecycle = _phase20_p_lifecycle_payload(runner, pm_reduce_records=[{"symbol": "11110", "decision_id": "pm-r1"}], reduce_plans=[], non_executable=[])
    assert lifecycle["status"] == "REVIEW_REQUIRED"
    assert lifecycle["unresolved_reduce_count"] == 1


def test_phase20_p_reduce_lifecycle_conflicting_plan_and_terminal_is_review_required() -> None:
    runner = load_runner()
    lifecycle = _phase20_p_lifecycle_payload(
        runner,
        pm_reduce_records=[{"symbol": "11110", "decision_id": "pm-r1"}],
        reduce_plans=[_phase20_p_reduce_plan(symbol="11110", decision_id="pm-r1")],
        non_executable=[_phase20_p_non_executable_reduce(symbol="11110", decision_id="pm-r1")],
    )
    assert lifecycle["status"] == "REVIEW_REQUIRED"
    assert lifecycle["conflicting_reduce_count"] == 1


def test_phase20_p_reduce_lifecycle_invalid_terminal_reason_is_review_required() -> None:
    runner = load_runner()
    lifecycle = _phase20_p_lifecycle_payload(
        runner,
        pm_reduce_records=[{"symbol": "11110", "decision_id": "pm-r1"}],
        reduce_plans=[],
        non_executable=[_phase20_p_non_executable_reduce(symbol="11110", decision_id="pm-r1", reason="UNKNOWN_REASON")],
    )
    assert lifecycle["status"] == "REVIEW_REQUIRED"
    assert lifecycle["unresolved_reduce_count"] == 1


def test_phase20_p_reduce_lifecycle_non_executable_position_mutation_is_review_required() -> None:
    runner = load_runner()
    lifecycle = _phase20_p_lifecycle_payload(
        runner,
        pm_reduce_records=[{"symbol": "11110", "decision_id": "pm-r1"}],
        reduce_plans=[],
        non_executable=[_phase20_p_non_executable_reduce(symbol="11110", decision_id="pm-r1", after=200.0)],
    )
    assert lifecycle["status"] == "REVIEW_REQUIRED"
    assert lifecycle["unresolved_reduce_count"] == 1


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


def test_phase23_ag_summarize_excludes_current_non_executable_sell_when_run_scoped_pm_is_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    _write_json(
        root / "runtime_state" / "sell_pipeline" / "2026-07-06" / "order_plan.json",
        {
            "business_date": "2026-07-06",
            "status": "NO_ACTION",
            "reason": "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY",
            "items": [],
            "non_executable_sell_decisions": [
                {
                    "business_date": "2026-07-06",
                    "symbol": "43780",
                    "source_decision_id": "pm-2026-07-06-43780-reduce",
                    "quantity_contract": {
                        "source_decision": "REDUCE",
                        "reason": "REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY",
                        "status": "NOT_EXECUTABLE",
                        "effective_action": "NO_SELL_ORDER",
                        "pending_order_generated": False,
                        "runtime_continuation_status": "PASS",
                        "position_lifecycle_event": "REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY",
                        "position_quantity_before": 300.0,
                        "position_quantity_after": 300.0,
                        "expected_remaining_quantity": 300.0,
                        "final_sell_quantity": 0.0,
                        "rounded_executable_quantity": 0.0,
                        "execution_feasibility_status": "NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY",
                    },
                }
            ],
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "items": []})
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1000.0, "market_value": 0.0, "total_equity": 1000.0, "positions": []})
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(root), "requested_business_days": 1, "resolved_business_day_count": 1, "window_resolution_status": "PASS", "business_dates": [{"business_date": "2026-07-06"}]})
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": ["2026-07-06"]})
    _write_json(run_dir / "fresh_run_summary.json", {"schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "date_from": "2026-07-06", "date_to": "2026-07-06", "initial_cash": 1000.0, "external_effect_policy": {"broker_write": False, "external_delivery": False, "jquants_fetch": False, "tachibana_api": False}})
    _write_json(run_dir / "daily" / "2026-07-06" / "sell_planning" / "position_management_evidence.json", {"status": "NO_POSITION", "pm_decision_count": 0, "pm_hold_count": 0, "pm_add_count": 0, "pm_reduce_count": 0, "pm_exit_count": 0, "runtime_test_run_id": RUN_ID})
    _write_json(run_dir / "daily" / "2026-07-06" / "sell_planning" / "sell_planning_manifest.json", {"manifest": {"business_date": "2026-07-06", "pm_decision_count": 0, "pm_reduce_count": 0, "pm_exit_count": 0, "runtime_test_run_id": RUN_ID, "runtime_test_evidence_root": str(run_dir)}})
    _write_json(run_dir / "daily" / "2026-07-06" / "position_management" / "pm_decisions.json", {"run_id": RUN_ID, "business_date": "2026-07-06", "decisions": [], "pm_decision_count": 0})
    _write_json(run_dir / "daily" / "2026-07-06" / "execution" / "fills.json", {"run_id": RUN_ID, "business_date": "2026-07-06", "fills": []})
    _write_json(run_dir / "daily" / "2026-07-06" / "positions" / "position_campaigns.json", {"run_id": RUN_ID, "business_date": "2026-07-06", "position_campaigns": []})
    _write_json(run_dir / "daily" / "2026-07-06" / "submit" / "external_effect_audit.json", {"status": "PASS"})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": RUN_ID, "status": "PASS", "final_judgment": "PASS", "final_state_hashes": runner.state_hashes(root)})

    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    assert payload["_exit_code"] == runner.EXIT_PASS
    assert payload["pm_decisions"]["decision_count"] == 0
    assert payload["reduce_exit"]["non_executable_reduce_terminal_count"] == 0
    assert payload["lifecycle_consistency"]["checks"]["PM_REDUCE_TO_PARTIAL_SELL_PLAN"] is True
    assert payload["lifecycle_consistency"]["status"] == "PASS"
    assert payload["summary_authority_matrix"]["non_executable_sell_decisions"]["authority"] == "RUN_SCOPED_EVIDENCE"
    assert payload["summary_authority_matrix"]["non_executable_sell_decisions"]["fallback_used"] is False
    assert payload["independent_acceptance"]["summary_evidence_isolation_judgment"] == "PASS"


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
