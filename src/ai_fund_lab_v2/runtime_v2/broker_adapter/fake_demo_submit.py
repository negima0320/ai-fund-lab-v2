"""Fake Runtime v2 demo submit adapter for dry-run tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ai_fund_lab_v2.runtime_v2.submit.models import (
    RuntimeV2SubmitCommand,
    RuntimeV2SubmitResult,
)


@dataclass(frozen=True)
class FakeRuntimeV2DemoSubmitAdapter:
    accept: bool = True
    post_send_unknown: bool = False

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        if command.environment != "demo":
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason="environment guard failure",
            )
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="fake runtime v2 demo submit preflight",
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        if command.environment != "demo":
            return RuntimeV2SubmitResult(
                status="BLOCKED",
                submitted=False,
                accepted=False,
                blocked=True,
                review_required=False,
                broker_api_called=False,
                reason="environment guard failure",
            )
        if self.post_send_unknown:
            return RuntimeV2SubmitResult(
                status="POST_SEND_UNKNOWN",
                submitted=True,
                accepted=False,
                blocked=False,
                review_required=True,
                broker_api_called=False,
                post_send_unknown=True,
                reason="fake post send unknown",
            )
        return RuntimeV2SubmitResult(
            status="ACCEPTED" if self.accept else "REJECTED_OR_UNKNOWN",
            submitted=True,
            accepted=self.accept,
            blocked=False,
            review_required=not self.accept,
            broker_api_called=False,
            broker_order_id_hash=_hash(command.command_id),
            reason="fake runtime v2 demo submit",
        )


def _hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
