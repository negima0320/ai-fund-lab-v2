from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.storage.path_resolver import resolve_current_path


def test_resolve_current_path_requires_mode():
    with pytest.raises(ValueError, match="mode is required"):
        resolve_current_path("", "demo", "runtime_state")


def test_resolve_current_path_requires_environment():
    with pytest.raises(ValueError, match="environment is required"):
        resolve_current_path("demo", "", "runtime_state")


def test_resolve_current_path_has_no_default_production_fallback():
    with pytest.raises(TypeError):
        resolve_current_path(environment="demo", object_type="runtime_state")


def test_current_path_uses_runtime_mode_root():
    path = resolve_current_path("demo", "demo", "runtime_state")

    assert path == Path(".runtime/runtime_state/current_state.json")


@pytest.mark.parametrize(
    "object_type",
    [
        "runtime_state",
        "pending_order_plan",
        "persistent_ledger_state",
        "persistent_ledger_orders",
        "persistent_ledger_executions",
        "persistent_ledger_positions",
        "persistent_ledger_cash",
        "persistent_ledger_events",
        "notification_delivery_ledger",
    ],
)
def test_current_path_does_not_include_business_date_or_phase_dir(object_type):
    path_text = str(resolve_current_path("demo", "demo", object_type))

    assert "2026-07-07" not in path_text
    assert "phase13" not in path_text.lower()


def test_persistent_ledger_state_resolves_to_current_state_path():
    path = resolve_current_path("demo", "demo", "persistent_ledger_state")

    assert path == Path(".runtime/persistent_ledger/state.json")


def test_pending_order_plan_resolves_to_current_pending_path():
    path = resolve_current_path("demo", "demo", "pending_order_plan")

    assert path == Path(".runtime/pending_order_plan/pending_order_plan.json")


def test_current_path_does_not_include_runtime_mode_root():
    path = str(resolve_current_path("demo", "demo", "persistent_ledger_state"))

    assert ".runtime/demo/" not in path
    assert ".runtime/production/" not in path


def test_persistent_ledger_cash_resolves_to_cash_jsonl():
    path = resolve_current_path("demo", "demo", "persistent_ledger_cash")

    assert path == Path(".runtime/persistent_ledger/cash.jsonl")
