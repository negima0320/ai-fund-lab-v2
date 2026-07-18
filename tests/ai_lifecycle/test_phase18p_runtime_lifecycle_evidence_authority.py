from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.rollback_revoke import (
    AtomicRevokeRequest,
    AtomicRollbackRequest,
    IsolatedRegistryRollbackRevokeOperator,
)
from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate
from ai_fund_lab_v2.runtime_v2.lifecycle_evidence import build_runtime_lifecycle_evidence
from ai_fund_lab_v2.runtime_v2.lifecycle_sell_continuity import evaluate_sell_continuity_from_buy_lifecycle_gate


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _bundle_fixture(root: Path, *, positive_rate: float = 0.5, score_mean: float = 0.1, score_min: float = -0.2, score_max: float = 0.4) -> Path:
    dataset_dir = root / "datasets" / "opportunity"
    training_dir = root / "training" / "opportunity"
    candidate_dataset_dir = root / "datasets" / "candidate"
    candidate_training_dir = root / "training" / "candidate"
    calendar_path = root / "calendar.csv"
    calendar_path.write_text("date\n2026-05-15\n2026-05-18\n2026-05-19\n2026-05-20\n2026-05-21\n2026-05-22\n2026-05-25\n2026-05-26\n2026-05-27\n2026-05-28\n2026-05-29\n2026-06-01\n2026-06-02\n2026-06-03\n2026-06-04\n2026-06-05\n2026-06-08\n2026-06-09\n2026-06-10\n", encoding="utf-8")
    _write_json(
        dataset_dir / "dataset_metadata.json",
        {
            "dataset_version": "opportunity_dataset_test",
            "label_safe_cutoff": {"label_safe_cutoff": "2026-06-04"},
            "input_artifacts": {
                "opportunity_source": {"max_target_date": "2026-05-15", "row_count": 100},
                "trading_calendar": {"source_ref": str(calendar_path)},
            },
        },
    )
    _write_json(dataset_dir / "lineage.json", {"lineage": "opportunity"})
    _write_json(dataset_dir / "feature_schema.json", {"features": ["f1"]})
    _write_json(dataset_dir / "target_schema.json", {"target": "label__expected_edge_label_20d"})
    _write_json(dataset_dir / "hash_manifest.json", {
        "dataset_hash": "opp-dataset-hash",
        "feature_schema_hash": "opp-feature-hash",
        "target_schema_hash": "opp-target-hash",
    })
    _write_json(
        candidate_dataset_dir / "dataset_metadata.json",
        {
            "dataset_version": "candidate_dataset_test",
            "input_artifacts": {
                "candidate_source": {"max_target_date": "2026-05-15", "min_target_date": "2026-01-01", "row_count": 100},
                "trading_calendar": {"source_ref": str(calendar_path)},
            },
        },
    )
    _write_json(candidate_dataset_dir / "lineage.json", {"lineage": "candidate"})
    _write_json(candidate_dataset_dir / "feature_schema.json", {"features": ["cf1"]})
    _write_json(candidate_dataset_dir / "target_schema.json", {"target": "candidate"})
    _write_json(candidate_dataset_dir / "hash_manifest.json", {
        "dataset_hash": "candidate-dataset-hash",
        "feature_schema_hash": "candidate-feature-hash",
        "target_schema_hash": "candidate-target-hash",
    })
    _write_json(training_dir / "training_metadata.json", {"training_version": "opportunity_training_test", "model_training_cutoff": "2026-06-01"})
    _write_json(training_dir / "lineage.json", {"lineage": "opportunity-training"})
    _write_json(training_dir / "calibration_parameters.json", {"method": "platt"})
    _write_json(training_dir / "calibration_schema.json", {"schema": "calibration"})
    _write_json(training_dir / "calibration_metadata.json", {"version": "v1"})
    (training_dir / "calibration_model.pkl").write_bytes(b"calibration")
    _write_json(training_dir / "hash_manifest.json", {
        "bundle_hash": "opp-training-hash",
        "file_hashes": {
            "calibration_model.pkl": _sha256(training_dir / "calibration_model.pkl"),
            "calibration_parameters.json": _sha256(training_dir / "calibration_parameters.json"),
            "calibration_schema.json": _sha256(training_dir / "calibration_schema.json"),
            "calibration_metadata.json": _sha256(training_dir / "calibration_metadata.json"),
        },
    })
    _write_json(candidate_training_dir / "training_metadata.json", {"training_version": "candidate_training_test", "model_training_cutoff": "2026-06-01"})
    _write_json(candidate_training_dir / "lineage.json", {"lineage": "candidate-training"})
    _write_json(candidate_training_dir / "hash_manifest.json", {"bundle_hash": "candidate-training-hash"})
    prediction_seed = [score_min, score_mean - 0.01, score_mean, score_mean + 0.01, score_mean + 0.02, score_max]
    prediction_values = [prediction_seed[idx % len(prediction_seed)] for idx in range(30)]
    if positive_rate == 0.0:
        prediction_values = [-0.01 for _ in range(30)]
    baseline = {
        "prediction_distribution_values": prediction_values,
        "feature_distribution_values": prediction_values,
        "candidate_population": 30,
        "positive_coverage": positive_rate,
        "row_count": 100,
        "baseline_date_range": {"min_target_date": "2026-01-01", "max_target_date": "2026-05-15"},
        "lineage": {"accepted_bundle": "bundle-test", "source": "materialized_fixture"},
    }
    baseline["baseline_hash"] = _stable_hash(baseline)
    payload = {
        "schema_version": "accepted_buy_ai_bundle.v1",
        "buy_ai_bundle_id": "bundle-test",
        "accepted_event_id": "event-test",
        "accepted_at": "2026-06-05T00:00:00+00:00",
        "candidate_dataset": {"dataset_dir": str(candidate_dataset_dir), "dataset_hash": "candidate-dataset-hash", "feature_schema_hash": "candidate-feature-hash", "target_schema_hash": "candidate-target-hash"},
        "opportunity_dataset": {"dataset_dir": str(dataset_dir), "dataset_hash": "opp-dataset-hash", "feature_schema_hash": "opp-feature-hash", "target_schema_hash": "opp-target-hash"},
        "candidate_training": {"training_dir": str(candidate_training_dir), "bundle_hash": "candidate-training-hash", "dataset_reference": {"dataset_hash": "candidate-dataset-hash", "feature_schema_hash": "candidate-feature-hash", "target_schema_hash": "candidate-target-hash"}},
        "opportunity_training": {"training_dir": str(training_dir), "bundle_hash": "opp-training-hash", "dataset_reference": {"dataset_hash": "opp-dataset-hash", "feature_schema_hash": "opp-feature-hash", "target_schema_hash": "opp-target-hash"}},
        "compatibility_evidence": {
            "candidate_and_opportunity_promoted_atomically": True,
            "candidate_dataset_hash_matches_training": True,
            "opportunity_dataset_hash_matches_training": True,
            "feature_contract_preserved": True,
            "opportunity_target_preserved": True,
            "bv15_preserved": True,
        },
        "runtime_baseline": baseline,
    }
    payload["joint_bundle_hash"] = _stable_hash(payload)
    bundle = root / "accepted_buy_ai_bundle.json"
    _write_json(bundle, payload)
    return bundle


