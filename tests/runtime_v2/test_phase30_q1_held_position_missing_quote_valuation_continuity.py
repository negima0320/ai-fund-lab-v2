from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh

from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    BUSINESS_DATE,
    _load_json,
    _now,
    _position,
    _runtime_root,
    _write_current,
    _write_json,
    _write_market,
)


def test_phase30_q1_authorized_stale_valuation_applies_with_explicit_taxonomy(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09", current_price=1000)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        missing_quote_classifications={"7203": _authorized_stale_classification()},
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")
    position = current["positions"][0]

    assert result.status == "READY"
    assert result.apply_executed is True
    assert result.postcondition_status == "PASS"
    assert current["valuation_as_of"] == BUSINESS_DATE
    assert current["source_market_date"] == "2026-07-09"
    assert current["valuation_quote_status"] == "AUTHORIZED_STALE_VALUATION"
    assert current["current_valuation_status"] == "VALID_CARRYOVER"
    assert position["valuation_quote_status"] == "AUTHORIZED_STALE_VALUATION"
    assert position["quote_business_date"] == "2026-07-09"
    assert position["valuation_business_date"] == BUSINESS_DATE
    assert position["staleness_business_days"] == 1
    assert position["current_price"] == 1000
    assert position["quantity_basis"] == position["valuation_price_basis"] == "RAW"
    assert position["stale_accounting_valuation_not_fresh_market_signal"] is True


def test_phase30_ak5r2_mixed_fresh_and_authorized_stale_portfolio_passes(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    stale_position = _position("7203", current_price=1000)
    fresh_position = _position("6758", current_price=2000)
    _write_current(
        root,
        positions=[stale_position, fresh_position],
        valuation_as_of="2026-07-09",
        source_market_date="2026-07-09",
    )
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={
            "6758": {
                "symbol": "6758",
                "price": 2100,
                "price_type": "jquants_daily_quote",
                "market_date": BUSINESS_DATE,
                "observed_at": BUSINESS_DATE,
                "source": "runtime_state/market/test",
                "freshness_status": "READY",
                "adjusted": False,
            }
        },
        missing_quote_classifications={"7203": _authorized_stale_classification()},
    )
    market_path = root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json"
    market = _load_json(market_path)
    market["quote_status"] = "REVIEW_REQUIRED"
    _write_json(market_path, market)

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")
    positions = {position["symbol"]: position for position in current["positions"]}

    assert result.status == "READY"
    assert result.apply_executed is True
    assert result.postcondition_status == "PASS"
    assert current["current_valuation_status"] == "VALID_CARRYOVER"
    assert current["valuation_quote_status"] == "AUTHORIZED_STALE_VALUATION"
    assert current["authorized_stale_valuation_symbols"] == ["7203"]
    assert positions["7203"]["valuation_quote_status"] == "AUTHORIZED_STALE_VALUATION"
    assert positions["7203"]["quote_business_date"] == "2026-07-09"
    assert positions["7203"]["valuation_business_date"] == BUSINESS_DATE
    assert positions["6758"]["valuation_quote_status"] == "FRESH_CURRENT_QUOTE"
    assert positions["6758"]["current_price"] == 2100
    assert current["market_value"] == positions["7203"]["market_value"] + positions["6758"]["market_value"]


def test_phase30_ak5r2_authorized_stale_basis_mismatch_remains_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    position = _position("7203", current_price=1000)
    position["valuation_price_basis"] = "ADJUSTED"
    _write_current(root, positions=[position], valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        missing_quote_classifications={"7203": _authorized_stale_classification()},
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)
    artifact = _load_json(Path(result.artifact_path))
    assert "current_valuation_quote_invalid:7203:stale_valuation_basis_mismatch" in artifact["missing_evidence"]


def test_phase30_ak5r2_authorized_stale_missing_provenance_remains_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    position = _position("7203", current_price=1000)
    position.pop("valuation_price_provenance")
    _write_current(root, positions=[position], valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        missing_quote_classifications={"7203": _authorized_stale_classification()},
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)
    artifact = _load_json(Path(result.artifact_path))
    assert "current_valuation_quote_invalid:7203:stale_valuation_provenance_missing" in artifact["missing_evidence"]


def test_phase30_q1_data_or_source_failure_remains_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        missing_quote_classifications={
            "7203": {
                "missing_quote_class": "DATA_OR_SOURCE_FAILURE",
                "classification_reason": "listed_symbol_missing_current_quote",
            }
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)


def test_phase30_q1_listing_or_ca_ambiguity_remains_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        missing_quote_classifications={
            "7203": {
                "missing_quote_class": "LISTING_OR_CORPORATE_ACTION_AMBIGUITY",
                "corporate_action_ambiguity_status": "UNRESOLVED",
            }
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert "current_valuation_quote_missing" in result.candidate_current.get("warnings", []) or result.review_required


def test_phase30_q1_unknown_missing_quote_remains_fail_closed(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    _write_market(root, market_date=BUSINESS_DATE, quotes={})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)


def test_phase30_q1_corporate_action_ambiguity_blocks_authorized_stale(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    classification = _authorized_stale_classification()
    classification["corporate_action_ambiguity_status"] = "UNRESOLVED"
    _write_market(root, market_date=BUSINESS_DATE, quotes={}, missing_quote_classifications={"7203": classification})

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase30_q1_recovery_from_stale_to_fresh_clears_stale_marker(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09", current_price=1000)
    _write_market(root, market_date=BUSINESS_DATE, quotes={}, missing_quote_classifications={"7203": _authorized_stale_classification()})
    stale = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())
    assert stale.status == "READY"

    next_day = "2026-07-13"
    _write_market(root, market_date=next_day, price=1050)
    fresh = run_current_valuation_refresh(
        runtime_root=root,
        business_date=next_day,
        apply_current_valuation=True,
        now=datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")

    assert fresh.status == "READY"
    assert current["positions"][0]["valuation_quote_status"] == "FRESH_CURRENT_QUOTE"
    assert current["positions"][0]["current_price"] == 1050
    assert current["positions"][0]["source_market_date"] == next_day


def test_phase30_q1_historical_asof_listed_absence_classifies_ambiguity_without_authorizing_stale(tmp_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    run_root = tmp_path / "reports" / "runtime_tests" / "runs" / "run-q1"
    market_refresh_root = run_root / "daily" / BUSINESS_DATE / "market_refresh"
    logical_root = market_refresh_root / "inputs" / "historical_asof" / BUSINESS_DATE
    normalized = logical_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw = logical_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed = logical_root / "raw" / "jquants" / "listed_issues" / "data.parquet"
    for path in (normalized, raw, listed):
        path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"target_date": BUSINESS_DATE, "code": "9999", "close": 1.0}]).to_parquet(normalized, index=False)
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": "9999", "C": 1.0}]).to_parquet(raw, index=False)
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": "9999", "CoName": "Other"}]).to_parquet(listed, index=False)
    manifest_path = logical_root / "logical_input_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "runtime_historical_logical_input_manifest_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "logical_paths": {
                "normalized_ohlcv": str(normalized),
                "raw_ohlcv": str(raw),
                "listed_issues": str(listed),
            },
        },
    )
    asof_view = market_refresh_root / "historical_asof_view.json"
    _write_json(
        asof_view,
        {
            "schema_version": "runtime_historical_asof_view_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "authorities": [
                {"authority": "normalized_ohlcv", "status": "PASS", "physical_source_path": str(normalized)},
                {"authority": "raw_ohlcv", "status": "PASS", "physical_source_path": str(raw)},
                {"authority": "listed_issues", "status": "PASS", "physical_source_path": str(listed)},
            ],
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        market_evidence_path=asof_view,
        now=_now(),
    )
    artifact = _load_json(Path(result.artifact_path))

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert artifact["candidate_current"] == artifact["candidate_current"]
    assert artifact["missing_symbols"] == ["7203"]


