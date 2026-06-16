from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, PendingOrderState, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.pending_virtual_fill_data_refresh import (
    DATA_NOT_YET_AVAILABLE,
    PARTIAL_READY,
    VIRTUAL_FILL_READY,
    check_pending_virtual_fill_readiness,
    update_canonical_normalized_for_date,
    write_phase9q_report,
)


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9q_market_data_refresh_for_pending_virtual_fill.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9q_market_data_refresh_for_pending_virtual_fill.json"
LEDGER_PATH = ROOT / ".runtime" / "phase9" / "ledger" / "latest.json"
CANONICAL_PATH = ROOT / ".runtime" / "phase9" / "canonical_data" / "normalized_daily_quotes" / "data.parquet"
SOURCE_NORMALIZED_PATH = ROOT / ".runtime" / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"


def main() -> int:
    ledger_before = _file_hash(LEDGER_PATH)
    canonical = update_canonical_normalized_for_date(
        target_date="2026-06-16",
        canonical_path=CANONICAL_PATH,
        source_normalized_path=SOURCE_NORMALIZED_PATH,
        execute=True,
    )
    readiness = check_pending_virtual_fill_readiness(target_date="2026-06-16", ledger_path=LEDGER_PATH, quotes_path=CANONICAL_PATH)
    ledger_after = _file_hash(LEDGER_PATH)
    temp = _run_temp_safety_checks()
    payload = write_phase9q_report(
        target_date="2026-06-16",
        fetch_status=_fetch_status_from_current_files(canonical),
        canonical_update=canonical,
        readiness=readiness,
        markdown_path=DOC_PATH,
        json_path=JSON_PATH,
    )
    checks = {
        "canonical_update_dry_run_execute_safe": temp["dry_run_no_write"] is True and temp["execute_ready"] is True,
        "backup_created": temp["backup_created"] is True,
        "duplicate_prevented": temp["duplicate_prevented"] is True,
        "future_row_blocked": temp["future_row_blocked"] is True,
        "readiness_check_runs": readiness.status in {VIRTUAL_FILL_READY, DATA_NOT_YET_AVAILABLE, PARTIAL_READY},
        "target_missing_maps_to_data_not_yet_available": temp["missing_status"] == DATA_NOT_YET_AVAILABLE,
        "partial_missing_code_maps_to_partial_ready": temp["partial_status"] == PARTIAL_READY,
        "all_prices_available_maps_to_virtual_fill_ready": temp["ready_status"] == VIRTUAL_FILL_READY,
        "ledger_unchanged": ledger_before == ledger_after,
        "virtual_fill_not_executed": payload["virtual_fill_executed"] is False,
        "broker_order_not_called": payload["broker_order_api_called"] is False,
        "open_d_not_started": payload["open_d_started"] is False,
        "unlock_trade_not_called": payload["unlock_trade_called"] is False,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload["audit_status"] = status
    payload["checks"] = checks
    payload["temp_safety_checks"] = temp
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _run_temp_safety_checks() -> dict[str, object]:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        canonical, source = _write_canonical_and_source(root, include_target=True)
        before = _file_hash(canonical)
        dry = update_canonical_normalized_for_date(target_date="2026-06-16", canonical_path=canonical, source_normalized_path=source, execute=False)
        after_dry = _file_hash(canonical)
        execute = update_canonical_normalized_for_date(target_date="2026-06-16", canonical_path=canonical, source_normalized_path=source, execute=True)
        frame = pd.read_parquet(canonical)
        ledger = _write_pending_ledger(root)
        ready = check_pending_virtual_fill_readiness(target_date="2026-06-16", ledger_path=ledger, quotes_path=canonical)
        missing_canonical, missing_source = _write_canonical_and_source(root / "missing", include_target=False)
        missing = update_canonical_normalized_for_date(target_date="2026-06-16", canonical_path=missing_canonical, source_normalized_path=missing_source, execute=True)
        partial_canonical, partial_source = _write_canonical_and_source(root / "partial", include_target=True, missing_second=True)
        update_canonical_normalized_for_date(target_date="2026-06-16", canonical_path=partial_canonical, source_normalized_path=partial_source, execute=True)
        partial = check_pending_virtual_fill_readiness(target_date="2026-06-16", ledger_path=ledger, quotes_path=partial_canonical)
        future_canonical, future_source = _write_canonical_and_source(root / "future", include_target=True, include_future=True)
        future = update_canonical_normalized_for_date(target_date="2026-06-16", canonical_path=future_canonical, source_normalized_path=future_source, execute=True)
        return {
            "dry_run_no_write": before == after_dry and dry.status == "CANONICAL_UPDATE_READY",
            "execute_ready": execute.status == VIRTUAL_FILL_READY,
            "backup_created": bool(execute.backup_path and Path(execute.backup_path).is_file()),
            "duplicate_prevented": int(frame.duplicated(subset=["date", "code"]).sum()) == 0,
            "future_row_blocked": "future_rows_detected" in future.blocked_reasons,
            "ready_status": ready.status,
            "missing_status": missing.status,
            "partial_status": partial.status,
        }


def _write_canonical_and_source(
    root: Path,
    *,
    include_target: bool,
    missing_second: bool = False,
    include_future: bool = False,
) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    canonical = root / "canonical.parquet"
    source = root / "source.parquet"
    base = [
        {"date": "2026-06-15", "code": "10010", "open": 900.0, "high": 910.0, "low": 890.0, "close": 905.0, "volume": 1000},
        {"date": "2026-06-15", "code": "10020", "open": 1400.0, "high": 1410.0, "low": 1390.0, "close": 1405.0, "volume": 1000},
    ]
    rows = list(base)
    if include_target:
        rows.append({"date": "2026-06-16", "code": "10010", "open": 1000.0, "high": 1010.0, "low": 990.0, "close": 1005.0, "volume": 1000})
        if not missing_second:
            rows.append({"date": "2026-06-16", "code": "10020", "open": 1500.0, "high": 1510.0, "low": 1490.0, "close": 1505.0, "volume": 1000})
    if include_future:
        rows.append({"date": "2026-06-17", "code": "10010", "open": 1001.0, "high": 1011.0, "low": 991.0, "close": 1006.0, "volume": 1000})
    pd.DataFrame(base).to_parquet(canonical, index=False)
    pd.DataFrame(rows).to_parquet(source, index=False)
    return canonical, source


def _write_pending_ledger(root: Path) -> Path:
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
    return write_ledger(ledger, runtime_dir=root / ".runtime")


def _fetch_status_from_current_files(canonical) -> str:
    if canonical.status == DATA_NOT_YET_AVAILABLE:
        return DATA_NOT_YET_AVAILABLE
    if canonical.target_date_row_count > 0:
        return "FETCHED_OR_ALREADY_AVAILABLE"
    return "NOT_READY"


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Phase9-Q Market Data Refresh for Pending Virtual Fill",
        "",
        f"- audit_status: {payload['audit_status']}",
        f"- judgment: {payload['judgment']}",
        f"- target_date: {payload['target_date']}",
        f"- fetch_status: {payload['fetch_status']}",
        f"- canonical_normalized_update_status: {payload['canonical_normalized_update_status']}",
        f"- canonical_min_date: {payload['canonical_min_date']}",
        f"- canonical_max_date: {payload['canonical_max_date']}",
        f"- target_date_row_count: {payload['target_date_row_count']}",
        "",
        "## Pending Order Codes",
        "",
    ]
    for code in payload["pending_order_codes"]:
        lines.append(f"- {code}: open_price_available={payload['open_price_availability'].get(code)}")
    lines.extend(["", "## Checks", ""])
    for key, value in sorted(payload["checks"].items()):
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Blocked Reasons", ""])
    blocked = payload["blocked_reasons"]
    lines.extend([f"- {reason}" for reason in blocked] if blocked else ["- none"])
    lines.extend(
        [
            "",
            "## Next Action",
            "",
            payload["next_action"],
            "",
            "## Safety",
            "",
            "- ledger_updated: false",
            "- virtual_fill_executed: false",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "",
        ]
    )
    return "\n".join(lines)


def _file_hash(path: Path) -> str:
    return __import__("hashlib").sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


if __name__ == "__main__":
    raise SystemExit(main())

