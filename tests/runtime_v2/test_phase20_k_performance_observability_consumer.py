from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


RUN_ID = "runtime-test-phase20k-consumer-fixture"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _make_campaign(symbol: str, campaign_id: str, *, day: str, closed: bool = False, events: int = 1, realized: float = 0.0, unrealized: float = 0.0) -> dict:
    event_rows = [{"stage": "BUY", "business_date": "2026-07-06", "quantity": 100, "price": 100}]
    if events > 1:
        event_rows.append({"stage": "EXIT" if closed else "REDUCE", "business_date": day, "quantity": 100 if closed else 40, "price": 80})
    total = realized + (0.0 if closed else unrealized)
    return {
        "position_campaign_id": campaign_id,
        "run_id": RUN_ID,
        "symbol": symbol,
        "campaign_status": "CLOSED" if closed else "OPEN",
        "opened_business_date": "2026-07-06",
        "closed_business_date": day if closed else "",
        "current_quantity": 0.0 if closed else 60.0,
        "average_cost": 100.0,
        "buy_notional": 10000.0,
        "sell_notional": 8000.0 if events > 1 else 0.0,
        "realized_pnl": realized,
        "unrealized_pnl": 0.0 if closed else unrealized,
        "total_campaign_pnl": total,
        "events": event_rows,
    }


