from __future__ import annotations

from typing import Any


PASS = "PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
METRIC_UNAVAILABLE = "METRIC_UNAVAILABLE"


def aggregate_opportunity_dual_gate(*, global_gate_result: dict[str, Any], selection_gate_result: dict[str, Any]) -> dict[str, Any]:
    global_status = global_gate_result.get("status")
    selection_status = selection_gate_result.get("status")
    if global_status == PASS and selection_status == PASS:
        status = "DUAL_GATE_PASS"
        reasons: list[str] = []
    elif global_status in {REVIEW_REQUIRED, METRIC_UNAVAILABLE} or selection_status in {REVIEW_REQUIRED, METRIC_UNAVAILABLE}:
        status = "DUAL_GATE_REVIEW_REQUIRED"
        reasons = _prefixed_reasons("global", global_gate_result) + _prefixed_reasons("selection", selection_gate_result)
    else:
        status = "DUAL_GATE_FAIL"
        reasons = _prefixed_reasons("global", global_gate_result) + _prefixed_reasons("selection", selection_gate_result)
    return {
        "status": status,
        "generation_eligibility": status == "DUAL_GATE_PASS",
        "runtime_eligibility": False,
        "accepted": False,
        "global_gate_status": global_status,
        "selection_gate_status": selection_status,
        "reason_codes": reasons,
        "non_offset_rules": [
            "Candidate PASS cannot offset Opportunity Global FAIL",
            "Candidate PASS cannot offset Opportunity Selection FAIL",
            "Opportunity Global PASS cannot offset Opportunity Selection FAIL",
            "Opportunity Selection PASS cannot offset Opportunity Global FAIL",
            "Runtime/Paper/Backtest profit cannot override either gate",
        ],
    }


def _prefixed_reasons(prefix: str, result: dict[str, Any]) -> list[str]:
    if result.get("status") == PASS:
        return []
    return [f"{prefix}:{reason}" for reason in result.get("reason_codes", [])] or [f"{prefix}:status_{result.get('status')}"]
