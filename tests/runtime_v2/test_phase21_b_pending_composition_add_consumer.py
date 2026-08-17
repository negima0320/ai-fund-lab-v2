import json
import hashlib
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.broker.settings import BrokerSettings
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.pending.models import PendingApprovalLink, PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link, promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.add_consumer import (
    LEGACY_ADD_MIGRATION_STATE,
    build_legacy_add_compatibility_artifact,
    evaluate_legacy_add_double_authority_guard,
    validate_legacy_add_compatibility_lineage,
)
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import SellExitDecision, run_sell_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import capital_deployment_policy_hash, load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.position_management.producer import _sell_exit_decisions_from_artifact
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


def test_phase21_b_no_signal_preserves_existing_buy_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    existing = _write_existing_buy_pending(runtime_root, symbol="7203")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "NO_SIGNAL"
    assert result.preserved_existing_buy_pending is True
    assert result.pending_plan_id == existing.pending_plan_id
    assert pending["pending_plan_id"] == existing.pending_plan_id
    assert pending["state"] == "APPROVED"
    assert pending["items"][0]["side"] == "BUY"


def test_phase29_l21t_f_no_signal_preserves_submit_visible_buy_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    pending = _write_submit_visible_buy_pending(
        runtime_root,
        policy_path=policy_path,
        pending_item_id="buy-78780",
        symbol="78780",
        quantity=100,
        estimated_price=2420,
        estimated_amount=242_000,
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "NO_SIGNAL"
    assert result.pending_composition_model == "PRESERVE_EXISTING_BUY_PENDING"
    assert result.pending_composition_status == "PASS"
    assert result.preserved_existing_buy_pending is True
    assert current_pending["state"] == "APPROVED"
    assert current_pending["items"][0]["symbol"] == "78780"
    assert current_pending["items"][0]["side"] == "BUY"
    assert current_pending["approved_item_ids"] == ["buy-78780"]
    snapshot = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "pre_sell_pending_snapshot_evidence.json")
    assert snapshot["pending_snapshot"]["approved_buy_item_count"] == 1
    assert snapshot["pending_snapshot"]["active_buy_pending_reason"] == "PASS"
    assert submit.status == "PASS"
    assert submit.submitted_count == 1
    assert submit.submit_guard_item_evidence[0]["symbol"] == "78780"
    assert submit.submit_guard_item_evidence[0]["side"] == "BUY"


def test_phase21_b_no_signal_without_existing_buy_writes_empty(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "NO_SIGNAL"
    assert result.preserved_existing_buy_pending is False
    assert pending["status"] == "EMPTY"
    assert pending["active_pending"] is False
    assert pending["no_order_authority_status"] == "PASS"
    assert pending["no_order_authority"]["status"] == "NO_ORDER_AUTHORIZED"
    assert "sell_no_signal" in pending["no_order_authority"]["authority_reason_codes"]


def test_phase24_e1_mixed_empty_materializes_no_order_authority_and_submit_accepts(tmp_path):
    business_date = "2022-07-06"
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path, max_buy_order_amount=12_920)
    policy = load_capital_deployment_policy(policy_path)
    _write_current_state(
        runtime_root,
        positions=[_current_position("94320", quantity=1100, price=153.3, as_of=business_date)],
        as_of=business_date,
    )
    _write_strategy_no_order_authority(runtime_root, business_date=business_date)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="94320",
                quantity=0,
                reason="add",
                source_decision="ADD",
                source_decision_id="pm-2022-07-06-94320-add",
            ),
        ),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "NO_SIGNAL"
    assert result.add_consumer_status == LEGACY_ADD_MIGRATION_STATE
    assert result.add_accepted_count == 0
    assert result.add_rejected_count == 0
    assert pending["state"] == "EMPTY"
    assert pending["items"] == []
    assert pending["no_order_authority_status"] == "PASS"
    reason_codes = pending["no_order_authority"]["authority_reason_codes"]
    assert "existing_position_capacity_satisfied" in reason_codes
    assert "sell_no_signal" in reason_codes
    assert "no_executable_order_items" in reason_codes
    assert pending["pm_add_consumer"]["decision_effect"] == "NONE"
    assert pending["pm_add_consumer"]["quantity_authority"] == "NONE"
    assert pending["pm_add_consumer"]["pending_authority"] == "NONE"
    assert pending["pm_add_consumer"]["approval_authority"] == "NONE"
    assert pending["pm_add_consumer"]["submit_authority"] == "NONE"
    assert pending["pm_add_consumer"]["telemetry_only"] is True
    assert submit.status == "PASS"
    assert submit.submitted_count == 0
    assert submit.no_order_authority_status == "PASS"
    assert submit.submit_action == "NO_ACTION"


def test_phase24_e1_empty_no_order_authority_business_date_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending = _load_json(pending_path)
    pending["no_order_authority"]["business_date"] = "2026-07-07"
    _write_json(pending_path, pending)

    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert submit.status == "REVIEW_REQUIRED"
    assert submit.reason == "pending EMPTY no_order_authority business_date mismatch"


def test_phase24_e1_empty_no_order_authority_source_hash_mismatch_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    order_plan_path = runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "order_plan.json"
    order_plan = _load_json(order_plan_path)
    order_plan["reason"] = "tampered"
    _write_json(order_plan_path, order_plan)

    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert submit.status == "REVIEW_REQUIRED"
    assert submit.reason == "pending EMPTY no_order_authority source_artifact hash mismatch"


def test_phase21_b_sell_order_composes_existing_buy_and_sell_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    _write_existing_buy_pending(runtime_root, symbol="7203")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=100, reason="exit signal"),),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.composite_pending is True
    assert result.pending_composition_model == "COMPOSITE_PENDING_PLAN"
    assert sorted(item["side"] for item in pending["items"]) == ["BUY", "SELL"]
    assert sorted(pending["approval"]["approved_item_ids"]) == sorted(item["pending_item_id"] for item in pending["items"])


def test_phase29_l21t_f_sell_order_composes_submit_visible_buy_and_sell_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    pending = _write_submit_visible_buy_pending(
        runtime_root,
        policy_path=policy_path,
        pending_item_id="buy-94320",
        symbol="94320",
        quantity=100,
        estimated_price=155.1,
        estimated_amount=15_510,
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=100, reason="exit signal"),),
        capital_deployment_policy=load_capital_deployment_policy(policy_path),
        submit_policy_context=_submit_policy_context(load_capital_deployment_policy(policy_path)),
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.pending_composition_model == "COMPOSITE_PENDING_PLAN"
    assert result.pending_composition_status == "PASS"
    assert result.preserved_existing_buy_pending is True
    assert result.composite_pending is True
    by_side = {item["side"]: item for item in current_pending["items"]}
    assert by_side["BUY"]["symbol"] == "94320"
    assert by_side["BUY"]["quantity"] == 100
    assert by_side["SELL"]["symbol"] == "6522"
    assert sorted(current_pending["approved_item_ids"]) == sorted(item["pending_item_id"] for item in current_pending["items"])
    assert sorted(current_pending["approval"]["approved_item_ids"]) == sorted(current_pending["approved_item_ids"])


