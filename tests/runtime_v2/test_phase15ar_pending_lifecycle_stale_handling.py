from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.pending.lifecycle import PENDING_STATE_CONTRACT
from ai_fund_lab_v2.runtime_v2.pending.lifecycle_runner import run_pending_lifecycle_review
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan


BUSINESS_DATE = "2026-07-10"
TARGET_DATE = "2026-07-09"


def test_phase15ar_stale_approved_pending_expires_to_history_and_empty_slot(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(runtime_root, pending_plan_id="pending-expire", target_date=TARGET_DATE)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )

    history_path = Path(result.manifest_fields["history_path"])
    slot = _load_json(pending_path)
    history = _load_json(history_path)

    assert result.status == "EXPIRED"
    assert result.manifest_fields["previous_state"] == "APPROVED"
    assert result.manifest_fields["new_state"] == "EXPIRED"
    assert result.manifest_fields["submit_attempt_detected"] is False
    assert slot["status"] == "EMPTY"
    assert slot["active_pending"] is False
    assert slot["last_pending_plan_id"] == "pending-expire"
    assert history["previous_state"] == "APPROVED"
    assert history["new_state"] == "EXPIRED"
    assert history["source_pending_path"] == str(pending_path)
    assert history["submit_attempt_detected"] is False


def test_phase29_l20d_historical_ca_quarantine_buy_expires_to_history_and_empty_slot(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(
        runtime_root,
        pending_plan_id="pending-ca-buy",
        target_date=TARGET_DATE,
        mode="historical",
        symbol="76920",
        side="BUY",
        quantity=2000,
    )
    _write_historical_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-ca-buy",
        symbol="76920",
        side="BUY",
        quantity=2000,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    slot = _load_json(pending_path)
    history = _load_json(Path(result.manifest_fields["history_path"]))

    assert result.status == "EXPIRED"
    assert result.reason == "historical_corporate_action_quarantine_not_submitted_non_retryable"
    assert slot["status"] == "EMPTY"
    assert slot["active_pending"] is False
    assert slot["last_pending_plan_id"] == "pending-ca-buy"
    assert history["new_state"] == "EXPIRED"
    assert history["pending_payload"]["items"][0]["symbol"] == "76920"
    ca = history["corporate_action_quarantine_terminalization"]
    assert ca["status"] == "PASS"
    assert ca["checks"]["production_never"] is True
    assert ca["checks"]["submitted_count_zero"] is True
    assert ca["checks"]["no_broker_write"] is True


def test_phase29_l20d_historical_ca_quarantine_sell_expires_to_history_and_empty_slot(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(
        runtime_root,
        pending_plan_id="pending-ca-sell",
        target_date=TARGET_DATE,
        mode="historical",
        symbol="76920",
        side="SELL",
        quantity=700,
    )
    _write_historical_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-ca-sell",
        symbol="76920",
        side="SELL",
        quantity=700,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "EXPIRED"
    assert result.manifest_fields["new_state"] == "EXPIRED"
    assert _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")["state"] == "EMPTY"


def test_phase29_l20d_historical_ca_quarantine_empty_slot_does_not_block_next_day_readiness(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(
        runtime_root,
        pending_plan_id="pending-ca-next-day",
        target_date=TARGET_DATE,
        mode="historical",
        symbol="76920",
        side="BUY",
        quantity=2000,
    )
    _write_historical_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-ca-next-day",
        symbol="76920",
        side="BUY",
        quantity=2000,
    )
    run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )
    _write_broker_snapshot(runtime_root)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="sell_planning",
        now=_now(),
    )

    assert result.payload["pending_status"] == "READY"
    assert "stale_approved_pending_exists" not in result.payload["review_reasons"]


def test_phase29_l21t_w_buy_item_scoped_review_no_submission_terminalizes_without_broker_write(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_buy_item_scoped_review_pending(runtime_root, target_date=TARGET_DATE)
    _write_buy_item_scoped_review_submit_no_submission_manifest(runtime_root, business_date=TARGET_DATE)
    _write_buy_item_scoped_review_execution_no_action_manifest(runtime_root, business_date=TARGET_DATE)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T15:30:00+09:00"),
    )

    slot = _load_json(pending_path)
    history = _load_json(Path(result.manifest_fields["history_path"]))
    authority = result.manifest_fields["buy_item_scoped_review_no_submission_terminalization"]

    assert result.status == "EXPIRED"
    assert result.reason == "buy_item_scoped_review_no_submission_terminal"
    assert slot["state"] == "EMPTY"
    assert slot["active_pending"] is False
    assert slot["last_pending_plan_id"] == "pending-buy-item-review"
    assert history["new_state"] == "EXPIRED"
    assert history["pending_payload"]["review_scope"] == "BUY_ITEM_SCOPED_REVIEW"
    assert authority["status"] == "PASS"
    assert authority["pending_plan_id"] == "pending-buy-item-review"
    assert authority["approved_item_ids"] == []
    assert authority["review_required_buy_item_ids"] == ["buy-review-76920"]
    assert authority["sell_continuation_allowed"] is True
    assert authority["submit_status"] == "CURRENT_STATE_LOADED"
    assert authority["execution_status"] == "PASS"
    assert authority["pending_lifecycle_terminal_status"] == "EXPIRED"
    assert authority["broker_write_performed"] is False
    assert authority["fail_open_used"] is False
    assert authority["partial_buy_submit_allowed"] is False
    assert authority["reviewed_buy_submitted"] is False
    assert history["buy_item_scoped_review_no_submission_terminalization"]["status"] == "PASS"


