from __future__ import annotations

from pathlib import Path
from typing import Any


PROHIBITED_RUNTIME_REFERENCES = (
    "opportunity_dual_gate",
    "opportunity_global_gate",
    "opportunity_selection_gate",
    "dual_gate_artifact",
    "DUAL_GATE_PASS",
    "OPPORTUNITY_GLOBAL_QUALITY_GATE",
    "OPPORTUNITY_SELECTION_UTILITY_GATE",
    "gate disagreement",
)

PROHIBITED_RUNTIME_AUTHORITIES = (
    "Dual Gate Evidence",
    "Global Gate metric payload",
    "Selection Gate metric payload",
    "Formal Validation working directory",
    "unaccepted Validation Artifact",
)


def guard_runtime_gate_access(*, action: str, referenced_authorities: list[str]) -> dict[str, Any]:
    blocked = [authority for authority in referenced_authorities if authority in PROHIBITED_RUNTIME_AUTHORITIES or "dual_gate" in authority.lower()]
    return {
        "status": "BLOCK" if blocked else "PASS",
        "action": action,
        "blocked_authorities": blocked,
        "reason_codes": ["runtime_dual_gate_access_prohibited"] if blocked else [],
    }


def runtime_dependency_static_audit(*, runtime_root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in sorted(runtime_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in PROHIBITED_RUNTIME_REFERENCES:
            if token in text:
                findings.append({"path": str(path), "token": token})
    return {
        "status": "BLOCK" if findings else "PASS",
        "findings": findings,
        "runtime_root": str(runtime_root),
    }


def validate_buy_suppression_reason(reason: str) -> dict[str, Any]:
    lowered = reason.lower()
    blocked = "gate disagreement" in lowered or "dual gate" in lowered or "global gate" in lowered or "selection gate" in lowered
    return {
        "status": "BLOCK" if blocked else "PASS",
        "reason": reason,
        "reason_codes": ["runtime_buy_suppression_by_dual_gate_prohibited"] if blocked else [],
    }
