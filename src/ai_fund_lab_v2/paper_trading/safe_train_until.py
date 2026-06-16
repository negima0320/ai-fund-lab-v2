from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SafeTrainUntilResult:
    data_until: str
    label_horizon_business_days: int | None
    safe_train_until: str
    calendar_source: str
    train_until_required: bool = True
    blocked_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["warnings"] = list(self.warnings)
        return payload


def resolve_safe_train_until(
    *,
    data_until: str,
    label_horizon_business_days: int | None,
    trading_calendar_path: Path | str | None = None,
    train_until_required: bool = True,
) -> SafeTrainUntilResult:
    blocked: list[str] = []
    warnings: list[str] = []
    if not train_until_required:
        return SafeTrainUntilResult(
            data_until=data_until,
            label_horizon_business_days=label_horizon_business_days,
            safe_train_until="",
            calendar_source="not_required",
            train_until_required=False,
        )
    if not data_until:
        blocked.append("missing_data_until")
    if label_horizon_business_days is None:
        blocked.append("missing_label_horizon")
    elif label_horizon_business_days < 0:
        blocked.append("invalid_label_horizon")
    if blocked:
        return SafeTrainUntilResult(
            data_until=data_until,
            label_horizon_business_days=label_horizon_business_days,
            safe_train_until="",
            calendar_source="unresolved",
            blocked_reasons=tuple(blocked),
        )

    calendar = _business_days_from_calendar(Path(trading_calendar_path)) if trading_calendar_path else []
    source = "trading_calendar" if calendar else "weekday_fallback"
    if not calendar:
        warnings.append("trading_calendar_missing_or_unusable_weekday_fallback_used")
        calendar = _weekday_business_days(end_date=data_until, days=max(260, label_horizon_business_days + 30))
    visible = sorted(day for day in calendar if day <= data_until)
    if len(visible) <= label_horizon_business_days:
        blocked.append("insufficient_calendar_history_for_label_horizon")
        safe = ""
    else:
        safe = visible[-(label_horizon_business_days + 1)]
    return SafeTrainUntilResult(
        data_until=data_until,
        label_horizon_business_days=label_horizon_business_days,
        safe_train_until=safe,
        calendar_source=source,
        blocked_reasons=tuple(blocked),
        warnings=tuple(warnings),
    )


def _business_days_from_calendar(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    try:
        frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    except Exception:
        return []
    if frame.empty:
        return []
    date_column = "Date" if "Date" in frame.columns else "date" if "date" in frame.columns else "target_date"
    dates = frame[date_column].astype(str)
    if "HolDiv" in frame.columns:
        return sorted(dates[frame["HolDiv"].astype(str) == "1"].tolist())
    if "is_business_day" in frame.columns:
        return sorted(dates[frame["is_business_day"].astype(bool)].tolist())
    return sorted(day for day in dates.tolist() if _is_weekday(day))


def _weekday_business_days(*, end_date: str, days: int) -> list[str]:
    current = datetime.strptime(end_date, "%Y-%m-%d").date()
    values: list[str] = []
    while len(values) < days:
        if current.weekday() < 5:
            values.append(current.isoformat())
        current -= timedelta(days=1)
    return sorted(values)


def _is_weekday(value: str) -> bool:
    try:
        return date.fromisoformat(value).weekday() < 5
    except ValueError:
        return False