def test_phase30_ak8r_multiple_buy_multiple_sell_composes_and_reaches_submit(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    policy = load_capital_deployment_policy(policy_path)
    _write_current_state(
        runtime_root,
        positions=[
            _current_position("6522", quantity=100, price=102),
            _current_position("76010", quantity=500, price=254),
        ],
    )
    _write_submit_visible_buy_pending(
        runtime_root,
        policy_path=policy_path,
        pending_item_id="buy-43550",
        symbol="43550",
        quantity=100,
        estimated_price=284,
        estimated_amount=28_400,
    )
    _append_submit_visible_buy_item(
        runtime_root,
        pending_item_id="buy-76920",
        symbol="76920",
        quantity=300,
        estimated_price=81.3,
        estimated_amount=24_390,
    )
    _write_broker_snapshots(
        runtime_root,
        records=[
            {"symbol": "6522", "quantity": 100, "available_quantity": 100},
            {"symbol": "76010", "quantity": 500, "available_quantity": 500},
        ],
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(
            SellExitDecision(symbol="6522", quantity=100, reason="mandatory exit", source_decision="EXIT"),
            SellExitDecision(symbol="76010", quantity=100, reason="risk reduce", source_decision="REDUCE", reduce_intensity="LIGHT"),
        ),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    composition = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "pending_composition_evidence.json")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "PASS"
    assert result.pending_composition_model == "COMPOSITE_PENDING_PLAN"
    assert result.pending_composition_status == "PASS"
    assert result.preserved_existing_buy_pending is True
    assert result.composite_pending is True
    assert sorted((item["side"], item["symbol"]) for item in current_pending["items"]) == [
        ("BUY", "43550"),
        ("BUY", "76920"),
        ("SELL", "6522"),
        ("SELL", "76010"),
    ]
    assert sorted(current_pending["approved_buy_item_ids"]) == ["buy-43550", "buy-76920"]
    assert len(current_pending["approved_sell_item_ids"]) == 2
    assert sorted(current_pending["approved_item_ids"]) == sorted(item["pending_item_id"] for item in current_pending["items"])
    assert composition["status"] == "PASS"
    assert composition["pre_sell_buy_pending_count"] == 2
    assert composition["preservable_buy_count"] == 2
    assert composition["sell_count"] == 2
    assert composition["composed_buy_count"] == 2
    assert composition["composed_sell_count"] == 2
    assert composition["dropped_buy_count"] == 0
    assert composition["final_canonical_pending_count"] == 4
    assert composition["valid_buy_pending_silent_overwrite_prohibited"] is True
    assert composition["sell_existence_alone_cannot_drop_valid_buy"] is True
    assert submit.status == "PASS"
    assert submit.submitted_count == 4
    assert sorted((item["side"], item["symbol"]) for item in submit.submit_guard_item_evidence) == [
        ("BUY", "43550"),
        ("BUY", "76920"),
        ("SELL", "6522"),
        ("SELL", "76010"),
    ]


def test_phase29_l21t_f_no_signal_preserves_invalid_active_buy_fail_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    _write_submit_visible_buy_pending(
        runtime_root,
        policy_path=policy_path,
        pending_item_id="buy-78780",
        symbol="78780",
        quantity=100,
        estimated_price=2420,
        estimated_amount=242_000,
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    tampered = _load_json(pending_path)
    tampered["approved_item_ids"] = []
    tampered["items"][0]["approved"] = False
    _write_json(pending_path, tampered)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    current_pending = _load_json(pending_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_composition_model == "PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL"
    assert result.pending_composition_status == "REVIEW_REQUIRED"
    assert result.preserved_existing_buy_pending is False
    assert "ACTIVE_PENDING_NOT_EMPTY:active_buy_missing" in result.reason
    assert current_pending["state"] == "APPROVED"
    assert current_pending["pending_plan_id"] == tampered["pending_plan_id"]
    assert current_pending["items"][0]["symbol"] == "78780"
    assert current_pending["approved_item_ids"] == []
    assert result.pre_sell_pending_snapshot["active_buy_pending_reason"] == "active_buy_missing"
    snapshot = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "pre_sell_pending_snapshot_evidence.json")
    assert snapshot["pending_snapshot"]["approved_buy_item_count"] == 0
    assert snapshot["pending_snapshot"]["items"][0]["approved_by_top_level"] is False


def test_phase29_l21t_f_sell_order_preserves_invalid_active_buy_fail_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("6522", quantity=100, price=102)])
    _write_submit_visible_buy_pending(
        runtime_root,
        policy_path=policy_path,
        pending_item_id="buy-94320",
        symbol="94320",
        quantity=100,
        estimated_price=155.1,
        estimated_amount=15_510,
    )
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    tampered = _load_json(pending_path)
    tampered["approved_item_ids"] = []
    tampered["items"][0]["approved"] = False
    _write_json(pending_path, tampered)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="6522", quantity=100, reason="exit signal"),),
        capital_deployment_policy=load_capital_deployment_policy(policy_path),
        submit_policy_context=_submit_policy_context(load_capital_deployment_policy(policy_path)),
    )
    current_pending = _load_json(pending_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_composition_model == "PRESERVE_ACTIVE_PENDING_ON_INVALID_BUY"
    assert "existing_buy_pending_not_preservable:active_buy_missing" in result.reason
    assert current_pending["pending_plan_id"] == tampered["pending_plan_id"]
    assert [(item["symbol"], item["side"]) for item in current_pending["items"]] == [("94320", "BUY")]
    assert current_pending["approved_item_ids"] == []
    assert result.pre_sell_pending_snapshot["active_buy_pending_reason"] == "active_buy_missing"


def test_phase29_l21t_m_buy_item_scoped_review_composes_valid_reduce_sell(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    policy = load_capital_deployment_policy(policy_path)
    _write_current_state(runtime_root, positions=[_current_position("76010", quantity=500, price=254)])
    reviewed_buy = _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="76010",
                quantity=100,
                reason="reduce signal",
                source_decision="REDUCE",
                reduce_intensity="LIGHT",
                source_decision_id="pm-76010-reduce",
            ),
        ),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.pending_composition_model == "BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_COMPOSITE_PENDING_PLAN"
    assert result.pending_composition_status == "PASS"
    assert result.composite_pending is True
    assert current_pending["state"] == "REVIEW_REQUIRED"
    assert current_pending["review_scope"] == "BUY_ITEM_SCOPED_REVIEW"
    assert current_pending["sell_continuation_allowed"] is True
    assert current_pending["approved_buy_item_ids"] == ["buy-pass-24350"]
    assert current_pending["review_required_buy_item_ids"] == ["buy-review-30410"]
    assert len(current_pending["approved_sell_item_ids"]) == 1
    assert sorted(current_pending["approved_item_ids"]) == sorted(["buy-pass-24350", *current_pending["approved_sell_item_ids"]])
    by_id = {item["pending_item_id"]: item for item in current_pending["items"]}
    assert by_id["buy-pass-24350"]["batch_submit_status"] == "PASS_ITEM_SUBMITTABLE"
    assert by_id["buy-pass-24350"]["approved"] is True
    assert by_id["buy-review-30410"]["batch_submit_status"] == "ITEM_REVIEW_REQUIRED"
    assert by_id["buy-review-30410"]["approved"] is False
    sell = next(item for item in current_pending["items"] if item["side"] == "SELL")
    assert sell["symbol"] == "76010"
    assert sell["side"] == "SELL"
    assert sell["quantity"] == 100
    assert sell["source_decision_type"] == "REDUCE"
    assert sell["approved"] is True
    assert result.pending_plan_id.startswith("pending-order-plan-buy-review-sell-continuation")
    assert reviewed_buy.pending_plan_id != result.pending_plan_id