def _prepare_consumer_fixture(runner, tmp_path: Path) -> tuple[Path, Path]:
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_dir = evidence_root / "runs" / RUN_ID
    days = ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10"]
    campaign_ids = [f"pc-fixture-{symbol}-0001" for symbol in ("31330", "45640", "45960", "67400", "89180")]
    symbols = ["31330", "45640", "45960", "67400", "89180"]

    for day in days:
        campaigns = []
        for symbol, campaign_id in zip(symbols, campaign_ids):
            if day < "2026-07-08":
                campaigns.append(_make_campaign(symbol, campaign_id, day=day, closed=False, events=1, realized=0.0, unrealized=100.0))
            elif symbol in {"31330", "45960"}:
                campaigns.append(_make_campaign(symbol, campaign_id, day="2026-07-08", closed=True, events=2, realized=-31200.0 if symbol == "31330" else -51800.0))
            elif symbol == "67400" and day >= "2026-07-10":
                campaigns.append(_make_campaign(symbol, campaign_id, day="2026-07-10", closed=False, events=2, realized=-2700.0, unrealized=-4200.0))
            else:
                campaigns.append(_make_campaign(symbol, campaign_id, day=day, closed=False, events=1, realized=0.0, unrealized=100.0))
        _write_json(
            run_dir / "daily" / day / "positions" / "position_campaigns.json",
            {"schema_version": "position_campaign_observability.v1", "run_id": RUN_ID, "business_date": day, "authority": "fixture", "generated_at": day, "source_artifacts": {}, "temporal_safety": {}, "position_campaigns": campaigns},
        )
        _write_json(
            run_dir / "daily" / day / "execution" / "fills.json",
            {
                "schema_version": "runtime_fill_observability.v1",
                "run_id": RUN_ID,
                "business_date": day,
                "authority": "fixture",
                "generated_at": day,
                "source_artifacts": {},
                "temporal_safety": {},
                "fills": [
                    {"run_id": RUN_ID, "business_date": day, "position_campaign_id": campaign_ids[0], "symbol": symbols[0], "side": "BUY", "execution_id": f"buy-{day}", "quantity": 10, "execution_price": 100, "gross_notional": {"value": 1000.0, "status": "DERIVABLE_EXACT"}, "cash_effect": {"value": -1000.0, "status": "DERIVABLE_EXACT"}, "fees": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "tax": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "slippage": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "source_decision_type": "BUY", "source_decision_id": "MISSING"},
                    {"run_id": RUN_ID, "business_date": day, "position_campaign_id": campaign_ids[0], "symbol": symbols[0], "side": "SELL", "execution_id": f"sell-{day}", "quantity": 5, "execution_price": 80, "gross_notional": {"value": 400.0, "status": "DERIVABLE_EXACT"}, "cash_effect": {"value": 400.0, "status": "DERIVABLE_EXACT"}, "fees": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "tax": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "slippage": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "source_decision_type": "EXIT", "source_decision_id": "pm-exit"},
                ]
                if day in {"2026-07-08", "2026-07-10"}
                else [],
            },
        )
        slices = []
        if day == "2026-07-08":
            slices = [
                {"realized_slice_id": "slice-31330", "position_campaign_id": campaign_ids[0], "symbol": "31330", "sell_execution_id": "sell-31330", "sell_quantity": 1200, "sell_price": 104, "cost_basis_method": "AVERAGE_COST_RUNTIME_OWNED_FILL_PROJECTION", "allocated_cost_basis": 156000, "gross_realized_pnl": -31200.0, "fees": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "tax": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "net_realized_pnl": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "remaining_quantity": 0, "remaining_average_cost": 0, "source_decision_type": "EXIT", "source_decision_id": "pm-exit"},
                {"realized_slice_id": "slice-45960", "position_campaign_id": campaign_ids[2], "symbol": "45960", "sell_execution_id": "sell-45960", "sell_quantity": 100, "sell_price": 482, "cost_basis_method": "AVERAGE_COST_RUNTIME_OWNED_FILL_PROJECTION", "allocated_cost_basis": 100000, "gross_realized_pnl": -51800.0, "fees": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "tax": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "net_realized_pnl": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "remaining_quantity": 0, "remaining_average_cost": 0, "source_decision_type": "EXIT", "source_decision_id": "pm-exit"},
            ]
        if day == "2026-07-10":
            slices = [
                {"realized_slice_id": "slice-67400", "position_campaign_id": campaign_ids[3], "symbol": "67400", "sell_execution_id": "sell-67400", "sell_quantity": 300, "sell_price": 45, "cost_basis_method": "AVERAGE_COST_RUNTIME_OWNED_FILL_PROJECTION", "allocated_cost_basis": 16200, "gross_realized_pnl": -2700.0, "fees": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "tax": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "net_realized_pnl": {"value": "MISSING", "status": "NOT_AVAILABLE"}, "remaining_quantity": 2100, "remaining_average_cost": 54, "source_decision_type": "REDUCE", "source_decision_id": "pm-reduce"},
            ]
        _write_json(run_dir / "daily" / day / "execution" / "realized_slices.json", {"schema_version": "realized_slice_observability.v1", "run_id": RUN_ID, "business_date": day, "authority": "fixture", "generated_at": day, "source_artifacts": {}, "temporal_safety": {}, "realized_slices": slices})
        _write_json(run_dir / "daily" / day / "position_management" / "pm_decisions.json", {"schema_version": "pm_decision_snapshot.v1", "run_id": RUN_ID, "business_date": day, "authority": "fixture", "generated_at": day, "source_artifacts": {}, "temporal_safety": {}, "snapshot_policy": "DECISION_TIME_ONLY_NO_POST_HOC_OUTCOMES", "decisions": []})

    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "environment": "historical",
            "cash": 469400,
            "market_value": 449200,
            "total_equity": 918600,
            "realized_pnl": -85700.0,
            "new_unrealized_pnl": 4300,
            "positions": [],
        },
    )
    final_hashes = runner.state_hashes(root)
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": RUN_ID, "profile_id": "historical-smoke", "runtime_root": str(root)})
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": RUN_ID, "status": "COMPLETED", "completed_business_days": days, "completed_jobs": []})
    _write_json(run_dir / "fresh_run_summary.json", {"run_id": RUN_ID, "profile_id": "historical-smoke", "initial_cash": 1000000, "completed_days": days, "external_effect_policy": {}})
    _write_json(run_dir / "final_summary.json", {"run_id": RUN_ID, "status": "PASS", "final_state_hashes": final_hashes})
    return root, evidence_root


