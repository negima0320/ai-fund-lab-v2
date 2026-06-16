from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.data_store import StorageBackendError, create_storage_backend
from ai_fund_lab_v2.runtime import RuntimePaths


READY = "READY"
NOT_READY = "NOT_READY"
INVALID = "INVALID"

OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class MarketDataReadinessResult:
    status: str
    data_until: str
    row_count: int
    missing_inputs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_market_data_readiness(
    *,
    decision_for: str,
    runtime_dir: Path | str = ".runtime",
    daily_quotes_path: Path | None = None,
    listed_info_path: Path | None = None,
    daily_quotes_records: list[Mapping[str, Any]] | None = None,
    listed_info_records: list[Mapping[str, Any]] | None = None,
) -> MarketDataReadinessResult:
    missing_inputs: list[str] = []
    warnings: list[str] = []
    blocked: list[str] = []

    daily_records = list(daily_quotes_records) if daily_quotes_records is not None else _read_records(
        daily_quotes_path or _discover_data_path(runtime_dir, "raw_normalized", "jquants/equities_bars_daily")
    )
    listed_records = list(listed_info_records) if listed_info_records is not None else _read_records(
        listed_info_path or _discover_data_path(runtime_dir, "raw", "jquants/listed_issues")
    )

    if daily_records is None:
        missing_inputs.append("daily_quotes")
        daily_records = []
    if listed_records is None:
        missing_inputs.append("listed_info")
        listed_records = []
    if missing_inputs:
        return MarketDataReadinessResult(
            status=NOT_READY,
            data_until="",
            row_count=0,
            missing_inputs=tuple(missing_inputs),
            blocked_reasons=tuple(f"missing_{item}" for item in missing_inputs),
        )
    if not daily_records:
        return MarketDataReadinessResult(
            status=NOT_READY,
            data_until="",
            row_count=0,
            blocked_reasons=("daily_quotes_row_count_zero",),
        )
    missing_schema = _schema_missing(daily_records[0])
    if missing_schema:
        return MarketDataReadinessResult(
            status=INVALID,
            data_until="",
            row_count=len(daily_records),
            blocked_reasons=tuple(f"missing_column_{column}" for column in missing_schema),
        )
    future_rows = [record for record in daily_records if _record_date(record) > decision_for]
    if future_rows:
        return MarketDataReadinessResult(
            status=INVALID,
            data_until=_latest_date(daily_records),
            row_count=len(daily_records),
            blocked_reasons=("future_row_detected",),
        )
    abnormal = [record for record in daily_records if _has_nonpositive_ohlcv(record)]
    if abnormal:
        warnings.append(f"nonpositive_ohlcv_row_count={len(abnormal)}")
    data_until = _latest_date(daily_records)
    if not data_until or data_until < decision_for:
        return MarketDataReadinessResult(
            status=NOT_READY,
            data_until=data_until,
            row_count=len(daily_records),
            warnings=tuple(warnings),
            blocked_reasons=("data_until_before_decision_for",),
        )
    return MarketDataReadinessResult(
        status=READY,
        data_until=data_until,
        row_count=len(daily_records),
        warnings=tuple(warnings),
    )


def _discover_data_path(runtime_dir: Path | str, root_attr: str, collection: str) -> Path | None:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    root = getattr(paths, f"{root_attr}_data")
    base = root / collection / "data"
    for storage_format in ("parquet", "jsonl"):
        path = create_storage_backend(storage_format).path_for(base)
        if path.exists():
            return path
    return None


def _read_records(path: Path | None) -> list[Mapping[str, Any]] | None:
    if path is None or not path.exists():
        return None
    suffix = path.suffix.lower().lstrip(".")
    storage_format = "parquet" if suffix == "parquet" else "jsonl"
    try:
        return create_storage_backend(storage_format).read_records(path)
    except (StorageBackendError, ImportError, RuntimeError):
        return None


def _schema_missing(record: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if not _value(record, "date"):
        missing.append("date")
    if not _value(record, "code"):
        missing.append("code")
    for column in OHLCV_COLUMNS:
        if _value(record, column) in (None, ""):
            missing.append(column)
    return missing


def _record_date(record: Mapping[str, Any]) -> str:
    return str(_value(record, "date") or "")


def _latest_date(records: list[Mapping[str, Any]]) -> str:
    dates = sorted(_record_date(record) for record in records if _record_date(record))
    return dates[-1] if dates else ""


def _has_nonpositive_ohlcv(record: Mapping[str, Any]) -> bool:
    for column in OHLCV_COLUMNS:
        try:
            if float(_value(record, column)) <= 0:
                return True
        except (TypeError, ValueError):
            return True
    return False


def _value(record: Mapping[str, Any], normalized_name: str) -> Any:
    aliases = {
        "date": ("date", "Date", "target_date"),
        "code": ("code", "Code", "business_key"),
        "open": ("open", "Open", "O", "AdjO"),
        "high": ("high", "High", "H", "AdjH"),
        "low": ("low", "Low", "L", "AdjL"),
        "close": ("close", "Close", "C", "AdjC"),
        "volume": ("volume", "Volume", "Vo", "AdjVo"),
    }
    for key in aliases[normalized_name]:
        if key in record:
            return record.get(key)
    return None