def test_phase29_l21t_m_buy_item_scoped_review_composes_valid_exit_sell_and_submit_filters_buy(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    policy = load_capital_deployment_policy(policy_path)
    _write_current_state(runtime_root, positions=[_current_position("76010", quantity=500, price=254)])
    _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)
    _write_broker_snapshot(runtime_root, symbol="76010", quantity=500, available_quantity=500)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="76010",
                quantity=500,
                reason="exit signal",
                source_decision="EXIT",
                source_decision_id="pm-76010-exit",
            ),
        ),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert len(current_pending["approved_sell_item_ids"]) == 1
    assert current_pending["approved_buy_item_ids"] == ["buy-pass-24350"]
    assert current_pending["review_required_buy_item_ids"] == ["buy-review-30410"]
    assert submit.status == "PASS"
    assert submit.submitted_count == 2
    assert sorted(submit.submitted_symbols) == ["24350", "76010"]
    assert sorted((item["side"], item["symbol"]) for item in submit.submit_guard_item_evidence) == [
        ("BUY", "24350"),
        ("BUY", "30410"),
        ("SELL", "76010"),
    ]
    reviewed = next(item for item in submit.submit_guard_item_evidence if item["symbol"] == "30410")
    assert reviewed["authority_type"] == "BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED"
    assert reviewed["blocked_other_items"] is False


def test_phase29_l21t_m_unscoped_invalid_buy_still_preserved_fail_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("76010", quantity=500, price=254)])
    _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path, sell_continuation_allowed=False)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(
            SellExitDecision(
                symbol="76010",
                quantity=100,
                reason="reduce signal",
                source_decision="REDUCE",
                reduce_intensity="LIGHT",
            ),
        ),
        capital_deployment_policy=load_capital_deployment_policy(policy_path),
        submit_policy_context=_submit_policy_context(load_capital_deployment_policy(policy_path)),
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_composition_model == "PRESERVE_ACTIVE_PENDING_ON_INVALID_BUY"
    assert current_pending["approved_item_ids"] == []
    assert [item["side"] for item in current_pending["items"]] == ["BUY", "BUY"]


def test_phase29_l21t_m_buy_item_scoped_review_no_signal_preserves_review_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    reviewed_buy = _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)
    _write_current_state(runtime_root, positions=[_current_position("76010", quantity=500, price=254)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(),
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "NO_SIGNAL"
    assert result.reason == "NO_SIGNAL:exit_ai_no_sell_signal"
    assert result.pending_plan_id == reviewed_buy.pending_plan_id
    assert result.pending_composition_model == "PRESERVE_EXISTING_BUY_PENDING"
    assert result.pending_composition_status == "PASS"
    assert result.preserved_existing_buy_pending is True
    assert current_pending["pending_plan_id"] == reviewed_buy.pending_plan_id
    assert current_pending["state"] == "REVIEW_REQUIRED"
    assert current_pending["review_scope"] == "BUY_ITEM_SCOPED_REVIEW"
    assert current_pending["sell_continuation_allowed"] is True
    assert [item["side"] for item in current_pending["items"]] == ["BUY", "BUY"]
    assert current_pending["approved_buy_item_ids"] == ["buy-pass-24350"]
    assert current_pending["review_required_buy_item_ids"] == ["buy-review-30410"]
    by_id = {item["pending_item_id"]: item for item in current_pending["items"]}
    assert by_id["buy-pass-24350"]["batch_submit_status"] == "PASS_ITEM_SUBMITTABLE"
    assert by_id["buy-review-30410"]["batch_submit_status"] == "ITEM_REVIEW_REQUIRED"


def test_phase30_ak9r1_buy_item_scoped_review_submits_pass_subset(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[])
    reviewed_buy = _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.reason == "submitted_with_reviewed_buy_items_not_submitted"
    assert result.submit_action == "SUBMIT"
    assert result.submitted_count == 1
    assert result.pending_item_count == 2
    assert result.no_order_authority_status == "PASS"
    assert result.no_order_authority_evidence["authority_type"] == "BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION"
    assert result.no_order_authority_evidence["partial_pass_buy_submission_allowed"] is True
    assert result.no_order_authority_evidence["item_review_does_not_escalate_to_batch_failure"] is True
    assert result.no_order_authority_evidence["reviewed_buy_submitted"] is False
    assert current_pending["pending_plan_id"] == reviewed_buy.pending_plan_id
    assert current_pending["state"] == "REVIEW_REQUIRED"
    assert current_pending["approved_item_ids"] == ["buy-pass-24350"]
    assert [item["batch_submit_status"] for item in current_pending["items"]] == [
        "PASS_ITEM_SUBMITTABLE",
        "ITEM_REVIEW_REQUIRED",
    ]
    assert _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl")
    reviewed = next(item for item in result.submit_guard_item_evidence if item["symbol"] == "30410")
    assert reviewed["not_submitted_reason"] == "item_scoped_review_required"
    assert reviewed["blocked_other_items"] is False


def test_phase30_ak9r25_buy_item_scoped_review_submits_approved_buy_and_sell_with_cash_reviewed_buy(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path, max_positions=20)
    _write_current_state(runtime_root, positions=[_current_position("43760", quantity=100, price=457)])
    _write_broker_snapshot(runtime_root, symbol="43760", quantity=100, available_quantity=100)
    _write_buy_item_scoped_review_pending(
        runtime_root,
        policy_path=policy_path,
        include_approved_sell=True,
        reviewed_buy_violated_policy="reserved_cash",
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.reason == "submitted_with_reviewed_buy_items_not_submitted"
    assert result.submit_action == "SUBMIT"
    assert result.submitted_count == 2
    assert set(result.submitted_symbols) == {"24350", "43760"}
    assert result.no_order_authority_evidence["authority_type"] == "BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION"
    assert result.no_order_authority_evidence["reviewed_buy_submitted"] is False
    assert result.no_order_authority_evidence["submitted_candidate_count"] == 2
    assert current_pending["review_required_buy_item_ids"] == ["buy-review-30410"]
    reviewed = next(item for item in result.submit_guard_item_evidence if item["symbol"] == "30410")
    assert reviewed["not_submitted_reason"] == "item_scoped_review_required"
    assert reviewed["blocked_other_items"] is False


def test_phase30_ak9r25_aggregate_cash_review_remains_submit_fail_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_current_state(runtime_root, positions=[])
    _write_buy_item_scoped_review_pending(
        runtime_root,
        policy_path=policy_path,
        reviewed_buy_violated_policy="aggregate_cash",
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "BLOCKED"
    assert result.reason == "dangerous pending state blocked: REVIEW_REQUIRED"
    assert result.submitted_count == 0


def test_phase30_ak9r1_ak9r0_equivalent_eight_pass_eight_review_buy_subset_submits(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path, max_positions=20)
    _write_current_state(runtime_root, positions=[])
    _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path)
    _expand_buy_item_scoped_review_pending(
        runtime_root,
        pass_symbols=("24350", "27620", "36640", "38410", "39950", "47770", "76920", "83060"),
        review_symbols=("23880", "47840", "61980", "76470", "89180", "94320", "94340", "95010"),
    )

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    current_pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")

    assert result.status == "PASS"
    assert result.submit_action == "SUBMIT"
    assert result.submitted_count == 8
    assert result.no_order_authority_evidence["authority_type"] == "BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION"
    assert result.no_order_authority_evidence["reviewed_item_count"] == 8
    assert result.no_order_authority_evidence["submitted_candidate_count"] == 8
    assert len(current_pending["approved_buy_item_ids"]) == 8
    assert len(current_pending["review_required_buy_item_ids"]) == 8
    assert {item["symbol"] for item in current_pending["items"] if item["state"] == "CONSUMED"} == set(result.submitted_symbols)
    reviewed_evidence = [
        item
        for item in result.submit_guard_item_evidence
        if item.get("authority_type") == "BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED"
    ]
    assert len(reviewed_evidence) == 8
    assert all(item["blocked_other_items"] is False for item in reviewed_evidence)
    assert all(item["not_submitted_reason"] == "item_scoped_review_required" for item in reviewed_evidence)


def test_phase29_l21t_v_execution_accepts_buy_item_scoped_review_submit_no_submission_authority(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path, all_review=True)
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )
    _write_submit_no_submission_manifest(runtime_root, business_date="2026-07-08", submit=submit)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("no-action execution must not request broker snapshot")),
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False
    assert result.submit_action == "NO_SUBMISSION_REQUIRED"
    assert result.submit_authority_status == "PASS"
    assert result.pending_plan_present is True
    assert result.pending_item_count == 2
    assert _read_jsonl(runtime_root / "persistent_ledger" / "orders.jsonl") == []


def test_phase29_l21t_v_unscoped_buy_review_submit_remains_blocked(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy_path = _policy_path(tmp_path)
    _write_buy_item_scoped_review_pending(runtime_root, policy_path=policy_path, sell_continuation_allowed=False)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "BLOCKED"
    assert result.reason == "dangerous pending state blocked: REVIEW_REQUIRED"
    assert result.submit_action == "BLOCKED"
    assert result.submitted_count == 0


def test_phase21_b_pm_add_generates_compatibility_telemetry_only(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy = _policy(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("94320", quantity=1000, price=100)])

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="9432", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1"),),
        capital_deployment_policy=policy,
        submit_policy_context=_submit_policy_context(policy),
    )
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    order_plan_path = runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "order_plan.json"
    order_plan = _load_json(order_plan_path)
    legacy_add_order_plan_path = runtime_root / "runtime_state" / "sell_pipeline" / "2026-07-08" / "pm_add_order_plan.json"

    assert result.status == "NO_SIGNAL"
    assert result.add_consumer_status == LEGACY_ADD_MIGRATION_STATE
    assert result.add_accepted_count == 0
    assert result.add_rejected_count == 0
    assert legacy_add_order_plan_path.exists() is False
    assert pending["state"] == "EMPTY"
    assert pending["items"] == []
    assert pending.get("approval_status", "") in {"", "NO_SIGNAL"}
    evidence = pending["pm_add_consumer"]
    assert evidence["requested_count"] == 1
    assert evidence["accepted_count"] == 0
    assert evidence["accepted_pending_item_ids"] == []
    assert evidence["migration_state"] == LEGACY_ADD_MIGRATION_STATE
    assert evidence["decision_effect"] == "NONE"
    assert evidence["quantity_authority"] == "NONE"
    assert evidence["pending_authority"] == "NONE"
    assert evidence["approval_authority"] == "NONE"
    assert evidence["submit_authority"] == "NONE"
    assert evidence["telemetry_only"] is True
    assert evidence["compatibility"][0]["source_pm_decision_id"] == "pm-add-1"
    assert evidence["compatibility"][0]["legacy_path_would_have_been_invoked"] is True
    assert order_plan["pm_add_consumer"]["compatibility_count"] == 1
def test_phase21_b_pm_add_rejects_duplicate_pending_order(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    policy = _policy(tmp_path)
    _write_current_state(runtime_root, positions=[_current_position("94320", quantity=1000, price=100)])
    _write_existing_buy_pending(runtime_root, symbol="9432")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-08",
        mode="demo",
        exit_decisions=(SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-dup"),),
        capital_deployment_policy=policy,
    )

    assert result.status == "NO_SIGNAL"
    assert result.preserved_existing_buy_pending is True
    assert result.add_consumer_status == LEGACY_ADD_MIGRATION_STATE
    assert result.add_accepted_count == 0
    assert result.add_rejected_count == 0


def test_phase21_b_pm_producer_keeps_add_as_planning_candidate():
    decisions = _sell_exit_decisions_from_artifact(
        {
            "artifact_path": "pm.json",
            "decisions": [
                {
                    "decision_id": "pm-2026-07-08-9432-add",
                    "symbol": "9432",
                    "decision": "ADD",
                    "reason": "ADD is outside SELL Planning scope",
                    "confidence": 0.9,
                    "runtime_sell_quantity": 0,
                }
            ],
        }
    )

    assert len(decisions) == 1
    assert decisions[0].source_decision == "ADD"
    assert decisions[0].source_decision_id == "pm-2026-07-08-9432-add"


def test_phase27_d2c_legacy_add_duplicate_dedup_key_blocks():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision, decision),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
    )

    assert artifact["review_status"] == "REVIEW_REQUIRED"
    assert artifact["double_authority_guard"]["status"] == "BLOCKED"
    assert artifact["double_authority_guard"]["fail_open_allowed"] is False


