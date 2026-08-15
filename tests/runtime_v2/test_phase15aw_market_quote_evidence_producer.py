from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from ai_fund_lab_v2.runtime_v2.data_readiness import _market_readiness_payload
from ai_fund_lab_v2.runtime_v2.market_refresh.evidence import produce_market_quote_evidence
from ai_fund_lab_v2.runtime_v2.safety.evaluation import run_runtime_safety_evaluation
from ai_fund_lab_v2.runtime_v2.temporal import PublicationWindow


BUSINESS_DATE = "2026-07-10"
JST = ZoneInfo("Asia/Tokyo")


def test_phase15aw_normal_market_evidence_ready_and_quote_schema(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, BUSINESS_DATE, symbols=("7203", "6758"))

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        now=_now(),
    )
    payload = _load_json(Path(result.artifact_path))

    assert result.status == "READY"
    assert payload["runtime_business_date"] == BUSINESS_DATE
    assert payload["market_date"] == BUSINESS_DATE
    assert payload["latest_expected_trading_date"] == BUSINESS_DATE
    assert payload["latest_available_market_date"] == BUSINESS_DATE
    assert payload["market_summary"]["quote_count"] == 2
    quote = payload["quotes"]["7203"]
    assert set(("symbol", "price", "price_type", "market_date", "observed_at", "source", "freshness_status", "adjusted")) <= set(quote)
    assert quote["price_type"] == "jquants_daily_quote"
    assert payload["no_feature_artifact_price_derivation"] is True
    assert "feature_artifacts" not in quote["source"]


def test_phase29_l21t_be_market_evidence_marks_adjusted_price_as_unreconciled_analytical(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(
        operations_root,
        BUSINESS_DATE,
        rows=[
            {
                "target_date": BUSINESS_DATE,
                "code": "67310",
                "close": 3000.0,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        current_symbols=("67310",),
        now=_now(),
    )
    payload = _load_json(Path(result.artifact_path))
    quote = payload["quotes"]["6731"]

    assert result.status == "READY"
    assert quote["adjusted"] is True
    assert quote["price_role"] == "adjusted_analytical_price"
    assert quote["economic_price_reconciliation_status"] == "REVIEW_REQUIRED"
    assert quote["normalized_price_source"] == "adjusted"


def test_phase29_l21t_bh_market_evidence_reconciles_adjusted_quote_from_raw_economic_source(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(
        operations_root,
        BUSINESS_DATE,
        rows=[
            {
                "target_date": BUSINESS_DATE,
                "code": "94320",
                "close": 149.8,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )
    _write_raw_daily_quotes(
        operations_root,
        BUSINESS_DATE,
        rows=[
            {
                "Date": BUSINESS_DATE,
                "Code": "94320",
                "C": 3744.0,
                "AdjC": 149.8,
            }
        ],
    )

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        current_symbols=("9432",),
        now=_now(),
    )
    payload = _load_json(Path(result.artifact_path))
    quote = payload["quotes"]["9432"]

    assert result.status == "READY"
    assert quote["adjusted"] is True
    assert quote["price"] == 149.8
    assert quote["price_role"] == "reconciled_raw_economic_valuation_price"
    assert quote["economic_price_reconciliation_status"] == "PASS"
    assert quote["economic_valuation_price"] == 3744.0
    assert quote["adjusted_analytical_price"] == 149.8
    assert "raw_ohlcv_close:" in quote["economic_price_provenance"]


def test_phase15aw_data_readiness_reads_formal_market_artifact(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, BUSINESS_DATE, symbols=("7203",))
    produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        now=_now(),
    )

    payload = _market_readiness_payload(root=runtime_root, business_date=BUSINESS_DATE, market_open=True, override=False)

    assert payload["status"] == "READY"
    assert payload["market_data_status"] == "READY"
    assert payload["quote_status"] == "READY"
    assert payload["market_summary_status"] == "READY"
    assert payload["market_date"] == BUSINESS_DATE


def test_phase15aw_safety_consumer_can_read_market_and_quote_evidence(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, BUSINESS_DATE, symbols=("7203",))
    produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        current_symbols=("7203",),
        now=_now(),
    )
    _write_safety_inputs(runtime_root)

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status in {"PASS", "REVIEW_REQUIRED"}
    assert "market" not in result.manifest_fields["missing_evidence"]


def test_phase15aw_before_publication_window_is_data_not_yet_available(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, "2026-07-09", symbols=("7203",))
    window = PublicationWindow(
        expected_available_at=datetime(2026, 7, 10, 15, 30, tzinfo=JST),
        grace_period=timedelta(minutes=30),
    )

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date="2026-07-09",
        publication_window=window,
        now=datetime(2026, 7, 10, 10, 0, tzinfo=JST),
    )
    payload = _load_json(Path(result.artifact_path))

    assert result.status == "DATA_NOT_YET_AVAILABLE"
    assert payload["data_not_yet_available"] is True
    assert payload["quotes"] == {}


def test_phase15aw_after_publication_grace_is_stale(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, "2026-07-09", symbols=("7203",))
    window = PublicationWindow(
        expected_available_at=datetime(2026, 7, 10, 15, 30, tzinfo=JST),
        grace_period=timedelta(minutes=30),
    )

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date="2026-07-09",
        publication_window=window,
        now=datetime(2026, 7, 10, 18, 0, tzinfo=JST),
    )

    assert result.status == "STALE"
    assert result.stale is True


def test_phase15aw_non_trading_day_previous_data_is_valid_carryover(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, "2026-07-10", symbols=("7203",))

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date="2026-07-11",
        latest_available_market_date="2026-07-10",
        now=datetime(2026, 7, 11, 9, 0, tzinfo=JST),
    )

    assert result.status == "READY"
    assert result.market_freshness_status == "VALID_CARRYOVER"
    assert result.market_date == "2026-07-10"


