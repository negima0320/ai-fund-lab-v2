from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.safe_train_until import resolve_safe_train_until


def test_safe_train_until_uses_20_business_days(tmp_path: Path) -> None:
    calendar = tmp_path / "jquants/calendar.parquet"
    calendar.parent.mkdir(parents=True)
    dates = pd.bdate_range("2026-05-01", "2026-06-15").strftime("%Y-%m-%d").tolist()
    pd.DataFrame({"Date": dates, "HolDiv": ["1"] * len(dates)}).to_parquet(calendar, index=False)

    result = resolve_safe_train_until(
        data_until="2026-06-15",
        label_horizon_business_days=20,
        trading_calendar_path=calendar,
    )

    assert result.safe_train_until == dates[-21]
    assert result.blocked_reasons == ()


def test_missing_label_horizon_is_blocked() -> None:
    result = resolve_safe_train_until(data_until="2026-06-15", label_horizon_business_days=None)

    assert "missing_label_horizon" in result.blocked_reasons


def test_policy_train_until_not_required() -> None:
    result = resolve_safe_train_until(
        data_until="2026-06-15",
        label_horizon_business_days=None,
        train_until_required=False,
    )

    assert result.safe_train_until == ""
    assert result.train_until_required is False
    assert result.blocked_reasons == ()
