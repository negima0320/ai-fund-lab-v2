from dataclasses import fields

from ai_fund_lab_v2.runtime_v2.pending.models import (
    PendingOrderItem,
    PendingOrderPlan,
    PendingPlanState,
)
from ai_fund_lab_v2.runtime_v2.state_machine.models import RuntimeState


def test_pending_order_plan_required_fields_exist():
    field_names = {field.name for field in fields(PendingOrderPlan)}

    assert {
        "schema_version",
        "pending_plan_id",
        "state",
        "environment",
        "created_at",
        "updated_at",
        "plan_created_date",
        "intended_submit_date",
        "target_session_date",
        "source_order_plan",
        "approval",
        "approved_item_ids",
        "items",
        "submit_constraints",
        "consume",
        "raw_request_saved",
        "raw_response_saved",
        "secret_saved",
    }.issubset(field_names)


def test_pending_order_item_required_fields_exist():
    field_names = {field.name for field in fields(PendingOrderItem)}

    assert {
        "pending_item_id",
        "symbol",
        "side",
        "quantity",
        "order_type",
        "estimated_price",
        "estimated_amount",
        "approved",
        "state",
    }.issubset(field_names)


def test_raw_payload_secret_flags_default_false():
    field_defaults = {field.name: field.default for field in fields(PendingOrderPlan)}

    assert field_defaults["raw_request_saved"] is False
    assert field_defaults["raw_response_saved"] is False
    assert field_defaults["secret_saved"] is False


def test_consumed_is_pending_state_not_runtime_state():
    assert PendingPlanState.CONSUMED.value == "CONSUMED"
    assert "CONSUMED" not in RuntimeState.__members__

