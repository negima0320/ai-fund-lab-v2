from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase18y_accepted_atomic_buy_ai_bundle_contract_completion.py"


def load_module():
    spec = importlib.util.spec_from_file_location("phase18y_contract_completion", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase18y_baseline_rebuild_is_deterministic_and_not_current_runtime() -> None:
    module = load_module()
    bundle = module.load_source_bundle()
    first = module.build_materialized_baseline(bundle)
    second = module.build_materialized_baseline(bundle)

    assert first["baseline_hash"] == second["baseline_hash"]
    assert first["row_count"] == 1440
    assert first["lineage"]["current_runtime_evidence_used"] is False
    assert first["lineage"]["paper_ledger_used"] is False
    assert first["lineage"]["backtest_pnl_used"] is False
    assert first["baseline_date_range"]["authority_split"] == "recent_holdout"


def test_phase18y_pre_acceptance_rejects_hash_mismatch_and_current_baseline() -> None:
    module = load_module()
    bundle = module.load_source_bundle()
    baseline = module.build_materialized_baseline(bundle)
    freshness = module.build_freshness_metadata(
        bundle,
        model_cutoff=module.derive_model_training_cutoff(module.ROOT / bundle["opportunity_training"]["training_dir"]),
    )

    tampered = dict(baseline)
    tampered["prediction_distribution_values"] = [0.0] + tampered["prediction_distribution_values"][1:]
    validation = module.validate_pre_acceptance(bundle, tampered, freshness)
    assert validation["checks"]["baseline_hash"] == "FAIL"

    current = dict(baseline)
    current["lineage"] = dict(baseline["lineage"])
    current["lineage"]["current_runtime_evidence_used"] = True
    current["baseline_hash"] = module.stable_hash({key: value for key, value in current.items() if key != "baseline_hash"})
    validation = module.validate_pre_acceptance(bundle, current, freshness)
    assert validation["checks"]["baseline_not_current_runtime"] == "FAIL"


def test_phase18y_training_cutoff_is_derived_from_training_split_and_blocks_stale_model() -> None:
    module = load_module()
    bundle = module.load_source_bundle()
    cutoff = module.derive_model_training_cutoff(module.ROOT / bundle["opportunity_training"]["training_dir"])
    freshness = module.build_freshness_metadata(bundle, model_cutoff=cutoff)
    baseline = module.build_materialized_baseline(bundle)
    validation = module.validate_pre_acceptance(bundle, baseline, freshness)

    assert cutoff["model_training_cutoff"] == "2024-12-02"
    assert freshness["label_safe_cutoff"] == "2026-06-04"
    assert validation["checks"]["model_training_lag_business_days"] == 69
    assert validation["checks"]["model_training_lag_status"] == "BLOCK"


def test_phase18y_contract_completion_does_not_materialize_accepted_state_when_blocked() -> None:
    module = load_module()
    before = module.source_snapshot()
    report = module.build_completed_transaction()
    after = module.source_snapshot()

    assert report["final_judgment"] == "PHASE18_Y_CONTRACT_COMPLETION_BLOCKED"
    assert report["eligibility_decision"]["runtime_use_eligible"] is False
    assert report["eligibility_decision"]["registry_accepted_event_requested"] is False
    assert report["authority_review"]["registry_accepted_event_authorized"] is False
    assert report["accepted_state_materialized"] is False
    assert before == after
    assert Path(report["materialized_runtime_baseline"]["path"]).exists()
    assert json.loads(Path(report["materialized_runtime_baseline"]["path"]).read_text())["baseline_hash"] == report["materialized_runtime_baseline"]["baseline_hash"]
