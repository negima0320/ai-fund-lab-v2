from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import stable_json_hash


GATE_ID = "OPPORTUNITY_SELECTION_UTILITY_GATE_V1"
PASS = "PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
METRIC_UNAVAILABLE = "METRIC_UNAVAILABLE"
TOP_NS = (5, 10, 20)
REQUIRED_METRIC_FAMILIES = (
    "realized_return",
    "top_minus_bottom",
    "hit_rate",
    "downside_rate",
    "rank_lift",
    "ndcg",
    "spearman_rank_correlation",
)


def candidate_selected_rows_hash(rows: list[dict[str, Any]]) -> str:
    keys = [
        {
            "target_date": row.get("target_date"),
            "symbol": row.get("symbol") or row.get("code"),
            "candidate_rank": row.get("candidate_rank"),
            "candidate_score": row.get("candidate_score"),
        }
        for row in rows
    ]
    return stable_json_hash(keys)


def validate_candidate_population_binding(*, rows: list[dict[str, Any]], binding: dict[str, Any]) -> dict[str, Any]:
    required = (
        "candidate_source_artifact_id",
        "candidate_source_content_hash",
        "candidate_score_field",
        "candidate_pass_rule",
        "candidate_population_size",
        "candidate_selected_rows_hash",
    )
    reasons = ["missing_binding:" + name for name in required if not binding.get(name)]
    if not rows:
        reasons.append("candidate_population_empty")
    if binding.get("candidate_population_size") != len(rows):
        reasons.append("candidate_population_size_mismatch")
    expected_source_hash = binding.get("expected_candidate_source_content_hash")
    if expected_source_hash and binding.get("candidate_source_content_hash") != expected_source_hash:
        reasons.append("candidate_source_content_hash_mismatch")
    expected_hash = candidate_selected_rows_hash(rows)
    if binding.get("candidate_selected_rows_hash") != expected_hash:
        reasons.append("candidate_selected_rows_hash_mismatch")
    ranks = [row.get("candidate_rank") for row in rows if row.get("candidate_rank") is not None]
    if not ranks:
        reasons.append("candidate_rank_missing")
    elif str(binding.get("candidate_pass_rule")) == "CandidateTop50" and (min(ranks) < 1 or max(ranks) > 50):
        reasons.append("candidate_top50_definition_mismatch")
    return {
        "status": PASS if not reasons else REVIEW_REQUIRED,
        "reason_codes": reasons,
        "expected_candidate_selected_rows_hash": expected_hash,
        "candidate_population_size": len(rows),
        "binding": binding,
    }


