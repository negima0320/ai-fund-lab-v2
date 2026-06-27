from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger


@dataclass(frozen=True)
class PendingOrderDedupResult:
    status: str
    ledger_path: str
    latest_path: str
    backup_path: str
    before_pending_count: int
    after_pending_count: int
    removed_count: int
    removed_orders: tuple[dict[str, Any], ...]
    cash_before: str
    cash_after: str
    positions_before: int
    positions_after: int
    trade_count_before: int
    trade_count_after: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["removed_orders"] = list(self.removed_orders)
        return payload


def pending_order_fingerprint(order: PendingOrderState, *, decision_for: str = "") -> tuple[str, str, str, str, str, str]:
    return (
        decision_for or order.decision_for,
        order.virtual_execution_date,
        order.code,
        order.side.upper(),
        str(order.quantity),
        str(order.planned_amount),
    )


def pending_order_legacy_fingerprint(order: PendingOrderState) -> tuple[str, str, str, str, str]:
    return (
        order.virtual_execution_date,
        order.code,
        order.side.upper(),
        str(order.quantity),
        str(order.planned_amount),
    )


def dedup_pending_orders_in_ledger_file(
    *,
    ledger_path: Path | str,
    runtime_dir: Path | str = ".runtime",
    backup: bool = True,
    dry_run: bool = False,
    backup_label: str = "phase9z_before_pending_dedup",
) -> PendingOrderDedupResult:
    path = Path(ledger_path)
    ledger = load_ledger(path)
    kept: list[PendingOrderState] = []
    removed: list[PendingOrderState] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for order in sorted(ledger.pending_orders, key=lambda item: item.created_at or ""):
        fp = pending_order_legacy_fingerprint(order)
        if fp in seen:
            removed.append(order)
            continue
        seen.add(fp)
        kept.append(order)

    backup_path = ""
    if backup and not dry_run:
        backup_dir = Path(runtime_dir) / "phase9" / "ledger" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = utc_now_iso().replace(":", "").replace("-", "").split(".")[0]
        backup_file = backup_dir / f"{backup_label}_{stamp}.json"
        shutil.copy2(path, backup_file)
        backup_path = str(backup_file)

    updated = PaperTradingLedger(
        cash=ledger.cash,
        positions=ledger.positions,
        pending_orders=tuple(kept),
        performance=ledger.performance,
        metadata=ledger.metadata,
    )
    latest_path = str(Path(runtime_dir) / "phase9" / "ledger" / "latest.json")
    written_path = str(path)
    if not dry_run and removed:
        written = write_ledger(updated, runtime_dir=runtime_dir)
        written_path = str(written)

    return PendingOrderDedupResult(
        status="PENDING_ORDER_DEDUP_APPLIED" if removed and not dry_run else ("PENDING_ORDER_DEDUP_DRY_RUN" if dry_run else "PENDING_ORDER_DEDUP_NOOP"),
        ledger_path=written_path,
        latest_path=latest_path,
        backup_path=backup_path,
        before_pending_count=len(ledger.pending_orders),
        after_pending_count=len(kept),
        removed_count=len(removed),
        removed_orders=tuple(_order_payload(order) for order in removed),
        cash_before=str(ledger.cash),
        cash_after=str(updated.cash),
        positions_before=len(ledger.positions),
        positions_after=len(updated.positions),
        trade_count_before=ledger.performance.trade_count,
        trade_count_after=updated.performance.trade_count,
    )


def write_dedup_report(result: PendingOrderDedupResult, *, json_path: Path | str, markdown_path: Path | str) -> None:
    payload = result.to_dict()
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = Path(markdown_path)
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Pending Order Dedup",
        "",
        f"- status: {payload['status']}",
        f"- before_pending_count: {payload['before_pending_count']}",
        f"- after_pending_count: {payload['after_pending_count']}",
        f"- removed_count: {payload['removed_count']}",
        f"- backup_path: {payload['backup_path']}",
        "",
        "## Removed Orders",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["removed_orders"])
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _order_payload(order: PendingOrderState) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "decision_for": order.decision_for,
        "code": order.code,
        "side": order.side,
        "quantity": str(order.quantity),
        "planned_amount": str(order.planned_amount),
        "created_at": order.created_at,
        "status": order.status,
        "virtual_order_date": order.virtual_order_date,
        "virtual_execution_date": order.virtual_execution_date,
    }
