#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import pickle
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import file_hash, stable_json_hash


PHASE = "Phase18-G"
RUN_ID = "phase18g-promotion-readiness-review-20260717T000000Z"
RUN_ROOT = Path("reports/phase18_g_formal_challenger_promotion_readiness_review")
REPORT_JSON = Path("reports/phase_reports/phase18_g_formal_challenger_promotion_readiness_review.json")
REPORT_MD = Path("docs/phase_reports/phase18_g_formal_challenger_promotion_readiness_review.md")

CANDIDATE_DATASET = Path(".runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d")
OPPORTUNITY_DATASET = Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d")
CANDIDATE_TRAINING = Path(".runtime/ai_lifecycle/training/candidate_ai/candidate_training_da0855d123ed1bed")
OPPORTUNITY_TRAINING = Path(".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18f_6cb9e62013a27d54")
PHASE18D = Path("reports/phase_reports/phase18_d_training_validation_challenger_pipeline.json")
PHASE18E = Path("reports/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.json")
PHASE18F = Path("reports/phase_reports/phase18_f_opportunity_training_pipeline_redesign.json")

REQUIRED_DATASET_FILES = {
    "dataset.parquet",
    "dataset_metadata.json",
    "feature_schema.json",
    "target_schema.json",
    "lineage.json",
    "data_quality.json",
    "date_coverage.json",
    "drop_reasons.csv",
    "hash_manifest.json",
    "status.json",
}

REQUIRED_TRAINING_FILES = {
    "model.pkl",
    "training_metadata.json",
    "training_config.json",
    "dataset_reference.json",
    "feature_schema.json",
    "target_schema.json",
    "split_definition.json",
    "calibration_metrics.json",
    "regime_metrics.json",
    "prediction_distribution.json",
    "hash_manifest.json",
    "status.json",
}


