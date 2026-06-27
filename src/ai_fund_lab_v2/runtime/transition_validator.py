from __future__ import annotations

from ai_fund_lab_v2.runtime.runtime_result import RuntimeResultStatus, RuntimeTransitionResult
from ai_fund_lab_v2.runtime.states import RuntimeState


ALLOWED_TRANSITIONS: dict[RuntimeState, tuple[RuntimeState, ...]] = {
    RuntimeState.PREOPEN: (RuntimeState.ORDER_PREPARED,),
    RuntimeState.ORDER_PREPARED: (RuntimeState.ORDER_SUBMITTED,),
    RuntimeState.ORDER_SUBMITTED: (RuntimeState.WAITING_FILL,),
    RuntimeState.WAITING_FILL: (RuntimeState.PARTIALLY_FILLED, RuntimeState.FILLED),
    RuntimeState.PARTIALLY_FILLED: (RuntimeState.FILLED, RuntimeState.MONITORING),
    RuntimeState.FILLED: (RuntimeState.MONITORING,),
    RuntimeState.MONITORING: (RuntimeState.CLOSE_VALUATION,),
    RuntimeState.CLOSE_VALUATION: (RuntimeState.NIGHTLY_INFERENCE,),
    RuntimeState.NIGHTLY_INFERENCE: (RuntimeState.REPORT_READY,),
    RuntimeState.REPORT_READY: (RuntimeState.PREOPEN,),
    RuntimeState.HALT: (),
}


class TransitionValidator:
    def validate(self, from_state: RuntimeState | str, to_state: RuntimeState | str) -> RuntimeTransitionResult:
        current = RuntimeState.parse_or_halt(from_state)
        target = RuntimeState.parse_or_halt(to_state)

        if current is RuntimeState.HALT or target is RuntimeState.HALT:
            return RuntimeTransitionResult(
                from_state=current,
                to_state=RuntimeState.HALT,
                allowed=False,
                status=RuntimeResultStatus.HALT,
                reason="unknown_state",
            )

        if target in ALLOWED_TRANSITIONS[current]:
            return RuntimeTransitionResult(
                from_state=current,
                to_state=target,
                allowed=True,
                status=RuntimeResultStatus.PASS,
                reason="allowed",
            )

        return RuntimeTransitionResult(
            from_state=current,
            to_state=target,
            allowed=False,
            status=RuntimeResultStatus.BLOCKED,
            reason="transition_not_allowed",
        )
