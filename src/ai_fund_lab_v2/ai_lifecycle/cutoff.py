from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class LabelSafeCutoff:
    latest_trading_date: str
    label_safe_cutoff: str
    target_horizon_business_days: int
    dataset_lag_business_days: int | None = None
    model_training_lag_business_days: int | None = None
    model_acceptance_age_business_days: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_label_safe_cutoff(
    *,
    trading_calendar: pd.DataFrame | Path | str,
    latest_trading_date: str | None = None,
    target_horizon_business_days: int = 20,
    dataset_max_date: str | None = None,
    model_training_date: str | None = None,
    model_acceptance_date: str | None = None,
) -> LabelSafeCutoff:
    calendar = _read_calendar(trading_calendar)
    dates = _trading_dates(calendar)
    if not dates:
        raise ValueError("trading calendar has no trading dates")
    latest = str(latest_trading_date or dates[-1])
    eligible = [date for date in dates if date <= latest]
    if len(eligible) <= target_horizon_business_days:
        raise ValueError("trading calendar is shorter than target horizon")
    cutoff = eligible[-(target_horizon_business_days + 1)]
    return LabelSafeCutoff(
        latest_trading_date=latest,
        label_safe_cutoff=cutoff,
        target_horizon_business_days=target_horizon_business_days,
        dataset_lag_business_days=_business_day_lag(dates, dataset_max_date, cutoff),
        model_training_lag_business_days=_business_day_lag(dates, model_training_date, cutoff),
        model_acceptance_age_business_days=_business_day_lag(dates, model_acceptance_date, latest),
    )


def _read_calendar(calendar: pd.DataFrame | Path | str) -> pd.DataFrame:
    if isinstance(calendar, pd.DataFrame):
        return calendar.copy()
    path = Path(calendar)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported trading calendar format: {path}")


def _trading_dates(calendar: pd.DataFrame) -> list[str]:
    date_column = next((column for column in ("target_date", "Date", "date", "business_date") if column in calendar.columns), None)
    if date_column is None:
        raise ValueError("trading calendar requires a date column")
    frame = calendar.copy()
    if "is_trading_day" in frame.columns:
        frame = frame[frame["is_trading_day"].astype(bool)]
    if "holiday" in frame.columns:
        frame = frame[~frame["holiday"].astype(bool)]
    return sorted(frame[date_column].dropna().astype(str).unique().tolist())


def _business_day_lag(dates: list[str], earlier: str | None, later: str | None) -> int | None:
    if earlier is None or later is None:
        return None
    eligible = [date for date in dates if earlier < date <= later]
    return len(eligible)
