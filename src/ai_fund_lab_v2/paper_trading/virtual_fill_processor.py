from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import (
    LedgerMetadata,
    PaperTradingLedger,
    PendingOrderState,
    PerformanceSnapshot,
    PositionSnapshot,
    ledger_directory,
    load_ledger,
    write_ledger,
)
from ai_fund_lab_v2.paper_trading.virtual_fill_policy import VirtualFillPolicy, resolve_open_price


def execution_id() -> str:
    return f"phase9_execution_{uuid4().hex}"


@dataclass(frozen=True)
class VirtualExecutionRecord:
    order_id: str
    code: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    fill_date: str
    realized_pnl: Decimal = Decimal("0")
    status: str = "FILLED"
    no_fill_reason: str = ""
    execution_id: str = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.execution_id is None:
            object.__setattr__(self, "execution_id", execution_id())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("quantity", "fill_price", "realized_pnl"):
            payload[key] = str(payload[key])
        return payload


@dataclass(frozen=True)
class VirtualFillResult:
    status: str
    ledger_before: PaperTradingLedger
    ledger_after: PaperTradingLedger
    executions: tuple[VirtualExecutionRecord, ...]
    no_fill_orders: tuple[VirtualExecutionRecord, ...]
    ledger_before_path: str
    ledger_after_path: str
    ledger_diff_path: str
    execution_paths: tuple[str, ...]
    dry_run: bool
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    live_order_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ledger_before": self.ledger_before.to_dict(),
            "ledger_after": self.ledger_after.to_dict(),
            "executions": [record.to_dict() for record in self.executions],
            "no_fill_orders": [record.to_dict() for record in self.no_fill_orders],
            "ledger_before_path": self.ledger_before_path,
            "ledger_after_path": self.ledger_after_path,
            "ledger_diff_path": self.ledger_diff_path,
            "execution_paths": list(self.execution_paths),
            "dry_run": self.dry_run,
            "broker_order_api_called": self.broker_order_api_called,
            "open_d_started": self.open_d_started,
            "unlock_trade_called": self.unlock_trade_called,
            "live_order_allowed": self.live_order_allowed,
        }


def process_virtual_fills(
    *,
    ledger: PaperTradingLedger,
    quote_rows: list[dict[str, Any]],
    execution_date: str,
    runtime_dir: Path | str = ".runtime",
    output_root: Path | str | None = None,
    dry_run: bool = False,
    safety_locked: bool = False,
    policy: VirtualFillPolicy | None = None,
) -> VirtualFillResult:
    policy = policy or VirtualFillPolicy()
    positions = {position.code: position for position in ledger.positions}
    cash = ledger.cash
    realized_total = ledger.performance.realized_pnl if ledger.performance else Decimal("0")
    trade_count = ledger.performance.trade_count if ledger.performance else 0
    executions: list[VirtualExecutionRecord] = []
    no_fills: list[VirtualExecutionRecord] = []
    remaining_orders: list[PendingOrderState] = []
    filled_order_ids: set[str] = set()

    orders = [order for order in ledger.pending_orders if order.status in {"APPROVED", "PENDING_VIRTUAL_FILL"}]
    ordered = [order for order in orders if order.side.upper() == "SELL"]
    ordered += [order for order in orders if order.side.upper() == "BUY" and order.dependency_order_id]
    ordered += [order for order in orders if order.side.upper() == "BUY" and not order.dependency_order_id]

    for order in ordered:
        positions, cash, realized_total, trade_count, record, updated_order = _process_order(
            order=order,
            positions=positions,
            cash=cash,
            realized_total=realized_total,
            trade_count=trade_count,
            quote_rows=quote_rows,
            execution_date=execution_date,
            filled_order_ids=filled_order_ids,
            safety_locked=safety_locked,
            policy=policy,
        )
        if record.status == "FILLED":
            executions.append(record)
            filled_order_ids.add(order.order_id)
        else:
            no_fills.append(record)
            remaining_orders.append(updated_order)
    untouched = [order for order in ledger.pending_orders if order.status != "APPROVED"]
    market_value = sum((position.market_value for position in positions.values()), Decimal("0"))
    unrealized = sum((position.unrealized_pnl for position in positions.values()), Decimal("0"))
    ledger_after = PaperTradingLedger(
        cash=cash,
        positions=tuple(positions.values()),
        pending_orders=tuple(untouched + remaining_orders),
        performance=PerformanceSnapshot(
            total_equity=cash + market_value,
            cash=cash,
            market_value=market_value,
            realized_pnl=realized_total,
            unrealized_pnl=unrealized,
            trade_count=trade_count,
        ),
        metadata=LedgerMetadata(),
    )
    paths = _write_outputs(
        ledger_before=ledger,
        ledger_after=ledger_after,
        executions=executions + no_fills,
        runtime_dir=runtime_dir,
        output_root=output_root,
        dry_run=dry_run,
    )
    return VirtualFillResult(
        status="OK",
        ledger_before=ledger,
        ledger_after=ledger_after,
        executions=tuple(executions),
        no_fill_orders=tuple(no_fills),
        ledger_before_path=paths["before"],
        ledger_after_path=paths["after"],
        ledger_diff_path=paths["diff"],
        execution_paths=tuple(paths["executions"]),
        dry_run=dry_run,
    )


