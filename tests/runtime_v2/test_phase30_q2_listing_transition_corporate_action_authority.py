from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh

from tests.runtime_v2.test_phase15az_current_valuation_no_fill_producer import (
    BUSINESS_DATE,
    _load_json,
    _now,
    _runtime_root,
    _write_current,
    _write_json,
    _write_market,
)


def test_phase30_q2_normal_listed_fresh_quote_remains_ready(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "READY"
    assert result.candidate_current["positions"][0]["valuation_quote_status"] == "FRESH_CURRENT_QUOTE"


def test_phase30_q2_listed_symbol_missing_quote_is_data_source_failure(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(state="CURRENTLY_LISTED"),
        corporate_action_ambiguity_authority=_ca_authority(status="CLEAR"),
    )

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())
    artifact = _load_json(Path(result.artifact_path))

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)
    assert artifact["missing_symbols"] == ["7203"]
    market = _load_json(Path(result.market_evidence_path))
    assert market["listing_state_authority"]["by_symbol"]["7203"]["listing_state"] == "CURRENTLY_LISTED"


def test_phase30_q2_previous_listed_current_absent_unknown_remains_ambiguity(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(
            state="PREVIOUSLY_LISTED_CURRENT_ABSENT",
            transition_status="UNKNOWN",
            stale_allowed=False,
        ),
        corporate_action_ambiguity_authority=_ca_authority(status="CLEAR"),
        tradability_authority=_tradability_authority(status="AUTHORITY_UNAVAILABLE"),
    )

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)


def test_phase30_q2_authorized_listing_transition_allows_stale_valuation(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09", current_price=1000)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(
            state="LISTING_TRANSITION_CONFIRMED",
            transition_status="CONFIRMED",
            transition_reason="authoritative_no_current_quote_after_listing_transition",
            stale_allowed=True,
        ),
        corporate_action_ambiguity_authority=_ca_authority(status="CLEAR"),
        tradability_authority=_tradability_authority(status="AUTHORIZED_NO_CURRENT_QUOTE", stale_allowed=True),
    )

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())
    current = _load_json(root / "persistent_ledger" / "state.json")
    position = current["positions"][0]

    assert result.status == "READY"
    assert result.apply_executed is True
    assert current["current_valuation_status"] == "VALID_CARRYOVER"
    assert current["authorized_stale_valuation_symbols"] == ["7203"]
    assert position["valuation_quote_status"] == "AUTHORIZED_STALE_VALUATION"
    assert position["quote_business_date"] == "2026-07-09"
    assert position["valuation_business_date"] == BUSINESS_DATE
    assert position["corporate_action_ambiguity_status"] == "CLEAR"
    assert position["quantity_basis"] == position["valuation_price_basis"] == "RAW"
    assert position["stale_accounting_valuation_not_fresh_market_signal"] is True


