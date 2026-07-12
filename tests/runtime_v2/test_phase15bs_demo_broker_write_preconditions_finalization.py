from __future__ import annotations

import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_phase15bs_summary_ready_for_user_authorization_without_send() -> None:
    summary = _read_json("reports/phase_reports/phase15_bs_demo_broker_write_preconditions_finalization.json")

    assert summary["final_judgment"] == "DEMO_WRITE_READY_FOR_USER_AUTHORIZATION"
    assert summary["runtime_root"] == ".runtime_acceptance_phase15_demo_reinit"
    assert summary["scenario_side"] == "SELL"
    assert summary["scenario_issue_code"] == "6501"
    assert summary["scenario_quantity"] == 100
    assert summary["position_origin"] == "DEMO_PRELOADED_POSITION"
    assert summary["fresh_broker_snapshot_status"] == "PASS_WITH_WARNINGS"
    assert summary["fresh_open_order_status"] == "READY_EMPTY"
    assert summary["available_quantity"] == 200
    assert summary["broker_capability_status"] == "READY"
    assert summary["policy_status"] == "READY"
    assert summary["safety_submit_permission"] == "ALLOWED"
    assert summary["safety_broker_write_permission"] == "ALLOWED_FOR_ACCEPTANCE"
    assert summary["authoritative_pending_status"] == "APPROVED"
    assert summary["submit_preflight_status"] == "READY"
    assert summary["request_hash"].startswith("sha256:")
    assert summary["user_authorization_present"] is False
    assert summary["broker_client_called"] is False
    assert summary["broker_write_performed"] is False
    assert summary["submit_executed"] is False


def test_phase15bs_safety_scope_blocks_buy_and_allows_acceptance_broker_write() -> None:
    safety = _read_json(".runtime_acceptance_phase15_demo_reinit/runtime_state/safety/latest_safety_decision.json")
    permissions = safety["action_permissions"]

    assert safety["decision"] == "ALLOW"
    assert safety["safety_status"] == "PASS"
    assert permissions["sell_submit"] == "ALLOWED"
    assert permissions["broker_write"] == "ALLOWED_FOR_ACCEPTANCE"
    assert permissions["buy_submit"] == "BLOCKED"
    assert permissions["auto_sell"] == "BLOCKED"


def test_phase15bs_authoritative_pending_matches_approved_order_conditions() -> None:
    pending = _read_json(".runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json")
    item = pending["items"][0]
    conditions = pending["approval"]["approved_order_conditions"][item["pending_item_id"]]

    assert pending["state"] == "APPROVED"
    assert pending["consume"]["consumed"] is False
    assert pending["target_session_date"] == "2026-07-13"
    assert item["symbol"] == "6501"
    assert item["side"] == "SELL"
    assert item["quantity"] == 100.0
    assert item["order_type"] == "MARKET"
    assert conditions["issue_code"] == "6501"
    assert conditions["broker_issue_code"] == "6501"
    assert conditions["price_condition"] == "MARKET"
    assert conditions["limit_price"] is None
    assert conditions["time_in_force"] == "DAY"
    assert conditions["target_session"] == "2026-07-13"


def test_phase15bs_no_send_preflight_and_request_review_are_redacted() -> None:
    preflight = _read_json(
        ".runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_preconditions/2026-07-13/no_send_submit_preflight.json"
    )
    review = _read_json("reports/phase_reports/phase15_bs/final_request_review_redacted.json")

    assert preflight["submit_preflight_status"] == "READY"
    assert preflight["preflight_allowed"] is True
    assert preflight["request_payload_ready"] is True
    assert preflight["request_hash_generated"] is True
    assert preflight["submit_attempted"] is False
    assert preflight["broker_client_called"] is False
    assert preflight["broker_write_performed"] is False
    assert preflight["user_authorization_present"] is False
    assert review["status"] == "READY_FOR_USER_AUTHORIZATION"
    assert review["contains_credentials"] is False
    assert review["contains_plain_account_id"] is False
    assert review["contains_raw_token"] is False
    assert review["contains_secret_key"] is False
    assert review["contains_full_raw_request"] is False
    assert review["broker_write_performed"] is False
    assert review["user_authorization_present"] is False


def test_phase15bs_existing_runtime_hashes_are_preserved() -> None:
    expected = {
        ".runtime/pending_order_plan/pending_order_plan.json": "84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77",
        ".runtime/runtime_state/safety/latest_safety_decision.json": "c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7",
        ".runtime/persistent_ledger/state.json": "add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f",
    }

    for relative, expected_hash in expected.items():
        digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert digest == expected_hash
