import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    capital_deployment_policy_hash,
    load_capital_deployment_policy,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import load_runtime_current_exposure
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings


def test_phase24_ht_planning_exposure_pass_allows_approved_pending(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=400_000, positions=[_position("1111", 100, 1000)])
    pending = _pending((_item("buy-1", amount=100_000),), policy=policy)
    approval = _approval(pending)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.APPROVED
    assert linked.approved_item_ids == ("buy-1",)
    assert linked.planning_submit_feasibility["status"] == "PASS"


def test_phase24_ht_planning_exposure_fail_blocks_approved_pending(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=265_230, positions=[_position("1111", 1, 685_510)])
    pending = _pending((_item("buy-1", amount=166_400),), policy=policy)
    approval = _approval(pending)

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.approved_item_ids == ()
    assert linked.items[0].approved is False
    assert linked.planning_submit_feasibility["status"] == "REVIEW_REQUIRED"
    assert linked.planning_submit_feasibility["items"][0]["violated_policy"] == "dynamic_exposure"
    assert linked.planning_submit_feasibility["items"][0]["remaining_exposure"] == 122_619
    assert linked.planning_submit_feasibility["items"][0]["active_deployment_capital"] == 950_740
    assert linked.planning_submit_feasibility["items"][0]["selected_runtime_exposure_limit"] == 808_129
    assert linked.planning_submit_feasibility["items"][0]["legacy_exposure_config_used"] is False
    assert linked.planning_submit_feasibility["items"][0]["cash_exposure_fallback_used"] is False
    assert linked.planning_submit_feasibility["items"][0]["legacy_capital_config_used"] is False
    assert linked.review_scope == "BUY_ITEM_SCOPED_REVIEW"
    assert linked.sell_continuation_allowed is True
    assert linked.approved_buy_item_ids == ()
    assert linked.review_required_buy_item_ids == ("buy-1",)


def test_phase24_id_planning_aggregate_cash_reservation_blocks_later_buy(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=250_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item("buy-1", amount=60_000, symbol="7203"),
            _item("buy-2", amount=60_000, symbol="6758"),
            _item("buy-3", amount=150_000, symbol="9984"),
        ),
        policy=policy,
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.planning_submit_feasibility["reservation_contract"] == "phase24_id_aggregate_pending_batch_reservation_v1"
    assert linked.planning_submit_feasibility["items"][0]["status"] == "PASS"
    assert linked.planning_submit_feasibility["items"][0]["post_buy_cash"] == 190_000
    assert linked.planning_submit_feasibility["items"][1]["status"] == "PASS"
    assert linked.planning_submit_feasibility["items"][2]["status"] == "REVIEW_REQUIRED"
    assert linked.planning_submit_feasibility["items"][2]["cash"] == 130_000
    assert linked.planning_submit_feasibility["items"][2]["violated_policy"] == "cash"
    assert linked.approved_item_ids == ()
    assert linked.approved_buy_item_ids == ()
    assert linked.review_required_buy_item_ids == ("buy-3",)
    assert linked.items[0].approved is False
    assert linked.items[0].feasibility_status == "PASS"
    assert linked.items[0].batch_submit_status == "BLOCKED_BY_BATCH_REVIEW"
    assert linked.items[0].item_review_reason == "batch_submit_blocked_by_item_scoped_review"
    assert linked.items[1].approved is False
    assert linked.items[1].feasibility_status == "PASS"
    assert linked.items[1].batch_submit_status == "BLOCKED_BY_BATCH_REVIEW"
    assert linked.items[2].approved is False
    assert linked.items[2].feasibility_status == "REVIEW_REQUIRED"
    assert linked.items[2].batch_submit_status == "ITEM_REVIEW_REQUIRED"


def test_phase24_id_submit_aggregate_preflight_blocks_before_adapter_boundary(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=900_000, positions=[_position("1111", 100, 1000)])
    pending = _pending(
        (
            _item("buy-1", amount=175_000, symbol="7203"),
            _item("buy-2", amount=175_000, symbol="6758"),
            _item("buy-3", amount=175_000, symbol="9984"),
        ),
        policy=policy,
    )
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    assert pending.state == PendingPlanState.APPROVED
    _write_current(root, cash=100_000, positions=[_position("1111", 100, 9000)])
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert result.reason == "submit blocked before broker boundary; manual review required"
    blocked = [item for item in result.submit_guard_item_evidence if item["guard_decision"] == "BLOCKED"]
    assert blocked
    assert {item["violated_policy"] for item in blocked} == {"cash"}


