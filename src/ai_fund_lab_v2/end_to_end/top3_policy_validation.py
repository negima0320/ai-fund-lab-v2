from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.end_to_end.expanded_random_validation import (
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    SEED,
    TARGET_YEARS,
    build_audit,
    run_phase6k_expanded_random_validation,
    write_json,
)
from ai_fund_lab_v2.opportunity_ai.inference import load_model_payload
from ai_fund_lab_v2.end_to_end.random_yearly_smoke_test import round_float

PHASE = "Phase6-L"
PHASE6L_TOP3_POLICY_VALIDATED = "PHASE6L_TOP3_POLICY_VALIDATED"
PHASE6L_TOP3_POLICY_WITH_FINDINGS = "PHASE6L_TOP3_POLICY_WITH_FINDINGS"
PHASE6L_TOP3_POLICY_NOT_VALIDATED = "PHASE6L_TOP3_POLICY_NOT_VALIDATED"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/end_to_end/phase6l_top3_policy_validation.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/end_to_end/phase6l_top3_policy_validation.json")
DEFAULT_COMPARISON_PATH = Path("reports/end_to_end/phase6l_top3_vs_top5_vs_top10.json")
DEFAULT_YEARLY_TOP3_PATH = Path("reports/end_to_end/phase6l_yearly_top3_summary.json")
DEFAULT_RISK_POLICY_PATH = Path("reports/end_to_end/phase6l_risk_guard_policy_comparison.json")
DEFAULT_RECOMMENDATION_PATH = Path("reports/end_to_end/phase6l_policy_recommendation.json")


@dataclass(frozen=True)
class Phase6LTop3PolicyValidationResult:
    output: pd.DataFrame
    summary: dict[str, Any]
    comparison: dict[str, Any]
    yearly_top3_summary: dict[str, Any]
    risk_guard_policy_comparison: dict[str, Any]
    policy_recommendation: dict[str, Any]


def run_phase6l_top3_policy_validation(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    opportunity_model_path: Path = DEFAULT_OPPORTUNITY_MODEL_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    comparison_path: Path = DEFAULT_COMPARISON_PATH,
    yearly_top3_path: Path = DEFAULT_YEARLY_TOP3_PATH,
    risk_policy_path: Path = DEFAULT_RISK_POLICY_PATH,
    recommendation_path: Path = DEFAULT_RECOMMENDATION_PATH,
    target_years: tuple[int, ...] = TARGET_YEARS,
    dates_per_year: int = 5,
    seed: int = SEED,
    created_at: str | None = None,
) -> Phase6LTop3PolicyValidationResult:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        phase6k = run_phase6k_expanded_random_validation(
            candidate_path=candidate_path,
            opportunity_dataset_path=opportunity_dataset_path,
            opportunity_model_path=opportunity_model_path,
            label_path=label_path,
            output_csv_path=tmpdir / "phase6k.csv",
            output_json_path=tmpdir / "phase6k.json",
            yearly_summary_path=tmpdir / "phase6k_yearly.json",
            topn_path=tmpdir / "phase6k_topn.json",
            risk_guard_path=tmpdir / "phase6k_risk.json",
            tail_dilution_path=tmpdir / "phase6k_tail.json",
            target_years=target_years,
            dates_per_year=dates_per_year,
            seed=seed,
            created_at=created_at,
        )

    output = add_policy_columns(phase6k.output)
    comparison = build_rank_bucket_comparison(output)
    yearly_top3_summary = build_yearly_top3_summary(output, phase6k.summary["selected_target_dates"])
    risk_policy_comparison = build_risk_guard_policy_comparison(output)
    model_payload = load_model_payload(opportunity_model_path)
    audit = build_audit(model_payload)
    policy_recommendation = build_policy_recommendation(comparison, yearly_top3_summary, risk_policy_comparison, audit)
    completion_status = decide_completion_status(policy_recommendation, audit)
    summary = {
        "phase": PHASE,
        "created_at": phase6k.summary["created_at"],
        "completion_status": completion_status,
        "seed": seed,
        "dates_per_year": dates_per_year,
        "target_years": list(target_years),
        "selected_target_dates": phase6k.summary["selected_target_dates"],
        "skipped_years": phase6k.summary["skipped_years"],
        "row_count": int(len(output)),
        "candidate_count": int(phase6k.summary["candidate_count"]),
        "candidate_source": phase6k.summary["candidate_source"],
        "opportunity_source": phase6k.summary["opportunity_source"],
        "future_outcome_source": phase6k.summary["future_outcome_source"],
        "comparison": comparison,
        "yearly_top3_summary": yearly_top3_summary,
        "risk_guard_policy_comparison": risk_policy_comparison,
        "policy_recommendation": policy_recommendation,
        "audit": audit,
        "candidate_path": str(candidate_path),
        "opportunity_dataset_path": str(opportunity_dataset_path),
        "opportunity_model_path": str(opportunity_model_path),
        "label_path": str(label_path),
    }

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_csv_path, index=False)
    write_json(output_json_path, {"phase": PHASE, "created_at": summary["created_at"], "summary": summary, "rows": output.to_dict("records")})
    write_json(comparison_path, comparison)
    write_json(yearly_top3_path, yearly_top3_summary)
    write_json(risk_policy_path, risk_policy_comparison)
    write_json(recommendation_path, policy_recommendation)
    return Phase6LTop3PolicyValidationResult(
        output=output,
        summary=summary,
        comparison=comparison,
        yearly_top3_summary=yearly_top3_summary,
        risk_guard_policy_comparison=risk_policy_comparison,
        policy_recommendation=policy_recommendation,
    )