def test_phase30_ak5r_listed_no_valid_close_with_ca_clear_authorizes_stale_valuation(tmp_path: Path) -> None:
    pd = _optional_pandas()
    if pd is None:
        return

    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2022-10-20", source_market_date="2022-10-20", current_price=613)
    _materialize_position_valuation_metadata(root, valuation_date="2022-10-20", source_market_date="2022-10-20")
    run_root = tmp_path / "reports" / "runtime_tests" / "runs" / "ak5r"
    asof_view = _write_historical_asof_with_no_valid_close(
        run_root=run_root,
        pd=pd,
        business_date=BUSINESS_DATE,
        symbol="7203",
    )
    _write_json(
        run_root / "daily" / BUSINESS_DATE / "strategy" / "corporate_event.json",
        {
            "symbol_event_facts": [
                {
                    "security_code": "7203",
                    "business_date": BUSINESS_DATE,
                    "event_status": "KNOWN_NO_EVENT",
                    "coverage_status": "AVAILABLE",
                    "event_dates": [],
                    "event_types": [],
                }
            ]
        },
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        market_evidence_path=asof_view,
        now=_now(),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")
    position = current["positions"][0]

    assert result.status == "READY"
    assert result.apply_executed is True
    assert current["current_valuation_status"] == "VALID_CARRYOVER"
    assert current["authorized_stale_valuation_symbols"] == ["7203"]
    assert position["current_price"] == 613
    assert position["source_market_date"] == "2022-10-20"
    assert position["valuation_business_date"] == BUSINESS_DATE
    assert position["valuation_quote_status"] == "AUTHORIZED_STALE_VALUATION"
    assert position["corporate_action_ambiguity_status"] == "CLEAR"
    assert position["stale_authority"] == "pit_listed_raw_no_valid_close_corporate_event_authority"


def test_phase30_ak5r_listed_no_valid_close_without_ca_clear_remains_fail_closed(tmp_path: Path) -> None:
    pd = _optional_pandas()
    if pd is None:
        return

    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2022-10-20", source_market_date="2022-10-20", current_price=613)
    _materialize_position_valuation_metadata(root, valuation_date="2022-10-20", source_market_date="2022-10-20")
    run_root = tmp_path / "reports" / "runtime_tests" / "runs" / "ak5r-ca-block"
    asof_view = _write_historical_asof_with_no_valid_close(
        run_root=run_root,
        pd=pd,
        business_date=BUSINESS_DATE,
        symbol="7203",
    )

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        market_evidence_path=asof_view,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False
    assert result.missing_symbols == ("7203",)


def test_phase30_q2_ca_coverage_incomplete_blocks_stale_authorization(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(state="LISTING_TRANSITION_CONFIRMED", transition_status="CONFIRMED", stale_allowed=True),
        corporate_action_ambiguity_authority=_ca_authority(status="COVERAGE_INCOMPLETE"),
        tradability_authority=_tradability_authority(status="AUTHORIZED_NO_CURRENT_QUOTE", stale_allowed=True),
    )

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase30_q2_unresolved_ca_blocks_stale_authorization(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(state="LISTING_TRANSITION_CONFIRMED", transition_status="CONFIRMED", stale_allowed=True),
        corporate_action_ambiguity_authority=_ca_authority(status="UNRESOLVED"),
        tradability_authority=_tradability_authority(status="AUTHORIZED_NO_CURRENT_QUOTE", stale_allowed=True),
    )

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase30_q2_stale_to_fresh_recovery_clears_authority_marker(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09", current_price=1000)
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(state="LISTING_TRANSITION_CONFIRMED", transition_status="CONFIRMED", stale_allowed=True),
        corporate_action_ambiguity_authority=_ca_authority(status="CLEAR"),
        tradability_authority=_tradability_authority(status="AUTHORIZED_NO_CURRENT_QUOTE", stale_allowed=True),
    )
    stale = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())
    assert stale.status == "READY"

    next_day = "2026-07-13"
    _write_market(root, market_date=next_day, price=1055)
    fresh = run_current_valuation_refresh(
        runtime_root=root,
        business_date=next_day,
        apply_current_valuation=True,
        now=datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc),
    )

    current = _load_json(root / "persistent_ledger" / "state.json")
    assert fresh.status == "READY"
    assert current["positions"][0]["valuation_quote_status"] == "FRESH_CURRENT_QUOTE"
    assert current["positions"][0]["source_market_date"] == next_day


def test_phase30_q2_resume_valuation_only_does_not_duplicate_prior_effects(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-09", source_market_date="2026-07-09")
    ledger_dir = root / "persistent_ledger" / "ledger"
    pending_path = root / "pending_orders" / BUSINESS_DATE / "pending_order_plan.json"
    _write_json(ledger_dir / "executions.json", {"rows": [{"execution_id": "already-applied"}]})
    _write_json(ledger_dir / "cash.json", {"rows": [{"cash_event_id": "already-applied"}]})
    _write_json(pending_path, {"items": [{"symbol": "7203", "side": "SELL", "status": "SUBMITTED"}]})
    before_execution = (ledger_dir / "executions.json").read_text(encoding="utf-8")
    before_cash = (ledger_dir / "cash.json").read_text(encoding="utf-8")
    before_pending = pending_path.read_text(encoding="utf-8")
    _write_market(
        root,
        market_date=BUSINESS_DATE,
        quotes={},
        listing_state_authority=_listing_authority(state="LISTING_TRANSITION_CONFIRMED", transition_status="CONFIRMED", stale_allowed=True),
        corporate_action_ambiguity_authority=_ca_authority(status="CLEAR"),
        tradability_authority=_tradability_authority(status="AUTHORIZED_NO_CURRENT_QUOTE", stale_allowed=True),
    )

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, apply_current_valuation=True, now=_now())

    assert result.status == "READY"
    assert (ledger_dir / "executions.json").read_text(encoding="utf-8") == before_execution
    assert (ledger_dir / "cash.json").read_text(encoding="utf-8") == before_cash
    assert pending_path.read_text(encoding="utf-8") == before_pending


