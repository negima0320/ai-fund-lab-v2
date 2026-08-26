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


def test_phase31_g10_execution_accepts_f2b_terminal_noop_submit_authority(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    _write_f2b_terminal_noop_pending(runtime_root, business_date="2022-12-16")
    _write_f2b_terminal_noop_submit_manifest(runtime_root, business_date="2022-12-16")

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2022-12-16",
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("safe NO_ACTION must not read broker")),
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.submitted_order_count == 0
    assert result.orders_count == 0
    assert result.fill_count == 0
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.ledger_cash_appended == 0
    assert result.ledger_positions_appended == 0
    assert result.pending_mutated is False
    assert result.pending_terminalization_status == "PENDING_LIFECYCLE_REQUIRED"
    assert result.submit_authority_status == "PASS"
    assert result.submit_action == "NO_SUBMIT_ATTEMPTED"
    assert result.submit_authority_reason == "submit_no_action_authority_ready"


def test_phase31_g10_zero_orders_with_unsafe_terminal_noop_authority_fails_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_asset_state(runtime_root)
    _write_f2b_terminal_noop_pending(runtime_root, business_date="2022-12-16")
    _write_f2b_terminal_noop_submit_manifest(
        runtime_root,
        business_date="2022-12-16",
        aggregate_overrides={
            "counts": {
                "blocked": 0,
                "deferred_item_scoped_review": 1,
                "rejected": 0,
                "retryable_executable": 0,
                "submitted_or_reconciled": 0,
                "terminal_not_executable": 1,
                "unknown_or_ambiguous": 1,
            }
        },
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2022-12-16",
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("unsafe NO_ACTION must fail before broker")),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "submit NO_ACTION authority inconsistent"
    assert result.execution_action == "NOT_EXECUTED"
    assert result.submitted_order_count == 0
    assert result.ledger_orders_appended == 0
    assert result.pending_mutated is False


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_f2b_terminal_noop_pending(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "pending_plan_id": "pending-strategy-plan-historical-2022-12-16-g10",
            "state": "REVIEW_REQUIRED",
            "status": "REVIEW_REQUIRED",
            "active_pending": True,
            "environment": "demo",
            "created_at": f"{business_date}T08:30:00+09:00",
            "updated_at": f"{business_date}T08:45:00+09:00",
            "plan_created_date": business_date,
            "intended_submit_date": business_date,
            "target_session_date": business_date,
            "source_order_plan": {"order_plan_id": "strategy-plan-g10", "path": "strategy/runtime_planning.json", "artifact_hash": "hash"},
            "approval": {
                "approval_path": "approval.json",
                "approval_hash": "approval-hash",
                "approval_status": "APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW",
                "approved_item_ids": [],
                "approval_expires_at": f"{business_date}T15:00:00+09:00",
            },
            "approved_item_ids": [],
            "approved_buy_item_ids": [],
            "approved_sell_item_ids": [],
            "review_required_buy_item_ids": ["strategy-72028bb5bdbc919568b5"],
            "review_required_sell_item_ids": [],
            "review_scope": "BUY_ITEM_SCOPED_REVIEW",
            "review_scope_source": "phase24_ht_planning_submit_feasibility_v1",
            "review_scope_reason": "corporate_action_event_not_resolved",
            "sell_continuation_allowed": True,
            "submit_constraints": {"expires_at": f"{business_date}T15:00:00+09:00"},
            "consume": {"consumed": False, "submitted_order_ids": [], "ledger_order_record_ids": []},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "items": [
                {
                    "pending_item_id": "strategy-72028bb5bdbc919568b5",
                    "symbol": "76920",
                    "side": "BUY",
                    "quantity": 200,
                    "order_type": "MARKET",
                    "estimated_price": 200,
                    "estimated_amount": 40000,
                    "approved": False,
                    "state": "REVIEW_REQUIRED",
                    "feasibility_status": "REVIEW_REQUIRED",
                    "batch_submit_status": "ITEM_REVIEW_REQUIRED",
                    "item_review_reason": "corporate_action_event_not_resolved",
                },
                {
                    "pending_item_id": "strategy-93951a07c698dde807ca",
                    "symbol": "41020",
                    "side": "SELL",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "estimated_price": 1305,
                    "estimated_amount": 130500,
                    "approved": False,
                    "state": "NOT_EXECUTABLE",
                    "feasibility_status": "NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE",
                    "batch_submit_status": "NOT_EXECUTABLE",
                    "item_review_reason": "EXECUTION_AUTHORITY_UNAVAILABLE",
                    "submit_status": "NOT_SUBMITTED",
                    "retry_eligible_same_day": False,
                    "adapter_submit_called": False,
                    "order_materialized": False,
                    "position_mutated": False,
                    "cash_mutated": False,
                    "broker_side_effect_created": False,
                    "ledger_order_created": False,
                },
            ],
        },
    )


