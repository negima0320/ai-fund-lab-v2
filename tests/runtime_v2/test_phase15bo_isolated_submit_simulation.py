from __future__ import annotations

import json
from pathlib import Path

from tests.runtime_v2.phase15bn_isolated_submit_fixture import build_isolated_submit_fixture
from tests.runtime_v2.phase15bo_submit_simulation import (
    run_phase15bo_acceptance,
    run_simulated_submit,
)


def test_phase15bo_simulated_accepted_updates_pending_and_ledger_without_network(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    evidence = run_phase15bo_acceptance(root, tmp_path / "evidence")
    pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    orders = _read_jsonl(root / "persistent_ledger" / "orders.jsonl")

    assert evidence["submit_result_classification"] == "ACCEPTED"
    assert evidence["network_called"] is False
    assert evidence["broker_write_performed"] is False
    assert evidence["real_broker_order_created"] is False
    assert evidence["pending_before_state"] == "APPROVED"
    assert evidence["pending_after_state"] == "CONSUMED"
    assert evidence["pending_consumed"] is True
    assert pending["consume"]["consumed"] is True
    assert len(orders) == 1
    assert orders[0]["status"] == "ACCEPTED"
    assert evidence["execution_created"] is False
    assert evidence["current_mutated"] is False


def test_phase15bo_command_and_request_payload_match_pending(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    result, adapter = run_simulated_submit(root, scenario="SIMULATED_ACCEPTED")
    payload = adapter.request_payloads[0]
    item = result.item_results[0]

    assert result.status == "PASS"
    assert item.symbol == "6522"
    assert item.side == "SELL"
    assert item.quantity == 100.0
    assert payload["issue_code"] == "6522"
    assert payload["side"] == "SELL"
    assert payload["quantity"] == 100.0
    assert payload["order_type"] == "MARKET"
    assert payload["price_type"] == "MARKET"
    assert payload["limit_price"] is None
    assert payload["target_session_date"] == "2026-07-09"
    assert payload["secret_saved"] is False
    assert payload["raw_request_saved"] is False
    assert payload["network_called"] is False


def test_phase15bo_idempotency_does_not_resubmit_or_duplicate_records(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    evidence = run_phase15bo_acceptance(root, tmp_path / "evidence")

    assert evidence["idempotency_status"] == "PASS_NO_RESUBMIT"
    assert evidence["second_run_result"]["transport_call_count"] == 0
    assert evidence["duplicate_order_count_delta"] == 0
    assert evidence["second_run_result"]["submitted_count"] == 0


def test_phase15bo_rejected_is_review_required_not_execution_or_current(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    before_current = (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")
    result, adapter = run_simulated_submit(root, scenario="SIMULATED_REJECTED")
    pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    orders = _read_jsonl(root / "persistent_ledger" / "orders.jsonl")

    assert adapter.submit_calls == 1
    assert result.status == "REVIEW_REQUIRED"
    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert pending["state"] == "REVIEW_REQUIRED"
    assert pending["consume"]["consumed"] is False
    assert orders[0]["status"] == "REJECTED"
    assert (root / "persistent_ledger" / "executions.jsonl").read_text(encoding="utf-8") == ""
    assert (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == before_current


def test_phase15bo_post_send_unknown_transitions_without_auto_resubmit(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    result, adapter = run_simulated_submit(root, scenario="SIMULATED_POST_SEND_UNKNOWN")
    pending = _read_json(root / "pending_order_plan" / "pending_order_plan.json")
    orders_before = _read_jsonl(root / "persistent_ledger" / "orders.jsonl")
    second_result, second_adapter = run_simulated_submit(root, scenario="SIMULATED_POST_SEND_UNKNOWN")
    orders_after = _read_jsonl(root / "persistent_ledger" / "orders.jsonl")

    assert adapter.submit_calls == 1
    assert result.status == "REVIEW_REQUIRED"
    assert result.unknown_count == 1
    assert pending["state"] == "POST_SEND_UNKNOWN"
    assert pending["consume"]["consumed"] is False
    assert orders_before[0]["status"] == "POST_SEND_UNKNOWN"
    assert second_result.status == "BLOCKED"
    assert "POST_SEND_UNKNOWN" in second_result.reason
    assert second_adapter.submit_calls == 0
    assert len(orders_after) == len(orders_before)


def test_phase15bo_existing_runtime_hashes_unchanged(tmp_path):
    before = _existing_runtime_hashes()
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    run_phase15bo_acceptance(root, tmp_path / "evidence")

    assert _existing_runtime_hashes() == before


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _existing_runtime_hashes() -> dict[str, str]:
    import hashlib

    paths = {
        "pending": Path(".runtime/pending_order_plan/pending_order_plan.json"),
        "safety": Path(".runtime/runtime_state/safety/latest_safety_decision.json"),
        "current": Path(".runtime/persistent_ledger/state.json"),
    }
    return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items() if path.is_file()}