def test_phase29_l21t_w_existing_review_history_does_not_block_repaired_terminal_history(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_buy_item_scoped_review_pending(runtime_root, target_date=TARGET_DATE)
    original_history = runtime_root / "pending_order_plan" / "history" / TARGET_DATE / "pending-buy-item-review.json"
    _write_json(
        original_history,
        {
            "pending_plan_id": "pending-buy-item-review",
            "previous_state": "REVIEW_REQUIRED",
            "new_state": "REVIEW_REQUIRED",
            "transition_reason": "pending_state_review_required_requires_operator_review",
        },
    )
    _write_buy_item_scoped_review_submit_no_submission_manifest(runtime_root, business_date=TARGET_DATE)
    _write_buy_item_scoped_review_execution_no_action_manifest(runtime_root, business_date=TARGET_DATE)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T15:30:00+09:00"),
    )

    repaired_history = Path(result.manifest_fields["history_path"])
    slot = _load_json(pending_path)

    assert result.status == "EXPIRED"
    assert repaired_history != original_history
    assert _load_json(original_history)["new_state"] == "REVIEW_REQUIRED"
    assert _load_json(repaired_history)["new_state"] == "EXPIRED"
    assert slot["history_path"] == str(repaired_history)


def test_phase29_l21t_w_buy_item_scoped_review_without_sell_continuation_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_buy_item_scoped_review_pending(
        runtime_root,
        target_date=TARGET_DATE,
        sell_continuation_allowed=False,
    )
    _write_buy_item_scoped_review_submit_no_submission_manifest(runtime_root, business_date=TARGET_DATE)
    _write_buy_item_scoped_review_execution_no_action_manifest(runtime_root, business_date=TARGET_DATE)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T15:30:00+09:00"),
    )

    slot = _load_json(pending_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "buy_item_scoped_review_pending_shape_invalid"
    assert slot["state"] == "REVIEW_REQUIRED"
    assert slot["active_pending"] is True


def test_phase29_l21t_w_global_review_required_pending_remains_fail_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(runtime_root, pending_plan_id="pending-global-review", target_date=TARGET_DATE)
    pending = _load_json(pending_path)
    pending["state"] = "REVIEW_REQUIRED"
    pending["status"] = "REVIEW_REQUIRED"
    pending["review_scope"] = "GLOBAL_REVIEW_REQUIRED"
    pending["approved_item_ids"] = []
    pending["approval"]["approved_item_ids"] = []
    _write_json(pending_path, pending)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T15:30:00+09:00"),
    )

    slot = _load_json(pending_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pending_state_review_required_requires_operator_review"
    assert slot["state"] == "REVIEW_REQUIRED"
    assert slot["active_pending"] is True


def test_phase29_l21t_w_missing_execution_no_action_authority_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_buy_item_scoped_review_pending(runtime_root, target_date=TARGET_DATE)
    _write_buy_item_scoped_review_submit_no_submission_manifest(runtime_root, business_date=TARGET_DATE)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T15:30:00+09:00"),
    )

    slot = _load_json(pending_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "buy_item_scoped_review_execution_no_action_authority_missing"
    assert slot["state"] == "REVIEW_REQUIRED"
    assert slot["active_pending"] is True


def test_phase29_l20d_mixed_quarantine_and_submitted_order_is_not_whole_plan_expired(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(
        runtime_root,
        pending_plan_id="pending-ca-mixed",
        target_date=TARGET_DATE,
        mode="historical",
        symbol="76920",
        side="BUY",
        quantity=2000,
    )
    _write_historical_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-ca-mixed",
        symbol="76920",
        side="BUY",
        quantity=2000,
        submitted_count=1,
        pass_item=True,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "possible_unknown_submit_outcome"
    slot = _load_json(pending_path)
    assert slot["state"] == "REVIEW_REQUIRED"
    assert slot["active_pending"] is True


def test_phase29_l20h_buy_quarantine_and_sell_filled_terminalizes_item_outcomes(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_mixed_pending(
        runtime_root,
        pending_plan_id="pending-l20h-buy-q-sell-fill",
        target_date=TARGET_DATE,
        quarantined_side="BUY",
        filled_side="SELL",
    )
    _write_mixed_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-l20h-buy-q-sell-fill",
        quarantined_symbol="76920",
        quarantined_side="BUY",
        filled_symbol="41650",
        filled_side="SELL",
    )
    _append_filled_ledger_order(
        runtime_root,
        business_date=TARGET_DATE,
        pending_item_id="item-filled",
        symbol="41650",
        side="SELL",
        quantity=200,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    slot = _load_json(pending_path)
    history = _load_json(Path(result.manifest_fields["history_path"]))
    authority = history["item_lifecycle_authority"]
    outcomes = {item["pending_item_id"]: item["outcome"] for item in authority["item_outcomes"]}

    assert result.status == "CONSUMED"
    assert result.reason == "historical_mixed_filled_and_ca_quarantined_items_terminal"
    assert slot["state"] == "EMPTY"
    assert slot["active_pending"] is False
    assert slot["last_terminal_state"] == "CONSUMED"
    assert outcomes == {"item-quarantine": "QUARANTINED_NOT_SUBMITTED", "item-filled": "FILLED"}
    assert authority["derived_plan_state"] == "CONSUMED"


def test_phase29_l20h_buy_filled_and_sell_quarantine_terminalizes_item_outcomes(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_mixed_pending(
        runtime_root,
        pending_plan_id="pending-l20h-buy-fill-sell-q",
        target_date=TARGET_DATE,
        quarantined_side="SELL",
        filled_side="BUY",
        quarantined_symbol="76920",
        filled_symbol="41650",
    )
    _write_mixed_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-l20h-buy-fill-sell-q",
        quarantined_symbol="76920",
        quarantined_side="SELL",
        filled_symbol="41650",
        filled_side="BUY",
    )
    _append_filled_ledger_order(
        runtime_root,
        business_date=TARGET_DATE,
        pending_item_id="item-filled",
        symbol="41650",
        side="BUY",
        quantity=200,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "CONSUMED"
    outcomes = {
        item["pending_item_id"]: item["outcome"]
        for item in result.manifest_fields["item_lifecycle_authority"]["item_outcomes"]
    }
    assert outcomes["item-filled"] == "FILLED"
    assert outcomes["item-quarantine"] == "QUARANTINED_NOT_SUBMITTED"


def test_phase29_l20h_post_send_unknown_plus_filled_sibling_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_mixed_pending(
        runtime_root,
        pending_plan_id="pending-l20h-unknown",
        target_date=TARGET_DATE,
    )
    _write_mixed_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-l20h-unknown",
        final_state="POST_SEND_UNKNOWN",
    )
    _append_filled_ledger_order(
        runtime_root,
        business_date=TARGET_DATE,
        pending_item_id="item-filled",
        symbol="41650",
        side="SELL",
        quantity=200,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert _load_json(pending_path)["state"] == "REVIEW_REQUIRED"


def test_phase29_l20h_generic_blocked_plus_filled_sibling_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_mixed_pending(
        runtime_root,
        pending_plan_id="pending-l20h-generic",
        target_date=TARGET_DATE,
    )
    _write_mixed_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-l20h-generic",
        guard_reason="aggregate_submit_feasibility_failed",
        violated_policy="submit_guard_canonical_evidence_revalidation",
    )
    _append_filled_ledger_order(
        runtime_root,
        business_date=TARGET_DATE,
        pending_item_id="item-filled",
        symbol="41650",
        side="SELL",
        quantity=200,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert _load_json(pending_path)["state"] == "REVIEW_REQUIRED"


def test_phase29_l20h_demo_unresolved_ca_plus_filled_sibling_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_mixed_pending(
        runtime_root,
        pending_plan_id="pending-l20h-demo",
        target_date=TARGET_DATE,
        mode="demo",
    )
    _write_mixed_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-l20h-demo",
    )
    _append_filled_ledger_order(
        runtime_root,
        business_date=TARGET_DATE,
        pending_item_id="item-filled",
        symbol="41650",
        side="SELL",
        quantity=200,
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert _load_json(pending_path)["state"] == "REVIEW_REQUIRED"


def test_phase29_l20d_generic_review_required_quarantine_payload_does_not_auto_expire(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(
        runtime_root,
        pending_plan_id="pending-ca-generic",
        target_date=TARGET_DATE,
        mode="historical",
        symbol="76920",
        side="BUY",
        quantity=2000,
    )
    _write_historical_ca_quarantine_submit_authority(
        runtime_root,
        business_date=TARGET_DATE,
        pending_plan_id="pending-ca-generic",
        symbol="76920",
        side="BUY",
        quantity=2000,
        guard_reason="aggregate_submit_feasibility_failed",
        violated_policy="submit_guard_canonical_evidence_revalidation",
    )

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=TARGET_DATE,
        mode="historical",
        action="review",
        now=datetime.fromisoformat(TARGET_DATE + "T09:00:00+09:00"),
    )

    assert result.status == "NOOP"
    assert _load_json(pending_path)["state"] == "APPROVED"


def test_phase15ar_data_readiness_pending_ready_after_expiration(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(runtime_root, pending_plan_id="pending-expire", target_date=TARGET_DATE)
    run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )
    _write_broker_snapshot(runtime_root)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="sell_planning",
        now=_now(),
    )

    assert result.status == "READY"
    assert result.payload["pending_status"] == "READY"


def test_phase15ar_unknown_submit_attempt_moves_to_review_required_not_empty(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(runtime_root, pending_plan_id="pending-unknown", target_date=TARGET_DATE)
    _write_submit_manifest(runtime_root, pending_plan_id="pending-unknown")

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )

    slot = _load_json(pending_path)
    history = _load_json(Path(result.manifest_fields["history_path"]))

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "possible_unknown_submit_outcome"
    assert result.manifest_fields["submit_attempt_detected"] is True
    assert result.manifest_fields["unknown_submit_risk"] is True
    assert slot["state"] == "REVIEW_REQUIRED"
    assert slot["active_pending"] is True
    assert history["new_state"] == "REVIEW_REQUIRED"


def test_phase15ar_unknown_submit_risk_keeps_data_readiness_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(runtime_root, pending_plan_id="pending-unknown", target_date=TARGET_DATE)
    _write_submit_manifest(runtime_root, pending_plan_id="pending-unknown")
    run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )
    _write_broker_snapshot(runtime_root)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="sell_planning",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["pending_status"] == "REVIEW_REQUIRED"


def test_phase15ar_valid_today_approved_pending_noop(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(runtime_root, pending_plan_id="pending-today", target_date=BUSINESS_DATE)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )

    slot = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    assert result.status == "NOOP"
    assert result.reason == "active_pending_not_stale"
    assert slot["state"] == "APPROVED"
    assert result.manifest_fields["idempotent_noop"] is True


def test_phase16d_historical_evaluation_time_prevents_wall_clock_expiration(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(runtime_root, pending_plan_id="pending-2021", target_date="2021-07-05")
    evaluation_time = datetime.fromisoformat("2021-07-05T09:00:00+09:00")

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date="2021-07-05",
        mode="demo",
        action="review",
        now=evaluation_time,
    )

    slot = _load_json(pending_path)

    assert result.status == "NOOP"
    assert result.reason == "active_pending_not_stale"
    assert result.manifest_fields["transitioned_at"] == evaluation_time.astimezone(timezone.utc).isoformat()
    assert slot["state"] == "APPROVED"
    assert slot["approval"]["approval_expires_at"] == "2021-07-05T15:00:00+09:00"


def test_phase16d_historical_evaluation_time_expires_after_approval_deadline(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_pending(runtime_root, pending_plan_id="pending-2021-expired", target_date="2021-07-05")
    evaluation_time = datetime.fromisoformat("2021-07-05T16:00:00+09:00")

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date="2021-07-05",
        mode="demo",
        action="review",
        now=evaluation_time,
    )

    slot = _load_json(pending_path)
    history = _load_json(Path(result.manifest_fields["history_path"]))

    assert result.status == "EXPIRED"
    assert result.reason == "approval_expired"
    assert result.manifest_fields["transitioned_at"] == evaluation_time.astimezone(timezone.utc).isoformat()
    assert slot["status"] == "EMPTY"
    assert history["transitioned_at"] == evaluation_time.astimezone(timezone.utc).isoformat()


def test_phase15ar_empty_slot_is_reader_valid_and_noop(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "status": "EMPTY",
            "state": "EMPTY",
            "active_pending": False,
            "last_pending_plan_id": "pending-old",
            "last_terminal_state": "EXPIRED",
            "last_transition_at": _now().isoformat(),
            "history_path": "history.json",
        },
    )

    read = read_pending_order_plan(mode="demo", environment="demo", base_dir=runtime_root.parent)
    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )

    assert read.valid is True
    assert read.classification == "EMPTY"
    assert result.status == "NOOP"
    assert result.manifest_fields["idempotent_noop"] is True


