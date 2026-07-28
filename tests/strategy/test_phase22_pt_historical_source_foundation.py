from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.strategy.historical_source_foundation import (
    build_historical_strategy_preflight,
    build_materialization_manifest,
    build_source_coverage_inventory,
)
from ai_fund_lab_v2.strategy.source_manifest import build_strategy_source_manifest


def test_phase22_pt_inventory_calculates_min_max_and_empty_source(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime", start="2026-07-01", days=5)
    inventory = build_source_coverage_inventory(runtime_root=runtime_root)
    quotes = _source(inventory, "daily_quotes")
    actions = _source(inventory, "corporate_actions")

    assert quotes["min_business_date"] == "2026-07-01"
    assert quotes["max_business_date"] == "2026-07-07"
    assert quotes["row_count"] > 0
    assert quotes["symbol_count"] == 2
    assert actions["pit_usability"] == "SOURCE_UNAVAILABLE"


def test_phase22_pt_start_date_eligibility_and_no_silent_shift(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime", start="2026-06-01", days=35)
    early = build_historical_strategy_preflight(runtime_root=runtime_root, requested_start_date="2026-05-29", requested_business_days=1)
    warmup = build_historical_strategy_preflight(runtime_root=runtime_root, requested_start_date="2026-06-02", requested_business_days=1)
    eligible = build_historical_strategy_preflight(runtime_root=runtime_root, requested_start_date="2026-07-06", requested_business_days=1)

    assert early["requested_start_date"] == "2026-05-29"
    assert early["judgment"] == "NOT_ELIGIBLE_SOURCE_COVERAGE"
    assert early["first_eligible_start_date"] == "2026-07-06"
    assert warmup["market_coverage"]["status"] == "BOOTSTRAP_REQUIRED"
    assert "daily_quotes_required_warmup_insufficient" in warmup["market_coverage"]["reason_codes"]
    assert eligible["judgment"] == "ELIGIBLE"
    assert eligible["operator_ready"] is True


def test_phase22_pt_sector_and_corporate_event_contracts(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime", start="2026-06-01", days=35)
    preflight = build_historical_strategy_preflight(runtime_root=runtime_root, requested_start_date="2026-07-06", requested_business_days=1)

    assert preflight["sector_coverage"]["sector_pit_available"] is True
    assert preflight["sector_coverage"]["sector_fallback_used"] is False
    assert preflight["corporate_event_coverage"]["overall_event_coverage"] == "PARTIAL"
    assert "SOURCE_PARTIAL" in preflight["corporate_event_coverage"]["event_states_supported"]


def test_phase22_pt_candidate_opportunity_date_binding_and_no_latest_fallback(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime", start="2026-06-01", days=35)
    missing = build_historical_strategy_preflight(runtime_root=runtime_root, requested_start_date="2026-07-07", requested_business_days=1)

    assert missing["candidate_generation_readiness"]["status"] == "NOT_ELIGIBLE_SOURCE_COVERAGE"
    assert missing["candidate_generation_readiness"]["latest_fallback_used"] is False
    assert missing["opportunity_generation_readiness"]["latest_fallback_used"] is False


def test_phase22_pt_runtime_root_isolation_ignores_active_state(tmp_path: Path) -> None:
    active_root = _runtime_root(tmp_path / "active", start="2026-06-01", days=35)
    isolated_root = _runtime_root(tmp_path / "isolated", start="2026-06-01", days=35)
    _write_json(active_root / "persistent_ledger" / "state.json", {"business_date": "2099-01-01", "cash": 1.0, "positions": []})
    _write_json(isolated_root / "persistent_ledger" / "state.json", {"business_date": "2026-07-06", "cash": 1000000.0, "positions": []})

    manifest = build_strategy_source_manifest(
        run_dir=tmp_path / "run",
        runtime_root=isolated_root,
        run_id="isolated-run",
        profile_id="historical-smoke",
        business_date="2026-07-06",
        strategy_dir=tmp_path / "run" / "daily" / "2026-07-06" / "strategy",
        input_manifest={},
    )

    assert manifest["portfolio_state"]["path"].startswith(str(isolated_root))
    assert manifest["portfolio_state"]["payload_business_date"] == "2026-07-06"
    assert manifest["pit_validation"]["current_state_leakage_detected"] is False


def test_phase22_pt_materialization_manifest_reuses_canonical_sources(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path / "runtime", start="2026-06-01", days=35)
    manifest = build_materialization_manifest(runtime_root=runtime_root)

    assert manifest["source_authority"] == "J_QUANTS_CANONICAL_DATA"
    assert manifest["pit_contract"]["future_rows_allowed_in_selection"] is False
    assert any(item["source_name"] == "daily_quotes" and item["materialization_strategy"] == "REUSE_EXISTING_CANONICAL_SOURCE" for item in manifest["outputs"])


def _runtime_root(root: Path, *, start: str, days: int) -> Path:
    _write_parquet_sources(root, start=start, days=days)
    _write_json(root / "runtime_state" / "accepted_buy_ai_bundle.json", {"accepted_generation_id": "accepted-fixture", "resolution_status": "RESOLVED_COMMITTED"})
    _write_json(root / "persistent_ledger" / "state.json", {"business_date": "2026-07-06", "cash": 1000000.0, "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"business_date": "2026-07-06", "items": []})
    for day in ("2026-07-06",):
        _write_json(root / "runtime_state" / "buy_ai" / day / "candidate_decisions.json", {"business_date": day, "accepted_generation_id": "accepted-fixture", "decisions": []})
        _write_json(root / "runtime_state" / "buy_ai" / day / "opportunity_rankings.json", {"business_date": day, "accepted_generation_id": "accepted-fixture", "rankings": []})
    return root


def _write_parquet_sources(root: Path, *, start: str, days: int) -> None:
    calendar_dates = _business_dates(start, days)
    quote_rows = [{"target_date": day, "code": code, "Close": 100.0 + idx, "Volume": 1000 + idx} for idx, day in enumerate(calendar_dates) for code in ("1001", "1002")]
    listed_rows = [{"target_date": day, "code": code, "S33Nm": sector, "MktNm": "Prime", "ListedStatus": "LISTED"} for day in calendar_dates if day >= "2026-07-06" for code, sector in (("1001", "Tech"), ("1002", "Retail"))]
    calendar_path = root / "operations" / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet"
    quotes_path = root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed_path = root / "operations" / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet"
    calendar_path.parent.mkdir(parents=True, exist_ok=True)
    quotes_path.parent.mkdir(parents=True, exist_ok=True)
    listed_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"target_date": day, "HolDiv": "1"} for day in calendar_dates]).to_parquet(calendar_path)
    pd.DataFrame(quote_rows).to_parquet(quotes_path)
    pd.DataFrame(listed_rows).to_parquet(listed_path)


def _business_dates(start: str, days: int) -> list[str]:
    cursor = date.fromisoformat(start)
    result: list[str] = []
    while len(result) < days:
        if cursor.weekday() < 5:
            result.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return result


def _source(inventory: dict, name: str) -> dict:
    return next(item for item in inventory["sources"] if item["name"] == name)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
