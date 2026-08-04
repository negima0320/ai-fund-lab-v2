import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload_from_summary
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current


def test_phase15r_report_shows_policy_safety_and_submit_guard_reason_evidence(tmp_path):
    runtime_root = _write_current_and_manifest(tmp_path / ".runtime")
    state_before = (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")
    pending_before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / "2026-07-09",
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / "2026-07-09",
        business_date="2026-07-09",
    )

    runtime_report = Path(result["runtime_report_md"]).read_text(encoding="utf-8")
    public_report = Path(result["public_report_md"]).read_text(encoding="utf-8")
    summary = json.loads(Path(result["runtime_report_json"]).read_text(encoding="utf-8"))

    assert "## Why BUY" in runtime_report
    assert "## Why SELL" in runtime_report
    assert "## Why BLOCKED / REVIEW_REQUIRED / HALT" in runtime_report
    assert "## Policy Evidence" in runtime_report
    assert "capital_deployment_policy_source" in runtime_report
    assert "capital_deployment_v1" in runtime_report
    assert "max_exposure: 900000" in runtime_report
    assert "## Safety Evidence" in runtime_report
    assert "safety_decision_id: safety-phase15r-review" in runtime_report
    assert "broker quantity requires refresh" in runtime_report
    assert "## Submit Guard Evidence" in runtime_report
    assert "broker_available_quantity" in runtime_report
    assert "Refresh Broker ReadOnly positions" in runtime_report
    assert "## Why" in public_report
    assert "Reason summary:" in public_report
    assert summary["reason_evidence"]["policy_evidence"]["capital_deployment_policy_source"] == "configs/demo_policy.json"
    assert summary["reason_evidence"]["safety_evidence"]["safety_reason"] == "broker quantity requires refresh"
    assert summary["reason_evidence"]["submit_guard_evidence"]["violated_policy"] == "broker_available_quantity"
    assert summary["reason_evidence"]["severity"] == "REVIEW_REQUIRED"
    assert (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == state_before
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == pending_before


def test_phase15r_notification_payload_contains_reason_summary_and_payload_only(tmp_path):
    runtime_root = _write_current_and_manifest(tmp_path / ".runtime")

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / "2026-07-09",
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / "2026-07-09",
        business_date="2026-07-09",
    )

    payload = json.loads(Path(result["notification_payload_json"]).read_text(encoding="utf-8"))
    assert payload["severity"] == "REVIEW_REQUIRED"
    assert payload["runtime_state"] == "REVIEW_REQUIRED"
    assert "reason_summary" in payload
    assert "policy_summary" in payload
    assert "safety_summary" in payload
    assert "guard_summary" in payload
    assert payload["review_required"] is True
    assert payload["notification_delivery_status"] == "PAYLOAD_ONLY"
    assert payload["notification_sent"] is False
    assert "Refresh Broker ReadOnly positions" in payload["next_operator_action"]

    summary = json.loads(Path(result["runtime_report_json"]).read_text(encoding="utf-8"))
    built_payload = build_notification_payload_from_summary(
        summary=summary,
        channel="runtime_v2",
        source_report_id="runtime-report-phase15r",
    )
    assert built_payload.reason_summary == summary["reason_evidence"]["reason_summary"]
    assert built_payload.policy_summary == summary["reason_evidence"]["policy_summary"]
    assert built_payload.safety_summary == summary["reason_evidence"]["safety_summary"]
    assert built_payload.guard_summary == summary["reason_evidence"]["guard_summary"]
    assert built_payload.severity == "REVIEW_REQUIRED"
    assert built_payload.notification_delivery_status == "PAYLOAD_ONLY"
    assert built_payload.notification_sent is False


def test_phase15r_notification_severity_classification():
    base = {
        "business_date": "2026-07-09",
        "runtime_mode": "demo",
        "environment": "demo",
        "current_run": {"run_id": "run-phase15r"},
        "current_portfolio": {},
        "today_operation": {"review_required": False},
        "warning_summary": {"notes": ()},
        "reconcile": {"review_required": False, "blocked": False},
        "notification": {},
    }

    assert _payload_for(base | {"reason_evidence": {"runtime_state": "PASS"}}).severity == "INFO"
    assert _payload_for(base | {"reason_evidence": {"runtime_state": "REVIEW_REQUIRED"}}).severity == "REVIEW_REQUIRED"
    assert _payload_for(base | {"reason_evidence": {"runtime_state": "BLOCKED"}}).severity == "BLOCKED"
    assert _payload_for(base | {"reason_evidence": {"runtime_state": "HALT"}}).severity == "HALT"


