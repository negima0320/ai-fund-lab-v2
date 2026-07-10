"""Runtime v2-native Submit models.

These models are the submit authority inside Runtime v2. They intentionally do
not import legacy runtime order command or broker implementation modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeV2SubmitCommand:
    command_id: str
    environment: str
    pending_plan_id: str
    pending_item_id: str
    approval_hash: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    price_type: str
    limit_price: float
    estimated_amount: float
    target_session_date: str
    live_order_allowed: bool
    source_current_path: str = "pending_order_plan/pending_order_plan.json"
    listed_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class RuntimeV2SubmitPreflightResult:
    allowed: bool
    blocked: bool
    review_required: bool
    reason: str
    command: RuntimeV2SubmitCommand | None = None
    guard_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeV2SubmitResult:
    status: str
    submitted: bool
    accepted: bool
    blocked: bool
    review_required: bool
    broker_api_called: bool
    broker_order_id_hash: str = ""
    post_send_unknown: bool = False
    reason: str = ""
    raw_request_saved: bool = False
    raw_response_saved: bool = False
    secret_saved: bool = False
    issue_code_normalization: dict[str, Any] = field(default_factory=dict)
    response_classification: dict[str, Any] = field(default_factory=dict)
    configuration_diagnostic: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""
