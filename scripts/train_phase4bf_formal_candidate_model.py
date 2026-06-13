#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, average_precision_score, precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai.validation import is_forbidden_column  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-BF"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
PHASE4BE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")

READY_INPUT = "READY_FOR_FORMAL_LIGHTGBM_TRAINING"
READY = "READY_FOR_FORMAL_CANDIDATE_INFERENCE"
WEAK = "TRAINING_COMPLETE_WITH_WEAK_MODEL"
BLOCKED_DATASET = "BLOCKED_BY_DATASET"
BLOCKED_NO_POSITIVE = "BLOCKED_BY_NO_POSITIVE_LABEL"
BLOCKED_TRAINING = "BLOCKED_BY_MODEL_TRAINING"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_ARTIFACT = "BLOCKED_BY_MODEL_ARTIFACT"
BLOCKED_ALL_SAME = "BLOCKED_BY_ALL_SAME_SCORE"

TARGET_LABEL = "label__momentum_candidate_label"
MODEL_FILENAME = "phase4bf_formal_candidate_model.pkl"
MODEL_MANIFEST_FILENAME = "phase4bf_formal_candidate_model_manifest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Phase4-BF formal Candidate AI model.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--phase4be-summary", default=str(PHASE4BE_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = train_phase4bf_formal_candidate_model(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        phase4be_summary_path=Path(args.phase4be_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def train_phase4bf_formal_candidate_model(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    phase4be_summary_path: Path = PHASE4BE_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    be_summary = _read_json_optional(phase4be_summary_path)
    models_dir = paths.runtime_dir / "candidate_ai" / "models"
    model_path = models_dir / MODEL_FILENAME
    model_manifest_path = models_dir / MODEL_MANIFEST_FILENAME

    if be_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(BLOCKED_DATASET, "Phase4-BE dataset summary is missing or not ready.", summary_path)
        _write_json(summary_path, summary)
        return summary
    if not _safe_model_output_path(paths.runtime_dir, models_dir):
        summary = _blocked_summary(BLOCKED_ARTIFACT, "Model output path is not under .runtime/candidate_ai/models.", summary_path)
        _write_json(summary_path, summary)
        return summary

    dataset_path = Path(str(be_summary.get("dataset_output_path") or ""))
    if not dataset_path.is_file():
        summary = _blocked_summary(BLOCKED_DATASET, "Phase4-BE dataset artifact is missing.", summary_path)
        _write_json(summary_path, summary)
        return summary

    dataset = _read_dataset_frame(dataset_path)
    if dataset.empty or TARGET_LABEL not in dataset.columns:
        summary = _blocked_summary(BLOCKED_DATASET, "Dataset is empty or target label is missing.", summary_path)
        _write_json(summary_path, summary)
        return summary

    feature_columns = sorted(column for column in dataset.columns if str(column).startswith("feature__"))
    label_columns = sorted(column for column in dataset.columns if str(column).startswith("label__"))
    leakage = audit_training_features(feature_columns)
    if leakage["status"] != "OK":
        summary = _blocked_summary(
            BLOCKED_LEAKAGE,
            "Training feature leakage audit failed.",
            summary_path,
            dataset_row_count=len(dataset),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            future_column_used_as_feature=leakage["future_column_used_as_feature"],
            label_column_used_as_feature=leakage["label_column_used_as_feature"],
        )
        _write_json(summary_path, summary)
        return summary

    splits = split_dataset(dataset)
    if any(split.empty for split in splits.values()):
        summary = _blocked_summary(BLOCKED_DATASET, "Train, validation, or test split is empty.", summary_path)
        _write_json(summary_path, summary)
        return summary

    y_train = _target_array(splits["train"])
    y_validation = _target_array(splits["validation"])
    y_test = _target_array(splits["test"])
    train_positive_count = int(y_train.sum())
    validation_positive_count = int(y_validation.sum())
    test_positive_count = int(y_test.sum())
    if min(train_positive_count, validation_positive_count, test_positive_count) <= 0:
        summary = _blocked_summary(
            BLOCKED_NO_POSITIVE,
            "One or more splits have no positive target labels.",
            summary_path,
            dataset_row_count=len(dataset),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            train_positive_count=train_positive_count,
            validation_positive_count=validation_positive_count,
            test_positive_count=test_positive_count,
        )
        _write_json(summary_path, summary)
        return summary

    x_train = _feature_matrix(splits["train"], feature_columns)
    x_validation = _feature_matrix(splits["validation"], feature_columns)
    x_test = _feature_matrix(splits["test"], feature_columns)
    scale_pos_weight = _scale_pos_weight(y_train)
    try:
        model, model_type, model_params, class_imbalance_strategy = _fit_model(x_train, y_train, scale_pos_weight)
        validation_scores = _predict_scores(model, x_validation)
        test_scores = _predict_scores(model, x_test)
    except Exception as exc:  # pragma: no cover - defensive path
        summary = _blocked_summary(BLOCKED_TRAINING, f"Model training failed: {type(exc).__name__}", summary_path)
        _write_json(summary_path, summary)
        return summary

    validation_metrics = calculate_formal_metrics(splits["validation"], y_validation, validation_scores)
    test_metrics = calculate_formal_metrics(splits["test"], y_test, test_scores)
    score_stats = score_distribution(np.concatenate([validation_scores, test_scores]))
    all_same_score = bool(score_stats["all_same_score"])
    feature_importance = extract_feature_importance(model, feature_columns)
    feature_importance_nonzero_count = sum(1 for item in feature_importance if item["importance"] > 0)
    tree_stats = extract_tree_stats(model)
    readiness_status = _resolve_readiness(
        all_same_score=all_same_score,
        leakage_ok=leakage["status"] == "OK",
        artifact_ok=True,
        validation_auc=validation_metrics["auc"],
        validation_precision_at_top_50=validation_metrics["precision_at_top_50"],
    )

    model_payload = {
        "phase": PHASE,
        "formal_training": True,
        "model_type": model_type,
        "target_label": TARGET_LABEL,
        "feature_columns": feature_columns,
        "label_columns": label_columns,
        "model": model,
        "model_params": model_params,
        "class_imbalance_strategy": class_imbalance_strategy,
        "created_at": _now(),
    }
    models_dir.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)
    artifact_ok = model_path.is_file()
    if not artifact_ok:
        readiness_status = BLOCKED_ARTIFACT

    manifest = {
        "phase": PHASE,
        "created_at": _now(),
        "formal_training": True,
        "model_type": model_type,
        "target_label": TARGET_LABEL,
        "feature_columns": feature_columns,
        "label_columns": label_columns,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "summary_path": str(summary_path),
        "model_params": model_params,
        "class_imbalance_strategy": class_imbalance_strategy,
        "training_executed": True,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "production_model_promoted": False,
        "reader_switch_performed": False,
    }
    _write_json(model_manifest_path, manifest)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status in {READY, WEAK} else "BLOCKED",
        "readiness_status": readiness_status,
        "training_executed": True,
        "formal_training": True,
        "model_type": model_type,
        "model_artifact_path": str(model_path),
        "model_manifest_path": str(model_manifest_path),
        "dataset_row_count": int(len(dataset)),
        "train_row_count": int(len(splits["train"])),
        "validation_row_count": int(len(splits["validation"])),
        "test_row_count": int(len(splits["test"])),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "target_label": TARGET_LABEL,
        "train_positive_count": train_positive_count,
        "validation_positive_count": validation_positive_count,
        "test_positive_count": test_positive_count,
        "train_positive_rate": _rate(train_positive_count, len(splits["train"])),
        "validation_positive_rate": _rate(validation_positive_count, len(splits["validation"])),
        "test_positive_rate": _rate(test_positive_count, len(splits["test"])),
        "model_params": model_params,
        "class_imbalance_strategy": class_imbalance_strategy,
        **_prefixed_metrics("validation", validation_metrics),
        **_prefixed_metrics("test", test_metrics),
        **score_stats,
        "feature_importance_nonzero_count": feature_importance_nonzero_count,
        "top_feature_importances": feature_importance[:10],
        "tree_count": tree_stats["tree_count"],
        "effective_split_count": tree_stats["effective_split_count"],
        "future_column_used_as_feature": leakage["future_column_used_as_feature"],
        "label_column_used_as_feature": leakage["label_column_used_as_feature"],
        "random_split_used": False,
        "leakage_audit_status": "OK" if leakage["status"] == "OK" else "ERROR",
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "production_model_promoted": False,
        "reader_switch_performed": False,
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def split_dataset(dataset: Any) -> dict[str, Any]:
    return {
        "train": dataset[dataset["split"] == "train"].copy(),
        "validation": dataset[dataset["split"] == "validation"].copy(),
        "test": dataset[dataset["split"] == "test"].copy(),
    }


def audit_training_features(feature_columns: list[str]) -> dict[str, Any]:
    stripped = [column.replace("feature__", "", 1) for column in feature_columns]
    future_columns = [column for column in stripped if is_forbidden_column(column)]
    label_columns = [
        column
        for column in feature_columns
        if column.startswith("label__") or "candidate_label" in column or "momentum_candidate_label" in column
    ]
    status = "OK" if not future_columns and not label_columns else "ERROR"
    return {
        "status": status,
        "future_column_used_as_feature": bool(future_columns),
        "future_columns": future_columns,
        "label_column_used_as_feature": bool(label_columns),
        "label_columns": label_columns,
    }


def calculate_formal_metrics(frame: Any, y_true: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    predictions = (scores >= 0.5).astype(np.int8)
    auc = None
    if len(set(y_true.tolist())) > 1:
        auc = round(float(roc_auc_score(y_true, scores)), 6)
    metrics = {
        "auc": auc,
        "average_precision": round(float(average_precision_score(y_true, scores)), 6),
        "accuracy": round(float(accuracy_score(y_true, predictions)), 6),
        "precision_at_top_50": precision_at_k(y_true, scores, 50),
        "precision_at_top_100": precision_at_k(y_true, scores, 100),
        "precision_at_top_200": precision_at_k(y_true, scores, 200),
    }
    top50 = top_k_frame(frame, scores, 50)
    metrics.update(
        {
            "candidate_top_decile_rate_at_top_50": _mean_bool(top50.get("label__top_decile_20d")),
            "candidate_downside_bad_rate_at_top_50": _mean_bool(top50.get("label__downside_bad_20d")),
            "candidate_mean_future_return_20d_at_top_50": _mean_numeric(top50.get("label__future_return_20d")),
            "candidate_mean_future_max_return_20d_at_top_50": _mean_numeric(top50.get("label__future_max_return_20d")),
        }
    )
    return metrics


def top_k_frame(frame: Any, scores: np.ndarray, k: int) -> Any:
    order = np.argsort(scores)[::-1][: min(k, len(scores))]
    return frame.iloc[order]


def precision_at_k(y_true: np.ndarray, scores: np.ndarray, k: int) -> float | None:
    if len(y_true) == 0:
        return None
    order = np.argsort(scores)[::-1][: min(k, len(y_true))]
    return round(float(precision_score(y_true[order], np.ones(len(order), dtype=np.int8), zero_division=0)), 6)


def score_distribution(scores: np.ndarray) -> dict[str, Any]:
    unique_count = int(len(np.unique(np.round(scores, 12))))
    return {
        "score_min": round(float(np.min(scores)), 8),
        "score_max": round(float(np.max(scores)), 8),
        "score_mean": round(float(np.mean(scores)), 8),
        "score_std": round(float(np.std(scores)), 8),
        "unique_score_count": unique_count,
        "all_same_score": unique_count <= 1,
    }


def _fit_model(x_train: np.ndarray, y_train: np.ndarray, scale_pos_weight: float) -> tuple[Any, str, dict[str, Any], str]:
    try:
        from lightgbm import LGBMClassifier

        params = {
            "n_estimators": 160,
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_child_samples": 200,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "scale_pos_weight": scale_pos_weight,
            "random_state": 42,
            "n_jobs": 4,
            "verbosity": -1,
        }
        model = LGBMClassifier(**params)
        model.fit(x_train, y_train)
        return model, "lightgbm.LGBMClassifier", params, "scale_pos_weight"
    except Exception:
        params = {"max_iter": 120, "learning_rate": 0.05, "random_state": 42, "class_weight": "balanced"}
        model = HistGradientBoostingClassifier(**params)
        model.fit(x_train, y_train)
        return model, "sklearn.HistGradientBoostingClassifier", params, "class_weight=balanced"


def _predict_scores(model: Any, matrix: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(matrix)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(matrix), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(matrix), dtype=float)


def extract_feature_importance(model: Any, feature_columns: list[str]) -> list[dict[str, Any]]:
    if hasattr(model, "feature_importances_"):
        values = list(model.feature_importances_)
    else:
        values = [0 for _ in feature_columns]
    items = [
        {"feature": feature, "importance": int(value) if float(value).is_integer() else round(float(value), 8)}
        for feature, value in zip(feature_columns, values)
    ]
    return sorted(items, key=lambda item: item["importance"], reverse=True)


def extract_tree_stats(model: Any) -> dict[str, int]:
    if hasattr(model, "booster_"):
        dump = model.booster_.dump_model()
        trees = dump.get("tree_info", [])
        return {
            "tree_count": len(trees),
            "effective_split_count": sum(_count_splits(tree.get("tree_structure", {})) for tree in trees),
        }
    return {"tree_count": int(getattr(model, "n_iter_", 0) or 0), "effective_split_count": 0}


def _count_splits(node: dict[str, Any]) -> int:
    if not node or "split_index" not in node:
        return 0
    return 1 + _count_splits(node.get("left_child", {})) + _count_splits(node.get("right_child", {}))


def _feature_matrix(frame: Any, feature_columns: list[str]) -> np.ndarray:
    values = frame[feature_columns].copy()
    for column in values.columns:
        if values[column].dtype == bool:
            values[column] = values[column].astype(float)
    return values.astype(float).to_numpy()


def _target_array(frame: Any) -> np.ndarray:
    return frame[TARGET_LABEL].astype(bool).astype(np.int8).to_numpy()


def _scale_pos_weight(y_train: np.ndarray) -> float:
    positive = int(y_train.sum())
    negative = int(len(y_train) - positive)
    return round(negative / positive, 6) if positive else 1.0


def _read_dataset_frame(path: Path) -> Any:
    import pandas as pd

    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    from ai_fund_lab_v2.data_store import create_storage_backend

    return pd.DataFrame(create_storage_backend("jsonl").read_records(path))


def _resolve_readiness(
    *,
    all_same_score: bool,
    leakage_ok: bool,
    artifact_ok: bool,
    validation_auc: float | None,
    validation_precision_at_top_50: float | None,
) -> str:
    if not artifact_ok:
        return BLOCKED_ARTIFACT
    if not leakage_ok:
        return BLOCKED_LEAKAGE
    if all_same_score:
        return BLOCKED_ALL_SAME
    if validation_auc is not None and validation_auc < 0.51 and (validation_precision_at_top_50 or 0.0) <= 0.0:
        return WEAK
    return READY


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-BG Formal Candidate Inference."
    if readiness_status == WEAK:
        return "Proceed to Phase4-BG for inference smoke, then run Candidate Quality Audit before promotion."
    if readiness_status == BLOCKED_ALL_SAME:
        return "Investigate model quality before candidate inference; scores have no useful variation."
    return "Fix the formal training blocker, then rerun Phase4-BF."


def _prefixed_metrics(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


def _mean_bool(series: Any) -> float | None:
    if series is None or len(series) == 0:
        return None
    return round(float(series.astype(bool).mean()), 6)


def _mean_numeric(series: Any) -> float | None:
    if series is None or len(series) == 0:
        return None
    return round(float(series.mean()), 6)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _blocked_summary(readiness_status: str, reason: str, summary_path: Path, **extra: Any) -> dict[str, Any]:
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "training_executed": False,
        "formal_training": True,
        "dataset_row_count": extra.get("dataset_row_count", 0),
        "feature_column_count": extra.get("feature_column_count", 0),
        "label_column_count": extra.get("label_column_count", 0),
        "future_column_used_as_feature": extra.get("future_column_used_as_feature", False),
        "label_column_used_as_feature": extra.get("label_column_used_as_feature", False),
        "random_split_used": False,
        "leakage_audit_status": "SKIPPED",
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "production_model_promoted": False,
        "recommended_next_action": "Fix the formal training blocker, then rerun Phase4-BF.",
        "summary_path": str(summary_path),
    }
    summary.update(extra)
    return summary


def _safe_model_output_path(runtime_dir: Path, models_dir: Path) -> bool:
    try:
        models_dir.resolve().relative_to((runtime_dir.resolve() / "candidate_ai" / "models").resolve())
        return True
    except ValueError:
        return False


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
