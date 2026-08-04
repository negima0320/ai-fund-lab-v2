from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import (
    resolve_accepted_generation,
    resolve_accepted_generation_for_evaluation,
)
from ai_fund_lab_v2.runtime_v2.buy_ai import producer
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions


BUSINESS_DATE = "2026-07-08"
FEATURE_DATE = "2026-07-07"


def test_phase19_ad_u1_a_pointer_missing_is_bootstrap_no_generation(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)

    resolution = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)

    assert resolution.resolution_status == "NO_ACCEPTED_GENERATION"
    assert resolution.block_reason == "NO_ACCEPTED_GENERATION_BOOTSTRAP"
    assert resolution.review_required is True


def test_phase19_ad_u1_a_non_committed_pointer_is_not_runtime_authority(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest(tmp_path)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "STAGED", "bundle_manifest_path": str(manifest)},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "NO_ACCEPTED_GENERATION"
    assert "accepted_generation_pointer_not_committed" in resolution.source_evidence["discovery_rejections"][0]["rejection_reasons"]


def test_phase19_ad_u1_a_manifest_hash_mismatch_fail_closed(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest(tmp_path)
    payload = _read_json(manifest)
    payload["aggregate_hash"] = "0" * 64
    _write_json(manifest, payload)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(manifest)},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_aggregate_hash_mismatch" in resolution.reason_codes


def test_phase19_ad_u1_a_candidate_member_missing_rejects_generation(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest(tmp_path)
    payload = _read_json(manifest)
    payload.pop("candidate_model")
    payload["aggregate_hash"] = _stable_hash({key: value for key, value in payload.items() if key != "aggregate_hash"})
    _write_json(manifest, payload)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(manifest)},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "candidate_member_missing" in resolution.reason_codes


def test_phase19_ad_u1_a_promotion_candidate_pointer_rejected(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    promotion = tmp_path / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / "tx" / "atomic_buy_ai_bundle.json"
    _write_json(promotion, {"generation_id": "promotion"})
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(promotion)},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "promotion_candidate_forbidden_for_runtime" in resolution.reason_codes


def test_phase19_ad_u1_a_no_accepted_generation_blocks_before_legacy_resolution(
    tmp_path: Path, monkeypatch
) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_trading_state(runtime_root)

    def fail_legacy(*args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("legacy resolver reached")

    monkeypatch.setattr(producer, "resolve_buy_ai_artifact_paths", fail_legacy)
    before = _trading_state_snapshot(runtime_root)

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=tmp_path / "features",
        feature_date=FEATURE_DATE,
    )
    after = _trading_state_snapshot(runtime_root)

    assert result.status == "BLOCKED"
    assert result.reason == "NO_ACCEPTED_GENERATION_BOOTSTRAP"
    assert result.lifecycle_gate_evidence is not None
    assert result.lifecycle_gate_evidence["trading_permission_effect"] == "BUY_BLOCK"
    assert result.lifecycle_gate_evidence["runtime_integrity_status"] == "BLOCK"
    assert result.lifecycle_gate_evidence["block_buy"] is True
    assert result.lifecycle_gate_evidence["block_sell"] is False
    assert before == after


def test_phase19_ad_r1_normal_runtime_explicit_model_paths_do_not_bypass_generation_resolver(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    runtime_root = Path(".runtime")
    (runtime_root / "runtime_state").mkdir(parents=True, exist_ok=True)

    def fail_legacy(*args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("legacy explicit model path resolver reached")

    monkeypatch.setattr(producer, "resolve_buy_ai_artifact_paths", fail_legacy)

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=tmp_path / "features",
        feature_date=FEATURE_DATE,
        candidate_model_path=tmp_path / "candidate.pkl",
        opportunity_model_path=tmp_path / "opportunity.pkl",
    )

    assert result.status == "BLOCKED"
    assert result.reason == "NO_ACCEPTED_GENERATION_BOOTSTRAP"
    assert result.lifecycle_gate_evidence is not None
    assert result.lifecycle_gate_evidence["trading_permission_effect"] == "BUY_BLOCK"
    assert result.ai_signals == ()


def test_phase19_ad_r1_lifecycle_gate_receives_same_resolution_instance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime_root = _runtime_root(tmp_path)
    resolution = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)
    calls = {"resolver": 0, "lifecycle_resolution_id": None}

    def fake_resolve(root, **kwargs):
        calls["resolver"] += 1
        return resolution

    class FakeLifecycleEvidence:
        def to_dict(self):
            return {
                "gate_input": {
                    "integrity": {"status": "REVIEW_REQUIRED", "reason": "accepted_missing"},
                    "freshness": {"reason_codes": []},
                    "drift": {},
                },
                "artifact_fields": {
                    "accepted_bundle_id": "",
                    "baseline_identity": "",
                    "current_window_identity": "",
                    "freshness_evidence": {},
                    "baseline_evidence": {},
                    "current_evidence": {},
                    "integrity_evidence": {"status": "REVIEW_REQUIRED"},
                    "reason_codes": ["accepted_generation_pointer_missing"],
                },
            }

    def fake_lifecycle_evidence(**kwargs):
        calls["lifecycle_resolution_id"] = id(kwargs["accepted_generation_resolution"])
        return FakeLifecycleEvidence()

    monkeypatch.setattr(producer, "resolve_accepted_generation", fake_resolve)
    monkeypatch.setattr(producer, "build_runtime_lifecycle_evidence", fake_lifecycle_evidence)

    result = produce_buy_ai_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        feature_root=tmp_path / "features",
        feature_date=FEATURE_DATE,
    )

    assert result.status in {"BLOCKED", "REVIEW_REQUIRED"}
    assert calls["resolver"] == 1
    assert calls["lifecycle_resolution_id"] == id(resolution)


