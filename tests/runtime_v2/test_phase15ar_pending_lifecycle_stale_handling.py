from __future__ import annotations

import json
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
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase15ar-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
        },
    )
    _write_safety(root)
    _write_market_evidence(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_pending(root: Path, *, pending_plan_id: str, target_date: str) -> Path:
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
            "environment": "demo",
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
                    "symbol": "7203",
                    "side": "SELL",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "estimated_price": 1000,
                    "estimated_amount": 100000,
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
