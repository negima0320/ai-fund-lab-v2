from __future__ import annotations

from decimal import Decimal

from ai_fund_lab_v2.runtime import (
    BusinessDayGuard,
    InMemoryRunLockStore,
    RuntimeContext,
    RuntimeEnvironment,
    RuntimeMode,
    RuntimeState,
    RuntimeStateMachine,
    TransitionValidator,
)
from ai_fund_lab_v2.runtime.runtime_result import RuntimeResultStatus


def test_normal_state_transition_path() -> None:
    machine = RuntimeStateMachine(context=_demo_context())
    for target in (
        RuntimeState.ORDER_PREPARED,
        RuntimeState.ORDER_SUBMITTED,
        RuntimeState.WAITING_FILL,
        RuntimeState.FILLED,
        RuntimeState.MONITORING,
        RuntimeState.CLOSE_VALUATION,
        RuntimeState.NIGHTLY_INFERENCE,
        RuntimeState.REPORT_READY,
    ):
        machine, manifest = machine.transition_to(target)
        assert manifest.transition.allowed is True
        assert machine.current_state is target


def test_partial_fill_path_can_rejoin_monitoring() -> None:
    machine = RuntimeStateMachine(context=_demo_context(), current_state=RuntimeState.WAITING_FILL)
    machine, partial_manifest = machine.transition_to(RuntimeState.PARTIALLY_FILLED)
    assert partial_manifest.transition.allowed is True
    assert machine.current_state is RuntimeState.PARTIALLY_FILLED

    machine, monitoring_manifest = machine.transition_to(RuntimeState.MONITORING)
    assert monitoring_manifest.transition.allowed is True
    assert machine.current_state is RuntimeState.MONITORING


def test_invalid_transition_is_blocked_and_keeps_state() -> None:
    machine = RuntimeStateMachine(context=_demo_context())
    next_machine, manifest = machine.transition_to(RuntimeState.FILLED)

    assert manifest.transition.allowed is False
    assert manifest.transition.status is RuntimeResultStatus.BLOCKED
    assert manifest.transition.reason == "transition_not_allowed"
    assert next_machine.current_state is RuntimeState.PREOPEN


def test_unknown_state_goes_to_halt() -> None:
    result = TransitionValidator().validate("NOT_A_STATE", RuntimeState.ORDER_PREPARED)

    assert result.allowed is False
    assert result.from_state is RuntimeState.HALT
    assert result.to_state is RuntimeState.HALT
    assert result.status is RuntimeResultStatus.HALT


def test_unknown_target_goes_to_halt() -> None:
    machine = RuntimeStateMachine(context=_demo_context())
    next_machine, manifest = machine.transition_to("NOT_A_STATE")

    assert manifest.transition.allowed is False
    assert manifest.transition.to_state is RuntimeState.HALT
    assert next_machine.current_state is RuntimeState.HALT


def test_runtime_context_modes_share_same_state_machine() -> None:
    contexts = (
        RuntimeContext.paper(business_date="2026-06-29", evaluation_cash=Decimal("1000000"), paper_test_id="paper_test2"),
        RuntimeContext.demo(
            business_date="2026-06-29",
            evaluation_cash=Decimal("1000000"),
            broker_actual_cash=Decimal("20000000"),
            broker_snapshot_path=".runtime/broker/tachibana/demo/latest_broker_snapshot.json",
        ),
        RuntimeContext.production(
            business_date="2026-06-29",
            broker_actual_cash=Decimal("1000000"),
            broker_snapshot_path=".runtime/broker/tachibana/prod/latest_broker_snapshot.json",
        ),
    )
    assert [context.environment for context in contexts] == [
        RuntimeMode.PAPER,
        RuntimeMode.DEMO,
        RuntimeMode.PRODUCTION,
    ]
    for context in contexts:
        machine, manifest = RuntimeStateMachine(context=context).transition_to(RuntimeState.ORDER_PREPARED)
        assert machine.current_state is RuntimeState.ORDER_PREPARED
        assert manifest.context.environment is context.environment


def test_manifest_schema_has_no_runtime_mutation_flags() -> None:
    manifest = RuntimeStateMachine(context=_demo_context()).manifest().to_dict()

    assert manifest["schema_version"] == "runtime_manifest_v1"
    assert manifest["immutable"] is True
    assert manifest["broker_api_called"] is False
    assert manifest["demo_order_submitted"] is False
    assert manifest["production_order_submitted"] is False
    assert manifest["paper_ledger_updated"] is False
    assert manifest["broker_snapshot_updated"] is False
    assert manifest["ai_learning_updated"] is False
    assert manifest["backtest_run"] is False


def test_runtime_state_machine_has_no_phase11_safety_states() -> None:
    assert "SAFETY_CHECKED" not in {state.value for state in RuntimeState}
    assert "EMERGENCY_STOP" not in {state.value for state in RuntimeState}


def test_run_lock_blocks_same_day_different_runtime() -> None:
    first = _demo_context()
    second = RuntimeContext.demo(
        business_date="2026-06-29",
        evaluation_cash=Decimal("1000000"),
        broker_actual_cash=Decimal("20000000"),
    )
    store = InMemoryRunLockStore()

    lock = store.acquire(first, reason="phase10n_test")
    assert lock.locked is True
    assert lock.conflicts_with(second) is True


def test_run_lock_release() -> None:
    context = _demo_context()
    store = InMemoryRunLockStore()
    store.acquire(context)
    released = store.release(context)

    assert released.locked is False


def test_business_day_guard_weekday_weekend_and_holiday() -> None:
    guard = BusinessDayGuard(holidays=frozenset({"2026-06-29"}))

    assert BusinessDayGuard().check("2026-06-26").is_business_day is True
    assert BusinessDayGuard().check("2026-06-27").reason == "weekend"
    assert guard.check("2026-06-29").reason == "holiday"


def test_runtime_environment_alias_kept_for_compatibility() -> None:
    assert RuntimeEnvironment is RuntimeMode


def _demo_context() -> RuntimeContext:
    return RuntimeContext.demo(
        business_date="2026-06-29",
        evaluation_cash=Decimal("1000000"),
        broker_actual_cash=Decimal("20000000"),
        broker_snapshot_path=".runtime/broker/tachibana/demo/latest_broker_snapshot.json",
        paper_test_id="paper_test2_2026-06-29",
    )
