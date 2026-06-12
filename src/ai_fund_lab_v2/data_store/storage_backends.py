from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class StorageBackendError(RuntimeError):
    """Raised when a storage backend cannot be used."""


class StorageBackend(Protocol):
    format_name: str

    def read_records(self, path: Path) -> list[dict]:
        ...

    def write_records(self, path: Path, records: list[dict]) -> None:
        ...

    def path_for(self, base_path: Path) -> Path:
        ...


@dataclass(frozen=True)
class JsonlStorageBackend:
    format_name: str = "jsonl"

    def read_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def write_records(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def path_for(self, base_path: Path) -> Path:
        return base_path.with_suffix(".jsonl")


@dataclass(frozen=True)
class ParquetStorageBackend:
    format_name: str = "parquet"

    def read_records(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            import pandas as pd
        except ImportError as exc:
            raise StorageBackendError("Parquet backend requires pandas and pyarrow.") from exc
        frame = pd.read_parquet(path)
        return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")

    def write_records(self, path: Path, records: list[dict]) -> None:
        try:
            import pandas as pd
        except ImportError as exc:
            raise StorageBackendError("Parquet backend requires pandas and pyarrow.") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(records)
        frame.to_parquet(path, index=False, engine="pyarrow")

    def path_for(self, base_path: Path) -> Path:
        return base_path.with_suffix(".parquet")


def create_storage_backend(format_name: str) -> StorageBackend:
    normalized = format_name.strip().lower()
    if normalized == "jsonl":
        return JsonlStorageBackend()
    if normalized == "parquet":
        return ParquetStorageBackend()
    raise StorageBackendError(f"Unsupported raw storage format: {format_name}. Supported: jsonl, parquet")
