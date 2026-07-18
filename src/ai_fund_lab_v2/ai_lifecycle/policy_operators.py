from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PolicyEvidenceRequest:
    component: str
    policy_identity: str
    policy_version: str
    evidence_input: dict[str, Any]
    rollback_target: str
    output_dir: Path


@dataclass(frozen=True)
class PolicyEvidenceResult:
    component: str
    status: str
    policy_identity: str
    policy_version: str
    checks: list[dict[str, Any]]
    authority_review_request: dict[str, Any]
    rollback_target: str
    status_artifact_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PM_REQUIRED_SCENARIOS = {
    "no_position",
    "single_position",
    "multiple_positions",
    "profit_threshold_reached",
    "loss_threshold_reached",
    "holding_period_reached",
    "stale_valuation",
    "missing_market_data",
    "buy_blocked_sell_allowed",
}

SAFETY_REQUIRED_SCENARIOS = {
    "normal_market",
    "individual_crash",
    "market_crash",
    "warning",
    "emergency_stop",
    "recovery",
    "stale_safety_evidence",
    "missing_safety_evidence",
    "buy_block_sell_continuity",
}

FUTURE_CLASSIFICATIONS = {"TRAINABLE", "POLICY_ADAPTER", "POLICY_ENGINE"}


class PMPolicyEvidenceOperator:
    def run(self, request: PolicyEvidenceRequest) -> PolicyEvidenceResult:
        checks = [
            _check("policy_identity", bool(request.policy_identity), "policy identity is required"),
            _check("policy_version", bool(request.policy_version), "policy version is required"),
            _check("policy_freshness", bool(request.evidence_input.get("policy_freshness") == "PASS"), "policy freshness must pass"),
            _check("semantic_regression", bool(request.evidence_input.get("semantic_regression") == "PASS"), "semantic regression must pass"),
            _check("runtime_compatibility", bool(request.evidence_input.get("runtime_compatibility") == "PASS"), "runtime compatibility must pass"),
            _check("sell_continuity", bool(request.evidence_input.get("buy_gate_independence") is True), "BUY gate independence / SELL continuity required"),
            _check("scenario_validation", PM_REQUIRED_SCENARIOS.issubset(set(request.evidence_input.get("scenarios") or [])), "PM required scenarios must be covered"),
        ]
        return _policy_result(request, checks, "PM_POLICY_AUTHORITY_REVIEW_REQUIRED")


class SafetyPolicyEvidenceOperator:
    def run(self, request: PolicyEvidenceRequest) -> PolicyEvidenceResult:
        checks = [
            _check("policy_identity", bool(request.policy_identity), "policy identity is required"),
            _check("policy_version", bool(request.policy_version), "policy version is required"),
            _check("policy_freshness", bool(request.evidence_input.get("policy_freshness") == "PASS"), "policy freshness must pass"),
            _check("threshold_evidence", bool(request.evidence_input.get("threshold_evidence") == "PASS"), "threshold evidence must pass"),
            _check("rule_evidence", bool(request.evidence_input.get("rule_evidence") == "PASS"), "rule evidence must pass"),
            _check("semantic_regression", bool(request.evidence_input.get("semantic_regression") == "PASS"), "semantic regression must pass"),
            _check("scenario_validation", SAFETY_REQUIRED_SCENARIOS.issubset(set(request.evidence_input.get("scenarios") or [])), "Safety required scenarios must be covered"),
        ]
        return _policy_result(request, checks, "SAFETY_POLICY_AUTHORITY_REVIEW_REQUIRED")


def validate_future_ai_onboarding(payload: dict[str, Any], *, output_dir: Path | None = None) -> dict[str, Any]:
    classification = str(payload.get("component_classification") or "")
    checks = [
        _check("classification", classification in FUTURE_CLASSIFICATIONS, "classification must be TRAINABLE, POLICY_ADAPTER, or POLICY_ENGINE"),
        _check("required_artifacts", bool(payload.get("required_artifacts")), "required artifacts must be declared"),
        _check("required_lifecycle_stages", bool(payload.get("required_lifecycle_stages")), "required lifecycle stages must be declared"),
        _check("runtime_consumer", bool(payload.get("runtime_consumer")), "runtime consumer contract is required"),
        _check("authority_scope", bool(payload.get("authority_scope")), "authority boundary is required"),
        _check("registry_scope", bool(payload.get("registry_scope")), "registry boundary is required"),
        _check("rollback_contract", bool(payload.get("rollback_contract")), "rollback contract is required"),
        _check("self_promotion", payload.get("self_promotion_allowed") is False, "self promotion must be prohibited"),
    ]
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "REVIEW_REQUIRED"
    result = {"schema_version": "future_ai_onboarding_validation.v1", "component_name": payload.get("component_name"), "status": status, "checks": checks}
    if output_dir is not None:
        _atomic_write_json(output_dir / "future_ai_onboarding_validation.json", result)
    return result


def _policy_result(request: PolicyEvidenceRequest, checks: list[dict[str, Any]], review_code: str) -> PolicyEvidenceResult:
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "REVIEW_REQUIRED"
    authority = {
        "schema_version": "policy_authority_review_request.v1",
        "component": request.component,
        "policy_identity": request.policy_identity,
        "policy_version": request.policy_version,
        "review_code": review_code,
        "status": "REQUESTED" if status == "PASS" else "BLOCKED",
    }
    result = PolicyEvidenceResult(request.component, status, request.policy_identity, request.policy_version, checks, authority, request.rollback_target, str(request.output_dir / f"{request.component}_policy_status.json"))
    _atomic_write_json(Path(result.status_artifact_path), result.to_dict())
    return result


def _check(name: str, passed: bool, reason: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if passed else "REVIEW_REQUIRED", "reason": reason}


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
