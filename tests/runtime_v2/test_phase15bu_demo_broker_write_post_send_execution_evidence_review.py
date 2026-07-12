from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_phase15bu_final_judgment_is_demo_only_execution_equivalent() -> None:
    report = _read_json("reports/phase_reports/phase15_bu_demo_broker_write_post_send_execution_evidence_review.json")

    assert report["phase"] == "Phase15-BU"
    assert report["final_judgment"] == "EXECUTION_EQUIVALENT_READY_DEMO_ONLY"
    assert report["evidence_authority_option"] == "B"
    assert report["demo_fallback_contract"] == "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1"
    assert report["production_boundary"] == "DEMO_ONLY_NOT_PRODUCTION_EXECUTION_AUTHORITY"


def test_phase15bu_execution_detail_failure_is_detail_only() -> None:
    evidence = _read_json("reports/phase_reports/phase15_bu/execution_evidence_authority.json")
    failure = evidence["execution_detail_failure"]

    assert failure["api"] == "CLMOrderListDetail"
    assert failure["request_parameter"] == "sOrderNumber"
    assert failure["failure_stage"] == "order_detail_response"
    assert failure["response_code_present"] is True
    assert failure["response_code_zero"] is False
    assert failure["session_status"] == "PASS"
    assert failure["login_status"] == "PASS"
    assert failure["root_cause_classification"] == "DEMO_API_UNSUPPORTED"


def test_phase15bu_orderlist_and_position_authority_match_sell_quantity() -> None:
    evidence = _read_json("reports/phase_reports/phase15_bu/execution_evidence_authority.json")

    order = evidence["broker_evidence"]["order_list"]
    assert order["source_clmid"] == "CLMOrderList"
    assert order["issue_code"] == "6501"
    assert order["side"] == "sell"
    assert order["quantity"] == "100"
    assert order["status"] == "全部約定"
    assert order["executed_quantity"] == "100"
    assert order["remaining_quantity"] == "0"
    assert order["data_origin"] == "BROKER_API"
    assert order["fixture_used"] is False
    assert order["mock_used"] is False

    position = evidence["broker_evidence"]["position_inventory"]
    assert position["before_quantity"] == "200"
    assert position["after_quantity"] == "100"
    assert position["difference"] == "-100"
    assert position["quantity_difference_matches_sell_quantity"] is True


def test_phase15bu_price_and_session_are_not_conflated() -> None:
    evidence = _read_json("reports/phase_reports/phase15_bu/execution_evidence_authority.json")

    price = evidence["price_authority"]
    assert price["execution_price"]["value"] == 100
    assert price["execution_price"]["source"] == "operator_browser_confirmation"
    assert price["execution_price"]["machine_readable_broker_detail_available"] is False
    assert price["valuation_price"]["value"] == 4700
    assert price["valuation_price"]["authority"] == "CURRENT_VALUATION_ONLY_NOT_EXECUTION_PRICE"
    assert "must not use 4700 JPY" in price["normalization_rule"]

    session = evidence["session_translation"]
    assert session["demo_session_translation_contract"] == "DEMO_SESSION_TRANSLATION_CONTRACT"
    assert session["runtime_target_session"] == "2026-07-13"
    assert session["broker_order_date"] == "2026-07-12"


def test_phase15bu_fallback_conditions_pass_but_runtime_mutations_remain_blocked() -> None:
    evidence = _read_json("reports/phase_reports/phase15_bu/execution_evidence_authority.json")

    fallback = evidence["demo_fallback_contract"]
    assert fallback["scope"] == "Tachibana Demo acceptance only"
    assert fallback["production_applicable"] is False
    assert fallback["bt_bu_condition_status"] == "PASS"
    assert all(fallback["required_conditions"].values())

    mutation = evidence["runtime_mutation"]
    assert mutation["new_broker_write"] is False
    assert mutation["resubmit"] is False
    assert mutation["auto_cancel"] is False
    assert mutation["execution_normalization"] is False
    assert mutation["ledger_append"] is False
    assert mutation["current_apply"] is False
    assert mutation["notification_send"] is False
    assert mutation["production_write"] is False
    assert mutation["existing_runtime_mutated"] is False

    pending = evidence["pending_state"]
    assert pending["state"] == "SUBMITTED"
    assert pending["consumed"] is False
    assert pending["resubmit_allowed"] is False