def _listing_authority(
    *,
    state: str,
    transition_status: str = "",
    transition_reason: str = "authoritative_no_current_quote_after_listing_transition",
    stale_allowed: bool = False,
) -> dict[str, object]:
    return {
        "owner": "Market Evidence / PIT Listed Issues Authority",
        "producer": "runtime_v2_market_evidence",
        "status": "PASS",
        "business_date": BUSINESS_DATE,
        "by_symbol": {
            "7203": {
                "listing_state": state,
                "listing_transition_status": transition_status,
                "listing_transition_reason": transition_reason,
                "last_listed_business_date": "2026-07-09",
                "staleness_business_days": 1,
                "stale_valuation_allowed": stale_allowed,
                "authority": "pit_listed_issues_transition_authority",
                "source_provenance": "pit_listed_issues:test",
            }
        },
    }


def _ca_authority(*, status: str) -> dict[str, object]:
    return {
        "owner": "Corporate Event Authority",
        "producer": "strategy.corporate_event",
        "coverage_status": "AVAILABLE" if status == "CLEAR" else "PARTIAL",
        "by_symbol": {
            "7203": {
                "corporate_action_ambiguity_status": status,
                "coverage_status": "AVAILABLE" if status == "CLEAR" else "PARTIAL",
                "unresolved_event_count": 0 if status == "CLEAR" else 1,
            }
        },
    }


def _tradability_authority(*, status: str, stale_allowed: bool = False) -> dict[str, object]:
    return {
        "owner": "Market Evidence / Tradability Authority",
        "producer": "runtime_v2_market_evidence",
        "status": "PASS" if status != "AUTHORITY_UNAVAILABLE" else "AUTHORITY_UNAVAILABLE",
        "by_symbol": {
            "7203": {
                "tradability_status": status,
                "stale_valuation_allowed": stale_allowed,
                "authority": "pit_tradability_authority",
            }
        },
    }


def _optional_pandas():
    try:
        import pandas as pd
    except ImportError:
        return None
    return pd


def _write_historical_asof_with_no_valid_close(
    *,
    run_root: Path,
    pd,
    business_date: str,
    symbol: str,
) -> Path:
    market_refresh_root = run_root / "daily" / business_date / "market_refresh"
    logical_root = market_refresh_root / "inputs" / "historical_asof" / business_date
    normalized = logical_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw = logical_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed = logical_root / "raw" / "jquants" / "listed_issues" / "data.parquet"
    for path in (normalized, raw, listed):
        path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": business_date, "Code": "9999", "Close": 1.0, "target_date": business_date, "code": "9999"}]).to_parquet(
        normalized,
        index=False,
    )
    pd.DataFrame(
        [
            {
                "Date": business_date,
                "Code": symbol,
                "O": None,
                "H": None,
                "L": None,
                "C": None,
                "AdjC": None,
                "target_date": business_date,
                "code": symbol,
            }
        ]
    ).to_parquet(raw, index=False)
    pd.DataFrame([{"Date": business_date, "Code": symbol, "CoName": "No Valid Close Co"}]).to_parquet(listed, index=False)
    _write_json(
        logical_root / "logical_input_manifest.json",
        {
            "schema_version": "runtime_historical_logical_input_manifest_v1",
            "status": "PASS",
            "business_date": business_date,
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
            "business_date": business_date,
            "latest_available_market_date": business_date,
            "future_rows_excluded_from_consumer": True,
            "authorities": [
                {"authority": "normalized_ohlcv", "status": "PASS", "physical_source_path": str(normalized)},
                {"authority": "raw_ohlcv", "status": "PASS", "physical_source_path": str(raw)},
                {"authority": "listed_issues", "status": "PASS", "physical_source_path": str(listed)},
            ],
        },
    )
    return asof_view


def _materialize_position_valuation_metadata(root: Path, *, valuation_date: str, source_market_date: str) -> None:
    current_path = root / "persistent_ledger" / "state.json"
    current = _load_json(current_path)
    for position in current.get("positions") or []:
        position["valuation_as_of"] = valuation_date
        position["source_market_date"] = source_market_date
        position["valuation_source"] = "prior_authoritative_current"
        position["valuation_price_type"] = "jquants_daily_quote"
        position["valuation_quote_status"] = "FRESH_CURRENT_QUOTE"
        position["quote_business_date"] = source_market_date
        position["valuation_business_date"] = valuation_date
    _write_json(current_path, current)
