import json
from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore, read_manifest
from ai_fund_lab_v2.data_store.manifest import manifest_path
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.normalize_jquants_raw import main


def seed_adjusted_daily(runtime_dir: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir), raw_storage_format="jsonl")
    store.save_raw(
        [
            {
                "Date": "2026-06-01",
                "Code": "72030",
                "AdjO": 10,
                "AdjH": 11,
                "AdjL": 9,
                "AdjC": 10,
                "AdjVo": 100,
            }
        ],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )


def test_normalize_jquants_raw_dry_run_does_not_save(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_adjusted_daily(runtime_dir)

    exit_code = main(
        [
            "--endpoint",
            "daily_quotes",
            "--runtime-dir",
            str(runtime_dir),
            "--input-format",
            "jsonl",
            "--output-format",
            "jsonl",
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "dry_run=True api_call=False save=False manifest=False" in output
    assert not (runtime_dir / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.jsonl").exists()


def test_normalize_jquants_raw_saves_normalized_and_manifest(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_adjusted_daily(runtime_dir)

    exit_code = main(
        [
            "--endpoint",
            "daily_quotes",
            "--runtime-dir",
            str(runtime_dir),
            "--input-format",
            "jsonl",
            "--output-format",
            "jsonl",
            "--validate",
        ]
    )

    output = capsys.readouterr().out
    normalized_path = runtime_dir / "data" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.jsonl"
    rows = [json.loads(line) for line in normalized_path.read_text(encoding="utf-8").splitlines()]
    manifest_rows = read_manifest(manifest_path(runtime_dir / "data" / "raw"))
    assert exit_code == 0
    assert "validation=OK" in output
    assert rows[0]["Open"] == 10
    assert rows[0]["PriceSource"] == "adjusted"
    assert manifest_rows[-1]["event_type"] == "NORMALIZED"
    assert manifest_rows[-1]["source_endpoint"] == "/v2/equities/bars/daily"
    assert manifest_rows[-1]["normalized_endpoint"] == "daily_quotes_normalized"
    assert manifest_rows[-1]["raw_schema_version"] == 1
    assert manifest_rows[-1]["normalized_schema_version"] == 2


def test_normalize_jquants_raw_output_and_manifest_do_not_leak_secret(tmp_path: Path, capsys, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    secret = "normalization-secret-key"
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    seed_adjusted_daily(runtime_dir)

    main(
        [
            "--endpoint",
            "daily_quotes",
            "--runtime-dir",
            str(runtime_dir),
            "--input-format",
            "jsonl",
            "--output-format",
            "jsonl",
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest_text = manifest_path(runtime_dir / "data" / "raw").read_text(encoding="utf-8")
    assert secret not in captured.out
    assert secret not in captured.err
    assert secret not in manifest_text
