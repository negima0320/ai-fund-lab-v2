from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.candidate_ai.schemas import (
    ALLOWED_FEATURE_PREFIXES,
    FORBIDDEN_FEATURE_TERMS,
    OPTIONAL_FEATURE_METADATA_COLUMNS,
    REQUIRED_FEATURE_COLUMNS,
)


@dataclass(frozen=True)
class FeatureTableValidationResult:
    is_valid: bool
    missing_required_columns: tuple[str, ...] = ()
    forbidden_columns: tuple[str, ...] = ()
    invalid_prefix_columns: tuple[str, ...] = ()
    invalid_date_rows: tuple[int, ...] = ()
    invalid_universe_eligible_rows: tuple[int, ...] = ()
    messages: tuple[str, ...] = ()


def validate_feature_table(table: Any) -> FeatureTableValidationResult:
    rows = _rows_from_table(table)
    columns = _columns_from_table(table, rows)
    missing_required = tuple(sorted(REQUIRED_FEATURE_COLUMNS - set(columns)))
    forbidden_columns = tuple(column for column in columns if is_forbidden_column(column))
    invalid_prefix_columns = tuple(column for column in columns if _is_invalid_feature_column(column))
    invalid_date_rows = tuple(index for index, row in enumerate(rows) if _row_has_invalid_dates(row))
    invalid_universe_rows = tuple(index for index, row in enumerate(rows) if not _universe_eligible_is_bool_like(row))
    messages = _build_messages(
        missing_required=missing_required,
        forbidden_columns=forbidden_columns,
        invalid_prefix_columns=invalid_prefix_columns,
        invalid_date_rows=invalid_date_rows,
        invalid_universe_rows=invalid_universe_rows,
    )
    return FeatureTableValidationResult(
        is_valid=not (
            missing_required
            or forbidden_columns
            or invalid_prefix_columns
            or invalid_date_rows
            or invalid_universe_rows
        ),
        missing_required_columns=missing_required,
        forbidden_columns=forbidden_columns,
        invalid_prefix_columns=invalid_prefix_columns,
        invalid_date_rows=invalid_date_rows,
        invalid_universe_eligible_rows=invalid_universe_rows,
        messages=messages,
    )


def is_forbidden_column(column: str) -> bool:
    normalized = column.strip().lower()
    if any(normalized.startswith(term) for term in FORBIDDEN_FEATURE_TERMS if term.endswith("_")):
        return True
    tokens = [token for token in normalized.replace("-", "_").split("_") if token]
    return any(term in tokens for term in FORBIDDEN_FEATURE_TERMS if not term.endswith("_"))


def _is_invalid_feature_column(column: str) -> bool:
    if column in REQUIRED_FEATURE_COLUMNS or column in OPTIONAL_FEATURE_METADATA_COLUMNS:
        return False
    return not column.startswith(ALLOWED_FEATURE_PREFIXES)


def _rows_from_table(table: Any) -> list[Mapping[str, Any]]:
    if hasattr(table, "to_dict") and hasattr(table, "columns"):
        records = table.to_dict("records")
        return [dict(row) for row in records]
    if isinstance(table, Mapping):
        return [table]
    if isinstance(table, Iterable) and not isinstance(table, (str, bytes)):
        return [dict(row) for row in table]
    raise TypeError("feature table must be a mapping, iterable of mappings, or DataFrame-like object")


def _columns_from_table(table: Any, rows: list[Mapping[str, Any]]) -> tuple[str, ...]:
    if hasattr(table, "columns"):
        return tuple(str(column) for column in table.columns)
    columns: set[str] = set()
    for row in rows:
        columns.update(str(column) for column in row.keys())
    return tuple(sorted(columns))


def _row_has_invalid_dates(row: Mapping[str, Any]) -> bool:
    if "as_of_date" not in row or "target_date" not in row:
        return False
    as_of_date = _parse_date(row.get("as_of_date"))
    target_date = _parse_date(row.get("target_date"))
    if as_of_date is None or target_date is None:
        return True
    return as_of_date > target_date


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _universe_eligible_is_bool_like(row: Mapping[str, Any]) -> bool:
    if "universe_eligible" not in row:
        return True
    value = row.get("universe_eligible")
    if isinstance(value, bool):
        return True
    if isinstance(value, int) and value in (0, 1):
        return True
    if isinstance(value, str) and value.lower() in {"true", "false", "0", "1"}:
        return True
    return False


def _build_messages(
    missing_required: tuple[str, ...],
    forbidden_columns: tuple[str, ...],
    invalid_prefix_columns: tuple[str, ...],
    invalid_date_rows: tuple[int, ...],
    invalid_universe_rows: tuple[int, ...],
) -> tuple[str, ...]:
    messages: list[str] = []
    if missing_required:
        messages.append(f"missing required columns: {', '.join(missing_required)}")
    if forbidden_columns:
        messages.append(f"forbidden columns detected: {', '.join(forbidden_columns)}")
    if invalid_prefix_columns:
        messages.append(f"invalid feature prefixes: {', '.join(invalid_prefix_columns)}")
    if invalid_date_rows:
        messages.append(f"as_of_date must be <= target_date at rows: {', '.join(map(str, invalid_date_rows))}")
    if invalid_universe_rows:
        messages.append(
            f"universe_eligible must be bool-like at rows: {', '.join(map(str, invalid_universe_rows))}"
        )
    return tuple(messages)
