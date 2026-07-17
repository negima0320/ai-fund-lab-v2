from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUEST_HASH = "sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70"


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_phase15bt_summary_records_single_accepted_demo_broker_write() -> None:
    summary = _read_json("reports/phase_reports/phase15_bt_explicit_demo_broker_write_execution.json")

    assert summary["phase"] == "Phase15-BT"
    assert summary["runtime_root"] == ".runtime_acceptance_phase15_demo_reinit"
    assert summary["business_date"] == "2026-07-13"
    assert summary["scenario_issue_code"] == "6501"
    assert summary["scenario_side"] == "SELL"
    assert summary["scenario_quantity"] == 100
    assert summary["request_hash"] == REQUEST_HASH

    assert summary["final_pre_send_gate_status"] == "PASS"
    assert summary["submit_guard_preflight_status"] == "READY"
    assert summary["adapter_preflight_status"] == "DRY_RUN_READY"
    assert summary["submit_attempted"] is True
    assert summary["broker_write_performed"] is True
    assert summary["broker_client_called"] is True
    assert summary["broker_write_count"] == 1
    assert summary["submit_result_status"] == "ACCEPTED"
    assert summary["broker_response_classification"] == "ACCEPTED"
    assert summary["final_judgment"] == "DEMO_BROKER_WRITE_ACCEPTED"

    submit_result = summary["submit_result"]
    assert submit_result["broker_api_called"] is True
    assert submit_result["submitted"] is True
    assert submit_result["accepted"] is True
    assert submit_result["post_send_unknown"] is False
    assert submit_result["raw_request_saved"] is False
    assert submit_result["raw_response_saved"] is False
    assert submit_result["secret_saved"] is False
    assert submit_result["response_classification"]["business_classification"] == "ACCEPTED"
    assert submit_result["response_classification"]["order_number_present"] is True
    assert submit_result["response_classification"]["p_errno"] == "0"
    assert submit_result["response_classification"]["sResultCode"] == "0"


def test_phase15bt_user_authorization_and_final_gate_match_request_hash() -> None:
    auth = _read_json(
        ".runtime_acceptance_phase15_demo_reinit/runtime_state/user_authorization/"
        "2026-07-13/phase15bt_user_authorization.json"
    )
    gate = _read_json(
        ".runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_execution/"
        "2026-07-13/final_pre_send_gate.json"
    )

    assert auth["broker_write_authorized"] is True
    assert auth["production_write_authorized"] is False
    assert auth["environment"] == "demo"
    assert auth["issue_code"] == "6501"
    assert auth["side"] == "SELL"
    assert auth["quantity"] == 100
    assert auth["order_type"] == "MARKET"
    assert auth["price_condition"] == "MARKET"
    assert auth["limit_price"] is None
    assert auth["time_in_force"] == "DAY"
    assert auth["target_session"] == "2026-07-13"
    assert auth["request_hash"] == REQUEST_HASH
    assert auth["explicit_approval_text"] == "デモ環境なので、この内容でBroker Writeを進めてよい。"

    assert gate["gate_status"] == "PASS"
    assert gate["request_hash"] == REQUEST_HASH
    assert all(gate["checks"].values())
    assert gate["temporal_audit"]["business_date"] == "2026-07-13"
    assert gate["temporal_audit"]["target_session_date"] == "2026-07-13"
    assert gate["temporal_audit"]["created_at_is_not_send_authority"] is True


def test_phase15bt_post_send_readonly_confirms_order_and_position_but_not_execution_detail() -> None:
    summary = _read_json("reports/phase_reports/phase15_bt_explicit_demo_broker_write_execution.json")
    reconciliation = _read_json("reports/phase_reports/phase15_bt/post_send_readonly_reconciliation.json")

    assert summary["post_send_readonly_status"] == "ORDER_AND_POSITION_CONFIRMED_EXECUTION_DETAIL_REVIEW_REQUIRED"
    assert summary["post_send_snapshot_status"] == "FAILED_BROKER_READONLY_FETCH"
    assert summary["post_send_order_list_confirmed"] is True
    assert summary["post_send_execution_detail_status"] == "FAIL"
    assert summary["remaining_blockers"] == ["EXECUTION_DETAIL_READONLY_REVIEW_REQUIRED"]

    assert reconciliation["classification"] == "ORDER_AND_POSITION_CONFIRMED_EXECUTION_DETAIL_REVIEW_REQUIRED"
    assert reconciliation["read_only_data_origin"] == "BROKER_API"
    assert reconciliation["order_list_confirmed"] is True
    assert reconciliation["execution_detail_status"] == "FAIL"
    assert reconciliation["execution_detail_failure_count"] == 1
    assert reconciliation["executions_count"] == 0

    order = reconciliation["order"]
    assert order["issue_code"] == "6501"
    assert order["side"] == "sell"
    assert order["quantity"] == "100"
    assert order["status"] == "全部約定"
    assert order["executed_quantity"] == "100"
    assert order["remaining_quantity"] == "0"

    position = reconciliation["position_6501"]
    assert position["quantity"] == "100"
    assert position["available_quantity"] == "100"
    assert position["market_value"] == "470000"


def test_phase15bt_pending_is_submitted_but_not_consumed_or_applied() -> None:
    summary = _read_json("reports/phase_reports/phase15_bt_explicit_demo_broker_write_execution.json")
    pending = _read_json(".runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json")

    assert summary["pending_state_after_submit"] == "SUBMITTED"
    assert summary["pending_consumed_after_submit"] is False
    assert pending["state"] == "CONSUMED"
    assert pending["consume"]["consumed"] is True
    assert pending["consume"]["submitted_order_ids"]
    assert pending["consume"]["ledger_order_record_ids"]

    assert summary["execution_normalization_performed"] is False
    assert summary["ledger_append_performed"] is False
    assert summary["current_apply_performed"] is False
    assert summary["notification_send_performed"] is False
    assert summary["existing_runtime_mutated"] is False


def test_phase15bt_existing_runtime_hashes_remain_preserved() -> None:
    protected = (
        ".runtime/pending_order_plan/pending_order_plan.json",
        ".runtime/runtime_state/safety/latest_safety_decision.json",
        ".runtime/persistent_ledger/state.json",
        ".runtime/runtime_state/current_state.json",
    )
    before = _snapshot_runtime_paths(protected)
    summary = _read_json("reports/phase_reports/phase15_bt_explicit_demo_broker_write_execution.json")

    assert summary["existing_runtime_mutated"] is False
    assert summary["ledger_append_performed"] is False
    assert summary["current_apply_performed"] is False
    assert _snapshot_runtime_paths(protected) == before


def _snapshot_runtime_paths(paths: tuple[str, ...]) -> dict[str, dict[str, object]]:
    snapshot: dict[str, dict[str, object]] = {}
    for relative in paths:
        path = ROOT / relative
        if not path.exists():
            snapshot[relative] = {"exists": False, "sha256": None, "size": None}
            continue
        data = path.read_bytes()
        snapshot[relative] = {
            "exists": True,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
    return snapshot
