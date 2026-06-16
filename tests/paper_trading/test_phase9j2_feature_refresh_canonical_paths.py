from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.feature_refresh import FEATURE_REFRESH_FAILED, run_feature_refresh


def _write_quotes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for day in pd.bdate_range("2026-05-01", periods=32):
        rows.append(
            {
                "target_date": day.strftime("%Y-%m-%d"),
                "Date": day.strftime("%Y-%m-%d"),
                "code": "10010",
                "Code": "10010",
                "Close": 100,
                "Volume": 1000,
            }
        )
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"target_date": "2026-06-15", "Date": "2026-06-15", "code": "10010", "Code": "10010"}]).to_parquet(path, index=False)


def _write_config(path: Path, *, quotes: Path | None, listed: Path | None) -> None:
    path.write_text(
        "\n".join(
            [
                "phase9_data_sources:",
                f"  normalized_daily_quotes: {quotes if quotes else 'null'}",
                f"  listed_info: {listed if listed else 'null'}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_feature_refresh_uses_canonical_resolver_and_records_manifest(tmp_path: Path) -> None:
    quotes = tmp_path / "jquants/quotes.parquet"
    listed = tmp_path / "jquants/listed.parquet"
    config = tmp_path / "phase9.yaml"
    _write_quotes(quotes)
    _write_listed(listed)
    _write_config(config, quotes=quotes, listed=listed)

    result = run_feature_refresh(
        target_data_until="2026-06-15",
        dry_run=False,
        execute=True,
        config_path=config,
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert manifest["artifacts"][0]["source_data_refs"]["normalized_daily_quotes_resolution"]["source"] == "config"
    assert manifest["artifacts"][0]["source_data_refs"]["normalized_daily_quotes"] == str(quotes)
    assert result.model_retraining_executed is False
    assert result.inference_executed is False
    assert result.order_plan_generation_executed is False
    assert result.broker_order_api_called is False


def test_missing_canonical_normalized_path_fail_closed(tmp_path: Path) -> None:
    listed = tmp_path / "jquants/listed.parquet"
    config = tmp_path / "phase9.yaml"
    _write_listed(listed)
    _write_config(config, quotes=None, listed=listed)

    result = run_feature_refresh(
        target_data_until="2026-06-15",
        dry_run=False,
        execute=True,
        config_path=config,
        feature_output_root=tmp_path / "features",
        manifest_root=tmp_path / "manifest",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    assert result.status == FEATURE_REFRESH_FAILED
    assert "normalized_daily_quotes_canonical_path_missing" in result.blocked_reasons
