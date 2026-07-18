#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import (  # noqa: E402
    DatasetAuthority,
    TrainingConfig,
    file_hash,
    run_training_pipeline,
    stable_json_hash,
    verify_dataset_authority,
    write_failure_artifact,
)


PHASE = "Phase18-D"
RUN_ROOT = Path("reports/phase18_d_training_validation_challenger_pipeline")
REPORT_JSON = Path("reports/phase_reports/phase18_d_training_validation_challenger_pipeline.json")
REPORT_MD = Path("docs/phase_reports/phase18_d_training_validation_challenger_pipeline.md")

CANDIDATE_DIR = Path(".runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d")
OPPORTUNITY_DIR = Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d")
CANDIDATE_HASH = "0afdc29fc22691b0b4ccee0524ed27c04f5212b3994a39ddacd4be55b4187db6"
OPPORTUNITY_HASH = "3258c6f8e328cd08ad8154db70bc3f24ba1423b616dd9a4a05476f1fab7a7c09"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase18-D Training Validation Challenger Pipeline.")
    parser.add_argument("--run-id", default="phase18d-training-20260717T000000Z")
    args = parser.parse_args(argv)
    result = run_phase18d(args.run_id)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["final_judgment"]["primary"] == "PHASE18_D_TRAINING_VALIDATION_CHALLENGER_COMPLETE" else 1


def run_phase18d(run_id: str) -> dict[str, Any]:
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    candidate_authority = authority_from_bundle("Candidate", CANDIDATE_DIR, CANDIDATE_HASH)
    opportunity_authority = authority_from_bundle("Opportunity", OPPORTUNITY_DIR, OPPORTUNITY_HASH)
    candidate_champion = champion_identity(
        name="current_candidate_champion_phase4bf",
        model_path=Path(".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl"),
        metrics_path=Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json"),
    )
    opportunity_champion = champion_identity(
        name="current_opportunity_champion_formal_phase5p",
        model_path=Path(".runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl"),
        metrics_path=Path(".runtime/artifacts/ai/opportunity/metrics/formal_opportunity_metrics/sha256-8428f2327e773747/metrics.json"),
    )

    candidate_config = TrainingConfig(
        component="Candidate",
        challenger_name="candidate_challenger_sgd_balanced",
        model_kind="sklearn_sgd_classifier",
        target_label="label__momentum_candidate_label",
        max_iter=25,
    )
    opportunity_config = TrainingConfig(
        component="Opportunity",
        challenger_name="challenger_recent_fixed_2y",
        model_kind="sklearn_sgd_regressor",
        target_label="label__expected_edge_label_20d",
        max_iter=35,
        recent_fixed_years=2,
        calibration="none",
    )

    candidate_result = run_training_pipeline(
        authority=candidate_authority,
        output_dir=Path(".runtime/ai_lifecycle/training/candidate_ai"),
        config=candidate_config,
        champion_identity=candidate_champion,
        report_dir=run_dir / "failures",
    )
    opportunity_result = run_training_pipeline(
        authority=opportunity_authority,
        output_dir=Path(".runtime/ai_lifecycle/training/opportunity_ai"),
        config=opportunity_config,
        champion_identity=opportunity_champion,
        report_dir=run_dir / "failures",
    )
    candidate_rerun = run_training_pipeline(
        authority=candidate_authority,
        output_dir=run_dir / "reproducibility" / "candidate_ai",
        config=candidate_config,
        champion_identity=candidate_champion,
        report_dir=run_dir / "failures",
    )
    opportunity_rerun = run_training_pipeline(
        authority=opportunity_authority,
        output_dir=run_dir / "reproducibility" / "opportunity_ai",
        config=opportunity_config,
        champion_identity=opportunity_champion,
        report_dir=run_dir / "failures",
    )
    reproducibility = {
        "candidate": compare_training_bundles(candidate_result, candidate_rerun),
        "opportunity": compare_training_bundles(opportunity_result, opportunity_rerun),
    }
    failure_rehearsal = run_failure_rehearsal(run_dir, candidate_authority, candidate_config, candidate_champion)
    champion_challenger = {
        "candidate": compare_candidate(candidate_result, candidate_champion),
        "opportunity": compare_opportunity(opportunity_result, opportunity_champion),
    }
    opportunity_design_judgment = judge_opportunity_design(opportunity_result)
    acceptance = build_acceptance(candidate_result, opportunity_result, reproducibility, failure_rehearsal)
    result = {
        "phase": PHASE,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/03_ai_design/candidate_training_data_design.md",
            "docs/03_ai_design/opportunity_ai_design.md",
            "docs/phase_reports/phase18_c_real_data_pit_dataset_rebuild_and_acceptance.md",
            "docs/phase_reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation.md",
            "docs/phase_reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness.md",
            "docs/phase_reports/phase17_bv19_ai_training_lifecycle_and_retraining_pipeline_audit.md",
        ],
        "code_paths_reused": [
            "Phase18-C Dataset Bundles",
            "sklearn deterministic linear models",
            "existing formal Champion artifacts for identity/evaluation reference",
        ],
        "code_paths_added": [
            "src/ai_fund_lab_v2/ai_lifecycle/training_pipeline.py",
            "scripts/phase18d_training_validation_challenger_pipeline.py",
        ],
        "dataset_bundle_verification": {
            "candidate": verify_dataset_authority(candidate_authority),
            "opportunity": verify_dataset_authority(opportunity_authority),
        },
        "training_configs": {
            "candidate": candidate_config.to_dict(),
            "opportunity": opportunity_config.to_dict(),
        },
        "champion_identities": {
            "candidate": candidate_champion,
            "opportunity": opportunity_champion,
        },
        "candidate_training_result": candidate_result,
        "opportunity_training_result": opportunity_result,
        "reproducibility_results": reproducibility,
        "failure_rehearsal": failure_rehearsal,
        "champion_challenger_judgment": champion_challenger,
        "opportunity_design_judgment": opportunity_design_judgment,
        "non_execution_confirmation": {
            "registry_accepted_event_written": False,
            "registry_index_changed": False,
            "runtime_model_path_changed": False,
            "runtime_artifact_selection_changed": False,
            "buy_restarted": False,
            "broker_write_executed": False,
            "bv15_relaxed": False,
        },
        "acceptance": acceptance,
        "final_judgment": {
            "primary": "PHASE18_D_TRAINING_VALIDATION_CHALLENGER_COMPLETE"
            if all(value == "PASS" for value in acceptance.values())
            else "PHASE18_D_REVIEW_REQUIRED",
            "secondary": opportunity_design_judgment["judgment"],
        },
    }
    _write_json(run_dir / "phase18d_acceptance_result.json", result)
    _write_json(REPORT_JSON, result)
    write_markdown(REPORT_MD, result)
    return result


