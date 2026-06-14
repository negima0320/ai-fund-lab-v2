from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.end_to_end.random_yearly_smoke_test import (
    DEFAULT_CANDIDATE_PATH,
    DEFAULT_LABEL_PATH,
    DEFAULT_OPPORTUNITY_DATASET_PATH,
    DEFAULT_OPPORTUNITY_MODEL_PATH,
    SEED,
    TARGET_YEARS,
    decide_buy,
    is_forbidden_feature,
    load_future_outcomes,
    round_float,
)
from ai_fund_lab_v2.opportunity_ai.inference import build_buy_reason, build_no_buy_reason, calculate_downside_risk_score, load_model_payload
from ai_fund_lab_v2.opportunity_ai.training import to_jsonable, transform_features

PHASE = "Phase6-K"
PHASE6K_EXPANDED_VALIDATION_PASSED = "PHASE6K_EXPANDED_VALIDATION_PASSED"
PHASE6K_EXPANDED_VALIDATION_WITH_FINDINGS = "PHASE6K_EXPANDED_VALIDATION_WITH_FINDINGS"
PHASE6K_EXPANDED_VALIDATION_FAILED = "PHASE6K_EXPANDED_VALIDATION_FAILED"

DEFAULT_OUTPUT_CSV_PATH = Path("reports/end_to_end/phase6k_expanded_random_validation.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/end_to_end/phase6k_expanded_random_validation.json")
DEFAULT_YEARLY_SUMMARY_PATH = Path("reports/end_to_end/phase6k_yearly_summary.json")
DEFAULT_TOPN_PATH = Path("reports/end_to_end/phase6k_top3_vs_top5_vs_top10.json")
DEFAULT_RISK_GUARD_PATH = Path("reports/end_to_end/phase6k_risk_guard_analysis.json")
DEFAULT_TAIL_DILUTION_PATH = Path("reports/end_to_end/phase6k_tail_dilution_analysis.json")

TOP_N_VALUES = (3, 5, 10)
TAIL_BANDS = {
    "Top1-3": (1, 3),
    "Top4-5": (4, 5),
    "Top6-10": (6, 10),
}


@dataclass(frozen=True)
class Phase6KExpandedValidationResult:
    output: pd.DataFrame
    summary: dict[str, Any]
    yearly_summary: dict[str, Any]
    topn_summary: dict[str, Any]
    risk_guard_analysis: dict[str, Any]
    tail_dilution_analysis: dict[str, Any]


