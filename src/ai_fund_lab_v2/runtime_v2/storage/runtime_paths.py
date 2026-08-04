from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    """Runtime v2 path layout for generated data, logs, cache, reports, and tmp files."""

    runtime_dir: Path = Path(".runtime")
    data_dir: Path | None = None
    log_dir: Path | None = None
    cache_dir: Path | None = None
    report_dir: Path | None = None
    tmp_dir: Path | None = None

    @property
    def data(self) -> Path:
        return self.data_dir or self.runtime_dir / "data"

    @property
    def raw_data(self) -> Path:
        return self.data / "raw"

    @property
    def raw_normalized_data(self) -> Path:
        return self.data / "raw_normalized"

    @property
    def feature_data(self) -> Path:
        return self.data / "features"

    @property
    def label_data(self) -> Path:
        return self.data / "labels"

    @property
    def logs(self) -> Path:
        return self.log_dir or self.runtime_dir / "logs"

    @property
    def cache(self) -> Path:
        return self.cache_dir or self.runtime_dir / "cache"

    @property
    def reports(self) -> Path:
        return self.report_dir or self.runtime_dir / "reports"

    @property
    def tmp(self) -> Path:
        return self.tmp_dir or self.runtime_dir / "tmp"

    def ensure_base_dirs(self) -> None:
        for path in self.iter_base_dirs():
            path.mkdir(parents=True, exist_ok=True)

    def ensure_data_dirs(self) -> None:
        for path in (self.raw_data, self.raw_normalized_data, self.feature_data, self.label_data):
            path.mkdir(parents=True, exist_ok=True)

    def iter_base_dirs(self) -> tuple[Path, ...]:
        return (
            self.raw_data,
            self.raw_normalized_data,
            self.feature_data,
            self.label_data,
            self.logs,
            self.cache,
            self.reports,
            self.tmp,
        )