def evaluate_opportunity_selection_gate(
    *,
    rows: list[dict[str, Any]],
    candidate_binding: dict[str, Any],
    historical_metric_mapping: dict[str, Any],
    approved_status_semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding_validation = validate_candidate_population_binding(rows=rows, binding=candidate_binding)
    if binding_validation["status"] != PASS:
        return _result(REVIEW_REQUIRED, binding_validation["reason_codes"], {}, binding_validation)
    mapping_reasons = _mapping_reasons(historical_metric_mapping)
    if mapping_reasons:
        return _result(REVIEW_REQUIRED, mapping_reasons, {}, binding_validation)

    frame = pd.DataFrame(rows).copy()
    required_columns = {"target_date", "score", "realized_return", "downside_bad", "candidate_rank", "candidate_score"}
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        return _result(METRIC_UNAVAILABLE, ["missing_column:" + name for name in missing_columns], {}, binding_validation)
    metrics = _compute_metrics(frame)
    missing_families = [name for name in REQUIRED_METRIC_FAMILIES if name not in (approved_status_semantics or {})]
    if missing_families:
        return _result(REVIEW_REQUIRED, ["approved_status_semantics_missing:" + name for name in missing_families], metrics, binding_validation)
    failures = _semantic_failures(metrics, approved_status_semantics or {})
    if failures:
        return _result(FAIL, failures, metrics, binding_validation)
    return _result(PASS, [], metrics, binding_validation)


def _compute_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    sorted_frame = frame.sort_values(["target_date", "score"], ascending=[True, False], kind="mergesort")
    candidate_average = float(frame["realized_return"].mean())
    by_topn: dict[str, Any] = {}
    for n in TOP_NS:
        topn = sorted_frame.groupby("target_date", sort=True).head(n)
        by_topn[f"top{n}"] = {
            "selected_count": int(len(topn)),
            "realized_return_mean": float(topn["realized_return"].mean()),
            "hit_rate": float((topn["realized_return"] > 0).mean()),
            "downside_rate": float(topn["downside_bad"].astype(bool).mean()),
            "rank_lift_vs_candidate_top50": float(topn["realized_return"].mean() - candidate_average),
            "ndcg": _mean_group_ndcg(topn_source=frame, n=n),
        }
    top_bucket = sorted_frame.groupby("target_date", sort=True).head(5)
    bottom_bucket = sorted_frame.groupby("target_date", sort=True).tail(5)
    spearman = float(frame["score"].corr(frame["realized_return"], method="spearman"))
    if math.isnan(spearman):
        spearman = 0.0
    return {
        "candidate_top50_average_realized_return": candidate_average,
        "topn": by_topn,
        "top_minus_bottom": float(top_bucket["realized_return"].mean() - bottom_bucket["realized_return"].mean()),
        "spearman_rank_correlation": spearman,
    }


def _mean_group_ndcg(*, topn_source: pd.DataFrame, n: int) -> float:
    values: list[float] = []
    for _, group in topn_source.groupby("target_date", sort=True):
        ordered = group.sort_values("score", ascending=False, kind="mergesort").head(n)
        ideal = group.sort_values("realized_return", ascending=False, kind="mergesort").head(n)
        dcg = _dcg(ordered["realized_return"].to_numpy(dtype=float))
        idcg = _dcg(ideal["realized_return"].to_numpy(dtype=float))
        values.append(float(dcg / idcg) if idcg > 0 else 0.0)
    return float(np.mean(values)) if values else 0.0


def _dcg(values: np.ndarray) -> float:
    gains = np.maximum(values, 0.0)
    discounts = np.log2(np.arange(2, gains.size + 2))
    return float(np.sum(gains / discounts))


def _mapping_reasons(mapping: dict[str, Any]) -> list[str]:
    names = {item.get("ag_metric") for item in mapping.get("metrics", [])}
    required = {"Top5 realized return", "Top10 realized return", "Top20 realized return", "Hit Rate", "Downside Rate", "Rank Lift", "NDCG", "Correlation", "Top-minus-bottom"}
    return ["missing_historical_metric_mapping:" + name for name in sorted(required - names)]


def _semantic_failures(metrics: dict[str, Any], semantics: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for n in TOP_NS:
        top = metrics["topn"][f"top{n}"]
        for family, metric_name in (
            ("realized_return", "realized_return_mean"),
            ("hit_rate", "hit_rate"),
            ("downside_rate", "downside_rate"),
            ("rank_lift", "rank_lift_vs_candidate_top50"),
            ("ndcg", "ndcg"),
        ):
            reason = _evaluate_value(f"top{n}_{family}", top[metric_name], semantics[family])
            if reason:
                failures.append(reason)
    for name in ("top_minus_bottom", "spearman_rank_correlation"):
        family = "spearman_rank_correlation" if name == "spearman_rank_correlation" else name
        reason = _evaluate_value(name, metrics[name], semantics[family])
        if reason:
            failures.append(reason)
    return failures


def _evaluate_value(name: str, value: float, semantic: dict[str, Any]) -> str | None:
    if semantic.get("status_policy") == "DIAGNOSTIC_ONLY":
        return None
    if "minimum" in semantic and value < float(semantic["minimum"]):
        return f"{name}_below_approved_minimum"
    if "maximum" in semantic and value > float(semantic["maximum"]):
        return f"{name}_above_approved_maximum"
    return None


def _result(status: str, reasons: list[str], metrics: dict[str, Any], binding_validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": GATE_ID,
        "status": status,
        "reason_codes": reasons,
        "generation_eligibility": status == PASS,
        "runtime_eligibility": False,
        "metrics": metrics,
        "candidate_population_binding_validation": binding_validation,
    }
