"""Models for Runtime v2 Current State Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class CurrentStateReadResult:
    object_type: str
    path: Path
    exists: bool
    valid: bool
    classification: str
    payload: Mapping[str, Any] | tuple[Mapping[str, Any], ...] | None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    state_missing: bool = False
    current_state_confirmed_empty: bool = False
    current_positions_unknown: bool = False
    cash_unknown: bool = False
    buying_power_unknown: bool = False
    review_required: bool = False

