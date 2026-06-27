from __future__ import annotations

from typing import Protocol

from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext
from ai_fund_lab_v2.runtime.runtime_result import RuntimeResult


class BrokerRuntimeInterface(Protocol):
    def preopen_snapshot(self, context: RuntimeContext) -> RuntimeResult: ...

    def order_status(self, context: RuntimeContext) -> RuntimeResult: ...

    def fill_status(self, context: RuntimeContext) -> RuntimeResult: ...

    def position_snapshot(self, context: RuntimeContext) -> RuntimeResult: ...

    def close_snapshot(self, context: RuntimeContext) -> RuntimeResult: ...