def test_phase15ar_cli_manifest_report_notification_include_lifecycle(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(runtime_root, pending_plan_id="pending-cli", target_date=TARGET_DATE)
    evaluation_time = "2026-07-10T02:03:04+00:00"

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "pending_lifecycle",
            "--pending-action",
            "review",
            "--business-date",
            BUSINESS_DATE,
            "--evaluation-time",
            evaluation_time,
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
        ]
    )

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    report = _load_json(tmp_path / "reports" / "runtime_v2" / BUSINESS_DATE / "runtime_report.json")
    notification = _load_json(tmp_path / "reports" / "runtime_v2" / BUSINESS_DATE / "notification_payload.json")

    assert exit_code == 0
    assert manifest["pending_lifecycle_status"] == "EXPIRED"
    assert manifest["new_state"] == "EXPIRED"
    assert manifest["transitioned_at"] == evaluation_time
    assert report["pending_lifecycle"]["pending_lifecycle_status"] == "EXPIRED"
    assert notification["pending_lifecycle_status"] == "EXPIRED"
    assert notification["notification_sent"] is False


def test_phase15ar_repeated_expiration_is_idempotent_noop(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_pending(runtime_root, pending_plan_id="pending-idempotent", target_date=TARGET_DATE)
    first = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )
    second = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        action="review",
        now=_now(),
    )

    assert first.status == "EXPIRED"
    assert second.status == "NOOP"
    assert second.manifest_fields["idempotent_noop"] is True
    assert Path(first.manifest_fields["history_path"]).read_text(encoding="utf-8")


