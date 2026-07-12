from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def test_phase15bp_review_artifact_blocks_without_user_authorization() -> None:
    artifact = _read_json(
        ".runtime_acceptance_phase15_submit/runtime_state/demo_broker_write_review/phase15bp_request_review.json"
    )

    assert artifact["broker_write_performed"] is False
    assert artifact["submit_executed"] is False
    assert artifact["user_authorization_present"] is False
    assert artifact["authorization_artifact_created"] is False
    assert artifact["evidence"]["send_preconditions_status"] == "BLOCKED_UNTIL_REGENERATED_AND_AUTHORIZED"
    assert "broker_write" in artifact["blocked_actions"]
    assert artifact["final_judgment"] == "DEMO_BROKER_WRITE_REVIEW_REQUIRED"


def test_phase15bp_request_hash_is_redacted_and_stable() -> None:
    artifact = _read_json("reports/phase_reports/phase15_bp/request_review_redacted.json")

    assert artifact["request_hash"] == "sha256:8e7f03c217ea1860554e76896721f82d9b5f0749c2f48cd276d82512662b9d60"
    assert artifact["contains_credentials"] is False
    assert artifact["contains_plain_account_id"] is False
    assert artifact["contains_raw_token"] is False
    assert artifact["contains_secret_key"] is False
    assert artifact["contains_full_raw_request"] is False


def test_phase15bp_current_isolated_pending_is_not_sendable() -> None:
    pending = _read_json(".runtime_acceptance_phase15_submit/pending_order_plan/pending_order_plan.json")
    artifact = _read_json(
        ".runtime_acceptance_phase15_submit/runtime_state/demo_broker_write_review/phase15bp_request_review.json"
    )

    assert pending["state"] == "CONSUMED"
    assert pending["consume"]["consumed"] is True
    assert artifact["evidence"]["pending_state_status"] == "BLOCKING_FOR_REAL_SEND"


def test_phase15bp_target_session_and_broker_snapshot_require_refresh() -> None:
    artifact = _read_json(
        ".runtime_acceptance_phase15_submit/runtime_state/demo_broker_write_review/phase15bp_request_review.json"
    )

    assert artifact["request_review"]["target_session"] == "2026-07-09"
    assert artifact["evidence"]["target_session_status"] == "PAST_SESSION_BLOCKING"
    assert artifact["evidence"]["broker_available_quantity"] == 100.0
    assert artifact["evidence"]["broker_available_quantity_status"] == "STALE_READONLY_REFRESH_REQUIRED"
    assert artifact["evidence"]["open_order_status"] == "UNKNOWN_FRESH_READONLY_REQUIRED"


def test_phase15bp_summary_json_declares_no_submit_or_broker_write() -> None:
    summary = _read_json("reports/phase_reports/phase15_bp_explicit_demo_broker_write_review.json")

    assert summary["broker_write_performed"] is False
    assert summary["submit_executed"] is False
    assert summary["current_apply_planned"] is False
    assert summary["send_preconditions_status"] == "BLOCKED_UNTIL_REGENERATED_AND_AUTHORIZED"
    assert summary["final_judgment"] == "DEMO_BROKER_WRITE_REVIEW_REQUIRED"
