from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase18aa_full_ai_artifact_generation_freshness_lineage_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase18aa_artifact_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase18aa_confirms_systemic_trainable_ai_staleness() -> None:
    module = load_module()
    report = module.build_report()

    assert report["primary_judgment"] == "PHASE18_AA_SYSTEMIC_AI_STALENESS_CONFIRMED"
    stale = {(item["component"], item["artifact_id"]): item for item in report["stale_component_list"]}
    assert stale[("Candidate AI", "candidate_training_da0855d123ed1bed")]["train_end"] == "2024-12-02"
    assert stale[("Opportunity AI", "opportunity_training_phase18h_1081babc49b5d26b")]["train_end"] == "2024-12-02"


def test_phase18aa_runtime_promotion_hash_mismatch_is_recorded() -> None:
    module = load_module()
    report = module.build_report()
    resolver = report["runtime_resolver_map"]

    assert "PHASE18_AA_RUNTIME_RESOLVER_MISMATCH_CONFIRMED" in report["secondary_judgments"]
    assert resolver["candidate_hash_match"] is False
    assert resolver["opportunity_hash_match"] is False
    assert resolver["accepted_state_exists"] is False


def test_phase18aa_policy_components_are_not_trainable_models() -> None:
    module = load_module()
    report = module.build_report()
    policies = {item["component"]: item for item in report["policy_rule_components"]}

    assert "Position Management Policy" in policies
    assert "Capital Allocation Policy" in policies
    assert "Safety Policy Engine" in policies
    assert policies["Safety Policy Engine"]["classification"] == "POLICY_OR_RULE_NOT_MODEL"


def test_phase18aa_audit_is_non_mutating_and_recommends_correct_scope() -> None:
    module = load_module()
    report = module.build_report()

    assert report["final_questions"]["retraining_scope"] == ["Candidate AI", "Opportunity AI"]
    assert report["final_questions"]["split_redesign_required"] is True
    assert report["non_mutation_confirmation"]["retraining_performed"] is False
    assert report["non_mutation_confirmation"]["registry_accepted_event_created"] is False
    assert report["non_mutation_confirmation"]["runtime_accepted_state_created"] is False
    assert report["validation"]["model_pickle_not_loaded"] == "PASS"
