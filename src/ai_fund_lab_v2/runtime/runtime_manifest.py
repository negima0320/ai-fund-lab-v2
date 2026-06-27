from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.runtime.runtime_context import RuntimeContext
from ai_fund_lab_v2.runtime.runtime_result import RuntimeTransitionResult
from ai_fund_lab_v2.runtime.states import RuntimeState


def manifest_id() -> str:
    return f"runtime_manifest_{uuid4().hex}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RuntimeManifest:
    context: RuntimeContext
    state: RuntimeState
    manifest_id: str = field(default_factory=manifest_id)
    schema_version: str = "runtime_manifest_v1"
    created_at: str = field(default_factory=utc_now_iso)
    immutable: bool = True
    broker_api_called: bool = False
    demo_order_submitted: bool = False
    production_order_submitted: bool = False
    paper_ledger_updated: bool = False
    broker_snapshot_updated: bool = False
    ai_learning_updated: bool = False
    backtest_run: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["context"] = self.context.to_dict()
        payload["state"] = self.state.value
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class RuntimeTransitionManifest:
    context: RuntimeContext
    transition: RuntimeTransitionResult
    manifest_id: str = field(default_factory=manifest_id)
    schema_version: str = "runtime_transition_manifest_v1"
    created_at: str = field(default_factory=utc_now_iso)
    immutable: bool = True
    broker_api_called: bool = False
    demo_order_submitted: bool = False
    production_order_submitted: bool = False
    paper_ledger_updated: bool = False
    broker_snapshot_updated: bool = False
    ai_learning_updated: bool = False
    backtest_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["context"] = self.context.to_dict()
        payload["transition"] = self.transition.to_dict()
        return payload


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