def add_policy_columns(output: pd.DataFrame) -> pd.DataFrame:
    frame = output.copy()
    frame["rank_bucket"] = frame["buy_rank"].map(rank_bucket)
    frame["top3_candidate"] = frame["buy_rank"] <= 3
    frame["top5_candidate"] = frame["buy_rank"] <= 5
    frame["top10_candidate"] = frame["buy_rank"] <= 10
    frame["risk_guard_policy_a"] = frame["buy_decision"].where(frame["buy_decision"] == "BUY_CANDIDATE", "SKIP")
    frame["risk_guard_policy_b"] = frame["buy_decision"].where(frame["buy_decision"] == "BUY_CANDIDATE", "LOW_PRIORITY")
    return frame.sort_values(["year", "target_date", "buy_rank", "code"]).reset_index(drop=True)


def rank_bucket(buy_rank: int) -> str:
    rank = int(buy_rank)
    if rank <= 3:
        return "Top1-3"
    if rank <= 5:
        return "Top4-5"
    return "Top6-10"


def build_rank_bucket_comparison(output: pd.DataFrame) -> dict[str, Any]:
    buckets = {
        "Top3": output[output["buy_rank"] <= 3],
        "Top5": output[output["buy_rank"] <= 5],
        "Top10": output[output["buy_rank"] <= 10],
        "Top4-5": output[(output["buy_rank"] >= 4) & (output["buy_rank"] <= 5)],
        "Top6-10": output[(output["buy_rank"] >= 6) & (output["buy_rank"] <= 10)],
    }
    comparison = {name: extended_metric_block(frame) for name, frame in buckets.items()}
    comparison["top3_advantage_confirmed"] = bool(
        comparison["Top3"]["mean_future_return_20bd"] > comparison["Top5"]["mean_future_return_20bd"]
        and comparison["Top3"]["mean_future_return_20bd"] > comparison["Top10"]["mean_future_return_20bd"]
        and comparison["Top3"]["positive_return_20bd_rate"] >= comparison["Top5"]["positive_return_20bd_rate"]
    )
    comparison["top4_5_backup_only"] = bool(
        comparison["Top4-5"]["mean_future_return_20bd"] < comparison["Top3"]["mean_future_return_20bd"]
        and comparison["Top4-5"]["positive_return_20bd_rate"] < comparison["Top3"]["positive_return_20bd_rate"]
    )
    comparison["top6_10_avoid_confirmed"] = bool(
        comparison["Top6-10"]["mean_future_return_20bd"] < comparison["Top3"]["mean_future_return_20bd"]
        and comparison["Top6-10"]["positive_return_20bd_rate"] < comparison["Top3"]["positive_return_20bd_rate"]
    )
    return comparison


