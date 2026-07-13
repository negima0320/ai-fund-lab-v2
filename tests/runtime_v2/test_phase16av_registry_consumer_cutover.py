from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.artifact_lookup import (
    RuntimeArtifactLookupHalt,
    resolve_capital_allocation_policy_artifacts,
    resolve_feature_schema_artifacts,
    resolve_position_management_policy_artifacts,
    resolve_runtime_capital_policy_path,
)
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import (
    PROHIBITED_OPPORTUNITY_PHASE5E_METRICS_PATH,
    resolve_buy_ai_artifact_paths,
)


LEGACY_CANDIDATE_MODEL = Path(".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl")
LEGACY_OPPORTUNITY_MODEL = Path("reports/opportunity_ai/phase5p/models/opportunity_model.pkl")
LEGACY_OPPORTUNITY_METRICS = Path("reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json")
LEGACY_PM_POLICY = Path(".runtime/phase9/policy_manifests/position_policy_manifest.json")
LEGACY_CAPITAL_POLICY = Path(".runtime/phase9/policy_manifests/capital_policy_manifest.json")
LOADABLE_CAPITAL_POLICY = Path("configs/runtime_v2/capital_deployment.json")
LEGACY_FEATURE_SCHEMA = Path(".runtime/operations/feature_consumer_readiness/2026-07-10.json")


def test_candidate_and_opportunity_registry_paths_semantically_match_legacy() -> None:
    paths = resolve_buy_ai_artifact_paths()
    assert _sha(paths["candidate_model"]) == _sha(LEGACY_CANDIDATE_MODEL)
    assert _sha(paths["opportunity_model"]) == _sha(LEGACY_OPPORTUNITY_MODEL)
    assert _sha(paths["opportunity_metrics"]) == _sha(LEGACY_OPPORTUNITY_METRICS)


def test_explicit_legacy_override_rejected() -> None:
    with pytest.raises(RuntimeArtifactLookupHalt, match="cannot override Registry authority"):
        resolve_buy_ai_artifact_paths(candidate_model_path=LEGACY_CANDIDATE_MODEL)


def test_phase5e_metrics_rejected() -> None:
    with pytest.raises(RuntimeArtifactLookupHalt, match="Phase5-E"):
        resolve_buy_ai_artifact_paths(opportunity_training_metrics_path=PROHIBITED_OPPORTUNITY_PHASE5E_METRICS_PATH)


def test_opportunity_same_set_model_metrics() -> None:
    paths = resolve_buy_ai_artifact_paths()
    assert paths["opportunity_model"].is_file()
    assert paths["opportunity_metrics"].is_file()
    assert "phase5e" not in paths["opportunity_metrics"].as_posix().lower()


def test_feature_schema_registry_member_matches_legacy() -> None:
    feature = resolve_feature_schema_artifacts()
    member = feature.require_member("FEATURE_SCHEMA")
    assert _sha(member.physical_path) == member.content_hash
    assert _sha(member.physical_path) == _sha(LEGACY_FEATURE_SCHEMA)


def test_pm_policy_registry_members_match_legacy() -> None:
    pm = resolve_position_management_policy_artifacts()
    assert _sha(pm.require_member("CODE_POLICY").physical_path) == _sha(LEGACY_PM_POLICY)
    assert pm.require_member("RUNTIME_ADAPTER").physical_path.is_file()
    assert pm.require_member("BEHAVIOR_CONTRACT").physical_path.is_file()


def test_capital_policy_registry_member_is_loadable_policy_json() -> None:
    capital = resolve_capital_allocation_policy_artifacts()
    policy_member = capital.require_member("POLICY")
    assert _sha(policy_member.physical_path) == _sha(LOADABLE_CAPITAL_POLICY)
    assert capital.require_member("POLICY_SCHEMA").physical_path.is_file()
    assert capital.require_member("POLICY_VERSION").physical_path.is_file()


def test_capital_explicit_legacy_override_rejected() -> None:
    with pytest.raises(RuntimeArtifactLookupHalt, match="cannot override Registry authority"):
        resolve_runtime_capital_policy_path(LEGACY_CAPITAL_POLICY)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
