from pathlib import Path

from ai_fund_lab_v2.data_store import DataLayer, MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths


def test_market_data_store_upserts_without_duplicate_keys(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))
    endpoint = "/v2/equities/bars/daily"

    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030", "C": 1000}],
        endpoint=endpoint,
    )
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030", "C": 1010}],
        endpoint=endpoint,
    )

    records = store.read_layer(DataLayer.RAW, endpoint)
    assert len(records) == 1
    assert records[0]["C"] == 1010
    assert records[0]["target_date"] == "2026-06-01"
    assert records[0]["code"] == "72030"
    assert records[0]["source"] == "jquants"
    assert records[0]["endpoint"] == endpoint
    assert records[0]["fetched_at"]


def test_market_data_store_save_result_contains_diff_and_validation(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))

    first = store.save_raw_with_result(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
        endpoint_name="daily_quotes",
    )
    second = store.save_raw_with_result(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 3, "L": 1, "C": 3, "Vo": 101}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
        endpoint_name="daily_quotes",
    )

    assert first.diff_summary.inserted_count == 1
    assert second.diff_summary.updated_count == 1
    assert second.diff_summary.record_count_after == 1
    assert second.validation_result is not None
    assert second.validation_result.status == "OK"


def test_market_data_store_parquet_upsert_and_diff(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"), raw_storage_format="parquet")

    first = store.save_raw_with_result(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
        endpoint_name="daily_quotes",
    )
    second = store.save_raw_with_result(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 3, "Vo": 101}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
        endpoint_name="daily_quotes",
    )

    assert first.path.suffix == ".parquet"
    assert second.diff_summary.updated_count == 1
    assert len(store.read_raw_collection("jquants/equities_bars_daily")) == 1


def test_raw_feature_label_paths_are_separated(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))

    raw_path = store.save_raw([{"target_date": "2026-06-01", "code": "11110"}], endpoint="/raw")
    feature_path = store.save_features([{"target_date": "2026-06-01", "code": "11110"}], endpoint="/features")
    label_path = store.save_labels([{"target_date": "2026-06-01", "code": "11110"}], endpoint="/labels")

    assert raw_path.parent == tmp_path / "runtime" / "data" / "raw"
    assert feature_path.parent == tmp_path / "runtime" / "data" / "features"
    assert label_path.parent == tmp_path / "runtime" / "data" / "labels"


def test_raw_store_can_write_endpoint_collection(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))

    path = store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030"}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )

    assert path == tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.jsonl"


def test_code_less_records_use_business_key_for_upsert(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))

    store.save_raw(
        [{"Date": "2026-06-01", "HolidayDivision": "1", "business_key": "2026-06-01"}],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
    store.save_raw(
        [{"Date": "2026-06-01", "HolidayDivision": "0", "business_key": "2026-06-01"}],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )

    records = store.read_raw_collection("jquants/trading_calendar")
    assert len(records) == 1
    assert records[0]["HolidayDivision"] == "0"
    assert records[0]["code"] == ""


def test_store_rejects_records_missing_business_key_metadata(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))

    try:
        store.save_raw([{"Name": "missing key"}], endpoint="/raw")
    except ValueError as exc:
        assert "target_date" in str(exc)
    else:
        raise AssertionError("Expected metadata validation failure")
