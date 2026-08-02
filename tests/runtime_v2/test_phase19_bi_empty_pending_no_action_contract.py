import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.no_order_authority import materialize_empty_pending_no_order_authority
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import (
    _demo_settings,
    _read_jsonl,
    _runtime_root,
    _write_asset_state,
    _write_policy,
)
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    BUSINESS_DATE,
    EVALUATION_TIME,
    _historical_context,
)


def test_phase19_bi_reset_canonical_empty_pending_submits_no_action(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending_payload = {
        "schema_version": "runtime_v2_pending_slot_v1",
        "state": "EMPTY",
        "status": "EMPTY",
        "active_pending": False,
    }
    _write_json(pending_path, pending_payload)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pending EMPTY no_order_authority missing"
    assert result.submit_action == "BLOCKED"
    assert result.submitted_count == 0
    assert result.accepted_count == 0
    assert result.blocked_count == 0
    assert result.pending_consumed is False
    assert result.demo_submit_executed is False
    assert _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl") == []
    assert json.loads(pending_path.read_text(encoding="utf-8")) == pending_payload


def test_phase19_bi_empty_pending_requires_order_authority_metadata(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "EMPTY",
            "status": "EMPTY",
            "active_pending": False,
            "environment": "historical",
            "target_session_date": "1999-01-01",
            "intended_submit_date": "1999-01-01",
            "safety_context": {},
            "items": [],
        },
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pending EMPTY no_order_authority missing"
    assert result.pending_classification == "EMPTY"
    assert result.submitted_count == 0


def test_phase19_bi_historical_empty_pending_no_action_has_no_broker_effects(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "EMPTY",
            "status": "EMPTY",
            "active_pending": False,
            "items": [],
        },
    )
    adapter = HistoricalSubmitAdapter(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        pit_manifest_path=tmp_path / "not-used-pit-manifest.json",
        historical_asof_view_path=tmp_path / "not-used-asof-view.json",
        ohlcv_path=tmp_path / "not-used-ohlcv.parquet",
        listed_issues_path=tmp_path / "not-used-listed.parquet",
        raw_ohlcv_path=tmp_path / "not-used-raw-ohlcv.parquet",
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pending EMPTY no_order_authority missing"
    assert result.demo_submit_executed is False
    assert result.raw_request_saved is False
    assert result.raw_response_saved is False
    assert result.secret_saved is False
    assert not (runtime_root / "runtime_state" / "historical_broker").exists()
    assert _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl") == []


def test_phase19_bi_active_pending_environment_mismatch_stays_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-active-wrong-env",
            "state": "APPROVED",
            "active_pending": True,
            "environment": "production",
            "target_session_date": "2026-07-08",
            "items": [{"pending_item_id": "x", "symbol": "7203", "side": "BUY", "quantity": 100}],
            "approval": {"approval_status": "APPROVED", "pending_policy_hash": "hash"},
            "pending_policy_hash": "hash",
            "consume": {"consumed": False},
        },
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "BLOCKED"
    assert result.submit_action == "BLOCKED"
    assert "pending current is missing or invalid" in result.reason


def test_phase19_bi_execution_accepts_empty_after_submit_no_action_authority(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending_payload = {
        "schema_version": "runtime_v2_pending_slot_v1",
        "state": "EMPTY",
        "status": "EMPTY",
        "active_pending": False,
        "pending_plan_id": "pending-empty-authorized-bi",
        "items": [],
    }
    _write_empty_authority_source_artifacts(runtime_root, business_date="2026-07-08")
    pending_payload = materialize_empty_pending_no_order_authority(
        pending_payload,
        runtime_root=runtime_root,
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        authority_reason="empty_pending_no_executable_order_items",
        sell_order_plan_path=runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "order_plan.json",
        sell_approval_path=runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "approval_artifact.json",
        sell_reason="NO_SIGNAL:fixture",
    )
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending_payload)
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )
    _write_json(
        runtime_root / "runtime_state" / "run_manifest" / "2026-07-08" / "runtime-v2-submit-bi.json",
        {
            "run_id": "runtime-v2-submit-bi",
            "job": "submit",
            "business_date": "2026-07-08",
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            **submit.to_stage_details(),
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
            },
        },
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("NO_ACTION must not read broker")),
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False
    assert result.ledger_orders_appended == 0
    assert result.pending_mutated is False


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_empty_authority_source_artifacts(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "sell_pipeline" / business_date / "order_plan.json",
        {
            "schema_version": "1",
            "order_plan_id": f"order-plan-sell-no-signal-{business_date}",
            "environment": "demo",
            "business_date": business_date,
            "target_session_date": business_date,
            "status": "NO_ACTION",
            "items": [],
            "reason": "NO_SIGNAL:fixture",
        },
    )
    _write_json(
        root / "runtime_state" / "sell_pipeline" / business_date / "approval_artifact.json",
        {
            "status": "NO_SIGNAL",
            "reason": "NO_SIGNAL:fixture",
        },
    )
