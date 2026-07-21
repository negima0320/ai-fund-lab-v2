from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.buy_ai import producer
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import produce_buy_ai_decisions


BUSINESS_DATE = "2026-07-08"
FEATURE_DATE = "2026-07-07"


def test_phase19_ad_u1_a_pointer_missing_is_bootstrap_no_generation(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)

    resolution = resolve_accepted_generation(runtime_root)

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

    resolution = resolve_accepted_generation(runtime_root)

    assert resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_pointer_not_committed" in resolution.reason_codes


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

    resolution = resolve_accepted_generation(runtime_root)

    assert resolution.resolution_status == "HASH_MISMATCH"
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

    resolution = resolve_accepted_generation(runtime_root)

    assert resolution.resolution_status == "INCOMPATIBLE_GENERATION"
    assert "candidate_member_missing" in resolution.reason_codes


def test_phase19_ad_u1_a_promotion_candidate_pointer_rejected(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    promotion = tmp_path / ".runtime" / "artifact_registry" / "promotion_candidates" / "transactions" / "tx" / "atomic_buy_ai_bundle.json"
    _write_json(promotion, {"generation_id": "promotion"})
    _write_json(
        runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json",
        {"transaction_state": "COMMITTED", "bundle_manifest_path": str(promotion)},
    )

    resolution = resolve_accepted_generation(runtime_root)

    assert resolution.resolution_status == "INVALID_MANIFEST"
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
    resolution = resolve_accepted_generation(runtime_root)
    calls = {"resolver": 0, "lifecycle_resolution_id": None}

    def fake_resolve(root):
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

    resolution = resolve_accepted_generation(runtime_root)

    assert resolution.resolution_status == "RESOLVED_COMMITTED"
    assert resolution.candidate_member is not None
    assert resolution.opportunity_member is not None
    assert resolution.artifact_paths()["candidate_model"].is_file()
    assert resolution.artifact_paths()["opportunity_model"].is_file()


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