def test_phase15ar_state_contract_marks_terminal_submit_blocked():
    for state in ("EXPIRED", "CANCELLED", "REJECTED", "CONSUMED", "SUPERSEDED", "EMPTY"):
        assert PENDING_STATE_CONTRACT[state]["terminal"] is True
        assert PENDING_STATE_CONTRACT[state]["submit_allowed"] is False
    assert PENDING_STATE_CONTRACT["REVIEW_REQUIRED"]["submit_allowed"] is False
    assert PENDING_STATE_CONTRACT["APPROVED"]["submit_allowed"] is True


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15ar",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "business_date": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase15ar-test",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "environment": "demo",
            "source": "phase15ar_fixture",
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
        },
    )
    _write_safety(root)
    _write_market_evidence(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_pending(
    root: Path,
    *,
    pending_plan_id: str,
    target_date: str,
    mode: str = "demo",
    symbol: str = "7203",
    side: str = "SELL",
    quantity: int = 100,
) -> Path:
    path = root / "pending_order_plan" / "pending_order_plan.json"
    approval_expires_at = target_date + "T15:00:00+09:00"
    _write_json(
        path,
        {
            "schema_version": "1",
            "pending_plan_id": pending_plan_id,
            "state": "APPROVED",
            "status": "APPROVED",
            "active_pending": True,
            "environment": mode,
            "created_at": TARGET_DATE + "T08:00:00+09:00",
            "updated_at": TARGET_DATE + "T08:10:00+09:00",
            "plan_created_date": TARGET_DATE,
            "intended_submit_date": target_date,
            "target_session_date": target_date,
            "source_order_plan": {
                "order_plan_id": "order-plan-" + pending_plan_id,
                "path": "order_plan.json",
                "artifact_hash": "hash-order-plan",
            },
            "approval": {
                "approval_path": "approval.json",
                "approval_hash": "hash-approval",
                "approval_status": "APPROVED",
                "approved_item_ids": ["item-1"],
                "approval_expires_at": approval_expires_at,
                "policy_version": "capital_deployment_v1",
                "pending_policy_hash": "hash-policy",
                "safety_decision_id": "safety-phase15ar",
                "safety_policy_version": "safety_operation_guard_v1",
            },
            "approved_item_ids": ["item-1"],
            "items": [
                {
                    "pending_item_id": "item-1",
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "order_type": "MARKET",
                    "estimated_price": 1000,
                    "estimated_amount": quantity * 1000,
                    "approved": True,
                    "state": "APPROVED",
                }
            ],
            "submit_constraints": {"expires_at": approval_expires_at},
            "consume": {"consumed": False, "submitted_order_ids": [], "ledger_order_record_ids": []},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "policy_version": "capital_deployment_v1",
            "pending_policy_hash": "hash-policy",
            "safety_decision_id": "safety-phase15ar",
        },
    )
    return path


def _write_buy_item_scoped_review_pending(
    root: Path,
    *,
    target_date: str,
    sell_continuation_allowed: bool = True,
) -> Path:
    path = _write_pending(
        root,
        pending_plan_id="pending-buy-item-review",
        target_date=target_date,
        symbol="65500",
        side="BUY",
        quantity=700,
    )
    payload = _load_json(path)
    payload["state"] = "REVIEW_REQUIRED"
    payload["status"] = "REVIEW_REQUIRED"
    payload["plan_overall_status"] = "REVIEW_REQUIRED"
    payload["approved_item_ids"] = []
    payload["approved_buy_item_ids"] = []
    payload["approved_sell_item_ids"] = []
    payload["review_required_buy_item_ids"] = ["buy-review-76920"]
    payload["review_required_sell_item_ids"] = []
    payload["review_scope"] = "BUY_ITEM_SCOPED_REVIEW"
    payload["review_scope_reason"] = "reserved notional exceeds dynamic cash capacity"
    payload["sell_continuation_allowed"] = sell_continuation_allowed
    payload["approval"]["approved_item_ids"] = []
    payload["items"] = [
        {
            "pending_item_id": "buy-pass-65500",
            "symbol": "65500",
            "side": "BUY",
            "quantity": 700,
            "order_type": "MARKET",
            "estimated_price": 244,
            "estimated_amount": 170800,
            "approved": False,
            "state": "REVIEW_REQUIRED",
            "feasibility_status": "PASS",
            "batch_submit_status": "BLOCKED_BY_BATCH_REVIEW",
            "item_review_reason": "batch_submit_blocked_by_item_scoped_review",
        },
        {
            "pending_item_id": "buy-review-76920",
            "symbol": "76920",
            "side": "BUY",
            "quantity": 1200,
            "order_type": "MARKET",
            "estimated_price": 183.3,
            "estimated_amount": 219960,
            "approved": False,
            "state": "REVIEW_REQUIRED",
            "feasibility_status": "REVIEW_REQUIRED",
            "batch_submit_status": "ITEM_REVIEW_REQUIRED",
            "item_review_reason": "reserved notional exceeds dynamic cash capacity",
        },
    ]
    _write_json(path, payload)
    return path


def _write_buy_item_scoped_review_submit_no_submission_manifest(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-l21t-w.json",
        {
            "schema_version": "1",
            "job": "submit",
            "business_date": business_date,
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            "pending_read_valid": True,
            "pending_classification": "VALID",
            "pending_active": True,
            "pending_plan_present": True,
            "pending_item_count": 2,
            "no_action_reason": "buy_item_scoped_review_no_approved_items",
            "no_order_authority_status": "PASS",
            "no_order_authority_reason": "buy_item_scoped_review_no_approved_items",
            "no_order_authority_evidence": {
                "status": "PASS",
                "authority_type": "BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION",
                "pending_plan_id": "pending-buy-item-review",
                "state": "REVIEW_REQUIRED",
                "review_scope": "BUY_ITEM_SCOPED_REVIEW",
                "approved_item_ids": [],
                "approved_buy_item_ids": [],
                "approved_sell_item_ids": [],
                "review_required_buy_item_ids": ["buy-review-76920"],
                "review_required_sell_item_ids": [],
                "sell_continuation_allowed": True,
                "buy_batch_atomicity_preserved": True,
                "partial_buy_submit_allowed": False,
                "reviewed_buy_submitted": False,
                "submitted_count": 0,
                "item_count": 2,
            },
            "submit_action": "NO_SUBMISSION_REQUIRED",
            "submitted_count": 0,
            "blocked_count": 0,
            "review_required": False,
            "halt_required": False,
            "broker_write": False,
            "external_delivery": False,
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
                "broker_write": False,
                "external_delivery": False,
            },
        },
    )


