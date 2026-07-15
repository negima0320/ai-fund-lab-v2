from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import (
    _data_readiness_required_for_job,
    _effective_runtime_safety_decision,
    _write_sell_planning_manifest_evidence,
)
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import evaluate_sell_planning_capability
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision, safety_allows_action


BUSINESS_DATE = "2026-07-06"
RUN_ID = "runtime-test-historical-smoke-fixture"
PROFILE_ID = "historical-smoke"


def test_phase17_x_historical_sell_planning_capability_allows_replay_only(tmp_path):
    decision = evaluate_sell_planning_capability(mode="historical", context=_historical_context(tmp_path))

    assert decision.status == "PASS"
    assert "position_management_ai" in decision.allowed_processing
    assert "broker_order_api_call" in decision.prohibited_external_effects


def test_phase17_x_historical_sell_planning_capability_does_not_depend_on_run_identity(tmp_path):
    context = {**_historical_context(tmp_path), "runtime_test_run_id": ""}

    decision = evaluate_sell_planning_capability(mode="historical", context=context)

    assert decision.status == "PASS"
    assert decision.runtime_test_run_id_present is False


def test_phase17_x_data_readiness_accepts_pending_safety_authority_and_empty_current_pm(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_authorized_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=_evidence_root(tmp_path),
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=False,
        external_delivery=False,
    )

    assert result.status == "READY"
    assert result.payload["pm_status"] == "READY"
    assert result.payload["components"]["pm"]["contract"]["pm_current_freshness"] == "FRESH"
    assert result.payload["components"]["pm"]["contract"]["pm_historical_empty_current_authority"] == "runtime_state_current_state"
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["status"] == "READY"
    assert result.payload["components"]["safety"]["historical_safety_temporal_authority"] == "historical_initial_no_external_effect"
    assert "historical_safety_temporal_authority_missing" not in result.payload["review_reasons"]
    assert "pending_safety_evidence_missing" not in result.payload["review_reasons"]
    assert "pm_input_stale_artifacts" not in result.payload["review_reasons"]


def test_phase17_x_historical_safety_authority_allows_submit_replay_after_data_readiness(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_authorized_pending(runtime_root, tmp_path)
    _write_stale_latest_safety(runtime_root)
    data_readiness = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="submit",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=_evidence_root(tmp_path),
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=False,
        external_delivery=False,
    )
    data_readiness_manifest = {
        "data_readiness_safety_authority": data_readiness.payload["components"]["safety"][
            "historical_safety_temporal_authority"
        ],
        "data_readiness_safety_reason": data_readiness.payload["components"]["safety"]["reason"],
    }

    stale_latest = load_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
    )
    effective = _effective_runtime_safety_decision(
        args=Namespace(mode="historical"),
        business_date=BUSINESS_DATE,
        runtime_safety_decision=stale_latest,
        data_readiness_manifest=data_readiness_manifest,
    )

    assert stale_latest.decision == "REVIEW_REQUIRED"
    assert effective is not None
    assert effective.safety_source == "data_readiness_historical_temporal_authority"
    assert effective.block_submit is False
    assert effective.action_permissions["broker_write"] == "BLOCKED"
    assert safety_allows_action(effective, action="submit", side="BUY") == (
        True,
        "PASS",
        "historical_neutral_no_event_safety_ready",
    )


def test_phase17_x_submit_job_rechecks_data_readiness_before_submit():
    assert _data_readiness_required_for_job("submit") is True


def test_phase17_x_pending_safety_authority_mismatch_remains_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_authorized_pending(runtime_root, tmp_path, run_id="wrong-run")
    _write_stale_latest_safety(runtime_root)

    result = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=_evidence_root(tmp_path),
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=False,
        external_delivery=False,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_safety_evidence_missing" in result.payload["review_reasons"]
    assert "historical_safety_temporal_authority_missing" in result.payload["review_reasons"]
    assert result.payload["components"]["pending"]["historical_pending_safety_authority"]["mismatched_fields"] == [
        "safety_context.runtime_test_run_id"
    ]


def test_phase17_x_pm_producer_uses_runtime_state_authority_for_historical_empty_current(tmp_path, monkeypatch):
    runtime_root = _runtime_root(tmp_path)
    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.position_management.producer.verify_position_management_runtime_adapter_authority",
        lambda: {"status": "PASS", "source": "phase17x-fixture"},
    )

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    artifact = _read_json(Path(result.artifact_path))
    assert result.status == "NO_POSITION"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["input_contract"]["pm_current_as_of"] == BUSINESS_DATE
    assert artifact["input_contract"]["pm_historical_empty_current_authority"] == "runtime_state_current_state"


