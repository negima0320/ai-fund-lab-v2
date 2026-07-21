from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.ap_runtime_materialization import (
    Phase19APContext,
    materialize_phase19_ap_payloads,
    validate_authority_history_preview,
    validate_freshness_metadata,
    validate_materialization_preview,
    validate_runtime_baseline,
)
from ai_fund_lab_v2.runtime_v2.accepted_generation_consumer_adapter import (
    enforce_feature_order,
    validate_manifest_compatibility,
)


ROOT = Path(__file__).resolve().parents[2]
GENERATION = Path(".runtime/ai_lifecycle/generations/phase19_al_unified_generation_eb72ea5bea87c787/generation_manifest.json")


def test_phase19_ap_materialization_is_deterministic_and_recent_holdout_unused() -> None:
    first = materialize_phase19_ap_payloads(Phase19APContext(repo_root=ROOT, generation_manifest_path=GENERATION))
    second = materialize_phase19_ap_payloads(Phase19APContext(repo_root=ROOT, generation_manifest_path=GENERATION))

    assert first == second
    baseline = first["runtime_baseline_artifact"]
    freshness = first["freshness_metadata_preview"]
    materialization = first["accepted_generation_materialization_preview"]

    assert validate_runtime_baseline(baseline)["status"] == "PASS"
    assert validate_runtime_baseline(baseline)["recent_holdout_accessed"] is False
    assert baseline["threshold_policy"]["threshold_status"] == "HUMAN_REVIEW_REQUIRED"
    assert validate_freshness_metadata(freshness)["status"] == "PASS"
    assert freshness["materialization_time"]["accepted_at"] is None
    assert len(freshness["freshness_taxonomy"]) == 8
    assert validate_materialization_preview(materialization)["status"] == "PASS"
    assert materialization["accepted"] is False
    assert materialization["runtime_eligibility"] is False
    assert all(value == 0 for value in materialization["no_mutation"].values())


def test_phase19_ap_runtime_consumer_adapter_loads_manifest_bound_members() -> None:
    payloads = materialize_phase19_ap_payloads(Phase19APContext(repo_root=ROOT, generation_manifest_path=GENERATION))
    result = validate_manifest_compatibility(
        payloads["accepted_generation_materialization_preview"],
        repo_root=ROOT,
        load_pickles=True,
    )

    assert result.status == "PASS"
    assert result.block_buy is False
    assert result.block_sell is False
    assert result.candidate is not None
    assert result.opportunity is not None
    assert result.legacy_fallback_used is False
    assert result.manual_path_used is False


def test_phase19_ap_feature_order_enforcement_blocks_mismatch() -> None:
    expected = ["a", "b", "c"]

    assert enforce_feature_order(["a", "b", "c"], expected)["status"] == "PASS"
    mismatch = enforce_feature_order(["a", "c", "b"], expected)

    assert mismatch["status"] == "BUY_ONLY_BLOCK"
    assert mismatch["order_match"] is False


def test_phase19_ap_consumer_adapter_fail_closed_missing_scaler(tmp_path: Path) -> None:
    payloads = materialize_phase19_ap_payloads(Phase19APContext(repo_root=ROOT, generation_manifest_path=GENERATION))
    manifest = json.loads(json.dumps(payloads["accepted_generation_materialization_preview"]))
    manifest["candidate_member"]["scaler_file"] = ""
    manifest["aggregate_hash_preview"] = _stable_hash({key: value for key, value in manifest.items() if key != "aggregate_hash_preview"})

    result = validate_manifest_compatibility(manifest, repo_root=ROOT, load_pickles=False)

    assert result.status == "BUY_ONLY_BLOCK"
    assert "missing_scaler" in result.reason_codes
    assert result.block_buy is True
    assert result.block_sell is False


def test_phase19_ap_authority_history_preview_not_appended() -> None:
    payloads = materialize_phase19_ap_payloads(Phase19APContext(repo_root=ROOT, generation_manifest_path=GENERATION))
    validation = validate_authority_history_preview(payloads["authority_history_append_preview"])

    assert validation["status"] == "PASS"
    assert validation["append_status"] == "NOT_EXECUTED"
    assert validation["not_appended"] is True


def _stable_hash(payload: object) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
