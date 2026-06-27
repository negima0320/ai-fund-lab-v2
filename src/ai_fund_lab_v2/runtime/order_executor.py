from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_fund_lab_v2.runtime.approval import ApprovalRecord, default_deny, paper_auto_approval
from ai_fund_lab_v2.runtime.order_authorization import OrderAuthorizationResult, OrderAuthorizationStatus
from ai_fund_lab_v2.runtime.order_command import OrderCommand, OrderResult, OrderResultStatus
from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext
from ai_fund_lab_v2.runtime.runtime_mode import RuntimeMode
from ai_fund_lab_v2.runtime.runtime_result import RuntimeResult, RuntimeResultStatus


@dataclass(frozen=True)
class PaperOrderExecutor:
    def prepare(self, context: RuntimeContext, order_plan: dict[str, Any]) -> RuntimeResult:
        return RuntimeResult(status=RuntimeResultStatus.PASS, message="paper_order_prepared")

    def submit(self, command: OrderCommand, approval: ApprovalRecord | None = None) -> OrderResult:
        approval = approval or paper_auto_approval()
        if command.environment is not RuntimeMode.PAPER:
            return _blocked_no_approval("paper_executor_environment_mismatch")
        if command.approval_required and not approval.approved:
            return _blocked_no_approval("approval_missing")
        return OrderResult(
            status=OrderResultStatus.PAPER_ONLY_SUBMITTED,
            submitted=True,
            accepted=True,
            reason="paper_only_no_broker_api",
        )

    def status(self, context: RuntimeContext, order_ref: str) -> RuntimeResult:
        return RuntimeResult(status=RuntimeResultStatus.PASS, message="paper_order_status_stub")


@dataclass(frozen=True)
class DemoOrderExecutor:
    def prepare(self, context: RuntimeContext, order_plan: dict[str, Any]) -> RuntimeResult:
        return RuntimeResult(status=RuntimeResultStatus.PASS, message="demo_order_prepared_stub")

    def submit(
        self,
        command: OrderCommand,
        approval: ApprovalRecord | None = None,
        *,
        authorization: OrderAuthorizationResult | None = None,
        dry_run: bool = False,
    ) -> OrderResult:
        approval = approval or default_deny(RuntimeMode.DEMO, reason="demo_approval_missing")
        if not command.live_order_allowed:
            return _blocked_live_disabled()
        if authorization is not None:
            mapped = _result_from_authorization(authorization)
            if mapped is not None:
                return mapped
            if dry_run:
                return OrderResult(status=OrderResultStatus.DRY_RUN_READY, skipped=True, reason="demo_dry_run_ready_no_broker_api")
        if command.approval_required and (not approval.approved or approval.environment is not RuntimeMode.DEMO):
            return _blocked_no_approval("demo_approval_missing")
        return OrderResult(status=OrderResultStatus.BLOCKED_EXECUTOR_STUB, skipped=True, reason="demo_executor_stub_no_broker_api")

    def status(self, context: RuntimeContext, order_ref: str) -> RuntimeResult:
        return RuntimeResult(status=RuntimeResultStatus.BLOCKED, message="demo_order_status_stub_no_broker_api")


@dataclass(frozen=True)
class ProductionOrderExecutor:
    def prepare(self, context: RuntimeContext, order_plan: dict[str, Any]) -> RuntimeResult:
        return RuntimeResult(status=RuntimeResultStatus.PASS, message="production_order_prepared_stub")

    def submit(self, command: OrderCommand, approval: ApprovalRecord | None = None) -> OrderResult:
        approval = approval or default_deny(RuntimeMode.PRODUCTION, reason="production_approval_missing")
        if command.environment is RuntimeMode.PRODUCTION:
            return OrderResult(
                status=OrderResultStatus.BLOCKED_PRODUCTION_PROHIBITED,
                skipped=True,
                reason="production_order_prohibited",
            )
        if not command.live_order_allowed:
            return _blocked_live_disabled()
        if command.approval_required and (not approval.approved or approval.environment is not RuntimeMode.PRODUCTION):
            return _blocked_no_approval("production_approval_missing")
        return OrderResult(
            status=OrderResultStatus.BLOCKED_EXECUTOR_STUB,
            skipped=True,
            reason="production_executor_stub_no_broker_api",
        )

    def status(self, context: RuntimeContext, order_ref: str) -> RuntimeResult:
        return RuntimeResult(status=RuntimeResultStatus.BLOCKED, message="production_order_status_stub_no_broker_api")


def _blocked_no_approval(reason: str) -> OrderResult:
    return OrderResult(status=OrderResultStatus.BLOCKED_NO_APPROVAL, skipped=True, reason=reason)


def _blocked_live_disabled() -> OrderResult:
    return OrderResult(
        status=OrderResultStatus.BLOCKED_LIVE_ORDER_DISABLED,
        skipped=True,
        reason="live_order_allowed_false",
    )


def _result_from_authorization(authorization: OrderAuthorizationResult) -> OrderResult | None:
    if authorization.status is OrderAuthorizationStatus.APPROVED:
        return None
    status_map = {
        OrderAuthorizationStatus.BLOCKED_NO_APPROVAL: OrderResultStatus.BLOCKED_NO_APPROVAL,
        OrderAuthorizationStatus.BLOCKED_LIVE_ORDER_DISABLED: OrderResultStatus.BLOCKED_LIVE_ORDER_DISABLED,
        OrderAuthorizationStatus.BLOCKED_APPROVAL_SCOPE_MISMATCH: OrderResultStatus.BLOCKED_APPROVAL_SCOPE_MISMATCH,
        OrderAuthorizationStatus.BLOCKED_SECOND_PASSWORD_MISSING: OrderResultStatus.BLOCKED_SECOND_PASSWORD_MISSING,
        OrderAuthorizationStatus.BLOCKED_PRODUCTION_PROHIBITED: OrderResultStatus.BLOCKED_PRODUCTION_PROHIBITED,
        OrderAuthorizationStatus.BLOCKED_APPROVAL_EXPIRED: OrderResultStatus.BLOCKED_APPROVAL_SCOPE_MISMATCH,
    }
    return OrderResult(status=status_map[authorization.status], skipped=True, reason=authorization.reason)
