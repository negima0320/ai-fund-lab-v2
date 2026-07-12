from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_phase15br2_selects_fresh_sell_6501_without_authorizing_send() -> None:
    summary = _read_json("reports/phase_reports/phase15_br2_demo_scenario_selection.json")
    scenario = summary["selected_scenario"]
    prohibited = summary["prohibited_actions"]

    assert summary["final_judgment"] == "DEMO_SCENARIO_SELECTED_WITH_CONDITIONS"
    assert scenario["scenario_side"] == "SELL"
    assert scenario["scenario_issue_code"] == "6501"
    assert scenario["scenario_quantity_candidate"] == 100
    assert scenario["position_origin"] == "DEMO_PRELOADED_POSITION"
    assert scenario["runtime_owned"] is False
    assert scenario["acceptance_only"] is True
    assert scenario["production_equivalent"] is False
    assert scenario["authorized_for_send"] is False
    assert scenario["target_session"] == "2026-07-13"
    assert prohibited["previous_6522_scenario_reused"] is False
    assert prohibited["broker_write_performed"] is False
    assert prohibited["submit_executed"] is False
    assert prohibited["approval_generated"] is False
    assert prohibited["pending_generated"] is False
    assert prohibited["request_hash_generated"] is False
    assert prohibited["user_authorization_artifact_generated"] is False


def test_phase15br2_evidence_uses_fresh_bq_r2_broker_snapshot_only() -> None:
    evidence = _read_json("reports/phase_reports/phase15_br2/scenario_selection_evidence.json")
    broker = evidence["fresh_broker_evidence"]
    source = evidence["source_of_truth"]

    assert source["runtime_root"] == ".runtime_acceptance_phase15_demo_reinit"
    assert source["previous_6522_scenario_reused"] is False
    assert broker["data_origin"] == "BROKER_API"
    assert broker["fixture_used"] is False
    assert broker["mock_used"] is False
    assert broker["open_orders_count"] == 0
    assert broker["business_date"] == "2026-07-13"
    assert broker["cash_available_jpy"] == 18070600
    assert broker["buying_power_jpy"] == 20000000


def test_phase15br2_candidate_selection_preserves_demo_only_exception() -> None:
    evidence = _read_json("reports/phase_reports/phase15_br2/scenario_selection_evidence.json")
    candidates = {item["issue_code"]: item for item in evidence["candidate_comparison"]}

    selected = candidates["6501"]
    assert selected["status"] == "SELECTED"
    assert selected["classification"] == "DEMO_PRELOADED_POSITION"
    assert selected["runtime_owned"] is False
    assert selected["acceptance_only"] is True
    assert selected["production_equivalent"] is False
    assert selected["quantity_candidate"] <= selected["available_quantity"]
    assert selected["estimated_notional_jpy"] == 470000

    assert candidates["6502"]["status"] == "NOT_SELECTED"
    assert candidates["6502"]["market_value_jpy"] == 0
    assert candidates["9984"]["status"] == "NOT_SELECTED"
    assert candidates["9984"]["estimated_notional_jpy"] > selected["estimated_notional_jpy"]


def test_phase15br2_regression_blocks_send_without_next_phase_preconditions() -> None:
    summary = _read_json("reports/phase_reports/phase15_br2_demo_scenario_selection.json")
    regression = summary["regression"]
    conditions = summary["remaining_conditions"]

    assert regression["old_scenario_not_reused"] == "PASS"
    assert regression["fresh_broker_evidence_only"] == "PASS"
    assert regression["open_order_conflict_checked"] == "PASS"
    assert regression["quantity_overage_rejected"] == "PASS"
    assert regression["past_session_rejected"] == "PASS"
    assert regression["send_without_user_authorization_blocked"] == "PASS"
    assert regression["broker_write_not_performed"] == "PASS"
    assert any("Fresh Safety / Approval / Pending" in item for item in conditions)
