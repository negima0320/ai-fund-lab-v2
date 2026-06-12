from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.build_jquants_refetch_plan import main
from tests.test_fetch_jquants_daily_cli import write_calendar


def test_refetch_plan_validation_error_and_missing_priorities(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir)
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir))
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030"}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )

    main(
        [
            "--endpoint",
            "daily_quotes",
            "--from-date",
            "2026-06-01",
            "--to-date",
            "2026-06-03",
            "--runtime-dir",
            str(runtime_dir),
            "--reason",
            "all",
            "--output",
            "markdown",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert "validation_error" in output
    assert "empty" in output
    assert "HIGH" in output
    assert (runtime_dir / "reports" / "jquants_refetch_plan").is_dir()


def test_refetch_plan_fins_summary_empty_is_low_priority(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir)

    main(
        [
            "--endpoint",
            "fins_summary",
            "--from-date",
            "2026-06-01",
            "--to-date",
            "2026-06-01",
            "--runtime-dir",
            str(runtime_dir),
            "--reason",
            "empty",
        ]
    )

    assert "LOW" in capsys.readouterr().out
