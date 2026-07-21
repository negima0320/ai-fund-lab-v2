from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.rollback_revoke import (
    AtomicRollbackRequest,
    IsolatedRegistryRollbackRevokeOperator,
)
from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _buy_lifecycle_continuity_stages
from ai_fund_lab_v2.runtime_v2.lifecycle_sell_continuity import evaluate_sell_continuity_from_buy_lifecycle_gate


def _registry_hashes(root: Path) -> dict[str, bytes | None]:
    return {
        name: (root / filename).read_bytes() if (root / filename).exists() else None
        for name, filename in {
            "accepted_state": "accepted_state.json",
            "event_log": "events.jsonl",
            "index": "index.json",
            "checkpoint": "checkpoint.json",
        }.items()
    }


def _gate_for(classification: str) -> dict:
    if classification == "MODEL_UNHEALTHY":
        return evaluate_runtime_ai_gate(
            {
                "integrity": {"status": "PASS"},
                "freshness": {"dataset_lag_business_days": 0, "model_training_lag_business_days": 21, "model_acceptance_age_business_days": 1},
                "drift": {
                    "baseline_prediction_scores": [0.1] * 30,
                    "current_prediction_scores": [0.1] * 30,
                    "baseline_feature_values": [1.0] * 30,
                    "current_feature_values": [1.0] * 30,
                    "baseline_positive_coverage": 0.0,
                    "current_positive_coverage": 0.5,
                    "baseline_candidate_population": 30,
                    "current_candidate_population": 30,
                },
            }
        ).to_dict()
    if classification == "INSUFFICIENT_EVIDENCE":
        return evaluate_runtime_ai_gate({"freshness": {}, "drift": {}}).to_dict()
    if classification == "MARKET_NO_OPPORTUNITY":
        return evaluate_runtime_ai_gate(
            {
                "integrity": {"status": "PASS"},
                "freshness": {"dataset_lag_business_days": 0, "model_training_lag_business_days": 0, "model_acceptance_age_business_days": 1},
                "drift": {
                    "baseline_prediction_scores": [-0.1] * 30,
                    "current_prediction_scores": [-0.1] * 30,
                    "baseline_feature_values": [1.0] * 30,
                    "current_feature_values": [1.0] * 30,
                    "baseline_positive_coverage": 0.0,
                    "current_positive_coverage": 0.0,
                    "baseline_candidate_population": 30,
                    "current_candidate_population": 30,
                },
            }
        ).to_dict()
    if classification == "BUY_REVIEW_REQUIRED":
        return evaluate_runtime_ai_gate(
            {
                "integrity": {"status": "PASS"},
                "freshness": {"dataset_lag_business_days": 0, "model_training_lag_business_days": 7, "model_acceptance_age_business_days": 1},
                "drift": {
                    "baseline_prediction_scores": [0.1] * 30,
                    "current_prediction_scores": [0.1] * 30,
                    "baseline_feature_values": [1.0] * 30,
                    "current_feature_values": [1.0] * 30,
                    "baseline_positive_coverage": 0.5,
                    "current_positive_coverage": 0.5,
                    "baseline_candidate_population": 30,
                    "current_candidate_population": 30,
                },
            }
        ).to_dict()
    raise AssertionError(classification)


def test_phase18t_buy_lifecycle_blocks_buy_only_for_runtime_integrity_scenarios() -> None:
    for name in ("MODEL_UNHEALTHY", "INSUFFICIENT_EVIDENCE", "MARKET_NO_OPPORTUNITY", "BUY_REVIEW_REQUIRED"):
        gate = _gate_for(name)
        continuity = evaluate_sell_continuity_from_buy_lifecycle_gate(gate).to_dict()
        assert continuity["allow_current_refresh"] is True
        assert continuity["allow_valuation_refresh"] is True
        assert continuity["allow_position_management"] is True
        assert continuity["allow_safety_evaluation"] is True
        assert continuity["allow_sell_planning"] is True
        assert continuity["allow_sell_submit_authorization"] is True
        assert continuity["broker_write_performed"] is False
        if gate.get("runtime_integrity_status") == "BLOCK":
            assert continuity["buy_planning_permission"] == "BLOCK"
            assert continuity["buy_submit_permission"] == "BLOCK"
        elif name == "MARKET_NO_OPPORTUNITY":
            assert gate["classification"] == "MARKET_NO_OPPORTUNITY"
            assert continuity["buy_planning_permission"] == "PASS"
        else:
            assert gate["trading_permission_effect"] == "NONE"
            assert continuity["buy_planning_permission"] == "PASS"
            assert continuity["buy_submit_permission"] == "PASS"


def test_phase18t_run_daily_operation_stage_reaches_sell_authorization_call_graph() -> None:
    gate = _gate_for("MODEL_UNHEALTHY")
    continuity = evaluate_sell_continuity_from_buy_lifecycle_gate(gate).to_dict()
    stages = _buy_lifecycle_continuity_stages(continuity)
    names = [stage["name"] for stage in stages]
    assert "buy_lifecycle_sell_continuity" in names
    assert "buy_lifecycle_sell_authorization_continuity" in names
    authorization = next(stage for stage in stages if stage["name"] == "buy_lifecycle_sell_authorization_continuity")
    assert authorization["status"] == "PASS"
    assert authorization["details"]["call_graph_reached"] is True
    assert authorization["details"]["sell_planning_stage_reached"] is True
    assert authorization["details"]["sell_submit_authorization_stage_reached"] is True
    assert authorization["details"]["broker_write_performed"] is False


def test_phase18t_restore_failure_is_critical_and_registry_unchanged(tmp_path: Path) -> None:
    failures = (
        "restore_event_failure",
        "restore_index_failure",
        "restore_checkpoint_failure",
        "temporary_cleanup_failure",
        "restore_validation_failure",
    )
    for fail_at in failures:
        registry_root = tmp_path / fail_at
        op = IsolatedRegistryRollbackRevokeOperator(registry_root=registry_root)
        state_a = {"bundle": "A", "runtime_use_eligible": True}
        state_b = {"bundle": "B", "runtime_use_eligible": True}
        init = op.initialize(accepted_state=state_b)
        before = _registry_hashes(registry_root)
        result = op.atomic_rollback(
            AtomicRollbackRequest(f"rb-{fail_at}", "B", "A", "rollback", "tester", "APPROVED", init["state_hash"], "", f"idem-{fail_at}"),
            targets={"A": state_a, "B": state_b},
            fail_at=fail_at,
        )
        assert result["status"] == "CRITICAL"
        assert result["transaction_state"] == "CRITICAL"
        assert result["restore_status"] == "RESTORE_FAILED"
        assert result["manual_recovery_required"] is True
        assert result["accepted_state_unchanged"] is True
        assert result["registry_hash_unchanged"] is True
        assert result["partial_event"] is False
        assert result["partial_index"] is False
        assert result["partial_checkpoint"] is False
        assert _registry_hashes(registry_root) == before
        audit = json.loads((registry_root / "audit" / f"idem-{fail_at}.json").read_text(encoding="utf-8"))
        assert audit["status"] == "CRITICAL"