def run_phase6k_expanded_random_validation(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    opportunity_model_path: Path = DEFAULT_OPPORTUNITY_MODEL_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    yearly_summary_path: Path = DEFAULT_YEARLY_SUMMARY_PATH,
    topn_path: Path = DEFAULT_TOPN_PATH,
    risk_guard_path: Path = DEFAULT_RISK_GUARD_PATH,
    tail_dilution_path: Path = DEFAULT_TAIL_DILUTION_PATH,
    target_years: tuple[int, ...] = TARGET_YEARS,
    dates_per_year: int = 5,
    seed: int = SEED,
    created_at: str | None = None,
) -> Phase6KExpandedValidationResult:
    created_at = created_at or now_utc()
    candidate = pd.read_parquet(candidate_path)
    opportunity_dataset = pd.read_parquet(opportunity_dataset_path)
    model_payload = load_model_payload(opportunity_model_path)
    selected_dates, skipped_years = select_random_dates(
        opportunity_dataset,
        target_years=target_years,
        dates_per_year=dates_per_year,
        seed=seed,
    )
    flat_dates = [date for dates in selected_dates.values() for date in dates]
    candidate_subset = subset_for_dates(candidate, flat_dates)
    opportunity_subset = subset_for_dates(opportunity_dataset, flat_dates)
    scored = score_opportunity_top10(opportunity_subset, model_payload=model_payload, created_at=created_at)
    labels = load_future_outcomes(label_path, scored[["target_date", "code"]])
    output = build_validation_output(scored=scored, labels=labels)
    yearly_summary = build_yearly_summary(output=output, candidate_subset=candidate_subset, selected_dates=selected_dates)
    topn_summary = build_topn_summary(output)
    risk_guard_analysis = build_risk_guard_analysis(output)
    tail_dilution_analysis = build_tail_dilution_analysis(output)
    audit = build_audit(model_payload)
    completion_status = decide_completion_status(
        topn_summary=topn_summary,
        risk_guard_analysis=risk_guard_analysis,
        tail_dilution_analysis=tail_dilution_analysis,
        audit=audit,
    )
    summary = {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": completion_status,
        "seed": seed,
        "dates_per_year": dates_per_year,
        "target_years": list(target_years),
        "selected_target_dates": {str(year): dates for year, dates in selected_dates.items()},
        "skipped_years": {str(year): reason for year, reason in skipped_years.items()},
        "row_count": int(len(output)),
        "candidate_count": int(len(candidate_subset)),
        "top10_row_count": int(len(output)),
        "candidate_source": "precomputed Phase4 historical Candidate Top50 artifact",
        "opportunity_source": "Phase5 formal Opportunity model re-scoring",
        "future_outcome_source": "Phase4 long-history label artifact; evaluation only",
        "yearly_summary": yearly_summary,
        "top3_vs_top5_vs_top10": topn_summary,
        "risk_guard_analysis": risk_guard_analysis,
        "tail_dilution_analysis": tail_dilution_analysis,
        "audit": audit,
        "candidate_path": str(candidate_path),
        "opportunity_dataset_path": str(opportunity_dataset_path),
        "opportunity_model_path": str(opportunity_model_path),
        "label_path": str(label_path),
    }
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_csv_path, index=False)
    write_json(output_json_path, {"phase": PHASE, "created_at": created_at, "summary": summary, "rows": output.to_dict("records")})
    write_json(yearly_summary_path, yearly_summary)
    write_json(topn_path, topn_summary)
    write_json(risk_guard_path, risk_guard_analysis)
    write_json(tail_dilution_path, tail_dilution_analysis)
    return Phase6KExpandedValidationResult(
        output=output,
        summary=summary,
        yearly_summary=yearly_summary,
        topn_summary=topn_summary,
        risk_guard_analysis=risk_guard_analysis,
        tail_dilution_analysis=tail_dilution_analysis,
    )


def select_random_dates(
    dataset: pd.DataFrame,
    *,
    target_years: tuple[int, ...],
    dates_per_year: int,
    seed: int,
) -> tuple[dict[int, list[str]], dict[int, str]]:
    rng = random.Random(seed)
    frame = dataset.copy()
    frame["target_date"] = frame["target_date"].astype(str)
    selected: dict[int, list[str]] = {}
    skipped: dict[int, str] = {}
    for year in target_years:
        year_dates = sorted(frame[frame["target_date"].str.startswith(str(year))]["target_date"].dropna().unique().tolist())
        eligible = []
        for target_date in year_dates:
            part = frame[frame["target_date"] == target_date]
            if len(part) >= 50 and part["label__future_return_20d"].notna().any() and part["label__future_max_return_20d"].notna().any():
                eligible.append(target_date)
        if len(eligible) < dates_per_year:
            if not eligible:
                skipped[year] = "no eligible target_date with Candidate Top50 and future outcome labels"
                continue
            skipped[year] = f"only {len(eligible)} eligible dates; selected all available"
            selected[year] = eligible
            continue
        selected[year] = sorted(rng.sample(eligible, dates_per_year))
    return selected, skipped


def subset_for_dates(frame: pd.DataFrame, dates: list[str]) -> pd.DataFrame:
    out = frame.copy()
    out["target_date"] = out["target_date"].astype(str)
    out["code"] = out["code"].astype(str)
    return out[out["target_date"].isin(set(dates))].copy()


