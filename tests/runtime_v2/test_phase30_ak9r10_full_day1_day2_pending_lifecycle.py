from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingApprovalLink, PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.pending.lifecycle_runner import run_pending_lifecycle_review
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from scripts import runtime_test as runtime_test_runner


DAY1 = "2026-07-08"
DAY2 = "2026-07-09"
RUN_ID = "runtime-test-phase30-ak9r10"
PROFILE_ID = "phase30-ak9r10"


def test_phase30_ak9r10_partial_review_day1_to_day2_full_lifecycle(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    runtime_root = _runtime_root(tmp_path)
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[], as_of=DAY1)
    pending = _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)

    morning_payload = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    assert pending.pending_plan_id == "pending-order-plan-phase30-ak9r10"
    assert morning_payload["state"] == "REVIEW_REQUIRED"
    assert morning_payload["review_scope"] == "BUY_ITEM_SCOPED_REVIEW"
    assert morning_payload["plan_overall_status"] == "APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW"
    assert morning_payload["approved_buy_item_ids"] == ["approved-buy-23700"]
    assert morning_payload["review_required_buy_item_ids"] == ["review-buy-38410"]

    sell_readiness = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=DAY1,
        mode="demo",
        readiness_scope="sell_planning",
        broker_write=False,
        external_delivery=False,
    )
    sell_result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=DAY1,
        mode="demo",
        exit_decisions=(),
    )
    preserved = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    assert sell_readiness.status == "READY"
    assert sell_result.status == "NO_SIGNAL"
    assert sell_result.preserved_existing_buy_pending is True
    assert preserved["pending_plan_id"] == "pending-order-plan-phase30-ak9r10"
    assert preserved["approved_buy_item_ids"] == ["approved-buy-23700"]
    assert preserved["review_required_buy_item_ids"] == ["review-buy-38410"]

    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=DAY1,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    after_submit = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    by_id = {item["pending_item_id"]: item for item in after_submit["items"]}
    assert submit.status == "PASS"
    assert submit.reason == "submitted_with_reviewed_buy_items_not_submitted"
    assert submit.submitted_count == 1
    assert submit.submitted_symbols == ("23700",)
    assert by_id["approved-buy-23700"]["state"] == "CONSUMED"
    assert by_id["review-buy-38410"]["state"] == "REVIEW_REQUIRED"
    reviewed = next(item for item in submit.submit_guard_item_evidence if item["pending_item_id"] == "review-buy-38410")
    assert reviewed["not_submitted_reason"] == "item_scoped_review_required"
    assert reviewed["blocked_other_items"] is False

    execution = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=DAY1,
        mode="demo",
        snapshot_provider=_filled_buy_snapshot,
    )
    current = _read_json(runtime_root / "persistent_ledger" / "state.json")
    after_execution = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    by_id = {item["pending_item_id"]: item for item in after_execution["items"]}
    assert execution.status == "PASS"
    assert execution.submitted_order_count == 1
    assert execution.fill_count >= 1
    assert "23700" in {position["symbol"] for position in current["positions"]}
    assert by_id["approved-buy-23700"]["state"] == "CONSUMED"
    assert by_id["review-buy-38410"]["state"] == "REVIEW_REQUIRED"

    _write_historical_safety_context(after_execution, tmp_path)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", after_execution)
    _write_runtime_operation_state(runtime_root, business_date=DAY1, mode="historical")
    _write_historical_asof_view(evidence_root, tmp_path, pd, business_date=DAY1, symbols=("23700",))
    current_readiness = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=DAY1,
        mode="historical",
        readiness_scope="current_valuation",
        broker_environment="historical_simulated",
        runtime_test_evidence_root=evidence_root,
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        broker_write=False,
        external_delivery=False,
    )
    valuation = run_current_valuation_refresh(
        runtime_root=runtime_root,
        business_date=DAY1,
        apply_current_valuation=True,
        now=datetime.fromisoformat(DAY1 + "T15:35:00+09:00"),
        market_evidence_path=evidence_root / "daily" / DAY1 / "market_refresh" / "historical_asof_view.json",
        safety_authority={
            "safety_status": "PASS",
            "safety_business_date": DAY1,
            "safety_policy_version": "historical_replay_neutral_safety_v1",
            "safety_source": "data_readiness_historical_temporal_authority",
            "safety_action_permissions": {"broker_write": "BLOCKED", "external_delivery": "BLOCKED"},
        },
        runtime_test_context={
            "run_id": RUN_ID,
            "profile_id": PROFILE_ID,
            "evidence_root": str(evidence_root),
            "business_date": DAY1,
        },
        environment_context={
            "mode": "historical",
            "broker_environment": "historical_simulated",
            "historical_replay": True,
            "broker_write": False,
            "external_delivery": False,
        },
        allow_legacy_temporal_current=True,
    )
    after_valuation = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    assert current_readiness.status == "READY"
    assert current_readiness.payload["components"]["pending"]["post_submit_residual_buy_review_current_valuation_ready"] is True
    assert valuation.status == "READY"
    assert valuation.apply_requested is True
    assert valuation.apply_executed is True
    assert after_valuation["items"][1]["state"] == "REVIEW_REQUIRED"
    assert after_valuation["items"][1]["approved"] is False

    day_completion = runtime_test_runner._write_day_completion_evidence(
        run_dir=run_dir,
        runtime_root=runtime_root,
        business_date=DAY1,
    )
    assert day_completion["status"] == "PASS"
    assert day_completion["pending_post_state"]["state"] == "REVIEW_REQUIRED"
    assert day_completion["completion_contract"]["completed_business_days_append_allowed"] is True

    lifecycle = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=DAY2,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(DAY2 + "T09:00:00+09:00"),
    )
    slot = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    history = _read_json(Path(lifecycle.manifest_fields["history_path"]))
    authority = lifecycle.manifest_fields["stale_residual_buy_review_expiration"]
    assert lifecycle.status == "EXPIRED"
    assert lifecycle.reason == "STALE_NEXT_DAY_RESIDUAL_BUY_REVIEW_EXPIRED"
    assert authority["original_target_session_date"] == DAY1
    assert authority["expiration_business_date"] == DAY2
    assert authority["consumed_buy_item_ids"] == ["approved-buy-23700"]
    assert authority["expired_residual_review_buy_item_ids"] == ["review-buy-38410"]
    assert authority["reviewed_buy_auto_approved"] is False
    assert authority["reviewed_buy_submitted"] is False
    assert authority["new_day_buy_requires_fresh_authority"] is True
    assert slot["state"] == "EMPTY"
    assert slot["active_pending"] is False
    assert history["transition_reason"] == "STALE_NEXT_DAY_RESIDUAL_BUY_REVIEW_EXPIRED"

    _write_runtime_operation_state(runtime_root, business_date=DAY2, mode="demo")
    _write_market_evidence(runtime_root, business_date=DAY2, quote_count=1)
    _write_safety_decision(runtime_root, business_date=DAY2)
    _write_broker_snapshot(runtime_root, business_date=DAY2)
    _write_day2_feature_artifacts(runtime_root, pd)
    _write_day2_buy_ai_opportunity(runtime_root)
    day2_readiness = evaluate_runtime_data_readiness(
        runtime_root=runtime_root,
        business_date=DAY2,
        mode="demo",
        readiness_scope="sell_planning",
        now=datetime.fromisoformat(DAY2 + "T09:05:00+09:00"),
        broker_write=False,
        external_delivery=False,
    )
    day2_sell = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=DAY2,
        mode="demo",
        exit_decisions=(),
    )
    post_day2 = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    current_day2 = _read_json(runtime_root / "persistent_ledger" / "state.json")
    assert day2_readiness.status == "READY"
    assert "pending_review_required" not in day2_readiness.payload["review_reasons"]
    assert day2_sell.status == "NO_SIGNAL"
    assert post_day2["state"] == "EMPTY"
    assert not any(item.get("pending_item_id") == "review-buy-38410" for item in post_day2.get("items", []))
    assert {position["symbol"] for position in current_day2["positions"]} == {"23700"}
    assert current_day2["cash"] == current["cash"]
    assert current_day2["valuation_as_of"] == DAY1
    assert current_day2["source_market_date"] == DAY1


