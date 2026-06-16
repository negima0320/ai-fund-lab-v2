from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.training_dataset_candidate import build_training_dataset_candidates


def test_training_dataset_candidates_generate_manifest_and_no_training(tmp_path: Path) -> None:
    quotes = tmp_path / "jquants/quotes.parquet"
    listed = tmp_path / "jquants/listed.parquet"
    calendar = tmp_path / "jquants/calendar.parquet"
    _write_quotes(quotes)
    _write_listed(listed)
    _write_calendar(calendar)

    result = build_training_dataset_candidates(
        normalized_daily_quotes_path=quotes,
        listed_info_path=listed,
        trading_calendar_path=calendar,
        data_until="2026-06-15",
        safe_train_until="2026-05-18",
        train_until="2026-05-18",
        label_horizon=20,
        output_root=tmp_path / "out",
    )

    assert result.status == "TRAINING_DATASETS_READY"
    assert Path(result.manifest_path).is_file()
    assert all(item.feature_schema_hash for item in result.datasets)
    assert all(item.max_date <= "2026-05-18" for item in result.datasets)
    assert result.model_retraining_executed is False
    assert result.inference_executed is False
    assert result.order_plan_generation_executed is False
    assert result.broker_order_api_called is False
    assert result.virtual_fill_executed is False


def test_candidate_builder_blocks_train_until_after_safe_train_until(tmp_path: Path) -> None:
    quotes = tmp_path / "jquants/quotes.parquet"
    listed = tmp_path / "jquants/listed.parquet"
    calendar = tmp_path / "jquants/calendar.parquet"
    _write_quotes(quotes)
    _write_listed(listed)
    _write_calendar(calendar)

    result = build_training_dataset_candidates(
        normalized_daily_quotes_path=quotes,
        listed_info_path=listed,
        trading_calendar_path=calendar,
        data_until="2026-06-15",
        safe_train_until="2026-05-18",
        train_until="2026-05-19",
        label_horizon=20,
        output_root=tmp_path / "out",
    )

    assert result.status == "TRAINING_DATASET_BLOCKED"
    assert any("train_until_after_safe_train_until" in item.blocked_reasons for item in result.datasets)


def _write_quotes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for code in ("10010", "10020"):
        base = 100.0 if code == "10010" else 200.0
        for index, day in enumerate(pd.bdate_range("2026-03-02", "2026-06-15")):
            rows.append({"date": day.strftime("%Y-%m-%d"), "code": code, "close": base + index, "volume": 1000 + index})
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": "2026-06-15", "Code": "10010"}, {"Date": "2026-06-15", "Code": "10020"}]).to_parquet(path, index=False)


def _write_calendar(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dates = pd.bdate_range("2026-03-02", "2026-06-15").strftime("%Y-%m-%d").tolist()
    pd.DataFrame({"Date": dates, "HolDiv": ["1"] * len(dates)}).to_parquet(path, index=False)
