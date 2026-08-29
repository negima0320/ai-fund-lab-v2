from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-phase20j-fixture"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _prepare_fixture(runner, tmp_path: Path) -> tuple[Path, Path, Path]:
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    business_date = "2026-07-02"
    _write_json(
        root / "runtime_state" / "morning_pipeline" / business_date / "order_plan.json",
        {
            "items": [
                {"symbol": "11110", "side": "BUY", "quantity": 10, "price": 100, "pending_item_id": "buy-1", "order_plan_item_id": "plan-buy-1"},
                {"symbol": "11110", "side": "BUY", "quantity": 5, "price": 110, "pending_item_id": "buy-2", "order_plan_item_id": "plan-buy-2"},
            ]
        },
    )
    _write_json(
        root / "runtime_state" / "sell_pipeline" / business_date / "order_plan.json",
        {
            "items": [
                {
                    "symbol": "11110",
                    "side": "SELL",
                    "quantity": 8,
                    "pending_item_id": "sell-1",
                    "order_plan_item_id": "plan-sell-1",
                    "quantity_contract": {"source_decision": "REDUCE", "source_decision_id": "pm-reduce", "final_sell_quantity": 8},
                },
                {
                    "symbol": "11110",
                    "side": "SELL",
                    "quantity": 7,
                    "pending_item_id": "sell-2",
                    "order_plan_item_id": "plan-sell-2",
                    "quantity_contract": {"source_decision": "EXIT", "source_decision_id": "pm-exit", "final_sell_quantity": 7},
                },
            ]
        },
    )
    _write_json(
        root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json",
        {
            "decisions": [
                {
                    "business_date": business_date,
                    "symbol": "11110",
                    "decision_id": "pm-reduce",
                    "decision": "REDUCE",
                    "reason": "peak_drawdown_warning",
                    "runtime_position_quantity": 15,
                    "runtime_sell_quantity": 8,
                    "current_price": 120,
                    "unrealized_pnl": 250,
                    "confidence": 0.62,
                    "generated_at": "2026-07-02T00:00:00+00:00",
                }
            ]
        },
    )
    _write_jsonl(
        root / "persistent_ledger" / "executions.jsonl",
        [
            {"record_type": "execution", "business_date": business_date, "side": "BUY", "symbol": "11110", "filled_quantity": 10, "price": 100, "execution_id": "exec-buy-1", "pending_item_id": "buy-1"},
            {"record_type": "execution", "business_date": business_date, "side": "BUY", "symbol": "11110", "filled_quantity": 5, "price": 110, "execution_id": "exec-buy-2", "pending_item_id": "buy-2"},
            {
                "record_type": "execution",
                "business_date": business_date,
                "side": "SELL",
                "symbol": "11110",
                "filled_quantity": 8,
                "price": 120,
                "execution_id": "exec-sell-1",
                "pending_item_id": "sell-1",
                "source_decision_id": "pm-reduce",
                "source_pm_decision_id": "pm-reduce",
                "source_decision_type": "REDUCE",
                "position_campaign_id": "pc-11110-0001",
            },
            {
                "record_type": "execution",
                "business_date": business_date,
                "side": "SELL",
                "symbol": "11110",
                "filled_quantity": 7,
                "price": 90,
                "execution_id": "exec-sell-2",
                "pending_item_id": "sell-2",
                "source_decision_id": "pm-exit",
                "source_pm_decision_id": "pm-exit",
                "source_decision_type": "EXIT",
                "position_campaign_id": "pc-11110-0001",
            },
            {"record_type": "execution", "business_date": business_date, "side": "BUY", "symbol": "11110", "filled_quantity": 3, "price": 95, "execution_id": "exec-buy-reopen", "pending_item_id": "buy-3"},
        ],
    )
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "environment": "historical",
            "cash": 1000,
            "market_value": 300,
            "total_equity": 1300,
            "new_unrealized_pnl": 15,
            "positions": [{"symbol": "11110", "quantity": 3, "average_price": 95, "current_price": 100, "market_value": 300, "unrealized_pnl": 15}],
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "items": []})
    final_hashes = runner.state_hashes(root)
    _write_json(
        run_dir / "plan.json",
        {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(root)},
    )
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": [business_date], "completed_jobs": []})
    _write_json(run_dir / "fresh_run_summary.json", {"run_id": RUN_ID, "profile_id": "historical-smoke", "initial_cash": 1000, "completed_days": [business_date], "external_effect_policy": {}})
    _write_json(run_dir / "final_summary.json", {"run_id": RUN_ID, "status": "PASS", "final_state_hashes": final_hashes})
    return root, evidence_root, run_dir


