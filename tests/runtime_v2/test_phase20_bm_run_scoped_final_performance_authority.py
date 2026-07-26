from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_v2.test_phase17_k_runtime_test_runner import call_main, load_runner, make_runtime_root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _base_run_evidence(runner, root: Path, evidence_root: Path, run_id: str, days: list[str]) -> Path:
    run_dir = evidence_root / "runs" / run_id
    _write_json(run_dir / "plan.json", {"schema_version": runner.PLAN_SCHEMA_VERSION, "run_id": run_id, "profile_id": "historical-smoke", "runtime_root": str(root)})
    _write_json(run_dir / "run_state.json", {"schema_version": runner.RUN_STATE_SCHEMA_VERSION, "run_id": run_id, "status": "COMPLETED", "completed_business_days": days})
    _write_json(
        run_dir / "fresh_run_summary.json",
        {
            "schema_version": runner.FRESH_RUN_SUMMARY_SCHEMA_VERSION,
            "run_id": run_id,
            "profile_id": "historical-smoke",
            "date_from": days[0],
            "date_to": days[-1],
            "initial_cash": 1000.0,
            "completed_days": days,
            "external_effect_policy": {"broker_write": False, "external_delivery": False, "jquants_fetch": False, "tachibana_api": False},
        },
    )
    return run_dir


def _write_observability(run_dir: Path, run_id: str, day: str) -> None:
    _write_json(
        run_dir / "daily" / day / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "run_id": run_id,
            "business_date": day,
            "authority": "fixture",
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-11110-0001",
                    "symbol": "11110",
                    "campaign_status": "CLOSED",
                    "opened_business_date": day,
                    "closed_business_date": day,
                    "current_quantity": 0.0,
                    "average_cost": 100.0,
                    "buy_notional": 500.0,
                    "sell_notional": 400.0,
                    "realized_pnl": -100.0,
                    "unrealized_pnl": 0.0,
                    "total_campaign_pnl": -100.0,
                    "events": [{"stage": "BUY", "business_date": day}, {"stage": "EXIT", "business_date": day}],
                },
                {
                    "position_campaign_id": "pc-22220-0001",
                    "symbol": "22220",
                    "campaign_status": "OPEN",
                    "opened_business_date": day,
                    "closed_business_date": "",
                    "current_quantity": 5.0,
                    "average_cost": 100.0,
                    "buy_notional": 500.0,
                    "sell_notional": 275.0,
                    "realized_pnl": 25.0,
                    "unrealized_pnl": 5.0,
                    "total_campaign_pnl": 30.0,
                    "events": [{"stage": "BUY", "business_date": day}, {"stage": "REDUCE", "business_date": day}],
                },
            ],
        },
    )
    _write_json(
        run_dir / "daily" / day / "execution" / "fills.json",
        {
            "schema_version": "runtime_fill_observability.v1",
            "run_id": run_id,
            "business_date": day,
            "authority": "fixture",
            "fills": [
                {"run_id": run_id, "business_date": day, "symbol": "11110", "side": "BUY", "quantity": 5.0, "execution_price": 100.0, "execution_id": "exec-buy-1", "gross_notional": {"value": 500.0, "status": "DERIVABLE_EXACT"}, "source_decision_type": "BUY", "source_decision_id": "MISSING"},
                {"run_id": run_id, "business_date": day, "symbol": "22220", "side": "BUY", "quantity": 5.0, "execution_price": 100.0, "execution_id": "exec-buy-2", "gross_notional": {"value": 500.0, "status": "DERIVABLE_EXACT"}, "source_decision_type": "BUY", "source_decision_id": "MISSING"},
                {"run_id": run_id, "business_date": day, "symbol": "11110", "side": "SELL", "quantity": 5.0, "execution_price": 80.0, "execution_id": "exec-sell-1", "gross_notional": {"value": 400.0, "status": "DERIVABLE_EXACT"}, "source_decision_type": "EXIT", "source_decision_id": "pm-exit"},
                {"run_id": run_id, "business_date": day, "symbol": "22220", "side": "SELL", "quantity": 5.0, "execution_price": 55.0, "execution_id": "exec-sell-2", "gross_notional": {"value": 275.0, "status": "DERIVABLE_EXACT"}, "source_decision_type": "REDUCE", "source_decision_id": "pm-reduce"},
            ],
        },
    )
    _write_json(
        run_dir / "daily" / day / "execution" / "realized_slices.json",
        {
            "schema_version": "realized_slice_observability.v1",
            "run_id": run_id,
            "business_date": day,
            "authority": "fixture",
            "realized_slices": [
                {"symbol": "11110", "position_campaign_id": "pc-11110-0001", "gross_realized_pnl": -100.0, "source_decision_type": "EXIT", "source_decision_id": "pm-exit"},
                {"symbol": "22220", "position_campaign_id": "pc-22220-0001", "gross_realized_pnl": 25.0, "source_decision_type": "REDUCE", "source_decision_id": "pm-reduce"},
            ],
        },
    )
    _write_json(
        run_dir / "daily" / day / "position_management" / "pm_decisions.json",
        {
            "schema_version": "pm_decision_snapshot.v1",
            "run_id": run_id,
            "business_date": day,
            "authority": "fixture",
            "decisions": [
                {"business_date": day, "symbol": "11110", "decision": "EXIT", "decision_id": "pm-exit", "runtime_action": "SELL_FULL_POSITION"},
                {"business_date": day, "symbol": "22220", "decision": "REDUCE", "decision_id": "pm-reduce", "runtime_action": "SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING"},
            ],
        },
    )


