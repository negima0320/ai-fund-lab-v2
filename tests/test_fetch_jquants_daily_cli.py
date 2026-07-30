from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_store import MarketDataStore, manifest_path, read_manifest
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.fetch_jquants_daily import main


def test_fetch_jquants_daily_dry_run_does_not_call_api_or_save(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"

    exit_code = main(
        [
            "--endpoint",
            "daily_quotes",
            "--date",
            "2026-06-01",
            "--dry-run",
            "--runtime-dir",
            str(runtime_dir),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "DRY-RUN endpoint=daily_quotes" in output
    assert str(runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.jsonl") in output
    assert not (runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.jsonl").exists()


def test_fetch_jquants_daily_dry_run_all_uses_runtime_paths(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir)

    main(["--endpoint", "all", "--from-date", "2026-06-01", "--to-date", "2026-06-07", "--dry-run", "--runtime-dir", str(runtime_dir)])

    output = capsys.readouterr().out
    assert "jquants/equities_bars_daily/data.jsonl" in output
    assert "jquants/listed_issues/data.jsonl" in output
    assert "jquants/earnings_calendar/data.jsonl" in output
    assert "jquants/trading_calendar/data.jsonl" in output
    assert "jquants/fins_summary/data.jsonl" in output
    assert "reason=business_day" in output
    assert "manifest=" in output
    assert "validation=planned" in output


def test_fetch_jquants_daily_dry_run_plan_skips_non_business_days(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir)

    main(["--endpoint", "daily_quotes", "--from-date", "2026-06-01", "--to-date", "2026-06-07", "--dry-run", "--runtime-dir", str(runtime_dir)])

    output = capsys.readouterr().out
    assert "date=2026-06-05" in output
    assert "date=2026-06-06" not in output
    assert "date=2026-06-07" not in output


def test_fins_summary_range_fetch_with_calendar_rows_writes_storage_manifest_and_output(tmp_path: Path, monkeypatch, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir, start="2026-07-06", days=5)
    fake_client = install_fake_jquants_client(monkeypatch, rows_by_date={"2026-07-06": [{"DiscDate": "2026-07-06", "Code": "72030"}]})

    exit_code = main(["--endpoint", "fins_summary", "--from-date", "2026-07-06", "--to-date", "2026-07-10", "--runtime-dir", str(runtime_dir)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert fake_client.instance is not None
    assert fake_client.instance.calls == ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10"]
    assert "fins_summary: saved" in output
    records = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir)).read_raw_collection("jquants/fins_summary")
    assert any(record["target_date"] == "2026-07-06" for record in records)
    manifest_rows = read_manifest(manifest_path(RuntimePaths(runtime_dir=runtime_dir).raw_data))
    assert any(row.get("endpoint") == "/v2/fins/summary" and row.get("target_date") == "2026-07-06" for row in manifest_rows)


def test_fins_summary_range_fetch_empty_plan_is_visible_failure_without_manifest(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir, start="2026-06-01", days=5)
    before = manifest_snapshot(runtime_dir)

    exit_code = main(["--endpoint", "fins_summary", "--from-date", "2026-07-06", "--to-date", "2026-07-17", "--runtime-dir", str(runtime_dir)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "ERROR fetch plan is empty" in captured.err
    assert "trading_calendar_coverage=2026-06-01..2026-06-05" in captured.err
    assert manifest_snapshot(runtime_dir) == before


def test_fins_summary_zero_row_response_still_writes_manifest_and_output(tmp_path: Path, monkeypatch, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir, start="2026-07-06", days=1)
    fake_client = install_fake_jquants_client(monkeypatch, rows_by_date={})

    exit_code = main(["--endpoint", "fins_summary", "--from-date", "2026-07-06", "--to-date", "2026-07-06", "--runtime-dir", str(runtime_dir)])

    assert exit_code == 0
    assert fake_client.instance is not None
    assert fake_client.instance.calls == ["2026-07-06"]
    assert "saved 0 records" in capsys.readouterr().out
    manifest_rows = read_manifest(manifest_path(RuntimePaths(runtime_dir=runtime_dir).raw_data))
    assert any(row.get("endpoint") == "/v2/fins/summary" and row.get("target_date") == "2026-07-06" and row.get("record_count") == 0 for row in manifest_rows)


def test_existing_fins_summary_for_other_date_does_not_skip_requested_range(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir, start="2026-07-06", days=1)
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir))
    store.save_raw([{"DiscDate": "2026-06-01", "Code": "11110"}], endpoint="/v2/fins/summary", collection="jquants/fins_summary")
    fake_client = install_fake_jquants_client(monkeypatch, rows_by_date={"2026-07-06": [{"DiscDate": "2026-07-06", "Code": "22220"}]})

    exit_code = main(["--endpoint", "fins_summary", "--from-date", "2026-07-06", "--to-date", "2026-07-06", "--runtime-dir", str(runtime_dir)])

    assert exit_code == 0
    assert fake_client.instance is not None
    assert fake_client.instance.calls == ["2026-07-06"]
    records = store.read_raw_collection("jquants/fins_summary")
    assert {record["target_date"] for record in records} >= {"2026-06-01", "2026-07-06"}


def test_existing_fins_summary_for_same_date_is_refetched_not_silent_skipped(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir, start="2026-07-06", days=1)
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir))
    store.save_raw([{"DiscDate": "2026-07-06", "Code": "11110"}], endpoint="/v2/fins/summary", collection="jquants/fins_summary")
    fake_client = install_fake_jquants_client(monkeypatch, rows_by_date={"2026-07-06": [{"DiscDate": "2026-07-06", "Code": "22220"}]})

    exit_code = main(["--endpoint", "fins_summary", "--from-date", "2026-07-06", "--to-date", "2026-07-06", "--runtime-dir", str(runtime_dir)])

    assert exit_code == 0
    assert fake_client.instance is not None
    assert fake_client.instance.calls == ["2026-07-06"]
    records = store.read_raw_collection("jquants/fins_summary")
    assert any(record.get("Code") == "22220" for record in records)


def write_calendar(runtime_dir: Path, *, start: str = "2026-06-01", days: int = 7) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir))
    from datetime import date, timedelta

    start_day = date.fromisoformat(start)
    store.save_raw(
        [
            {"Date": (start_day + timedelta(days=index)).isoformat(), "HolDiv": "1" if index < min(days, 5) else "0"}
            for index in range(days)
        ],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )


class FakeJQuantsClient:
    instance: "FakeJQuantsClient | None" = None

    def __init__(self, *args: Any, rows_by_date: dict[str, list[dict[str, Any]]] | None = None, **kwargs: Any) -> None:
        self.rows_by_date = rows_by_date or {}
        self.calls: list[str] = []
        FakeJQuantsClient.instance = self

    def fetch_all_fins_summary(self, *, date: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(str(date or ""))
        return [dict(row) for row in self.rows_by_date.get(str(date or ""), [])]


def install_fake_jquants_client(monkeypatch: Any, *, rows_by_date: dict[str, list[dict[str, Any]]]) -> type[FakeJQuantsClient]:
    import scripts.fetch_jquants_daily as cli

    class BoundFakeJQuantsClient(FakeJQuantsClient):
        instance: "BoundFakeJQuantsClient | None" = None

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, rows_by_date=rows_by_date, **kwargs)
            BoundFakeJQuantsClient.instance = self

    monkeypatch.setattr(cli, "JQuantsClient", BoundFakeJQuantsClient)
    return BoundFakeJQuantsClient


def manifest_snapshot(runtime_dir: Path) -> list[dict[str, Any]]:
    path = manifest_path(RuntimePaths(runtime_dir=runtime_dir).raw_data)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
