import json
from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.migrate_raw_storage import main


def seed_daily_jsonl(runtime_dir: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir), raw_storage_format="jsonl")
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )


def test_migrate_raw_storage_dry_run_does_not_create_parquet(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_daily_jsonl(runtime_dir)

    main(["--endpoint", "daily_quotes", "--from-format", "jsonl", "--to-format", "parquet", "--runtime-dir", str(runtime_dir), "--dry-run"])

    output = capsys.readouterr().out
    assert "daily_quotes: jsonl->parquet records=1 schema_version=1" in output
    assert not (runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet").exists()


def test_migrate_raw_storage_creates_parquet_and_manifest(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    seed_daily_jsonl(runtime_dir)

    main(["--endpoint", "daily_quotes", "--from-format", "jsonl", "--to-format", "parquet", "--runtime-dir", str(runtime_dir), "--validate"])

    parquet_path = runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    manifest_path = runtime_dir / "data" / "raw" / "jquants" / "manifest.jsonl"
    assert parquet_path.exists()
    assert (runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.jsonl").exists()
    entry = json.loads(manifest_path.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["status"] == "MIGRATED"
    assert entry["schema_version"] == 1
    assert entry["storage_format"] == "parquet"
    assert entry["diff_summary"]["target_record_count"] == 1