def test_phase27_d2c_legacy_add_non_decision_does_not_conflict_with_canonical_authority():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
    )
    canonical = {
        "run_id": "run-1",
        "business_date": "2026-07-08",
        "symbol": "94320",
        "position_campaign_id": "UNKNOWN",
        "decision_id": "pm-add-1",
        "decision_effect": "BUY_ADD",
        "quantity_authority": "POSITION_SIZING",
        "pending_authority": "RUNTIME_PLANNING",
    }

    guard = evaluate_legacy_add_double_authority_guard(artifact, canonical_authority_records=(canonical,))

    assert guard["status"] == "PASS"
    assert guard["canonical_legacy_authority_overlaps"] == []


def test_phase27_d2c_legacy_add_executable_overlap_blocks():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
    )
    artifact["compatibility"][0]["decision_effect"] = "BUY_ADD"
    artifact["compatibility"][0]["quantity_authority"] = "LEGACY_ADD_CONSUMER"
    canonical = {
        "run_id": "run-1",
        "business_date": "2026-07-08",
        "symbol": "94320",
        "position_campaign_id": "UNKNOWN",
        "decision_id": "pm-add-1",
        "decision_effect": "BUY_ADD",
        "quantity_authority": "POSITION_SIZING",
        "pending_authority": "RUNTIME_PLANNING",
    }

    guard = evaluate_legacy_add_double_authority_guard(artifact, canonical_authority_records=(canonical,))

    assert guard["status"] == "BLOCKED"
    assert guard["conflict_behavior"] == "BLOCKED"
    assert guard["fail_open_allowed"] is False


def test_phase27_d2c_legacy_add_lineage_mismatches_require_review():
    decision = SellExitDecision(symbol="94320", quantity=0, reason="add", source_decision="ADD", source_decision_id="pm-add-1")
    artifact = build_legacy_add_compatibility_artifact(
        add_decisions=(decision,),
        business_date="2026-07-08",
        target_session_date="2026-07-08",
        environment="demo",
        run_id="run-1",
        accepted_generation="generation-a",
    )

    validation = validate_legacy_add_compatibility_lineage(
        artifact,
        expected_business_date="2026-07-09",
        expected_accepted_generation="generation-b",
        expected_campaign_by_symbol={"94320": "campaign-1"},
    )

    assert validation["status"] == "REVIEW_REQUIRED"
    assert validation["fail_open_allowed"] is False
    assert validation["reason_codes"] == [
        "ACCEPTED_GENERATION_MISMATCH",
        "BUSINESS_DATE_MISMATCH",
        "POSITION_CAMPAIGN_MISMATCH",
    ]
def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root)
    return root


