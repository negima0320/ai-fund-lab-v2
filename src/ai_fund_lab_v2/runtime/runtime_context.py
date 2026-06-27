from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.runtime.runtime_mode import RuntimeEnvironment, RuntimeMode


def runtime_id() -> str:
    return f"runtime_{uuid4().hex}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RuntimeContext:
    environment: RuntimeMode
    business_date: str
    evaluation_cash: Decimal = Decimal("0")
    broker_actual_cash: Decimal = Decimal("0")
    broker_snapshot_path: str = ""
    paper_ledger_path: str = ""
    paper_test_id: str = ""
    runtime_id: str = field(default_factory=runtime_id)
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not self.business_date:
            raise ValueError("RuntimeContext requires business_date.")
        if not self.runtime_id:
            raise ValueError("RuntimeContext requires runtime_id.")
        if self.evaluation_cash < Decimal("0"):
            raise ValueError("RuntimeContext evaluation_cash must be non-negative.")
        if self.broker_actual_cash < Decimal("0"):
            raise ValueError("RuntimeContext broker_actual_cash must be non-negative.")

    @classmethod
    def paper(
        cls,
        *,
        business_date: str,
        evaluation_cash: Decimal,
        paper_test_id: str = "",
        paper_ledger_path: str = "",
        broker_snapshot_path: str = "",
    ) -> "RuntimeContext":
        return cls(
            environment=RuntimeEnvironment.PAPER,
            business_date=business_date,
            evaluation_cash=evaluation_cash,
            paper_test_id=paper_test_id,
            paper_ledger_path=paper_ledger_path,
            broker_snapshot_path=broker_snapshot_path,
        )

    @classmethod
    def demo(
        cls,
        *,
        business_date: str,
        evaluation_cash: Decimal,
        broker_actual_cash: Decimal,
        broker_snapshot_path: str = "",
        paper_test_id: str = "",
        paper_ledger_path: str = "",
    ) -> "RuntimeContext":
        return cls(
            environment=RuntimeEnvironment.DEMO,
            business_date=business_date,
            evaluation_cash=evaluation_cash,
            broker_actual_cash=broker_actual_cash,
            broker_snapshot_path=broker_snapshot_path,
            paper_test_id=paper_test_id,
            paper_ledger_path=paper_ledger_path,
        )

    @classmethod
    def production(
        cls,
        *,
        business_date: str,
        broker_actual_cash: Decimal,
        broker_snapshot_path: str = "",
    ) -> "RuntimeContext":
        return cls(
            environment=RuntimeEnvironment.PRODUCTION,
            business_date=business_date,
            evaluation_cash=broker_actual_cash,
            broker_actual_cash=broker_actual_cash,
            broker_snapshot_path=broker_snapshot_path,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _jsonable(asdict(self))
        payload["environment"] = self.environment.value
        payload["runtime_mode"] = self.environment.value
        return payload


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
