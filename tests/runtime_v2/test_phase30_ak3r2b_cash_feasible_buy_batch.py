from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalDecision, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.approval.policy import build_approval_artifact, build_approval_request
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import _cash_feasible_buy_batch
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import RuntimeCurrentExposure
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import CapitalDeploymentPolicy, ManualReviewThreshold


BUSINESS_DATE = "2026-07-15"


def test_phase30_ak3r2b_all_fit_keeps_all_buy_items() -> None:
    items = (_item("A", 100_000), _item("B", 150_000), _item("C", 200_000))

    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=500_000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert [item.symbol for item in active] == ["A", "B", "C"]
    assert evidence["included_buy_count"] == 3
    assert evidence["cash_pruned_count"] == 0
    assert evidence["final_reserved_notional_total"] == 450_000
    assert evidence["remaining_reserved_cash"] == 50_000


def test_phase30_ak3r2b_prunes_one_cash_infeasible_item_and_continues() -> None:
    items = (_item("A", 200_000), _item("B", 400_000), _item("C", 100_000))

    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=350_000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert [item.symbol for item in active] == ["A", "C"]
    assert [row["decision"] for row in evidence["items"]] == ["INCLUDE", "PRUNE", "INCLUDE"]
    assert evidence["items"][1]["symbol"] == "B"
    assert evidence["items"][1]["reason"] == "DEFERRED_INSUFFICIENT_RESERVED_CASH"
    assert evidence["cash_pruned_count"] == 1
    assert evidence["priority_order_preservation"] == "PASS"
    assert evidence["selection_semantic"] == "PRIORITY_ORDERED_RESERVED_NOTIONAL_SKIP_AND_CONTINUE_PRUNING"
    assert evidence["new_investment_priority_created"] is False
    assert evidence["new_batch_optimization_created"] is False


def test_phase30_ak3r2b_exact_cash_boundary_passes() -> None:
    items = (_item("A", 200_000), _item("B", 150_000))

    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=350_000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert [item.symbol for item in active] == ["A", "B"]
    assert evidence["remaining_reserved_cash"] == 0
    assert evidence["cash_pruned_count"] == 0


