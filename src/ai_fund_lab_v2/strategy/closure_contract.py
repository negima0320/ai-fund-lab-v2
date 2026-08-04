from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "phase26_closure_ledger.v1"
CONTRACT_VERSION = "phase26_step0_closure_contract.v1"


class ClosureContractError(ValueError):
    pass


class ClosureLabel(str, Enum):
    DESIGN_CLOSURE = "DESIGN_CLOSURE"
    ARTIFACT_FOUNDATION_CLOSURE = "ARTIFACT_FOUNDATION_CLOSURE"
    RUNTIME_OPERABILITY_CLOSURE = "RUNTIME_OPERABILITY_CLOSURE"
    MIGRATION_CLOSURE = "MIGRATION_CLOSURE"
    ARCHITECTURE_CONFORMANCE_CLOSURE = "ARCHITECTURE_CONFORMANCE_CLOSURE"
    PERFORMANCE_EVALUATION_CLOSURE = "PERFORMANCE_EVALUATION_CLOSURE"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Mode(str, Enum):
    PRODUCTION = "Production"
    DEMO = "Demo"
    HISTORICAL = "Historical"


REQUIRED_NEGATIVE_ASSERTIONS = (
    "old_production_consumer_zero",
    "old_demo_consumer_zero",
    "old_historical_consumer_zero",
    "old_config_authority_zero",
    "old_schema_authority_zero",
    "old_fallback_zero",
    "old_runtime_activation_zero",
    "old_fixture_test_expectation_zero",
)

FULL_MIGRATION_REQUIREMENTS = (
    "producer_pass",
    "artifact_pass",
    "schema_pass",
    "consumer_pass",
    "runtime_evidence_pass",
    "old_production_consumer_zero",
    "old_demo_consumer_zero",
    "old_historical_consumer_zero",
    "old_config_authority_zero",
    "old_schema_authority_zero",
    "old_fallback_zero",
    "old_runtime_activation_zero",
    "old_fixture_test_expectation_zero",
    "negative_assertion_pass",
    "mode_parity_pass",
)

LEDGER_STAGES = (
    "claim",
    "design_sot",
    "implementation",
    "producer",
    "consumer",
    "runtime_evidence",
    "negative_assertion",
    "regression",
    "closure",
)


@dataclass(frozen=True)
class ContractValidationResult:
    status: str
    failure_class: str | None
    checks: list[dict[str, Any]]
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "failure_class": self.failure_class,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def build_phase26_closure_ledger(
    *,
    task_id: str,
    gap_ids: Sequence[str],
    closure_label: ClosureLabel | str,
    ledger: Mapping[str, Any],
    mode_evidence: Mapping[str, Mapping[str, str]],
    full_migration_regression: Mapping[str, str],
    runtime_behavior_changed: bool = False,
    intended_architecture_behavior_change: bool = False,
    strategy_behavior_changed: bool = False,
    safety_behavior_weakened: bool = False,
    submit_behavior_changed: bool | None = None,
    buy_sell_independence_behavior_repaired: bool | None = None,
    submit_guard_weakened: bool | None = None,
    contract_version: str = CONTRACT_VERSION,
) -> dict[str, Any]:
    label = _closure_value(closure_label)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": contract_version,
        "task_id": task_id,
        "gap_ids": list(gap_ids),
        "closure_label": label,
        "ledger": dict(ledger),
        "negative_assertions": normalize_negative_assertions(ledger.get("negative_assertion", {})),
        "mode_parity": evaluate_mode_parity(mode_evidence),
        "full_migration_regression": evaluate_full_migration_regression(full_migration_regression),
        "runtime_behavior_changed": runtime_behavior_changed,
        "intended_architecture_behavior_change": intended_architecture_behavior_change,
        "strategy_behavior_changed": strategy_behavior_changed,
        "safety_behavior_weakened": safety_behavior_weakened,
    }
    if submit_behavior_changed is not None:
        payload["submit_behavior_changed"] = submit_behavior_changed
    if buy_sell_independence_behavior_repaired is not None:
        payload["buy_sell_independence_behavior_repaired"] = buy_sell_independence_behavior_repaired
    if submit_guard_weakened is not None:
        payload["submit_guard_weakened"] = submit_guard_weakened
    return payload


