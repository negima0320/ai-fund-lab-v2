from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import (
    DAILY_QUOTES_NORMALIZED_ENDPOINT,
    normalize_daily_quotes,
    normalized_output_path,
    write_daily_quotes_normalized,
)
from ai_fund_lab_v2.candidate_ai.data_loader import adapt_daily_quotes_normalized
from ai_fund_lab_v2.data_store import create_storage_backend, validate_records
from ai_fund_lab_v2.runtime import RuntimePaths


def test_normalize_daily_quotes_prefers_adjusted_fields() -> None:
    records, report = normalize_daily_quotes(
        [
            {
                "Date": "2026-06-01",
                "Code": "72030",
                "O": 10,
                "H": 11,
                "L": 9,
                "C": 10,
                "Vo": 100,
                "AdjO": 20,
                "AdjH": 21,
                "AdjL": 19,
                "AdjC": 20,
                "AdjVo": 200,
            }
        ]
    )

    assert records[0]["Open"] == 20
    assert records[0]["Volume"] == 200
    assert records[0]["PriceSource"] == "adjusted"
    assert records[0]["SchemaVersion"] == 2
    assert report.adjusted_count == 1
    assert report.validation_status == "OK"


def test_normalize_daily_quotes_falls_back_to_unadjusted_fields() -> None:
    records, report = normalize_daily_quotes(
        [{"Date": "2026-06-01", "Code": "72030", "O": 10, "H": 11, "L": 9, "C": 10, "Vo": 100}]
    )

    assert records[0]["Open"] == 10
    assert records[0]["PriceSource"] == "unadjusted"
    assert report.unadjusted_count == 1


def test_normalize_daily_quotes_reports_errors_and_warnings() -> None:
    records, report = normalize_daily_quotes(
        [
            {"Date": "2026-06-01", "Code": "72030", "AdjO": 0, "AdjH": 1, "AdjL": 1, "AdjC": 1, "AdjVo": 0},
            {"Date": "2026-06-02", "Code": "67580", "AdjO": 1},
        ],
        limit_errors=5,
    )

    assert len(records) == 1
    assert report.error_count == 1
    assert report.warning_count == 2
    assert report.status == "ERROR"
    assert report.sample_errors
    assert report.sample_warnings
    validation = validate_records(DAILY_QUOTES_NORMALIZED_ENDPOINT, records)
    assert validation.status == "WARNING"


def test_normalize_daily_quotes_drops_valid_no_price_rows_without_fabricating_zeroes() -> None:
    records, report = normalize_daily_quotes(
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
        limit_errors=5,
    )

    assert records == []
    assert report.error_count == 0
    assert report.valid_no_price_dropped_count == 1
    assert report.status == "WARNING"
    assert report.sample_errors == []
    assert "valid_no_price_row_dropped_from_canonical_ohlcv" in report.sample_warnings[0]


def test_candidate_loader_excludes_no_price_rows_after_normalization() -> None:
    normalized_records, _ = normalize_daily_quotes(
        [
            {"Date": "2026-06-01", "Code": "72030", "O": 10, "H": 11, "L": 9, "C": 10, "Vo": 100},
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
            },
        ]
    )

    loaded = adapt_daily_quotes_normalized(normalized_records, as_of_date="2026-06-01")

    assert [row["code"] for row in loaded.rows] == ["72030"]
    assert loaded.rows[0]["close"] == 10.0
    assert loaded.rows[0]["volume"] == 100.0
    assert all(row["code"] != "131A0" for row in loaded.rows)


def test_normalized_schema_errors_on_null_prices() -> None:
    result = validate_records(
        DAILY_QUOTES_NORMALIZED_ENDPOINT,
        [
            {
                "Date": "2026-06-01",
                "Code": "72030",
                "Open": None,
                "High": 1,
                "Low": 1,
                "Close": 1,
                "Volume": 100,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )

    assert result.status == "ERROR"
    assert result.missing_required_fields == {"Open": 1}


def test_write_daily_quotes_normalized_uses_raw_normalized_path(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    records, _ = normalize_daily_quotes(
        [{"Date": "2026-06-01", "Code": "72030", "O": 10, "H": 11, "L": 9, "C": 10, "Vo": 100}]
    )

    output_path = write_daily_quotes_normalized(paths, "jsonl", records)

    assert output_path == normalized_output_path(paths, "jsonl")
    assert output_path == tmp_path / "runtime" / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.jsonl"
    assert create_storage_backend("jsonl").read_records(output_path)[0]["SchemaVersion"] == 2
