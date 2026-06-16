from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


def paper_ledger_id() -> str:
    return f"paper_ledger_{uuid4().hex}"


@dataclass(frozen=True)
class PaperPosition:
    issue_code: str
    quantity: Decimal
    issue_name: str = ""
    average_price: Decimal = Decimal("0")
    market_price: Decimal = Decimal("0")


@dataclass(frozen=True)
class PaperOrder:
    paper_order_id: str
    issue_code: str
    side: str
    quantity: Decimal
    status: str = "PENDING"


@dataclass(frozen=True)
class PaperExecution:
    paper_execution_id: str
    paper_order_id: str
    issue_code: str
    side: str
    quantity: Decimal
    price: Decimal
    executed_at: str


@dataclass(frozen=True)
class PaperLedger:
    cash: Decimal
    buying_power: Decimal
    positions: tuple[PaperPosition, ...] = ()
    pending_orders: tuple[PaperOrder, ...] = ()
    executions: tuple[PaperExecution, ...] = ()
    as_of: str = field(default_factory=utc_now_iso)
    ledger_id: str = field(default_factory=paper_ledger_id)
    schema_version: str = "phase8.paper_ledger.v1"
    source: str = "paper"

    def __post_init__(self) -> None:
        if self.source != "paper":
            raise ValueError("PaperLedger source must be paper.")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def write_paper_ledger(ledger: PaperLedger, runtime_dir: Path | str = ".runtime") -> Path:
    path = paper_ledger_directory(runtime_dir) / f"{ledger.ledger_id}.json"
    payload = sanitize_mapping(ledger.to_dict())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_paper_ledger(path: Path) -> PaperLedger:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Paper ledger payload must be an object.")
    return PaperLedger(
        cash=_decimal(payload.get("cash")),
        buying_power=_decimal(payload.get("buying_power")),
        positions=tuple(
            PaperPosition(
                issue_code=str(item.get("issue_code", "")),
                issue_name=str(item.get("issue_name", "")),
                quantity=_decimal(item.get("quantity")),
                average_price=_decimal(item.get("average_price")),
                market_price=_decimal(item.get("market_price")),
            )
            for item in payload.get("positions", [])
            if isinstance(item, dict)
        ),
        pending_orders=tuple(
            PaperOrder(
                paper_order_id=str(item.get("paper_order_id", "")),
                issue_code=str(item.get("issue_code", "")),
                side=str(item.get("side", "")),
                quantity=_decimal(item.get("quantity")),
                status=str(item.get("status", "PENDING")),
            )
            for item in payload.get("pending_orders", [])
            if isinstance(item, dict)
        ),
        executions=tuple(
            PaperExecution(
                paper_execution_id=str(item.get("paper_execution_id", "")),
                paper_order_id=str(item.get("paper_order_id", "")),
                issue_code=str(item.get("issue_code", "")),
                side=str(item.get("side", "")),
                quantity=_decimal(item.get("quantity")),
                price=_decimal(item.get("price")),
                executed_at=str(item.get("executed_at", "")),
            )
            for item in payload.get("executions", [])
            if isinstance(item, dict)
        ),
        as_of=str(payload.get("as_of", "")),
        ledger_id=str(payload.get("ledger_id", "")),
        schema_version=str(payload.get("schema_version", "")),
        source=str(payload.get("source", "")),
    )


def paper_ledger_directory(runtime_dir: Path | str = ".runtime") -> Path:
    return Path(runtime_dir) / "order_manager" / "paper" / "ledgers"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))