def test_phase30_ak9r10_invalid_shapes_remain_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[], as_of=DAY1)
    policy_path = _policy_path(tmp_path)
    _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=DAY1,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    pending["items"][1]["submitted_order_id"] = "tampered-reviewed-buy-submit"
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_pending_lifecycle_review(
        runtime_root=runtime_root,
        business_date=DAY2,
        mode="demo",
        action="review",
        now=datetime.fromisoformat(DAY2 + "T09:00:00+09:00"),
    )

    assert submit.status == "PASS"
    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "stale_residual_buy_review_expiration_checks_failed"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_contract_calendar(root)
    _write_safety_decision(root, business_date=DAY1)
    return root


def _write_current_state(root: Path, *, positions: list[dict], as_of: str) -> None:
    market_value = sum(float(item["market_value"]) for item in positions)
    payload = {
        "schema_version": "runtime_v2_current_temporal_v1",
        "temporal_schema_version": "runtime_v2_current_temporal_v1",
        "asset_state_id": "asset-phase30-ak9r10",
        "environment": "demo",
        "runtime_mode": "demo",
        "source": "fixture",
        "as_of": as_of,
        "business_date": as_of,
        "position_state_as_of": as_of,
        "valuation_as_of": as_of,
        "source_market_date": as_of,
        "last_execution_date": as_of,
        "positions": positions,
        "cash": 1_000_000,
        "buying_power": 1_000_000,
        "market_value": market_value,
        "total_equity": 1_000_000 + market_value,
        "review_required": False,
        "production_equivalent": False,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": as_of,
        "updated_at": as_of,
    }
    _write_json(root / "persistent_ledger" / "state.json", payload)
    _write_json(
        root / "runtime_state" / "current_state.json",
        _runtime_operation_state_payload(business_date=as_of, mode="demo"),
    )
    _write_market_evidence(root, business_date=as_of, quote_count=max(len(positions), 1))
    _write_broker_snapshot(root, business_date=as_of)
    _write_dynamic_cash_exposure(root, business_date=as_of, cash=1_000_000, market_value=market_value)
    _write_position_sizing(root, business_date=as_of, positions=positions, cash=1_000_000, market_value=market_value)


