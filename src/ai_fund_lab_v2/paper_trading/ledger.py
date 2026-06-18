from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping


PENDING_ORDER_STATUSES = {"PENDING", "APPROVED", "PENDING_VIRTUAL_FILL", "REJECTED", "EXPIRED"}


def ledger_id() -> str:
    return f"phase9_ledger_{uuid4().hex}"


def pending_order_id() -> str:
    return f"phase9_pending_order_{uuid4().hex}"


@dataclass(frozen=True)
class LedgerMetadata:
    ledger_id: str = field(default_factory=ledger_id)
    as_of: str = field(default_factory=utc_now_iso)
    schema_version: str = "phase9.paper_ledger.v1"
    source: str = "phase9_paper_trading"
    phase: str = "phase9"
    created_at: str = field(default_factory=utc_now_iso)
    start_date: str = ""
    currency: str = "JPY"
    initial_cash: Decimal = Decimal("0")
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    virtual_fill_executed: bool = False


@dataclass(frozen=True)
class PositionSnapshot:
    code: str
    quantity: Decimal
    average_cost: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    holding_days: int = 0
    name: str = ""
    last_valuation_date: str = ""


@dataclass(frozen=True)
class PendingOrderState:
    code: str
    side: str
    quantity: Decimal
    status: str = "PENDING"
    created_at: str = field(default_factory=utc_now_iso)
    order_id: str = field(default_factory=pending_order_id)
    dependency_order_id: str = ""
    no_fill_reason: str = ""
    planned_amount: Decimal = Decimal("0")
    virtual_order_date: str = ""
    virtual_execution_date: str = ""
    reason: str = ""
    review_status: str = ""

    def __post_init__(self) -> None:
        if self.status not in PENDING_ORDER_STATUSES:
            raise ValueError(f"Unsupported pending order status: {self.status}")
        if self.side.upper() not in {"BUY", "SELL", "HOLD"}:
            raise ValueError(f"Unsupported pending order side: {self.side}")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class PerformanceSnapshot:
    total_equity: Decimal
    cash: Decimal
    market_value: Decimal
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    trade_count: int = 0


@dataclass(frozen=True)
class PaperTradingLedger:
    cash: Decimal
    positions: tuple[PositionSnapshot, ...] = ()
    pending_orders: tuple[PendingOrderState, ...] = ()
    performance: PerformanceSnapshot | None = None
    metadata: LedgerMetadata = field(default_factory=LedgerMetadata)

    def __post_init__(self) -> None:
        if self.performance is None:
            object.__setattr__(self, "performance", calculate_performance_snapshot(self))

    def to_dict(self) -> dict[str, Any]:
        return sanitize_mapping(_jsonable(asdict(self)))


def calculate_performance_snapshot(ledger: PaperTradingLedger) -> PerformanceSnapshot:
    market_value = sum((position.market_value for position in ledger.positions), Decimal("0"))
    unrealized_pnl = sum((position.unrealized_pnl for position in ledger.positions), Decimal("0"))
    return PerformanceSnapshot(
        total_equity=ledger.cash + market_value,
        cash=ledger.cash,
        market_value=market_value,
        realized_pnl=Decimal("0"),
        unrealized_pnl=unrealized_pnl,
        trade_count=0,
    )


def ledger_directory(runtime_dir: Path | str = ".runtime") -> Path:
    return Path(runtime_dir) / "phase9" / "ledger"


def write_ledger(ledger: PaperTradingLedger, runtime_dir: Path | str = ".runtime") -> Path:
    directory = ledger_directory(runtime_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{ledger.metadata.ledger_id}.json"
    payload = ledger.to_dict()
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest = directory / "latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_ledger(path: Path | str) -> PaperTradingLedger:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Paper trading ledger payload must be an object.")
    metadata_payload = payload.get("metadata") or {}
    performance_payload = payload.get("performance") or {}
    return PaperTradingLedger(
        cash=_decimal(payload.get("cash")),
        positions=tuple(
            PositionSnapshot(
                code=str(item.get("code") or ""),
                name=str(item.get("name") or ""),
                quantity=_decimal(item.get("quantity")),
                average_cost=_decimal(item.get("average_cost")),
                market_value=_decimal(item.get("market_value")),
                unrealized_pnl=_decimal(item.get("unrealized_pnl")),
                holding_days=int(item.get("holding_days") or 0),
                last_valuation_date=str(item.get("last_valuation_date") or ""),
            )
            for item in payload.get("positions", [])
            if isinstance(item, dict)
        ),
        pending_orders=tuple(
            PendingOrderState(
                order_id=str(item.get("order_id") or pending_order_id()),
                code=str(item.get("code") or ""),
                side=str(item.get("side") or ""),
                quantity=_decimal(item.get("quantity")),
                created_at=str(item.get("created_at") or ""),
                status=str(item.get("status") or "PENDING"),
                dependency_order_id=str(item.get("dependency_order_id") or ""),
                no_fill_reason=str(item.get("no_fill_reason") or ""),
                planned_amount=_decimal(item.get("planned_amount")),
                virtual_order_date=str(item.get("virtual_order_date") or ""),
                virtual_execution_date=str(item.get("virtual_execution_date") or ""),
                reason=str(item.get("reason") or ""),
                review_status=str(item.get("review_status") or ""),
            )
            for item in payload.get("pending_orders", [])
            if isinstance(item, dict)
        ),
        performance=PerformanceSnapshot(
            total_equity=_decimal(performance_payload.get("total_equity")),
            cash=_decimal(performance_payload.get("cash")),
            market_value=_decimal(performance_payload.get("market_value")),
            realized_pnl=_decimal(performance_payload.get("realized_pnl")),
            unrealized_pnl=_decimal(performance_payload.get("unrealized_pnl")),
            trade_count=int(performance_payload.get("trade_count") or 0),
        ),
        metadata=LedgerMetadata(
            ledger_id=str(metadata_payload.get("ledger_id") or ""),
            as_of=str(metadata_payload.get("as_of") or ""),
            schema_version=str(metadata_payload.get("schema_version") or ""),
            source=str(metadata_payload.get("source") or ""),
            phase=str(metadata_payload.get("phase") or "phase9"),
            created_at=str(metadata_payload.get("created_at") or metadata_payload.get("as_of") or ""),
            start_date=str(metadata_payload.get("start_date") or ""),
            currency=str(metadata_payload.get("currency") or "JPY"),
            initial_cash=_decimal(metadata_payload.get("initial_cash")),
            broker_order_api_called=bool(metadata_payload.get("broker_order_api_called", False)),
            open_d_started=bool(metadata_payload.get("open_d_started", False)),
            unlock_trade_called=bool(metadata_payload.get("unlock_trade_called", False)),
            virtual_fill_executed=bool(metadata_payload.get("virtual_fill_executed", False)),
        ),
    )


def load_latest_ledger(runtime_dir: Path | str = ".runtime") -> PaperTradingLedger | None:
    path = ledger_directory(runtime_dir) / "latest.json"
    if not path.exists():
        return None
    return load_ledger(path)


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
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value).replace(",", ""))
