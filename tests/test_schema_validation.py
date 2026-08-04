from ai_fund_lab_v2.data_store import validate_records


def test_daily_quotes_schema_validation_ok() -> None:
    result = validate_records(
        "daily_quotes",
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}],
    )

    assert result.status == "OK"
    assert result.schema_version == 1


def test_daily_quotes_schema_missing_required_field_is_error() -> None:
    result = validate_records("daily_quotes", [{"Date": "2026-06-01", "Code": "72030"}])

    assert result.status == "WARNING"
    assert result.missing_required_fields == {}
    assert result.row_classification_summary["valid_no_price_row_count"] == 1


def test_daily_quotes_schema_accepts_complete_adjusted_price_row() -> None:
    result = validate_records(
        "daily_quotes",
        [{"Date": "2026-06-01", "Code": "72030", "AdjO": 1, "AdjH": 2, "AdjL": 1, "AdjC": 2, "AdjVo": 100}],
    )

    assert result.status == "OK"
    assert result.row_classification_summary["valid_price_row_count"] == 1


def test_daily_quotes_schema_classifies_valid_no_price_row_without_error() -> None:
    result = validate_records(
        "daily_quotes",
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
    )

    assert result.status == "WARNING"
    assert result.missing_required_fields == {}
    assert result.row_classification_summary["valid_no_price_row_count"] == 1
    assert result.row_classification_summary["endpoint_validation_status"] == "WARNING"


def test_daily_quotes_schema_rejects_partial_raw_ohlcv() -> None:
    result = validate_records(
        "daily_quotes",
        [{"Date": "2026-06-01", "Code": "72030", "O": None, "H": 2, "L": 1, "C": 2, "Vo": 100}],
    )

    assert result.status == "ERROR"
    assert result.row_classification_summary["partial_ohlcv_corruption_count"] == 1
    assert "O" in result.missing_required_fields


def test_daily_quotes_schema_rejects_partial_adjusted_ohlcv() -> None:
    result = validate_records(
        "daily_quotes",
        [{"Date": "2026-06-01", "Code": "72030", "AdjO": 1, "AdjH": 2, "AdjL": 1, "AdjC": 2}],
    )

    assert result.status == "ERROR"
    assert result.row_classification_summary["partial_ohlcv_corruption_count"] == 1


def test_daily_quotes_schema_rejects_nan_inf_and_negative_volume() -> None:
    result = validate_records(
        "daily_quotes",
        [
            {"Date": "2026-06-01", "Code": "72030", "O": float("nan"), "H": 2, "L": 1, "C": 2, "Vo": 100},
            {"Date": "2026-06-01", "Code": "67580", "O": 1, "H": float("inf"), "L": 1, "C": 2, "Vo": 100},
            {"Date": "2026-06-01", "Code": "99840", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": -1},
        ],
    )

    assert result.status == "ERROR"
    assert result.row_classification_summary["partial_ohlcv_corruption_count"] == 1
    assert result.row_classification_summary["invalid_numeric_row_count"] == 2


def test_daily_quotes_schema_rejects_missing_identity() -> None:
    result = validate_records("daily_quotes", [{"Date": "2026-06-01", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}])

    assert result.status == "ERROR"
    assert result.missing_key_count == 1
    assert result.row_classification_summary["schema_corruption_count"] == 1


def test_trading_calendar_schema_detects_missing_holdiv() -> None:
    result = validate_records("trading_calendar", [{"Date": "2026-06-01"}])

    assert result.status == "ERROR"
    assert result.missing_required_fields == {"HolDiv": 1}


def test_listed_issues_schema_detects_key_missing() -> None:
    result = validate_records("listed_issues", [{"Date": "2026-06-01", "CoName": "A", "Mkt": "0111"}])

    assert result.status == "ERROR"
    assert result.missing_key_count == 1


def test_fins_summary_empty_is_allowed() -> None:
    result = validate_records("fins_summary", [])

    assert result.status == "OK"


def test_fins_summary_schema_uses_disc_no_as_disclosure_identity() -> None:
    result = validate_records(
        "fins_summary",
        [
            {"DiscDate": "2026-07-14", "Code": "94440", "DiscNo": "20260714590001", "DocType": "ForecastRevision"},
            {"DiscDate": "2026-07-14", "Code": "94440", "DiscNo": "20260714590002", "DocType": "DividendForecastRevision"},
        ],
    )

    assert result.status == "OK"
    assert result.duplicate_key_count == 0


def test_fins_summary_schema_warns_on_exact_disclosure_identity_duplicate() -> None:
    record = {"DiscDate": "2026-07-14", "Code": "94440", "DiscNo": "20260714590001", "DocType": "ForecastRevision"}
    result = validate_records("fins_summary", [dict(record), dict(record)])

    assert result.status == "WARNING"
    assert result.duplicate_key_count == 1


def test_earnings_calendar_schema_validation_ok() -> None:
    result = validate_records(
        "earnings_calendar",
        [{"Date": "2026-08-08", "Code": "72030", "CoName": "Toyota", "FQ": "1Q"}],
    )

    assert result.status == "OK"
    assert result.schema_version == 1


def test_earnings_calendar_schema_missing_key_is_error() -> None:
    result = validate_records("earnings_calendar", [{"Date": "2026-08-08", "CoName": "Toyota"}])

    assert result.status == "ERROR"
    assert result.missing_key_count == 1


def test_schema_detects_duplicate_business_key() -> None:
    record = {"Date": "2026-06-01", "HolDiv": "1"}
    result = validate_records("trading_calendar", [record, record])

    assert result.status == "WARNING"
    assert result.duplicate_key_count == 1


def test_daily_quotes_normalized_schema_validation_ok() -> None:
    result = validate_records(
        "daily_quotes_normalized",
        [
            {
                "Date": "2026-06-01",
                "Code": "72030",
                "Open": 1,
                "High": 2,
                "Low": 1,
                "Close": 2,
                "Volume": 100,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )

    assert result.status == "OK"
    assert result.schema_version == 2


def test_daily_quotes_normalized_zero_price_is_warning() -> None:
    result = validate_records(
        "daily_quotes_normalized",
        [
            {
                "Date": "2026-06-01",
                "Code": "72030",
                "Open": 0,
                "High": 2,
                "Low": 1,
                "Close": 2,
                "Volume": 0,
                "PriceSource": "adjusted",
                "SchemaVersion": 2,
            }
        ],
    )

    assert result.status == "WARNING"
    assert result.type_warning_count == 2
