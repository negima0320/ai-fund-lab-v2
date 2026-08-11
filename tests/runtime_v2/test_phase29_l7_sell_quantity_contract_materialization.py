from __future__ import annotations

from dataclasses import replace

from ai_fund_lab_v2.runtime_v2.pending.composition import reconcile_with_existing_sell_pending
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem
from ai_fund_lab_v2.runtime_v2.pending.promotion import promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal, CapitalAllocationSignal, PlanningDecisionStatus
from ai_fund_lab_v2.runtime_v2.planning.planner import (
    SELL_ITEM_QUANTITY_CONTRACT_MISMATCH,
    SELL_ITEM_QUANTITY_CONTRACT_MISSING,
    _validate_sell_quantity_contract,
    build_order_plan,
)
from tests.runtime_v2.planning_fixtures import (
    make_allocation,
    make_asset_state,
    make_planning_input,
    make_position,
)
from tests.runtime_v2.test_phase28_d3_sell_pending_reconciliation import (
    BUSINESS_DATE,
    _pending_item,
    _runtime_root,
    _write_existing_pending,
)


def test_phase29_l7_reduce_final_sell_quantity_survives_order_plan_materialization() -> None:
    result = build_order_plan(
        _sell_input(
            symbol="76920",
            owned_quantity=2000,
            source_decision="REDUCE",
            final_sell_quantity=1000,
            allocated_amount=137800.0,
            estimated_price=137.8,
            signal_id="sell-reduce-pm-76920-001",
        )
    )

    item = result.order_plan.items[0]
    assert result.status == PlanningDecisionStatus.CREATED
    assert item.quantity == 1000.0
    assert item.quantity_contract["final_sell_quantity"] == 1000.0


def test_phase29_l7_exit_final_sell_quantity_survives_order_plan_materialization() -> None:
    result = build_order_plan(
        _sell_input(
            symbol="59550",
            owned_quantity=700,
            source_decision="EXIT",
            final_sell_quantity=700,
            allocated_amount=62999.0,
            estimated_price=90.0,
            signal_id="sell-exit-pm-59550-001",
        )
    )

    item = result.order_plan.items[0]
    assert result.status == PlanningDecisionStatus.CREATED
    assert item.quantity == 700.0
    assert item.quantity_contract["source_decision"] == "EXIT"


def test_phase29_l7_notional_price_disagreement_does_not_override_formal_sell_quantity() -> None:
    result = build_order_plan(
        _sell_input(
            symbol="76920",
            owned_quantity=2000,
            source_decision="REDUCE",
            final_sell_quantity=1000,
            allocated_amount=137800.0,
            estimated_price=137.8,
            signal_id="sell-reduce-pm-76920-001",
        )
    )

    item = result.order_plan.items[0]
    assert item.estimated_amount == 137800.0
    assert item.estimated_price == 137.8
    assert item.quantity == 1000.0


def test_phase29_l7_sell_item_quantity_contract_mismatch_fail_closes() -> None:
    allocation = _sell_allocation(
        symbol="76920",
        source_decision="REDUCE",
        final_sell_quantity=1000,
        allocated_amount=137800.0,
        estimated_price=137.8,
    )

    reason = _validate_sell_quantity_contract(
        signal_side="SELL",
        signal_id="sell-reduce-pm-76920-001",
        allocation=allocation,
        materialized_quantity=900.0,
    )

    assert reason == SELL_ITEM_QUANTITY_CONTRACT_MISMATCH


def test_phase29_l7_required_sell_quantity_contract_missing_blocks_reduce() -> None:
    allocation = _sell_allocation(
        symbol="76920",
        source_decision="REDUCE",
        final_sell_quantity=1000,
        allocated_amount=137800.0,
        estimated_price=137.8,
    )
    allocation = replace(allocation, quantity_contract={"source_decision": "REDUCE"})
    result = build_order_plan(
        _sell_input(
            symbol="76920",
            owned_quantity=2000,
            source_decision="REDUCE",
            final_sell_quantity=1000,
            allocated_amount=137800.0,
            estimated_price=137.8,
            signal_id="sell-reduce-pm-76920-001",
            allocation=allocation,
        )
    )

    assert result.status == PlanningDecisionStatus.BLOCKED
    assert SELL_ITEM_QUANTITY_CONTRACT_MISSING in result.order_plan.items[0].reason


def test_phase29_l7_buy_quantity_behavior_is_unchanged() -> None:
    result = build_order_plan(
        make_planning_input(
            asset_state=make_asset_state(cash=300000.0, buying_power=300000.0),
            capital_allocations=(make_allocation(cash_required=250000.0),),
        )
    )

    item = result.order_plan.items[0]
    assert item.side == "BUY"
    assert item.quantity == 100.0
    assert item.quantity_contract is None


def test_phase29_l7_sell_more_than_owned_protection_is_preserved() -> None:
    result = build_order_plan(
        _sell_input(
            symbol="76920",
            owned_quantity=900,
            source_decision="REDUCE",
            final_sell_quantity=1000,
            allocated_amount=137800.0,
            estimated_price=137.8,
            signal_id="sell-reduce-pm-76920-001",
        )
    )

    assert result.status == PlanningDecisionStatus.BLOCKED
    assert "sell quantity exceeds current position" in result.order_plan.items[0].reason


def test_phase29_l7_same_quantity_pending_reconciliation_preserves_existing(tmp_path) -> None:
    runtime_root = _runtime_root(tmp_path)
    existing_plan = _write_existing_pending(
        runtime_root,
        items=(_sell_pending_item("opi-existing-reduce-76920", "76920", 1000, source_decision_type="REDUCE"),),
    )
    new_item = _sell_pending_item("opi-sell-reduce-pm-76920-001", "76920", 1000, source_decision_type="REDUCE")
    pending = _new_pending_plan(runtime_root, new_item)

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE,
    )

    assert result.status == "PASS"
    assert result.pending.items[0].pending_item_id == existing_plan.items[0].pending_item_id
    assert result.evidence["reason_codes"] == ["PENDING_SELL_COMPATIBLE_UPDATE_MERGED"]