def validate_phase26_closure_ledger(payload: Mapping[str, Any]) -> ContractValidationResult:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    _check(checks, errors, payload.get("schema_version") == SCHEMA_VERSION, "schema_version", "schema_version matches Phase26 closure ledger", "$.schema_version")
    _check(checks, errors, payload.get("contract_version") == CONTRACT_VERSION, "contract_version", "contract_version matches Step0 contract", "$.contract_version")
    _check(checks, errors, bool(payload.get("task_id")), "task_identity", "task_id present", "$.task_id")
    _check(checks, errors, bool(payload.get("gap_ids")), "gap_identity", "at least one gap_id present", "$.gap_ids")
    _check(checks, errors, payload.get("closure_label") in {item.value for item in ClosureLabel}, "closure_label", "closure label is declared and known", "$.closure_label")
    runtime_changed = payload.get("runtime_behavior_changed") is True
    if "runtime_decision_behavior_changed" in payload:
        _check(
            checks,
            errors,
            payload.get("runtime_decision_behavior_changed") is False,
            "runtime_decision_behavior",
            "runtime decision behavior unchanged",
            "$.runtime_decision_behavior_changed",
        )
    runtime_change_allowed = (
        runtime_changed
        and payload.get("intended_architecture_behavior_change") is True
        and payload.get("strategy_behavior_changed") is False
        and payload.get("safety_behavior_weakened") is False
    )
    _check(
        checks,
        errors,
        payload.get("runtime_behavior_changed") is False or runtime_change_allowed,
        "runtime_behavior",
        "runtime behavior unchanged or explicitly intended architecture behavior change",
        "$.runtime_behavior_changed",
    )
    if runtime_changed:
        _check(checks, errors, payload.get("intended_architecture_behavior_change") is True, "runtime_behavior", "architecture behavior change is intentional", "$.intended_architecture_behavior_change")
        _check(checks, errors, payload.get("strategy_behavior_changed") is False, "strategy_behavior", "strategy behavior unchanged", "$.strategy_behavior_changed")
        _check(checks, errors, payload.get("safety_behavior_weakened") is False, "safety_behavior", "safety behavior not weakened", "$.safety_behavior_weakened")
    if "submit_behavior_changed" in payload:
        _check(checks, errors, payload.get("submit_behavior_changed") is False, "submit_behavior", "submit behavior unchanged", "$.submit_behavior_changed")
    if "submit_guard_weakened" in payload:
        _check(checks, errors, payload.get("submit_guard_weakened") is False, "submit_guard", "submit guard not weakened", "$.submit_guard_weakened")
    if "buy_sell_independence_behavior_repaired" in payload:
        _check(checks, errors, payload.get("buy_sell_independence_behavior_repaired") is True, "buy_sell_independence", "BUY/SELL independence behavior repaired", "$.buy_sell_independence_behavior_repaired")

    ledger = payload.get("ledger")
    _check(checks, errors, isinstance(ledger, Mapping), "claim_to_evidence_ledger", "ledger object present", "$.ledger")
    if isinstance(ledger, Mapping):
        for stage in LEDGER_STAGES:
            stage_value = ledger.get(stage)
            _check(
                checks,
                errors,
                isinstance(stage_value, Mapping) and bool(stage_value.get("status")) and bool(stage_value.get("evidence_refs")),
                "claim_to_evidence_ledger",
                f"{stage} has status and evidence_refs",
                f"$.ledger.{stage}",
            )

    negative = payload.get("negative_assertions")
    _check(checks, errors, isinstance(negative, Mapping), "negative_assertion", "negative assertion object present", "$.negative_assertions")
    if isinstance(negative, Mapping):
        negative_status = validate_negative_assertions(negative)
        checks.extend(negative_status.checks)
        errors.extend(negative_status.errors)
        warnings.extend(negative_status.warnings)

    mode_parity = payload.get("mode_parity")
    _check(checks, errors, isinstance(mode_parity, Mapping), "mode_parity", "mode parity object present", "$.mode_parity")
    if isinstance(mode_parity, Mapping):
        _check(checks, errors, mode_parity.get("status") == "PASS", "mode_parity", "Production/Demo/Historical authority, consumer, and runtime path match", "$.mode_parity.status")

    full = payload.get("full_migration_regression")
    _check(checks, errors, isinstance(full, Mapping), "full_migration_regression", "full migration regression object present", "$.full_migration_regression")
    if isinstance(full, Mapping):
        _check(checks, errors, full.get("status") == "PASS", "full_migration_regression", "FULL_MIGRATION_REGRESSION passes every required gate", "$.full_migration_regression.status")
        full_checks = {str(item.get("name")): item.get("status") for item in full.get("checks") or [] if isinstance(item, Mapping)}
        for requirement in FULL_MIGRATION_REQUIREMENTS:
            _check(
                checks,
                errors,
                full_checks.get(requirement) == CheckStatus.PASS.value,
                "full_migration_regression",
                f"{requirement} is PASS",
                f"$.full_migration_regression.checks.{requirement}",
            )

    status = "PASS" if not errors else "FAIL"
    return ContractValidationResult(status=status, failure_class=None if status == "PASS" else "HALT", checks=checks, errors=errors, warnings=warnings)


