from pathlib import Path
from typing import Any
import json

from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import JQuantsRawIngestor
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths


class FakeClient:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records

    def fetch_all_daily_quotes(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.records

    def fetch_all_listed_issues(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.records

    def fetch_all_trading_calendar(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.records

    def fetch_all_earnings_calendar(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.records

    def fetch_all_fins_summary(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.records


def test_ingestor_saves_daily_quotes_to_raw_collection(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(
        client=FakeClient([{"Date": "2026-06-01", "Code": "72030", "C": 1000}]),
        store=MarketDataStore(paths),
        paths=paths,
    )

    result = ingestor.fetch_and_store("daily_quotes", date="2026-06-01")

    assert result.records_saved == 1
    assert result.output_path.endswith("data/raw/jquants/equities_bars_daily/data.jsonl")
    records = MarketDataStore(paths).read_raw_collection("jquants/equities_bars_daily")
    assert records[0]["source"] == "jquants"
    assert records[0]["endpoint"] == "/v2/equities/bars/daily"


def test_ingestor_updates_manifest_without_secrets(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(
        client=FakeClient([{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}]),
        store=MarketDataStore(paths),
        paths=paths,
    )

    ingestor.fetch_and_store("daily_quotes", date="2026-06-01", max_pages=1)

    manifest = paths.raw_data / "jquants" / "manifest.jsonl"
    entry = json.loads(manifest.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["endpoint"] == "/v2/equities/bars/daily"
    assert entry["record_count"] == 1
    assert entry["storage_format"] == "jsonl"
    assert entry["validation_status"] == "OK"
    assert entry["schema_version"] == 1
    assert "diff_summary" in entry
    text = manifest.read_text(encoding="utf-8")
    assert "x-api-key" not in text.lower()
    assert "authorization" not in text.lower()


def test_ingestor_resave_does_not_duplicate_daily_quotes(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    store = MarketDataStore(paths)
    ingestor = JQuantsRawIngestor(
        client=FakeClient([{"Date": "2026-06-01", "Code": "72030", "C": 1000}]),
        store=store,
        paths=paths,
    )

    ingestor.fetch_and_store("daily_quotes", date="2026-06-01")
    ingestor.client = FakeClient([{"Date": "2026-06-01", "Code": "72030", "C": 1010}])
    ingestor.fetch_and_store("daily_quotes", date="2026-06-01")

    records = store.read_raw_collection("jquants/equities_bars_daily")
    assert len(records) == 1
    assert records[0]["C"] == 1010


def test_ingestor_saves_code_less_trading_calendar(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(
        client=FakeClient([{"Date": "2026-06-01", "HolidayDivision": "1"}]),
        store=MarketDataStore(paths),
        paths=paths,
    )

    ingestor.fetch_and_store("trading_calendar", from_date="2026-06-01", to_date="2026-06-01")

    records = MarketDataStore(paths).read_raw_collection("jquants/trading_calendar")
    assert len(records) == 1
    assert records[0]["business_key"] == "2026-06-01"
    assert records[0]["code"] == ""


def test_ingestor_saves_earnings_calendar_to_raw_collection(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(
        client=FakeClient([{"Date": "2026-08-08", "Code": "72030", "CoName": "Toyota"}]),
        store=MarketDataStore(paths),
        paths=paths,
    )

    result = ingestor.fetch_and_store("earnings_calendar", date="2026-06-01")

    assert result.records_saved == 1
    assert result.output_path.endswith("data/raw/jquants/earnings_calendar/data.jsonl")
    records = MarketDataStore(paths).read_raw_collection("jquants/earnings_calendar")
    assert records[0]["endpoint"] == "/v2/equities/earnings-calendar"
    assert records[0]["target_date"] == "2026-08-08"
    assert records[0]["fetched_at"]


def test_fins_summary_preserves_same_day_same_code_distinct_disc_no(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(
        client=FakeClient(
            [
                {"DiscDate": "2026-07-14", "Code": "94440", "DiscNo": "20260714590001", "DiscTime": "15:00:00", "DocType": "ForecastRevision"},
                {"DiscDate": "2026-07-14", "Code": "94440", "DiscNo": "20260714590002", "DiscTime": "15:10:00", "DocType": "DividendForecastRevision"},
            ]
        ),
        store=MarketDataStore(paths),
        paths=paths,
    )

    result = ingestor.fetch_and_store("fins_summary", date="2026-07-14")

    records = MarketDataStore(paths).read_raw_collection("jquants/fins_summary")
    assert result.records_saved == 2
    assert result.validation_status == "OK"
    assert len(records) == 2
    assert {record["DiscNo"] for record in records} == {"20260714590001", "20260714590002"}
    assert len({record["business_key"] for record in records}) == 2
    assert result.diff_summary is not None
    assert result.diff_summary["duplicate_key_count"] == 0
    assert result.diff_summary["business_key_collision_count"] == 0


def test_fins_summary_exact_duplicate_disc_no_collapses_with_diagnostic(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    record = {"DiscDate": "2026-07-14", "Code": "94440", "DiscNo": "20260714590001", "DiscTime": "15:00:00", "DocType": "ForecastRevision"}
    ingestor = JQuantsRawIngestor(client=FakeClient([dict(record), dict(record)]), store=MarketDataStore(paths), paths=paths)

    result = ingestor.fetch_and_store("fins_summary", date="2026-07-14")

    records = MarketDataStore(paths).read_raw_collection("jquants/fins_summary")
    assert result.records_saved == 2
    assert result.validation_status == "WARNING"
    assert len(records) == 1
    assert result.diff_summary is not None
    assert result.diff_summary["duplicate_key_count"] == 1
    assert result.diff_summary["exact_source_duplicate_count"] == 1
    assert result.diff_summary["business_key_collision_count"] == 0


def test_fins_summary_missing_disc_no_fallback_preserves_distinct_disclosures(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(
        client=FakeClient(
            [
                {"DiscDate": "2026-07-14", "Code": "94440", "DiscTime": "15:00:00", "DocType": "ForecastRevision", "CurPerType": "FY", "CurPerEn": "2026-03-31"},
                {"DiscDate": "2026-07-14", "Code": "94440", "DiscTime": "15:10:00", "DocType": "DividendForecastRevision", "CurPerType": "FY", "CurPerEn": "2026-03-31"},
            ]
        ),
        store=MarketDataStore(paths),
        paths=paths,
    )

    result = ingestor.fetch_and_store("fins_summary", date="2026-07-14")

    records = MarketDataStore(paths).read_raw_collection("jquants/fins_summary")
    assert result.validation_status == "OK"
    assert len(records) == 2
    assert len({record["business_key"] for record in records}) == 2


def test_daily_quotes_empty_result_writes_missing_log(tmp_path: Path) -> None:
    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    ingestor = JQuantsRawIngestor(client=FakeClient([]), store=MarketDataStore(paths), paths=paths)

    ingestor.fetch_and_store("daily_quotes", date="2026-06-01")

    log_text = (paths.logs / "jquants_ingestion.log").read_text(encoding="utf-8")
    assert "missing_or_non_business_day" in log_text
    assert "2026-06-01" in log_text


def test_ingestor_filters_conflicting_all_parameters_by_endpoint(tmp_path: Path) -> None:
    class RecordingClient(FakeClient):
        def __init__(self) -> None:
            super().__init__([{"Date": "2026-06-01", "Code": "72030"}])
            self.calls: list[tuple[str, dict[str, Any]]] = []

        def fetch_all_daily_quotes(self, **kwargs: Any) -> list[dict[str, Any]]:
            self.calls.append(("daily_quotes", kwargs))
            return self.records

        def fetch_all_trading_calendar(self, **kwargs: Any) -> list[dict[str, Any]]:
            self.calls.append(("trading_calendar", kwargs))
            return [{"Date": "2026-06-01"}]

    paths = RuntimePaths(runtime_dir=tmp_path / "runtime")
    client = RecordingClient()
    ingestor = JQuantsRawIngestor(client=client, store=MarketDataStore(paths), paths=paths)

    ingestor.fetch_and_store("daily_quotes", date="2026-06-01", from_date="2026-06-01", to_date="2026-06-07", max_pages=1)
    ingestor.fetch_and_store("trading_calendar", date="2026-06-01", from_date="2026-06-01", to_date="2026-06-07", max_pages=1)

    daily_call = client.calls[0][1]
    calendar_call = client.calls[1][1]
    assert daily_call["date"] == "2026-06-01"
    assert daily_call["from_date"] is None
    assert daily_call["to_date"] is None
    assert calendar_call["date"] is None
    assert calendar_call["from_date"] == "2026-06-01"
    assert calendar_call["to_date"] == "2026-06-07"