def test_phase15aw_api_error_generates_review_required_artifact(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, BUSINESS_DATE, symbols=("7203",))

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        provider_status="API_ERROR",
        now=_now(),
    )
    payload = _load_json(Path(result.artifact_path))

    assert result.status == "REVIEW_REQUIRED"
    assert payload["provider_status"] == "API_ERROR"


def test_phase15aw_missing_monitored_quote_requires_review(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, BUSINESS_DATE, symbols=("7203",))

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date=BUSINESS_DATE,
        current_symbols=("9999",),
        now=_now(),
    )
    payload = _load_json(Path(result.artifact_path))

    assert result.status == "REVIEW_REQUIRED"
    assert result.quote_status == "REVIEW_REQUIRED"
    assert payload["missing_quote_symbols"] == ["9999"]


def test_phase20_bl_historical_quote_source_override_uses_resolver_logical_input(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    operations_source = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    operations_source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"target_date": "2026-07-10", "code": "9999", "close": 1.0}]).to_parquet(operations_source, index=False)
    logical_source = tmp_path / "run" / "inputs" / "historical_asof" / "2022-08-01" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    logical_source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": "2022-08-01", "Code": "72030", "Close": 1000.0}]).to_parquet(logical_source, index=False)

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date="2022-08-01",
        latest_available_market_date="2022-08-01",
        mode="historical",
        quote_source_path=logical_source,
        source_authority={
            "runtime_mode": "historical",
            "source_role": "acquisition_staging",
            "quote_source_authority": "physical/acquisition/data.parquet",
            "logical_cutoff": "2022-08-01",
            "source_business_date": "2022-08-01",
            "historical_asof_status": "PASS",
            "historical_logical_input_manifest_path": "logical_input_manifest.json",
            "historical_logical_input_manifest_hash": "sha256",
            "future_rows_excluded": True,
        },
        now=datetime(2022, 8, 1, 9, 0, tzinfo=JST),
    )
    payload = _load_json(Path(result.artifact_path))

    assert result.status == "READY"
    assert result.quote_count == 1
    assert payload["quote_source"] == str(logical_source)
    assert payload["source_role"] == "acquisition_staging"
    assert payload["quote_source_authority"] == "physical/acquisition/data.parquet"
    assert payload["logical_cutoff"] == "2022-08-01"
    assert payload["historical_asof_status"] == "PASS"
    assert payload["future_rows_excluded"] is True


