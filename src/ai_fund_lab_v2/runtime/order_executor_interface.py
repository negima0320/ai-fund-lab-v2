from __future__ import annotations

from typing import Any, Protocol

from ai_fund_lab_v2.runtime.approval import ApprovalRecord
from ai_fund_lab_v2.runtime.order_command import OrderCommand, OrderResult
from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext
from ai_fund_lab_v2.runtime.runtime_result import RuntimeResult


class OrderExecutorInterface(Protocol):
    def prepare(self, context: RuntimeContext, order_plan: dict[str, Any]) -> RuntimeResult: ...

    def submit(self, command: OrderCommand, approval: ApprovalRecord | None = None) -> OrderResult: ...

    def status(self, context: RuntimeContext, order_ref: str) -> RuntimeResult: ...
