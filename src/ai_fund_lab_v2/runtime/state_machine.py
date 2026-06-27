from __future__ import annotations

from dataclasses import dataclass, field

from ai_fund_lab_v2.runtime.fill_event import FillMonitorResult
from ai_fund_lab_v2.runtime.order_command import OrderResult
from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext
from ai_fund_lab_v2.runtime.runtime_manifest import RuntimeManifest, RuntimeTransitionManifest
from ai_fund_lab_v2.runtime.runtime_result import RuntimeResultStatus, RuntimeTransitionResult
from ai_fund_lab_v2.runtime.states import RuntimeState
from ai_fund_lab_v2.runtime.transition_validator import TransitionValidator


@dataclass(frozen=True)
class RuntimeStateMachine:
    context: RuntimeContext
    current_state: RuntimeState = RuntimeState.PREOPEN
    validator: TransitionValidator = field(default_factory=TransitionValidator)

    def transition_to(self, target: RuntimeState | str) -> tuple["RuntimeStateMachine", RuntimeTransitionManifest]:
        result = self.validator.validate(self.current_state, target)
        next_state = result.to_state if result.allowed else RuntimeState.HALT if result.reason == "unknown_state" else self.current_state
        next_machine = RuntimeStateMachine(context=self.context, current_state=next_state, validator=self.validator)
        return next_machine, RuntimeTransitionManifest(context=self.context, transition=result)

    def transition_result(self, target: RuntimeState | str) -> RuntimeTransitionResult:
        return self.validator.validate(self.current_state, target)

    def transition_after_order_result(self, order_result: OrderResult) -> tuple["RuntimeStateMachine", RuntimeTransitionManifest]:
        if self.current_state is not RuntimeState.ORDER_PREPARED:
            result = RuntimeTransitionResult(
                from_state=self.current_state,
                to_state=RuntimeState.ORDER_SUBMITTED,
                allowed=False,
                status=RuntimeResultStatus.BLOCKED,
                reason="order_result_transition_requires_order_prepared",
            )
            return self, RuntimeTransitionManifest(context=self.context, transition=result)
        if not order_result.submitted:
            result = RuntimeTransitionResult(
                from_state=self.current_state,
                to_state=RuntimeState.ORDER_SUBMITTED,
                allowed=False,
                status=RuntimeResultStatus.BLOCKED,
                reason=order_result.reason or "order_not_submitted",
            )
            return self, RuntimeTransitionManifest(context=self.context, transition=result)
        return self.transition_to(RuntimeState.ORDER_SUBMITTED)

    def transition_after_fill_monitor(self, fill_result: FillMonitorResult) -> tuple["RuntimeStateMachine", RuntimeTransitionManifest]:
        target = fill_result.runtime_next_state
        if target is RuntimeState.HALT:
            result = RuntimeTransitionResult(
                from_state=self.current_state,
                to_state=RuntimeState.HALT,
                allowed=True,
                status=RuntimeResultStatus.HALT,
                reason=fill_result.reason or "fill_monitor_halt",
            )
            return RuntimeStateMachine(context=self.context, current_state=RuntimeState.HALT, validator=self.validator), RuntimeTransitionManifest(
                context=self.context, transition=result
            )
        return self.transition_to(target)

    def manifest(self) -> RuntimeManifest:
        return RuntimeManifest(context=self.context, state=self.current_state)
