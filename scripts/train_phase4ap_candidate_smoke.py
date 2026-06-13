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

PHASE = "Phase4-AP"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ap_candidate_training_smoke_summary.json")
PHASE4AO_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json")

READY_INPUT = "READY_FOR_FIRST_LIGHTGBM_TRAINING"
READY = "READY_FOR_CANDIDATE_INFERENCE_SMOKE"
BLOCKED_DATASET = "BLOCKED_BY_DATASET"
BLOCKED_NO_POSITIVE = "BLOCKED_BY_NO_POSITIVE_LABEL"
BLOCKED_TRAINING = "BLOCKED_BY_MODEL_TRAINING"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_ARTIFACT = "BLOCKED_BY_MODEL_ARTIFACT"

TARGET_LABEL = "label__momentum_candidate_label"
MODEL_FILENAME = "phase4ap_candidate_smoke_model.pkl"
MODEL_MANIFEST_FILENAME = "phase4ap_candidate_smoke_manifest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-AP Candidate AI training smoke test.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--phase4ao-summary", default=str(PHASE4AO_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = train_phase4ap_candidate_smoke(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        phase4ao_summary_path=Path(args.phase4ao_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def train_phase4ap_candidate_smoke(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    phase4ao_summary_path: Path = PHASE4AO_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    ao_summary = _read_json_optional(phase4ao_summary_path)
    models_dir = paths.runtime_dir / "candidate_ai" / "models"
    model_path = models_dir / MODEL_FILENAME
    model_manifest_path = models_dir / MODEL_MANIFEST_FILENAME

    if ao_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_DATASET,
            reason="Phase4-AO dataset summary is missing or not ready.",
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _safe_runtime_output_path(paths.runtime_dir, models_dir):
        summary = _blocked_summary(
            readiness_status=BLOCKED_ARTIFACT,
            reason="Model output path is not under .runtime/candidate_ai/models.",
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    dataset_path = Path(str(ao_summary.get("dataset_output_path") or ""))
    dataset_payload = _read_json_optional(dataset_path)
    rows = [dict(row) for row in dataset_payload.get("rows", []) if isinstance(row, dict)]
    if not rows:
        summary = _blocked_summary(
            readiness_status=BLOCKED_DATASET,
            reason="Phase4-AO dataset has no rows.",
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_columns = _feature_columns(rows)
    label_columns = _label_columns(rows)
    leakage = audit_training_features(feature_columns)
    y = np.asarray([1 if row.get(TARGET_LABEL) is True else 0 for row in rows], dtype=np.int8)
    positive_label_count = int(y.sum())
    if positive_label_count <= 0:
        summary = _blocked_summary(
            readiness_status=BLOCKED_NO_POSITIVE,
            reason="Target label has no positive rows.",
            summary_path=summary_path,
            dataset_row_count=len(rows),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            positive_label_count=positive_label_count,
        )
        _write_json(summary_path, summary)
        return summary
    if leakage["status"] != "OK":
        summary = _blocked_summary(
            readiness_status=BLOCKED_LEAKAGE,
            reason="Training feature leakage audit failed.",
            summary_path=summary_path,
            dataset_row_count=len(rows),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            positive_label_count=positive_label_count,
            future_column_used_as_feature=leakage["future_column_used_as_feature"],
            label_column_used_as_feature=leakage["label_column_used_as_feature"],
        )
        _write_json(summary_path, summary)
        return summary

    split = build_smoke_time_series_split(rows)
    if not split["train_indices"] or not split["validation_indices"]:
        summary = _blocked_summary(
            readiness_status=BLOCKED_DATASET,
            reason="Smoke time-series split could not create train and validation rows.",
            summary_path=summary_path,
            dataset_row_count=len(rows),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            positive_label_count=positive_label_count,
        )
        _write_json(summary_path, summary)
        return summary

    x_all = _feature_matrix(rows, feature_columns)
    train_indices = np.asarray(split["train_indices"], dtype=np.int64)
    validation_indices = np.asarray(split["validation_indices"], dtype=np.int64)
    x_train = x_all[train_indices]
    y_train = y[train_indices]
    x_valid = x_all[validation_indices]
    y_valid = y[validation_indices]
    if int(y_train.sum()) <= 0:
        summary = _blocked_summary(
            readiness_status=BLOCKED_NO_POSITIVE,
            reason="Smoke train split has no positive target labels.",
            summary_path=summary_path,
            dataset_row_count=len(rows),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            positive_label_count=positive_label_count,
        )
        _write_json(summary_path, summary)
        return summary

    try:
        model, model_type = _fit_model(x_train, y_train)
        scores = _predict_scores(model, x_valid)
    except Exception as exc:  # pragma: no cover - defensive path
        summary = _blocked_summary(
            readiness_status=BLOCKED_TRAINING,
            reason=f"Model training failed: {type(exc).__name__}",
            summary_path=summary_path,
            dataset_row_count=len(rows),
            feature_column_count=len(feature_columns),
            label_column_count=len(label_columns),
            positive_label_count=positive_label_count,
        )
        _write_json(summary_path, summary)
        return summary

    metrics = calculate_metrics(y_valid, scores)
    model_payload = {
        "phase": PHASE,
        "model_type": model_type,
        "target_label": TARGET_LABEL,
        "feature_columns": feature_columns,
        "model": model,
        "created_at": _now(),
        "smoke_test": True,
    }
    models_dir.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(model_payload, handle)

    readiness_status = READY if model_path.is_file() else BLOCKED_ARTIFACT
    manifest = {
        "phase": PHASE,
        "created_at": _now(),
        "smoke_test": True,
        "model_type": model_type,
        "target_label": TARGET_LABEL,
        "feature_columns": feature_columns,
        "dataset_path": str(dataset_path),
        "model_artifact_path": str(model_path),
        "summary_path": str(summary_path),
        "smoke_train_date_min": split["train_date_min"],
        "smoke_train_date_max": split["train_date_max"],
        "smoke_validation_date_min": split["validation_date_min"],
        "smoke_validation_date_max": split["validation_date_max"],
        "production_model_promoted": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }
    _write_json(model_manifest_path, manifest)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "training_executed": True,
        "smoke_test": True,
        "model_type": model_type,
        "model_artifact_path": str(model_path),
        "model_manifest_path": str(model_manifest_path),
        "dataset_row_count": len(rows),
        "smoke_train_row_count": len(train_indices),
        "smoke_validation_row_count": len(validation_indices),
        "feature_column_count": len(feature_columns),
        "label_column_count": len(label_columns),
        "target_label": TARGET_LABEL.replace("label__", "", 1),
        "positive_label_count": positive_label_count,
        "positive_label_rate": round(positive_label_count / len(rows), 6),
        "auc": metrics["auc"],
        "average_precision": metrics["average_precision"],
        "accuracy": metrics["accuracy"],
        "precision_at_top_50": metrics["precision_at_top_50"],
        "future_column_used_as_feature": leakage["future_column_used_as_feature"],
        "label_column_used_as_feature": leakage["label_column_used_as_feature"],
        "random_split_used": False,
        "leakage_audit_status": "OK" if leakage["status"] == "OK" else "ERROR",
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "production_model_promoted": False,
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_smoke_time_series_split(rows: list[dict[str, Any]], *, train_ratio: float = 0.7) -> dict[str, Any]:
    dates = sorted({str(row.get("target_date")) for row in rows if row.get("target_date")})
    if len(dates) < 2:
        return {
            "train_indices": [],
            "validation_indices": [],
            "train_date_min": None,
            "train_date_max": None,
            "validation_date_min": None,
            "validation_date_max": None,
        }
    cutoff = max(1, min(len(dates) - 1, int(len(dates) * train_ratio)))
    train_dates = set(dates[:cutoff])
    validation_dates = set(dates[cutoff:])
    train_indices = [index for index, row in enumerate(rows) if str(row.get("target_date")) in train_dates]
    validation_indices = [index for index, row in enumerate(rows) if str(row.get("target_date")) in validation_dates]
    return {
        "train_indices": train_indices,
        "validation_indices": validation_indices,
        "train_date_min": dates[0],
        "train_date_max": dates[cutoff - 1],
        "validation_date_min": dates[cutoff],
        "validation_date_max": dates[-1],
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


def calculate_metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float | None]:
    predictions = (scores >= 0.5).astype(np.int8)
    auc = None
    if len(set(y_true.tolist())) > 1:
        auc = round(float(roc_auc_score(y_true, scores)), 6)
    average_precision = round(float(average_precision_score(y_true, scores)), 6)
    accuracy = round(float(accuracy_score(y_true, predictions)), 6)
    precision_at_top_50 = _precision_at_k(y_true, scores, k=50)
    return {
        "auc": auc,
        "average_precision": average_precision,
        "accuracy": accuracy,
        "precision_at_top_50": precision_at_top_50,
    }


def _fit_model(x_train: np.ndarray, y_train: np.ndarray) -> tuple[Any, str]:
    try:
        from lightgbm import LGBMClassifier

        model = LGBMClassifier(
            n_estimators=50,
            learning_rate=0.05,
            num_leaves=15,
            min_child_samples=50,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=1,
            verbosity=-1,
        )
        model.fit(x_train, y_train)
        return model, "lightgbm.LGBMClassifier"
    except Exception:
        model = HistGradientBoostingClassifier(max_iter=50, learning_rate=0.05, random_state=42)
        model.fit(x_train, y_train)
        return model, "sklearn.HistGradientBoostingClassifier"


def _predict_scores(model: Any, x_valid: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x_valid)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x_valid), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(x_valid), dtype=float)


def _precision_at_k(y_true: np.ndarray, scores: np.ndarray, *, k: int) -> float | None:
    if len(y_true) == 0:
        return None
    top_k = min(k, len(y_true))
    order = np.argsort(scores)[::-1][:top_k]
    return round(float(precision_score(y_true[order], np.ones(top_k, dtype=np.int8), zero_division=0)), 6)


def _feature_matrix(rows: list[dict[str, Any]], feature_columns: list[str]) -> np.ndarray:
    matrix: list[list[float]] = []
    for row in rows:
        matrix.append([_numeric_value(row.get(column)) for column in feature_columns])
    return np.asarray(matrix, dtype=float)


def _numeric_value(value: Any) -> float:
    if value is None:
        return np.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({column for row in rows for column in row if column.startswith("feature__")})


def _label_columns(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({column for row in rows for column in row if column.startswith("label__")})


def _safe_runtime_output_path(runtime_dir: Path, models_dir: Path) -> bool:
    try:
        models_dir.resolve().relative_to((runtime_dir.resolve() / "candidate_ai" / "models").resolve())
        return True
    except ValueError:
        return False


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    summary_path: Path,
    dataset_row_count: int = 0,
    feature_column_count: int = 0,
    label_column_count: int = 0,
    positive_label_count: int = 0,
    future_column_used_as_feature: bool = False,
    label_column_used_as_feature: bool = False,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "training_executed": False,
        "smoke_test": True,
        "model_type": None,
        "model_artifact_path": None,
        "model_manifest_path": None,
        "dataset_row_count": dataset_row_count,
        "smoke_train_row_count": 0,
        "smoke_validation_row_count": 0,
        "feature_column_count": feature_column_count,
        "label_column_count": label_column_count,
        "target_label": TARGET_LABEL.replace("label__", "", 1),
        "positive_label_count": positive_label_count,
        "positive_label_rate": 0.0,
        "auc": None,
        "average_precision": None,
        "accuracy": None,
        "precision_at_top_50": None,
        "future_column_used_as_feature": future_column_used_as_feature,
        "label_column_used_as_feature": label_column_used_as_feature,
        "random_split_used": False,
        "leakage_audit_status": "ERROR" if future_column_used_as_feature or label_column_used_as_feature else "SKIPPED",
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "production_model_promoted": False,
        "recommended_next_action": _recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }


def _recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY:
        return "Phase4-AQ Candidate Inference Smoke using the smoke model; do not promote to production."
    return "Fix the Phase4-AP smoke training blocker, then rerun the smoke test."


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