def _write_f2b_terminal_noop_submit_manifest(
    root: Path,
    *,
    business_date: str,
    aggregate_overrides=None,
) -> None:
    aggregate = {
        "accepted_count": 0,
        "authority_type": "SUBMIT_AGGREGATE_TERMINAL_NOOP_CONTINUATION",
        "checks": {
            "all_items_have_known_dispositions": True,
            "blocked_absent": True,
            "item_scoped_reviews_deferred_by_authority": True,
            "items_present": True,
            "pending_review_scope_no_executable_items_after_terminalization": True,
            "pending_review_scope_no_non_terminal_items_after_terminalization": True,
            "pending_review_scope_not_batch_blocked": True,
            "pending_review_scope_structural_valid": True,
            "rejected_absent": True,
            "retryable_executable_absent": True,
            "reviewed_sell_absent": True,
            "terminal_not_executable_items_safety_qualified": True,
            "unknown_or_ambiguous_absent": True,
        },
        "classification_authority": "SubmitItemResult + PendingReviewScopeAuthority",
        "counts": {
            "blocked": 0,
            "deferred_item_scoped_review": 1,
            "rejected": 0,
            "retryable_executable": 0,
            "submitted_or_reconciled": 0,
            "terminal_not_executable": 1,
            "unknown_or_ambiguous": 0,
        },
        "fake_cash_mutation": False,
        "fake_execution_created": False,
        "fake_position_mutation": False,
        "fake_submission_created": False,
        "item_classes": {
            "strategy-72028bb5bdbc919568b5": "DEFERRED_ITEM_SCOPED_REVIEW",
            "strategy-93951a07c698dde807ca": "TERMINAL_NOT_EXECUTABLE",
        },
        "known_safe_terminal_or_deferred_count": 2,
        "pending_review_scope_authority": {
            "batch_blocked": False,
            "executable_item_ids": [],
            "non_terminal_item_ids": [],
            "reviewed_item_ids": ["strategy-72028bb5bdbc919568b5"],
            "reviewed_buy_item_ids": ["strategy-72028bb5bdbc919568b5"],
            "reviewed_sell_item_ids": [],
            "structural_validity": "PASS",
            "terminal_item_ids": ["strategy-93951a07c698dde807ca"],
        },
        "reason": "zero_submission_terminal_noop_continuation",
        "same_day_retry_prevented_for_terminal_items": True,
        "status": "PASS",
        "submitted_count": 0,
        "zero_submission_safe_terminal_pass_supported": True,
    }
    if aggregate_overrides:
        aggregate.update(aggregate_overrides)
    _write_json(
        root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-g10.json",
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
            "pending_slot_status": "REVIEW_REQUIRED",
            "no_order_authority_status": "PASS",
            "no_order_authority_reason": "pass_buy_items_submit_review_buy_items_deferred",
            "no_order_authority_evidence": {
                "authority_type": "BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION",
                "status": "PASS",
                "reason": "pass_buy_items_submit_review_buy_items_deferred",
                "submit_aggregate_terminal_noop_authority": aggregate,
            },
            "submit_action": "NO_SUBMIT_ATTEMPTED",
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