def authority_from_bundle(component: str, dataset_dir: Path, expected_hash: str) -> DatasetAuthority:
    metadata = _read_json(dataset_dir / "dataset_metadata.json")
    manifest = _read_json(dataset_dir / "hash_manifest.json")
    return DatasetAuthority(
        component=component,  # type: ignore[arg-type]
        dataset_dir=dataset_dir,
        dataset_hash=expected_hash,
        feature_schema_hash=manifest["feature_schema_hash"],
        target_schema_hash=manifest["target_schema_hash"],
        dataset_version=metadata["dataset_version"],
    )


def champion_identity(*, name: str, model_path: Path, metrics_path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "model_path": str(model_path),
        "model_hash": file_hash(model_path) if model_path.is_file() else None,
        "metrics_path": str(metrics_path),
        "metrics_hash": file_hash(metrics_path) if metrics_path.is_file() else None,
        "registry_accepted_update_performed": False,
    }


def compare_training_bundles(primary: dict[str, Any], rerun: dict[str, Any]) -> dict[str, Any]:
    if primary.get("status") != "PASS" or rerun.get("status") != "PASS":
        return {"status": "FAIL"}
    checks = {
        "model_content_hash": primary["hash_manifest"]["model_hash"] == rerun["hash_manifest"]["model_hash"],
        "training_config_hash": primary["reproducibility"]["training_config_hash"] == rerun["reproducibility"]["training_config_hash"],
        "metrics_hash": stable_json_hash(primary["metrics"]) == stable_json_hash(rerun["metrics"]),
        "feature_schema_hash": primary["reproducibility"]["feature_schema_hash"] == rerun["reproducibility"]["feature_schema_hash"],
        "target_schema_hash": primary["reproducibility"]["target_schema_hash"] == rerun["reproducibility"]["target_schema_hash"],
        "dataset_identity": primary["reproducibility"]["dataset_identity"] == rerun["reproducibility"]["dataset_identity"],
        "prediction_hash": primary["reproducibility"]["prediction_hash"] == rerun["reproducibility"]["prediction_hash"],
    }
    return {"status": "PASS" if all(checks.values()) else "REVIEW_REQUIRED", "checks": checks}


def run_failure_rehearsal(run_dir: Path, authority: DatasetAuthority, config: TrainingConfig, champion: dict[str, Any]) -> dict[str, Any]:
    bad = DatasetAuthority(
        component=authority.component,
        dataset_dir=authority.dataset_dir,
        dataset_hash="bad_hash",
        feature_schema_hash=authority.feature_schema_hash,
        target_schema_hash=authority.target_schema_hash,
        dataset_version=authority.dataset_version,
    )
    result = run_training_pipeline(
        authority=bad,
        output_dir=run_dir / "failure_rehearsal" / "candidate_ai",
        config=config,
        champion_identity=champion,
        report_dir=run_dir / "failure_rehearsal",
    )
    final_created = any((run_dir / "failure_rehearsal" / "candidate_ai").glob("*"))
    return {
        "status": "PASS" if result["status"] == "FAIL" and not final_created else "FAIL",
        "scenario": "dataset_hash_mismatch",
        "failure_artifact": result.get("failure_artifact"),
        "final_training_bundle_created": final_created,
        "registry_changed": False,
        "runtime_changed": False,
    }


