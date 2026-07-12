from __future__ import annotations

import json

from tests.runtime_v2.phase15by_buy_origin_e2e import run_phase15by_buy_origin_e2e


def test_phase15by_buy_origin_reaches_next_day_pm_sell_hold(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_buy_origin"
    payload = run_phase15by_buy_origin_e2e(
        root=root,
        evidence_dir=tmp_path / "phase15_by",
        write_phase_report=False,
    )

    assert payload["final_judgment"] == "BUY_ORIGIN_END_TO_END_ACCEPTED_WITH_CONDITIONS"
    assert payload["market_feature_ai"]["investment_decision_generated_by_codex"] is False
    assert payload["buy_mainline"]["morning_status"] == "PASS"
    assert payload["buy_mainline"]["issue_code"] == "7203"
    assert payload["buy_mainline"]["side"] == "BUY"
    assert payload["buy_mainline"]["quantity"] == 100.0
    assert payload["submit"]["status"] == "PASS"
    assert payload["submit"]["accepted_count"] == 1
    assert payload["submit"]["pending_consumed"] is True
    assert payload["submit"]["broker_write_performed"] is False
    assert payload["execution"]["status"] == "PASS"
    assert payload["execution"]["execution_equivalent_count"] == 1
    assert payload["execution"]["ledger_execution"]["price"] == 1000.0
    assert payload["execution"]["ledger_execution"]["cash_effect"] == 100000.0
    assert payload["buy_current"]["cash"] == 900000.0
    assert payload["buy_current"]["position"]["symbol"] == "7203"
    assert payload["buy_current"]["position"]["quantity"] == 100.0
    assert payload["next_day_current"]["cash"] == 900000.0
    assert payload["next_day_current"]["market_value"] == 105000.0
    assert payload["next_day_current"]["position"]["current_price"] == 1050.0
    assert payload["current_restart"]["temporal_migration_status"] == "READY"
    assert payload["current_restart"]["temporal_migration_apply_executed"] is True
    assert payload["current_restart"]["position_state_as_of"] == "2026-07-13"
    assert payload["current_restart"]["valuation_as_of"] == "2026-07-14"
    assert payload["current_restart"]["current_position_status"] == "READY"
    assert payload["current_restart"]["current_valuation_status"] == "READY"
    assert payload["pm_ai"]["status"] == "PASS"
    assert payload["pm_ai"]["decision_count"] == 1
    assert payload["pm_ai"]["decision"]["symbol"] == "7203"
    assert payload["pm_ai"]["input_contract"]["pm_input_schema_status"] == "READY"
    assert payload["pm_ai"]["input_contract"]["pm_derived_fields"]
    assert payload["sell_hold"]["decision"] in {"HOLD", "EXIT"}
    assert payload["sell_hold"]["sell_execution_performed"] is False
    assert payload["report"]["generated"] is True
    assert payload["report"]["notification_sent"] is False
    assert payload["regression"]["ledger_duplicate_delta"] == {
        "orders": 0,
        "executions": 0,
        "positions": 0,
        "cash": 0,
        "events": 0,
    }
    assert payload["regression"]["current_double_update"] is True
    assert payload["runtime_mutation"]["existing_runtime_mutated"] is False
    assert payload["runtime_mutation"]["production_write"] is False

    current = json.loads((root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert current["positions"][0]["symbol"] == "7203"
    assert current["positions"][0]["quantity"] == 100.0
    assert current["valuation_as_of"] == "2026-07-14"