def test_phase20_bm_summary_uses_run_scoped_evidence_when_current_root_hash_mismatches(tmp_path: Path, capsys) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-phase20bm-run-scoped"
    day = "2026-07-21"
    run_dir = _base_run_evidence(runner, root, evidence_root, run_id, [day])
    _write_observability(run_dir, run_id, day)
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1000.0, "market_value": 0.0, "total_equity": 1000.0, "positions": []})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": run_id, "status": "PASS", "final_state_hashes": runner.state_hashes(root)})
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1.0, "market_value": 0.0, "total_equity": 1.0, "positions": []})

    payload = call_main(runner, ["summarize", "--run-id", run_id, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "full"], capsys)

    assert payload["status"] == "PASS"
    assert payload["authority"]["runtime_root_detail"] == "CURRENT_RUNTIME_ROOT_FINAL_HASH_MISMATCH"
    assert payload["performance"]["performance_authority_status"] == "DERIVABLE_EXACT_FROM_RUN_SCOPED_POSITION_CAMPAIGNS"
    assert payload["performance"]["final_equity"] == 930.0
    assert payload["performance"]["realized_pnl"] == -75.0
    assert payload["performance"]["unrealized_pnl"] == 5.0
    assert payload["trading"]["execution_distribution"] == {"BUY": 2, "SELL": 2}
    assert payload["trading"]["buy_plan_count"] == 2
    assert payload["trading"]["sell_plan_count"] == 2
    assert payload["lifecycle_consistency"]["status"] == "PASS"
    assert [(row["severity"], row["reason"]) for row in payload["findings"]] == [
        ("INFO", "RUN_FINAL_STATE_HASH_MISMATCH"),
        ("INFO", "CURRENT_RUNTIME_ROOT_LEDGER_NOT_USED_FOR_PAST_RUN"),
    ]


def test_phase20_bm_no_trade_past_run_remains_zero_when_current_root_mismatches(tmp_path: Path, capsys) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-phase20bm-no-trade"
    day = "2026-07-22"
    run_dir = _base_run_evidence(runner, root, evidence_root, run_id, [day])
    _write_json(run_dir / "daily" / day / "execution" / "fills.json", {"schema_version": "runtime_fill_observability.v1", "run_id": run_id, "business_date": day, "fills": []})
    _write_json(run_dir / "daily" / day / "positions" / "position_campaigns.json", {"schema_version": "position_campaign_observability.v1", "run_id": run_id, "business_date": day, "position_campaigns": []})
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1000.0, "market_value": 0.0, "total_equity": 1000.0, "positions": []})
    _write_json(run_dir / "final_summary.json", {"schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION, "run_id": run_id, "status": "PASS", "final_state_hashes": runner.state_hashes(root)})
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1.0, "market_value": 0.0, "total_equity": 1.0, "positions": []})

    payload = call_main(runner, ["summarize", "--run-id", run_id, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "performance"], capsys)

    assert payload["status"] == "PASS"
    assert payload["performance"]["performance_authority_status"] == "DERIVABLE_EXACT_FROM_RUN_SCOPED_NO_TRADE_EVIDENCE"
    assert payload["performance"]["final_equity"] == 1000.0
    assert payload["performance"]["total_return_amount"] == 0.0
    assert payload["performance_scope"]["metrics"]["BUY Count"]["value"] == 0
    assert payload["performance_scope"]["metrics"]["SELL Count"]["value"] == 0


def test_phase20_bm_verified_final_snapshot_takes_priority_over_derived_evidence(tmp_path: Path, capsys) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports" / "runtime_tests"
    run_id = "runtime-test-phase20bm-final-snapshot"
    day = "2026-07-23"
    run_dir = _base_run_evidence(runner, root, evidence_root, run_id, [day])
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 900.0, "market_value": 200.0, "total_equity": 1100.0, "realized_pnl": 90.0, "new_unrealized_pnl": 10.0, "positions": [{"symbol": "33330", "quantity": 1}]})
    snapshot = runner.write_final_state_snapshot(run_dir=run_dir, runtime_root=root)
    _write_json(
        run_dir / "final_summary.json",
        {
            "schema_version": runner.FINAL_SUMMARY_SCHEMA_VERSION,
            "run_id": run_id,
            "status": "PASS",
            "final_state_hashes": runner.state_hashes(root),
            "final_state_snapshot": {"status": snapshot["status"], "manifest_path": str(run_dir / "final_state_snapshot" / "manifest.json")},
        },
    )
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1.0, "market_value": 0.0, "total_equity": 1.0, "positions": []})

    payload = call_main(runner, ["summarize", "--run-id", run_id, "--runtime-root", str(root), "--evidence-root", str(evidence_root), "--scope", "performance"], capsys)

    assert payload["status"] == "PASS"
    assert payload["run"]["final_state_authority"] == "RUN_SCOPED_FINAL_STATE_SNAPSHOT_VERIFIED"
    assert payload["performance"]["performance_authority_status"] == "CANONICAL_FINAL_STATE_SNAPSHOT"
    assert payload["performance"]["final_equity"] == 1100.0
    assert payload["performance"]["total_return_amount"] == 100.0
