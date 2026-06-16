from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.pending_virtual_fill_data_refresh import (
    DATA_NOT_YET_AVAILABLE,
    PARTIAL_READY,
    VIRTUAL_FILL_READY,
    check_pending_virtual_fill_readiness,
    update_canonical_normalized_for_date,
)


def test_target_date_missing_returns_data_not_yet_available_and_ledger_unchanged(tmp_path: Path) -> None:
    canonical, source = _write_canonical_and_source(tmp_path, include_target=False)
    ledger_path = _write_pending_ledger(tmp_path)
    before = Path(ledger_path).read_text(encoding="utf-8")

    update = update_canonical_normalized_for_date(
        target_date="2026-06-16",
        canonical_path=canonical,
        source_normalized_path=source,
        execute=True,
    )
    readiness = check_pending_virtual_fill_readiness(target_date="2026-06-16", ledger_path=ledger_path, quotes_path=canonical)

    assert update.status == DATA_NOT_YET_AVAILABLE
    assert readiness.status == DATA_NOT_YET_AVAILABLE
    assert Path(ledger_path).read_text(encoding="utf-8") == before
    assert load_ledger(ledger_path).cash == Decimal("1000000")


def test_canonical_update_with_target_date_creates_backup_and_reaches_ready(tmp_path: Path) -> None:
    canonical, source = _write_canonical_and_source(tmp_path, include_target=True)
    ledger_path = _write_pending_ledger(tmp_path)

    update = update_canonical_normalized_for_date(
        target_date="2026-06-16",
        canonical_path=canonical,
        source_normalized_path=source,
        execute=True,
    )
    readiness = check_pending_virtual_fill_readiness(target_date="2026-06-16", ledger_path=ledger_path, quotes_path=canonical)

    assert update.status == VIRTUAL_FILL_READY
    assert Path(update.backup_path).is_file()
    assert update.max_date == "2026-06-16"
    assert update.target_date_row_count == 2
    assert readiness.status == VIRTUAL_FILL_READY
    assert readiness.open_price_availability == {"10010": True, "10020": True}


def test_duplicate_date_code_replaced_or_deduplicated(tmp_path: Path) -> None:
    canonical, source = _write_canonical_and_source(tmp_path, include_target=True, duplicate_target=True)

    update = update_canonical_normalized_for_date(
        target_date="2026-06-16",
        canonical_path=canonical,
        source_normalized_path=source,
        execute=True,
    )
    frame = pd.read_parquet(canonical)

    assert update.duplicate_date_code_count > 0
    assert frame.duplicated(subset=["date", "code"]).sum() == 0


def test_partial_missing_pending_code_returns_partial_ready(tmp_path: Path) -> None:
    canonical, source = _write_canonical_and_source(tmp_path, include_target=True, missing_second=True)
    ledger_path = _write_pending_ledger(tmp_path)
    update_canonical_normalized_for_date(
        target_date="2026-06-16",
        canonical_path=canonical,
        source_normalized_path=source,
        execute=True,
    )

    readiness = check_pending_virtual_fill_readiness(target_date="2026-06-16", ledger_path=ledger_path, quotes_path=canonical)

    assert readiness.status == PARTIAL_READY
    assert readiness.open_price_availability["10010"] is True
    assert readiness.open_price_availability["10020"] is False
    assert "pending_order_open_price_missing" in readiness.blocked_reasons


def _write_canonical_and_source(
    tmp_path: Path,
    *,
    include_target: bool,
    duplicate_target: bool = False,
    missing_second: bool = False,
) -> tuple[Path, Path]:
    canonical = tmp_path / "canonical.parquet"
    source = tmp_path / "source.parquet"
    base = [
        {"date": "2026-06-15", "code": "10010", "open": 900.0, "high": 910.0, "low": 890.0, "close": 905.0, "volume": 1000},
        {"date": "2026-06-15", "code": "10020", "open": 1400.0, "high": 1410.0, "low": 1390.0, "close": 1405.0, "volume": 1000},
    ]
    source_rows = list(base)
    if include_target:
        source_rows.append({"date": "2026-06-16", "code": "10010", "open": 1000.0, "high": 1010.0, "low": 990.0, "close": 1005.0, "volume": 1000})
        if not missing_second:
            source_rows.append({"date": "2026-06-16", "code": "10020", "open": 1500.0, "high": 1510.0, "low": 1490.0, "close": 1505.0, "volume": 1000})
        if duplicate_target:
            source_rows.append({"date": "2026-06-16", "code": "10020", "open": 1501.0, "high": 1511.0, "low": 1491.0, "close": 1506.0, "volume": 1000})
    pd.DataFrame(base).to_parquet(canonical, index=False)
    pd.DataFrame(source_rows).to_parquet(source, index=False)
    return canonical, source


def _write_pending_ledger(tmp_path: Path) -> Path:
    ledger = PaperTradingLedger(
        cash=Decimal("1000000"),
        pending_orders=(
            PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="10020", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="10020", side="BUY", quantity=Decimal("100"), status="APPROVED"),
            PendingOrderState(code="10010", side="BUY", quantity=Decimal("100"), status="APPROVED"),
        ),
    )
    return write_ledger(ledger, runtime_dir=tmp_path / ".runtime")