def test_phase20_j_writes_campaign_fills_realized_slices_and_pm_snapshot(tmp_path: Path) -> None:
    runner = load_runner()
    root, _, run_dir = _prepare_fixture(runner, tmp_path)

    runner.write_performance_observability_evidence(run_dir=run_dir, runtime_root=root, run_id=RUN_ID, business_date="2026-07-02", job="execution")
    runner.write_performance_observability_evidence(run_dir=run_dir, runtime_root=root, run_id=RUN_ID, business_date="2026-07-02", job="sell_planning")

    campaigns = json.loads((run_dir / "daily" / "2026-07-02" / "positions" / "position_campaigns.json").read_text(encoding="utf-8"))
    fills = json.loads((run_dir / "daily" / "2026-07-02" / "execution" / "fills.json").read_text(encoding="utf-8"))
    slices = json.loads((run_dir / "daily" / "2026-07-02" / "execution" / "realized_slices.json").read_text(encoding="utf-8"))
    pm = json.loads((run_dir / "daily" / "2026-07-02" / "position_management" / "pm_decisions.json").read_text(encoding="utf-8"))

    assert campaigns["symbol_only_identity"] == "PROHIBITED"
    assert [row["campaign_status"] for row in campaigns["position_campaigns"]] == ["CLOSED", "OPEN"]
    assert campaigns["position_campaigns"][0]["position_campaign_id"] != campaigns["position_campaigns"][1]["position_campaign_id"]
    assert len(fills["fills"]) == 5
    assert fills["fills"][0]["fees"] == {"value": "MISSING", "status": "NOT_AVAILABLE"}
    assert [row["source_decision_type"] for row in slices["realized_slices"]] == ["REDUCE", "EXIT"]
    sell_fills = [row for row in fills["fills"] if row["side"] == "SELL"]
    assert [row["source_decision_id"] for row in sell_fills] == ["pm-reduce", "pm-exit"]
    assert [row["source_decision_type"] for row in sell_fills] == ["REDUCE", "EXIT"]
    assert [row["position_campaign_id"] for row in sell_fills] == [
        row["position_campaign_id"] for row in slices["realized_slices"]
    ]
    assert slices["realized_slices"][0]["gross_realized_pnl"] == pytest.approx((120 - 103.3333333333) * 8)
    assert slices["realized_slices"][0]["net_realized_pnl"] == {"value": "MISSING", "status": "NOT_AVAILABLE"}
    assert pm["snapshot_policy"] == "DECISION_TIME_ONLY_NO_POST_HOC_OUTCOMES"
    assert pm["decisions"][0]["pm_decision_id"] == "pm-reduce"


def test_phase20_u_pm_halt_metadata_is_preserved_and_blocks_validation_close(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-phase20u-pm-halt"
    business_date = "2026-07-02"
    run_dir = evidence_root / "runs" / run_id
    _write_json(
        run_dir / "run_state.json",
        {
            "schema_version": runner.RUN_STATE_SCHEMA_VERSION,
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "status": "COMPLETED",
            "completed_business_days": [business_date],
            "completed_jobs": [],
        },
    )
    _write_json(
        root / "runtime_state" / "position_management" / business_date / "position_management_decisions.json",
        {
            "status": "HALT",
            "reason": "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
            "decisions": [],
            "input_contract": {
                "pm_input_schema_status": "HALT",
                "pm_runtime_adapter_authority_status": "HALT",
                "pm_runtime_adapter_authority_reason": "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER",
            },
        },
    )

    runner.write_performance_observability_evidence(run_dir=run_dir, runtime_root=root, run_id=run_id, business_date=business_date, job="sell_planning")
    pm = json.loads((run_dir / "daily" / business_date / "position_management" / "pm_decisions.json").read_text(encoding="utf-8"))
    validate = call_main(runner, ["validate", "--run-id", run_id, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    close = call_main(runner, ["close", "--run-id", run_id, "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    assert pm["source_status"] == "AVAILABLE"
    assert pm["pm_status"] == "HALT"
    assert pm["pm_input_schema_status"] == "HALT"
    assert pm["pm_reason"] == "artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER"
    assert validate["status"] == "VALIDATION_FAILURE"
    assert validate["checks"]["position_management_halt_absent"] is False
    assert close["status"] == "REVIEW_REQUIRED"
    assert close["acceptance_gate_judgment"] == "REVIEW_REQUIRED"
    assert close["position_management_halt_evidence"]


def test_phase20_j_summary_scopes_use_observability_without_breaking_legacy_fields(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root, run_dir = _prepare_fixture(runner, tmp_path)
    runner.write_performance_observability_evidence(run_dir=run_dir, runtime_root=root, run_id=RUN_ID, business_date="2026-07-02", job="execution")
    runner.write_performance_observability_evidence(run_dir=run_dir, runtime_root=root, run_id=RUN_ID, business_date="2026-07-02", job="sell_planning")
    runner.write_performance_observability_evidence(run_dir=run_dir, runtime_root=root, run_id=RUN_ID, business_date="2026-07-02", job="market_refresh")

    performance = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "performance", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    positions = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "positions", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    lifecycle = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "lifecycle", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    assert performance["performance_scope"]["realized_slice_observability"]["status"] == "AVAILABLE"
    assert performance["performance_scope"]["benchmark_observability"]["status"] == "MISSING"
    assert positions["positions_scope"]["position_campaign_identity"] == "POSITION_CAMPAIGN_ID_AVAILABLE"
    assert positions["positions_scope"]["positions"][0]["position_campaign_id"].startswith("pc-")
    assert lifecycle["lifecycle_scope"]["status"] == "AVAILABLE_WITH_PHASE20_J_OBSERVABILITY"
    assert lifecycle["lifecycle_scope"]["pm_decision_snapshots"][0]["pm_decision_id"] == "pm-reduce"