def _write_current_state(root: Path, *, positions, as_of: str = "2026-07-08"):
    market_value = sum(float(item["market_value"]) for item in positions)
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-phase21b",
        "environment": "demo",
        "source": "fixture",
        "as_of": as_of,
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
    _write_dynamic_cash_exposure(root, business_date=as_of, cash=1_000_000, market_value=market_value)
    _write_position_sizing(root, business_date=as_of, positions=positions, cash=1_000_000, market_value=market_value)


def _current_position(symbol: str, *, quantity: float, price: float, as_of: str = "2026-07-08") -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": price,
        "market_value": quantity * price,
        "source": "fixture",
        "as_of": as_of,
    }


def _write_existing_buy_pending(root: Path, *, symbol: str):
    order_plan_path = root / "fixtures" / f"buy_order_plan_{symbol}.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": f"order-plan-buy-{symbol}"}), encoding="utf-8")
    item = PendingOrderItem(
        pending_item_id=f"opi-buy-{symbol}",
        symbol=symbol,
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=500,
        estimated_amount=50_000,
        approved=True,
        state="READY",
        policy_version="capital_deployment_v1",
        policy_source="fixture",
        evaluation_capital=1_000_000,
        target_investment_ratio=None,
        cash_buffer=None,
        max_exposure=None,
        max_positions=5,
        min_order_amount=0,
        buy_notional_policy="fixture",
        sell_liquidation_policy="fixture",
    )
    pending = promote_order_plan_to_pending(
        order_plan_id=f"order-plan-buy-{symbol}",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:fixture",
        environment="demo",
        plan_created_date="2026-07-08",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(item,),
    )
    from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link

    pending = attach_approval_link(
        pending,
        approval_path=str(root / "fixtures" / f"buy_approval_{symbol}.json"),
        approval_hash="sha256:approval",
        approval_status="APPROVED",
        approved_item_ids=(item.pending_item_id,),
        approval_expires_at="2026-07-08T15:00:00+09:00",
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _write_submit_visible_buy_pending(
    root: Path,
    *,
    policy_path: Path,
    pending_item_id: str,
    symbol: str,
    quantity: float,
    estimated_price: float,
    estimated_amount: float,
):
    policy = load_capital_deployment_policy(policy_path)
    policy_hash = capital_deployment_policy_hash(policy)
    order_plan_path = root / "fixtures" / f"submit_visible_buy_order_plan_{symbol}.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": f"order-plan-buy-{symbol}"}), encoding="utf-8")
    item = PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=estimated_price,
        estimated_amount=estimated_amount,
        approved=True,
        state="APPROVED",
        listed_info={
            "code": symbol,
            "market": "プライム",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
            "opportunity_buy_eligibility_status": "PASS",
            "opportunity_buy_eligibility": "BUY_ELIGIBLE",
            "opportunity_expected_edge_score": 0.10,
            "opportunity_expected_return": 0.10,
            "opportunity_no_buy_reason": "",
            "opportunity_buy_rank": 1,
            "opportunity_business_date": "2026-07-08",
            "opportunity_feature_date": "2026-07-08",
            "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
            "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
        },
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
        accepted_generation_id="phase29-l21t-f-fixture-generation",
        accepted_generation_business_date="2026-07-08",
        accepted_generation_binding_status="PASS",
        accepted_generation_binding={
            "schema_version": "phase26_step8_accepted_generation_binding.v1",
            "consumer": "phase29_l21t_f_submit_visible_buy_fixture",
            "mode": "demo",
            "requested_business_date": "2026-07-08",
            "selected_business_date": "2026-07-08",
            "accepted_generation_id": "phase29-l21t-f-fixture-generation",
            "accepted_generation_business_date": "2026-07-08",
            "generation_binding_status": "PASS",
            "temporal_binding_status": "PASS",
            "latest_fallback_used": False,
            "shared_state_fallback_used": False,
            "default_generation_used": False,
            "legacy_component_fallback_used": False,
            "promotion_candidate_fallback_used": False,
        },
        quantity_contract={
            "status": "PASS",
            "quantity_authority": "strategy_runtime_planning_authority",
            "quantity_status": "RESOLVED_EXECUTABLE",
            "position_count_authority": {
                "selected_dynamic_position_count": policy.max_positions,
                "target_position_count": policy.max_positions,
                "safety_hard_maximum": policy.max_positions,
            },
            "cash_exposure_authority": {
                "selected_dynamic_cash_ratio": 0.05,
                "target_cash_ratio": 0.05,
                "selected_dynamic_exposure_ratio": 0.85,
                "target_gross_exposure_ratio": 0.85,
                "exposure_safety_maximum": 0.85,
            },
            "position_sizing_authority": {
                "positions": [
                    {
                        "symbol": symbol,
                        "target_weight": 0.20,
                        "target_notional": estimated_amount,
                        "incremental_buy_notional": estimated_amount,
                        "maximum_position_weight": 1.0,
                    }
                ],
                "effective_maximum_position_weight": 1.0,
            },
        },
        sizing_policy_reason="phase29_l21t_f fixture policy evidence",
    )
    pending = promote_order_plan_to_pending(
        order_plan_id=f"order-plan-buy-{symbol}",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:phase29-l21t-f-buy-order-plan",
        environment="demo",
        plan_created_date="2026-07-08",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(item,),
        submit_policy_context=_submit_policy_context(policy),
    )
    pending = attach_approval_link(
        pending,
        approval_path=str(root / "fixtures" / f"submit_visible_buy_approval_{symbol}.json"),
        approval_hash="sha256:phase29-l21t-f-buy-approval",
        approval_status="APPROVED",
        approved_item_ids=(item.pending_item_id,),
        approval_expires_at="2026-07-08T15:00:00+09:00",
        approved_order_conditions={
            item.pending_item_id: {
                "schema_version": "runtime_v2_approved_order_condition.v1",
                "condition_authority": "strategy_planning_approval_order_conditions",
                "condition_consumer": "runtime_v2.submit.guards.run_submit_preflight",
                "pending_item_id": item.pending_item_id,
                "issue_code": item.symbol,
                "side": item.side,
                "quantity": item.quantity,
                "estimated_price": item.estimated_price,
                "estimated_amount": item.estimated_amount,
                "order_type": item.order_type,
                "price_condition": item.order_type,
                "limit_price": None,
                "target_session": "2026-07-08",
                "time_in_force": "DAY",
                "approval_runtime_path": "Production/Demo/Historical common runtime_v2",
                "legacy_approval_used": False,
                "approval_fallback_used": False,
            }
        },
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _append_submit_visible_buy_item(
    root: Path,
    *,
    pending_item_id: str,
    symbol: str,
    quantity: float,
    estimated_price: float,
    estimated_amount: float,
) -> None:
    path = root / "pending_order_plan" / "pending_order_plan.json"
    pending = _load_json(path)
    source_symbol = str(pending["items"][0].get("symbol") or "")
    template = _replace_symbol_value(dict(pending["items"][0]), old=source_symbol, new=symbol)
    template.update(
        {
            "pending_item_id": pending_item_id,
            "symbol": symbol,
            "issue_code": symbol,
            "security_code": symbol,
            "quantity": quantity,
            "estimated_price": estimated_price,
            "estimated_amount": estimated_amount,
        }
    )
    template["listed_info"] = {
        **dict(template.get("listed_info") or {}),
        "code": symbol,
        "opportunity_symbol": symbol,
    }
    pending["items"].append(template)
    pending["approved_item_ids"].append(pending_item_id)
    pending["approved_buy_item_ids"].append(pending_item_id)
    approval = dict(pending.get("approval") or {})
    approval.setdefault("approved_item_ids", list(pending["approved_item_ids"]))
    approval["approved_item_ids"] = list(pending["approved_item_ids"])
    approval_conditions = dict(approval.get("approved_order_conditions") or {})
    base_condition = dict(next(iter(approval_conditions.values()))) if approval_conditions else {}
    base_condition.update(
        {
            "pending_item_id": pending_item_id,
            "issue_code": symbol,
            "quantity": quantity,
            "estimated_price": estimated_price,
            "estimated_amount": estimated_amount,
        }
    )
    approval_conditions[pending_item_id] = base_condition
    approval["approved_order_conditions"] = approval_conditions
    pending["approval"] = approval
    pending["planning_submit_feasibility"] = pending.get("planning_submit_feasibility") or {
        "status": "PASS",
        "items": [],
    }
    pending["planning_submit_feasibility"]["items"].append(
        {
            "pending_item_id": pending_item_id,
            "side": "BUY",
            "status": "PASS",
            "reason": "planning_submit_feasibility_pass",
            "reserved_notional": estimated_amount,
        }
    )
    _write_json(path, pending)


def _replace_symbol_value(value, *, old: str, new: str):
    if isinstance(value, dict):
        return {
            key: _replace_symbol_value(new if key in {"symbol", "issue_code", "security_code", "code"} and item == old else item, old=old, new=new)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_symbol_value(item, old=old, new=new) for item in value]
    if isinstance(value, str) and value == old:
        return new
    return value


def _write_buy_item_scoped_review_pending(
    root: Path,
    *,
    policy_path: Path,
    sell_continuation_allowed: bool = True,
    all_review: bool = False,
    include_approved_sell: bool = False,
    reviewed_buy_violated_policy: str = "position_sizing",
):
    policy = load_capital_deployment_policy(policy_path)
    policy_hash = capital_deployment_policy_hash(policy)
    all_review = all_review or not sell_continuation_allowed
    order_plan_path = root / "fixtures" / "buy_item_scoped_review_order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": "order-plan-buy-item-scoped-review"}), encoding="utf-8")
    buy_pass = PendingOrderItem(
        pending_item_id="buy-pass-24350",
        symbol="24350",
        side="BUY",
        quantity=500,
        order_type="MARKET",
        estimated_price=319,
        estimated_amount=159_500,
        approved=False,
        state="REVIEW_REQUIRED",
        feasibility_status="PASS",
        batch_submit_status="BLOCKED_BY_BATCH_REVIEW",
        item_review_reason="batch_submit_blocked_by_item_scoped_review",
        listed_info={
            "code": "24350",
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
            "opportunity_business_date": "2026-07-08",
            "opportunity_feature_date": "2026-07-08",
            "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
            "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
        },
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
        accepted_generation_id="phase30-ak9r1-fixture-generation",
        accepted_generation_business_date="2026-07-08",
        accepted_generation_binding_status="PASS",
        accepted_generation_binding={
            "schema_version": "phase26_step8_accepted_generation_binding.v1",
            "consumer": "phase30_ak9r1_buy_item_scoped_review_fixture",
            "mode": "demo",
            "requested_business_date": "2026-07-08",
            "selected_business_date": "2026-07-08",
            "accepted_generation_id": "phase30-ak9r1-fixture-generation",
            "accepted_generation_business_date": "2026-07-08",
            "generation_binding_status": "PASS",
            "temporal_binding_status": "PASS",
            "latest_fallback_used": False,
            "shared_state_fallback_used": False,
            "default_generation_used": False,
            "legacy_component_fallback_used": False,
            "promotion_candidate_fallback_used": False,
        },
        quantity_contract={
            "status": "PASS",
            "quantity_authority": "strategy_runtime_planning_authority",
            "quantity_status": "RESOLVED_EXECUTABLE",
            "position_count_authority": {
                "selected_dynamic_position_count": policy.max_positions,
                "target_position_count": policy.max_positions,
                "safety_hard_maximum": policy.max_positions,
            },
            "cash_exposure_authority": {
                "selected_dynamic_cash_ratio": 0.05,
                "target_cash_ratio": 0.05,
                "selected_dynamic_exposure_ratio": 0.85,
                "target_gross_exposure_ratio": 0.85,
                "exposure_safety_maximum": 0.85,
            },
            "position_sizing_authority": {
                "positions": [
                    {
                        "symbol": "24350",
                        "target_weight": 0.20,
                        "target_notional": 159_500,
                        "incremental_buy_notional": 159_500,
                        "maximum_position_weight": 1.0,
                    }
                ],
                "effective_maximum_position_weight": 1.0,
            },
        },
    )
    buy_review = replace(
        buy_pass,
        pending_item_id="buy-review-30410",
        symbol="30410",
        quantity=100,
        estimated_price=2274,
        estimated_amount=227_400,
        feasibility_status="REVIEW_REQUIRED",
        batch_submit_status="ITEM_REVIEW_REQUIRED",
        item_review_reason="estimated amount exceeds selected_position_amount",
        listed_info={"code": "30410", "current_listed": True, "market": "プライム", "product_category": "011", "security_type": "011"},
    )
    sell_pass = replace(
        buy_pass,
        pending_item_id="sell-pass-43760",
        symbol="43760",
        side="SELL",
        quantity=100,
        estimated_price=457,
        estimated_amount=45_700,
        approved=True,
        state="APPROVED",
        feasibility_status="PASS",
        batch_submit_status="PASS_ITEM_SUBMITTABLE",
        item_review_reason="",
        listed_info={"code": "43760", "current_listed": True, "market": "プライム", "product_category": "011", "security_type": "011"},
    )
    if all_review:
        buy_pass = replace(
            buy_pass,
            approved=False,
            state="REVIEW_REQUIRED",
            feasibility_status="REVIEW_REQUIRED",
            batch_submit_status="ITEM_REVIEW_REQUIRED",
            item_review_reason="estimated amount exceeds selected_position_amount",
        )
    else:
        buy_pass = replace(
            buy_pass,
            approved=True,
            state="APPROVED",
            feasibility_status="PASS",
            batch_submit_status="PASS_ITEM_SUBMITTABLE",
            item_review_reason="",
        )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-buy-item-scoped-review",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:phase29-l21t-m-buy-review-order-plan",
        environment="demo",
        plan_created_date="2026-07-08",
        intended_submit_date="2026-07-08",
        target_session_date="2026-07-08",
        items=(buy_pass, buy_review, sell_pass) if include_approved_sell else (buy_pass, buy_review),
        submit_policy_context=_submit_policy_context(policy),
    )
    if all_review:
        approved_item_ids = ()
    elif include_approved_sell:
        approved_item_ids = ("buy-pass-24350", "sell-pass-43760")
    else:
        approved_item_ids = ("buy-pass-24350",)
    approved_order_conditions = (
        {}
        if all_review
        else {
            "buy-pass-24350": {
                "schema_version": "runtime_v2_approved_order_condition.v1",
                "condition_authority": "strategy_planning_approval_order_conditions",
                "condition_consumer": "runtime_v2.submit.guards.run_submit_preflight",
                "pending_item_id": "buy-pass-24350",
                "issue_code": "24350",
                "side": "BUY",
                "quantity": 500,
                "estimated_price": 319,
                "estimated_amount": 159_500,
                "order_type": "MARKET",
                "price_condition": "MARKET",
                "limit_price": None,
                "target_session": "2026-07-08",
                "time_in_force": "DAY",
                "approval_runtime_path": "Production/Demo/Historical common runtime_v2",
                "legacy_approval_used": False,
                "approval_fallback_used": False,
            },
            **(
                {
                    "sell-pass-43760": {
                        "schema_version": "runtime_v2_approved_order_condition.v1",
                        "condition_authority": "strategy_planning_approval_order_conditions",
                        "condition_consumer": "runtime_v2.submit.guards.run_submit_preflight",
                        "pending_item_id": "sell-pass-43760",
                        "issue_code": "43760",
                        "side": "SELL",
                        "quantity": 100,
                        "estimated_price": 457,
                        "estimated_amount": 45_700,
                        "order_type": "MARKET",
                        "price_condition": "MARKET",
                        "limit_price": None,
                        "target_session": "2026-07-08",
                        "time_in_force": "DAY",
                        "approval_runtime_path": "Production/Demo/Historical common runtime_v2",
                        "legacy_approval_used": False,
                        "approval_fallback_used": False,
                    }
                }
                if include_approved_sell
                else {}
            ),
        }
    )
    pending = replace(
        pending,
        state=PendingPlanState.REVIEW_REQUIRED,
        approval=None
        if all_review
        else PendingApprovalLink(
            approval_path=str(root / "fixtures" / "buy_item_scoped_review_approval.json"),
            approval_hash="sha256:phase30-ak9r1-buy-review-approval",
            approval_status="APPROVED",
            approved_item_ids=approved_item_ids,
            approval_expires_at="2026-07-08T15:00:00+09:00",
            policy_version=policy.policy_version,
            policy_source=policy.policy_source,
            pending_policy_hash=policy_hash,
            planning_authority_version="",
            planning_authority_source="",
            planning_authority_hash="",
            submit_policy_version=policy.policy_version,
            submit_policy_source=policy.policy_source,
            submit_policy_hash=policy_hash,
            accepted_generation_id="phase30-ak9r1-fixture-generation",
            accepted_generation_business_date="2026-07-08",
            accepted_generation_binding_status="PASS",
            accepted_generation_binding={
                "schema_version": "phase26_step8_accepted_generation_binding.v1",
                "consumer": "phase30_ak9r1_buy_item_scoped_review_fixture",
                "mode": "demo",
                "requested_business_date": "2026-07-08",
                "selected_business_date": "2026-07-08",
                "accepted_generation_id": "phase30-ak9r1-fixture-generation",
                "accepted_generation_business_date": "2026-07-08",
                "generation_binding_status": "PASS",
                "temporal_binding_status": "PASS",
                "latest_fallback_used": False,
                "shared_state_fallback_used": False,
                "default_generation_used": False,
                "legacy_component_fallback_used": False,
                "promotion_candidate_fallback_used": False,
            },
            approved_order_conditions=approved_order_conditions,
        ),
        approved_item_ids=approved_item_ids,
        buy_items_status="REVIEW_REQUIRED",
        sell_items_status="APPROVED" if include_approved_sell else "NOT_PRESENT",
        plan_overall_status="REVIEW_REQUIRED" if all_review else "APPROVED_WITH_BUY_ITEM_SCOPED_REVIEW",
        approved_buy_item_ids=() if all_review else ("buy-pass-24350",),
        approved_sell_item_ids=("sell-pass-43760",) if include_approved_sell and not all_review else (),
        review_required_buy_item_ids=("buy-pass-24350", "buy-review-30410") if all_review else ("buy-review-30410",),
        review_required_sell_item_ids=(),
        review_scope="BUY_ITEM_SCOPED_REVIEW" if sell_continuation_allowed else "AUTHORITY_UNKNOWN_REVIEW",
        review_scope_source="phase24_ht_planning_submit_feasibility_v1",
        review_scope_reason="estimated amount exceeds selected_position_amount",
        sell_continuation_allowed=sell_continuation_allowed,
        planning_submit_feasibility={
            "status": "REVIEW_REQUIRED",
            "contract_id": "phase24_ht_planning_submit_feasibility_v1",
            "reason": "estimated amount exceeds selected_position_amount",
            "items": [
                {
                    "pending_item_id": "buy-pass-24350",
                    "side": "BUY",
                    "status": "REVIEW_REQUIRED" if all_review else "PASS",
                    "reason": "estimated amount exceeds selected_position_amount" if all_review else "planning_submit_feasibility_pass",
                    "violated_policy": "position_sizing" if all_review else "",
                    "violated_policy_source": "fixture_position_sizing" if all_review else "",
                },
                {
                    "pending_item_id": "buy-review-30410",
                    "side": "BUY",
                    "status": "REVIEW_REQUIRED",
                    "reason": "estimated amount exceeds selected_position_amount",
                    "violated_policy": reviewed_buy_violated_policy,
                    "violated_policy_source": f"fixture_{reviewed_buy_violated_policy}",
                },
                *(
                    [
                        {
                            "pending_item_id": "sell-pass-43760",
                            "side": "SELL",
                            "status": "PASS",
                            "reason": "sell_exposure_reducing_submit_feasibility_not_blocked_by_buy_dynamic_exposure",
                            "violated_policy": "",
                            "violated_policy_source": "",
                        }
                    ]
                    if include_approved_sell
                    else []
                ),
            ],
        },
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _expand_buy_item_scoped_review_pending(
    root: Path,
    *,
    pass_symbols: tuple[str, ...],
    review_symbols: tuple[str, ...],
) -> None:
    path = root / "pending_order_plan" / "pending_order_plan.json"
    pending = _load_json(path)
    pass_template = next(item for item in pending["items"] if item["pending_item_id"] == "buy-pass-24350")
    review_template = next(item for item in pending["items"] if item["pending_item_id"] == "buy-review-30410")
    approved_order_condition = dict(
        pending["approval"]["approved_order_conditions"]["buy-pass-24350"]
    )
    items = []
    approved_ids = []
    review_ids = []
    feasibility_items = []
    approved_conditions = {}
    for index, symbol in enumerate(pass_symbols, start=1):
        item_id = f"buy-pass-{symbol}"
        quantity = 100
        price = 10 + index
        amount = quantity * price
        item = _replace_symbol_value(dict(pass_template), old="24350", new=symbol)
        item.update(
            {
                "pending_item_id": item_id,
                "quantity": quantity,
                "estimated_price": price,
                "estimated_amount": amount,
                "state": "APPROVED",
                "approved": True,
                "feasibility_status": "PASS",
                "batch_submit_status": "PASS_ITEM_SUBMITTABLE",
                "item_review_reason": "",
            }
        )
        items.append(item)
        approved_ids.append(item_id)
        condition = _replace_symbol_value(dict(approved_order_condition), old="24350", new=symbol)
        condition.update(
            {
                "pending_item_id": item_id,
                "quantity": quantity,
                "estimated_price": price,
                "estimated_amount": amount,
            }
        )
        approved_conditions[item_id] = condition
        feasibility_items.append(
            {
                "pending_item_id": item_id,
                "side": "BUY",
                "status": "PASS",
                "reason": "planning_submit_feasibility_pass",
                "violated_policy": "",
                "violated_policy_source": "",
            }
        )
    for index, symbol in enumerate(review_symbols, start=1):
        item_id = f"buy-review-{symbol}"
        quantity = 100 * index
        price = 200 + index
        amount = quantity * price
        item = _replace_symbol_value(dict(review_template), old="30410", new=symbol)
        item.update(
            {
                "pending_item_id": item_id,
                "quantity": quantity,
                "estimated_price": price,
                "estimated_amount": amount,
                "state": "REVIEW_REQUIRED",
                "approved": False,
                "feasibility_status": "REVIEW_REQUIRED",
                "batch_submit_status": "ITEM_REVIEW_REQUIRED",
                "item_review_reason": "estimated amount exceeds selected_position_amount",
            }
        )
        items.append(item)
        review_ids.append(item_id)
        feasibility_items.append(
            {
                "pending_item_id": item_id,
                "side": "BUY",
                "status": "REVIEW_REQUIRED",
                "reason": "estimated amount exceeds selected_position_amount",
                "violated_policy": "position_sizing",
                "violated_policy_source": "fixture_position_sizing",
            }
        )
    pending["items"] = items
    pending["approved_item_ids"] = approved_ids
    pending["approved_buy_item_ids"] = approved_ids
    pending["review_required_buy_item_ids"] = review_ids
    pending["approval"]["approved_item_ids"] = approved_ids
    pending["approval"]["approved_order_conditions"] = approved_conditions
    pending["planning_submit_feasibility"]["items"] = feasibility_items
    _write_json(path, pending)


def _policy(tmp_path: Path):
    return load_capital_deployment_policy(_policy_path(tmp_path))


def _policy_path(tmp_path: Path, *, max_buy_order_amount=None, max_positions: int = 5) -> Path:
    path = tmp_path / "capital_deployment_policy.json"
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": max_positions,
            "min_order_amount": 0,
            "max_buy_order_amount": max_buy_order_amount,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _write_position_sizing(root: Path, *, business_date: str, positions, cash: float, market_value: float) -> None:
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
                "target_weight_authority": {
                    "portfolio_policy_reference": {
                        "path": "fixture_portfolio_policy",
                    }
                },
            }
        )
    total_target_weight = round(sum(float(row["target_weight"]) for row in rows), 6)
    payload = {
        "schema_version": "position_sizing.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": business_date,
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "PASS",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "target_gross_exposure_ratio": 0.80,
        "target_position_count": len(rows),
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
        "dynamic_position_count": len(rows),
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
    }
    _write_json(
        root / "strategy_artifacts" / "position_sizing" / business_date / "position_sizing.json",
        payload,
    )