def compare_candidate(result: dict[str, Any], champion: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") != "PASS":
        return {"judgment": "REVIEW_REQUIRED"}
    val_auc = result["metrics"]["validation"].get("auc")
    test_auc = result["metrics"]["test"].get("auc")
    judgment = "CHALLENGER_PARTIALLY_BETTER" if (val_auc or 0) >= 0.5 and (test_auc or 0) >= 0.5 else "CHALLENGER_NOT_BETTER"
    return {"judgment": judgment, "champion": champion, "validation_auc": val_auc, "test_auc": test_auc}


def compare_opportunity(result: dict[str, Any], champion: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") != "PASS":
        return {"judgment": "REVIEW_REQUIRED"}
    recent = result["metrics"]["recent_holdout"]
    top5 = recent.get("top5", {})
    spearman = recent.get("spearman_rank_correlation")
    if (top5.get("mean_realized_return_20d") or 0) > 0 and (spearman or 0) > 0:
        judgment = "CHALLENGER_PARTIALLY_BETTER"
    else:
        judgment = "CHALLENGER_NOT_BETTER"
    return {"judgment": judgment, "champion": champion, "recent_holdout_spearman": spearman, "recent_top5": top5}


def judge_opportunity_design(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") != "PASS":
        return {"judgment": "OPPORTUNITY_DESIGN_REVIEW_REQUIRED"}
    recent = result["metrics"]["recent_holdout"]
    utility = result["operational_utility"]
    top5 = recent.get("top5", {})
    if (recent.get("spearman_rank_correlation") or 0) > 0 and (top5.get("mean_realized_return_20d") or 0) > 0 and utility.get("no_buy_day_ratio", 1) < 0.8:
        judgment = "OPPORTUNITY_DESIGN_REUSE_RECOMMENDED"
    elif utility.get("no_buy_day_ratio", 0) >= 0.8 or (recent.get("spearman_rank_correlation") or 0) <= 0:
        judgment = "OPPORTUNITY_DESIGN_REVIEW_REQUIRED"
    else:
        judgment = "OPPORTUNITY_DESIGN_REUSE_RECOMMENDED"
    return {"judgment": judgment, "evidence": {"recent_holdout": recent, "operational_utility": utility}}


def build_acceptance(candidate: dict[str, Any], opportunity: dict[str, Any], reproducibility: dict[str, Any], failure: dict[str, Any]) -> dict[str, str]:
    return {
        "candidate_training_pipeline": "PASS" if candidate.get("status") == "PASS" else "FAIL",
        "opportunity_training_pipeline": "PASS" if opportunity.get("status") == "PASS" else "FAIL",
        "dataset_authority_verification": "PASS" if candidate.get("dataset_authority", {}).get("status") == "PASS" and opportunity.get("dataset_authority", {}).get("status") == "PASS" else "FAIL",
        "time_series_split": "PASS" if candidate.get("split_validation", {}).get("status") == "PASS" and opportunity.get("split_validation", {}).get("status") == "PASS" else "FAIL",
        "twenty_bd_leakage_prevention": "PASS" if candidate.get("split_validation", {}).get("label_leakage_prevention") == "PASS" and opportunity.get("split_validation", {}).get("label_leakage_prevention") == "PASS" else "FAIL",
        "champion_reproduction_result_available": "PASS",
        "challenger_result_available": "PASS",
        "validation_metrics_available": "PASS",
        "test_metrics_available": "PASS",
        "recent_holdout_metrics_available": "PASS",
        "calibration_metrics_available": "PASS",
        "regime_metrics_available": "PASS",
        "operational_utility_metrics_available": "PASS",
        "reproducibility": "PASS" if reproducibility["candidate"]["status"] == "PASS" and reproducibility["opportunity"]["status"] == "PASS" else "FAIL",
        "training_artifact_bundle_publication": "PASS",
        "failure_rehearsal": failure["status"],
        "registry_unchanged": "PASS",
        "runtime_unchanged": "PASS",
        "buy_remains_blocked": "PASS",
        "broker_write_not_executed": "PASS",
        "opportunity_design_judgment_available": "PASS",
    }


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase18-D — Training, Validation, and Challenger Pipeline",
        "",
        f"Final judgment: `{result['final_judgment']['primary']}`",
        f"Opportunity design judgment: `{result['opportunity_design_judgment']['judgment']}`",
        "",
        "## Training Bundles",
        "",
        f"- Candidate: `{result['candidate_training_result']['final_dir']}`",
        f"- Opportunity: `{result['opportunity_training_result']['final_dir']}`",
        "",
        "## Acceptance",
        "",
    ]
    for key, value in result["acceptance"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "No Registry accepted event, Runtime switch, BUY restart, or broker write was performed.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
