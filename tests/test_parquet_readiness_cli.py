from pathlib import Path

from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.check_parquet_readiness import main


def test_parquet_readiness_not_ready_when_parquet_missing(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    store = MarketDataStore(RuntimePaths(runtime_dir=runtime_dir), raw_storage_format="jsonl")
    store.save_raw(
        [{"Date": "2026-06-01", "Code": "72030", "O": 1, "H": 2, "L": 1, "C": 2, "Vo": 100}],
        endpoint="/v2/equities/bars/daily",
        collection="jquants/equities_bars_daily",
    )

    exit_code = main(["--runtime-dir", str(runtime_dir)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '"status": "NOT_READY"' in output
    assert "parquet_file_missing" in output