def _write_buy_item_scoped_review_execution_no_action_manifest(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-execution-l21t-w.json",
        {
            "schema_version": "1",
            "job": "execution",
            "business_date": business_date,
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            "broker_write": False,
            "external_delivery": False,
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
                "broker_write": False,
                "external_delivery": False,
            },
            "stages": [
                {
                    "name": "runtime_v2_execution_readonly_pipeline",
                    "status": "PASS",
                    "details": {
                        "status": "PASS",
                        "reason": "no_submitted_orders",
                        "execution_action": "NO_ACTION",
                        "submitted_order_count": 0,
                        "fill_count": 0,
                        "pending_terminalization_status": "PENDING_LIFECYCLE_REQUIRED",
                        "pending_consumed": False,
                        "pending_mutated": False,
                        "pending_plan_present": True,
                        "pending_item_count": 2,
                        "pending_read_valid": True,
                        "pending_classification": "VALID",
                        "submit_authority_status": "PASS",
                        "submit_action": "NO_SUBMISSION_REQUIRED",
                        "submit_authority_path": str(
                            root
                            / "runtime_state"
                            / "run_manifest"
                            / business_date
                            / "runtime-v2-submit-l21t-w.json"
                        ),
                        "submit_authority_reason": "submit_no_action_authority_ready",
                    },
                }
            ],
        },
    )


