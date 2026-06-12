from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ai_fund_lab_v2.runtime.paths import RuntimePaths


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class JQuantsSettings:
    api_key: str | None
    base_url: str = "https://api.jquants.com"
    rate_limit_per_minute: int = 60
    timeout_seconds: float = 30.0

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ConfigurationError(
                "JQUANTS_API_KEY is required for J-Quants API access. "
                "Set it in your environment or local .env file; never commit it."
            )
        return self.api_key


@dataclass(frozen=True)
class AppSettings:
    runtime_paths: RuntimePaths
    jquants: JQuantsSettings
    raw_storage_format: str = "jsonl"


def load_settings(env: Mapping[str, str] | None = None) -> AppSettings:
    if env is None:
        load_dotenv_file()
    values = os.environ if env is None else env

    runtime_paths = RuntimePaths(
        runtime_dir=Path(values.get("AI_FUND_LAB_RUNTIME_DIR", ".runtime")),
        data_dir=_optional_path(values, "AI_FUND_LAB_DATA_DIR"),
        log_dir=_optional_path(values, "AI_FUND_LAB_LOG_DIR"),
        cache_dir=_optional_path(values, "AI_FUND_LAB_CACHE_DIR"),
        report_dir=_optional_path(values, "AI_FUND_LAB_REPORT_DIR"),
        tmp_dir=_optional_path(values, "AI_FUND_LAB_TMP_DIR"),
    )

    return AppSettings(
        runtime_paths=runtime_paths,
        jquants=JQuantsSettings(
            api_key=_blank_to_none(values.get("JQUANTS_API_KEY")),
            base_url=values.get("JQUANTS_BASE_URL", "https://api.jquants.com").rstrip("/"),
            rate_limit_per_minute=int(values.get("JQUANTS_RATE_LIMIT_PER_MINUTE", "60")),
            timeout_seconds=float(values.get("JQUANTS_TIMEOUT_SECONDS", "30")),
        ),
        raw_storage_format=values.get("AI_FUND_LAB_RAW_STORAGE_FORMAT", "jsonl").strip().lower(),
    )


def load_dotenv_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _optional_path(values: Mapping[str, str], name: str) -> Path | None:
    value = _blank_to_none(values.get(name))
    return Path(value) if value else None


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
