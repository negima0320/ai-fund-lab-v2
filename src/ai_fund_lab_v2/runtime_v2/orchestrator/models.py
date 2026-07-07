"""Models for Runtime v2 orchestrator skeleton."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_fund_lab_v2.runtime_v2.state_machine.models import (
    RuntimeState,
    RuntimeTransition,
)
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import (
    ALLOWED_ENVIRONMENTS,
    ALLOWED_MODES,
)

_BUSINESS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class RuntimeRunRequest:
    mode: str
    environment: str
    business_date: str
    start_state: RuntimeState = RuntimeState.IDLE
    dry_run: bool = True

    def __post_init__(self) -> None:
        if not self.mode:
            raise ValueError("mode is required")
        if self.mode not in ALLOWED_MODES:
            raise ValueError(f"unsupported mode: {self.mode}")
        if not self.environment:
            raise ValueError("environment is required")
        if self.environment not in ALLOWED_ENVIRONMENTS:
            raise ValueError(f"unsupported environment: {self.environment}")
        if not self.business_date:
            raise ValueError("business_date is required")
        if not _BUSINESS_DATE_RE.fullmatch(self.business_date):
            raise ValueError(f"invalid business_date: {self.business_date}")
        if not isinstance(self.start_state, RuntimeState):
            object.__setattr__(self, "start_state", RuntimeState(self.start_state))


@dataclass(frozen=True)
class RuntimeRunResult:
    mode: str
    environment: str
    business_date: str
    start_state: RuntimeState
    end_state: RuntimeState
    transitions: tuple[RuntimeTransition, ...]
    review_required: bool
    blocked: bool
    side_effect_executed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

