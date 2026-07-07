"""Execution classification models for Runtime v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FillClassificationType(str, Enum):
    NO_FILL = "NO_FILL"
    PARTIAL_FILL = "PARTIAL_FILL"
    FULL_FILL = "FULL_FILL"
    UNKNOWN_FILL = "UNKNOWN_FILL"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    ORDER_REJECTED = "ORDER_REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class FillClassification:
    classification_id: str
    order_ref_hash: str
    pending_plan_id: str
    pending_item_id: str
    symbol: str
    side: str
    ordered_quantity: float
    filled_quantity: float
    remaining_quantity: float
    classification: FillClassificationType
    review_required: bool
    production_equivalent: bool
    source: str
    as_of: str
