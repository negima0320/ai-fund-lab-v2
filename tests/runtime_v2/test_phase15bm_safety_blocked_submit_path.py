from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision, safety_allows_action
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _approved_pending,
    _item,
    _position,
    _runtime_root,
    _write_broker_positions_snapshot,
    _write_current_state,
    _write_policy,
)


BUSINESS_DATE = "2026-07-09"


def test_phase15bm_safety_blocked_submit_path_never_calls_broker_or_consumes_pending(tmp_path):
    runtime_root, policy_path = _safety_blocked_sell_runtime(tmp_path)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    orders_path = runtime_root / "persistent_ledger" / "orders.jsonl"
    before_pending = pending_path.read_text(encoding="utf-8")
    before_orders = orders_path.read_text(encoding="utf-8")
    adapter = _CountingAdapter()

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "submit blocked before broker boundary; manual review required"
    assert result.submitted_count == 0
    assert result.demo_submit_executed is False
    assert result.pending_consumed is False
    assert result.submitted_order_ids == ()
    assert result.ledger_order_record_ids == ()
    assert adapter.preflight_calls == 0
    assert adapter.submit_calls == 0
    assert evidence["guard_decision"] == "BLOCKED"
    assert evidence["safety_guard_status"] == "BLOCKED"
    assert evidence["guard_reason"] == "HIGH_RISK_REVIEW"
    assert evidence["violated_policy"] == "safety_operation_guard"
    assert "POST_SEND_UNKNOWN" not in pending_path.read_text(encoding="utf-8")
    assert pending_path.read_text(encoding="utf-8") == before_pending
    assert orders_path.read_text(encoding="utf-8") == before_orders


def test_phase15bm_safety_blocked_retry_is_idempotent(tmp_path):
    runtime_root, policy_path = _safety_blocked_sell_runtime(tmp_path)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    before_pending = pending_path.read_text(encoding="utf-8")
    first = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_CountingAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    second = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_CountingAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert first.status == "REVIEW_REQUIRED"
    assert second.status == "REVIEW_REQUIRED"
    assert first.submitted_count == second.submitted_count == 0
    assert first.pending_consumed is second.pending_consumed is False
    assert pending_path.read_text(encoding="utf-8") == before_pending


