from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.inspect_raw_validation import main


def seed_bad_daily(runtime_dir: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir), raw_storage_format="jsonl")
    store.save_raw(
        [
            {"Date": "2026-06-01", "Code": "11110", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100},
            {"Date": "2026-06-01", "Code": "22220", "AdjO": 1, "AdjH": 2, "AdjL": 1, "AdjC": 2, "AdjVo": 100},
            {"Date": "2026-06-02", "Code": "33330", "O": None, "H": None, "L": None, "C": None, "Vo": None},
        ],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )


def test_inspect_raw_validation_outputs_details_and_limits_samples(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_bad_daily(runtime_dir)

    main(["--endpoint", "daily_quotes", "--runtime-dir", str(runtime_dir), "--limit", "1", "--output", "json"])

    output = capsys.readouterr().out
    assert '"validation_status": "ERROR"' in output
    assert '"missing_required_fields"' in output
    assert '"affected_dates"' in output
    assert '"affected_codes"' in output
    assert "consider mapping from AdjO" in output
    assert output.count('"target_date"') == 1


def test_inspect_raw_validation_report_does_not_leak_secret(tmp_path: Path, capsys, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    secret = "inspection-secret"
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    seed_bad_daily(runtime_dir)

    main(["--endpoint", "daily_quotes", "--runtime-dir", str(runtime_dir), "--output", "markdown", "--save-report"])

    captured = capsys.readouterr()
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in (runtime_dir / "reports" / "raw_validation_inspection").glob("*"))
    assert secret not in captured.out
    assert secret not in report_text
