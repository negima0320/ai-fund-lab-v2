from ai_fund_lab_v2.runtime_v2.execution.ledger_projection import (
    can_use_broker_orders_fallback,
    fallback_policy_metadata,
)


def test_production_mode_fallback_false():
    assert not can_use_broker_orders_fallback(
        environment="demo",
        mode="production",
        explicitly_requested=True,
    )


def test_production_environment_fallback_false():
    assert not can_use_broker_orders_fallback(
        environment="production",
        mode="demo",
        explicitly_requested=True,
    )


def test_demo_explicit_fallback_true():
    assert can_use_broker_orders_fallback(
        environment="demo",
        mode="demo",
        explicitly_requested=True,
    )


def test_demo_fallback_requires_explicit_request():
    assert not can_use_broker_orders_fallback(
        environment="demo",
        mode="demo",
        explicitly_requested=False,
    )


def test_fallback_metadata_sets_review_required_and_not_production_equivalent():
    metadata = fallback_policy_metadata(
        environment="demo",
        mode="demo",
        explicitly_requested=True,
    )

    assert metadata["allowed"] is True
    assert metadata["review_required"] is True
    assert metadata["production_equivalent"] is False
    assert metadata["source"] == "broker_orders_fallback"