def test_phase20_bl_review_required_market_artifact_is_not_reported_missing(tmp_path):
    runtime_root, _ = _roots(tmp_path)
    _write_json(
        runtime_root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": BUSINESS_DATE,
            "business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "market_status": "REVIEW_REQUIRED",
            "market_freshness_status": "READY",
            "quote_status": "NOT_REQUIRED",
            "reason": "quote_source_empty",
            "market_summary": {"quote_count": 0},
        },
    )

    payload = _market_readiness_payload(root=runtime_root, business_date=BUSINESS_DATE, market_open=True, override=False)

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["reason"] == "quote_source_empty"
    assert payload["quote_reason"] == "quote_source_empty"
    assert payload["missing_evidence"] == []


def test_phase15aw_runtime_business_date_and_market_date_are_separate(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, "2026-07-09", symbols=("7203",))

    result = produce_market_quote_evidence(
        runtime_root=runtime_root,
        operations_root=operations_root,
        runtime_business_date=BUSINESS_DATE,
        latest_available_market_date="2026-07-09",
        now=_now(),
    )
    payload = _load_json(Path(result.artifact_path))

    assert payload["runtime_business_date"] == BUSINESS_DATE
    assert payload["market_date"] == "2026-07-09"
    assert result.status in {"STALE", "REVIEW_REQUIRED"}


def test_phase15aw_duplicate_run_is_idempotent_for_same_content(tmp_path):
    runtime_root, operations_root = _roots(tmp_path)
    _write_daily_quotes(operations_root, BUSINESS_DATE, symbols=("7203",))
    kwargs = {
        "runtime_root": runtime_root,
        "operations_root": operations_root,
        "runtime_business_date": BUSINESS_DATE,
        "latest_available_market_date": BUSINESS_DATE,
        "now": _now(),
    }

    first = produce_market_quote_evidence(**kwargs)
    second = produce_market_quote_evidence(**kwargs)

    assert first.artifact_path == second.artifact_path
    assert first.history_artifact_path == second.history_artifact_path
    assert _load_json(Path(first.artifact_path)) == _load_json(Path(second.artifact_path))


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    operations_root.mkdir(parents=True, exist_ok=True)
    return runtime_root, operations_root


def _write_daily_quotes(
    operations_root: Path,
    market_date: str,
    *,
    symbols: tuple[str, ...] = (),
    rows: list[dict] | None = None,
) -> None:
    path = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = rows or [
        {
            "target_date": market_date,
            "code": symbol,
            "close": 1000.0 + index,
        }
        for index, symbol in enumerate(symbols)
    ]
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_raw_daily_quotes(
    operations_root: Path,
    market_date: str,
    *,
    rows: list[dict],
) -> None:
    path = operations_root / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_safety_inputs(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "positions": [{"symbol": "7203", "quantity": 100, "price": 1000, "market_value": 100000}],
            "cash": 900000,
            "buying_power": 900000,
            "market_value": 100000,
            "total_equity": 1000000,
            "previous_total_equity": 1000000,
        },
    )
    for name in ("orders", "executions", "positions", "cash", "events"):
        path = runtime_root / "persistent_ledger" / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    _write_json(
        runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "snapshot_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "broker_mode": "demo",
            "positions": [{"symbol": "7203", "quantity": 100}],
        },
    )
    _write_json(
        runtime_root / "runtime_state" / "current_state.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
        },
    )
    _write_json(
        runtime_root / "safety" / "locks" / "manual_emergency_state.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "is_locked": False,
            "status": "CLEAR",
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
