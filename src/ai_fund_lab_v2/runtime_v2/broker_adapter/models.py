"""Runtime v2 broker adapter protocols."""

from __future__ import annotations

from typing import Protocol

from ai_fund_lab_v2.runtime_v2.submit.models import (
    RuntimeV2SubmitCommand,
    RuntimeV2SubmitResult,
)


class RuntimeV2DemoSubmitAdapter(Protocol):
    """Broker adapter boundary for demo submit.

    Implementations may reuse low-level Tachibana clients, codecs, transports,
    and response parsers, but must not require legacy runtime OrderCommand as
    the submit authority.
    """

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        ...