def test_phase20_k_deduplicates_campaign_snapshots_and_human_lifecycle_matches_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _prepare_consumer_fixture(runner, tmp_path)

    payload = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "lifecycle", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    scope = payload["lifecycle_scope"]
    human = payload["human_summary"]

    assert scope["daily_snapshot_count"] == 25
    assert scope["campaign_count"] == 5
    assert len(scope["position_lifecycles"]) == 5
    closed = next(row for row in scope["position_lifecycles"] if row["symbol"] == "31330")
    assert closed["campaign_status"] == "CLOSED"
    assert len(closed["events"]) == 2
    assert closed["realized_pnl"] == -31200.0
    assert "- position_campaigns: 5" in human
    assert "status=None" not in human
    assert "31330 / pc-fixture-31330-0001: status=CLOSED" in human
    assert "realized=-31200.0" in human
    assert "total=-31200.0" in human


def test_phase20_k_positions_and_performance_consumer_use_campaign_pnl_and_notional(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _prepare_consumer_fixture(runner, tmp_path)

    positions = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "positions", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)
    performance = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "performance", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    closed = next(row for row in positions["positions_scope"]["positions"] if row["symbol"] == "45960")
    open_row = next(row for row in positions["positions_scope"]["positions"] if row["symbol"] == "67400")
    assert closed["campaign_status"] == "CLOSED"
    assert closed["realized_pnl"] == -51800.0
    assert closed["total_campaign_pnl"] == -51800.0
    assert open_row["campaign_status"] == "OPEN"
    assert open_row["realized_pnl"] == -2700.0
    assert open_row["unrealized_pnl"] == -4200.0
    assert open_row["total_campaign_pnl"] == -6900.0
    assert "realized=-51800.0" in positions["human_summary"]
    assert "total=-51800.0" in positions["human_summary"]

    metrics = performance["performance_scope"]["metrics"]
    assert metrics["Realized PnL"]["status"] == "DERIVABLE_EXACT"
    assert performance["performance_scope"]["realized_slice_observability"]["reconciliation"]["status"] == "PASS"
    assert metrics["Execution Notional"]["status"] == "DERIVABLE_EXACT"
    assert metrics["Execution Notional"]["value"] == {
        "buy_execution_notional": 2000.0,
        "sell_execution_notional": 800.0,
        "total_execution_notional": 2800.0,
    }
    assert "Realized PnL" not in performance["human_summary"].split("metric_warnings: ", 1)[1]
    assert "Execution Notional" not in performance["human_summary"].split("metric_warnings: ", 1)[1]


def test_phase20_k_realized_pnl_mismatch_is_review_required(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root, evidence_root = _prepare_consumer_fixture(runner, tmp_path)
    state_path = root / "persistent_ledger" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["realized_pnl"] = -1.0
    _write_json(state_path, state)
    run_dir = evidence_root / "runs" / RUN_ID
    final_summary = json.loads((run_dir / "final_summary.json").read_text(encoding="utf-8"))
    final_summary["final_state_hashes"] = runner.state_hashes(root)
    _write_json(run_dir / "final_summary.json", final_summary)

    performance = call_main(runner, ["summarize", "--run-id", RUN_ID, "--scope", "performance", "--runtime-root", str(root), "--evidence-root", str(evidence_root)], capsys)

    reconciliation = performance["performance_scope"]["realized_slice_observability"]["reconciliation"]
    assert reconciliation["status"] == "REVIEW_REQUIRED"
    assert performance["performance_scope"]["metrics"]["Realized PnL"]["status"] == "REVIEW_REQUIRED"
    assert "REALIZED_PNL_RECONCILIATION_MISMATCH" in performance["performance_scope"]["metrics"]["Realized PnL"]["warnings"]