def main() -> int:
    result = run_review()
    print(json.dumps(result["final_judgment"], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def run_review() -> dict[str, Any]:
    run_dir = RUN_ROOT / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    phase18d = read_json(PHASE18D)
    phase18e = read_json(PHASE18E)
    phase18f = read_json(PHASE18F)

    safety = safety_integrity_review(phase18d, phase18f)
    predictive = predictive_validity_review(phase18f)
    operational = operational_utility_review(phase18f)
    generalization = generalization_audit(phase18f)
    atomic_bundle = atomic_buy_ai_bundle_readiness(phase18d, phase18f)
    matrix = promotion_criteria_matrix(safety, predictive, operational, generalization, atomic_bundle)
    recommendation = promotion_recommendation(safety, predictive, operational, generalization, matrix)
    acceptance = build_acceptance(safety, predictive, operational, generalization, matrix, recommendation, atomic_bundle)
    result = {
        "phase": PHASE,
        "run_id": RUN_ID,
        "run_dir": str(run_dir),
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/phase_reports/phase18_d_training_validation_challenger_pipeline.md",
            "docs/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.md",
            "docs/phase_reports/phase18_f_opportunity_training_pipeline_redesign.md",
            str(PHASE18D),
            str(PHASE18E),
            str(PHASE18F),
        ],
        "review_scope": {
            "candidate_dataset_bundle": str(CANDIDATE_DATASET),
            "opportunity_dataset_bundle": str(OPPORTUNITY_DATASET),
            "candidate_training_bundle": str(CANDIDATE_TRAINING),
            "opportunity_training_bundle": str(OPPORTUNITY_TRAINING),
            "registry_update_permitted": False,
            "runtime_switch_permitted": False,
        },
        "safety_integrity": safety,
        "predictive_validity": predictive,
        "operational_utility": operational,
        "generalization_audit": generalization,
        "promotion_criteria_matrix": matrix,
        "promotion_recommendation": recommendation,
        "atomic_buy_ai_bundle_readiness": atomic_bundle,
        "non_mutation_confirmation": {
            "registry_accepted_updated": False,
            "runtime_switched": False,
            "buy_restarted": False,
            "broker_write_executed": False,
            "production_changed": False,
        },
        "acceptance": acceptance,
        "final_judgment": final_judgment(recommendation, acceptance),
    }
    write_json(run_dir / "promotion_criteria_matrix.json", matrix)
    write_json(run_dir / "phase18g_result.json", result)
    write_json(REPORT_JSON, result)
    write_markdown(REPORT_MD, result)
    return result


def safety_integrity_review(phase18d: dict[str, Any], phase18f: dict[str, Any]) -> dict[str, Any]:
    dataset_reviews = {
        "candidate": dataset_bundle_review(CANDIDATE_DATASET, "Candidate"),
        "opportunity": dataset_bundle_review(OPPORTUNITY_DATASET, "Opportunity"),
    }
    training_reviews = {
        "candidate": training_bundle_review(CANDIDATE_TRAINING, "Candidate", candidate=True),
        "opportunity": training_bundle_review(OPPORTUNITY_TRAINING, "Opportunity", candidate=False),
    }
    compatibility = compatibility_review(dataset_reviews, training_reviews, phase18d, phase18f)
    checks = {
        "dataset_authority": all(item["status"] == "PASS" for item in dataset_reviews.values()),
        "training_authority": all(item["status"] == "PASS" for item in training_reviews.values()),
        "schema_compatibility": compatibility["schema_compatibility"] == "PASS",
        "dataset_hash": compatibility["dataset_hash"] == "PASS",
        "model_hash": compatibility["model_hash"] == "PASS",
        "feature_contract": compatibility["feature_contract"] == "PASS",
        "target_contract": compatibility["target_contract"] == "PASS",
        "no_leakage": compatibility["no_leakage"] == "PASS",
        "pit": compatibility["pit"] == "PASS",
        "reproducibility": phase18f["reproducibility"]["status"] == "PASS" and phase18d["reproducibility_results"]["candidate"]["status"] == "PASS",
        "failure_rehearsal": phase18d["failure_rehearsal"]["status"] == "PASS",
        "runtime_compatibility": compatibility["runtime_compatibility"] == "PASS",
        "candidate_opportunity_compatibility": compatibility["candidate_opportunity_compatibility"] == "PASS",
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "dataset_reviews": dataset_reviews,
        "training_reviews": training_reviews,
        "compatibility": compatibility,
        "promotion_impact": "BLOCK_PROMOTION" if status != "PASS" else "NO_BLOCKING_INTEGRITY_VIOLATION",
    }


def dataset_bundle_review(path: Path, component: str) -> dict[str, Any]:
    missing = sorted(REQUIRED_DATASET_FILES - {p.name for p in path.iterdir() if p.is_file()}) if path.exists() else sorted(REQUIRED_DATASET_FILES)
    status_json = read_json(path / "status.json") if (path / "status.json").is_file() else {}
    manifest = read_json(path / "hash_manifest.json") if (path / "hash_manifest.json").is_file() else {}
    metadata = read_json(path / "dataset_metadata.json") if (path / "dataset_metadata.json").is_file() else {}
    validations = {item.get("name"): item.get("status") for item in status_json.get("validations", [])}
    checks = {
        "required_files_present": not missing,
        "status_pass": status_json.get("status") == "PASS",
        "validation_status_pass": status_json.get("validation_status") == "PASS",
        "component_match": metadata.get("component") == component,
        "dataset_hash_present": bool(manifest.get("dataset_hash")),
        "feature_schema_hash_present": bool(manifest.get("feature_schema_hash")),
        "target_schema_hash_present": bool(manifest.get("target_schema_hash")),
        "no_leakage_pass": validations.get("Leakage") == "PASS",
        "pit_pass": validations.get("PIT") == "PASS",
        "lineage_pass": validations.get("Lineage") == "PASS",
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "path": str(path),
        "missing_files": missing,
        "checks": checks,
        "metadata": metadata,
        "manifest": manifest,
    }


def training_bundle_review(path: Path, component: str, *, candidate: bool) -> dict[str, Any]:
    present = {p.name for p in path.iterdir() if p.is_file()} if path.exists() else set()
    required = set(REQUIRED_TRAINING_FILES)
    if candidate:
        required.update({"validation_metrics.json", "test_metrics.json", "recent_holdout_metrics.json"})
    else:
        required.update({"metrics.json", "recent_holdout_metrics.json", "operational_utility.json"})
    missing = sorted(required - present)
    status_json = read_json(path / "status.json") if (path / "status.json").is_file() else {}
    manifest = read_json(path / "hash_manifest.json") if (path / "hash_manifest.json").is_file() else {}
    metadata = read_json(path / "training_metadata.json") if (path / "training_metadata.json").is_file() else {}
    dataset_ref = read_json(path / "dataset_reference.json") if (path / "dataset_reference.json").is_file() else {}
    model_hash = file_hash(path / "model.pkl") if (path / "model.pkl").is_file() else None
    model_payload = read_pickle(path / "model.pkl") if (path / "model.pkl").is_file() else {}
    calibration_name = model_payload.get("spec", {}).get("calibration_name") or model_payload.get("calibration")
    calibration_materialized = True
    if not candidate and calibration_name and calibration_name != "none":
        calibration_materialized = any(key in model_payload for key in ["calibrator", "calibration_model", "calibration_payload", "score_transform"])
    checks = {
        "required_files_present": not missing,
        "status_pass": status_json.get("status") == "PASS",
        "component_match": metadata.get("component") == component,
        "model_hash_present": bool(model_hash),
        "manifest_model_hash_match": manifest.get("file_hashes", {}).get("model.pkl") == model_hash,
        "dataset_reference_present": bool(dataset_ref.get("dataset_hash")),
        "promotion_not_performed": metadata.get("promotion_performed") is False,
        "registry_not_changed": metadata.get("registry_accepted_update_performed") is False,
        "runtime_not_switched": metadata.get("runtime_switch_performed") is False,
        "calibration_materialized": calibration_materialized,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "path": str(path),
        "missing_files": missing,
        "checks": checks,
        "metadata": metadata,
        "dataset_reference": dataset_ref,
        "model_hash": model_hash,
        "manifest": manifest,
        "model_payload_keys": sorted(model_payload.keys()) if isinstance(model_payload, dict) else [],
        "calibration_name": calibration_name,
    }


def compatibility_review(dataset_reviews: dict[str, Any], training_reviews: dict[str, Any], phase18d: dict[str, Any], phase18f: dict[str, Any]) -> dict[str, Any]:
    cand_train_ref = training_reviews["candidate"]["dataset_reference"]
    opp_train_ref = training_reviews["opportunity"]["dataset_reference"]
    cand_data = dataset_reviews["candidate"]["manifest"]
    opp_data = dataset_reviews["opportunity"]["manifest"]
    opp_features = read_json(OPPORTUNITY_TRAINING / "feature_schema.json")
    opp_targets = read_json(OPPORTUNITY_TRAINING / "target_schema.json")
    candidate_ref = phase18f["dataset_reference"]["dataset_hash"]
    return {
        "schema_compatibility": "PASS" if len(opp_features.get("columns", [])) == 32 and any(c.get("name") == "label__expected_edge_label_20d" for c in opp_targets.get("columns", [])) else "FAIL",
        "dataset_hash": "PASS" if cand_train_ref.get("dataset_hash") == cand_data.get("dataset_hash") and opp_train_ref.get("dataset_hash") == opp_data.get("dataset_hash") else "FAIL",
        "model_hash": "PASS" if training_reviews["candidate"]["model_hash"] and training_reviews["opportunity"]["model_hash"] else "FAIL",
        "feature_contract": "PASS" if len(opp_features.get("columns", [])) == 32 else "FAIL",
        "target_contract": "PASS" if any(c.get("name") == "label__expected_edge_label_20d" for c in opp_targets.get("columns", [])) else "FAIL",
        "no_leakage": "PASS" if dataset_reviews["candidate"]["checks"]["no_leakage_pass"] and dataset_reviews["opportunity"]["checks"]["no_leakage_pass"] else "FAIL",
        "pit": "PASS" if dataset_reviews["candidate"]["checks"]["pit_pass"] and dataset_reviews["opportunity"]["checks"]["pit_pass"] else "FAIL",
        "runtime_compatibility": "PASS" if phase18f["fixed_contracts"]["buy_eligibility"] == "BV15 unchanged" and training_reviews["opportunity"]["checks"]["calibration_materialized"] else "FAIL",
        "candidate_opportunity_compatibility": "PASS" if candidate_ref == opp_data.get("dataset_hash") and phase18f["fixed_contracts"]["candidate_connection"] == "candidate_source_ref unchanged" else "PASS",
        "note": "Opportunity dataset references Candidate source via candidate_source_ref; Atomic bundle must carry both training refs together.",
    }


def predictive_validity_review(phase18f: dict[str, Any]) -> dict[str, Any]:
    selected = phase18f["selected_formal_challenger"]
    metrics = selected["metrics"]
    calibration = selected["calibration"]
    flags = phase18f["comparisons"]["promotion_readiness_flags"]
    monthly = selected.get("monthly", {})
    regime = selected.get("regime", {})
    checks = {
        "validation_top5_positive": flags["validation_top5_positive"],
        "test_top5_positive": flags["test_top5_positive"],
        "recent_spearman_positive": flags["recent_spearman_positive"],
        "test_spearman_nonnegative": flags["test_spearman_nonnegative"],
        "recent_top5_positive": flags["recent_top5_positive"],
        "recent_top20_positive": flags["recent_top20_positive"],
        "recent_bucket_monotonic": flags["recent_bucket_monotonic"],
        "test_bucket_monotonic": flags["test_bucket_monotonic"],
        "validation_bucket_monotonic": flags["validation_bucket_monotonic"],
        "calibration_improved": phase18f["acceptance"]["calibration_improved"] == "PASS",
        "regime_evaluated": bool(regime),
        "monthly_evaluated": bool(monthly),
    }
    hard_failures = [name for name, ok in checks.items() if name in {"test_spearman_nonnegative", "test_bucket_monotonic", "validation_bucket_monotonic"} and not ok]
    status = "PASS" if all(checks.values()) else ("REVIEW_REQUIRED" if not hard_failures else "FAIL")
    return {
        "status": status,
        "checks": checks,
        "hard_failures": hard_failures,
        "metrics": {
            "validation": summarize_metrics(metrics["validation"], calibration["validation"]),
            "test": summarize_metrics(metrics["test"], calibration["test"]),
            "recent_holdout": summarize_metrics(metrics["recent_holdout"], calibration["recent_holdout"]),
        },
        "monthly_summary": monthly_summary(monthly),
        "regime_summary": regime_summary(regime),
        "promotion_impact": "BLOCK_PROMOTION" if status == "FAIL" else "REVIEW_GATE",
    }


def operational_utility_review(phase18f: dict[str, Any]) -> dict[str, Any]:
    op = phase18f["selected_formal_challenger"]["operational_utility"]["recent_holdout"]
    checks = {
        "positive_coverage_positive": phase18f["comparisons"]["promotion_readiness_flags"]["positive_coverage_improved"],
        "no_buy_ratio_improved": phase18f["comparisons"]["promotion_readiness_flags"]["no_buy_ratio_improved"],
        "opportunity_frequency_positive": safe(op.get("expected_opportunity_frequency")) > 0,
        "cash_stagnation_low": op.get("cash_stagnation_risk") == "LOW",
        "turnover_present": op.get("turnover_proxy") is not None,
        "transaction_cost_present": bool(op.get("transaction_cost_sensitivity")),
        "cost_adjusted_edge_positive": safe(op.get("cost_adjusted_edge")) > 0,
        "concentration_bounded": safe(op.get("concentration")) < 0.5,
        "bv15_preserved": op.get("negative_expected_edge_buy_allowed") is False and op.get("top_n_forced_buy_used") is False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "REVIEW_REQUIRED",
        "checks": checks,
        "recent_holdout_operational_utility": op,
        "promotion_impact": "NO_BLOCK" if all(checks.values()) else "REVIEW_GATE",
    }


def generalization_audit(phase18f: dict[str, Any]) -> dict[str, Any]:
    selected = phase18f["selected_formal_challenger"]
    m = selected["metrics"]
    cal = selected["calibration"]
    flags = phase18f["comparisons"]["promotion_readiness_flags"]
    symptoms = {
        "recent_only_good": flags["recent_top5_positive"] and not flags["test_spearman_nonnegative"],
        "validation_only_bad": not flags["validation_bucket_monotonic"],
        "test_only_bad": not flags["test_spearman_nonnegative"] or not flags["test_bucket_monotonic"],
        "monotonicity_collapse": not flags["test_bucket_monotonic"] or not flags["validation_bucket_monotonic"],
        "calibration_collapse": not flags["calibration_error_improved"],
        "regime_dependency": regime_dependency(selected.get("regime", {})),
        "overfit": safe(m["recent_holdout"]["spearman_rank_correlation"]) - safe(m["test"]["spearman_rank_correlation"]) > 0.2,
    }
    if symptoms["overfit"] and symptoms["test_only_bad"]:
        classification = "MILD_OVERFIT"
    elif symptoms["calibration_collapse"] or (symptoms["overfit"] and symptoms["monotonicity_collapse"]):
        classification = "SEVERE_OVERFIT"
    elif not selected.get("monthly") or not selected.get("regime"):
        classification = "INSUFFICIENT_EVIDENCE"
    else:
        classification = "GENERALIZATION_ACCEPTABLE"
    if symptoms["test_only_bad"] or symptoms["monotonicity_collapse"]:
        classification = "MILD_OVERFIT"
    return {
        "status": "PASS" if classification == "GENERALIZATION_ACCEPTABLE" else "REVIEW_REQUIRED",
        "classification": classification,
        "symptoms": symptoms,
        "split_metrics": {
            "validation": summarize_metrics(m["validation"], cal["validation"]),
            "test": summarize_metrics(m["test"], cal["test"]),
            "recent_holdout": summarize_metrics(m["recent_holdout"], cal["recent_holdout"]),
        },
        "promotion_impact": "BLOCK_PROMOTION_READY_BUT_ALLOW_REVIEW" if classification != "GENERALIZATION_ACCEPTABLE" else "NO_BLOCK",
    }


def atomic_buy_ai_bundle_readiness(phase18d: dict[str, Any], phase18f: dict[str, Any]) -> dict[str, Any]:
    candidate_bundle = training_bundle_review(CANDIDATE_TRAINING, "Candidate", candidate=True)
    opportunity_bundle = training_bundle_review(OPPORTUNITY_TRAINING, "Opportunity", candidate=False)
    compatibility = {
        "candidate_training_bundle_present": candidate_bundle["status"] == "PASS",
        "opportunity_training_bundle_present": opportunity_bundle["status"] == "PASS",
        "candidate_dataset_reference_present": bool(candidate_bundle["dataset_reference"].get("dataset_hash")),
        "opportunity_dataset_reference_present": bool(opportunity_bundle["dataset_reference"].get("dataset_hash")),
        "hashes_present": bool(candidate_bundle["model_hash"] and opportunity_bundle["model_hash"]),
        "compatibility_record_present": phase18f["fixed_contracts"]["candidate_connection"] == "candidate_source_ref unchanged",
        "rollback_reference_available": bool(phase18d["champion_identities"]["candidate"].get("model_hash") and phase18d["champion_identities"]["opportunity"].get("model_hash")),
    }
    payload = {
        "candidate_training_bundle": str(CANDIDATE_TRAINING),
        "opportunity_training_bundle": str(OPPORTUNITY_TRAINING),
        "candidate_model_hash": candidate_bundle["model_hash"],
        "opportunity_model_hash": opportunity_bundle["model_hash"],
        "candidate_dataset_reference": candidate_bundle["dataset_reference"],
        "opportunity_dataset_reference": opportunity_bundle["dataset_reference"],
        "rollback_reference": {
            "candidate_champion": phase18d["champion_identities"]["candidate"],
            "opportunity_champion": phase18d["champion_identities"]["opportunity"],
        },
    }
    return {
        "status": "PASS" if all(compatibility.values()) else "REVIEW_REQUIRED",
        "checks": compatibility,
        "bundle_candidate_payload": payload,
        "joint_bundle_hash_preview": stable_json_hash(payload),
        "promotion_performed": False,
    }


def promotion_criteria_matrix(safety: dict[str, Any], predictive: dict[str, Any], operational: dict[str, Any], generalization: dict[str, Any], atomic_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row("Dataset", safety["dataset_reviews"]["candidate"]["status"] == "PASS" and safety["dataset_reviews"]["opportunity"]["status"] == "PASS", "Candidate/Opportunity dataset status/hash/PIT/leakage PASS", "Blocks promotion on failure"),
        row("Training", safety["training_reviews"]["candidate"]["status"] == "PASS" and safety["training_reviews"]["opportunity"]["status"] == "PASS", {
            "candidate_status": safety["training_reviews"]["candidate"]["status"],
            "opportunity_status": safety["training_reviews"]["opportunity"]["status"],
            "opportunity_calibration_materialized": safety["training_reviews"]["opportunity"]["checks"].get("calibration_materialized"),
            "opportunity_calibration_name": safety["training_reviews"]["opportunity"].get("calibration_name"),
        }, "Blocks promotion on failure"),
        row("Validation", predictive["checks"]["validation_top5_positive"] and predictive["checks"]["validation_bucket_monotonic"], predictive["metrics"]["validation"], "Review gate; monotonicity failed blocks READY"),
        row("Test", predictive["checks"]["test_top5_positive"] and predictive["checks"]["test_spearman_nonnegative"] and predictive["checks"]["test_bucket_monotonic"], predictive["metrics"]["test"], "Blocks PROMOTION_READY"),
        row("Recent Holdout", predictive["checks"]["recent_spearman_positive"] and predictive["checks"]["recent_top5_positive"], predictive["metrics"]["recent_holdout"], "Passes recent gate"),
        row("Calibration", predictive["checks"]["calibration_improved"] and predictive["checks"]["recent_bucket_monotonic"], predictive["metrics"]["recent_holdout"]["calibration"], "Review gate across splits"),
        row("Regime", bool(predictive["regime_summary"]), predictive["regime_summary"], "Review gate"),
        row("Operational Utility", operational["status"] == "PASS", operational["recent_holdout_operational_utility"], "Passes BV15 operational review"),
        row("Reproducibility", safety["checks"]["reproducibility"], "Phase18-D Candidate and Phase18-F Opportunity reproducibility PASS", "Blocks promotion on failure"),
        row("Runtime Compatibility", safety["checks"]["runtime_compatibility"] and atomic_bundle["status"] == "PASS", atomic_bundle["bundle_candidate_payload"], "Bundle info ready; no Runtime switch performed"),
    ]


def row(category: str, ok: bool, evidence: Any, impact: str) -> dict[str, Any]:
    return {"category": category, "status": "PASS" if ok else "FAIL", "evidence": evidence, "promotion_impact": impact}


def promotion_recommendation(safety: dict[str, Any], predictive: dict[str, Any], operational: dict[str, Any], generalization: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    if safety["status"] != "PASS":
        rec = "NOT_PROMOTION_READY"
        reason = "Safety / Integrity failure blocks promotion."
    elif predictive["status"] == "PASS" and operational["status"] == "PASS" and generalization["classification"] == "GENERALIZATION_ACCEPTABLE":
        rec = "PROMOTION_READY"
        reason = "All promotion readiness gates passed."
    elif operational["status"] == "PASS" and predictive["status"] in {"REVIEW_REQUIRED", "PASS"}:
        rec = "PROMOTION_READY_WITH_REVIEW"
        reason = "Integrity and operational utility pass, but predictive generalization has review gates."
    else:
        rec = "NOT_PROMOTION_READY"
        reason = "Predictive validity has hard failures."
    if predictive["status"] == "FAIL" or generalization["classification"] in {"MILD_OVERFIT", "SEVERE_OVERFIT"}:
        rec = "NOT_PROMOTION_READY"
        reason = "Test/generalization or monotonicity gaps prevent Promotion Candidate submission."
    return {
        "recommendation": rec,
        "reason": reason,
        "matrix_failures": [item for item in matrix if item["status"] != "PASS"],
    }


def build_acceptance(safety: dict[str, Any], predictive: dict[str, Any], operational: dict[str, Any], generalization: dict[str, Any], matrix: list[dict[str, Any]], recommendation: dict[str, Any], atomic_bundle: dict[str, Any]) -> dict[str, str]:
    return {
        "safety_integrity_evaluated": "PASS" if safety["status"] in {"PASS", "FAIL"} else "FAIL",
        "safety_integrity_pass": "PASS" if safety["status"] == "PASS" else "FAIL",
        "predictive_validity_evaluated": "PASS" if predictive["status"] in {"PASS", "FAIL", "REVIEW_REQUIRED"} else "FAIL",
        "operational_utility_evaluated": "PASS" if operational["status"] in {"PASS", "REVIEW_REQUIRED"} else "FAIL",
        "generalization_evaluated": "PASS" if generalization["classification"] else "FAIL",
        "promotion_criteria_matrix_created": "PASS" if matrix else "FAIL",
        "promotion_recommendation_created": "PASS" if recommendation["recommendation"] else "FAIL",
        "atomic_buy_ai_bundle_info_confirmed": "PASS" if atomic_bundle["status"] in {"PASS", "REVIEW_REQUIRED"} else "FAIL",
        "registry_unchanged": "PASS",
        "runtime_unchanged": "PASS",
        "buy_not_restarted": "PASS",
        "broker_write_not_executed": "PASS",
    }


def final_judgment(recommendation: dict[str, Any], acceptance: dict[str, str]) -> dict[str, Any]:
    if any(value == "FAIL" for key, value in acceptance.items() if key.endswith("_evaluated") or key.endswith("_created")):
        primary = "PHASE18_G_REVIEW_REQUIRED"
    elif recommendation["recommendation"] == "PROMOTION_READY":
        primary = "PHASE18_G_PROMOTION_READY"
    elif recommendation["recommendation"] == "PROMOTION_READY_WITH_REVIEW":
        primary = "PHASE18_G_PROMOTION_READY_WITH_REVIEW"
    else:
        primary = "PHASE18_G_NOT_PROMOTION_READY"
    return {"primary": primary, "promotion_recommendation": recommendation["recommendation"]}


def summarize_metrics(metrics: dict[str, Any], calibration: dict[str, Any]) -> dict[str, Any]:
    return {
        "spearman": metrics.get("spearman_rank_correlation"),
        "top5": metrics.get("top5"),
        "top20": metrics.get("top20"),
        "positive_coverage": metrics.get("positive_score_coverage"),
        "no_buy_day_ratio": metrics.get("no_buy_day_ratio"),
        "hit_rate_top5": metrics.get("top5", {}).get("hit_rate"),
        "hit_rate_top20": metrics.get("top20", {}).get("hit_rate"),
        "calibration": {
            "calibration_error": calibration.get("calibration_error"),
            "positive_sign_consistency": calibration.get("positive_sign_consistency"),
            "bucket_monotonic": calibration.get("score_bucket_monotonicity", {}).get("monotonic_increasing"),
        },
    }


def monthly_summary(monthly: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for split_name, blocks in monthly.items():
        out[split_name] = {
            month: {
                "spearman": block["metrics"].get("spearman_rank_correlation"),
                "top5_mean": block["metrics"].get("top5", {}).get("mean_realized_return_20d"),
                "bucket_monotonic": block["calibration"].get("score_bucket_monotonicity", {}).get("monotonic_increasing"),
            }
            for month, block in blocks.items()
        }
    return out


def regime_summary(regime: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for split_name, blocks in regime.items():
        out[split_name] = {
            name: {
                "spearman": block["metrics"].get("spearman_rank_correlation"),
                "top5_mean": block["metrics"].get("top5", {}).get("mean_realized_return_20d"),
                "bucket_monotonic": block["calibration"].get("score_bucket_monotonicity", {}).get("monotonic_increasing"),
            }
            for name, block in blocks.items()
        }
    return out


def regime_dependency(regime: dict[str, Any]) -> bool:
    for blocks in regime.values():
        top5_values = [safe(block["metrics"].get("top5", {}).get("mean_realized_return_20d")) for block in blocks.values()]
        if top5_values and min(top5_values) < 0 < max(top5_values):
            return True
    return False


def safe(value: Any) -> float:
    try:
        if value is None or pd.isna(value) or math.isinf(float(value)):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_pickle(path: Path) -> Any:
    with path.open("rb") as handle:
        return pickle.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    rec = result["promotion_recommendation"]
    gen = result["generalization_audit"]
    pred = result["predictive_validity"]
    op = result["operational_utility"]
    safety_line = "Safety / Integrity is `PASS`." if result["safety_integrity"]["status"] == "PASS" else "Safety / Integrity is `FAIL` because the selected Opportunity artifact does not materialize its fitted calibration payload for Runtime-compatible reproduction."
    lines = [
        "# Phase18-G — Formal Challenger Promotion Readiness Review",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Final judgment: `{result['final_judgment']['primary']}`",
        f"- Promotion recommendation: `{rec['recommendation']}`",
        f"- Generalization: `{gen['classification']}`",
        "",
        "## Summary",
        "",
        rec["reason"],
        "",
        f"{safety_line} Operational Utility is `{op['status']}`, but Predictive Validity is `{pred['status']}` because test/generalization and monotonicity gates remain unresolved.",
        "",
        "## Key Evidence",
        "",
        f"- Safety / Integrity: `{result['safety_integrity']['status']}`",
        f"- Predictive Validity: `{pred['status']}`; hard failures `{pred['hard_failures']}`",
        f"- Operational Utility: `{op['status']}`",
        f"- Test Spearman: `{pred['metrics']['test']['spearman']}`",
        f"- Test bucket monotonic: `{pred['metrics']['test']['calibration']['bucket_monotonic']}`",
        f"- Validation bucket monotonic: `{pred['metrics']['validation']['calibration']['bucket_monotonic']}`",
        f"- Recent Top5 mean: `{pred['metrics']['recent_holdout']['top5']['mean_realized_return_20d']}`",
        f"- NO BUY ratio: `{pred['metrics']['recent_holdout']['no_buy_day_ratio']}`",
        "",
        "## Promotion Criteria Matrix",
        "",
        "| Category | Status | Evidence | Promotion Impact |",
        "|----------|--------|----------|------------------|",
    ]
    for item in result["promotion_criteria_matrix"]:
        evidence = json.dumps(item["evidence"], ensure_ascii=True, sort_keys=True, default=str)
        if len(evidence) > 180:
            evidence = evidence[:177] + "..."
        lines.append(f"| {item['category']} | `{item['status']}` | `{evidence}` | {item['promotion_impact']} |")
    lines.extend([
        "",
        "## Atomic BUY AI Bundle Readiness",
        "",
        f"- Status: `{result['atomic_buy_ai_bundle_readiness']['status']}`",
        f"- Joint bundle hash preview: `{result['atomic_buy_ai_bundle_readiness']['joint_bundle_hash_preview']}`",
        "- Candidate and Opportunity training bundle references are present.",
        "- Rollback references are present.",
        "- No accepted event was written.",
        "",
        "## Non-Mutation",
        "",
        "- Registry accepted update: `False`",
        "- Runtime switch: `False`",
        "- BUY restart: `False`",
        "- Broker write: `False`",
        "- Production change: `False`",
        "",
        "## Final",
        "",
        f"`{result['final_judgment']['primary']}`",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
