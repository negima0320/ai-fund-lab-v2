from dataclasses import fields

from ai_fund_lab_v2.runtime_v2.planning.models import (
    AIPlanningSignal,
    CapitalAllocationSignal,
    DailyPlan,
    OrderPlan,
    PlanningResult,
    RuntimeSafetyContext,
)


def test_planning_signal_models_exist():
    assert AIPlanningSignal
    assert CapitalAllocationSignal
    assert RuntimeSafetyContext


def test_order_plan_daily_plan_and_result_required_fields():
    assert {"order_plan_id", "items", "asset_state_id", "review_required", "blocked"}.issubset(
        {field.name for field in fields(OrderPlan)}
    )
    assert {"daily_plan_id", "order_plan_id", "summary"}.issubset(
        {field.name for field in fields(DailyPlan)}
    )
    assert {"daily_plan", "order_plan", "status", "errors", "warnings"}.issubset(
        {field.name for field in fields(PlanningResult)}
    )


def test_runtime_has_no_fixed_symbol_count_field():
    all_fields = set()
    for model in (OrderPlan, DailyPlan, PlanningResult):
        all_fields.update(field.name for field in fields(model))

    assert "max_symbols" not in all_fields
    assert "fixed_symbol_count" not in all_fields
    assert "top5_only" not in all_fields


def test_ai_score_and_rank_are_input_fields_only():
    field_names = {field.name for field in fields(AIPlanningSignal)}

    assert {"rank", "score"}.issubset(field_names)
