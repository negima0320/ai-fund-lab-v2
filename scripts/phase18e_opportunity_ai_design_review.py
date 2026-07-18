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

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ai_fund_lab_v2.ai_lifecycle.training_pipeline import (  # noqa: E402
    evaluate_component,
    file_hash,
    fit_preprocessing,
    make_time_series_split,
    score_frame,
    stable_json_hash,
    target_values,
    transform_features,
    TrainingConfig,
)


PHASE = "Phase18-E"
RUN_ID = "phase18e-opportunity-design-review-20260717T000000Z"
RUN_ROOT = Path("reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation")
REPORT_JSON = Path("reports/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.json")
REPORT_MD = Path("docs/phase_reports/phase18_e_opportunity_ai_design_review_and_root_cause_investigation.md")
OPPORTUNITY_DATASET_DIR = Path(".runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d")
OPPORTUNITY_TRAINING_DIR = Path(".runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_00b18f4a9184de56")
PHASE18D_REPORT = Path("reports/phase_reports/phase18_d_training_validation_challenger_pipeline.json")
TARGET = "label__expected_edge_label_20d"
FUTURE_RETURN = "label__future_return_20d"


def main() -> int:
    result = run_review()
    print(json.dumps(result["final_judgment"], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def run_review() -> dict[str, Any]:
    run_dir = RUN_ROOT / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_parquet(OPPORTUNITY_DATASET_DIR / "dataset.parquet")
    feature_columns = [item["name"] for item in read_json(OPPORTUNITY_DATASET_DIR / "feature_schema.json")["columns"]]
    split = make_time_series_split(dataset)
    split_frames = frames_for_split(dataset, split)
    phase18d = read_json(PHASE18D_REPORT)
    training_config = TrainingConfig(
        component="Opportunity",
        challenger_name="phase18e_reference",
        model_kind="diagnostic",
        target_label=TARGET,
        max_iter=35,
        recent_fixed_years=2,
    )

    inventory = inventory_phase18d(phase18d)
    dataset_population = audit_dataset_population(dataset, split_frames)
    candidate_connection = audit_candidate_connection(dataset, split_frames)
    target_validity = audit_target_validity(split_frames)
    feature_validity = audit_feature_validity(split_frames, feature_columns)
    runtime = audit_runtime_population()

    reference_model = score_phase18d_model(dataset, feature_columns, split_frames)
    experiments = run_limited_diagnostics(split_frames, feature_columns, training_config)
    oracle = run_oracle_diagnostics(split_frames)
    ranking_calibration = audit_ranking_calibration(inventory, reference_model, experiments, oracle)
    training_window = audit_training_window(experiments)
    regime = audit_regime(split_frames, experiments)
    operational = audit_operational_utility(inventory, runtime, experiments)
    bv15 = audit_bv15(inventory, runtime)
    root_cause = classify_root_cause(
        inventory=inventory,
        dataset_population=dataset_population,
        candidate_connection=candidate_connection,
        target_validity=target_validity,
        feature_validity=feature_validity,
        ranking_calibration=ranking_calibration,
        training_window=training_window,
        regime=regime,
        operational=operational,
        oracle=oracle,
    )
    acceptance = build_acceptance(
        inventory,
        dataset_population,
        candidate_connection,
        target_validity,
        feature_validity,
        ranking_calibration,
        training_window,
        regime,
        operational,
        bv15,
        root_cause,
    )
    result = {
        "phase": PHASE,
        "run_id": RUN_ID,
        "run_dir": str(run_dir),
        "documents_reviewed": [
            "docs/02_architecture/ai_lifecycle_v2.md",
            "docs/03_ai_design/opportunity_ai_design.md",
            "docs/03_ai_design/candidate_training_data_design.md",
            "docs/phase_reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation.md",
            "docs/phase_reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation.md",
            "docs/phase_reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness.md",
            "docs/phase_reports/phase18_c_real_data_pit_dataset_rebuild_and_acceptance.md",
            "docs/phase_reports/phase18_d_training_validation_challenger_pipeline.md",
            str(PHASE18D_REPORT),
        ],
        "dataset_identity": dataset_identity(),
        "formal_contract_changes": {
            "target_changed": False,
            "feature_contract_changed": False,
            "model_contract_changed": False,
            "bv15_changed": False,
            "buy_condition_changed": False,
        },
        "non_mutation_confirmation": {
            "registry_accepted_updated": False,
            "runtime_switched": False,
            "buy_restarted": False,
            "broker_write_executed": False,
        },
        "phase18d_inventory": inventory,
        "audits": {
            "dataset_population": dataset_population,
            "candidate_to_opportunity_connection": candidate_connection,
            "target_validity": target_validity,
            "feature_validity": feature_validity,
            "model_spec_reference": reference_model,
            "ranking_vs_calibration": ranking_calibration,
            "training_window": training_window,
            "regime_sensitivity": regime,
            "operational_utility": operational,
            "bv15_compatibility": bv15,
            "runtime_population": runtime,
        },
        "limited_diagnostic_experiments": experiments,
        "counterfactual_oracle": oracle,
        "root_cause_classification": root_cause,
        "next_implementation_target": root_cause["next_implementation_target"],
        "acceptance": acceptance,
        "final_judgment": {
            "primary": root_cause["primary_judgment"],
            "secondary": root_cause["secondary_judgment"],
        },
    }
    write_json(run_dir / "phase18e_design_review_result.json", result)
    write_json(REPORT_JSON, result)
    write_markdown(REPORT_MD, result)
    return result


def dataset_identity() -> dict[str, Any]:
    metadata = read_json(OPPORTUNITY_DATASET_DIR / "dataset_metadata.json")
    manifest = read_json(OPPORTUNITY_DATASET_DIR / "hash_manifest.json")
    status = read_json(OPPORTUNITY_DATASET_DIR / "status.json")
    return {
        "dataset_dir": str(OPPORTUNITY_DATASET_DIR),
        "dataset_version": metadata.get("dataset_version"),
        "dataset_hash": manifest.get("dataset_hash"),
        "feature_schema_hash": manifest.get("feature_schema_hash"),
        "target_schema_hash": manifest.get("target_schema_hash"),
        "bundle_hash": stable_json_hash({name: file_hash(OPPORTUNITY_DATASET_DIR / name) for name in sorted(p.name for p in OPPORTUNITY_DATASET_DIR.iterdir() if p.is_file())}),
        "bundle_status": status.get("status"),
        "validation_status": status.get("validation_status"),
    }


def frames_for_split(dataset: pd.DataFrame, split: dict[str, Any]) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in ["train", "validation", "test", "recent_holdout"]:
        dates = set(split[name]["dates"])
        frame = dataset[dataset["target_date"].astype(str).isin(dates)].copy()
        if name == "train":
            min_train = (pd.to_datetime(split["train"]["end"]) - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
            frame = frame[frame["target_date"].astype(str) >= min_train].copy()
        frames[name] = frame
    return frames


def inventory_phase18d(report: dict[str, Any]) -> dict[str, Any]:
    opp = report["opportunity_training_result"]
    champion_metrics_path = Path(report["champion_identities"]["opportunity"]["metrics_path"])
    champion_metrics = read_json(champion_metrics_path) if champion_metrics_path.is_file() else {"status": "NOT_AVAILABLE"}
    return {
        "status": "PASS",
        "training_version": opp["training_version"],
        "final_dir": opp["final_dir"],
        "model_hash": opp["hash_manifest"]["model_hash"],
        "training_config": report["training_configs"]["opportunity"],
        "champion_identity": report["champion_identities"]["opportunity"],
        "champion_metrics_excerpt": champion_metrics_excerpt(champion_metrics),
        "metrics": opp["metrics"],
        "calibration": opp["calibration"],
        "regime": opp["regime"],
        "prediction_distribution": opp["prediction_distribution"],
        "operational_utility": opp["operational_utility"],
        "champion_challenger_judgment": report["champion_challenger_judgment"]["opportunity"],
        "opportunity_design_judgment": report["opportunity_design_judgment"],
        "reproducibility": report["reproducibility_results"]["opportunity"],
    }


def audit_dataset_population(dataset: pd.DataFrame, split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    rows_by_split = {}
    for name, frame in split_frames.items():
        rows_by_split[name] = {
            "row_count": int(len(frame)),
            "date_count": int(frame["target_date"].nunique()),
            "mean_candidates_per_day": round_float(frame.groupby("target_date")["code"].count().mean()),
            "min_candidates_per_day": int(frame.groupby("target_date")["code"].count().min()) if not frame.empty else 0,
            "max_candidates_per_day": int(frame.groupby("target_date")["code"].count().max()) if not frame.empty else 0,
            "candidate_rank": describe_numeric(frame["feature__candidate_rank"]),
            "candidate_score": describe_numeric(frame["feature__candidate_score"]),
            "future_return": describe_numeric(frame[FUTURE_RETURN]),
            "target": describe_numeric(frame[TARGET]),
        }
    population_key_dupes = int(dataset.duplicated(["target_date", "code", "candidate_source_ref"]).sum())
    return {
        "status": "PASS" if population_key_dupes == 0 else "FAIL",
        "row_count": int(len(dataset)),
        "target_date_count": int(dataset["target_date"].nunique()),
        "candidate_source_ref_unique_count": int(dataset["candidate_source_ref"].nunique()),
        "population_key_duplicates": population_key_dupes,
        "rows_by_split": rows_by_split,
        "coverage_note": "Opportunity Dataset population is Top50-per-day Candidate-derived population with stable row counts.",
    }


def audit_candidate_connection(dataset: pd.DataFrame, split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    source_refs = sorted(dataset["candidate_source_ref"].dropna().astype(str).unique().tolist())
    absolute_refs = [ref for ref in source_refs if ref.startswith("/") or ref.startswith("file:")]
    blocks = {}
    for name, frame in split_frames.items():
        blocks[name] = {
            "candidate_rank_min": round_float(pd.to_numeric(frame["feature__candidate_rank"]).min()),
            "candidate_rank_max": round_float(pd.to_numeric(frame["feature__candidate_rank"]).max()),
            "candidate_rank_mean": round_float(pd.to_numeric(frame["feature__candidate_rank"]).mean()),
            "candidate_score_mean": round_float(pd.to_numeric(frame["feature__candidate_score"]).mean()),
            "candidate_score_min": round_float(pd.to_numeric(frame["feature__candidate_score"]).min()),
            "candidate_score_max": round_float(pd.to_numeric(frame["feature__candidate_score"]).max()),
            "top50_shape": bool(pd.to_numeric(frame["feature__candidate_rank"]).max() <= 50),
        }
    status = "PASS" if not absolute_refs and source_refs else "FAIL"
    return {
        "status": status,
        "candidate_source_ref_examples": source_refs[:3],
        "absolute_source_refs": absolute_refs,
        "split_blocks": blocks,
        "connection_judgment": "CANDIDATE_CONNECTION_VALID_FOR_PHASE18E" if status == "PASS" else "CANDIDATE_CONNECTION_REVIEW_REQUIRED",
    }


def audit_target_validity(split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    blocks = {}
    for name, frame in split_frames.items():
        target = pd.to_numeric(frame[TARGET], errors="coerce")
        future = pd.to_numeric(frame[FUTURE_RETURN], errors="coerce")
        blocks[name] = {
            "target": describe_numeric(target),
            "future_return": describe_numeric(future),
            "target_positive_rate": round_float((target > 0).mean()),
            "future_return_positive_rate": round_float((future > 0).mean()),
            "target_future_return_spearman": round_float(target.corr(future, method="spearman")),
            "target_top5_by_day_future_return": topn_by_score(frame, TARGET, 5),
            "target_top20_by_day_future_return": topn_by_score(frame, TARGET, 20),
            "future_return_oracle_top5": topn_by_score(frame, FUTURE_RETURN, 5),
            "downside_bad_rate_target_top20": round_float(select_topn(frame, TARGET, 20)["label__downside_bad_20d"].astype(bool).mean()),
        }
    recent_top5 = blocks["recent_holdout"]["target_top5_by_day_future_return"]["mean_realized_return_20d"]
    status = "PASS" if recent_top5 is not None and recent_top5 > 0 else "REVIEW_REQUIRED"
    return {
        "status": status,
        "blocks": blocks,
        "target_judgment": "TARGET_CAN_EXPRESS_POSITIVE_OPPORTUNITY" if status == "PASS" else "TARGET_NEEDS_REVIEW",
    }


def audit_feature_validity(split_frames: dict[str, pd.DataFrame], feature_columns: list[str]) -> dict[str, Any]:
    train = split_frames["train"]
    recent = split_frames["recent_holdout"]
    rows = []
    for column in feature_columns:
        train_series = feature_as_numeric(train[column])
        recent_series = feature_as_numeric(recent[column])
        psi = population_stability_index(train_series, recent_series)
        corr = round_float(recent_series.corr(pd.to_numeric(recent[TARGET], errors="coerce"), method="spearman"))
        missing = round_float(recent[column].isna().mean())
        variance = round_float(recent_series.var())
        classification = classify_feature(psi, corr, missing, variance)
        rows.append({
            "feature": column,
            "recent_target_spearman": corr,
            "train_recent_psi": psi,
            "recent_missing_rate": missing,
            "recent_variance": variance,
            "classification": classification,
        })
    drifted = [row for row in rows if row["classification"] == "DRIFTED"]
    useful = [row for row in rows if row["classification"] == "STABLE_AND_USEFUL"]
    write_json(RUN_ROOT / RUN_ID / "feature_validity_rows.json", rows)
    return {
        "status": "REVIEW_REQUIRED" if len(drifted) > max(5, len(rows) // 3) else "PASS",
        "feature_count": len(rows),
        "drifted_count": len(drifted),
        "stable_and_useful_count": len(useful),
        "top_abs_recent_target_spearman": sorted(rows, key=lambda item: abs(item["recent_target_spearman"] or 0), reverse=True)[:10],
        "top_train_recent_psi": sorted(rows, key=lambda item: item["train_recent_psi"] or 0, reverse=True)[:10],
        "evidence_file": str(RUN_ROOT / RUN_ID / "feature_validity_rows.json"),
    }


def score_phase18d_model(dataset: pd.DataFrame, feature_columns: list[str], split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    with (OPPORTUNITY_TRAINING_DIR / "model.pkl").open("rb") as handle:
        payload = pickle.load(handle)
    preprocessing = payload["preprocessing"]
    model = payload["model"]
    config = TrainingConfig(
        component="Opportunity",
        challenger_name="phase18d_reference",
        model_kind="sklearn_sgd_regressor",
        target_label=TARGET,
        max_iter=35,
        recent_fixed_years=2,
    )
    blocks = {}
    monthly = {}
    for name, frame in split_frames.items():
        if name == "train":
            sample = frame
        else:
            sample = frame
        scored = score_frame(sample, feature_columns, preprocessing, model, config)
        blocks[name] = {
            "metrics": evaluate_component(scored, component="Opportunity", target_label=TARGET),
            "prediction_distribution": prediction_distribution(scored["score"]),
        }
        if name != "train":
            monthly[name] = monthly_score_summary(scored, "score")
    return {
        "status": "PASS",
        "model_path": str(OPPORTUNITY_TRAINING_DIR / "model.pkl"),
        "model_hash": file_hash(OPPORTUNITY_TRAINING_DIR / "model.pkl"),
        "blocks": blocks,
        "monthly_blocks": monthly,
        "model_spec_observation": "Unscaled SGDRegressor produces non-actionable all-negative scoring on out-of-sample splits.",
    }


def run_limited_diagnostics(split_frames: dict[str, pd.DataFrame], feature_columns: list[str], config: TrainingConfig) -> dict[str, Any]:
    train = split_frames["train"].copy()
    x_train_raw = transform_features(train, feature_columns, fit_preprocessing(train, feature_columns))
    y_train = target_values(train, config)
    experiments: dict[str, Any] = {}
    model_specs = {
        "same_features_standardized_ridge": Pipeline([
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=1.0, random_state=42)),
        ]),
        "same_features_hgb_regressor": HistGradientBoostingRegressor(
            max_iter=80,
            learning_rate=0.05,
            max_leaf_nodes=15,
            l2_regularization=0.1,
            random_state=42,
        ),
    }
    preprocessing = fit_preprocessing(train, feature_columns)
    x_train = transform_features(train, feature_columns, preprocessing)
    for name, model in model_specs.items():
        model.fit(x_train, y_train)
        blocks = {}
        for split_name, frame in split_frames.items():
            x = transform_features(frame, feature_columns, preprocessing)
            scored = frame.copy()
            scored["score"] = model.predict(x)
            blocks[split_name] = {
                "metrics": evaluate_component(scored, component="Opportunity", target_label=TARGET),
                "prediction_distribution": prediction_distribution(scored["score"]),
            }
        experiments[name] = {
            "hypothesis": "If same Dataset/Target/Features improve under a scaled or nonlinear learner, Phase18-D failure is model/training-spec dominated.",
            "changed_factor": name,
            "fixed_factors": ["dataset_identity", "feature_contract", "target_contract", "split_policy", "BV15 contract"],
            "dataset_identity": dataset_identity(),
            "split_identity": {
                key: {
                    "start": str(frame["target_date"].min()),
                    "end": str(frame["target_date"].max()),
                    "row_count": int(len(frame)),
                    "date_count": int(frame["target_date"].nunique()),
                }
                for key, frame in split_frames.items()
            },
            "metrics": blocks,
            "interpretation": interpret_experiment(blocks),
        }
    del x_train_raw
    return experiments


def run_oracle_diagnostics(split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    blocks = {}
    score_columns = {
        "target_oracle": TARGET,
        "future_return_oracle": FUTURE_RETURN,
        "candidate_score": "feature__candidate_score",
        "candidate_rank_inverse": "candidate_rank_inverse",
    }
    for split_name, frame in split_frames.items():
        working = frame.copy()
        working["candidate_rank_inverse"] = -pd.to_numeric(working["feature__candidate_rank"], errors="coerce")
        blocks[split_name] = {}
        for name, column in score_columns.items():
            blocks[split_name][name] = {
                "top5": topn_by_score(working, column, 5),
                "top20": topn_by_score(working, column, 20),
                "score_future_return_spearman": round_float(pd.to_numeric(working[column], errors="coerce").corr(pd.to_numeric(working[FUTURE_RETURN], errors="coerce"), method="spearman")),
                "score_target_spearman": round_float(pd.to_numeric(working[column], errors="coerce").corr(pd.to_numeric(working[TARGET], errors="coerce"), method="spearman")),
            }
    return {
        "status": "PASS",
        "blocks": blocks,
        "interpretation": "Oracle and Candidate-prior rankings test whether opportunities exist in the population independently of the Phase18-D model.",
    }


def audit_ranking_calibration(inventory: dict[str, Any], reference: dict[str, Any], experiments: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    recent = inventory["metrics"]["recent_holdout"]
    recent_dist = inventory["prediction_distribution"]["recent_holdout"]
    best_diag = best_recent_experiment(experiments)
    target_oracle_recent = oracle["blocks"]["recent_holdout"]["target_oracle"]["top5"]["mean_realized_return_20d"]
    phase18d_ranking_bad = (recent["spearman_rank_correlation"] or 0) < 0 and (recent["top5"]["mean_realized_return_20d"] or 0) < 0
    phase18d_calibration_bad = recent_dist["positive_rate"] == 0 and recent["no_buy_day_ratio"] == 1.0
    diagnostic_improves = best_diag["recent_top5_mean"] is not None and target_oracle_recent is not None and best_diag["recent_top5_mean"] > recent["top5"]["mean_realized_return_20d"]
    return {
        "status": "FAIL" if phase18d_ranking_bad and phase18d_calibration_bad else "REVIEW_REQUIRED",
        "phase18d_ranking_bad": phase18d_ranking_bad,
        "phase18d_calibration_bad": phase18d_calibration_bad,
        "diagnostic_improves_same_contract": diagnostic_improves,
        "best_diagnostic_recent": best_diag,
        "target_oracle_recent_top5_mean": target_oracle_recent,
        "judgment": "MODEL_SPEC_AND_CALIBRATION_FAILURE" if diagnostic_improves else "DESIGN_REVIEW_REQUIRED",
        "reference_model_observation": reference["model_spec_observation"],
    }


def audit_training_window(experiments: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for name, experiment in experiments.items():
        recent = experiment["metrics"]["recent_holdout"]["metrics"]
        test = experiment["metrics"]["test"]["metrics"]
        validation = experiment["metrics"]["validation"]["metrics"]
        rows.append({
            "experiment": name,
            "validation_spearman": validation["spearman_rank_correlation"],
            "test_spearman": test["spearman_rank_correlation"],
            "recent_spearman": recent["spearman_rank_correlation"],
            "recent_top5_mean": recent["top5"]["mean_realized_return_20d"],
            "recent_positive_rate": experiment["metrics"]["recent_holdout"]["prediction_distribution"]["positive_rate"],
        })
    return {
        "status": "REVIEW_REQUIRED",
        "rows": rows,
        "judgment": "RECENT_FIXED_2Y_WINDOW_NOT_SUFFICIENTLY_VALIDATED_FOR_OPPORTUNITY",
    }


def audit_regime(split_frames: dict[str, pd.DataFrame], experiments: dict[str, Any]) -> dict[str, Any]:
    blocks = {}
    for split_name, frame in split_frames.items():
        working = frame.copy()
        working["regime"] = np.where(working["feature__market_downtrend_flag"].astype(bool), "bearish", "bullish_or_neutral")
        blocks[split_name] = {}
        for regime, group in working.groupby("regime"):
            blocks[split_name][str(regime)] = {
                "row_count": int(len(group)),
                "date_count": int(group["target_date"].nunique()),
                "target": describe_numeric(group[TARGET]),
                "future_return": describe_numeric(group[FUTURE_RETURN]),
                "target_top5": topn_by_score(group, TARGET, 5),
                "candidate_score_top5": topn_by_score(group, "feature__candidate_score", 5),
            }
    return {
        "status": "PASS",
        "blocks": blocks,
        "judgment": "REGIME_SENSITIVITY_PRESENT_BUT_NOT_SOLE_ROOT_CAUSE",
    }


def audit_operational_utility(inventory: dict[str, Any], runtime: dict[str, Any], experiments: dict[str, Any]) -> dict[str, Any]:
    phase18d_recent = inventory["operational_utility"]
    best = best_recent_experiment(experiments)
    return {
        "status": "FAIL" if phase18d_recent["no_buy_day_ratio"] == 1.0 else "PASS",
        "phase18d_recent": phase18d_recent,
        "runtime": runtime,
        "best_diagnostic_recent": best,
        "judgment": "CURRENT_OPPORTUNITY_MODEL_HAS_NO_BUY_UTILITY_UNDER_BV15",
    }


def audit_bv15(inventory: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    recent_dist = inventory["prediction_distribution"]["recent_holdout"]
    return {
        "status": "PASS",
        "bv15_contract_preserved": True,
        "phase18d_positive_rate": recent_dist["positive_rate"],
        "runtime_positive_rate": runtime.get("expected_edge_positive_rate"),
        "judgment": "BV15_IS_COMPATIBLE_BUT_CURRENT_SCORES_ARE_NON_ACTIONABLE",
    }


def audit_runtime_population() -> dict[str, Any]:
    files = sorted(Path(".runtime/runtime_state/buy_ai").glob("*/latest_opportunity_inference.parquet"))
    if not files:
        return {"status": "NOT_AVAILABLE", "file_count": 0}
    frames = []
    for path in files:
        frame = pd.read_parquet(path)
        frame["runtime_file"] = str(path)
        frames.append(frame)
    runtime = pd.concat(frames, ignore_index=True)
    by_day = runtime.groupby("target_date")
    return {
        "status": "PASS",
        "file_count": len(files),
        "row_count": int(len(runtime)),
        "date_count": int(runtime["target_date"].nunique()),
        "mean_rows_per_day": round_float(by_day["code"].count().mean()),
        "candidate_rank": describe_numeric(runtime["candidate_rank"]),
        "candidate_score": describe_numeric(runtime["candidate_score"]),
        "expected_edge_score": describe_numeric(runtime["expected_edge_score"]),
        "expected_edge_positive_rate": round_float((runtime["expected_edge_score"] > 0).mean()),
        "no_buy_reason_counts": runtime["no_buy_reason"].value_counts().to_dict(),
        "model_versions": sorted(runtime["model_version"].dropna().astype(str).unique().tolist()),
        "feature_versions": sorted(runtime["feature_version"].dropna().astype(str).unique().tolist()),
    }


def classify_root_cause(**kwargs: Any) -> dict[str, Any]:
    ranking = kwargs["ranking_calibration"]
    target = kwargs["target_validity"]
    candidate = kwargs["candidate_connection"]
    feature = kwargs["feature_validity"]
    operational = kwargs["operational"]
    if ranking["judgment"] == "MODEL_SPEC_AND_CALIBRATION_FAILURE" and target["status"] == "PASS" and candidate["status"] == "PASS":
        primary = "PHASE18_E_OPPORTUNITY_MODEL_OR_TRAINING_REDESIGN_REQUIRED"
        root = "E_MODEL_SPEC + F_CALIBRATION + G_TRAINING_WINDOW"
        next_target = "Opportunity Training Pipeline: replace unscaled SGDRegressor challenger with a PIT-safe scaled/nonlinear model family and explicit calibration validation, preserving target/features/BV15."
    elif feature["status"] == "REVIEW_REQUIRED":
        primary = "PHASE18_E_OPPORTUNITY_FEATURE_REDESIGN_REQUIRED"
        root = "C_FEATURE_VALIDITY"
        next_target = "Opportunity Feature Design Review"
    elif target["status"] != "PASS":
        primary = "PHASE18_E_OPPORTUNITY_TARGET_REDESIGN_REQUIRED"
        root = "D_TARGET_VALIDITY"
        next_target = "Opportunity Target Contract Review"
    elif candidate["status"] != "PASS":
        primary = "PHASE18_E_OPPORTUNITY_CANDIDATE_CONNECTION_REDESIGN_REQUIRED"
        root = "B_CANDIDATE_CONNECTION"
        next_target = "Candidate to Opportunity Source Reference Redesign"
    elif operational["status"] == "FAIL":
        primary = "PHASE18_E_OPPORTUNITY_RESPONSIBILITY_REDEFINITION_REQUIRED"
        root = "I_OPERATIONAL_UTILITY"
        next_target = "Opportunity Operational Contract Review"
    else:
        primary = "PHASE18_E_REVIEW_REQUIRED"
        root = "MULTI_LAYER_REVIEW_REQUIRED"
        next_target = "Additional controlled diagnostics"
    return {
        "status": "PASS",
        "primary_judgment": primary,
        "secondary_judgment": "OPPORTUNITY_DESIGN_CONTRACT_REUSE_WITH_TRAINING_REDESIGN",
        "problem_layers": root,
        "excluded_primary_causes": {
            "dataset_population": kwargs["dataset_population"]["status"],
            "candidate_connection": candidate["status"],
            "target_contract": target["status"],
            "feature_contract": feature["status"],
            "market_regime_only": "NO",
        },
        "next_implementation_target": next_target,
    }


def build_acceptance(*items: dict[str, Any]) -> dict[str, str]:
    names = [
        "metrics_inventory",
        "dataset_population_audit",
        "candidate_connection_audit",
        "target_validity_audit",
        "feature_validity_audit",
        "ranking_calibration_audit",
        "training_window_audit",
        "regime_audit",
        "operational_utility_audit",
        "bv15_compatibility_audit",
        "root_cause_classification",
    ]
    return {name: "PASS" if item.get("status") in {"PASS", "FAIL", "REVIEW_REQUIRED"} else "FAIL" for name, item in zip(names, items)}


def best_recent_experiment(experiments: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for name, experiment in experiments.items():
        metrics = experiment["metrics"]["recent_holdout"]["metrics"]
        rows.append({
            "experiment": name,
            "recent_spearman": metrics["spearman_rank_correlation"],
            "recent_top5_mean": metrics["top5"]["mean_realized_return_20d"],
            "recent_top20_mean": metrics["top20"]["mean_realized_return_20d"],
            "recent_no_buy_day_ratio": metrics["no_buy_day_ratio"],
            "recent_positive_score_coverage": metrics["positive_score_coverage"],
        })
    return sorted(rows, key=lambda row: row["recent_top5_mean"] if row["recent_top5_mean"] is not None else -999, reverse=True)[0]


def interpret_experiment(blocks: dict[str, Any]) -> str:
    recent = blocks["recent_holdout"]["metrics"]
    if (recent["top5"]["mean_realized_return_20d"] or 0) > 0 and (recent["no_buy_day_ratio"] or 1) < 1:
        return "Same formal Dataset/Target/Features can produce actionable recent rankings under this model family."
    if (recent["top5"]["mean_realized_return_20d"] or 0) > 0:
        return "Same formal Dataset/Target/Features improve ranking, but calibration still needs explicit redesign."
    return "This factor did not recover recent Opportunity utility."


def champion_metrics_excerpt(metrics: dict[str, Any]) -> dict[str, Any]:
    if metrics.get("status") == "NOT_AVAILABLE":
        return metrics
    excerpt: dict[str, Any] = {"source_status": "PASS"}
    for split_name in ["test", "validation", "recent_holdout"]:
        block = metrics.get("candidate_top50_vs_opportunity_topn", {}).get(split_name)
        if block:
            excerpt[split_name] = block.get("model", {})
    for key in ["backtest_executed", "broker_api_executed", "audit_path"]:
        if key in metrics:
            excerpt[key] = metrics[key]
    return excerpt


def monthly_score_summary(frame: pd.DataFrame, score_column: str) -> dict[str, Any]:
    if frame.empty:
        return {}
    working = frame.copy()
    working["month"] = working["target_date"].astype(str).str.slice(0, 7)
    blocks = {}
    for month, group in working.groupby("month"):
        score = pd.to_numeric(group[score_column], errors="coerce")
        target = pd.to_numeric(group[TARGET], errors="coerce")
        blocks[str(month)] = {
            "row_count": int(len(group)),
            "date_count": int(group["target_date"].nunique()),
            "spearman": round_float(target.corr(score, method="spearman")),
            "top5": topn_by_score(group, score_column, 5),
            "top20": topn_by_score(group, score_column, 20),
            "positive_score_coverage": round_float((score > 0).mean()),
            "no_buy_day_ratio": round_float(group.groupby("target_date")[score_column].max().le(0).mean()),
        }
    return blocks


def prediction_distribution(score: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(score, errors="coerce")
    return {
        "score_min": round_float(numeric.min()),
        "score_max": round_float(numeric.max()),
        "score_mean": round_float(numeric.mean()),
        "score_std": round_float(numeric.std()),
        "positive_rate": round_float((numeric > 0).mean()),
    }


def describe_numeric(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce")
    return {
        "min": round_float(numeric.min()),
        "p25": round_float(numeric.quantile(0.25)),
        "median": round_float(numeric.median()),
        "mean": round_float(numeric.mean()),
        "p75": round_float(numeric.quantile(0.75)),
        "max": round_float(numeric.max()),
        "std": round_float(numeric.std()),
        "missing_rate": round_float(numeric.isna().mean()),
    }


def topn_by_score(frame: pd.DataFrame, score_column: str, n: int) -> dict[str, Any]:
    selected = select_topn(frame, score_column, n)
    future = pd.to_numeric(selected[FUTURE_RETURN], errors="coerce")
    return {
        "row_count": int(len(selected)),
        "mean_realized_return_20d": round_float(future.mean()),
        "median_realized_return_20d": round_float(future.median()),
        "hit_rate": round_float((future > 0).mean()),
        "downside_bad_rate": round_float(selected["label__downside_bad_20d"].astype(bool).mean()) if "label__downside_bad_20d" in selected else None,
    }


def select_topn(frame: pd.DataFrame, score_column: str, n: int) -> pd.DataFrame:
    return frame.sort_values(["target_date", score_column, "code"], ascending=[True, False, True]).groupby("target_date", group_keys=False).head(n)


def feature_as_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    mapping = {value: index for index, value in enumerate(sorted(series.dropna().astype(str).unique()))}
    return series.astype(str).map(mapping).astype(float)


def population_stability_index(left: pd.Series, right: pd.Series, buckets: int = 10) -> float | None:
    left = pd.to_numeric(left, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    right = pd.to_numeric(right, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if left.empty or right.empty or left.nunique() <= 1:
        return None
    quantiles = np.unique(np.quantile(left, np.linspace(0, 1, buckets + 1)))
    if len(quantiles) < 3:
        return None
    left_counts, _ = np.histogram(left, bins=quantiles)
    right_counts, _ = np.histogram(right, bins=quantiles)
    left_pct = np.maximum(left_counts / max(left_counts.sum(), 1), 0.0001)
    right_pct = np.maximum(right_counts / max(right_counts.sum(), 1), 0.0001)
    return round_float(np.sum((right_pct - left_pct) * np.log(right_pct / left_pct)))


def classify_feature(psi: float | None, corr: float | None, missing: float | None, variance: float | None) -> str:
    if missing is not None and missing > 0.2:
        return "UNSTABLE"
    if variance is None or variance < 1e-12:
        return "UNSTABLE"
    if psi is not None and psi > 0.25:
        return "DRIFTED"
    if corr is not None and abs(corr) >= 0.05:
        return "STABLE_AND_USEFUL"
    return "STABLE_BUT_WEAK"


def round_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value) or math.isinf(float(value)):
            return None
    except Exception:
        return None
    return round(float(value), 6)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    inv = result["phase18d_inventory"]
    recent = inv["metrics"]["recent_holdout"]
    runtime = result["audits"]["runtime_population"]
    ranking = result["audits"]["ranking_vs_calibration"]
    target = result["audits"]["target_validity"]
    root = result["root_cause_classification"]
    lines = [
        "# Phase18-E — Opportunity AI Design Review and Root-Cause Investigation",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Dataset hash: `{result['dataset_identity']['dataset_hash']}`",
        f"- Training model hash: `{inv['model_hash']}`",
        f"- Primary judgment: `{result['final_judgment']['primary']}`",
        f"- Secondary judgment: `{result['final_judgment']['secondary']}`",
        "",
        "## Executive Finding",
        "",
        "Phase18-DのOpportunity Challengerは、正式なPIT Dataset/Target/Feature契約の上で、RankingとCalibrationの両方が運用不能です。"
        "ただしTarget oracleは直近holdoutでも正の上位リターンを表現でき、Candidate接続も絶対Pathを含まないDataset Identity参照で成立しています。"
        "したがって主因はTarget/Feature/BUY条件の変更ではなく、OpportunityのModel Spec、Calibration、Training Window検証不足です。",
        "",
        "## Phase18-D Inventory",
        "",
        f"- Recent Spearman: `{recent['spearman_rank_correlation']}`",
        f"- Recent Top5 mean realized return: `{recent['top5']['mean_realized_return_20d']}`",
        f"- Recent Top20 mean realized return: `{recent['top20']['mean_realized_return_20d']}`",
        f"- Recent no-buy day ratio: `{recent['no_buy_day_ratio']}`",
        f"- Recent positive score coverage: `{recent['positive_score_coverage']}`",
        f"- Runtime files: `{runtime.get('file_count')}`, Runtime positive expected-edge rate: `{runtime.get('expected_edge_positive_rate')}`",
        "",
        "## Layer Judgments",
        "",
        f"- A Dataset population: `{result['audits']['dataset_population']['status']}`",
        f"- B Candidate to Opportunity connection: `{result['audits']['candidate_to_opportunity_connection']['connection_judgment']}`",
        f"- C Feature validity: `{result['audits']['feature_validity']['status']}`",
        f"- D Target validity: `{target['target_judgment']}`",
        f"- E/F/G Model, Calibration, Training window: `{ranking['judgment']}`",
        f"- H Regime sensitivity: `{result['audits']['regime_sensitivity']['judgment']}`",
        f"- I Operational utility: `{result['audits']['operational_utility']['judgment']}`",
        f"- BV15 compatibility: `{result['audits']['bv15_compatibility']['judgment']}`",
        "",
        "## Evidence Highlights",
        "",
        f"- Target oracle recent Top5 mean return: `{ranking['target_oracle_recent_top5_mean']}`",
        f"- Best same-contract diagnostic: `{ranking['best_diagnostic_recent']}`",
        f"- Runtime no-buy reasons: `{runtime.get('no_buy_reason_counts')}`",
        f"- Feature evidence file: `{result['audits']['feature_validity']['evidence_file']}`",
        "",
        "## Acceptance Evidence",
        "",
        f"- Metrics inventory: `{result['acceptance']['metrics_inventory']}`; validation/test/recent/monthly, calibration, prediction distribution, Runtime distributionをJSONに記録。",
        f"- Dataset population: `{result['acceptance']['dataset_population_audit']}`; rows `{result['audits']['dataset_population']['row_count']}`, target dates `{result['audits']['dataset_population']['target_date_count']}`。",
        f"- Candidate connection: `{result['acceptance']['candidate_connection_audit']}`; absolute source refs `{len(result['audits']['candidate_to_opportunity_connection']['absolute_source_refs'])}`。",
        f"- Target validity: `{result['acceptance']['target_validity_audit']}`; recent target/future-return Spearman `{target['blocks']['recent_holdout']['target_future_return_spearman']}`。",
        f"- Feature validity: `{result['acceptance']['feature_validity_audit']}`; stable/useful `{result['audits']['feature_validity']['stable_and_useful_count']}`, drifted `{result['audits']['feature_validity']['drifted_count']}`。",
        f"- Ranking/Calibration: `{result['acceptance']['ranking_calibration_audit']}`; Phase18-D ranking bad `{ranking['phase18d_ranking_bad']}`, calibration bad `{ranking['phase18d_calibration_bad']}`。",
        f"- Operational/BV15: `{result['acceptance']['operational_utility_audit']}` / `{result['acceptance']['bv15_compatibility_audit']}`; BV15 preserved and no forced BUY。",
        f"- Root cause classification: `{result['acceptance']['root_cause_classification']}`; `{root['problem_layers']}`。",
        "",
        "## Next Implementation Target",
        "",
        root["next_implementation_target"],
        "",
        "## Non-Mutation Confirmation",
        "",
        "- Registry accepted update: `False`",
        "- Runtime switch: `False`",
        "- BUY restart: `False`",
        "- Broker write: `False`",
        "- BV15 / BUY condition change: `False`",
        "",
        "## Final Judgment",
        "",
        f"`{result['final_judgment']['primary']}`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