def test_phase18p_freshness_and_baseline_are_authoritative_not_self_baseline(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path)
    candidate_payload = {"rows": [{"code": "1001", "candidate_score": 0.11}, {"code": "1002", "candidate_score": 0.12}] * 15}
    opportunity_payload = {"rankings": [{"code": "1001", "opportunity_score": 0.05}, {"code": "1002", "opportunity_score": 0.06}] * 15}
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="runtime-test",
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
        accepted_bundle_path=bundle,
    )
    artifact = evidence.to_artifact_fields()
    assert evidence.freshness["dataset_lag_business_days"] is not None
    assert evidence.freshness["model_training_lag_business_days"] is not None
    assert evidence.freshness["model_acceptance_age_business_days"] is not None
    assert artifact["baseline_identity"] != artifact["current_window_identity"]
    assert evidence.drift["baseline_prediction_scores"] != evidence.drift["current_prediction_scores"]
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert gate["block_sell"] is False


def test_phase18p_missing_baseline_fail_closed(tmp_path: Path) -> None:
    candidate_payload = {"rows": [{"code": "1001", "candidate_score": 0.1}] * 30}
    opportunity_payload = {"rankings": [{"code": "1001", "opportunity_score": 0.1}] * 30}
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="runtime-test",
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
        accepted_bundle_path=tmp_path / "missing.json",
    )
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert gate["decision"] in {"REVIEW_REQUIRED", "BLOCK"}
    assert gate["classification"] == "INSUFFICIENT_EVIDENCE"
    assert gate["block_buy"] is True
    assert gate["block_sell"] is False