def test_phase29_l7_genuine_different_quantity_conflict_remains_review_required(tmp_path) -> None:
    runtime_root = _runtime_root(tmp_path)
    existing_plan = _write_existing_pending(
        runtime_root,
        items=(_sell_pending_item("opi-existing-reduce-76920", "76920", 1000, source_decision_type="REDUCE"),),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    new_item = _sell_pending_item("opi-sell-reduce-pm-76920-001", "76920", 800, source_decision_type="REDUCE")
    pending = _new_pending_plan(runtime_root, new_item)

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert existing_plan.pending_plan_id in before
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before
    assert "PENDING_SELL_CONFLICTING_QUANTITY_REVIEW" in result.evidence["reason_codes"]


def test_phase29_l7_reduce_to_exit_and_exit_to_reduce_d3_priority_preserved(tmp_path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_existing_pending(
        runtime_root,
        items=(_sell_pending_item("opi-existing-reduce-76920", "76920", 1000, source_decision_type="REDUCE"),),
    )

    reduce_to_exit = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=_new_pending_plan(
            runtime_root,
            _sell_pending_item("opi-sell-exit-pm-76920-001", "76920", 2000, source_decision_type="EXIT"),
        ),
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE,
    )

    runtime_root = _runtime_root(tmp_path / "second")
    _write_existing_pending(
        runtime_root,
        items=(_sell_pending_item("opi-existing-exit-76920", "76920", 2000, source_decision_type="EXIT"),),
    )
    exit_to_reduce = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=_new_pending_plan(
            runtime_root,
            _sell_pending_item("opi-sell-reduce-pm-76920-001", "76920", 1000, source_decision_type="REDUCE"),
        ),
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE,
    )

    assert reduce_to_exit.status == "PASS"
    assert reduce_to_exit.evidence["reason_codes"] == ["PENDING_SELL_REDUCE_UPGRADED_TO_EXIT"]
    assert reduce_to_exit.pending.items[0].pending_item_id == "opi-sell-exit-pm-76920-001"
    assert exit_to_reduce.status == "PASS"
    assert exit_to_reduce.evidence["reason_codes"] == ["PENDING_SELL_EXIT_PRESERVED_OVER_REDUCE"]
    assert exit_to_reduce.pending.items[0].pending_item_id == "opi-existing-exit-76920"


def _sell_input(
    *,
    symbol: str,
    owned_quantity: float,
    source_decision: str,
    final_sell_quantity: float,
    allocated_amount: float,
    estimated_price: float,
    signal_id: str,
    allocation: CapitalAllocationSignal | None = None,
):
    return make_planning_input(
        asset_state=make_asset_state(positions=(make_position(symbol=symbol).__class__(
            symbol=symbol,
            quantity=owned_quantity,
            average_price=estimated_price,
            market_value=owned_quantity * estimated_price,
            source="fixture",
            as_of="2026-07-07",
        ),)),
        ai_signals=(
            AIPlanningSignal(
                signal_id=signal_id,
                symbol=symbol,
                side="SELL",
                rank=1,
                score=1.0,
                reason="fixture sell",
                source_ai="runtime_v2_position_management",
            ),
        ),
        capital_allocations=(
            allocation
            or _sell_allocation(
                symbol=symbol,
                source_decision=source_decision,
                final_sell_quantity=final_sell_quantity,
                allocated_amount=allocated_amount,
                estimated_price=estimated_price,
            ),
        ),
    )


def _sell_allocation(
    *,
    symbol: str,
    source_decision: str,
    final_sell_quantity: float,
    allocated_amount: float,
    estimated_price: float,
) -> CapitalAllocationSignal:
    return CapitalAllocationSignal(
        allocation_id=f"sell-allocation-{symbol}",
        symbol=symbol,
        side="SELL",
        allocated_amount=allocated_amount,
        max_amount=allocated_amount,
        cash_required=0.0,
        reason="fixture sell allocation",
        estimated_price=estimated_price,
        price_source="fixture",
        price_as_of="2026-07-07",
        price_confidence="fixture",
        price_required=True,
        quantity_contract={
            "quantity_contract_version": "fixture.v1",
            "source_decision": source_decision,
            "status": "PASS",
            "final_sell_quantity": final_sell_quantity,
        },
    )


def _sell_pending_item(
    pending_item_id: str,
    symbol: str,
    quantity: float,
    *,
    source_decision_type: str,
) -> PendingOrderItem:
    item = _pending_item(
        pending_item_id,
        symbol,
        "SELL",
        quantity,
        source_decision_type=source_decision_type,
        listed_info={
            "code": symbol,
            "market": "東証",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
            "listed_info_authority": "canonical_pit_listed_issues",
            "listed_info_row_id": f"canonical_listed_issues:{BUSINESS_DATE}:{symbol}",
        },
    )
    return replace(
        item,
        quantity_contract={
            "source_decision": source_decision_type,
            "final_sell_quantity": quantity,
        },
        source_decision_type=source_decision_type,
    )


def _new_pending_plan(runtime_root, item: PendingOrderItem):
    order_plan_path = runtime_root / "fixtures" / f"{item.pending_item_id}.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text('{"order_plan_id":"order-plan-new"}', encoding="utf-8")
    return promote_order_plan_to_pending(
        order_plan_id="order-plan-new",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:new",
        environment="historical",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=(item,),
    )
