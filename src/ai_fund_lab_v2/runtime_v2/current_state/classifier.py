"""Classification rules for Runtime v2 current state payloads."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.current_state.models import CurrentStateReadResult


class CurrentStateClassification(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    CONFIRMED_EMPTY = "CONFIRMED_EMPTY"
    INVALID = "INVALID"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


_ALLOWED_CONFIRMED_EMPTY_SOURCES = frozenset(
    {
        "broker_positions",
        "broker_cash",
        "manual_migration",
        "phase14e8_demo_operation_initial_state",
    }
)
_DIVERGENCE_EVENT_TYPES = frozenset(
    {"POST_SEND_UNKNOWN", "BROKER_DIVERGENCE", "LEDGER_DIVERGENCE"}
)


def classify_current_state(
    *,
    object_type: str,
    exists: bool,
    validation_ok: bool,
    payload: object | None,
    errors: tuple[str, ...] = (),
    path=None,
    expected_environment: str | None = None,
) -> CurrentStateReadResult:
    """Classify a current state read result without using fallback artifacts."""

    normalized_path = path
    if not exists or payload is None or _has_missing_required_field(errors):
        return _result(
            object_type=object_type,
            path=normalized_path,
            exists=exists,
            valid=False,
            classification=CurrentStateClassification.MISSING,
            payload=None,
            errors=errors,
            state_missing=True,
            review_required=True,
        )

    if not validation_ok:
        return _result(
            object_type=object_type,
            path=normalized_path,
            exists=exists,
            valid=False,
            classification=CurrentStateClassification.INVALID,
            payload=_payload_for_result(payload),
            errors=errors,
            state_missing=True,
            review_required=True,
        )

    review_required = _payload_review_required(payload)
    if object_type == "persistent_ledger_state" and _is_confirmed_empty(payload):
        return _result(
            object_type=object_type,
            path=normalized_path,
            exists=exists,
            valid=True,
            classification=CurrentStateClassification.CONFIRMED_EMPTY,
            payload=_payload_for_result(payload),
            errors=errors,
            current_state_confirmed_empty=True,
            review_required=review_required,
        )

    if _is_stale(payload):
        return _result(
            object_type=object_type,
            path=normalized_path,
            exists=exists,
            valid=True,
            classification=CurrentStateClassification.STALE,
            payload=_payload_for_result(payload),
            errors=errors,
            review_required=True,
        )

    if _is_unknown(
        object_type=object_type,
        payload=payload,
        expected_environment=expected_environment,
    ):
        return _result(
            object_type=object_type,
            path=normalized_path,
            exists=exists,
            valid=False,
            classification=CurrentStateClassification.UNKNOWN,
            payload=_payload_for_result(payload),
            errors=errors,
            state_missing=True,
            review_required=True,
        )

    if review_required:
        return _result(
            object_type=object_type,
            path=normalized_path,
            exists=exists,
            valid=True,
            classification=CurrentStateClassification.REVIEW_REQUIRED,
            payload=_payload_for_result(payload),
            errors=errors,
            review_required=True,
        )

    return _result(
        object_type=object_type,
        path=normalized_path,
        exists=exists,
        valid=True,
        classification=CurrentStateClassification.VALID,
        payload=_payload_for_result(payload),
        errors=errors,
    )


def _result(
    *,
    object_type: str,
    path,
    exists: bool,
    valid: bool,
    classification: CurrentStateClassification,
    payload,
    errors: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    state_missing: bool = False,
    current_state_confirmed_empty: bool = False,
    review_required: bool = False,
) -> CurrentStateReadResult:
    unknown = classification in {
        CurrentStateClassification.MISSING,
        CurrentStateClassification.INVALID,
        CurrentStateClassification.UNKNOWN,
    }
    return CurrentStateReadResult(
        object_type=object_type,
        path=path,
        exists=exists,
        valid=valid,
        classification=classification.value,
        payload=payload,
        errors=errors,
        warnings=warnings,
        state_missing=state_missing,
        current_state_confirmed_empty=current_state_confirmed_empty,
        current_positions_unknown=unknown,
        cash_unknown=unknown,
        buying_power_unknown=unknown,
        review_required=review_required,
    )


def _has_missing_required_field(errors: tuple[str, ...]) -> bool:
    return any("missing required field:" in error for error in errors)


def _payload_for_result(payload: object):
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, tuple) and all(isinstance(item, Mapping) for item in payload):
        return payload
    return None


def _is_confirmed_empty(payload: object) -> bool:
    if not isinstance(payload, Mapping):
        return False
    if payload.get("current_state_confirmed_empty") is not True:
        return False
    if payload.get("positions") != []:
        return False
    if payload.get("cash") is None or payload.get("buying_power") is None:
        return False
    if payload.get("cash_confirmed") is not True:
        return False
    if payload.get("buying_power_confirmed") is not True:
        return False
    return payload.get("source") in _ALLOWED_CONFIRMED_EMPTY_SOURCES


def _is_stale(payload: object) -> bool:
    return _any_record_matches(payload, lambda item: item.get("stale") is True)


def _is_unknown(
    *,
    object_type: str,
    payload: object,
    expected_environment: str | None,
) -> bool:
    def record_unknown(item: Mapping[str, Any]) -> bool:
        if expected_environment and item.get("environment") != expected_environment:
            return True
        if item.get("source") in {None, "", "unknown"} and "source" in item:
            return True
        if item.get("state") in {None, "", "UNKNOWN"} and "state" in item:
            return True
        if "production_equivalent" in item and item.get("production_equivalent") is None:
            return True
        return False

    if _any_record_matches(payload, record_unknown):
        return True

    if object_type == "persistent_ledger_state" and isinstance(payload, Mapping):
        if payload.get("positions") is None:
            return True
        if payload.get("cash") is None:
            return True
        if payload.get("buying_power") is None:
            return True
        if payload.get("source") in {None, "", "unknown"}:
            return True

    return False


def _payload_review_required(payload: object) -> bool:
    def record_review_required(item: Mapping[str, Any]) -> bool:
        if item.get("review_required") is True:
            return True
        if (
            item.get("production_equivalent") is False
            and item.get("source") != "phase14e8_demo_operation_initial_state"
        ):
            return True
        if item.get("source") == "broker_orders_fallback":
            return True
        if item.get("event_type") in _DIVERGENCE_EVENT_TYPES:
            return True
        return False

    return _any_record_matches(payload, record_review_required)


def _any_record_matches(payload: object, predicate) -> bool:
    if isinstance(payload, Mapping):
        return predicate(payload)
    if isinstance(payload, tuple):
        return any(isinstance(item, Mapping) and predicate(item) for item in payload)
    return False
