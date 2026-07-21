from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss


class CandidateCalibrationError(ValueError):
    """Fail-closed error for Candidate calibration failures."""


@dataclass(frozen=True)
class CandidateCalibrationResult:
    status: str
    parameters: dict[str, Any]
    raw_scores: list[float]
    calibrated_probability: list[float]
    quality_metrics: dict[str, Any]
    quality_gate_result: dict[str, Any]


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -709.0, 709.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def expected_calibration_error(probabilities: np.ndarray, labels: np.ndarray, *, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lower, upper in zip(edges[:-1], edges[1:]):
        mask = (probabilities >= lower) & (probabilities <= upper if upper == 1.0 else probabilities < upper)
        if not mask.any():
            continue
        ece += float(mask.mean()) * abs(float(probabilities[mask].mean()) - float(labels[mask].mean()))
    return float(ece)


def calibration_curve(probabilities: np.ndarray, labels: np.ndarray, *, bins: int = 10) -> list[dict[str, Any]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    curve: list[dict[str, Any]] = []
    for idx, (lower, upper) in enumerate(zip(edges[:-1], edges[1:])):
        mask = (probabilities >= lower) & (probabilities <= upper if upper == 1.0 else probabilities < upper)
        curve.append(
            {
                "bin": idx,
                "lower": float(lower),
                "upper": float(upper),
                "count": int(mask.sum()),
                "mean_probability": float(probabilities[mask].mean()) if mask.any() else None,
                "positive_rate": float(labels[mask].mean()) if mask.any() else None,
            }
        )
    return curve


def prediction_histogram(values: np.ndarray, *, bins: int = 10) -> dict[str, Any]:
    counts, edges = np.histogram(values, bins=bins)
    return {"counts": [int(v) for v in counts], "edges": [float(v) for v in edges]}


def candidate_metrics(probabilities: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    return {
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "log_loss": float(log_loss(labels, np.clip(probabilities, 1e-15, 1.0 - 1e-15), labels=[0, 1])),
        "expected_calibration_error": expected_calibration_error(probabilities, labels),
        "calibration_curve": calibration_curve(probabilities, labels),
        "prediction_histogram": prediction_histogram(probabilities),
        "finite": bool(np.isfinite(probabilities).all()),
        "collapse": bool(np.unique(np.round(probabilities, 12)).size <= 1),
    }


def fit_candidate_platt(raw_scores: list[float] | np.ndarray, labels: list[int] | np.ndarray) -> CandidateCalibrationResult:
    scores = np.asarray(raw_scores, dtype=float).reshape(-1)
    y = np.asarray(labels, dtype=int).reshape(-1)
    if scores.size != y.size or scores.size == 0:
        raise CandidateCalibrationError("candidate_input_size_mismatch")
    if not np.isfinite(scores).all() or not np.isfinite(y).all():
        raise CandidateCalibrationError("candidate_nan_or_inf")
    if np.unique(y).size < 2:
        raise CandidateCalibrationError("candidate_one_sided_labels")
    identity_prob = sigmoid(scores)
    model = LogisticRegression(solver="lbfgs", random_state=42)
    model.fit(scores.reshape(-1, 1), y)
    calibrated = model.predict_proba(scores.reshape(-1, 1))[:, 1]
    identity_metrics = candidate_metrics(identity_prob, y)
    calibrated_metrics = candidate_metrics(calibrated, y)
    monotonic = bool(model.coef_[0][0] >= 0)
    worsened = (
        calibrated_metrics["brier_score"] > identity_metrics["brier_score"]
        or calibrated_metrics["log_loss"] > identity_metrics["log_loss"]
    )
    reason_codes: list[str] = []
    if not calibrated_metrics["finite"]:
        reason_codes.append("candidate_non_finite_probability")
    if calibrated.min() < 0.0 or calibrated.max() > 1.0:
        reason_codes.append("candidate_probability_out_of_range")
    if calibrated_metrics["collapse"]:
        reason_codes.append("candidate_collapsed_prediction")
    if not monotonic:
        reason_codes.append("candidate_non_monotonic_mapping")
        reason_codes.append("candidate_platt_worse_than_identity")
    if worsened:
        reason_codes.append("candidate_platt_worse_than_identity")
    reason_codes = list(dict.fromkeys(reason_codes))
    status = "PASS" if not reason_codes else "CANDIDATE_CALIBRATION_REVIEW_REQUIRED"
    return CandidateCalibrationResult(
        status=status,
        parameters={
            "method": "PLATT_SCALING",
            "intercept": float(model.intercept_[0]),
            "coefficient": float(model.coef_[0][0]),
            "identity_comparison_required": True,
        },
        raw_scores=[float(v) for v in scores],
        calibrated_probability=[float(v) for v in calibrated],
        quality_metrics={
            "identity": identity_metrics,
            "platt": calibrated_metrics,
            "main_metric_worsened_vs_identity": bool(worsened),
            "monotonicity": {"status": "PASS" if monotonic else "BLOCK", "coefficient": float(model.coef_[0][0])},
        },
        quality_gate_result={"status": status, "reason_codes": reason_codes},
    )