def score_opportunity_top10(dataset: pd.DataFrame, *, model_payload: dict[str, Any], created_at: str) -> pd.DataFrame:
    frame = dataset.copy()
    feature_columns = list(model_payload.get("feature_columns") or [])
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    matrix = transform_features(frame, feature_columns, model_payload.get("preprocessing", {}))
    frame["expected_edge_score"] = np.asarray(model_payload["model"].predict(matrix), dtype=float)
    frame["downside_risk_score"] = calculate_downside_risk_score(frame)
    frame["candidate_score"] = pd.to_numeric(frame.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
    frame["candidate_rank"] = pd.to_numeric(frame.get("feature__candidate_rank", 999), errors="coerce").fillna(999).astype(int)
    frame = frame.sort_values(["target_date", "expected_edge_score", "code"], ascending=[True, False, True]).copy()
    frame["buy_rank"] = frame.groupby("target_date")["expected_edge_score"].rank(method="first", ascending=False).astype(int)
    frame["is_top5"] = frame["buy_rank"] <= 5
    frame["is_top10"] = frame["buy_rank"] <= 10
    frame["is_top20"] = frame["buy_rank"] <= 20
    frame["buy_reason"] = frame.apply(build_buy_reason, axis=1)
    frame["no_buy_reason"] = frame.apply(build_no_buy_reason, axis=1)
    frame["risk_guard_status"] = np.where(frame["downside_risk_score"] >= 0.75, "bad", "ok")
    frame["buy_decision"] = frame.apply(decide_buy, axis=1)
    frame["created_at"] = created_at
    return frame[frame["buy_rank"] <= 10].copy()


def build_validation_output(*, scored: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    output = scored.merge(labels, on=["target_date", "code"], how="left", validate="one_to_one")
    output["year"] = output["target_date"].astype(str).str[:4].astype(int)
    output = output.rename(
        columns={
            "future_return_5d": "future_return_5bd",
            "future_return_10d": "future_return_10bd",
            "future_return_20d": "future_return_20bd",
            "future_max_return_20d": "future_max_return_20bd",
            "future_max_drawdown_20d": "future_min_return_20bd",
        }
    )
    columns = [
        "year",
        "target_date",
        "code",
        "candidate_rank",
        "candidate_score",
        "buy_rank",
        "expected_edge_score",
        "downside_risk_score",
        "risk_guard_status",
        "buy_decision",
        "buy_reason",
        "no_buy_reason",
        "future_return_5bd",
        "future_return_10bd",
        "future_return_20bd",
        "future_max_return_20bd",
        "future_min_return_20bd",
    ]
    return output[columns].sort_values(["year", "target_date", "buy_rank", "code"]).reset_index(drop=True)


def build_yearly_summary(*, output: pd.DataFrame, candidate_subset: pd.DataFrame, selected_dates: dict[int, list[str]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for year, dates in selected_dates.items():
        year_output = output[output["year"] == year]
        year_candidates = candidate_subset[candidate_subset["target_date"].astype(str).isin(dates)]
        summary[str(year)] = {
            "selected_target_dates": dates,
            "candidate_count": int(len(year_candidates)),
            "top10_count": int(len(year_output)),
            "top5_count": int((year_output["buy_rank"] <= 5).sum()),
            **metric_block(year_output[year_output["buy_rank"] <= 5]),
        }
    return summary


def build_topn_summary(output: pd.DataFrame) -> dict[str, Any]:
    return {f"Top{top_n}": metric_block(output[output["buy_rank"] <= top_n]) for top_n in TOP_N_VALUES}


def build_risk_guard_analysis(output: pd.DataFrame) -> dict[str, Any]:
    buy = output[output["buy_decision"] == "BUY_CANDIDATE"]
    skip = output[output["buy_decision"] != "BUY_CANDIDATE"]
    return {
        "BUY_CANDIDATE": {"count": int(len(buy)), **metric_block(buy)},
        "SKIP": {"count": int(len(skip)), **metric_block(skip)},
        "skip_decision_counts": {str(key): int(value) for key, value in skip["buy_decision"].value_counts().items()},
    }


def build_tail_dilution_analysis(output: pd.DataFrame) -> dict[str, Any]:
    analysis: dict[str, Any] = {}
    for name, (start, end) in TAIL_BANDS.items():
        band = output[(output["buy_rank"] >= start) & (output["buy_rank"] <= end)]
        analysis[name] = metric_block(band)
    top13 = analysis["Top1-3"]
    top610 = analysis["Top6-10"]
    analysis["tail_dilution_confirmed"] = bool(
        top610["mean_future_return_20bd"] < top13["mean_future_return_20bd"]
        or top610["positive_return_rate"] < top13["positive_return_rate"]
    )
    return analysis


def metric_block(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "row_count": 0,
            "mean_future_return_5bd": 0.0,
            "mean_future_return_10bd": 0.0,
            "mean_future_return_20bd": 0.0,
            "mean_future_max_return_20bd": 0.0,
            "mean_future_min_return_20bd": 0.0,
            "positive_return_count": 0,
            "positive_return_rate": 0.0,
        }
    positive_count = int((frame["future_return_20bd"] > 0).sum())
    return {
        "row_count": int(len(frame)),
        "mean_future_return_5bd": round_float(frame["future_return_5bd"].mean()),
        "mean_future_return_10bd": round_float(frame["future_return_10bd"].mean()),
        "mean_future_return_20bd": round_float(frame["future_return_20bd"].mean()),
        "mean_future_max_return_20bd": round_float(frame["future_max_return_20bd"].mean()),
        "mean_future_min_return_20bd": round_float(frame["future_min_return_20bd"].mean()),
        "positive_return_count": positive_count,
        "positive_return_rate": round_float(positive_count / len(frame)),
    }


def build_audit(model_payload: dict[str, Any]) -> dict[str, Any]:
    feature_columns = list(model_payload.get("feature_columns") or [])
    forbidden_columns = [column for column in feature_columns if is_forbidden_feature(column.replace("feature__", "", 1))]
    future_columns = [column for column in feature_columns if "future" in column.lower()]
    audit_ok = not forbidden_columns and not future_columns
    return {
        "forbidden_feature_audit_status": "OK" if not forbidden_columns else "ERROR",
        "forbidden_feature_columns": forbidden_columns,
        "forbidden_feature_column_count": len(forbidden_columns),
        "future_columns_not_used_for_inference": not future_columns,
        "future_feature_columns": future_columns,
        "leakage_audit_status": "OK" if audit_ok else "ERROR",
        "broker_api_executed": False,
        "order_executed": False,
        "paper_trading_executed": False,
        "capital_allocation_executed": False,
        "live_order_executed": False,
        "real_account_updated": False,
        "full_backtest_executed": False,
    }


def decide_completion_status(
    *,
    topn_summary: dict[str, Any],
    risk_guard_analysis: dict[str, Any],
    tail_dilution_analysis: dict[str, Any],
    audit: dict[str, Any],
) -> str:
    if audit["leakage_audit_status"] != "OK":
        return PHASE6K_EXPANDED_VALIDATION_FAILED
    top3 = topn_summary["Top3"]
    top5 = topn_summary["Top5"]
    top10 = topn_summary["Top10"]
    top3_or_top5_reasonable = (
        top5["mean_future_return_20bd"] >= top10["mean_future_return_20bd"]
        or top3["mean_future_return_20bd"] >= top10["mean_future_return_20bd"]
        or top5["positive_return_rate"] >= top10["positive_return_rate"]
    )
    risk_guard_effective = (
        risk_guard_analysis["BUY_CANDIDATE"]["mean_future_return_20bd"]
        >= risk_guard_analysis["SKIP"]["mean_future_return_20bd"]
    )
    if top3_or_top5_reasonable and tail_dilution_analysis.get("tail_dilution_confirmed") and risk_guard_effective:
        return PHASE6K_EXPANDED_VALIDATION_PASSED
    if top3_or_top5_reasonable or tail_dilution_analysis.get("tail_dilution_confirmed") or risk_guard_effective:
        return PHASE6K_EXPANDED_VALIDATION_WITH_FINDINGS
    return PHASE6K_EXPANDED_VALIDATION_FAILED


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