def build_yearly_top3_summary(output: pd.DataFrame, selected_dates: dict[str, list[str]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    top3 = output[output["buy_rank"] <= 3]
    for year, dates in selected_dates.items():
        year_frame = top3[top3["year"] == int(year)]
        summary[str(year)] = {
            "selected_target_dates": dates,
            **extended_metric_block(year_frame),
        }
    return summary


def build_risk_guard_policy_comparison(output: pd.DataFrame) -> dict[str, Any]:
    return {
        "Top3_BUY_ONLY": policy_metric_block(output[output["buy_rank"] <= 3], include_low_priority=False),
        "Top3_WITH_LOW_PRIORITY": policy_metric_block(output[output["buy_rank"] <= 3], include_low_priority=True),
        "Top5_BUY_ONLY": policy_metric_block(output[output["buy_rank"] <= 5], include_low_priority=False),
        "Top5_WITH_LOW_PRIORITY": policy_metric_block(output[output["buy_rank"] <= 5], include_low_priority=True),
    }


def policy_metric_block(frame: pd.DataFrame, *, include_low_priority: bool) -> dict[str, Any]:
    skipped = frame[frame["buy_decision"] != "BUY_CANDIDATE"]
    included = frame if include_low_priority else frame[frame["buy_decision"] == "BUY_CANDIDATE"]
    metrics = extended_metric_block(included)
    metrics["skip_count"] = 0 if include_low_priority else int(len(skipped))
    metrics["low_priority_count"] = int(len(skipped)) if include_low_priority else 0
    metrics["included_count"] = int(len(included))
    metrics["excluded_count"] = int(len(frame) - len(included))
    return metrics


def extended_metric_block(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "count": 0,
            "mean_future_return_5bd": 0.0,
            "mean_future_return_10bd": 0.0,
            "mean_future_return_20bd": 0.0,
            "median_future_return_20bd": 0.0,
            "mean_future_max_return_20bd": 0.0,
            "mean_future_min_return_20bd": 0.0,
            "positive_return_20bd_count": 0,
            "positive_return_20bd_rate": 0.0,
            "worst_future_return_20bd": 0.0,
            "best_future_return_20bd": 0.0,
        }
    positive_count = int((frame["future_return_20bd"] > 0).sum())
    return {
        "count": int(len(frame)),
        "mean_future_return_5bd": round_float(frame["future_return_5bd"].mean()),
        "mean_future_return_10bd": round_float(frame["future_return_10bd"].mean()),
        "mean_future_return_20bd": round_float(frame["future_return_20bd"].mean()),
        "median_future_return_20bd": round_float(frame["future_return_20bd"].median()),
        "mean_future_max_return_20bd": round_float(frame["future_max_return_20bd"].mean()),
        "mean_future_min_return_20bd": round_float(frame["future_min_return_20bd"].mean()),
        "positive_return_20bd_count": positive_count,
        "positive_return_20bd_rate": round_float(positive_count / len(frame)),
        "worst_future_return_20bd": round_float(frame["future_return_20bd"].min()),
        "best_future_return_20bd": round_float(frame["future_return_20bd"].max()),
    }


def build_policy_recommendation(
    comparison: dict[str, Any],
    yearly_top3_summary: dict[str, Any],
    risk_policy_comparison: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    top3 = comparison["Top3"]
    top5 = comparison["Top5"]
    top10 = comparison["Top10"]
    top4_5 = comparison["Top4-5"]
    top6_10 = comparison["Top6-10"]
    top3_positive_years = sum(1 for item in yearly_top3_summary.values() if item["mean_future_return_20bd"] > 0)
    top3_weak_years = [year for year, item in yearly_top3_summary.items() if item["mean_future_return_20bd"] <= 0]
    top3_skip = risk_policy_comparison["Top3_BUY_ONLY"]
    top3_low = risk_policy_comparison["Top3_WITH_LOW_PRIORITY"]
    top5_skip = risk_policy_comparison["Top5_BUY_ONLY"]
    top5_low = risk_policy_comparison["Top5_WITH_LOW_PRIORITY"]
    low_priority_has_upside = (
        top3_low["mean_future_max_return_20bd"] >= top3_skip["mean_future_max_return_20bd"]
        or top5_low["mean_future_max_return_20bd"] >= top5_skip["mean_future_max_return_20bd"]
    )
    low_priority_has_cost = (
        top3_low["mean_future_min_return_20bd"] < top3_skip["mean_future_min_return_20bd"]
        or top5_low["mean_future_min_return_20bd"] < top5_skip["mean_future_min_return_20bd"]
    )
    return {
        "primary_buy_target": "Top3",
        "backup_watchlist": "Top4-5",
        "avoid_or_no_buy": "Top6-10",
        "risk_guard_bad_policy": "LOW_PRIORITY_REVIEW",
        "top3_advantage_confirmed": comparison["top3_advantage_confirmed"],
        "top4_5_backup_only": comparison["top4_5_backup_only"],
        "top6_10_avoid_confirmed": comparison["top6_10_avoid_confirmed"],
        "top3_positive_year_count": top3_positive_years,
        "top3_weak_years": top3_weak_years,
        "risk_guard_low_priority_has_upside": bool(low_priority_has_upside),
        "risk_guard_low_priority_has_downside_cost": bool(low_priority_has_cost),
        "recommended_policy": (
            "Use Top3 as primary buy target. Treat Top4-5 as backup watchlist. Exclude Top6-10 from normal buy candidates. "
            "Treat risk_guard bad as LOW_PRIORITY_REVIEW rather than automatic buy; require additional review because upside outliers exist but downside cost remains."
        ),
        "evidence": {
            "top3_mean_future_return_20bd": top3["mean_future_return_20bd"],
            "top5_mean_future_return_20bd": top5["mean_future_return_20bd"],
            "top10_mean_future_return_20bd": top10["mean_future_return_20bd"],
            "top4_5_mean_future_return_20bd": top4_5["mean_future_return_20bd"],
            "top6_10_mean_future_return_20bd": top6_10["mean_future_return_20bd"],
            "audit_status": audit["leakage_audit_status"],
        },
    }


def decide_completion_status(policy_recommendation: dict[str, Any], audit: dict[str, Any]) -> str:
    if audit["leakage_audit_status"] != "OK":
        return PHASE6L_TOP3_POLICY_NOT_VALIDATED
    if policy_recommendation["top3_advantage_confirmed"] and not policy_recommendation["top3_weak_years"]:
        return PHASE6L_TOP3_POLICY_VALIDATED
    if policy_recommendation["top3_advantage_confirmed"]:
        return PHASE6L_TOP3_POLICY_WITH_FINDINGS
    return PHASE6L_TOP3_POLICY_NOT_VALIDATED
