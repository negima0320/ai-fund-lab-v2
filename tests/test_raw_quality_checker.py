import json
from pathlib import Path

from ai_fund_lab_v2.data_quality import FetchPlanBuilder, RawQualityChecker, TradingCalendarService
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from tests.test_trading_calendar_service import calendar_store


def test_raw_quality_detects_expected_fetched_and_missing_dates(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    store.save_raw([valid_daily_record()], endpoint="/v2/equities/bars/daily", collection="jquants/equities_bars_daily")
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-01", "2026-06-03")

    assert report.expected_dates == ["2026-06-01", "2026-06-02", "2026-06-03"]
    assert report.fetched_dates == ["2026-06-01"]
    assert report.missing_dates == ["2026-06-02", "2026-06-03"]
    assert report.status == "WARNING"


def test_raw_quality_does_not_warn_for_non_business_day_missing(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-06", "2026-06-07")

    assert report.expected_dates == []
    assert report.missing_dates == []
    assert report.status == "OK"


def test_raw_quality_detects_duplicate_keys(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    path = store.paths.raw_data / "jquants" / "equities_bars_daily" / "data.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "Date": "2026-06-01",
        "Code": "72030",
        "O": 1,
        "H": 2,
        "L": 1,
        "C": 2,
        "Vo": 100,
        "target_date": "2026-06-01",
        "business_key": "72030",
        "code": "72030",
        "endpoint": "/v2/equities/bars/daily",
    }
    path.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-01", "2026-06-01")

    assert report.duplicate_key_count == 1
    assert report.status == "WARNING"


def test_raw_quality_detects_empty_dates(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-01", "2026-06-01")

    assert report.empty_dates == ["2026-06-01"]


def test_raw_quality_saves_json_and_markdown_reports_under_runtime_reports(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    checker = checker_for(store, tmp_path)
    report = checker.check("daily_quotes", "2026-06-06", "2026-06-07")

    json_path, markdown_path = checker.save_reports([report], "both")

    assert json_path is not None
    assert markdown_path is not None
    assert json_path.parent == store.paths.reports / "jquants_raw_quality"
    assert markdown_path.parent == store.paths.reports / "jquants_raw_quality"
    assert "daily_quotes" in markdown_path.read_text(encoding="utf-8")


def test_raw_quality_report_includes_validation_summary(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030"}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-01", "2026-06-01")

    assert report.validation["status"] == "ERROR"
    assert report.schema_version == 1
    assert "missing_required_fields" in report.validation


def test_raw_quality_distinguishes_raw_v1_error_from_normalized_v2_ok(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    adjusted_only = {
        "Date": "2026-06-01",
        "Code": "72030",
        "AdjO": 1,
        "AdjH": 2,
        "AdjL": 1,
        "AdjC": 2,
        "AdjVo": 100,
    }
    store.save_raw([adjusted_only], endpoint="/v2/equities/bars/daily", collection="jquants/equities_bars_daily")
    normalized_records, _ = normalize_daily_quotes([adjusted_only])
    write_daily_quotes_normalized(store.paths, "jsonl", normalized_records)
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-01", "2026-06-01")

    assert report.validation["status"] == "ERROR"
    assert report.normalized is not None
    assert report.normalized["validation"]["status"] == "OK"
    assert report.normalized["schema_version"] == 2


def checker_for(store: MarketDataStore, tmp_path: Path) -> RawQualityChecker:
    return RawQualityChecker(
        store=store,
        paths=store.paths,
        fetch_plan_builder=FetchPlanBuilder(TradingCalendarService(store)),
    )


def valid_daily_record() -> dict:
    return {"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}