def test_phase15bm_fail_closed_for_missing_stale_expired_and_action_scope_missing(tmp_path):
    cases = (
        ("missing", None, "REVIEW_REQUIRED"),
        ("stale", {"freshness_status": "STALE"}, "REVIEW_REQUIRED"),
        ("expired", {"freshness_status": "EXPIRED"}, "REVIEW_REQUIRED"),
        ("submit_scope_missing", {"action_permissions": {"broker_write": "BLOCKED"}}, "REVIEW_REQUIRED"),
    )
    for name, safety_updates, expected_status in cases:
        runtime_root, policy_path = _safety_blocked_sell_runtime(tmp_path / name)
        if safety_updates is None:
            (runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json").unlink()
        else:
            safety_path = runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json"
            payload = _read_json(safety_path)
            payload.update(safety_updates)
            _write_json(safety_path, payload)

        result = run_submit_pipeline(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode="demo",
            submit_enabled=True,
            job="submit",
            settings=_demo_settings(),
            adapter=_CountingAdapter(),
            capital_deployment_policy_path=policy_path,
        )

        evidence = result.submit_guard_item_evidence[0]
        assert result.status == expected_status
        assert result.submitted_count == 0
        assert result.pending_consumed is False
        assert evidence["guard_decision"] == "BLOCKED"
        assert evidence["violated_policy"] == "safety_operation_guard"


def test_phase15bm_broker_write_scope_missing_fails_closed(tmp_path):
    runtime_root, _ = _safety_blocked_sell_runtime(tmp_path)
    safety_path = runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json"
    payload = _read_json(safety_path)
    payload["decision"] = "ALLOW"
    payload["review_required"] = False
    payload["block_submit"] = False
    payload["action_permissions"] = {"sell_submit": "ALLOWED"}
    _write_json(safety_path, payload)

    decision = load_runtime_safety_decision(runtime_root=runtime_root, business_date=BUSINESS_DATE, mode="demo")
    allowed, status, reason = safety_allows_action(decision, action="broker_write")

    assert allowed is False
    assert status == "REVIEW_REQUIRED"
    assert reason == "HIGH_RISK_REVIEW"


def test_phase15bm_order_condition_unresolved_blocks_submit_before_broker(tmp_path):
    runtime_root, policy_path = _safety_blocked_sell_runtime(tmp_path)
    _write_safety_allow(runtime_root)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending = _approved_pending(
        (
            replace(
                _item(
                    pending_item_id="sell-4591",
                    symbol="4591",
                    side="SELL",
                    quantity=100,
                    estimated_price=100,
                    estimated_amount=10_000,
                ),
                order_type="REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY",
            ),
        ),
        policy_path=policy_path,
    )
    write_pending_order_plan(pending_path, pending)
    before_pending = pending_path.read_text(encoding="utf-8")
    adapter = _CountingAdapter()

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "BLOCKED"
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert adapter.preflight_calls == 0
    assert adapter.submit_calls == 0
    assert evidence["blocked_at_submit_reason"] == "order condition authority review required"
    assert pending_path.read_text(encoding="utf-8") == before_pending


def test_phase15bm_isolated_fixture_does_not_modify_existing_runtime_root():
    root = Path(".runtime")
    pending_path = root / "pending_order_plan" / "pending_order_plan.json"
    apply_candidate_path = (
        root
        / "runtime_state"
        / "authoritative_pending_apply_candidate"
        / "2026-07-10"
        / "apply-candidate-a6d308ef3dac7170.json"
    )
    assert pending_path.is_file()
    assert apply_candidate_path.is_file()
    pending = _read_json(pending_path)
    candidate = _read_json(apply_candidate_path)
    assert pending["state"] == "EMPTY"
    assert pending["active_pending"] is False
    assert candidate["authoritative_pending_mutated"] is False
    assert candidate["submit_executed"] is False
    assert candidate["broker_write_performed"] is False


def _safety_blocked_sell_runtime(tmp_path: Path) -> tuple[Path, Path]:
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_current_state(
        runtime_root,
        positions=[_position("4591", quantity=5000, price=100)],
        cash=500_000,
        market_value=500_000,
    )
    _write_broker_positions_snapshot(runtime_root, symbol="4591", quantity=5000, available_quantity=5000)
    _write_safety_blocked(runtime_root)
    pending = _approved_pending(
        (
            _item(
                pending_item_id="sell-4591",
                symbol="4591",
                side="SELL",
                quantity=5000,
                estimated_price=100,
                estimated_amount=500_000,
            ),
        ),
        policy_path=policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    return runtime_root, policy_path


def _write_safety_blocked(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15bm-blocked",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase15bm_fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "REVIEW_REQUIRED",
            "reason": "HIGH_RISK_REVIEW",
            "review_required": True,
            "block_buy": True,
            "block_sell": False,
            "block_submit": True,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T08:00:00+09:00",
            "expires_at": "2026-07-09T15:00:00+09:00",
            "action_permissions": {
                "sell_submit": "BLOCKED",
                "broker_write": "BLOCKED",
            },
        },
    )


def _write_safety_allow(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15bm-allow",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase15bm_fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15bm isolated allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T08:00:00+09:00",
            "expires_at": "2026-07-09T15:00:00+09:00",
            "action_permissions": {
                "sell_submit": "ALLOWED",
                "broker_write": "ALLOWED",
            },
        },
    )


class _CountingAdapter:
    def __init__(self) -> None:
        self.preflight_calls = 0
        self.submit_calls = 0

    def preflight(self, command):
        self.preflight_calls += 1
        raise AssertionError("broker preflight must not be called")

    def submit(self, command):
        self.submit_calls += 1
        raise AssertionError("broker submit must not be called")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