def test_phase19_ad_u1_a_resolved_committed_generation_returns_atomic_members(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest(tmp_path)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(manifest), "aggregate_hash": _read_json(manifest)["aggregate_hash"]},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "RESOLVED_COMMITTED"
    assert resolution.candidate_member is not None
    assert resolution.opportunity_member is not None
    assert resolution.artifact_paths()["candidate_model"].is_file()
    assert resolution.artifact_paths()["opportunity_model"].is_file()


def test_phase23_b_future_effective_generation_is_not_business_date_authority(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest(tmp_path)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(manifest), "aggregate_hash": _read_json(manifest)["aggregate_hash"]},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-06-30")

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_accepted_at_after_business_date" in resolution.reason_codes
    assert "accepted_generation_effective_from_after_business_date" in resolution.reason_codes


def test_phase26_pf3g_fixed_historical_authority_uses_evaluation_time_not_market_date(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest_with_scalers(
        tmp_path,
        generation_id="future-generation",
        accepted_at="2026-07-20T00:00:00+00:00",
        effective_from="2026-07-20",
    )
    _install_generation(runtime_root, manifest)
    payload = _read_json(manifest)
    authority_path = tmp_path / "run" / "historical_evaluation_authority.json"
    _write_json(
        authority_path,
        {
            "schema_version": "historical_evaluation_authority.v1",
            "generation_id": payload["generation_id"],
            "bundle_manifest_path": str(manifest),
            "accepted_at": payload["accepted_at"],
            "effective_from": payload["effective_from"],
            "aggregate_hash": payload["aggregate_hash"],
            "latest_fallback_used": False,
            "fixed_at": "2026-08-03T00:00:00Z",
            "evaluation_authority_time": "2026-08-03T00:00:00Z",
            "historical_business_date_acceptance_comparison": "NOT_APPLIED_TO_ACCEPTED_GENERATION",
        },
    )

    production_resolution = resolve_accepted_generation(runtime_root, business_date="2022-09-01")
    historical_resolution = resolve_accepted_generation(runtime_root, business_date="2022-09-01", fixed_authority_path=authority_path)

    assert production_resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_accepted_at_after_business_date" in production_resolution.reason_codes
    assert historical_resolution.resolution_status == "RESOLVED_COMMITTED"
    assert historical_resolution.source_evidence["market_as_of_business_date"] == "2022-09-01"
    assert historical_resolution.source_evidence["selected_business_date"] == "2026-08-03"
    assert historical_resolution.source_evidence["business_date_temporal_comparison_applied"] is False
    assert historical_resolution.source_evidence["evaluation_authority_time_temporal_comparison_applied"] is True
    binding = historical_resolution.binding_evidence(runtime_mode="historical-smoke", business_date="2022-09-01", consumer="test")
    assert binding["temporal_binding_status"] == "PASS"
    assert binding["business_date_conflict"] is False


def test_phase26_pf3g_run_start_evaluation_authority_rejects_future_generation(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest_with_scalers(
        tmp_path,
        generation_id="future-generation",
        accepted_at="2026-07-20T00:00:00+00:00",
        effective_from="2026-07-20",
    )
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(manifest), "aggregate_hash": _read_json(manifest)["aggregate_hash"]},
    )

    resolution = resolve_accepted_generation_for_evaluation(
        runtime_root,
        evaluation_authority_time="2026-07-19T23:59:59Z",
    )

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_accepted_at_after_business_date" in resolution.reason_codes
    assert "accepted_generation_effective_from_after_business_date" in resolution.reason_codes
    assert resolution.source_evidence["business_date_temporal_comparison_applied"] is False
    assert resolution.source_evidence["evaluation_authority_time_temporal_comparison_applied"] is True


