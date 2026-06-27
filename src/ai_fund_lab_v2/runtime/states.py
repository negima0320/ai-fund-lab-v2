from __future__ import annotations

from enum import Enum


class RuntimeState(str, Enum):
    PREOPEN = "PREOPEN"
    ORDER_PREPARED = "ORDER_PREPARED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    WAITING_FILL = "WAITING_FILL"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    MONITORING = "MONITORING"
    CLOSE_VALUATION = "CLOSE_VALUATION"
    NIGHTLY_INFERENCE = "NIGHTLY_INFERENCE"
    REPORT_READY = "REPORT_READY"
    HALT = "HALT"

    @classmethod
    def parse(cls, value: "RuntimeState | str") -> "RuntimeState":
        if isinstance(value, RuntimeState):
            return value
        return cls(str(value))

    @classmethod
    def parse_or_halt(cls, value: "RuntimeState | str") -> "RuntimeState":
        try:
            return cls.parse(value)
        except ValueError:
            return cls.HALT