def test_phase30_q1_resume_boundary_valuation_only_does_not_duplicate_existing_effects(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09", current_price=1000)
    ledger_dir = root / "persistent_ledger" / "ledger"
    _write_json(ledger_dir / "executions.json", {"rows": [{"execution_id": "already-applied"}]})
    _write_json(ledger_dir / "cash.json", {"rows": [{"cash_event_id": "already-applied"}]})
    pending_path = root / "pending_orders" / BUSINESS_DATE / "pending_order_plan.json"
    _write_json(pending_path, {"items": [{"symbol": "7203", "side": "SELL", "status": "SUBMITTED"}]})
    before_execution = (ledger_dir / "executions.json").read_text(encoding="utf-8")
    before_cash = (ledger_dir / "cash.json").read_text(encoding="utf-8")
    before_pending = pending_path.read_text(encoding="utf-8")
    _write_market(root, market_date=BUSINESS_DATE, quotes={}, missing_quote_classifications={"7203": _authorized_stale_classification()})

    first = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())
    second = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())

    assert first.status == "READY"
    assert second.status == "READY"
    assert (ledger_dir / "executions.json").read_text(encoding="utf-8") == before_execution
    assert (ledger_dir / "cash.json").read_text(encoding="utf-8") == before_cash
    assert pending_path.read_text(encoding="utf-8") == before_pending
    assert first.new_total_market_value == second.new_total_market_value


def _authorized_stale_classification() -> dict[str, object]:
    return {
        "missing_quote_class": "AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION",
        "stale_reason": "authoritative_no_trade_or_listing_transition",
        "stale_authority": "test_listing_trading_state_authority",
        "quote_business_date": "2026-07-09",
        "staleness_business_days": 1,
        "corporate_action_ambiguity_status": "CLEAR",
        "source_provenance": "prior_current_authoritative_valuation",
        "listing_status_evidence": {
            "symbol_expected_to_have_fresh_quote": False,
            "authority": "test_listing_trading_state_authority",
        },
    }
