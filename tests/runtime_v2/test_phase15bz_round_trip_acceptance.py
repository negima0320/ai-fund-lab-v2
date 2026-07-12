from __future__ import annotations

from tests.runtime_v2.phase15by_buy_origin_e2e import run_phase15by_buy_origin_e2e
from tests.runtime_v2.phase15by2_authority_cleanup import run_phase15by2_authority_cleanup
from tests.runtime_v2.phase15bz_round_trip_acceptance import run_phase15bz_round_trip_acceptance


def test_phase15bz_runtime_round_trip_buy_sell_acceptance(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_buy_origin"
    run_phase15by_buy_origin_e2e(root=root, evidence_dir=tmp_path / "phase15_by", write_phase_report=False)
    run_phase15by2_authority_cleanup(root=root, evidence_dir=tmp_path / "phase15_by2", write_phase_report=False)

    result = run_phase15bz_round_trip_acceptance(root=root, evidence_dir=tmp_path / "phase15_bz", write_phase_report=False)

    assert result["final_judgment"] == "RUNTIME_ROUND_TRIP_ACCEPTED_WITH_CONDITIONS"
    assert result["sell_decision_authority"]["original_pm_decision"] == "HOLD"
    assert result["sell_decision_authority"]["acceptance_override"] == "EXIT_FOR_ROUND_TRIP_ACCEPTANCE"
    assert result["sell_decision_authority"]["production_applicable"] is False
    assert result["normal_submit_pipeline"]["status"] == "PASS"
    assert result["normal_submit_pipeline"]["broker_write_performed"] is False
    assert result["sell_execution"]["execution_price"] == 1050.0
    assert result["sell_execution"]["production_equivalent"] is False
    assert result["round_trip_math"]["final_cash_equals_initial_cash_plus_realized_pnl"] is True
    assert result["final_current"]["position_count"] == 0
    assert result["final_current"]["quantity_7203"] == 0
    assert result["final_current"]["cash"] == 1_005_000.0
    assert result["final_current"]["buying_power"] == 1_005_000.0
    assert result["final_current"]["market_value"] == 0
    assert result["final_current"]["total_equity"] == 1_005_000.0
    assert result["final_current"]["realized_pnl"] == 5_000.0
    assert result["final_current"]["current_version"]
    assert result["final_current"]["current_hash"]
    assert result["pending_lifecycle"]["buy_pending_before_sell"] == "CONSUMED"
    assert result["pending_lifecycle"]["buy_pending_item_states_before_sell"] == ["CONSUMED"]
    assert result["pending_lifecycle"]["sell_pending_after_submit"] == "CONSUMED"
    assert result["pending_lifecycle"]["sell_pending_item_states"] == ["CONSUMED"]
    assert result["runtime_state"]["state"] == "CURRENT_APPLIED"
    assert result["runtime_state"]["execution_reference"].startswith("execution-equivalent:")
    assert result["runtime_state"]["production_equivalent"] is False
    assert result["ledger"]["sell_order_record_count"] >= 1
    assert result["ledger"]["sell_execution_record_count"] >= 1
    assert result["ledger"]["position_close_record_count"] >= 1
    assert result["ledger"]["realized_pnl_event_count"] == 1
    assert result["ledger"]["current_apply_event_count"] == 1
    assert result["idempotency"]["first_status"] == "APPLIED"
    assert result["idempotency"]["second_status"] == "NOOP_ALREADY_APPLIED"
    assert result["idempotency"]["sell_ledger_no_duplicate_after_second"] is True
    assert result["idempotency"]["cash_unchanged_after_second"] is True
    assert result["idempotency"]["realized_pnl_not_double_counted"] is True
    assert result["restart_restore"]["cash"] == 1_005_000.0
    assert result["restart_restore"]["position_count"] == 0
    assert result["restart_restore"]["realized_pnl"] == 5_000.0
    assert result["restart_restore"]["pending"] == "CONSUMED"
    assert result["restart_restore"]["current_hash_matches"] is True
    assert result["runtime_mutation"]["existing_runtime_mutated"] is False
    assert all(result["regression"].values())