def process_virtual_fills_from_files(
    *,
    ledger_path: Path,
    quotes_path: Path,
    execution_date: str,
    runtime_dir: Path | str = ".runtime",
    output_root: Path | str | None = None,
    dry_run: bool = False,
) -> VirtualFillResult:
    return process_virtual_fills(
        ledger=load_ledger(ledger_path),
        quote_rows=_read_quotes(quotes_path),
        execution_date=execution_date,
        runtime_dir=runtime_dir,
        output_root=output_root,
        dry_run=dry_run,
    )


def _process_order(
    *,
    order: PendingOrderState,
    positions: dict[str, PositionSnapshot],
    cash: Decimal,
    realized_total: Decimal,
    trade_count: int,
    quote_rows: list[dict[str, Any]],
    execution_date: str,
    filled_order_ids: set[str],
    safety_locked: bool,
    policy: VirtualFillPolicy,
) -> tuple[dict[str, PositionSnapshot], Decimal, Decimal, int, VirtualExecutionRecord, PendingOrderState]:
    reason = _precheck_order(order, cash=cash, positions=positions, filled_order_ids=filled_order_ids, safety_locked=safety_locked, policy=policy)
    fill_price = Decimal("0")
    if not reason:
        price, price_reason = resolve_open_price(code=order.code, execution_date=execution_date, quote_rows=quote_rows, side=order.side)
        if price_reason:
            reason = price_reason
        else:
            fill_price = price or Decimal("0")
            if order.side.upper() == "BUY" and fill_price * order.quantity > cash:
                reason = "CASH_INSUFFICIENT"
    if reason:
        record = _execution_record(order, fill_date=execution_date, fill_price=fill_price, status="NO_FILL", no_fill_reason=reason)
        return positions, cash, realized_total, trade_count, record, _with_no_fill(order, reason)
    if order.side.upper() == "BUY":
        cost = fill_price * order.quantity
        current = positions.get(order.code)
        old_qty = current.quantity if current else Decimal("0")
        old_cost = current.average_cost if current else Decimal("0")
        new_qty = old_qty + order.quantity
        average = ((old_cost * old_qty) + (fill_price * order.quantity)) / new_qty
        positions[order.code] = PositionSnapshot(
            code=order.code,
            quantity=new_qty,
            average_cost=average,
            market_value=new_qty * fill_price,
            unrealized_pnl=(fill_price - average) * new_qty,
            holding_days=current.holding_days if current else 0,
            name=current.name if current else "",
        )
        cash -= cost
        trade_count += 1
        return positions, cash, realized_total, trade_count, _execution_record(order, fill_date=execution_date, fill_price=fill_price), order
    current = positions[order.code]
    realized = (fill_price - current.average_cost) * order.quantity
    remaining = current.quantity - order.quantity
    if remaining > 0:
        positions[order.code] = PositionSnapshot(
            code=current.code,
            name=current.name,
            quantity=remaining,
            average_cost=current.average_cost,
            market_value=remaining * fill_price,
            unrealized_pnl=(fill_price - current.average_cost) * remaining,
            holding_days=current.holding_days,
        )
    else:
        positions.pop(order.code, None)
    cash += fill_price * order.quantity
    realized_total += realized
    trade_count += 1
    return positions, cash, realized_total, trade_count, _execution_record(order, fill_date=execution_date, fill_price=fill_price, realized_pnl=realized), order


