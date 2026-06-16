from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.canonical_data_source import (
    load_phase9_data_source_config,
    resolve_data_source,
    resolve_phase9_data_sources,
)


def _config(path: Path, quotes: Path | str | None, listed: Path | str | None = None) -> None:
    path.write_text(
        "\n".join(
            [
                "phase9_data_sources:",
                f"  normalized_daily_quotes: {quotes if quotes is not None else 'null'}",
                f"  listed_info: {listed if listed is not None else 'null'}",
                "  raw_daily_quotes: null",
                "  trading_calendar: null",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_canonical_config_load_and_config_priority(tmp_path: Path) -> None:
    quotes = tmp_path / "jquants/quotes.parquet"
    quotes.parent.mkdir(parents=True)
    quotes.write_text("placeholder", encoding="utf-8")
    config = tmp_path / "phase9.yaml"
    _config(config, quotes)

    loaded = load_phase9_data_source_config(config)
    ref = resolve_data_source("normalized_daily_quotes", config_path=config)

    assert loaded["normalized_daily_quotes"] == str(quotes)
    assert ref.source == "config"
    assert ref.path == str(quotes)
    assert ref.usable_for_phase9 is True


def test_cli_override_priority(tmp_path: Path) -> None:
    config_path = tmp_path / "phase9.yaml"
    configured = tmp_path / "jquants/configured.parquet"
    override = tmp_path / "jquants/override.parquet"
    configured.parent.mkdir(parents=True)
    configured.write_text("configured", encoding="utf-8")
    override.write_text("override", encoding="utf-8")
    _config(config_path, configured)

    ref = resolve_data_source("normalized_daily_quotes", override_path=override, config_path=config_path)

    assert ref.source == "cli_override"
    assert ref.path == str(override)


def test_fallback_recorded(tmp_path: Path, monkeypatch) -> None:
    fallback = tmp_path / ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"
    fallback.parent.mkdir(parents=True)
    pd.DataFrame([{"target_date": "2026-06-15"}]).to_parquet(fallback, index=False)
    monkeypatch.chdir(tmp_path)

    ref = resolve_data_source("normalized_daily_quotes", config_path=tmp_path / "missing.yaml", allow_fallback=True)

    assert ref.source == "fallback"
    assert ref.fallback_used is True
    assert ref.usable_for_phase9 is True


def test_prohibited_source_rejected(tmp_path: Path) -> None:
    broker_path = tmp_path / "broker/snapshot.parquet"
    broker_path.parent.mkdir(parents=True)
    broker_path.write_text("x", encoding="utf-8")

    ref = resolve_data_source("normalized_daily_quotes", override_path=broker_path, config_path=tmp_path / "missing.yaml")

    assert ref.usable_for_phase9 is False
    assert "normalized_daily_quotes_prohibited_source_path" in ref.blocked_reasons


def test_resolve_all_keys(tmp_path: Path) -> None:
    config = tmp_path / "phase9.yaml"
    _config(config, None)

    refs = resolve_phase9_data_sources(config_path=config)

    assert "normalized_daily_quotes" in refs
    assert refs["normalized_daily_quotes"].usable_for_phase9 is False
