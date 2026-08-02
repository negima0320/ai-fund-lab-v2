"""Shared precision contract for serialized target weights."""

from __future__ import annotations


TARGET_WEIGHT_DECIMALS = 6
TARGET_WEIGHT_ABSOLUTE_TOLERANCE = 0.000001


def target_weight_sum_tolerance(selected_member_count: int) -> float:
    rounding_unit = 10 ** -TARGET_WEIGHT_DECIMALS
    rounding_tolerance = max(0, selected_member_count) * rounding_unit / 2
    return max(TARGET_WEIGHT_ABSOLUTE_TOLERANCE, rounding_tolerance)
