from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _read_jsonl(path: str) -> list[dict]:
    full = ROOT / path
    return [json.loads(line) for line in full.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_phase15bv_report_accepts_current_apply_demo_only() -> None:
    report = _read_json("reports/phase_reports/phase15_bv_execution_normalization_current_apply.json")

    assert report["final_judgment"] == "CURRENT_APPLY_ACCEPTED_DEMO_ONLY"
    assert report["execution_source"] == "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1"
    assert report["production_equivalent"] is False
    assert report["runtime_mutation"]["existing_dot_runtime_mutated"] is False
    assert report["runtime_mutation"]["new_broker_write"] is False
    assert report["runtime_mutation"]["resubmit"] is False
    assert report["runtime_mutation"]["notification_send"] is False
    assert report["runtime_mutation"]["production_write"] is False


def test_phase15bv_execution_normalization_keeps_execution_and_valuation_prices_separate() -> None:
    normalized = _read_json("reports/phase_reports/phase15_bv/execution_normalization.json")

    assert normalized["issue_code"] == "6501"
    assert normalized["side"] == "SELL"
    assert normalized["quantity"] == 100.0
    assert normalized["execution_price"] == 100.0
    assert normalized["valuation_price"] == 4700.0
    assert normalized["valuation_price_used_as_execution_price"] is False
    assert normalized["execution_equivalent"] is True
    assert normalized["production_equivalent"] is False
    assert normalized["execution_source"] == "DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1"


def test_phase15bv_ledger_records_are_appended_once() -> None:
    base = ".runtime_acceptance_phase15_demo_reinit/persistent_ledger"

    assert len(_read_jsonl(f"{base}/orders.jsonl")) == 1
    assert len(_read_jsonl(f"{base}/executions.jsonl")) == 1
    assert len(_read_jsonl(f"{base}/positions.jsonl")) == 1
    assert len(_read_jsonl(f"{base}/cash.jsonl")) == 1
    assert len(_read_jsonl(f"{base}/events.jsonl")) == 1

    execution = _read_jsonl(f"{base}/executions.jsonl")[0]
    assert execution["ledger_record_id"] == "ledger-execution-phase15bv-6501-sell-100"
    assert execution["execution_evidence_type"] == "demo_orderlist_position_execution_equivalent"
    assert execution["execution_equivalent"] is True
    assert execution["production_equivalent"] is False
    assert execution["price"] == 100.0
    assert execution["market_price"] == 4700.0
    assert execution["cash_effect"] == 10000.0


def test_phase15bv_current_and_runtime_state_reflect_apply() -> None:
    current = _read_json(".runtime_acceptance_phase15_demo_reinit/persistent_ledger/state.json")
    runtime_state = _read_json(".runtime_acceptance_phase15_demo_reinit/runtime_state/current_state.json")

    assert current["current_version"] == "phase15bv_current_v1"
    assert current["production_equivalent"] is False
    assert current["positions"][0]["symbol"] == "6501"
    assert current["positions"][0]["quantity"] == 100.0
    assert current["positions"][0]["execution_price"] == 100.0
    assert current["positions"][0]["valuation_price"] == 4700.0
    assert current["cash"] == 17704424.0
    assert current["cash_delta"] == 10000.0
    assert current["buying_power"] == 20009824.0
    assert current["market_value"] == 470000.0
    assert current["total_equity"] == 18174424.0
    assert current["phase15_bv_current_apply"]["applied"] is True

    assert runtime_state["state"] == "CURRENT_APPLIED"
    assert runtime_state["runtime_state_version"] == "phase15bv_runtime_state_v1"
    assert runtime_state["current_version"] == "phase15bv_current_v1"
    assert runtime_state["current_hash"] == "sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4"
    assert runtime_state["execution_reference"] == "phase15bv-demo-execution-equivalent-6501-sell-100"


def test_phase15bv_pending_consumed_after_current_apply() -> None:
    pending = _read_json(".runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json")

    assert pending["state"] == "CONSUMED"
    assert pending["consume"]["consumed"] is True
    assert pending["consume"]["consume_reason"] == "phase15bv_execution_normalization_ledger_current_apply_completed"
    assert pending["consume"]["ledger_order_record_ids"] == ["ledger-order-phase15bv-6501-sell-100"]
    assert pending["items"][0]["state"] == "CURRENT_APPLIED"
    assert pending["items"][0]["execution_id"] == "phase15bv-demo-execution-equivalent-6501-sell-100"


def test_phase15bv_idempotency_second_apply_is_noop() -> None:
    attempt1 = _read_json("reports/phase_reports/phase15_bv/apply_attempt_1.json")
    attempt2 = _read_json("reports/phase_reports/phase15_bv/apply_attempt_2.json")

    assert attempt1["status"] == "APPLIED"
    assert attempt1["ledger_records_appended"] == 5
    assert attempt1["current_hash_changed"] is True

    assert attempt2["status"] == "NOOP_ALREADY_APPLIED"
    assert attempt2["ledger_records_appended"] == 0
    assert attempt2["idempotent"] is True
    assert attempt2["before"]["current_hash"] == attempt2["after"]["current_hash"]
    assert attempt2["after"]["position_6501_quantity"] == 100.0
    assert attempt2["after"]["cash"] == 17704424.0
