from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def test_phase15bq_preconditions_blocked_without_broker_snapshot() -> None:
    artifact = _read_json(
        ".runtime_acceptance_phase15_demo_write/runtime_state/demo_broker_write_preconditions/phase15bq_preconditions.json"
    )

    assert artifact["broker_write_performed"] is False
    assert artifact["submit_executed"] is False
    assert artifact["broker_client_called"] is False
    assert artifact["broker_readonly"]["snapshot_status"] == "FAILED_LOGIN_SESSION"
    assert artifact["broker_readonly"]["fresh_broker_snapshot_status"] == "MISSING"
    assert artifact["scenario_selection"]["status"] == "BLOCKED"
    assert artifact["final_judgment"] == "DEMO_WRITE_PRECONDITIONS_BLOCKED"


def test_phase15bq_does_not_generate_approval_pending_or_user_authorization() -> None:
    artifact = _read_json(
        ".runtime_acceptance_phase15_demo_write/runtime_state/demo_broker_write_preconditions/phase15bq_preconditions.json"
    )

    assert artifact["fresh_chain"]["approval_candidate_status"] == "NOT_GENERATED"
    assert artifact["fresh_chain"]["authoritative_pending_status"] == "NOT_GENERATED"
    assert artifact["fresh_chain"]["submit_preflight_status"] == "NOT_RUN"
    assert "user_authorization_artifact_generation" in artifact["blocked_actions"]


def test_phase15bq_final_request_review_is_redacted_and_blocked() -> None:
    review = _read_json("reports/phase_reports/phase15_bq/final_request_review_redacted.json")

    assert review["status"] == "BLOCKED"
    assert review["request_payload_ready"] is False
    assert review["request_hash"] == ""
    assert review["contains_credentials"] is False
    assert review["contains_plain_account_id"] is False
    assert review["contains_raw_token"] is False
    assert review["contains_secret_key"] is False
    assert review["contains_full_raw_request"] is False


def test_phase15bq_summary_declares_no_write_or_submit() -> None:
    summary = _read_json("reports/phase_reports/phase15_bq_demo_broker_write_preconditions_regeneration.json")

    assert summary["broker_write_performed"] is False
    assert summary["submit_executed"] is False
    assert summary["broker_client_called"] is False
    assert summary["fresh_broker_snapshot_status"] == "FAILED_LOGIN_SESSION_NO_SNAPSHOT_CREATED"
    assert summary["authoritative_pending_status"] == "NOT_GENERATED"
    assert summary["final_judgment"] == "DEMO_WRITE_PRECONDITIONS_BLOCKED"


def test_phase15bq_uses_new_isolated_root_not_consumed_bo_root() -> None:
    summary = _read_json("reports/phase_reports/phase15_bq_demo_broker_write_preconditions_regeneration.json")
    bo_pending = _read_json(".runtime_acceptance_phase15_submit/pending_order_plan/pending_order_plan.json")

    assert summary["isolated_runtime_root"] == ".runtime_acceptance_phase15_demo_write"
    assert bo_pending["state"] == "CONSUMED"
    assert summary["authoritative_pending_status"] == "NOT_GENERATED"
