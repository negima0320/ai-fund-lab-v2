from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase18z_model_training_cutoff_root_cause_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase18z_cutoff_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase18z_confirms_true_stale_model_from_training_splits() -> None:
    module = load_module()
    report = module.build_report()

    assert report["final_judgment"] == "PHASE18_Z_TRUE_STALE_MODEL_CONFIRMED"
    assert report["root_cause_decision"]["TRUE_STALE_MODEL"] is True
    assert report["root_cause_decision"]["TRAINING_METADATA_LINEAGE_BUG"] is False
    assert report["root_cause_decision"]["CUTOFF_DEFINITION_BUG"] is False
    assert report["candidate_training_period"]["train"]["split_end"] == "2024-12-02"
    assert report["opportunity_training_period"]["train"]["split_end"] == "2024-12-02"
    assert report["atomic_cutoff_decision"]["adopted_cutoff"] == "2024-12-02"


def test_phase18z_holdout_is_not_training_and_lag_exceeds_threshold() -> None:
    module = load_module()
    report = module.build_report()

    assert report["holdout_separation"]["validation_after_train"] is True
    assert report["holdout_separation"]["test_after_validation"] is True
    assert report["holdout_separation"]["recent_holdout_after_test"] is True
    assert report["holdout_separation"]["recent_holdout_is_training_data"] is False
    assert report["formal_calendar_lag"]["business_day_lag"] == 69
    assert report["formal_calendar_lag"]["business_day_lag"] > 20


def test_phase18z_legacy_resolver_models_differ_from_promotion_candidate() -> None:
    module = load_module()
    report = module.build_report()

    assert report["legacy_resolver_comparison"]["candidate_same"] is False
    assert report["legacy_resolver_comparison"]["opportunity_same"] is False
    assert report["legacy_resolver_comparison"]["promotion_opportunity"]["hash"] == report["opportunity_model_payload"]["hash"]


def test_phase18z_audit_is_non_mutating() -> None:
    module = load_module()
    report = module.build_report()

    assert report["non_mutation_confirmation"]["registry_accepted_updated"] is False
    assert report["non_mutation_confirmation"]["runtime_accepted_state_created"] is False
    assert report["non_mutation_confirmation"]["retraining_performed"] is False
    assert report["non_mutation_confirmation"]["threshold_relaxed"] is False
