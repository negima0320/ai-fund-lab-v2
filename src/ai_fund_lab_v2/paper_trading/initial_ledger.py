from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import LedgerMetadata, PaperTradingLedger, load_ledger


INITIAL_LEDGER_CREATED = "INITIAL_LEDGER_CREATED"
INITIAL_LEDGER_BLOCKED = "INITIAL_LEDGER_BLOCKED"


@dataclass(frozen=True)
class InitialLedgerCreationResult:
    status: str
    ledger_path: str = ""
    latest_path: str = ""
    ledger_id: str = ""
    initial_cash: str = "0"
    currency: str = "JPY"
    start_date: str = ""
    positions_count: int = 0
    pending_orders_count: int = 0
    performance: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    prohibited_flags: dict[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prohibited_flags"] = self.prohibited_flags or prohibited_flags()
        return payload


def create_initial_ledger(
    *,
    initial_cash: Decimal,
    currency: str,
    ledger_root: Path | str,
    start_date: str,
    overwrite: bool = False,
) -> InitialLedgerCreationResult:
    root = Path(ledger_root)
    latest_path = root / "latest.json"
    if latest_path.exists() and not overwrite:
        existing = load_ledger(latest_path)
        return InitialLedgerCreationResult(
            status=INITIAL_LEDGER_BLOCKED,
            latest_path=str(latest_path),
            ledger_id=existing.metadata.ledger_id,
            initial_cash=str(existing.metadata.initial_cash or existing.cash),
            currency=existing.metadata.currency,
            start_date=existing.metadata.start_date,
            positions_count=len(existing.positions),
            pending_orders_count=len(existing.pending_orders),
            performance=_jsonable(asdict(existing.performance)),
            blocked_reasons=("latest_ledger_already_exists",),
            prohibited_flags=prohibited_flags(),
        )
    if initial_cash <= 0:
        return InitialLedgerCreationResult(
            status=INITIAL_LEDGER_BLOCKED,
            latest_path=str(latest_path),
            initial_cash=str(initial_cash),
            currency=currency,
            start_date=start_date,
            blocked_reasons=("initial_cash_must_be_positive",),
            prohibited_flags=prohibited_flags(),
        )
    now = utc_now_iso()
    ledger = PaperTradingLedger(
        cash=initial_cash,
        positions=(),
        pending_orders=(),
        metadata=LedgerMetadata(
            as_of=now,
            source="phase9_initial_paper_trading_ledger",
            phase="phase9",
            created_at=now,
            start_date=start_date,
            currency=currency,
            initial_cash=initial_cash,
            broker_order_api_called=False,
            open_d_started=False,
            unlock_trade_called=False,
            virtual_fill_executed=False,
        ),
    )
    root.mkdir(parents=True, exist_ok=True)
    payload = ledger.to_dict()
    ledger_path = root / f"{ledger.metadata.ledger_id}.json"
    serialized = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ledger_path.write_text(serialized, encoding="utf-8")
    latest_path.write_text(serialized, encoding="utf-8")
    return InitialLedgerCreationResult(
        status=INITIAL_LEDGER_CREATED,
        ledger_path=str(ledger_path),
        latest_path=str(latest_path),
        ledger_id=ledger.metadata.ledger_id,
        initial_cash=str(initial_cash),
        currency=currency,
        start_date=start_date,
        positions_count=0,
        pending_orders_count=0,
        performance=_jsonable(asdict(ledger.performance)),
        prohibited_flags=prohibited_flags(),
    )


def prohibited_flags() -> dict[str, bool]:
    return {
        "broker_order_api_called": False,
        "moomoo_simulate_order_called": False,
        "tachibana_order_called": False,
        "open_d_started": False,
        "login_called": False,
        "logout_called": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value