def test_phase23_b_business_date_bound_generation_resolves_without_latest_fallback(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest(tmp_path)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(manifest), "aggregate_hash": _read_json(manifest)["aggregate_hash"]},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "RESOLVED_COMMITTED"
    assert resolution.source_evidence["legacy_component_fallback_used"] is False
    assert resolution.source_evidence["promotion_candidate_fallback_used"] is False
    assert resolution.source_evidence["business_date"] == "2026-07-01"
    assert resolution.source_evidence["temporal_authority_status"] == "PASS"


def test_phase23_l_business_date_resolves_historical_generation_before_future_current_pointer(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    old_manifest = _accepted_manifest_with_scalers(tmp_path, generation_id="old-generation", accepted_at="2026-06-15T00:00:00+00:00", effective_from="2026-06-15")
    future_manifest = _accepted_manifest_with_scalers(tmp_path, generation_id="future-generation", accepted_at="2026-07-20T00:00:00+00:00", effective_from="2026-07-20")
    _install_generation(runtime_root, old_manifest)
    _install_generation(runtime_root, future_manifest)
    _append_history(runtime_root, old_manifest)
    _append_history(runtime_root, future_manifest)
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(future_manifest), "aggregate_hash": _read_json(future_manifest)["aggregate_hash"]},
    )

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "RESOLVED_COMMITTED"
    assert resolution.generation_id == "old-generation"
    assert resolution.source_evidence["eligible_candidate_count"] == 1
    assert resolution.source_evidence["future_generation_used"] is False
    assert resolution.source_evidence["latest_fallback_used"] is False


