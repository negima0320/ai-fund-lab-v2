"""Side-effect-free Runtime v2 orchestrator skeleton."""

from __future__ import annotations

from pathlib import Path
import json

from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state
from ai_fund_lab_v2.runtime_v2.orchestrator.models import (
    RuntimeRunRequest,
    RuntimeRunResult,
)
from ai_fund_lab_v2.runtime_v2.state_machine.models import RuntimeState
from ai_fund_lab_v2.runtime_v2.state_machine.transitions import validate_transition


class RuntimeOrchestrator:
    """Minimal preflight orchestrator.

    Phase13-N intentionally performs no market refresh, AI inference, planning,
    submit, broker connection, ledger write, notification, scheduler, or plist
    operation.
    """

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir

    def run_preflight(self, request: RuntimeRunRequest) -> RuntimeRunResult:
        """Run side-effect-free preflight using fixed Current State paths."""

        request = _ensure_request(request)
        transitions = []
        errors: list[str] = []
        warnings: list[str] = []

        persistent_state = read_current_state(
            mode=request.mode,
            environment=request.environment,
            object_type="persistent_ledger_state",
            base_dir=self._base_dir,
        )
        runtime_state = read_current_state(
            mode=request.mode,
            environment=request.environment,
            object_type="runtime_state",
            base_dir=self._base_dir,
        )
        pending_plan = read_current_state(
            mode=request.mode,
            environment=request.environment,
            object_type="pending_order_plan",
            base_dir=self._base_dir,
        )

        _collect_non_blocking_current_warning(warnings, runtime_state)
        _collect_non_blocking_current_warning(warnings, pending_plan)

        if persistent_state.classification in {"MISSING", "UNKNOWN", "INVALID"}:
            transition = validate_transition(
                request.start_state,
                RuntimeState.REVIEW_REQUIRED,
                reason=f"persistent_ledger_state {persistent_state.classification}",
            )
            transitions.append(transition)
            errors.extend(persistent_state.errors)
            return RuntimeRunResult(
                mode=request.mode,
                environment=request.environment,
                business_date=request.business_date,
                start_state=request.start_state,
                end_state=RuntimeState.REVIEW_REQUIRED,
                transitions=tuple(transitions),
                review_required=True,
                blocked=False,
                side_effect_executed=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

        transitions.extend(
            (
                validate_transition(
                    request.start_state,
                    RuntimeState.MARKET_DATA_READY,
                    reason="preflight marker only; market refresh not executed",
                ),
                validate_transition(
                    RuntimeState.MARKET_DATA_READY,
                    RuntimeState.FEATURE_READY,
                    reason="preflight marker only; feature refresh not executed",
                ),
                validate_transition(
                    RuntimeState.FEATURE_READY,
                    RuntimeState.CURRENT_STATE_LOADED,
                    reason="persistent_ledger_state current loaded",
                ),
            )
        )
        invalid_transitions = tuple(
            transition for transition in transitions if not transition.allowed
        )
        if invalid_transitions:
            errors.extend(
                f"invalid transition: {transition.from_state.value}->{transition.to_state.value}"
                for transition in invalid_transitions
            )
            return RuntimeRunResult(
                mode=request.mode,
                environment=request.environment,
                business_date=request.business_date,
                start_state=request.start_state,
                end_state=RuntimeState.BLOCKED,
                transitions=tuple(transitions),
                review_required=True,
                blocked=True,
                side_effect_executed=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

        return RuntimeRunResult(
            mode=request.mode,
            environment=request.environment,
            business_date=request.business_date,
            start_state=request.start_state,
            end_state=RuntimeState.CURRENT_STATE_LOADED,
            transitions=tuple(transitions),
            review_required=False,
            blocked=False,
            side_effect_executed=False,
            errors=(),
            warnings=tuple(warnings),
        )


def _ensure_request(request: RuntimeRunRequest) -> RuntimeRunRequest:
    if not isinstance(request, RuntimeRunRequest):
        raise TypeError("request must be RuntimeRunRequest")
    return request


def _collect_non_blocking_current_warning(warnings: list[str], result) -> None:
    if result.object_type == "runtime_state" and result.classification == "MISSING":
        return
    if result.object_type == "pending_order_plan" and _pending_slot_is_empty(result.path):
        return
    if result.classification in {"MISSING", "UNKNOWN", "INVALID"}:
        warnings.append(f"{result.object_type} {result.classification}")


def _pending_slot_is_empty(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return str(payload.get("status") or payload.get("state") or "").upper() == "EMPTY" and not bool(
        payload.get("active_pending", True)
    )