def _write_dynamic_cash_exposure(root: Path, *, business_date: str, cash: float, market_value: float) -> None:
    total_equity = cash + market_value
    target_cash_ratio = 0.20
    target_exposure_ratio = 0.80
    payload = {
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
            "previous_day_dynamic_cash_exposure_copied": False
        },
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "lot_rounding_decided": False
    }
    _write_json(
        root / "strategy_artifacts" / "dynamic_cash_exposure" / business_date / "dynamic_cash_exposure.json",
        payload,
    )


def _submit_policy_context(policy) -> dict:
    return {
        "submit_policy_authority": "capital_deployment_policy",
        "submit_policy_schema_version": "phase23_bb_submit_policy_authority.v1",
        "submit_policy_version": policy.policy_version,
        "submit_policy_source": policy.policy_source,
        "submit_policy_hash": capital_deployment_policy_hash(policy),
    }


def _write_strategy_no_order_authority(root: Path, *, business_date: str) -> None:
    strategy_dir = root / "runtime_state" / "strategy_planning" / business_date
    order_plan = {
        "schema_version": "phase23_i_strategy_authority_order_plan.v1",
        "order_plan_id": f"strategy-plan-demo-{business_date}-no-order",
        "environment": "demo",
        "business_date": business_date,
        "target_session_date": business_date,
        "status": "NO_ORDER_AUTHORIZED",
        "planning_consumer_eligibility": "NO_ORDER_AUTHORIZED",
        "planning_authority": "phase22_strategy_runtime_planning",
        "strategy_artifact_path": str(root / "strategy" / business_date / "runtime_planning.json"),
        "position_sizing_artifact_path": str(root / "strategy" / business_date / "position_sizing.json"),
        "items": [],
        "strategy_item_lineage": [
            {
                "planning_id": f"rp-{business_date}-94320-no-action",
                "security_code": "94320",
                "planning_intent": "NO_ACTION",
                "order_side_intent": "NONE",
                "pending_item_generated": False,
                "reason": "no_action_strategy_intent",
            }
        ],
        "broker_write_allowed": False,
        "broker_write_performed": False,
        "production_decision_allowed": False,
        "silent_fallback_used": False,
        "latest_fallback_used": False,
        "future_information_used": False,
    }
    _write_json(strategy_dir / "order_plan.json", order_plan)
    _write_json(
        strategy_dir / "approval_artifact.json",
        {
            "schema_version": "phase23_ab_no_order_authorized_approval.v1",
            "status": "NO_ORDER_AUTHORIZED",
            "reason": "strategy_planning_no_order_authorized",
            "business_date": business_date,
            "target_session_date": business_date,
            "pending_item_count": 0,
            "order_plan_id": order_plan["order_plan_id"],
            "order_plan_hash": hashlib.sha256((strategy_dir / "order_plan.json").read_bytes()).hexdigest(),
        },
    )


