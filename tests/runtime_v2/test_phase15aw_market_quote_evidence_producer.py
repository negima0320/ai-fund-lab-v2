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


def _write_daily_quotes(operations_root: Path, market_date: str, *, symbols: tuple[str, ...]) -> None:
    path = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "target_date": market_date,
            "code": symbol,
            "close": 1000.0 + index,
        }
        for index, symbol in enumerate(symbols)
    ]
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
