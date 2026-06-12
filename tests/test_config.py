from pathlib import Path

import pytest

from ai_fund_lab_v2.config import ConfigurationError, load_settings


def test_load_settings_defaults_to_runtime_tree() -> None:
    settings = load_settings({"JQUANTS_API_KEY": "test-key"})

    assert settings.runtime_paths.runtime_dir == Path(".runtime")
    assert settings.runtime_paths.raw_data == Path(".runtime/data/raw")
    assert settings.runtime_paths.feature_data == Path(".runtime/data/features")
    assert settings.runtime_paths.label_data == Path(".runtime/data/labels")
    assert settings.jquants.base_url == "https://api.jquants.com"
    assert settings.jquants.rate_limit_per_minute == 60


def test_load_settings_allows_runtime_overrides(tmp_path: Path) -> None:
    settings = load_settings(
        {
            "JQUANTS_API_KEY": "test-key",
            "AI_FUND_LAB_RUNTIME_DIR": str(tmp_path / "runtime"),
            "AI_FUND_LAB_DATA_DIR": str(tmp_path / "external-data"),
            "AI_FUND_LAB_LOG_DIR": str(tmp_path / "external-logs"),
            "AI_FUND_LAB_CACHE_DIR": str(tmp_path / "external-cache"),
            "AI_FUND_LAB_REPORT_DIR": str(tmp_path / "external-reports"),
            "AI_FUND_LAB_TMP_DIR": str(tmp_path / "external-tmp"),
        }
    )

    assert settings.runtime_paths.raw_data == tmp_path / "external-data" / "raw"
    assert settings.runtime_paths.logs == tmp_path / "external-logs"
    assert settings.runtime_paths.cache == tmp_path / "external-cache"
    assert settings.runtime_paths.reports == tmp_path / "external-reports"
    assert settings.runtime_paths.tmp == tmp_path / "external-tmp"


def test_missing_jquants_api_key_raises_clear_error() -> None:
    settings = load_settings({})

    with pytest.raises(ConfigurationError, match="JQUANTS_API_KEY is required"):
        settings.jquants.require_api_key()
