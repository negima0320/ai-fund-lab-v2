from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ai_fund_lab_v2.candidate_ai.schemas import CandidateFeatureAudit
from ai_fund_lab_v2.candidate_ai.validation import validate_feature_table


def audit_feature_table(table: Any) -> CandidateFeatureAudit:
    rows = _rows_from_table(table)
    validation = validate_feature_table(rows)
    columns = _columns_from_rows(rows)
    forbidden_columns = validation.forbidden_columns
    future_column_detected = any(_is_future_column(column) for column in forbidden_columns)
    label_column_detected = any("label" in column.lower() for column in forbidden_columns)
    post_as_of_data_detected = bool(validation.invalid_date_rows)
    status = "OK" if validation.is_valid else "ERROR"
    return CandidateFeatureAudit(
        status=status,
        feature_version=_first_value(rows, "feature_version"),
        as_of_date=_first_value(rows, "as_of_date"),
        target_date=_first_value(rows, "target_date"),
        row_count=len(rows),
        forbidden_feature_detected=bool(forbidden_columns),
        forbidden_columns=forbidden_columns,
        future_column_detected=future_column_detected,
        label_column_detected=label_column_detected,
        post_as_of_data_detected=post_as_of_data_detected,
        target_date_leakage_detected=post_as_of_data_detected,
        missing_required_columns=validation.missing_required_columns,
        invalid_prefix_columns=validation.invalid_prefix_columns,
        eligible_count=sum(1 for row in rows if _is_true(row.get("universe_eligible"))),
        excluded_count=sum(1 for row in rows if not _is_true(row.get("universe_eligible"))),
        excluded_reason_counts=dict(_excluded_reason_counts(rows)),
        messages=validation.messages,
    )


def _rows_from_table(table: Any) -> list[Mapping[str, Any]]:
    if hasattr(table, "to_dict") and hasattr(table, "columns"):
        return [dict(row) for row in table.to_dict("records")]
    if isinstance(table, Mapping):
        return [table]
    return [dict(row) for row in table]


def _columns_from_rows(rows: list[Mapping[str, Any]]) -> tuple[str, ...]:
    columns: set[str] = set()
    for row in rows:
        columns.update(str(column) for column in row.keys())
    return tuple(sorted(columns))


def _is_future_column(column: str) -> bool:
    normalized = column.lower()
    return normalized.startswith(("future_return_", "future_max_return_", "future_max_drawdown_"))


def _first_value(rows: list[Mapping[str, Any]], key: str) -> str | None:
    for row in rows:
        value = row.get(key)
        if value is not None:
            return str(value)
    return None


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    if isinstance(value, str):
        return value.lower() in {"true", "1"}
    return False


def _excluded_reason_counts(rows: list[Mapping[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        if _is_true(row.get("universe_eligible")):
            continue
        reason = str(row.get("excluded_reason") or "unknown")
        counter[reason] += 1
    return counter
