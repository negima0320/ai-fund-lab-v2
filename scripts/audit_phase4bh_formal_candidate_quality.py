#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PHASE = "Phase4-BH"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bh_formal_candidate_quality_summary.json")
PHASE4BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
PHASE4BG_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_summary.json")
PHASE4BG_TOP50_PATH = Path("reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_top50.json")

PHASE4_COMPLETE = "PHASE4_COMPLETE"
PHASE4_COMPLETE_WITH_IMPROVEMENT = "PHASE4_COMPLETE_WITH_IMPROVEMENT_OPPORTUNITIES"
READY_FOR_FEATURE_EXPANSION = "READY_FOR_FEATURE_EXPANSION_PHASE"
BLOCKED_QUALITY = "BLOCKED_BY_CANDIDATE_QUALITY"
BLOCKED_AUDIT = "BLOCKED_BY_AUDIT_FAILURE"

TOP_K_VALUES = (50, 100, 200)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-BH formal Candidate AI quality.")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--phase4bf-summary", default=str(PHASE4BF_SUMMARY_PATH))
    parser.add_argument("--phase4bg-summary", default=str(PHASE4BG_SUMMARY_PATH))
    parser.add_argument("--phase4bg-top50", default=str(PHASE4BG_TOP50_PATH))
    args = parser.parse_args(argv)
    summary = audit_phase4bh_formal_candidate_quality(
        report_dir=args.report_dir,
        phase4bf_summary_path=Path(args.phase4bf_summary),
        phase4bg_summary_path=Path(args.phase4bg_summary),
        phase4bg_top50_path=Path(args.phase4bg_top50),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def audit_phase4bh_formal_candidate_quality(
    *,
    report_dir: Path | str = "reports/candidate_ai/full_range",
    phase4bf_summary_path: Path = PHASE4BF_SUMMARY_PATH,
    phase4bg_summary_path: Path = PHASE4BG_SUMMARY_PATH,
    phase4bg_top50_path: Path = PHASE4BG_TOP50_PATH,
) -> dict[str, Any]:
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    try:
        bf_summary = _read_json(phase4bf_summary_path)
        bg_summary = _read_json(phase4bg_summary_path)
        bg_top50 = _read_json(phase4bg_top50_path)
        if bf_summary.get("readiness_status") != "READY_FOR_FORMAL_CANDIDATE_INFERENCE":
            return _write_and_return(summary_path, _blocked("Phase4-BF summary is not ready for quality audit."))
        if bg_summary.get("readiness_status") != "READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT":
            return _write_and_return(summary_path, _blocked("Phase4-BG summary is not ready for quality audit."))
        if not isinstance(bg_top50.get("rows"), list) or len(bg_top50["rows"]) != 50:
            return _write_and_return(summary_path, _blocked("Phase4-BG top50 artifact is missing or invalid."))

        model_path = Path(str(bf_summary.get("model_artifact_path") or ""))
        model_manifest_path = Path(str(bf_summary.get("model_manifest_path") or ""))
        model_payload = _read_pickle(model_path)
        model_manifest = _read_json(model_manifest_path) if model_manifest_path.is_file() else {}
        dataset_path = Path(str(model_payload.get("dataset_path") or model_manifest.get("dataset_path") or ""))
        feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
        model = model_payload.get("model")
        if not model_path.is_file() or not dataset_path.is_file() or not feature_columns or model is None:
            return _write_and_return(summary_path, _blocked("Model artifact, dataset, or feature columns are missing."))

        dataset = _read_dataset(dataset_path, feature_columns)
        validation = dataset[dataset["split"] == "validation"].copy()
        test = dataset[dataset["split"] == "test"].copy()
        if validation.empty or test.empty:
            return _write_and_return(summary_path, _blocked("Validation or test split is empty."))

        validation_scores = _predict_scores(model, _feature_matrix(validation, feature_columns))
        test_scores = _predict_scores(model, _feature_matrix(test, feature_columns))
        validation_metrics = evaluate_split(validation, validation_scores)
        test_metrics = evaluate_split(test, test_scores)
        validation_deciles = score_decile_report(validation, validation_scores)
        test_deciles = score_decile_report(test, test_scores)
        correlations = {
            "validation": score_correlations(validation, validation_scores),
            "test": score_correlations(test, test_scores),
        }
        monotonicity = evaluate_monotonicity(validation_deciles, test_deciles, correlations)
        quality = judge_candidate_quality(validation_metrics, test_metrics, monotonicity)

        summary = {
            "phase": PHASE,
            "status": "OK" if quality["readiness_status"] in {PHASE4_COMPLETE, PHASE4_COMPLETE_WITH_IMPROVEMENT} else "BLOCKED",
            "readiness_status": quality["readiness_status"],
            "candidate_quality_audit_executed": True,
            "validation_top50_top_decile_rate": validation_metrics["top_50"]["top_decile_rate"],
            "validation_top100_top_decile_rate": validation_metrics["top_100"]["top_decile_rate"],
            "validation_top200_top_decile_rate": validation_metrics["top_200"]["top_decile_rate"],
            "test_top50_top_decile_rate": test_metrics["top_50"]["top_decile_rate"],
            "test_top100_top_decile_rate": test_metrics["top_100"]["top_decile_rate"],
            "test_top200_top_decile_rate": test_metrics["top_200"]["top_decile_rate"],
            "validation_top50_mean_future_return_20d": validation_metrics["top_50"]["mean_future_return_20d"],
            "test_top50_mean_future_return_20d": test_metrics["top_50"]["mean_future_return_20d"],
            "validation_top50_mean_future_max_return_20d": validation_metrics["top_50"]["mean_future_max_return_20d"],
            "test_top50_mean_future_max_return_20d": test_metrics["top_50"]["mean_future_max_return_20d"],
            "validation_top50_downside_bad_rate": validation_metrics["top_50"]["downside_bad_rate"],
            "test_top50_downside_bad_rate": test_metrics["top_50"]["downside_bad_rate"],
            "validation_market_baseline": validation_metrics["market_baseline"],
            "test_market_baseline": test_metrics["market_baseline"],
            "validation_random_baseline": validation_metrics["random_baseline"],
            "test_random_baseline": test_metrics["random_baseline"],
            "validation_top_k_metrics": {key: value for key, value in validation_metrics.items() if key.startswith("top_")},
            "test_top_k_metrics": {key: value for key, value in test_metrics.items() if key.startswith("top_")},
            "validation_score_decile_report": validation_deciles,
            "test_score_decile_report": test_deciles,
            "score_future_return_correlation": {
                "validation": correlations["validation"]["future_return_20d"],
                "test": correlations["test"]["future_return_20d"],
            },
            "score_future_max_return_correlation": {
                "validation": correlations["validation"]["future_max_return_20d"],
                "test": correlations["test"]["future_max_return_20d"],
            },
            "score_downside_bad_correlation": {
                "validation": correlations["validation"]["downside_bad_20d"],
                "test": correlations["test"]["downside_bad_20d"],
            },
            "score_monotonicity_status": monotonicity["status"],
            "score_monotonicity_detail": monotonicity,
            "candidate_quality_pass": quality["candidate_quality_pass"],
            "candidate_quality_strengths": quality["strengths"],
            "candidate_quality_weaknesses": quality["weaknesses"],
            "phase4bg_top50_candidate_count": len(bg_top50["rows"]),
            "phase4bg_target_date": bg_summary.get("target_date"),
            "backtest_executed": False,
            "trading_executed": False,
            "paper_trading_executed": False,
            "broker_api_called": False,
            "order_executed": False,
            "production_model_promoted": False,
            "reader_switch_performed": False,
            "recommended_next_action": quality["recommended_next_action"],
            "summary_path": str(summary_path),
        }
        _write_json(summary_path, summary)
        _write_markdown(Path("docs/phase_reports/phase4bh_formal_candidate_quality_audit.md"), summary)
        if summary["readiness_status"] in {PHASE4_COMPLETE, PHASE4_COMPLETE_WITH_IMPROVEMENT}:
            _write_phase4_completion_report(summary)
        return summary
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return _write_and_return(summary_path, _blocked(f"Candidate quality audit failed: {type(exc).__name__}"))


def evaluate_split(frame: Any, scores: np.ndarray) -> dict[str, Any]:
    scored = frame.copy()
    scored["_candidate_score"] = scores
    scored = scored.sort_values("_candidate_score", ascending=False)
    metrics: dict[str, Any] = {
        "market_baseline": metric_bundle(frame),
        "random_baseline": random_baseline(frame),
    }
    for k in TOP_K_VALUES:
        metrics[f"top_{k}"] = metric_bundle(scored.head(k))
    return metrics


def metric_bundle(frame: Any) -> dict[str, Any]:
    return {
        "row_count": int(len(frame)),
        "top_decile_rate": _mean_bool(frame["label__top_decile_20d"]),
        "mean_future_return_5d": _mean_float(frame["label__future_return_5d"]),
        "mean_future_return_10d": _mean_float(frame["label__future_return_10d"]),
        "mean_future_return_20d": _mean_float(frame["label__future_return_20d"]),
        "mean_future_max_return_20d": _mean_float(frame["label__future_max_return_20d"]),
        "mean_future_max_drawdown_20d": _mean_float(frame["label__future_max_drawdown_20d"]),
        "downside_bad_rate": _mean_bool(frame["label__downside_bad_20d"]),
        "precision": _mean_bool(frame["label__momentum_candidate_label"]),
    }


def random_baseline(frame: Any, *, seed: int = 42, samples: int = 20) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    result: dict[str, Any] = {}
    for k in TOP_K_VALUES:
        bundles = []
        sample_size = min(k, len(frame))
        for _ in range(samples):
            indices = rng.choice(len(frame), size=sample_size, replace=False)
            bundles.append(metric_bundle(frame.iloc[indices]))
        result[f"top_{k}"] = _average_bundles(bundles)
    return result


def score_decile_report(frame: Any, scores: np.ndarray) -> list[dict[str, Any]]:
    scored = frame.copy()
    scored["_candidate_score"] = scores
    scored["_score_decile"] = np.floor(scored["_candidate_score"].rank(method="first", pct=True) * 10).clip(0, 9).astype(int) + 1
    report: list[dict[str, Any]] = []
    for decile, group in scored.groupby("_score_decile", sort=True):
        bundle = metric_bundle(group)
        bundle["score_decile"] = int(decile)
        bundle["score_mean"] = round(float(group["_candidate_score"].mean()), 8)
        report.append(bundle)
    return report


def score_correlations(frame: Any, scores: np.ndarray) -> dict[str, float | None]:
    import pandas as pd

    series = pd.Series(scores)
    return {
        "future_return_20d": _corr(series, frame["label__future_return_20d"]),
        "future_max_return_20d": _corr(series, frame["label__future_max_return_20d"]),
        "downside_bad_20d": _corr(series, frame["label__downside_bad_20d"].astype(float)),
    }


def evaluate_monotonicity(validation_deciles: list[dict[str, Any]], test_deciles: list[dict[str, Any]], correlations: dict[str, Any]) -> dict[str, Any]:
    validation_top = validation_deciles[-1]
    validation_bottom = validation_deciles[0]
    test_top = test_deciles[-1]
    test_bottom = test_deciles[0]
    checks = {
        "validation_top_decile_rate_gt_bottom": validation_top["top_decile_rate"] > validation_bottom["top_decile_rate"],
        "test_top_decile_rate_gt_bottom": test_top["top_decile_rate"] > test_bottom["top_decile_rate"],
        "validation_max_return_corr_positive": (correlations["validation"]["future_max_return_20d"] or 0.0) > 0,
        "test_max_return_corr_positive": (correlations["test"]["future_max_return_20d"] or 0.0) > 0,
    }
    passed = sum(1 for value in checks.values() if value)
    return {
        "status": "OK" if passed >= 3 else "WEAK" if passed >= 2 else "NG",
        "checks": checks,
        "passed_count": passed,
    }


def judge_candidate_quality(validation: dict[str, Any], test: dict[str, Any], monotonicity: dict[str, Any]) -> dict[str, Any]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    validation_market = validation["market_baseline"]
    test_market = test["market_baseline"]
    validation_top50 = validation["top_50"]
    test_top50 = test["top_50"]
    top_decile_lift_ok = (
        validation_top50["top_decile_rate"] > validation_market["top_decile_rate"]
        and test_top50["top_decile_rate"] > test_market["top_decile_rate"]
    )
    max_return_lift_ok = (
        validation_top50["mean_future_max_return_20d"] > validation_market["mean_future_max_return_20d"]
        and test_top50["mean_future_max_return_20d"] > test_market["mean_future_max_return_20d"]
    )
    downside_ok = (
        validation_top50["downside_bad_rate"] <= validation_market["downside_bad_rate"]
        and test_top50["downside_bad_rate"] <= test_market["downside_bad_rate"]
    )
    if top_decile_lift_ok:
        strengths.append("top50_top_decile_rate_beats_market_in_validation_and_test")
    else:
        weaknesses.append("top50_top_decile_rate_does_not_consistently_beat_market")
    if max_return_lift_ok:
        strengths.append("top50_future_max_return_beats_market_in_validation_and_test")
    else:
        weaknesses.append("top50_future_max_return_lift_is_weak")
    if downside_ok:
        strengths.append("top50_downside_bad_rate_not_worse_than_market")
    else:
        weaknesses.append("top50_downside_bad_rate_is_worse_than_market")
    if monotonicity["status"] == "OK":
        strengths.append("score_monotonicity_is_acceptable")
    else:
        weaknesses.append("score_monotonicity_needs_improvement")

    candidate_quality_pass = top_decile_lift_ok and max_return_lift_ok
    if candidate_quality_pass and not weaknesses:
        readiness = PHASE4_COMPLETE
    elif candidate_quality_pass:
        readiness = PHASE4_COMPLETE_WITH_IMPROVEMENT
    elif top_decile_lift_ok or max_return_lift_ok:
        readiness = READY_FOR_FEATURE_EXPANSION
    else:
        readiness = BLOCKED_QUALITY
    next_action = (
        "Phase4 complete; prepare Phase5 Opportunity AI design."
        if readiness == PHASE4_COMPLETE
        else "Close Phase4 as effective Candidate AI with improvement opportunities; prepare Phase5 Opportunity AI design."
        if readiness == PHASE4_COMPLETE_WITH_IMPROVEMENT
        else "Improve Candidate features/model before closing Phase4."
    )
    return {
        "candidate_quality_pass": candidate_quality_pass,
        "readiness_status": readiness,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommended_next_action": next_action,
    }


def _read_dataset(path: Path, feature_columns: list[str]) -> Any:
    import pandas as pd

    columns = [
        "split",
        *feature_columns,
        "label__future_return_5d",
        "label__future_return_10d",
        "label__future_return_20d",
        "label__future_max_return_20d",
        "label__future_max_drawdown_20d",
        "label__top_decile_20d",
        "label__downside_bad_20d",
        "label__momentum_candidate_label",
    ]
    return pd.read_parquet(path, columns=columns)


def _feature_matrix(frame: Any, feature_columns: list[str]) -> np.ndarray:
    values = frame[feature_columns].copy()
    for column in values.columns:
        if values[column].dtype == bool:
            values[column] = values[column].astype(float)
    return values.astype(float).to_numpy()


def _predict_scores(model: Any, matrix: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(matrix)
        if proba.ndim == 2 and proba.shape[1] > 1:
            return np.asarray(proba[:, 1], dtype=float)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(matrix), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    return np.asarray(model.predict(matrix), dtype=float)


def _average_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    if not bundles:
        return {}
    result = {"row_count": bundles[0]["row_count"]}
    for key in bundles[0]:
        if key == "row_count":
            continue
        result[key] = round(float(np.mean([bundle[key] for bundle in bundles])), 6)
    return result


def _mean_bool(series: Any) -> float:
    return round(float(series.astype(bool).mean()), 6) if len(series) else 0.0


def _mean_float(series: Any) -> float:
    return round(float(series.astype(float).mean()), 6) if len(series) else 0.0


def _corr(left: Any, right: Any) -> float | None:
    value = left.astype(float).corr(right.astype(float))
    if value != value:
        return None
    return round(float(value), 6)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BH Formal Candidate Quality Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- candidate_quality_pass: `{summary['candidate_quality_pass']}`",
        "",
        "## Top K Quality",
        "",
        f"- validation_top50_top_decile_rate: `{summary['validation_top50_top_decile_rate']}`",
        f"- test_top50_top_decile_rate: `{summary['test_top50_top_decile_rate']}`",
        f"- validation_top50_mean_future_max_return_20d: `{summary['validation_top50_mean_future_max_return_20d']}`",
        f"- test_top50_mean_future_max_return_20d: `{summary['test_top50_mean_future_max_return_20d']}`",
        f"- validation_top50_downside_bad_rate: `{summary['validation_top50_downside_bad_rate']}`",
        f"- test_top50_downside_bad_rate: `{summary['test_top50_downside_bad_rate']}`",
        "",
        "## Baseline",
        "",
        f"- validation_market_baseline: `{summary['validation_market_baseline']}`",
        f"- test_market_baseline: `{summary['test_market_baseline']}`",
        "",
        "## Strengths",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["candidate_quality_strengths"])
    lines.extend(["", "## Weaknesses", ""])
    lines.extend(f"- {item}" for item in summary["candidate_quality_weaknesses"])
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Candidate Quality Audit only.",
            "- No retraining, feature addition, label change, inference rerun, backtest, trading, Paper Trading, broker API, promotion, reader switch, or order execution.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_phase4_completion_report(summary: dict[str, Any]) -> None:
    path = Path("docs/phase_reports/phase4_completion_summary.md")
    lines = [
        "# Phase4 Candidate AI Completion Summary",
        "",
        f"- completion_status: `{summary['readiness_status']}`",
        f"- candidate_quality_pass: `{summary['candidate_quality_pass']}`",
        "- scope: Candidate AI candidate extraction only.",
        "- no backtest, trading, Paper Trading, broker API, promotion, reader switch, or order execution was performed.",
        "",
        "## Evidence",
        "",
        f"- validation_top50_top_decile_rate: `{summary['validation_top50_top_decile_rate']}`",
        f"- test_top50_top_decile_rate: `{summary['test_top50_top_decile_rate']}`",
        f"- validation_top50_mean_future_max_return_20d: `{summary['validation_top50_mean_future_max_return_20d']}`",
        f"- test_top50_mean_future_max_return_20d: `{summary['test_top50_mean_future_max_return_20d']}`",
        f"- score_monotonicity_status: `{summary['score_monotonicity_status']}`",
        "",
        "## Next Phase",
        "",
        "Proceed to Phase5 Opportunity AI design. Phase5 decides opportunity quality; Phase4 does not decide buy, sell, holding, allocation, or order execution.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": BLOCKED_AUDIT,
        "candidate_quality_audit_executed": False,
        "block_reason": reason,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "production_model_promoted": False,
        "reader_switch_performed": False,
        "recommended_next_action": "Fix the Candidate Quality Audit blocker, then rerun Phase4-BH.",
    }


def _write_and_return(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _write_json(path, payload)
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
