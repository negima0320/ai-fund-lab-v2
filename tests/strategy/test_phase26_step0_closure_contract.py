from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.artifact_registry.validator import schema_validate
from ai_fund_lab_v2.strategy.closure_contract import (
    CONTRACT_VERSION,
    FULL_MIGRATION_REQUIREMENTS,
    REQUIRED_NEGATIVE_ASSERTIONS,
    SCHEMA_VERSION,
    ClosureLabel,
    build_phase26_closure_ledger,
    evaluate_full_migration_regression,
    evaluate_mode_parity,
    main,
    read_only_validate_closure_file,
    validate_phase26_closure_ledger,
)


def test_phase26_step0_closure_labels_are_fixed_contract() -> None:
    assert {item.value for item in ClosureLabel} == {
        "DESIGN_CLOSURE",
        "ARTIFACT_FOUNDATION_CLOSURE",
        "RUNTIME_OPERABILITY_CLOSURE",
        "MIGRATION_CLOSURE",
        "ARCHITECTURE_CONFORMANCE_CLOSURE",
        "PERFORMANCE_EVALUATION_CLOSURE",
    }


def test_phase26_step0_valid_full_contract_passes_schema_and_semantic_validation(tmp_path: Path) -> None:
    payload = _valid_payload()
    schema = json.loads(Path("schemas/strategy/phase26_closure_ledger.schema.json").read_text(encoding="utf-8"))

    assert schema_validate(payload, schema, field_path="$") == []
    result = validate_phase26_closure_ledger(payload)
    assert result.status == "PASS"
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["runtime_behavior_changed"] is False

    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    assert read_only_validate_closure_file(path)["status"] == "PASS"
    assert main([str(path)]) == 0


def test_phase26_step0_positive_evidence_without_negative_assertions_does_not_pass() -> None:
    payload = _valid_payload()
    payload["ledger"]["negative_assertion"]["old_fallback_zero"] = "REVIEW_REQUIRED"
    payload["negative_assertions"]["old_fallback_zero"] = "REVIEW_REQUIRED"
    payload["full_migration_regression"] = evaluate_full_migration_regression(
        {
            **{key: "PASS" for key in FULL_MIGRATION_REQUIREMENTS},
            "old_fallback_zero": "REVIEW_REQUIRED",
            "negative_assertion_pass": "REVIEW_REQUIRED",
        }
    )

    result = validate_phase26_closure_ledger(payload)
    assert result.status == "FAIL"
    assert result.failure_class == "HALT"
    assert any("old_fallback_zero" in error for error in result.errors)


def test_phase26_step0_mode_parity_requires_authority_consumer_and_runtime_path_match() -> None:
    parity = evaluate_mode_parity(
        {
            "Production": {"authority": "capital.v2", "consumer": "planning.v2", "runtime_path": "common"},
            "Demo": {"authority": "capital.v2", "consumer": "planning.v2", "runtime_path": "common"},
            "Historical": {"authority": "capital.v2", "consumer": "legacy_planning", "runtime_path": "common"},
        }
    )

    assert parity["status"] == "FAIL"
    consumer = [item for item in parity["comparisons"] if item["field"] == "consumer"][0]
    assert consumer["status"] == "FAIL"


def test_phase26_step0_full_migration_requires_every_gate() -> None:
    regression = evaluate_full_migration_regression({key: "PASS" for key in FULL_MIGRATION_REQUIREMENTS})
    assert regression["status"] == "PASS"
    assert {item["name"] for item in regression["checks"]} == set(FULL_MIGRATION_REQUIREMENTS)

    missing_runtime = evaluate_full_migration_regression(
        {key: "PASS" for key in FULL_MIGRATION_REQUIREMENTS if key != "runtime_evidence_pass"}
    )
    assert missing_runtime["status"] == "FAIL"
    assert [item for item in missing_runtime["checks"] if item["name"] == "runtime_evidence_pass"][0]["status"] == "REVIEW_REQUIRED"


def test_phase26_step0_runtime_behavior_change_blocks_closure() -> None:
    payload = _valid_payload()
    payload["runtime_behavior_changed"] = True

    result = validate_phase26_closure_ledger(payload)
    assert result.status == "FAIL"
    assert any("runtime behavior unchanged or explicitly intended" in error for error in result.errors)


def test_phase26_step0_allows_explicit_architecture_behavior_change_only_when_strategy_and_safety_preserved() -> None:
    payload = _valid_payload()
    payload["runtime_behavior_changed"] = True
    payload["intended_architecture_behavior_change"] = True
    payload["strategy_behavior_changed"] = False
    payload["safety_behavior_weakened"] = False

    assert validate_phase26_closure_ledger(payload).status == "PASS"


def _valid_payload() -> dict:
    stage = {"status": "PASS", "evidence_refs": ["reports/phase26_step0_architecture_foundation_closure_gate_contract/step0_contract_summary.md"]}
    negative_stage = {**stage, **{key: "PASS" for key in REQUIRED_NEGATIVE_ASSERTIONS}}
    ledger = {
        "claim": stage,
        "design_sot": stage,
        "implementation": stage,
        "producer": stage,
        "consumer": stage,
        "runtime_evidence": stage,
        "negative_assertion": negative_stage,
        "regression": stage,
        "closure": stage,
    }
    mode = {
        "Production": {"authority": "phase26.common.authority", "consumer": "phase26.common.consumer", "runtime_path": "phase26.common.runtime_path"},
        "Demo": {"authority": "phase26.common.authority", "consumer": "phase26.common.consumer", "runtime_path": "phase26.common.runtime_path"},
        "Historical": {"authority": "phase26.common.authority", "consumer": "phase26.common.consumer", "runtime_path": "phase26.common.runtime_path"},
    }
    return build_phase26_closure_ledger(
        task_id="Phase26-Step0",
        gap_ids=["P25-GAP-LEG-CAP-001"],
        closure_label=ClosureLabel.ARTIFACT_FOUNDATION_CLOSURE,
        ledger=ledger,
        mode_evidence=mode,
        full_migration_regression={key: "PASS" for key in FULL_MIGRATION_REQUIREMENTS},
        runtime_behavior_changed=False,
        intended_architecture_behavior_change=False,
        strategy_behavior_changed=False,
        safety_behavior_weakened=False,
    )
