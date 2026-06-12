from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
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


def write_calendar(runtime_dir: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir))
    store.save_raw(
        [
            {"Date": "2026-06-01", "HolDiv": "1"},
            {"Date": "2026-06-02", "HolDiv": "1"},
            {"Date": "2026-06-03", "HolDiv": "1"},
            {"Date": "2026-06-04", "HolDiv": "1"},
            {"Date": "2026-06-05", "HolDiv": "1"},
            {"Date": "2026-06-06", "HolDiv": "0"},
            {"Date": "2026-06-07", "HolDiv": "0"},
        ],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
