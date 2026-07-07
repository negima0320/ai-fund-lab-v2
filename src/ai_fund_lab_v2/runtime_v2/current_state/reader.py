"""Current State Reader for Runtime v2 fixed current paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.contracts.current_state_contracts import (
    CURRENT_STATE_CONTRACTS,
)
from ai_fund_lab_v2.runtime_v2.contracts.validation import (
    ValidationResult,
    validate_json_object,
    validate_jsonl_record,
)
from ai_fund_lab_v2.runtime_v2.current_state.classifier import classify_current_state
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import resolve_current_path


def read_current_state(
    *,
    mode: str,
    environment: str,
    object_type: str,
    base_dir: Path | None = None,
):
    """Read and classify a Runtime v2 Current artifact from its fixed path."""

    relative_path = resolve_current_path(
        mode=mode,
        environment=environment,
        object_type=object_type,
    )
    path = (base_dir / relative_path) if base_dir is not None else relative_path
    contract = CURRENT_STATE_CONTRACTS[object_type]

    if not path.exists():
        return classify_current_state(
            object_type=object_type,
            exists=False,
            validation_ok=False,
            payload=None,
            errors=("current file missing",),
            path=path,
            expected_environment=environment,
        )

    try:
        payload = _read_payload(path, contract.file_kind)
    except ValueError as exc:
        return classify_current_state(
            object_type=object_type,
            exists=True,
            validation_ok=False,
            payload={},
            errors=(str(exc),),
            path=path,
            expected_environment=environment,
        )

    validation = _validate_payload(
        payload=payload,
        object_type=object_type,
        file_kind=contract.file_kind,
    )

    return classify_current_state(
        object_type=object_type,
        exists=True,
        validation_ok=validation.ok,
        payload=payload,
        errors=validation.errors,
        path=path,
        expected_environment=environment,
    )


def _read_payload(path: Path, file_kind: str):
    if file_kind == "json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"json parse error: {exc.msg}") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("json payload must be an object")
        return payload

    if file_kind == "jsonl":
        records: list[Mapping[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"jsonl parse error on line {line_number}: {exc.msg}") from exc
            if not isinstance(record, Mapping):
                raise ValueError(f"jsonl record on line {line_number} must be an object")
            records.append(record)
        return tuple(records)

    raise ValueError(f"unsupported file kind: {file_kind}")


def _validate_payload(*, payload: object, object_type: str, file_kind: str):
    if file_kind == "json":
        return validate_json_object(payload, object_type)

    errors: list[str] = []
    if not isinstance(payload, tuple):
        return validate_jsonl_record(payload, object_type)
    for index, record in enumerate(payload, 1):
        result = validate_jsonl_record(record, object_type)
        if not result.ok:
            errors.extend(f"record {index}: {error}" for error in result.errors)
    if errors:
        return ValidationResult(
            ok=False,
            object_type=object_type,
            errors=tuple(errors),
            state="INVALID",
        )
    return ValidationResult(ok=True, object_type=object_type, state="VALID")
