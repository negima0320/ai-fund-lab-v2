from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.check_jquants_raw_quality import main
from tests.test_fetch_jquants_daily_cli import write_calendar


def test_check_jquants_raw_quality_cli_writes_reports(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_calendar(runtime_dir)
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir))
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )

    exit_code = main(
        [
            "--endpoint",
            "daily_quotes",
            "--from-date",
            "2026-06-01",
            "--to-date",
            "2026-06-03",
            "--runtime-dir",
            str(runtime_dir),
            "--output",
            "both",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "daily_quotes:WARNING" in output
    report_dir = runtime_dir / "reports" / "jquants_raw_quality"
    assert list(report_dir.glob("*.json"))
    assert list(report_dir.glob("*.md"))


def test_check_jquants_raw_quality_report_does_not_leak_secret(tmp_path: Path, capsys, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    secret = "quality-secret-key"
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    write_calendar(runtime_dir)

    main(
        [
            "--endpoint",
            "daily_quotes",
            "--from-date",
            "2026-06-06",
            "--to-date",
            "2026-06-07",
            "--runtime-dir",
            str(runtime_dir),
            "--output",
            "both",
        ]
    )

    captured = capsys.readouterr()
    assert secret not in captured.out
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in (runtime_dir / "reports" / "jquants_raw_quality").glob("*"))
    assert secret not in report_text
