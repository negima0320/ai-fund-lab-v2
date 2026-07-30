from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _approved_pending,
    _item,
    _write_current_state,
    _write_policy,
    _write_safety_decision,
)


BUSINESS_DATE = "2026-07-09"


def test_phase23_ab_authorized_no_order_empty_pending_submit_passes_without_broker(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _write_no_order_authority(runtime_root)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "PASS"
    assert result.reason == "NO_ORDER_AUTHORIZED"
    assert result.pending_plan_id == pending.pending_plan_id
    assert result.pending_item_count == 0
    assert result.submitted_count == 0
    assert result.demo_submit_executed is False
    assert result.submit_action == "NO_SUBMISSION_REQUIRED"
    assert result.no_order_authority_status == "PASS"
    assert result.no_order_authority_evidence["status"] == "PASS"


def test_phase23_ab_empty_pending_without_no_order_authority_fails_closed(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = promote_order_plan_to_pending(
        order_plan_id="strategy-plan-no-order-missing",
        source_order_plan_path=str(runtime_root / "runtime_state" / "strategy_planning" / BUSINESS_DATE / "order_plan.json"),
        source_order_plan_hash="missing-authority-hash",
        environment="demo",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=(),
    )
    write_pending_order_plan(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        replace(pending, state=pending.state.EMPTY),
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert result.reason == "authorized no-order order plan missing"


def test_phase23_ab_no_order_business_date_mismatch_fails_closed(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_no_order_authority(runtime_root, approval_overrides={"business_date": "2026-07-08"})

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "authorized no-order approval business_date mismatch"


def test_phase23_ab_no_order_hash_mismatch_fails_closed(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_no_order_authority(runtime_root, approval_overrides={"order_plan_hash": "bad-hash"})

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "authorized no-order approval order_plan_hash mismatch"


def test_phase23_ab_zero_item_rejected_no_order_fails_closed(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_no_order_authority(runtime_root, approval_overrides={"status": "REJECTED"})

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "authorized no-order approval status mismatch"


def test_phase23_ab_plain_empty_container_without_authority_fails_closed(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "status": "EMPTY",
            "state": "EMPTY",
            "active_pending": False,
            "items": [],
            "approved_item_ids": [],
        },
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pending EMPTY no_order_authority missing"


def test_phase23_ab_approved_executable_pending_path_is_preserved(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    pending = _approved_pending(
        (
            _item(
                pending_item_id="buy-1",
                symbol="7203",
                side="BUY",
                quantity=100,
                estimated_price=1000,
                estimated_amount=100_000,
            ),
        ),
        policy_path=policy_path,
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "PASS"
    assert result.submitted_count == 1
    assert result.submit_action == "SUBMIT"


def test_phase23_ab_execution_accepts_authorized_no_submission_required(tmp_path: Path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    _write_no_order_authority(runtime_root)
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    manifest_path = runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE / "runtime-v2-submit-ab-test.json"
    _write_json(
        manifest_path,
        {
            **submit.to_stage_details(),
            "job": "submit",
            "business_date": BUSINESS_DATE,
            "exit_code": 0,
            "final_state": "PASS",
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
            },
        },
    )

    execution = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
    )

    assert execution.status == "PASS"
    assert execution.reason == "no_submitted_orders"
    assert execution.execution_action == "NO_ACTION"
    assert execution.executions_count == 0
    assert execution.fill_count == 0


def _runtime_root(tmp_path: Path) -> Path:
    runtime_root = tmp_path / ".runtime"
    (runtime_root / "pending_order_plan").mkdir(parents=True)
    (runtime_root / "runtime_state").mkdir(parents=True)
    ledger = runtime_root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    _write_safety_decision(runtime_root)
    return runtime_root


def _write_no_order_authority(
    runtime_root: Path,
    *,
    approval_overrides: dict | None = None,
):
    planning_dir = runtime_root / "runtime_state" / "strategy_planning" / BUSINESS_DATE
    strategy_dir = runtime_root / "strategy" / BUSINESS_DATE
    runtime_planning_path = strategy_dir / "runtime_planning.json"
    position_sizing_path = strategy_dir / "position_sizing.json"
    order_plan_path = planning_dir / "order_plan.json"
    approval_path = planning_dir / "approval_artifact.json"
    runtime_planning = {
        "business_date": BUSINESS_DATE,
        "producer_result_status": "PASS",
        "plans": [
            {
                "planning_id": "rp-no-order-7203",
                "security_code": "7203",
                "planning_intent": "NO_ORDER",
                "order_side_intent": "NONE",
                "quantity_required": False,
                "quantity_status": "RESOLVED_ZERO_ALLOCATION",
                "planned_quantity": 0,
            }
        ],
    }
    position_sizing = {
        "business_date": BUSINESS_DATE,
        "producer_result_status": "PASS",
        "positions": [],
    }
    _write_json(runtime_planning_path, runtime_planning)
    _write_json(position_sizing_path, position_sizing)
    order_plan = {
        "schema_version": "phase23_i_strategy_authority_order_plan.v1",
        "order_plan_id": "strategy-plan-demo-no-order",
        "environment": "demo",
        "business_date": BUSINESS_DATE,
        "target_session_date": BUSINESS_DATE,
        "status": "NO_ORDER_AUTHORIZED",
        "planning_consumer_eligibility": "NO_ORDER_AUTHORIZED",
        "planning_authority": "phase22_strategy_runtime_planning",
        "strategy_artifact_path": str(runtime_planning_path),
        "position_sizing_artifact_path": str(position_sizing_path),
        "items": [],
        "broker_write_allowed": False,
        "broker_write_performed": False,
        "production_decision_allowed": False,
        "silent_fallback_used": False,
        "latest_fallback_used": False,
        "future_information_used": False,
    }
    _write_json(order_plan_path, order_plan)
    order_plan_hash = _hash_file(order_plan_path)
    pending = promote_order_plan_to_pending(
        order_plan_id=order_plan["order_plan_id"],
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash=order_plan_hash,
        environment="demo",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=(),
    )
    pending = replace(pending, state=pending.state.EMPTY)
    approval = {
        "schema_version": "phase23_ab_no_order_authorized_approval.v1",
        "status": "NO_ORDER_AUTHORIZED",
        "reason": "strategy_planning_no_order_authorized",
        "business_date": BUSINESS_DATE,
        "target_session_date": BUSINESS_DATE,
        "pending_plan_id": pending.pending_plan_id,
        "order_plan_id": order_plan["order_plan_id"],
        "order_plan_path": str(order_plan_path),
        "order_plan_hash": order_plan_hash,
        "runtime_planning_path": str(runtime_planning_path),
        "runtime_planning_hash": _hash_file(runtime_planning_path),
        "position_sizing_path": str(position_sizing_path),
        "position_sizing_hash": _hash_file(position_sizing_path),
        "planning_consumer_eligibility": "NO_ORDER_AUTHORIZED",
        "runtime_planning_status": "PASS",
        "pending_item_count": 0,
        "quantity_unresolved_count": 0,
        "review_required_quantity_count": 0,
        "broker_write_allowed": False,
        "broker_write_performed": False,
        "production_decision_allowed": False,
    }
    approval.update(approval_overrides or {})
    _write_json(approval_path, approval)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
