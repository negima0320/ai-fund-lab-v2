from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalSubmitAdapter
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand


BUSINESS_DATE = "2026-06-29"
EVALUATION_TIME = "2026-06-29T14:59:00+09:00"
PENDING_SYMBOLS = ("33500", "36810", "186A0", "70630", "31340")


def test_phase17_bv8_submit_resolves_20260629_pending_symbols_from_asof_listed_snapshot(tmp_path: Path) -> None:
    adapter, listed_path = _adapter(tmp_path, symbols=PENDING_SYMBOLS)

    for symbol in PENDING_SYMBOLS:
        result = adapter.preflight(_command(symbol))

        assert result.status == "DRY_RUN_READY"
        authority = result.response_classification["pit_universe_authority"]
        assert authority["pit_universe_authority_type"] == "HISTORICAL_ASOF_LISTED_ISSUES"
        assert authority["selected_snapshot_date"] == BUSINESS_DATE
        assert authority["selected_snapshot_path"] == str(listed_path)
        assert authority["selected_content_hash"] == _sha(listed_path)
        assert authority["future_snapshot_used"] is False
        assert authority["normalized_symbol"] == symbol
        assert authority["lineage_match"] is True


def test_phase17_bv8_submit_normalizes_numeric_and_alpha_five_character_codes(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, symbols=("33500", "186A0"))

    numeric = adapter.preflight(_command("33500", listed_info_code="33500"))
    alpha = adapter.preflight(_command("186a0", listed_info_code="186A0"))

    assert numeric.status == "DRY_RUN_READY"
    assert alpha.status == "DRY_RUN_READY"
    assert alpha.response_classification["pit_universe_authority"]["normalized_symbol"] == "186A0"


def test_phase17_bv8_submit_rejects_future_listed_snapshot_authority(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, symbols=("33500",), selected_snapshot_date="2026-06-30")

    result = adapter.preflight(_command("33500"))

    assert result.status == "HALT"
    assert result.blocked is True
    assert result.response_classification["reason"] == "historical_asof_listed_issues_future_snapshot_rejected"


def test_phase17_bv8_submit_rejects_missing_snapshot_even_with_pending_embedded_listed_info(tmp_path: Path) -> None:
    adapter, listed_path = _adapter(tmp_path, symbols=("33500",))
    listed_path.unlink()

    result = adapter.preflight(_command("33500", listed_info_code="33500", current_listed=True))

    assert result.status == "HALT"
    assert result.blocked is True
    assert result.response_classification["reason"] == "historical_asof_listed_issues_path_missing"


def test_phase17_bv8_submit_rejects_pending_listed_info_lineage_mismatch(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, symbols=("33500",))

    result = adapter.preflight(_command("33500", listed_info_code="36810"))

    assert result.status == "HALT"
    assert result.blocked is True
    assert result.response_classification["reason"] == "pending_listed_info_code_mismatch"
    assert result.response_classification["lineage_match"] is False


def test_phase17_bv8_historical_resolver_does_not_authorize_non_historical_command(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, symbols=("33500",))

    result = adapter.preflight(_command("33500", environment="demo"))

    assert result.status == "BLOCKED"
    assert result.reason == "historical submit adapter cannot run outside historical environment"


def test_phase17_bv8_corporate_action_guard_is_target_symbol_scoped(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, symbols=("33500",), unrelated_corporate_action=True)

    result = adapter.preflight(_command("33500"))

    assert result.status == "DRY_RUN_READY"


def test_phase17_bv8_corporate_action_guard_still_halts_target_symbol(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path, symbols=("33500",), target_corporate_action=True)

    result = adapter.preflight(_command("33500"))

    assert result.status == "HALT"
    assert result.reason == "corporate action guard failed"
    assert result.response_classification["corporate_action_status"] == "IMPACT_DETECTED"


def _adapter(
    tmp_path: Path,
    *,
    symbols: tuple[str, ...],
    selected_snapshot_date: str = BUSINESS_DATE,
    unrelated_corporate_action: bool = False,
    target_corporate_action: bool = False,
) -> tuple[HistoricalSubmitAdapter, Path]:
    ohlcv_path = tmp_path / "ohlcv.parquet"
    raw_ohlcv_path = tmp_path / "raw_ohlcv.parquet"
    listed_path = tmp_path / "listed.parquet"
    asof_path = tmp_path / "historical_asof_view.json"
    pit_manifest_path = tmp_path / "pit_manifest.json"
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": symbol.upper(), "Open": 1000.0} for symbol in symbols]).to_parquet(ohlcv_path, index=False)
    raw_rows = [
        {"Date": BUSINESS_DATE, "Code": symbol.upper(), "AdjFactor": 0.5 if target_corporate_action else 1.0}
        for symbol in symbols
    ]
    if unrelated_corporate_action:
        raw_rows.append({"Date": BUSINESS_DATE, "Code": "99990", "AdjFactor": 0.5})
    pd.DataFrame(raw_rows).to_parquet(raw_ohlcv_path, index=False)
    pd.DataFrame([{"Date": selected_snapshot_date, "Code": symbol.upper(), "ProdCat": "011", "MktNm": "東証"} for symbol in symbols]).to_parquet(listed_path, index=False)
    pit_manifest_path.write_text(
        json.dumps({"entries": [{"business_date": BUSINESS_DATE, "source_hashes": {"ohlcv_normalized": _sha(ohlcv_path)}}]}),
        encoding="utf-8",
    )
    asof_path.write_text(
        json.dumps(
            {
                "business_date": BUSINESS_DATE,
                "authorities": [
                    {
                        "authority": "listed_issues",
                        "status": "PASS",
                        "business_date": BUSINESS_DATE,
                        "physical_source_path": str(listed_path),
                        "physical_source_hash": _sha(listed_path),
                        "physical_row_count": len(symbols),
                        "selected_snapshot_date": selected_snapshot_date,
                        "selection_policy": "latest_snapshot_not_after_business_date",
                        "snapshot_age_days": 0,
                    },
                    {
                        "authority": "normalized_ohlcv",
                        "status": "PASS",
                        "business_date": BUSINESS_DATE,
                        "physical_source_path": str(ohlcv_path),
                        "physical_source_hash": _sha(ohlcv_path),
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return (
        HistoricalSubmitAdapter(
            runtime_root=tmp_path / ".runtime",
            business_date=BUSINESS_DATE,
            evaluation_time=EVALUATION_TIME,
            pit_manifest_path=pit_manifest_path,
            historical_asof_view_path=asof_path,
            ohlcv_path=ohlcv_path,
            listed_issues_path=tmp_path / "legacy_listed.parquet",
            raw_ohlcv_path=raw_ohlcv_path,
        ),
        listed_path,
    )


def _command(
    symbol: str,
    *,
    environment: str = "historical",
    listed_info_code: str | None = None,
    current_listed: bool = True,
) -> RuntimeV2SubmitCommand:
    return RuntimeV2SubmitCommand(
        command_id=f"command-{symbol}",
        environment=environment,
        pending_plan_id="pending-plan-bv8",
        pending_item_id=f"item-{symbol}",
        approval_hash="approval-hash",
        symbol=symbol,
        side="BUY",
        quantity=100.0,
        order_type="MARKET",
        price_type="MARKET",
        limit_price=0.0,
        estimated_amount=100000.0,
        target_session_date=BUSINESS_DATE,
        live_order_allowed=True,
        listed_info={"code": listed_info_code or symbol, "current_listed": current_listed, "trading_unit": 100},
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
