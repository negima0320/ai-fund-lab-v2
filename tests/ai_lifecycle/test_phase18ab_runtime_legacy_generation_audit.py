from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase18ab_runtime_legacy_model_provenance_and_ai_generation_pipeline_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase18ab_generation_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase18ab_confirms_runtime_uses_legacy_accepted_models() -> None:
    module = load_module()
    report = module.build_report()

    assert report["primary_judgment"] == "PHASE18_AB_SYSTEMIC_AI_GENERATION_GAP_CONFIRMED"
    assert report["runtime_legacy_model_provenance"]["candidate"]["runtime_status"] == "Registry accepted set Runtime eligible"
    assert report["runtime_legacy_model_provenance"]["opportunity"]["runtime_status"] == "Registry accepted set Runtime eligible"


def test_phase18ab_runtime_and_promotion_candidate_hashes_differ() -> None:
    module = load_module()
    report = module.build_report()
    comparison = report["runtime_resolver_matrix"]["hash_comparison"]

    assert comparison["candidate_runtime_equals_promotion"] is False
    assert comparison["opportunity_runtime_equals_promotion"] is False
    assert "PHASE18_AB_RUNTIME_RESOLVER_REMEDIATION_REQUIRED" in report["secondary_judgments"]


def test_phase18ab_latest_dataset_does_not_imply_latest_ai() -> None:
    module = load_module()
    report = module.build_report()

    assert report["final_answers"]["latest_dataset_means_latest_ai"] is False
    assert report["final_answers"]["ai_generation_pipeline_complete"] is False
    assert report["latest_ai_maintenance_design"]["dataset_to_latest_ai_contract"]["complete"] is False
    assert report["latest_ai_maintenance_design"]["weekly_lifecycle_scheduler"]["runtime_hot_swap_allowed"] is False


def test_phase18ab_read_only_and_retraining_scope() -> None:
    module = load_module()
    report = module.build_report()

    assert report["final_answers"]["retraining_required"] is True
    assert report["final_answers"]["retraining_scope"] == ["Candidate AI", "Opportunity AI"]
    assert report["non_mutation_confirmation"]["retraining_performed"] is False
    assert report["non_mutation_confirmation"]["registry_changed"] is False
    assert report["non_mutation_confirmation"]["runtime_changed"] is False
    assert report["non_mutation_confirmation"]["model_pickle_loaded"] is False
