from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate
from ai_fund_lab_v2.runtime_v2.lifecycle_evidence import build_runtime_lifecycle_evidence

from tests.ai_lifecycle.test_phase18p_runtime_lifecycle_evidence_authority import _bundle_fixture, _write_json


def _payloads(candidate_count: int = 30, scores: list[float] | None = None) -> tuple[dict, dict]:
    scores = scores or [0.08, 0.09, 0.10, 0.11, 0.12, 0.13]
    candidate = {"rows": [{"code": f"{idx}", "candidate_score": scores[idx % len(scores)]} for idx in range(candidate_count)]}
    opportunity = {"rankings": [{"code": f"{idx}", "opportunity_score": scores[idx % len(scores)]} for idx in range(max(candidate_count, len(scores)))]}
    return candidate, opportunity


def _evidence(tmp_path: Path, bundle: Path | None, *, candidate_count: int = 30, scores: list[float] | None = None):
    candidate, opportunity = _payloads(candidate_count=candidate_count, scores=scores)
    return build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="phase18s-test",
        candidate_payload=candidate,
        opportunity_payload=opportunity,
        accepted_bundle_path=bundle,
    )


def test_phase18s_accepted_state_resolves_without_manual_path(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path)
    state = tmp_path / "runtime_state" / "accepted_buy_ai_bundle.json"
    _write_json(state, {"accepted_bundle_path": str(bundle), "accepted_event_id": "event-test", "accepted_state_hash": "state-test"})
    candidate, opportunity = _payloads()
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="phase18s-state",
        candidate_payload=candidate,
        opportunity_payload=opportunity,
    )
    assert evidence.integrity_evidence["status"] == "PASS"
    assert evidence.integrity_evidence["accepted_event_identity"] == "event-test"


def test_phase18s_accepted_state_missing_does_not_fallback_to_promotion_candidate(tmp_path: Path) -> None:
    candidate, opportunity = _payloads()
    promotion = tmp_path / "artifact_registry" / "promotion_candidates" / "transactions" / "tx" / "atomic_buy_ai_bundle.json"
    _write_json(promotion, {"buy_ai_bundle_id": "promotion-only"})
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=tmp_path,
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="phase18s-no-state",
        candidate_payload=candidate,
        opportunity_payload=opportunity,
    )
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert "accepted_state_missing" in evidence.integrity_evidence["reason_codes"]
    assert gate["classification"] == "RUNTIME_INTEGRITY_BLOCK"
    assert gate["trading_permission_effect"] == "BUY_BLOCK"
    assert gate["runtime_integrity_status"] == "BLOCK"
    assert gate["block_buy"] is True


def test_phase18s_manual_path_rejected_in_production_runtime() -> None:
    candidate, opportunity = _payloads()
    evidence = build_runtime_lifecycle_evidence(
        runtime_root=Path(".runtime"),
        business_date="2026-06-10",
        feature_date="2026-06-10",
        runtime_id="phase18s-manual-prod",
        candidate_payload=candidate,
        opportunity_payload=opportunity,
        accepted_bundle_path=Path(".runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18i-1081babc49b5d26b/atomic_buy_ai_bundle.json"),
    )
    assert "manual_accepted_bundle_path_forbidden" in evidence.integrity_evidence["reason_codes"]
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert gate["classification"] == "RUNTIME_INTEGRITY_BLOCK"
    assert gate["trading_permission_effect"] == "BUY_BLOCK"
    assert gate["runtime_integrity_status"] == "BLOCK"


def test_phase18s_hash_schema_lineage_mismatch_fail_closed(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path)
    payload = json.loads(bundle.read_text(encoding="utf-8"))
    payload["opportunity_dataset"]["dataset_hash"] = "wrong"
    _write_json(bundle, payload)
    evidence = _evidence(tmp_path, bundle)
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert "joint_bundle_hash_mismatch" in evidence.integrity_evidence["reason_codes"]
    assert "opportunity_dataset_dataset_hash_mismatch" in evidence.integrity_evidence["reason_codes"]
    assert gate["classification"] == "CRITICAL_AUTHORITY_VIOLATION"


def test_phase18s_freshness_invalid_calendar_and_negative_lag_fail_closed(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path)
    payload = json.loads(bundle.read_text(encoding="utf-8"))
    meta_path = Path(payload["opportunity_dataset"]["dataset_dir"]) / "dataset_metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    formal_calendar_ref = meta["input_artifacts"]["trading_calendar"]["source_ref"]
    meta["input_artifacts"]["trading_calendar"]["source_ref"] = "weekday_fallback"
    _write_json(meta_path, meta)
    evidence = _evidence(tmp_path, bundle)
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert "weekday_fallback_forbidden" in evidence.freshness_evidence["reason_codes"]
    assert gate["decision"] == "BLOCK"

    meta["input_artifacts"]["trading_calendar"]["source_ref"] = formal_calendar_ref
    _write_json(meta_path, meta)
    training_meta_path = Path(payload["opportunity_training"]["training_dir"]) / "training_metadata.json"
    _write_json(training_meta_path, {"training_version": "opportunity_training_test", "model_training_cutoff": "2026-06-10"})
    negative_lag = _evidence(tmp_path, bundle)
    assert "negative_model_training_lag" in negative_lag.freshness_evidence["reason_codes"]
    assert evaluate_runtime_ai_gate(negative_lag.to_gate_input()).to_dict()["decision"] == "BLOCK"


def test_phase18s_materialized_baseline_required_and_hash_verified(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path)
    payload = json.loads(bundle.read_text(encoding="utf-8"))
    payload["runtime_baseline"]["baseline_hash"] = "bad"
    payload["joint_bundle_hash"] = "bad-joint"
    _write_json(bundle, payload)
    evidence = _evidence(tmp_path, bundle)
    gate = evaluate_runtime_ai_gate(evidence.to_gate_input()).to_dict()
    assert "baseline_hash_mismatch" in evidence.baseline_evidence["reason_codes"]
    assert gate["block_buy"] is True


def test_phase18s_immediate_drift_cases(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path, positive_rate=0.5, score_mean=0.1, score_min=0.08, score_max=0.13)
    stable_scores = [0.08, 0.1 - 0.01, 0.1, 0.1 + 0.01, 0.1 + 0.02, 0.13]
    stable = evaluate_runtime_ai_gate(_evidence(tmp_path, bundle, scores=stable_scores).to_gate_input()).to_dict()
    assert stable["decision"] == "PASS"
    hard_prediction = evaluate_runtime_ai_gate(_evidence(tmp_path, bundle, scores=[9.0, 9.1, 9.2, 9.3, 9.4, 9.5]).to_gate_input()).to_dict()
    assert hard_prediction["classification"] == "STATISTICAL_DRIFT_REVIEW_REQUIRED"
    population = evaluate_runtime_ai_gate(_evidence(tmp_path, bundle, candidate_count=1, scores=[0.08, 0.09, 0.10]).to_gate_input()).to_dict()
    assert population["trading_permission_effect"] == "NONE"
    assert population["block_buy"] is False


def test_phase18s_all_negative_without_hard_drift_is_market_no_opportunity(tmp_path: Path) -> None:
    bundle = _bundle_fixture(tmp_path, positive_rate=0.0, score_mean=-0.01, score_min=-0.01, score_max=-0.01)
    gate = evaluate_runtime_ai_gate(_evidence(tmp_path, bundle, scores=[-0.01, -0.01, -0.01, -0.01, -0.01]).to_gate_input()).to_dict()
    assert gate["decision"] == "PASS"
    assert gate["classification"] == "MARKET_NO_OPPORTUNITY"
    assert gate["block_buy"] is False
