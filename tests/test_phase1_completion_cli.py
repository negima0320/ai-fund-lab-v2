import json
from pathlib import Path

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes, write_daily_quotes_normalized
from ai_fund_lab_v2.data_store import MarketDataStore, append_manifest_record, manifest_path, now_utc
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase1_completion import main as audit_main
from scripts.write_phase1_completion_report import main as report_main


def seed_phase1_runtime(runtime_dir: Path) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    paths.ensure_base_dirs()
    store = MarketDataStore(paths, raw_storage_format="jsonl")
    daily = [
        {"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100},
        {"Date": "2026-06-01", "Code": "131A0"},
    ]
    store.save_raw(daily, endpoint="/v2/equities/bars/daily", collection="jquants/equities_bars_daily")
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030", "CoName": "Toyota", "Mkt": "0111"}],
        endpoint="/v2/equities/master",
        collection="jquants/listed_issues",
    )
    store.save_raw(
        [{"Date": "2026-06-01", "HolDiv": "1"}, {"Date": "2026-06-02", "HolDiv": "1"}],
        endpoint="/v2/markets/calendar",
        collection="jquants/trading_calendar",
    )
    store.save_raw(
        [{"DiscDate": "2026-06-01", "Code": "72030"}],
        endpoint="/v2/fins/summary",
        collection="jquants/fins_summary",
    )
    normalized, _ = normalize_daily_quotes(daily)
    write_daily_quotes_normalized(paths, "jsonl", normalized)
    for endpoint, count in [
        ("/v2/equities/bars/daily", 2),
        ("/v2/equities/master", 1),
        ("/v2/markets/calendar", 2),
        ("/v2/fins/summary", 1),
    ]:
        append_manifest_record(
            manifest_path(paths.raw_data),
            {
                "fetched_at": now_utc(),
                "endpoint": endpoint,
                "record_count": count,
                "storage_format": "jsonl",
                "storage_path": str(paths.raw_data),
                "status": "SAVED",
                "validation_status": "OK",
                "schema_version": 1,
                "diff_summary": {},
                "request_params": {},
            },
        )


def test_audit_phase1_completion_includes_required_items_and_writes_reports(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_phase1_runtime(runtime_dir)

    exit_code = audit_main(["--runtime-dir", str(runtime_dir), "--output", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out.split("json_report=")[0])
    names = {item["name"] for item in payload["items"]}
    assert exit_code in (0, 1)
    assert "J-Quants接続" in names
    assert "AI/broker/orderに進んでいない" in names
    assert "normalized raw" in names
    assert payload["decision"] in ("完了", "条件付き完了", "未完了")
    assert (runtime_dir / "reports" / "phase1_final" / "phase1_completion_audit.json").exists()
    assert (runtime_dir / "reports" / "phase1_final" / "phase1_completion_audit.md").exists()


def test_write_phase1_completion_report_creates_docs_and_runtime_report(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_phase1_runtime(runtime_dir)

    exit_code = report_main(["--runtime-dir", str(runtime_dir)])

    docs_path = Path("docs/phase_reports/phase1_completion_report.md")
    runtime_path = runtime_dir / "reports" / "phase1_final" / "phase1_completion_report.md"
    assert exit_code == 0
    assert docs_path.exists()
    assert runtime_path.exists()
    text = docs_path.read_text(encoding="utf-8")
    assert "Phase1 Completion Report" in text
    assert "Explicitly Not Implemented In Phase1" in text
    assert "daily_quotes_normalized" in text