def _write_runtime_operation_state(root: Path, *, business_date: str, mode: str) -> None:
    _write_json(root / "runtime_state" / "current_state.json", _runtime_operation_state_payload(business_date=business_date, mode=mode))


def _runtime_operation_state_payload(*, business_date: str, mode: str) -> dict:
    return {
        "schema_version": "runtime_v2_operation_state_v1",
        "role": "authoritative_runtime_operation_state",
        "business_date": business_date,
        "generated_at": business_date + "T09:00:00+09:00",
        "updated_at": business_date + "T09:00:00+09:00",
        "environment": mode,
        "runtime_mode": mode,
        "state": "CURRENT_STATE_LOADED",
        "safety_state": "NORMAL",
        "current_safety_state": "NORMAL",
        "source": "fixture",
        "asset_state_is_authoritative_here": False,
        "pending_state_is_authoritative_here": False,
    }


def _write_buy_item_scoped_review_pending(root: Path, *, policy_path: Path):
    policy = load_capital_deployment_policy(policy_path)
    policy_hash = capital_deployment_policy_hash(policy)
    order_plan_path = root / "fixtures" / "phase30_ak9r10_order_plan.json"
    _write_json(order_plan_path, {"order_plan_id": "order-plan-phase30-ak9r10"})
    accepted_generation = {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "phase30_ak9r10_full_chain_fixture",
        "mode": "demo",
        "requested_business_date": DAY1,
        "selected_business_date": DAY1,
        "accepted_generation_id": "phase30-ak9r10-generation",
        "accepted_generation_business_date": DAY1,
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
    }
    buy_pass = PendingOrderItem(
        pending_item_id="approved-buy-23700",
        symbol="23700",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=1000,
        estimated_amount=100_000,
        approved=True,
        state="APPROVED",
        feasibility_status="PASS",
        batch_submit_status="PASS_ITEM_SUBMITTABLE",
        listed_info=_listed_info("23700"),
        policy_version=policy.policy_version,
        policy_source=policy.policy_source,
        submit_policy_version=policy.policy_version,
        submit_policy_source=policy.policy_source,
        submit_policy_hash=policy_hash,
        evaluation_capital=policy.evaluation_capital,
        max_positions=policy.max_positions,
        min_order_amount=policy.min_order_amount,
        max_buy_order_amount=policy.max_buy_order_amount,
        max_sell_liquidation_amount=policy.max_sell_liquidation_amount,
        buy_notional_policy=policy.buy_notional_policy,
        sell_liquidation_policy=policy.sell_liquidation_policy,
        accepted_generation_id="phase30-ak9r10-generation",
        accepted_generation_business_date=DAY1,
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=accepted_generation,
        quantity_contract={
            "status": "PASS",
            "quantity_authority": "strategy_runtime_planning_authority",
            "quantity_status": "RESOLVED_EXECUTABLE",
            "position_count_authority": {
                "safety_hard_maximum": 5,
                "selected_dynamic_position_count": 5,
                "target_position_count": 5,
                "maximum_position_count": 5,
            },
            "cash_exposure_authority": {
                "selected_dynamic_cash_ratio": 0.20,
                "target_cash_ratio": 0.20,
                "selected_dynamic_exposure_ratio": 0.80,
                "target_gross_exposure_ratio": 0.80,
                "maximum_gross_exposure_ratio": 0.88,
                "current_total_equity": 1_000_000,
                "current_cash": 1_000_000,
                "current_market_value": 0,
            },
            "position_sizing_authority": {
                "positions": [
                    {
                        "security_code": "23700",
                        "symbol": "23700",
                        "target_weight": 0.10,
                        "target_notional": 100_000,
                        "incremental_buy_notional": 100_000,
                        "maximum_position_weight": 0.18,
                    }
                ],
                "effective_maximum_position_weight": 0.18,
            },
        },
    )
    buy_review = replace(
        buy_pass,
        pending_item_id="review-buy-38410",
        symbol="38410",
        quantity=100,
        estimated_price=3000,
        estimated_amount=300_000,
        approved=False,
        state="REVIEW_REQUIRED",
        feasibility_status="REVIEW_REQUIRED",
        batch_submit_status="ITEM_REVIEW_REQUIRED",
        item_review_reason="estimated amount exceeds selected_position_amount",
        listed_info=_listed_info("38410"),
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase30-ak9r10",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:phase30-ak9r10-order-plan",
        environment="demo",
        plan_created_date=DAY1,
        intended_submit_date=DAY1,
        target_session_date=DAY1,
        items=(buy_pass, buy_review),
        submit_policy_context=_submit_policy_context(policy),
    )
    pending = replace(
        pending,
        state=PendingPlanState.REVIEW_REQUIRED,
        approval=PendingApprovalLink(
            approval_path=str(root / "fixtures" / "phase30_ak9r10_approval.json"),
            approval_hash="sha256:phase30-ak9r10-approval",
            approval_status="APPROVED",
            approved_item_ids=("approved-buy-23700",),
            approval_expires_at=DAY1 + "T15:00:00+09:00",
            policy_version=policy.policy_version,
            policy_source=policy.policy_source,
            pending_policy_hash=policy_hash,
            submit_policy_version=policy.policy_version,
            submit_policy_source=policy.policy_source,
            submit_policy_hash=policy_hash,
            accepted_generation_id="phase30-ak9r10-generation",
            accepted_generation_business_date=DAY1,
            accepted_generation_binding_status="PASS",
            accepted_generation_binding=accepted_generation,
            approved_order_conditions={
                "approved-buy-23700": {
                    "schema_version": "runtime_v2_approved_order_condition.v1",
                    "condition_authority": "strategy_planning_approval_order_conditions",
                    "condition_consumer": "runtime_v2.submit.guards.run_submit_preflight",
                    "pending_item_id": "approved-buy-23700",
                    "issue_code": "23700",
                    "side": "BUY",
                    "quantity": 100,
                    "estimated_price": 1000,
                    "estimated_amount": 100_000,
                    "order_type": "MARKET",
                    "price_condition": "MARKET",
                    "limit_price": None,
                    "target_session": DAY1,
                    "time_in_force": "DAY",
                    "approval_runtime_path": "Production/Demo/Historical common runtime_v2",
                    "legacy_approval_used": False,
                    "approval_fallback_used": False,
                }
            },
        ),
        approved_item_ids=("approved-buy-23700",),
        buy_items_status="REVIEW_REQUIRED",
        sell_items_status="NOT_PRESENT",
        plan_overall_status="APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW",
        approved_buy_item_ids=("approved-buy-23700",),
        approved_sell_item_ids=(),
        review_required_buy_item_ids=("review-buy-38410",),
        review_required_sell_item_ids=(),
        review_scope="BUY_ITEM_SCOPED_REVIEW",
        review_scope_source="phase24_ht_planning_submit_feasibility_v1",
        review_scope_reason="estimated amount exceeds selected_position_amount",
        sell_continuation_allowed=True,
        planning_submit_feasibility={
            "status": "REVIEW_REQUIRED",
            "contract_id": "phase24_ht_planning_submit_feasibility_v1",
            "items": [
                {
                    "pending_item_id": "approved-buy-23700",
                    "side": "BUY",
                    "status": "PASS",
                    "reason": "planning_submit_feasibility_pass",
                    "violated_policy": "",
                    "violated_policy_source": "",
                },
                {
                    "pending_item_id": "review-buy-38410",
                    "side": "BUY",
                    "status": "REVIEW_REQUIRED",
                    "reason": "estimated amount exceeds selected_position_amount",
                    "violated_policy": "position_sizing",
                    "violated_policy_source": "fixture_position_sizing",
                },
            ],
        },
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _filled_buy_snapshot(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    _write_json(
        snapshot_path,
        {
            "generated_at": DAY1 + "T15:30:00+09:00",
            "orders": [
                {
                    "order_id_hash": "sha256:order-ak9r10-23700",
                    "pending_item_id": "approved-buy-23700",
                    "pending_plan_id": "pending-order-plan-phase30-ak9r10",
                    "issue_code": "23700",
                    "side": "buy",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "status": "全部約定",
                    "as_of": DAY1 + "T15:30:00+09:00",
                }
            ],
            "executions": [
                {
                    "execution_id": "exec-ak9r10-23700",
                    "order_id_hash": "sha256:order-ak9r10-23700",
                    "issue_code": "23700",
                    "side": "buy",
                    "quantity": "100",
                    "price": "1000",
                    "executed_at": DAY1 + "T15:30:00+09:00",
                }
            ],
            "positions": [{"issue_code": "23700", "quantity": "100", "average_price": "1000", "market_value": "100000"}],
            "buying_power": {"cash_available": "900000", "buying_power": "900000", "currency": "JPY"},
        },
    )
    _write_json(Path(kwargs["report_path"]), {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _write_historical_safety_context(pending: dict, tmp_path: Path) -> None:
    safety_context = {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision_id": f"historical-neutral-safety:{DAY1}",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_decision": "ALLOW",
        "safety_reason": "historical_neutral_no_event_safety_ready",
        "safety_business_date": DAY1,
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": str(tmp_path / "reports" / "runtime_tests" / "runs" / RUN_ID),
    }
    pending["environment"] = "historical"
    pending["safety_policy_version"] = "historical_replay_neutral_safety_v1"
    pending["safety_context"] = safety_context
    for item in pending["items"]:
        item.update(safety_context)
        item["temporal_authority_business_date"] = DAY1


def _write_historical_asof_view(
    evidence_root: Path,
    tmp_path: Path,
    pd,
    *,
    business_date: str,
    symbols: tuple[str, ...],
) -> None:
    parquet = tmp_path / f"normalized_ohlcv_{business_date}.parquet"
    calendar = tmp_path / f"trading_calendar_{business_date}.jsonl"
    pd.DataFrame([{"Date": business_date, "Code": symbol, "Close": 1000.0} for symbol in symbols]).to_parquet(parquet)
    _write_jsonl(
        calendar,
        [
            {"Date": "2026-07-07", "target_date": "2026-07-07", "HolDiv": "1"},
            {"Date": DAY1, "target_date": DAY1, "HolDiv": "1"},
            {"Date": DAY2, "target_date": DAY2, "HolDiv": "1"},
        ],
    )
    _write_json(
        evidence_root / "daily" / business_date / "market_refresh" / "historical_asof_view.json",
        {
            "schema_version": "phase17_l_historical_asof_view_v1",
            "status": "PASS",
            "reason": "historical_asof_view_ready",
            "business_date": business_date,
            "latest_available_market_date": business_date,
            "future_rows_excluded_from_consumer": True,
            "authorities": [
                {
                    "authority": "normalized_ohlcv",
                    "status": "PASS",
                    "reason": "historical_asof_authority_ready",
                    "business_date": business_date,
                    "physical_source_path": str(parquet),
                    "physical_source_hash": "fixture",
                    "logical_cutoff": business_date,
                    "logical_max_date": business_date,
                },
                {
                    "authority": "trading_calendar",
                    "status": "PASS",
                    "reason": "historical_calendar_authority_ready",
                    "business_date": business_date,
                    "physical_source_path": str(calendar),
                    "physical_source_hash": "fixture-calendar",
                    "logical_cutoff": business_date,
                    "logical_max_date": business_date,
                },
            ],
        },
    )


def _write_broker_snapshot(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "broker_readonly" / business_date / "tachibana_snapshot.json",
        {
            "generated_at": business_date + "T09:00:00+09:00",
            "positions": [{"issue_code": "23700", "quantity": "100", "average_price": "1000", "market_value": "100000"}],
            "orders": [],
            "executions": [],
            "buying_power": {"cash_available": "900000", "buying_power": "900000", "currency": "JPY"},
        },
    )


def _write_day2_feature_artifacts(root: Path, pd) -> None:
    operations_root = root / "operations"
    feature_dir = operations_root / "feature_artifacts" / DAY2
    feature_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "target_date": DAY2,
                "position_state_as_of": DAY1,
                "entry_date": DAY1,
                "code": "23700",
                "broker_issue_code": "23700",
                "holding_days": 1,
                "average_price": 1000.0,
                "current_price": 1000.0,
                "unrealized_return": 0.0,
                "quantity": 100.0,
                "feature_as_of_date": DAY2,
                "price_momentum_return_5d": 0.0,
                "price_momentum_return_20d": 0.0,
                "trend_close_over_ma_20d": 0.0,
                "trend_ma_5_20_ratio": 0.0,
                "volume_momentum_ratio_5d": 0.0,
                "volatility_return_std_20d": 0.0,
                "feature_source_artifact": "phase30_ak9r10_fixture",
                "feature_source_hash": "phase30-ak9r10-fixture-hash",
                "required_features": [],
                "optional_features": [],
                "missing_features": [],
                "defaulted_features": [],
                "temporal_validation_status": "PASS",
                "feature_version": "runtime_v2_pm_feature_input_v1",
                "data_until": DAY2,
                "created_at": DAY2 + "T08:00:00+09:00",
            }
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame([_feature_row("23700", CANDIDATE_REQUIRED_COLUMNS)]).to_parquet(
        feature_dir / "candidate_features.parquet",
        index=False,
    )
    pd.DataFrame([_feature_row("23700", OPPORTUNITY_REQUIRED_COLUMNS)]).to_parquet(
        feature_dir / "opportunity_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": DAY2, "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    _write_json(
        operations_root / "feature_date_contract" / f"{DAY2}.json",
        {
            "schema_version": "runtime_v2_feature_contract_v2",
            "status": "PASS",
            "reason": "requested_feature_artifacts_available",
            "requested_feature_date": DAY2,
            "selected_feature_date": DAY2,
            "latest_available_market_date": DAY2,
            "carryover_used": False,
            "carryover_reason": "",
            "freshness_lag_business_days": 0,
            "freshness_limit_business_days": 1,
            "feature_artifact_dir": str(feature_dir),
            "generated_feature_artifacts": {
                "candidate_features.parquet": str(feature_dir / "candidate_features.parquet"),
                "opportunity_feature_input.parquet": str(feature_dir / "opportunity_feature_input.parquet"),
                "position_feature_input.parquet": str(feature_dir / "position_feature_input.parquet"),
                "capital_policy_input.parquet": str(feature_dir / "capital_policy_input.parquet"),
            },
            "missing_feature_artifacts": [],
            "requested_feature_artifact_dir": str(feature_dir),
            "requested_missing_feature_artifacts": [],
            "price_source_alignment": "selected_feature_date",
            "consumer_ready": True,
            "candidate_schema_status": "READY",
            "opportunity_schema_status": "READY",
            "pm_schema_status": "READY",
            "consumer_readiness_artifact_path": str(operations_root / "feature_consumer_readiness" / f"{DAY2}.json"),
            "contract_artifact_path": str(operations_root / "feature_date_contract" / f"{DAY2}.json"),
        },
    )


def _write_day2_buy_ai_opportunity(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "buy_ai" / DAY2 / "opportunity_rankings.json",
        {
            "schema_version": "runtime_v2_opportunity_rankings_v1",
            "status": "PASS",
            "model_version": "phase30-ak9r10-fixture",
            "generated_at": DAY2 + "T08:30:00+09:00",
            "feature_date": DAY2,
            "rankings": [
                {
                    "target_date": DAY2,
                    "code": "23700",
                    "expected_edge_score": 0.01,
                    "buy_rank": 1,
                    "downside_risk_score": 0.4,
                }
            ],
        },
    )


def _feature_row(symbol: str, required_columns: tuple[str, ...]) -> dict:
    row = {"target_date": DAY2, "code": symbol}
    for column in required_columns:
        row.setdefault(column, 0.0)
    return row


def _write_market_evidence(root: Path, *, business_date: str, quote_count: int) -> None:
    _write_json(
        root / "runtime_state" / "market" / business_date / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": business_date,
            "business_date": business_date,
            "market_date": business_date,
            "status": "READY",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": quote_count,
            "market_summary": {"quote_count": quote_count},
        },
    )


def _write_position_sizing(root: Path, *, business_date: str, positions: list[dict], cash: float, market_value: float) -> None:
    total_equity = cash + market_value
    rows = []
    for item in positions:
        current_notional = float(item["market_value"])
        target_weight = 0.18
        target_notional = round(total_equity * target_weight, 2)
        incremental = max(round(target_notional - current_notional, 2), 0.0)
        rows.append(
            {
                "security_code": str(item["symbol"]),
                "membership_intent": "KEEP",
                "pm_action": "ADD",
                "current_weight": round(current_notional / total_equity, 6) if total_equity else 0.0,
                "base_weight": target_weight,
                "quality_adjustment": 1.0,
                "volatility_adjustment": 1.0,
                "pm_intent_adjustment": 1.0,
                "adjusted_weight": target_weight,
                "capped_weight": target_weight,
                "target_weight": target_weight,
                "weight_delta": round(target_weight - (current_notional / total_equity if total_equity else 0.0), 6),
                "target_notional": target_notional,
                "current_notional": current_notional,
                "incremental_target_notional": incremental,
                "incremental_buy_notional": incremental,
                "minimum_meaningful_notional": 0.0,
                "maximum_position_weight": target_weight,
                "sizing_status": "SIZED",
                "confidence": 0.9,
                "uncertainty": "LOW",
                "reason_codes": ["fixture_position_sizing"],
                "target_weight_authority": {"portfolio_policy_reference": {"path": "fixture_portfolio_policy"}},
            }
        )
    total_target_weight = round(sum(float(row["target_weight"]) for row in rows), 6)
    _write_json(
        root / "strategy_artifacts" / "position_sizing" / business_date / "position_sizing.json",
        {
            "schema_version": "position_sizing.v1",
            "business_date": business_date,
            "as_of": f"{business_date}T00:00:00+00:00",
            "feature_date": business_date,
            "artifact_lifecycle_status": "DRAFT",
            "source_authority_status": "VALID",
            "producer_result_status": "PASS",
            "runtime_consumer_eligibility": "NOT_ELIGIBLE",
            "target_gross_exposure_ratio": 0.80,
            "target_position_count": max(len(rows), 5),
            "positions": rows,
            "positions_sized": len(rows),
            "positions_withheld": 0,
            "total_target_weight": total_target_weight,
            "residual_cash_ratio": round(max(1.0 - total_target_weight, 0.0), 6),
            "concrete_target_weight_decided": True,
            "target_notional_decided": True,
            "share_quantity_decided": False,
            "lot_rounding_decided": False,
            "order_price_decided": False,
            "pending_decided": False,
            "submit_decided": False,
            "strategy_maximum_position_weight": 0.18,
            "strategy_maximum_position_weight_source": "fixture#strategy_maximum_position_weight",
            "safety_maximum_position_weight": 0.25,
            "safety_maximum_position_weight_source": "fixture#safety_maximum_position_weight",
            "safety_authority_status": "PASS",
            "effective_maximum_position_weight": 0.18,
            "effective_maximum_position_weight_derivation": "min(strategy_maximum_position_weight, safety_maximum_position_weight)",
            "explicit_zero_cap": False,
            "emergency_brake_active": False,
            "market_context_risk_state": "NORMAL",
            "dynamic_position_count": max(len(rows), 5),
            "dynamic_cash_exposure": 0.80,
            "aggregate_exposure_cap": 0.80,
            "source_artifacts": [{"role": "portfolio_policy", "path": "fixture_portfolio_policy", "required": True, "status": "PASS"}],
            "source_hashes": [{"role": "fixture", "path": "fixture", "sha256": "0" * 64}],
            "temporal_safety": {
                "point_in_time": True,
                "future_leakage_used": False,
                "feature_date_lte_business_date": True,
                "implicit_latest_fallback_used": False,
                "previous_day_position_sizing_copied": False,
            },
            "production_consumer_connected": False,
            "runtime_switch_performed": False,
        },
    )


def _write_dynamic_cash_exposure(root: Path, *, business_date: str, cash: float, market_value: float) -> None:
    total_equity = cash + market_value
    target_cash_ratio = 0.20
    target_exposure_ratio = 0.80
    _write_json(
        root / "strategy_artifacts" / "dynamic_cash_exposure" / business_date / "dynamic_cash_exposure.json",
        {
            "schema_version": "dynamic_cash_exposure.v1",
            "business_date": business_date,
            "as_of": f"{business_date}T00:00:00+00:00",
            "feature_date": business_date,
            "artifact_lifecycle_status": "DRAFT",
            "source_authority_status": "VALID",
            "producer_result_status": "PASS",
            "runtime_consumer_eligibility": "NOT_ELIGIBLE",
            "minimum_cash_ratio": 0.12,
            "target_cash_ratio": target_cash_ratio,
            "maximum_cash_ratio": 0.50,
            "minimum_gross_exposure_ratio": 0.40,
            "target_gross_exposure_ratio": target_exposure_ratio,
            "maximum_gross_exposure_ratio": 0.88,
            "portfolio_total_equity": total_equity,
            "current_cash": cash,
            "current_market_value": market_value,
            "pending_reserved_cash": 0.0,
            "net_available_cash": cash,
            "target_cash_amount": round(total_equity * target_cash_ratio, 2),
            "target_invested_ratio": target_exposure_ratio,
            "target_invested_notional": round(total_equity * target_exposure_ratio, 2),
            "current_invested_ratio": 0.0 if total_equity <= 0 else round(market_value / total_equity, 6),
            "incremental_deployment_capacity": max(round(total_equity * target_exposure_ratio - market_value, 2), 0.0),
            "strategy_fixed_jpy_exposure_cap_used": False,
            "legacy_max_exposure_authority_used": False,
            "current_cash_ratio": 0.0 if total_equity <= 0 else round(cash / total_equity, 6),
            "current_gross_exposure_ratio": 0.0 if total_equity <= 0 else round(market_value / total_equity, 6),
            "cash_posture": "DEPLOY",
            "exposure_posture": "INCREASE",
            "capital_constraint_status": "SUFFICIENT",
            "confidence": 0.9,
            "uncertainty": "LOW",
            "reason_codes": ["fixture_dynamic_cash_exposure"],
            "source_artifacts": [{"role": "fixture", "path": "fixture", "required": True, "status": "PASS"}],
            "source_hashes": [{"role": "fixture", "path": "fixture", "sha256": "0" * 64}],
            "temporal_safety": {
                "point_in_time": True,
                "future_leakage_used": False,
                "feature_date_lte_business_date": True,
                "implicit_latest_fallback_used": False,
                "previous_day_dynamic_cash_exposure_copied": False,
            },
            "production_consumer_connected": False,
            "runtime_switch_performed": False,
            "position_sizing_decided": False,
            "allocation_decided": False,
            "quantity_decided": False,
            "lot_rounding_decided": False,
        },
    )


def _listed_info(symbol: str) -> dict:
    return {
        "code": symbol,
        "current_listed": True,
        "market": "プライム",
        "product_category": "011",
        "security_type": "011",
        "opportunity_buy_eligibility_status": "PASS",
        "opportunity_buy_eligibility": "BUY_ELIGIBLE",
        "opportunity_expected_edge_score": 0.10,
        "opportunity_expected_return": 0.10,
        "opportunity_no_buy_reason": "",
        "opportunity_buy_rank": 1,
        "opportunity_business_date": DAY1,
        "opportunity_feature_date": DAY1,
        "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
        "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
    }


def _write_contract_calendar(root: Path) -> None:
    _write_jsonl(
        root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.jsonl",
        [
            {"Date": "2026-07-07", "target_date": "2026-07-07", "HolDiv": "1"},
            {"Date": DAY1, "target_date": DAY1, "HolDiv": "1"},
            {"Date": DAY2, "target_date": DAY2, "HolDiv": "1"},
        ],
    )


def _write_safety_decision(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "business_date": business_date,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "fixture",
            "review_required": False,
        },
    )


def _policy_path(tmp_path: Path) -> Path:
    path = tmp_path / "capital_deployment_policy.json"
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _submit_policy_context(policy) -> dict:
    return {
        "policy_version": policy.policy_version,
        "policy_source": policy.policy_source,
        "pending_policy_hash": capital_deployment_policy_hash(policy),
        "submit_policy_version": policy.policy_version,
        "submit_policy_source": policy.policy_source,
        "submit_policy_hash": capital_deployment_policy_hash(policy),
        "evaluation_capital": policy.evaluation_capital,
        "max_positions": policy.max_positions,
        "min_order_amount": policy.min_order_amount,
        "max_buy_order_amount": policy.max_buy_order_amount,
        "max_sell_liquidation_amount": policy.max_sell_liquidation_amount,
        "buy_notional_policy": policy.buy_notional_policy,
        "sell_liquidation_policy": policy.sell_liquidation_policy,
    }


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file=Path("/tmp/phase30-ak9r10-second-password"),
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
