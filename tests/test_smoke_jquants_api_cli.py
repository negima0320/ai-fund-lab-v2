from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import FetchResult
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.smoke_jquants_api import main


class FakeIngestor:
    def __init__(self, paths: RuntimePaths, calls: list[dict[str, Any]]) -> None:
        self.paths = paths
        self.calls = calls

    def fetch_and_store(self, endpoint_name: str, **kwargs: Any) -> FetchResult:
        self.calls.append({"endpoint_name": endpoint_name, **kwargs})
        output_path = self.paths.raw_data / "jquants" / endpoint_name / "data.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text('{"ok": true}\n', encoding="utf-8")
        return FetchResult(endpoint_name, f"/mock/{endpoint_name}", 1, str(output_path))


def test_smoke_dry_run_does_not_call_api_or_save(tmp_path: Path, capsys) -> None:
    calls: list[dict[str, Any]] = []
    runtime_dir = tmp_path / "runtime"

    exit_code = main(
        [
            "--endpoint",
            "daily_quotes",
            "--date",
            "2026-06-01",
            "--runtime-dir",
            str(runtime_dir),
            "--dry-run",
        ],
        ingestor_factory=lambda paths: FakeIngestor(paths, calls),
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == []
    assert "DRY-RUN endpoint=daily_quotes" in output
    assert "rate_limit_per_minute=60" in output
    assert "max_pages=1" in output
    assert not (runtime_dir / "data" / "raw" / "jquants" / "equities_bars_daily" / "data.jsonl").exists()


def test_smoke_all_dry_run_lists_all_endpoints(tmp_path: Path, capsys) -> None:
    main(["--endpoint", "all", "--date", "2026-06-01", "--runtime-dir", str(tmp_path / "runtime"), "--dry-run"])

    output = capsys.readouterr().out
    assert "endpoint=daily_quotes" in output
    assert "endpoint=listed_issues" in output
    assert "endpoint=trading_calendar" in output
    assert "endpoint=fins_summary" in output


def test_smoke_execution_passes_max_pages_and_uses_runtime_paths(tmp_path: Path, capsys) -> None:
    calls: list[dict[str, Any]] = []
    runtime_dir = tmp_path / "runtime"

    exit_code = main(
        [
            "--endpoint",
            "daily_quotes",
            "--date",
            "2026-06-01",
            "--runtime-dir",
            str(runtime_dir),
            "--max-pages",
            "1",
        ],
        ingestor_factory=lambda paths: FakeIngestor(paths, calls),
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls == [
        {
            "endpoint_name": "daily_quotes",
            "date": "2026-06-01",
            "from_date": None,
            "to_date": None,
            "max_pages": 1,
        }
    ]
    assert str(runtime_dir / "data" / "raw" / "jquants" / "daily_quotes" / "data.jsonl") in output
    assert (runtime_dir / "logs" / "smoke_jquants_api.log").exists()


def test_smoke_cli_does_not_print_or_log_api_key(tmp_path: Path, capsys, monkeypatch) -> None:
    secret = "live-smoke-secret-key"
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    calls: list[dict[str, Any]] = []
    runtime_dir = tmp_path / "runtime"

    main(
        ["--endpoint", "daily_quotes", "--date", "2026-06-01", "--runtime-dir", str(runtime_dir), "--max-pages", "1"],
        ingestor_factory=lambda paths: FakeIngestor(paths, calls),
    )

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    log_text = (runtime_dir / "logs" / "smoke_jquants_api.log").read_text(encoding="utf-8")
    assert secret not in log_text
    assert "x-api-key" not in log_text.lower()
    assert "authorization" not in log_text.lower()