def _payload_for(summary: dict):
    return build_notification_payload_from_summary(
        summary=summary,
        channel="runtime_v2",
        source_report_id="runtime-report-phase15r",
    )


def _write_current_and_manifest(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "as_of": "2026-07-09",
            "environment": "demo",
            "cash": 500000,
            "buying_power": 500000,
            "market_value": 500000,
            "total_equity": 1000000,
            "positions": [{"symbol": "7203", "quantity": 100, "average_price": 5000, "market_value": 500000}],
            "review_required": True,
        },
    )
    _write_jsonl(root / "persistent_ledger" / "orders.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "positions.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "cash.jsonl", [])
    _write_jsonl(
        root / "persistent_ledger" / "events.jsonl",
        [{"record_type": "event", "severity": "REVIEW_REQUIRED", "message": "operator review required"}],
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "environment": "demo",
            "state": "PENDING_APPROVAL",
            "target_session_date": "2026-07-10",
            "policy_context": {
                "policy_source": "configs/demo_policy.json",
                "policy_version": "capital_deployment_v1",
                "target_investment_ratio": 0.95,
                "cash_buffer": 50000,
                "max_exposure": 900000,
                "max_positions": 6,
            },
            "safety_context": {
                "safety_decision_id": "safety-phase15r-review",
                "safety_policy_version": "safety_v1",
                "safety_source": "runtime_safety",
                "decision": "REVIEW_REQUIRED",
                "reason": "broker quantity requires refresh",
                "block_buy": False,
                "block_sell": False,
                "block_submit": True,
                "halt_runtime": False,
                "emergency_stop": False,
            },
            "items": [{"symbol": "7203", "side": "SELL", "quantity": 100}],
            "consume": {"consumed": False},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {"environment": "demo", "runtime_mode": "demo", "state": "REVIEW_REQUIRED", "updated_at": "2026-07-09"},
    )
    _write_json(
        root / "runtime_state" / "run_manifest" / "2026-07-09" / "runtime-v2-submit-2026-07-09.json",
        {
            "business_date": "2026-07-09",
            "final_state": "REVIEW_REQUIRED",
            "capital_deployment_policy_source": "configs/demo_policy.json",
            "capital_deployment_policy_version": "capital_deployment_v1",
            "active_policy_hash": "policy-hash-phase15r",
            "target_investment_ratio": 0.95,
            "cash_buffer": 50000,
            "max_exposure": 900000,
            "max_positions": 6,
            "safety_decision_id": "safety-phase15r-review",
            "safety_policy_version": "safety_v1",
            "safety_source": "runtime_safety",
            "safety_decision": "REVIEW_REQUIRED",
            "safety_reason": "broker quantity requires refresh",
            "safety_status": "REVIEW_REQUIRED",
            "safety_block_buy": False,
            "safety_block_sell": False,
            "safety_block_submit": True,
            "safety_halt_runtime": False,
            "safety_emergency_stop": False,
            "submit_policy_consistency": {
                "policy_consistency_status": "PASS",
                "policy_mismatch_reason": "",
            },
            "submit_guard_item_evidence": [
                {
                    "side": "SELL",
                    "guard_decision": "REVIEW_REQUIRED",
                    "guard_reason": "broker_available_quantity missing",
                    "violated_policy": "broker_available_quantity",
                    "violated_policy_source": "submit_guard.sell_quantity",
                    "manual_review_required": True,
                    "broker_available_quantity_checked": False,
                    "broker_available_quantity_source": "broker_readonly.positions",
                    "sell_quantity_guard_status": "REVIEW_REQUIRED",
                }
            ],
            "warnings": ["SELL requires broker available quantity evidence"],
            "errors": [],
            "stages": [
                {
                    "name": "runtime_v2_submit_pipeline",
                    "status": "REVIEW_REQUIRED",
                    "message": "Submit Guard requested review.",
                }
            ],
        },
    )
    return root


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