def _precheck_order(
    order: PendingOrderState,
    *,
    cash: Decimal,
    positions: dict[str, PositionSnapshot],
    filled_order_ids: set[str],
    safety_locked: bool,
    policy: VirtualFillPolicy,
) -> str:
    if safety_locked:
        return "SAFETY_LOCKED"
    if order.quantity <= 0 or order.quantity % Decimal(str(policy.lot_size)) != 0:
        return "LOT_SIZE_INVALID"
    if order.dependency_order_id and order.dependency_order_id not in filled_order_ids:
        return "SELL_DEPENDENCY_NOT_FILLED"
    if order.side.upper() == "SELL":
        current = positions.get(order.code)
        if current is None or current.quantity < order.quantity:
            return "SELL_QUANTITY_INSUFFICIENT"
    return ""


def _execution_record(
    order: PendingOrderState,
    *,
    fill_date: str,
    fill_price: Decimal,
    realized_pnl: Decimal = Decimal("0"),
    status: str = "FILLED",
    no_fill_reason: str = "",
) -> VirtualExecutionRecord:
    return VirtualExecutionRecord(
        order_id=order.order_id,
        code=order.code,
        side=order.side.upper(),
        quantity=order.quantity,
        fill_price=fill_price,
        fill_date=fill_date,
        realized_pnl=realized_pnl,
        status=status,
        no_fill_reason=no_fill_reason,
    )


def _with_no_fill(order: PendingOrderState, reason: str) -> PendingOrderState:
    return PendingOrderState(
        order_id=order.order_id,
        code=order.code,
        side=order.side,
        quantity=order.quantity,
        created_at=order.created_at,
        status=order.status,
        dependency_order_id=order.dependency_order_id,
        no_fill_reason=reason,
        planned_amount=order.planned_amount,
        virtual_order_date=order.virtual_order_date,
        virtual_execution_date=order.virtual_execution_date,
        reason=order.reason,
        review_status=order.review_status,
    )


def _write_outputs(
    *,
    ledger_before: PaperTradingLedger,
    ledger_after: PaperTradingLedger,
    executions: list[VirtualExecutionRecord],
    runtime_dir: Path | str,
    output_root: Path | str | None,
    dry_run: bool,
) -> dict[str, Any]:
    root = Path(output_root) if output_root else Path(runtime_dir)
    run_dir = root / "phase9" / "ledger_runs" / ledger_after.metadata.ledger_id
    run_dir.mkdir(parents=True, exist_ok=True)
    before_path = run_dir / "ledger_before.json"
    after_path = run_dir / "ledger_after.json"
    diff_path = run_dir / "ledger_diff.json"
    before_path.write_text(json.dumps(ledger_before.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    after_path.write_text(json.dumps(ledger_after.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diff = _ledger_diff(ledger_before, ledger_after)
    diff_path.write_text(json.dumps(diff, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    execution_paths = _write_execution_records(executions, Path(runtime_dir) if not dry_run else root)
    if not dry_run:
        write_ledger(ledger_after, runtime_dir)
    return {"before": str(before_path), "after": str(after_path), "diff": str(diff_path), "executions": execution_paths}


def _write_execution_records(records: list[VirtualExecutionRecord], root: Path) -> list[str]:
    directory = ledger_directory(root) / "executions"
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for record in records:
        path = directory / f"{record.execution_id}.json"
        path.write_text(json.dumps(record.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(str(path))
    return paths


def _ledger_diff(before: PaperTradingLedger, after: PaperTradingLedger) -> dict[str, str]:
    before_perf = before.performance
    after_perf = after.performance
    return {
        "cash_change": str(after.cash - before.cash),
        "market_value_change": str((after_perf.market_value if after_perf else Decimal("0")) - (before_perf.market_value if before_perf else Decimal("0"))),
        "realized_pnl_change": str((after_perf.realized_pnl if after_perf else Decimal("0")) - (before_perf.realized_pnl if before_perf else Decimal("0"))),
        "unrealized_pnl_change": str((after_perf.unrealized_pnl if after_perf else Decimal("0")) - (before_perf.unrealized_pnl if before_perf else Decimal("0"))),
        "position_count_change": str(len(after.positions) - len(before.positions)),
        "pending_order_count_change": str(len(after.pending_orders) - len(before.pending_orders)),
    }


def _read_quotes(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".parquet":
        import pandas as pd

        return [dict(item) for item in pd.read_parquet(path).to_dict(orient="records")]
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".jsonl":
            return [json.loads(line) for line in handle if line.strip()]
        payload = json.load(handle)
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        rows = payload.get("rows") or payload.get("daily_quotes") or []
        return [dict(item) for item in rows if isinstance(item, dict)]
    return []