def test_phase23_l_multiple_eligible_generations_fail_closed_as_authority_conflict(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    first = _accepted_manifest_with_scalers(tmp_path, generation_id="generation-a", accepted_at="2026-06-01T00:00:00+00:00", effective_from="2026-06-01")
    second = _accepted_manifest_with_scalers(tmp_path, generation_id="generation-b", accepted_at="2026-06-20T00:00:00+00:00", effective_from="2026-06-20")
    _install_generation(runtime_root, first)
    _install_generation(runtime_root, second)
    _append_history(runtime_root, first)
    _append_history(runtime_root, second)

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_conflict_multiple_eligible" in resolution.reason_codes
    assert resolution.source_evidence["generation_conflict"] is True


def test_phase23_l_revoked_superseded_and_expired_generations_are_excluded(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    revoked = _accepted_manifest_with_scalers(tmp_path, generation_id="revoked", accepted_at="2026-06-01T00:00:00+00:00", effective_from="2026-06-01", extra={"revoked_at": "2026-06-15"})
    superseded = _accepted_manifest_with_scalers(tmp_path, generation_id="superseded", accepted_at="2026-06-01T00:00:00+00:00", effective_from="2026-06-01", extra={"superseded_at": "2026-06-15"})
    expired = _accepted_manifest_with_scalers(tmp_path, generation_id="expired", accepted_at="2026-06-01T00:00:00+00:00", effective_from="2026-06-01", extra={"effective_until": "2026-06-15"})
    for manifest in (revoked, superseded, expired):
        _install_generation(runtime_root, manifest)
        _append_history(runtime_root, manifest)

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_revoked_at_lte_business_date" in resolution.reason_codes
    assert "accepted_generation_superseded_at_lte_business_date" in resolution.reason_codes
    assert "accepted_generation_effective_until_before_business_date" in resolution.reason_codes


def test_phase23_l_generation_absence_fails_closed_for_business_date(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "NO_ACCEPTED_GENERATION"
    assert "NO_ACCEPTED_GENERATION_BOOTSTRAP" in resolution.reason_codes
    assert resolution.source_evidence["candidate_count"] == 0


def test_phase23_l_scaler_hash_mismatch_rejects_historical_generation(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    manifest = _accepted_manifest_with_scalers(tmp_path, generation_id="bad-scaler", accepted_at="2026-06-01T00:00:00+00:00", effective_from="2026-06-01")
    payload = _read_json(manifest)
    payload["candidate_member"]["scaler_hash"] = "0" * 64
    payload["aggregate_hash"] = _stable_hash({key: value for key, value in payload.items() if key != "aggregate_hash"})
    _write_json(manifest, payload)
    _install_generation(runtime_root, manifest)
    _append_history(runtime_root, manifest)

    resolution = resolve_accepted_generation(runtime_root, business_date="2026-07-01")

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "candidate_scaler_hash_mismatch" in resolution.reason_codes


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "runtime_state").mkdir(parents=True, exist_ok=True)
    return root


def _write_trading_state(root: Path) -> None:
    _write_json(root / "persistent_ledger" / "state.json", {"cash": 1_000_000, "positions": []})
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})


def _trading_state_snapshot(root: Path) -> dict[str, str]:
    paths = [
        root / "persistent_ledger" / "state.json",
        root / "pending_order_plan" / "pending_order_plan.json",
        root / "runtime_state" / "current_state.json",
    ]
    return {str(path.relative_to(root)): path.read_text(encoding="utf-8") for path in paths}


def _accepted_manifest(tmp_path: Path) -> Path:
    generation_dir = tmp_path / "accepted_generation"
    candidate = generation_dir / "candidate_model.pkl"
    opportunity = generation_dir / "opportunity_model.pkl"
    metrics = generation_dir / "opportunity_metrics.json"
    calibration = generation_dir / "calibration.json"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(b"candidate-model")
    opportunity.write_bytes(b"opportunity-model")
    _write_json(metrics, {"status": "PASS"})
    _write_json(calibration, {"status": "PASS"})
    payload = {
        "schema_version": "accepted_buy_ai_bundle.v1",
        "generation_id": "phase19-u1-a-fixture-generation",
        "accepted_at": "2026-07-01T00:00:00+00:00",
        "effective_from": "2026-07-01",
        "authority_decision": "fixture-authority-decision",
        "candidate_model": {"artifact_path": str(candidate), "model_hash": _sha(candidate)},
        "opportunity_model": {"artifact_path": str(opportunity), "model_hash": _sha(opportunity)},
        "opportunity_metrics": {"artifact_path": str(metrics)},
        "calibration": {"artifact_path": str(calibration)},
        "runtime_baseline": {"candidate_population": 30, "positive_coverage": 0.5},
        "freshness_metadata": {"label_safe_cutoff": "2026-06-01"},
        "rollback_reference": {"previous_generation_ref": None},
    }
    payload["aggregate_hash"] = _stable_hash(payload)
    manifest = generation_dir / "accepted_generation_manifest.json"
    _write_json(manifest, payload)
    return manifest


def _accepted_manifest_with_scalers(
    tmp_path: Path,
    *,
    generation_id: str,
    accepted_at: str,
    effective_from: str,
    extra: dict | None = None,
) -> Path:
    generation_dir = tmp_path / "accepted_generation_sources" / generation_id
    candidate = generation_dir / "candidate_model.pkl"
    opportunity = generation_dir / "opportunity_model.pkl"
    candidate_scaler = generation_dir / "candidate_scaler.pkl"
    opportunity_scaler = generation_dir / "opportunity_scaler.pkl"
    generation_dir.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(f"{generation_id}-candidate-model".encode("ascii"))
    opportunity.write_bytes(f"{generation_id}-opportunity-model".encode("ascii"))
    candidate_scaler.write_bytes(f"{generation_id}-candidate-scaler".encode("ascii"))
    opportunity_scaler.write_bytes(f"{generation_id}-opportunity-scaler".encode("ascii"))
    payload = {
        "schema_version": "accepted_buy_ai_bundle.v1",
        "generation_id": generation_id,
        "accepted_at": accepted_at,
        "effective_from": effective_from,
        "runtime_eligibility_status": "RUNTIME_ELIGIBLE_ACCEPTED_ONLY",
        "authority_decision": "fixture-authority-decision",
        "candidate_member": {
            "model_file": str(candidate),
            "model_hash": _sha(candidate),
            "scaler_file": str(candidate_scaler),
            "scaler_hash": _sha(candidate_scaler),
            "feature_schema_hash": _stable_hash({"feature_order": ["candidate_score"]}),
        },
        "opportunity_member": {
            "model_file": str(opportunity),
            "model_hash": _sha(opportunity),
            "scaler_file": str(opportunity_scaler),
            "scaler_hash": _sha(opportunity_scaler),
            "feature_schema_hash": _stable_hash({"feature_order": ["candidate_score", "opportunity_score"]}),
        },
        "runtime_baseline": {"candidate_population": 30, "positive_coverage": 0.5},
        "freshness_metadata": {"label_safe_cutoff": "2026-05-01"},
        "rollback_reference": {"previous_generation_ref": None},
    }
    payload.update(extra or {})
    payload["aggregate_hash"] = _stable_hash(payload)
    manifest = generation_dir / "accepted_generation_manifest.json"
    _write_json(manifest, payload)
    return manifest


def _install_generation(runtime_root: Path, manifest: Path) -> Path:
    payload = _read_json(manifest)
    target = runtime_root / "ai_lifecycle" / "generations" / payload["generation_id"] / "accepted_generation_manifest.json"
    _write_json(target, payload)
    return target


def _append_history(runtime_root: Path, manifest: Path) -> None:
    payload = _read_json(manifest)
    path = runtime_root / "ai_lifecycle" / "authority_history" / "accepted_generation_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event_type": "ACCEPTED_GENERATION_CREATED",
        "generation_id": payload["generation_id"],
        "accepted_at": payload["accepted_at"],
        "effective_from": payload["effective_from"],
        "aggregate_hash": payload["aggregate_hash"],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