def test_phase17_x_sell_planning_evidence_records_no_position_pending_continuity(tmp_path):
    evidence_root = _evidence_root(tmp_path)
    manifest_path = tmp_path / ".runtime" / "runtime_state" / "run_manifest" / BUSINESS_DATE / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = {
        "mode": "historical",
        "final_state": "SUCCESS",
        "errors": [],
        "warnings": ["sell planning no position: existing pending continuity preserved"],
        "data_readiness_status": "READY",
        "data_readiness_safety_authority": "historical_initial_no_external_effect",
        "prohibited_actions": {
            "demo_submit_executed": False,
            "production_order_executed": False,
            "notification_sent": False,
            "phase9_runtime_called": False,
            "phase9_writer_called": False,
            "mode_rooted_current_used": False,
        },
        "stages": [
            {
                "name": "environment_capability_decision",
                "status": "PASS",
                "message": "ready",
                "details": {"reason": "historical_sell_planning_capability_ready"},
            },
            {
                "name": "position_management_ai_runtime_producer",
                "status": "NO_POSITION",
                "message": "pm",
                "details": {"reason": "current_position_missing"},
            },
        ],
    }

    _write_sell_planning_manifest_evidence(
        evidence_root=evidence_root,
        business_date=BUSINESS_DATE,
        manifest_path=manifest_path,
        manifest=manifest,
    )
    evidence_dir = evidence_root / "daily" / BUSINESS_DATE / "sell_planning"

    assert _read_json(evidence_dir / "environment_capability_decision.json")["status"] == "PASS"
    assert _read_json(evidence_dir / "position_management_evidence.json")["status"] == "NO_POSITION"
    assert _read_json(evidence_dir / "pending_continuity_evidence.json")["no_position_preserved_existing_pending"] is True
    assert _read_json(evidence_dir / "external_effect_audit.json")["status"] == "PASS"


def _historical_context(tmp_path: Path) -> dict:
    return {
        "runtime_mode": "historical",
        "broker_environment": "historical_simulated",
        "historical_replay": True,
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "tachibana_demo_write": False,
        "tachibana_production_write": False,
        "submit_enabled": False,
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
    }


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase17x",
            "environment": "historical",
            "source": "phase17_x_fixture",
            "as_of": "2026-07-14T23:14:10Z",
            "updated_at": "2026-07-14T23:14:10Z",
            "business_date": "",
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
            "generated_at": "2026-07-05T23:40:00+00:00",
            "updated_at": "2026-07-05T23:40:00+00:00",
            "environment": "historical",
            "runtime_mode": "historical",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
        },
    )
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "status": "READY",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"quote_count": 1},
        },
    )
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T00:00:00Z",
            "broker_mode": "historical_simulated",
            "production_equivalent": False,
            "review_required": False,
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_authorized_pending(runtime_root: Path, tmp_path: Path, *, run_id: str = RUN_ID) -> None:
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-phase17x",
            "state": "APPROVED",
            "environment": "historical",
            "plan_created_date": BUSINESS_DATE,
            "intended_submit_date": BUSINESS_DATE,
            "target_session_date": BUSINESS_DATE,
            "pending_policy_hash": "policy-hash",
            "approval": {
                "approval_status": "APPROVED",
                "pending_policy_hash": "policy-hash",
                "safety_decision_id": "",
                "safety_policy_version": "historical_replay_neutral_safety_v1",
            },
            "consume": {"consumed": False},
            "safety_decision_id": "",
            "safety_policy_version": "historical_replay_neutral_safety_v1",
            "safety_context": {
                "safety_authority": "historical_initial_no_external_effect",
                "safety_decision_id": "",
                "safety_policy_version": "historical_replay_neutral_safety_v1",
                "safety_source": "data_readiness_historical_temporal_authority",
                "safety_decision": "ALLOW",
                "safety_reason": "historical_neutral_no_event_safety_ready",
                "safety_business_date": BUSINESS_DATE,
                "runtime_test_run_id": run_id,
                "runtime_test_profile_id": PROFILE_ID,
                "runtime_test_evidence_root": str(_evidence_root(tmp_path)),
            },
            "items": [
                {
                    "pending_item_id": "buy-1",
                    "symbol": "7203",
                    "side": "BUY",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "estimated_price": 1000,
                    "estimated_amount": 100000,
                    "approved": True,
                    "state": "APPROVED",
                }
            ],
        },
    )


def _write_stale_latest_safety(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "demo-latest-2026-07-10",
            "safety_policy_version": "runtime_safety_v1",
            "safety_source": "reports/safety/phase11/2026-07-10_safety_report.json",
            "business_date": "2026-07-10",
            "runtime_mode": "historical",
            "decision": "REVIEW_REQUIRED",
            "reason": "HIGH_RISK_REVIEW",
            "review_required": True,
            "block_buy": True,
            "block_sell": True,
            "block_submit": True,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-10T00:00:00Z",
            "expires_at": "2026-07-11T00:00:00Z",
            "safety_status": "REVIEW_REQUIRED",
            "artifact_path": str(runtime_root / "runtime_state" / "safety" / "latest_safety_decision.json"),
        },
    )


def _evidence_root(tmp_path: Path) -> Path:
    return tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
