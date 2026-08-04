import json
from pathlib import Path

from ai_fund_lab_v2.data_quality import FetchPlanBuilder, RawQualityChecker, TradingCalendarService
from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import ManifestEntry, MarketDataStore, append_manifest, create_storage_backend, manifest_path, now_utc
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

    assert report.validation["status"] == "WARNING"
    assert report.schema_version == 1
    assert "missing_required_fields" in report.validation
    assert report.validation["row_classification_summary"]["valid_no_price_row_count"] == 1


def test_raw_quality_accepts_earnings_calendar_snapshot_without_date_gap(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    store.save_raw(
        [{"Date": "2026-08-08", "Code": "72030", "CoName": "Toyota"}],
        endpoint="/v2/equities/earnings-calendar",
        collection="jquants/earnings_calendar",
    )
    checker = checker_for(store, tmp_path)

    report = checker.check("earnings_calendar", "2026-07-06", "2026-07-10")

    assert report.expected_dates == []
    assert report.missing_dates == []
    assert report.validation["status"] == "OK"
    assert report.status == "OK"


def test_raw_quality_accepts_complete_adjusted_raw_and_reports_normalized_v2_ok(tmp_path: Path) -> None:
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

    assert report.validation["status"] == "OK"
    assert report.valid_price_row_count == 1
    assert report.normalized is not None
    assert report.normalized["validation"]["status"] == "OK"
    assert report.normalized["schema_version"] == 2


def test_raw_quality_reports_valid_no_price_rows_without_endpoint_error(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    store.save_raw(
        [
            {
                "Date": "2026-06-01",
                "Code": "131A0",
                "O": None,
                "H": None,
                "L": None,
                "C": None,
                "Vo": None,
                "AdjO": None,
                "AdjH": None,
                "AdjL": None,
                "AdjC": None,
                "AdjVo": None,
            }
        ],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )
    checker = checker_for(store, tmp_path)

    report = checker.check("daily_quotes", "2026-06-01", "2026-06-01")

    assert report.validation["status"] == "WARNING"
    assert report.status == "WARNING"
    assert report.valid_no_price_row_count == 1
    assert report.partial_ohlcv_corruption_count == 0
    assert report.invalid_numeric_row_count == 0
    assert report.schema_corruption_count == 0
    assert report.source_null_policy == "raw_source_faithful_valid_no_price_rows_are_not_canonical_price_rows"


def test_raw_quality_ignores_inactive_legacy_storage_format_after_parquet_manifest(tmp_path: Path) -> None:
    store = calendar_store(tmp_path)
    store.save_raw(
        [{"Date": "2026-07-06", "HolDiv": "1"}, {"Date": "2026-07-07", "HolDiv": "1"}],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
    paths = store.paths
    MarketDataStore(paths, raw_storage_format="parquet").save_raw(
        [{"Date": "2026-07-06", "HolDiv": "1"}, {"Date": "2026-07-07", "HolDiv": "1"}],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
    base_path = paths.raw_data / "jquants" / "fins_summary" / "data"
    old_jsonl = [{"DiscDate": "2026-06-01", "Code": "13010", "DiscNo": "20260601590001"}]
    current_parquet = [
        {
            "DiscDate": "2026-07-06",
            "Code": "72030",
            "DiscNo": "20260706590001",
            "business_key": "fins_summary:2026-07-06:72030:20260706590001",
            "target_date": "2026-07-06",
            "endpoint": "/v2/fins/summary",
        },
        {
            "DiscDate": "2026-07-07",
            "Code": "72030",
            "DiscNo": "20260707590001",
            "business_key": "fins_summary:2026-07-07:72030:20260707590001",
            "target_date": "2026-07-07",
            "endpoint": "/v2/fins/summary",
        },
    ]
    create_storage_backend("jsonl").write_records(create_storage_backend("jsonl").path_for(base_path), old_jsonl)
    create_storage_backend("parquet").write_records(create_storage_backend("parquet").path_for(base_path), current_parquet)
    append_manifest(
        manifest_path(paths.raw_data),
        ManifestEntry(
            fetched_at=now_utc(),
            endpoint="/v2/fins/summary",
            target_date="2026-07-07",
            from_date=None,
            to_date=None,
            record_count=1,
            storage_format="parquet",
            storage_path=str(create_storage_backend("parquet").path_for(base_path)),
            status="OK",
            validation_status="OK",
            schema_version=1,
            diff_summary={"duplicate_key_count": 0},
            request_params={"endpoint_name": "fins_summary"},
        ),
    )
    checker = checker_for(MarketDataStore(paths, raw_storage_format="parquet"), tmp_path)

    report = checker.check("fins_summary", "2026-07-06", "2026-07-07")

    assert report.storage_count_mismatch is False
    assert report.status == "OK"


def checker_for(store: MarketDataStore, tmp_path: Path) -> RawQualityChecker:
    return RawQualityChecker(
        store=store,
        paths=store.paths,
        fetch_plan_builder=FetchPlanBuilder(TradingCalendarService(store)),
    )


def valid_daily_record() -> dict:
    return {"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}