def test_phase18p_market_no_opportunity_and_model_unhealthy_separated(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path, positive_rate=0.0, score_mean=-0.01, score_min=-0.01, score_max=-0.01)
    stable_negative = [-0.01, -0.01, -0.01, -0.01, -0.01, -0.01, -0.01]
    candidate_payload = {"rows": [{"code": f"{idx}", "candidate_score": stable_negative[idx % len(stable_negative)]} for idx in range(30)]}
    no_opportunity = {"rankings": [{"code": f"{idx}", "opportunity_score": stable_negative[idx % len(stable_negative)]} for idx in range(30)]}
    no_opp_evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="runtime-no-opp",
        candidate_payload=candidate_payload,
        opportunity_payload=no_opportunity,
        accepted_bundle_path=bundle,
    )
    no_opp_gate = evaluate_runtime_ai_gate(no_opp_evidence.to_gate_input()).to_dict()
    assert no_opp_gate["classification"] == "MARKET_NO_OPPORTUNITY"
    assert no_opp_gate["block_sell"] is False

    hard_drift = {"rankings": [{"code": f"{idx}", "opportunity_score": 9.0 + idx} for idx in range(30)]}
    hard_evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="runtime-hard-drift",
        candidate_payload=candidate_payload,
        opportunity_payload=hard_drift,
        accepted_bundle_path=bundle,
    )
    hard_gate = evaluate_runtime_ai_gate(hard_evidence.to_gate_input()).to_dict()
    assert hard_gate["classification"] == "MODEL_UNHEALTHY"
    assert hard_gate["block_buy"] is True
    assert hard_gate["block_sell"] is False


def test_phase18p_rollback_revoke_failure_injection_is_atomic(tmp_path: Path) -> None:
    op = IsolatedRegistryRollbackRevokeOperator(registry_root=tmp_path)
    state_a = {"bundle": "A", "runtime_use_eligible": True}
    state_b = {"bundle": "B", "runtime_use_eligible": True}
    init = op.initialize(accepted_state=state_b)
    targets = {"A": state_a, "B": state_b}
    before_hashes = _registry_hashes(tmp_path)
    for fail_at in ("event_write", "event_replace", "index_write", "checkpoint_write", "post_validation"):
        result = op.atomic_rollback(
            AtomicRollbackRequest(f"rb-{fail_at}", "B", "A", "rollback", "tester", "APPROVED", init["state_hash"], "", f"idem-{fail_at}"),
            targets=targets,
            fail_at=fail_at,
        )
        assert result["status"] == "FAILED"
        assert result["partial_state"] is False
        assert _registry_hashes(tmp_path) == before_hashes

    success = op.atomic_rollback(
        AtomicRollbackRequest("rb-success", "B", "A", "rollback", "tester", "APPROVED", init["state_hash"], "", "idem-success"),
        targets=targets,
    )
    assert success["status"] == "PASS"
    revoke_before = _registry_hashes(tmp_path)
    revoke = op.atomic_revoke(
        AtomicRevokeRequest("rv-fail", "A", "revoke", "tester", "APPROVED", "B", success["after_state_hash"], "idem-rv"),
        targets=targets,
        fail_at="checkpoint_write",
    )
    assert revoke["status"] == "FAILED"
    assert _registry_hashes(tmp_path) == revoke_before


def test_phase18p_sell_continuity_from_buy_lifecycle_gate() -> None:
    for gate in (
        {"decision": "BLOCK", "classification": "MODEL_UNHEALTHY", "block_buy": True, "block_sell": False, "block_submit": True},
        {"decision": "PASS", "classification": "MARKET_NO_OPPORTUNITY", "block_buy": False, "block_sell": False, "block_submit": False},
        {"decision": "REVIEW_REQUIRED", "classification": "INSUFFICIENT_EVIDENCE", "block_buy": True, "block_sell": False, "block_submit": True},
        {"decision": "REVIEW_REQUIRED", "classification": "MODEL_HEALTH_REVIEW_REQUIRED", "block_buy": True, "block_sell": False, "block_submit": True},
    ):
        decision = evaluate_sell_continuity_from_buy_lifecycle_gate(gate)
        assert decision.status == "PASS"
        assert decision.current_refresh_allowed is True
        assert decision.valuation_refresh_allowed is True
        assert decision.position_management_allowed is True
        assert decision.safety_allowed is True
        assert decision.sell_planning_allowed is True
        assert decision.sell_submit_authorization_allowed is True
        assert decision.broker_write_performed is False


def _registry_hashes(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in ("accepted_state.json", "events.jsonl", "index.json", "checkpoint.json"):
        path = root / name
        out[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    return out