def _demo_settings() -> BrokerSettings:
    return BrokerSettings(
        environment="demo",
        base_url="https://demo-kabuka.e-shiten.jp/e_api_v4r9",
        second_password_file="/tmp/phase21b-second-password",
    )


def _write_broker_snapshot(root: Path, *, symbol: str, quantity: float, available_quantity: float) -> None:
    _write_broker_snapshots(
        root,
        records=[{"symbol": symbol, "quantity": quantity, "available_quantity": available_quantity}],
    )


def _write_broker_snapshots(root: Path, *, records: list[dict]) -> None:
    path = root / "broker" / "snapshots" / "positions" / "positions_20260708.json"
    rows = []
    for record in records:
        symbol = str(record["symbol"])
        quantity = float(record["quantity"])
        available_quantity = float(record["available_quantity"])
        rows.extend(
            [
                {
                    "issue_code": symbol,
                    "quantity": quantity,
                    "available_quantity": available_quantity,
                    "account_type": "specific",
                    "production_equivalent": True,
                },
                {
                    "issue_code": symbol[:4],
                    "quantity": quantity,
                    "available_quantity": available_quantity,
                    "account_type": "specific",
                    "production_equivalent": True,
                },
            ]
        )
    _write_json(
        path,
        {
            "source": "broker_readonly",
            "as_of": "2026-07-08T08:50:00+09:00",
            "production_equivalent": True,
            "records": rows,
        },
    )


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase21b-fixture",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": str(path),
            "business_date": "2026-07-08",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase21b fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-08T08:00:00+09:00",
            "expires_at": "2026-07-08T15:00:00+09:00",
        },
    )
    return path


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_submit_no_submission_manifest(root: Path, *, business_date: str, submit) -> None:
    _write_json(
        root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-l21t-v.json",
        {
            "run_id": "runtime-v2-submit-l21t-v",
            "job": "submit",
            "business_date": business_date,
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            "pending_read_valid": submit.pending_read_valid,
            "pending_classification": submit.pending_classification,
            "pending_active": submit.pending_active,
            "pending_plan_present": submit.pending_plan_present,
            "pending_item_count": submit.pending_item_count,
            "no_action_reason": submit.no_action_reason,
            "no_order_authority_status": submit.no_order_authority_status,
            "no_order_authority_evidence": submit.no_order_authority_evidence,
            "submit_action": submit.submit_action,
            "submitted_count": submit.submitted_count,
            "blocked_count": submit.blocked_count,
            "review_required": submit.review_required,
            "halt_required": submit.halt_required,
            "prohibited_actions": {"demo_submit_executed": False, "production_order_executed": False},
        },
    )


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
