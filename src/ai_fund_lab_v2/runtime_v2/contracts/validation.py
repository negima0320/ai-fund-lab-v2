"""Pure validation helpers for Runtime v2 current state contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ai_fund_lab_v2.runtime_v2.contracts.current_state_contracts import (
    CURRENT_STATE_CONTRACTS,
)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    object_type: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    state: str | None = None


def validate_required_fields(
    payload: Mapping[str, Any],
    required_fields: Sequence[str],
) -> ValidationResult:
    """Validate that a mapping contains all required top-level fields."""

    if not isinstance(payload, Mapping):
        return ValidationResult(
            ok=False,
            object_type="unknown",
            errors=("payload must be a mapping",),
            state="INVALID",
        )
    missing = tuple(field for field in required_fields if field not in payload)
    if missing:
        return ValidationResult(
            ok=False,
            object_type=str(payload.get("object_type", "unknown")),
            errors=tuple(f"missing required field: {field}" for field in missing),
            state="INVALID",
        )
    return ValidationResult(
        ok=True,
        object_type=str(payload.get("object_type", "unknown")),
        state="VALID",
    )


def validate_json_object(payload: object, object_type: str) -> ValidationResult:
    """Validate a JSON object payload for a snapshot current contract."""

    contract = _get_contract(object_type)
    if contract.file_kind != "json":
        return ValidationResult(
            ok=False,
            object_type=object_type,
            errors=(f"{object_type} is not a json object contract",),
            state="INVALID",
        )
    if not isinstance(payload, Mapping):
        return ValidationResult(
            ok=False,
            object_type=object_type,
            errors=("payload must be a mapping",),
            state="INVALID",
        )
    return _with_object_type(
        validate_required_fields(payload, contract.required_fields),
        object_type,
    )


def validate_jsonl_record(payload: object, object_type: str) -> ValidationResult:
    """Validate one JSONL record payload for an append-only current contract."""

    contract = _get_contract(object_type)
    if contract.file_kind != "jsonl":
        return ValidationResult(
            ok=False,
            object_type=object_type,
            errors=(f"{object_type} is not a jsonl record contract",),
            state="INVALID",
        )
    if not isinstance(payload, Mapping):
        return ValidationResult(
            ok=False,
            object_type=object_type,
            errors=("payload must be a mapping",),
            state="INVALID",
        )
    return _with_object_type(
        validate_required_fields(payload, contract.required_fields),
        object_type,
    )


def _get_contract(object_type: str):
    try:
        return CURRENT_STATE_CONTRACTS[object_type]
    except KeyError as exc:
        raise ValueError(f"unsupported current contract object_type: {object_type}") from exc


def _with_object_type(result: ValidationResult, object_type: str) -> ValidationResult:
    return ValidationResult(
        ok=result.ok,
        object_type=object_type,
        errors=result.errors,
        warnings=result.warnings,
        state=result.state,
    )