def normalize_negative_assertions(source: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: _status_value(source.get(key, CheckStatus.REVIEW_REQUIRED.value))
        for key in REQUIRED_NEGATIVE_ASSERTIONS
    }


def validate_negative_assertions(assertions: Mapping[str, Any]) -> ContractValidationResult:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED_NEGATIVE_ASSERTIONS:
        status = assertions.get(key)
        _check(
            checks,
            errors,
            status == CheckStatus.PASS.value,
            "negative_assertion",
            f"{key} is PASS",
            f"$.negative_assertions.{key}",
        )
    result = "PASS" if not errors else "FAIL"
    return ContractValidationResult(result, None if result == "PASS" else "HALT", checks, errors, warnings)


def evaluate_mode_parity(mode_evidence: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    required_fields = ("authority", "consumer", "runtime_path")
    required_modes = tuple(mode.value for mode in Mode)
    missing = [mode for mode in required_modes if mode not in mode_evidence]
    comparisons: list[dict[str, Any]] = []
    for field in required_fields:
        values = {mode: (mode_evidence.get(mode) or {}).get(field) for mode in required_modes}
        comparisons.append({"field": field, "values": values, "status": "PASS" if None not in values.values() and len(set(values.values())) == 1 else "FAIL"})
    status = "PASS" if not missing and all(item["status"] == "PASS" for item in comparisons) else "FAIL"
    return {
        "status": status,
        "required_modes": list(required_modes),
        "missing_modes": missing,
        "comparisons": comparisons,
    }


def evaluate_full_migration_regression(results: Mapping[str, Any]) -> dict[str, Any]:
    checks = []
    for key in FULL_MIGRATION_REQUIREMENTS:
        status = _status_value(results.get(key, CheckStatus.REVIEW_REQUIRED.value))
        checks.append({"name": key, "status": status})
    overall = "PASS" if all(item["status"] == CheckStatus.PASS.value for item in checks) else "FAIL"
    return {"status": overall, "checks": checks}


def read_only_validate_closure_file(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_phase26_closure_ledger(payload).to_dict()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a Phase26 closure ledger JSON file without modifying runtime state.")
    parser.add_argument("ledger_path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = read_only_validate_closure_file(args.ledger_path)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


def _closure_value(value: ClosureLabel | str) -> str:
    raw = value.value if isinstance(value, ClosureLabel) else str(value)
    if raw not in {item.value for item in ClosureLabel}:
        raise ClosureContractError(f"unknown closure label: {raw}")
    return raw


def _status_value(value: Any) -> str:
    raw = value.value if isinstance(value, CheckStatus) else str(value)
    if raw not in {item.value for item in CheckStatus}:
        return CheckStatus.REVIEW_REQUIRED.value
    return raw


def _check(
    checks: list[dict[str, Any]],
    errors: list[str],
    condition: bool,
    check_id: str,
    message: str,
    path: str,
) -> None:
    status = "PASS" if condition else "FAIL"
    checks.append({"check_id": check_id, "message": message, "path": path, "status": status})
    if not condition:
        errors.append(f"{path}: {message}")


if __name__ == "__main__":
    raise SystemExit(main())