def _write_mixed_pending(
    root: Path,
    *,
    pending_plan_id: str,
    target_date: str,
    mode: str = "historical",
    quarantined_symbol: str = "76920",
    quarantined_side: str = "BUY",
    filled_symbol: str = "41650",
    filled_side: str = "SELL",
) -> Path:
    path = _write_pending(
        root,
        pending_plan_id=pending_plan_id,
        target_date=target_date,
        mode=mode,
        symbol=quarantined_symbol,
        side=quarantined_side,
        quantity=1400,
    )
    payload = _load_json(path)
    payload["state"] = "REVIEW_REQUIRED"
    payload["status"] = "REVIEW_REQUIRED"
    payload["approved_item_ids"] = ["item-quarantine", "item-filled"]
    payload["approval"]["approved_item_ids"] = ["item-quarantine", "item-filled"]
    payload["items"] = [
        {
            "pending_item_id": "item-quarantine",
            "symbol": quarantined_symbol,
            "side": quarantined_side,
            "quantity": 1400,
            "order_type": "MARKET",
            "estimated_price": 100,
            "estimated_amount": 140000,
            "approved": True,
            "state": "APPROVED",
        },
        {
            "pending_item_id": "item-filled",
            "symbol": filled_symbol,
            "side": filled_side,
            "quantity": 200,
            "order_type": "MARKET",
            "estimated_price": 500,
            "estimated_amount": 100000,
            "approved": True,
            "state": "APPROVED",
        },
    ]
    _write_json(path, payload)
    return path