def test_phase30_ak3r2b_non_cash_authority_failure_stays_fail_closed() -> None:
    items = (_item("A", 100_000), _item("B", 100_000, selected_position_amount=50_000), _item("C", 100_000))

    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=_current(cash=500_000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert [item.symbol for item in active] == ["A", "B", "C"]
    assert evidence["items"][1]["decision"] == "INCLUDE_REVIEW_REQUIRED"
    assert evidence["items"][1]["source_violated_policy"] == "position_sizing"
    assert evidence["cash_pruned_count"] == 0


def test_phase30_ak3r2b_ak2_one_lot_uses_normal_cash_priority() -> None:
    normal = _item("A", 100_000)
    one_lot = _item("B", 227_400, one_lot=True)

    active, evidence = _cash_feasible_buy_batch(
        items=(normal, one_lot),
        current=_current(cash=350_000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert [item.symbol for item in active] == ["A", "B"]
    assert evidence["ak2_one_lot_cash_priority_special_case_required"] is False
    assert evidence["items"][1]["decision"] == "INCLUDE"


def test_phase30_ak3r2b_ak2_one_lot_cash_shortfall_prunes_without_special_case() -> None:
    normal = _item("A", 100_000)
    one_lot = _item("B", 227_400, one_lot=True)

    active, evidence = _cash_feasible_buy_batch(
        items=(normal, one_lot),
        current=_current(cash=200_000),
        policy=_policy(),
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert [item.symbol for item in active] == ["A"]
    assert evidence["items"][1]["decision"] == "PRUNE"
    assert evidence["items"][1]["reason"] == "DEFERRED_INSUFFICIENT_RESERVED_CASH"
    assert evidence["ak2_one_lot_cash_priority_special_case_required"] is False


def test_phase30_ak3r2b_submit_final_verification_still_runs_on_pruned_batch(tmp_path: Path) -> None:
    items = (_item("A", 200_000), _item("B", 400_000), _item("C", 100_000))
    current = _current(cash=350_000)
    policy = _policy()

    active, evidence = _cash_feasible_buy_batch(
        items=items,
        current=current,
        policy=policy,
        business_date=BUSINESS_DATE,
        mode="historical",
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="phase30-ak3r2b-plan",
        source_order_plan_path=str(tmp_path / "order_plan.json"),
        source_order_plan_hash="sha256:test",
        environment="historical",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=active,
    )
    approval = build_approval_artifact(
        request=build_approval_request(
            pending_plan=pending,
            business_date=BUSINESS_DATE,
            expires_at=f"{BUSINESS_DATE}T15:00:00+09:00",
        ),
        decision=ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approved_item_ids=tuple(item.pending_item_id for item in active),
            rejected_item_ids=(),
            reason="phase30_ak3r2b_test_approval",
            operator="pytest",
            decided_at=f"{BUSINESS_DATE}T08:45:00+09:00",
        ),
    )

    linked = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=approval,
        planning_submit_feasibility_current=current,
        planning_submit_feasibility_policy=policy,
    )

    assert [item.symbol for item in active] == ["A", "C"]
    assert evidence["cash_pruned_valid_batch_can_submit"] is True
    assert linked.state == PendingPlanState.APPROVED
    assert linked.planning_submit_feasibility["status"] == "PASS"
    assert [row["symbol"] for row in linked.planning_submit_feasibility["items"]] == ["A", "C"]


def _item(
    symbol: str,
    reserved_notional: float,
    *,
    selected_position_amount: float | None = None,
    one_lot: bool = False,
) -> PendingOrderItem:
    quantity = 100.0
    price = round(reserved_notional / quantity, 6)
    selected_amount = float(selected_position_amount if selected_position_amount is not None else reserved_notional)
    quantity_contract = {
        "selected_notional": reserved_notional,
        "selected_quantity": quantity,
        "planned_quantity": quantity,
        "planning_intent": "BUY_NEW",
        "position_count_authority": {
            "selected_dynamic_position_count": 10,
            "safety_hard_maximum": 10,
        },
        "cash_exposure_authority": {
            "selected_dynamic_cash_ratio": 0.0,
            "selected_dynamic_exposure_ratio": 1.0,
            "maximum_gross_exposure_ratio": 1.0,
        },
        "position_sizing_authority": {
            "schema_version": "position_sizing.v1",
            "business_date": BUSINESS_DATE,
            "positions": [
                {
                    "security_code": symbol,
                    "target_notional": selected_amount,
                    "incremental_buy_notional": selected_amount,
                    "selected_position_amount": selected_amount,
                    "remaining_add_capacity": selected_amount,
                    "target_weight": 0.10,
                    "selected_position_weight": 0.10,
                    "maximum_position_weight": 0.25,
                    "quantity_delta_candidate": quantity,
                    "target_quantity_candidate": quantity,
                    "quantity_status": "RESOLVED_EXECUTABLE",
                    "phase29_l19_lot_resolution": {},
                }
            ],
        },
    }
    if one_lot:
        one_lot_authority = {
            "boundary_classification": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
            "semantic_type": "BUY_NEW",
            "minimum_executable_one_lot_authority": {
                "authority_type": "PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION",
                "decision": "ADMIT",
                "reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
                "symbol": symbol,
                "intent": "BUY_NEW",
            },
            "one_lot_quantity": quantity,
            "one_lot_notional": reserved_notional,
            "final_allocated_quantity": quantity,
            "safety_hard_cap_preserved": True,
            "strategy_cap_preserved": True,
        }
        quantity_contract["position_sizing_authority"]["positions"][0].update(
            {
                "discrete_authorized_quantity": quantity,
                "discrete_authorized_notional": reserved_notional,
                "one_lot_authority_consumed": True,
                "one_lot_authority_reason": "MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED",
                "phase29_l19_lot_resolution": one_lot_authority,
            }
        )
    return PendingOrderItem(
        pending_item_id=f"buy-{symbol}",
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        order_type="MARKET",
        estimated_price=price,
        estimated_amount=reserved_notional,
        approved=False,
        state="CREATED",
        reference_price=price,
        reservation_price=price,
        reservation_price_type="test_canonical_reserved_notional",
        reservation_price_authority={
            "authority_type": "ORDER_CONDITION_DERIVED_RESERVATION_PRICE_AUTHORITY",
            "authority_status": "PASS",
            "future_execution_price_used": False,
            "target_day_ohlc_used": False,
        },
        reservation_reason="reservation_price_authority_resolved",
        reserved_notional=reserved_notional,
        quantity_contract=quantity_contract,
        source_decision_type="BUY_NEW",
        source_position_symbol=symbol,
    )


def _current(*, cash: float) -> RuntimeCurrentExposure:
    return RuntimeCurrentExposure(
        cash=cash,
        buying_power=cash,
        current_exposure=0.0,
        current_total_equity=cash,
        active_deployment_capital=cash,
        selected_capital_source="test_current_total_equity",
        capital_fallback_used=False,
        initial_or_bootstrap_capital=cash,
        positions={},
        position_market_values={},
        current_position_source="test_current",
    )


def _policy() -> CapitalDeploymentPolicy:
    return CapitalDeploymentPolicy(
        policy_version="capital_deployment_v1",
        policy_source="phase30_ak3r2b_test_policy",
        evaluation_capital=1_000_000,
        max_positions=10,
        min_order_amount=0.0,
        max_buy_order_amount=None,
        max_sell_liquidation_amount=None,
        buy_notional_policy="derived_from_capital_allocation_and_constraints",
        sell_liquidation_policy="current_owned_available_quantity_policy",
        manual_review_threshold=ManualReviewThreshold(buy_amount=None, sell_liquidation_amount=None),
        loaded_from="phase30_ak3r2b_test_policy",
    )
