import json
from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.inspect_daily_quote_exclusions import main


def seed_exclusion_fixture(runtime_dir: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir), raw_storage_format="jsonl")
    store.save_raw(
        [
            {"Date": "2026-06-01", "Code": "72030", "AdjO": 1, "AdjH": 2, "AdjL": 1, "AdjC": 2, "AdjVo": 100},
            {"Date": "2026-06-01", "Code": "131A0"},
            {"Date": "2026-06-02", "Code": "132A0", "O": 1, "H": 2, "L": 1, "C": 2},
        ],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )
    store.save_raw(
        [
            {"Date": "2026-06-01", "Code": "131A0", "CoName": "Alpha", "Mkt": "0111", "MktNm": "Growth"},
            {"Date": "2026-06-01", "Code": "132A0", "CoName": "Beta", "Mkt": "0112", "MktNm": "Standard"},
        ],
        endpoint="/v2/equities/master",
        collection="jquants/listed_issues",
    )


def test_inspect_daily_quote_exclusions_classifies_and_saves_report(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_exclusion_fixture(runtime_dir)

    exit_code = main(["--runtime-dir", str(runtime_dir), "--input-format", "jsonl", "--output", "json", "--save-report"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out.split("json_report=")[0])
    assert exit_code == 0
    assert payload["excluded_count"] == 2
    assert payload["by_date"] == {"2026-06-01": 1, "2026-06-02": 1}
    assert payload["by_code"]["131A0"] == 1
    assert "unknown" in json.dumps(payload["by_estimated_reason"])
    assert payload["recommended_policy"]
    assert payload["joined_listed_issue_sample"][0]["CoName"] == "Alpha"
    assert (runtime_dir / "reports" / "phase1_final").exists()
    assert list((runtime_dir / "reports" / "phase1_final").glob("daily_quote_exclusions_*.json"))
    assert list((runtime_dir / "reports" / "phase1_final").glob("daily_quote_exclusions_*.md"))


def test_inspect_daily_quote_exclusions_does_not_leak_secret(tmp_path: Path, capsys, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    secret = "phase1-h-secret"
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    seed_exclusion_fixture(runtime_dir)

    main(["--runtime-dir", str(runtime_dir), "--input-format", "jsonl", "--save-report"])

    captured = capsys.readouterr()
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in (runtime_dir / "reports" / "phase1_final").glob("*"))
    assert secret not in captured.out
    assert secret not in captured.err
    assert secret not in report_text
