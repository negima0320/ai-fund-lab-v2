from pathlib import Path

import pytest

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data_store import JsonlStorageBackend, StorageBackendError, create_storage_backend


def test_raw_storage_format_setting_is_read() -> None:
    settings = load_settings({"JQUANTS_API_KEY": "test", "AI_FUND_LAB_RAW_STORAGE_FORMAT": "jsonl"})

    assert settings.raw_storage_format == "jsonl"


def test_jsonl_backend_writes_and_reads(tmp_path: Path) -> None:
    backend = JsonlStorageBackend()
    path = backend.path_for(tmp_path / "data")

    backend.write_records(path, [{"a": 1}, {"a": 2}])

    assert path == tmp_path / "data.jsonl"
    assert backend.read_records(path) == [{"a": 1}, {"a": 2}]


def test_unsupported_storage_format_raises_clear_error() -> None:
    with pytest.raises(StorageBackendError, match="Unsupported raw storage format"):
        create_storage_backend("xml")


def test_parquet_backend_writes_and_reads(tmp_path: Path) -> None:
    backend = create_storage_backend("parquet")
    path = backend.path_for(tmp_path / "data")

    backend.write_records(path, [{"a": "1"}, {"a": "2"}])

    assert path == tmp_path / "data.parquet"
    assert backend.read_records(path) == [{"a": "1"}, {"a": "2"}]


def test_parquet_backend_normalizes_missing_values_to_none(tmp_path: Path) -> None:
    backend = create_storage_backend("parquet")
    path = backend.path_for(tmp_path / "data")

    backend.write_records(path, [{"a": 1.0}, {"a": None}])

    assert backend.read_records(path)[1]["a"] is None