def _write_submit_manifest(root: Path, *, pending_plan_id: str) -> None:
    _write_json(
        root / "runtime_state" / "run_manifest" / TARGET_DATE / "submit-unknown.json",
        {
            "schema_version": "1",
            "job": "submit",
            "business_date": TARGET_DATE,
            "final_state": "POST_SEND_UNKNOWN",
            "pending_plan_id": pending_plan_id,
            "stages": [
                {
                    "name": "runtime_v2_submit_pipeline",
                    "status": "REVIEW_REQUIRED",
                    "details": {"broker_request_attempted": True, "unknown_outcome": True},
                }
            ],
        },
    )


def _write_historical_ca_quarantine_submit_authority(
    root: Path,
    *,
    business_date: str,
    pending_plan_id: str,
    symbol: str,
    side: str,
    quantity: int,
    submitted_count: int = 0,
    pass_item: bool = False,
    guard_reason: str = "corporate_action_event_not_resolved",
    violated_policy: str = "historical_corporate_action_symbol_quarantine",
) -> None:
    run_dir = root.parent / "reports" / "runtime_tests" / "runs" / f"run-{pending_plan_id}"
    manifest_path = root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-ca.json"
    guard_items = []
    if pass_item:
        guard_items.append(
            {
                "pending_item_id": "item-pass",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "submit_item_status": "PASS",
                "guard_decision": "PASS",
                "guard_reason": "approved_by_submit_guard_policy",
            }
        )
    guard_items.append(
        {
            "pending_item_id": "item-1",
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "submit_item_status": "REVIEW_REQUIRED",
            "submit_status": "NOT_SUBMITTED",
            "guard_decision": "BLOCKED",
            "guard_reason": guard_reason,
            "blocked_at_submit_reason": guard_reason,
            "violated_policy": violated_policy,
            "corporate_action_event_status": "IMPACT_DETECTED",
            "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
            "corporate_action_adjustment_authority_reason": "corporate_action_event_not_resolved",
            "corporate_action_split_inference_used": False,
            "corporate_action_quantity_adjustment_performed": False,
        }
    )
    _write_json(
        manifest_path,
        {
            "schema_version": "1",
            "job": "submit",
            "business_date": business_date,
            "run_type": "HISTORICAL",
            "runtime_mode": "historical",
            "historical_replay": True,
            "broker_environment": "historical_simulated",
            "runtime_test_run_id": run_dir.name,
            "runtime_test_evidence_root": str(run_dir),
            "exit_code": 20,
            "final_state": "REVIEW_REQUIRED",
            "pending_plan_id": pending_plan_id,
            "pending_read_valid": True,
            "pending_classification": "VALID",
            "pending_active": True,
            "pending_plan_present": True,
            "pending_item_count": len(guard_items),
            "submit_action": "SUBMIT" if submitted_count else "NO_SUBMIT_ATTEMPTED",
            "submitted_count": submitted_count,
            "blocked_count": 1,
            "review_required": True,
            "broker_write": False,
            "external_delivery": False,
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
                "broker_write": False,
                "external_delivery": False,
            },
            "submit_guard_item_evidence": guard_items,
        },
    )
    _write_json(
        run_dir / "daily" / business_date / "submit" / "corporate_action_symbol_quarantine_continuation.json",
        {
            "schema_version": "runtime_test_historical_corporate_action_symbol_quarantine_continuation_v1",
            "status": "COMPLETED_WITH_SYMBOL_QUARANTINE",
            "scope": "CORPORATE_ACTION_SYMBOL_ONLY",
            "business_date": business_date,
            "job": "submit",
            "runtime_manifest_path": str(run_dir / "daily" / business_date / "submit" / "runtime_manifest.json"),
            "checks": {
                "runtime_cli_nonzero": True,
                "submit_job": True,
                "historical_replay": True,
                "broker_environment_historical_simulated": True,
                "no_actual_broker_write": True,
                "runtime_submit_review_required": True,
                "blocked_item_count_positive": True,
                "pending_count_matches_guard_evidence": True,
                "submitted_count_matches_pass_items": submitted_count == int(pass_item),
                "blocked_count_matches_ca_items": guard_reason == "corporate_action_event_not_resolved",
                "other_item_results_independently_inspectable": True,
                "has_eligible_corporate_action_item": True,
                "generic_review_required_not_continued": guard_reason == "corporate_action_event_not_resolved",
            },
            "affected_symbols": [symbol],
            "quarantined_symbols": [symbol],
            "corporate_action_quarantine_status": "QUARANTINED",
            "corporate_action_quarantine_scope": "SYMBOL_ONLY",
            "corporate_action_run_continuation_eligibility": "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY",
            "production_applicability": "NEVER",
        },
    )


