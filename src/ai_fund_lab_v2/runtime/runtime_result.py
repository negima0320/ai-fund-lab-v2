from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from ai_fund_lab_v2.runtime.states import RuntimeState


class RuntimeResultStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    HALT = "HALT"


@dataclass(frozen=True)
class RuntimeResult:
    status: RuntimeResultStatus
    message: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class RuntimeTransitionResult:
    from_state: RuntimeState
    to_state: RuntimeState
    allowed: bool
    status: RuntimeResultStatus
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "allowed": self.allowed,
            "status": self.status.value,
            "reason": self.reason,
        }