def test_phase24_ht_planning_pass_then_submit_guard_passes(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _pending((_item("buy-1", amount=100_000),), policy=policy)
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submit_guard_item_evidence[0]["guard_decision"] == "BLOCKED"
    assert result.submit_guard_item_evidence[0]["violated_policy"] == "accepted_generation_binding"


def test_phase24_ht_submit_guard_revalidates_after_planning_pass(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    pending = _pending((_item("buy-1", amount=100_000),), policy=policy)
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    assert pending.planning_submit_feasibility["status"] == "PASS"
    _write_current(root, cash=300_000, positions=[_position("1111", 1, 1_600_000)])
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submit_guard_item_evidence[0]["guard_decision"] == "BLOCKED"
    assert result.submit_guard_item_evidence[0]["violated_policy"] == "dynamic_exposure"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "persistent_ledger").mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety(root)
    return root


def _pending(items: tuple[PendingOrderItem, ...], *, policy) -> object:
    items = tuple(
        item.__class__(
            **{
                **item.__dict__,
                "policy_version": policy.policy_version,
                "policy_source": policy.policy_source,
                "submit_policy_version": policy.policy_version,
                "submit_policy_source": policy.policy_source,
                "submit_policy_hash": capital_deployment_policy_hash(policy),
                "evaluation_capital": policy.evaluation_capital,
                "target_investment_ratio": None,
                "cash_buffer": None,
                "max_exposure": None,
                "max_positions": policy.max_positions,
                "buy_notional_policy": policy.buy_notional_policy,
                "sell_liquidation_policy": policy.sell_liquidation_policy,
            }
        )
        for item in items
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase24-ht",
        source_order_plan_path=".runtime/runtime_state/morning/order_plan.json",
        source_order_plan_hash="sha256:phase24-ht-order-plan",
        environment="demo",
        plan_created_date="2026-07-09",
        intended_submit_date="2026-07-09",
        target_session_date="2026-07-09",
        items=items,
    )
    return pending.__class__(
        **{
            **pending.__dict__,
            "policy_context": {
                "policy_version": policy.policy_version,
                "policy_source": policy.policy_source,
                "target_position_count": 8,
                "selected_dynamic_position_count": 8,
                "safety_hard_maximum": None,
                "legacy_position_count_config_used": False,
                "position_count_fallback_used": False,
                "target_cash_ratio": 0.10,
                "target_gross_exposure_ratio": 0.85,
                "maximum_gross_exposure_ratio": 0.90,
                "legacy_cash_config_used": False,
                "legacy_exposure_config_used": False,
                "cash_exposure_fallback_used": False,
            },
        }
    )


def _approval(pending) -> ApprovalArtifact:
    return ApprovalArtifact(
        approval_id="approval-phase24-ht",
        approval_request_id="approval-request-phase24-ht",
        pending_plan_id=pending.pending_plan_id,
        order_plan_id=pending.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=tuple(item.pending_item_id for item in pending.items),
        rejected_item_ids=(),
        approval_hash="sha256:approval-phase24-ht",
        approved_at="2026-07-09T08:45:00+09:00",
        expires_at="2026-07-09T15:00:00+09:00",
        review_required=False,
        reason="phase24 ht approval",
        submit_policy_version=pending.submit_policy_version,
        submit_policy_source=pending.submit_policy_source,
        submit_policy_hash=pending.submit_policy_hash,
        approved_order_conditions={
            item.pending_item_id: {
                "order_type": item.order_type,
                "target_session": pending.target_session_date,
                "quantity": item.quantity,
                "side": item.side,
                "issue_code": item.symbol,
                "price_condition": "MARKET" if item.order_type == "MARKET" else "LIMIT",
                "limit_price": None if item.order_type == "MARKET" else item.estimated_price,
                "time_in_force": "DAY",
            }
            for item in pending.items
        },
    )


def _item(pending_item_id: str, *, amount: float, symbol: str = "7203") -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=amount / 100,
        estimated_amount=amount,
        approved=False,
        state="PENDING_APPROVAL",
        listed_info={
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
            "opportunity_business_date": "2026-07-09",
            "opportunity_feature_date": "2026-07-09",
            "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
            "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
        },
        quantity_contract=_quantity_contract(symbol=symbol, amount=amount),
    )


def _position(symbol: str, quantity: float, price: float) -> dict:
    return {"symbol": symbol, "quantity": quantity, "market_value": quantity * price, "average_price": price}


def _write_current(root: Path, *, cash: float, positions: list[dict]) -> None:
    market_value = sum(float(position["market_value"]) for position in positions)
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase24-ht",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "positions": positions,
            "cash": cash,
            "buying_power": cash,
            "market_value": market_value,
            "total_equity": cash + market_value,
        },
    )


def _write_policy(path: Path) -> Path:
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


def _write_safety(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": "safety-phase24-ht",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": "phase24_ht_fixture",
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase24 ht safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
        },
    )


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _quantity_contract(*, symbol: str, amount: float) -> dict:
    return {
        "quantity_contract_version": "phase26_step4_test_quantity_contract",
        "target_position_count": 8,
        "selected_dynamic_position_count": 8,
        "safety_hard_maximum": None,
        "legacy_position_count_config_used": False,
        "position_count_fallback_used": False,
        "target_cash_ratio": 0.10,
        "target_gross_exposure_ratio": 0.85,
        "maximum_gross_exposure_ratio": 0.90,
        "legacy_cash_config_used": False,
        "legacy_exposure_config_used": False,
        "cash_exposure_fallback_used": False,
        "position_sizing_authority": {
            "symbol": symbol,
            "selected_position_amount": amount,
            "remaining_add_capacity": amount,
            "selected_position_weight": 0.18,
            "target_weight": 0.18,
            "target_notional": amount,
            "incremental_buy_notional": amount,
            "maximum_position_weight": 0.18,
            "portfolio_policy_source": "phase24_ht_fixture_portfolio_policy",
        },
    }