def _write_mixed_ca_quarantine_submit_authority(
    root: Path,
    *,
    business_date: str,
    pending_plan_id: str,
    quarantined_symbol: str = "76920",
    quarantined_side: str = "BUY",
    filled_symbol: str = "41650",
    filled_side: str = "SELL",
    final_state: str = "REVIEW_REQUIRED",
    guard_reason: str = "corporate_action_event_not_resolved",
    violated_policy: str = "historical_corporate_action_symbol_quarantine",
) -> None:
    run_dir = root.parent / "reports" / "runtime_tests" / "runs" / f"run-{pending_plan_id}"
    manifest_path = root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-mixed-ca.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "1",
            "job": "submit",
            "business_date": business_date,
            "run_type": "HISTORICAL",
            "runtime_mode": "historical",
            "historical_replay": True,
            "broker_environment": "historical_simulated",
            "runtime_test_run_id": run_dir.name,
            "runtime_test_evidence_root": str(run_dir),
            "exit_code": 20,
            "final_state": final_state,
            "pending_plan_id": pending_plan_id,
            "pending_read_valid": True,
            "pending_classification": "VALID",
            "pending_active": True,
            "pending_plan_present": True,
            "pending_item_count": 2,
            "submit_action": "SUBMIT",
            "submitted_count": 1,
            "blocked_count": 1,
            "review_required": True,
            "broker_write": False,
            "external_delivery": False,
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
                "broker_write": False,
                "external_delivery": False,
            },
            "submit_guard_item_evidence": [
                {
                    "pending_item_id": "item-filled",
                    "symbol": filled_symbol,
                    "side": filled_side,
                    "quantity": 200,
                    "submit_item_status": "PASS",
                    "guard_decision": "PASS",
                    "guard_reason": "approved_by_submit_guard_policy",
                },
                {
                    "pending_item_id": "item-quarantine",
                    "symbol": quarantined_symbol,
                    "side": quarantined_side,
                    "quantity": 1400.0,
                    "submit_item_status": "REVIEW_REQUIRED",
                    "submit_status": "NOT_SUBMITTED",
                    "guard_decision": "BLOCKED",
                    "guard_reason": guard_reason,
                    "blocked_at_submit_reason": guard_reason,
                    "violated_policy": violated_policy,
                    "corporate_action_event_status": "IMPACT_DETECTED",
                    "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
                    "corporate_action_adjustment_authority_reason": "corporate_action_event_not_resolved",
                    "corporate_action_split_inference_used": False,
                    "corporate_action_quantity_adjustment_performed": False,
                },
            ],
        },
    )
    _write_json(
        run_dir / "daily" / business_date / "submit" / "corporate_action_symbol_quarantine_continuation.json",
        {
            "schema_version": "runtime_test_historical_corporate_action_symbol_quarantine_continuation_v1",
            "status": "COMPLETED_WITH_SYMBOL_QUARANTINE",
            "scope": "CORPORATE_ACTION_SYMBOL_ONLY",
            "business_date": business_date,
            "job": "submit",
            "runtime_manifest_path": str(run_dir / "daily" / business_date / "submit" / "runtime_manifest.json"),
            "checks": {
                "runtime_cli_nonzero": True,
                "submit_job": True,
                "historical_replay": True,
                "broker_environment_historical_simulated": True,
                "no_actual_broker_write": True,
                "runtime_submit_review_required": True,
                "blocked_item_count_positive": True,
                "pending_count_matches_guard_evidence": True,
                "submitted_count_matches_pass_items": True,
                "blocked_count_matches_ca_items": guard_reason == "corporate_action_event_not_resolved",
                "other_item_results_independently_inspectable": True,
                "has_eligible_corporate_action_item": True,
                "generic_review_required_not_continued": guard_reason == "corporate_action_event_not_resolved",
            },
            "affected_symbols": [quarantined_symbol],
            "quarantined_symbols": [quarantined_symbol],
            "corporate_action_quarantine_status": "QUARANTINED",
            "corporate_action_quarantine_scope": "SYMBOL_ONLY",
            "corporate_action_run_continuation_eligibility": "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY",
            "production_applicability": "NEVER",
        },
    )


def _append_filled_ledger_order(
    root: Path,
    *,
    business_date: str,
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: int,
) -> None:
    _write_jsonl(
        root / "persistent_ledger" / "orders.jsonl",
        [
            {
                "record_id": f"ledger-order-{pending_item_id}",
                "record_type": "order",
                "schema_version": "1",
                "environment": "historical",
                "source": "test",
                "created_at": business_date + "T15:30:00+09:00",
                "dedup_key": f"order-{pending_item_id}",
                "order_id": f"order-{pending_item_id}",
                "business_date": business_date,
                "pending_plan_id": "unused",
                "pending_item_id": pending_item_id,
                "side": side,
                "symbol": symbol,
                "quantity": quantity,
                "status": "filled",
            }
        ],
    )


def _write_broker_snapshot(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "broker_mode": "demo",
            "production_equivalent": False,
            "review_required": False,
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )


def _write_market_evidence(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "market_summary": {"quote_count": 1},
            "quote_count": 1,
        },
    )


def _write_safety(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase15ar",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": "fixture",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15ar fixture allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": BUSINESS_DATE + "T23:59:59+09:00",
        },
    )


def _now():
    from datetime import datetime, timezone

    return datetime(2026, 7, 10, 1, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_manifest(runtime_root: Path, business_date: str) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return _load_json(manifests[-1])
