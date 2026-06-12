from pathlib import Path

from ai_fund_lab_v2.data_store import ManifestEntry, append_manifest, manifest_path, now_utc
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.show_jquants_manifest import main


def write_manifest(runtime_dir: Path) -> None:
    paths = RuntimePaths(runtime_dir=runtime_dir)
    append_manifest(
        manifest_path(paths.raw_data),
        ManifestEntry(
            fetched_at=now_utc(),
            endpoint="/v2/equities/bars/daily",
            target_date="2026-06-01",
            from_date=None,
            to_date=None,
            record_count=0,
            storage_format="jsonl",
            storage_path=str(paths.raw_data / "jquants" / "equities_bars_daily" / "data.jsonl"),
            status="OK",
            validation_status="ERROR",
            schema_version=1,
            diff_summary={"inserted_count": 0, "updated_count": 0, "unchanged_count": 0, "duplicate_key_count": 0},
            request_params={"endpoint_name": "daily_quotes"},
        ),
    )
    append_manifest(
        manifest_path(paths.raw_data),
        ManifestEntry(
            fetched_at=now_utc(),
            endpoint="/v2/equities/master",
            target_date="2026-06-01",
            from_date=None,
            to_date=None,
            record_count=10,
            storage_format="parquet",
            storage_path=str(paths.raw_data / "jquants" / "listed_issues" / "data.parquet"),
            status="MIGRATED",
            validation_status="OK",
            schema_version=1,
            diff_summary={"inserted_count": 10, "updated_count": 0, "unchanged_count": 0, "duplicate_key_count": 0},
            request_params={"endpoint_name": "listed_issues"},
        ),
    )


def test_show_jquants_manifest_latest_table(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_manifest(runtime_dir)

    main(["--endpoint", "daily_quotes", "--runtime-dir", str(runtime_dir), "--latest"])

    output = capsys.readouterr().out
    assert "schema" in output
    assert "/v2/equities/bars/daily" in output
    assert "ERROR" in output


def test_show_jquants_manifest_needs_refetch(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_manifest(runtime_dir)

    main(["--endpoint", "daily_quotes", "--runtime-dir", str(runtime_dir), "--needs-refetch"])

    output = capsys.readouterr().out
    assert "validation_status_not_ok" in output
    assert "/v2/equities/bars/daily" in output


def test_show_jquants_manifest_filters_and_summary(tmp_path: Path, capsys) -> None:
    runtime_dir = tmp_path / "runtime"
    write_manifest(runtime_dir)

    main(["--endpoint", "all", "--runtime-dir", str(runtime_dir), "--storage-format", "parquet", "--validation-status", "OK", "--summary"])

    output = capsys.readouterr().out
    assert "manifest_count" in output
    assert "/v2/equities/master" in output
    assert "/v2/equities/bars/daily" not in output
