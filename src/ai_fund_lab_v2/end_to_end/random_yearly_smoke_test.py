from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.inference import (
    build_buy_reason,
    build_no_buy_reason,
    calculate_downside_risk_score,
    load_model_payload,
)
from ai_fund_lab_v2.opportunity_ai.training import FORBIDDEN_FEATURE_PREFIXES, FORBIDDEN_FEATURE_TERMS, to_jsonable, transform_features

PHASE = "Phase6-J"
PHASE6J_E2E_SMOKE_TEST_PASSED = "PHASE6J_E2E_SMOKE_TEST_PASSED"
PHASE6J_E2E_SMOKE_TEST_PASSED_WITH_LIMITATIONS = "PHASE6J_E2E_SMOKE_TEST_PASSED_WITH_LIMITATIONS"
PHASE6J_E2E_SMOKE_TEST_FAILED = "PHASE6J_E2E_SMOKE_TEST_FAILED"

DEFAULT_CANDIDATE_PATH = Path("reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet")
DEFAULT_OPPORTUNITY_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_OPPORTUNITY_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_LABEL_PATH = Path(".runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet")

DEFAULT_OUTPUT_CSV_PATH = Path("reports/end_to_end/phase6j_random_yearly_e2e_smoke_test.csv")
DEFAULT_OUTPUT_JSON_PATH = Path("reports/end_to_end/phase6j_random_yearly_e2e_smoke_test.json")
DEFAULT_SUMMARY_PATH = Path("reports/end_to_end/phase6j_random_yearly_e2e_summary.json")

TARGET_YEARS = (2021, 2022, 2023, 2024, 2025, 2026)
SEED = 42

OUTPUT_COLUMNS = (
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
)


@dataclass(frozen=True)
class Phase6JSmokeResult:
    output: pd.DataFrame
    records: dict[str, Any]
    summary: dict[str, Any]


def run_phase6j_random_yearly_e2e_smoke_test(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    opportunity_dataset_path: Path = DEFAULT_OPPORTUNITY_DATASET_PATH,
    opportunity_model_path: Path = DEFAULT_OPPORTUNITY_MODEL_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    output_csv_path: Path = DEFAULT_OUTPUT_CSV_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    target_years: tuple[int, ...] = TARGET_YEARS,
    seed: int = SEED,
    created_at: str | None = None,
) -> Phase6JSmokeResult:
    created_at = created_at or now_utc()
    candidate = pd.read_parquet(candidate_path)
    opportunity_dataset = pd.read_parquet(opportunity_dataset_path)
    model_payload = load_model_payload(opportunity_model_path)
    selected_dates, skipped_years = select_random_target_dates(opportunity_dataset, target_years=target_years, seed=seed)
    candidate_subset = subset_for_dates(candidate, selected_dates)
    opportunity_subset = subset_for_dates(opportunity_dataset, selected_dates)
    opportunity_output = run_opportunity_top5(opportunity_subset, model_payload=model_payload, created_at=created_at)
    labels = load_future_outcomes(label_path, opportunity_output[["target_date", "code"]])
    output = build_smoke_output(opportunity_output=opportunity_output, labels=labels)
    summary = build_summary(
        output=output,
        candidate_subset=candidate_subset,
        selected_dates=selected_dates,
        skipped_years=skipped_years,
        model_payload=model_payload,
        created_at=created_at,
        seed=seed,
        candidate_path=candidate_path,
        opportunity_dataset_path=opportunity_dataset_path,
        opportunity_model_path=opportunity_model_path,
        label_path=label_path,
    )
    records = {
        "phase": PHASE,
        "created_at": created_at,
        "rows": output.to_dict("records"),
        "summary_path": str(summary_path),
        "output_csv_path": str(output_csv_path),
    }
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_csv_path, index=False)
    write_json(output_json_path, records)
    write_json(summary_path, summary)
    return Phase6JSmokeResult(output=output, records=records, summary=summary)


def select_random_target_dates(dataset: pd.DataFrame, *, target_years: tuple[int, ...], seed: int) -> tuple[dict[int, str], dict[int, str]]:
    rng = random.Random(seed)
    frame = dataset.copy()
    frame["target_date"] = frame["target_date"].astype(str)
    selected: dict[int, str] = {}
    skipped: dict[int, str] = {}
    for year in target_years:
        year_dates = sorted(frame[frame["target_date"].str.startswith(str(year))]["target_date"].dropna().unique().tolist())
        eligible = []
        for target_date in year_dates:
            part = frame[frame["target_date"] == target_date]
            if len(part) >= 50 and part["label__future_return_20d"].notna().any() and part["label__future_max_return_20d"].notna().any():
                eligible.append(target_date)
        if not eligible:
            skipped[year] = "no eligible target_date with Candidate Top50 and future outcome labels"
            continue
        selected[year] = rng.choice(eligible)
    return selected, skipped


def subset_for_dates(frame: pd.DataFrame, selected_dates: dict[int, str]) -> pd.DataFrame:
    out = frame.copy()
    out["target_date"] = out["target_date"].astype(str)
    dates = set(selected_dates.values())
    out = out[out["target_date"].isin(dates)].copy()
    out["code"] = out["code"].astype(str)
    return out


def run_opportunity_top5(dataset: pd.DataFrame, *, model_payload: dict[str, Any], created_at: str) -> pd.DataFrame:
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
    frame["created_at"] = created_at
    return frame[frame["buy_rank"] <= 5].copy()


def load_future_outcomes(label_path: Path, keys: pd.DataFrame) -> pd.DataFrame:
    target_dates = sorted(keys["target_date"].astype(str).unique().tolist())
    codes = sorted(keys["code"].astype(str).unique().tolist())
    try:
        labels = pd.read_parquet(label_path, filters=[("target_date", "in", target_dates), ("code", "in", codes)])
    except Exception:
        labels = pd.read_parquet(label_path)
        labels = labels[labels["target_date"].astype(str).isin(target_dates) & labels["code"].astype(str).isin(codes)].copy()
    labels["target_date"] = labels["target_date"].astype(str)
    labels["code"] = labels["code"].astype(str)
    return labels[
        [
            "target_date",
            "code",
            "future_return_5d",
            "future_return_10d",
            "future_return_20d",
            "future_max_return_20d",
            "future_max_drawdown_20d",
        ]
    ].drop_duplicates(["target_date", "code"], keep="first")


def build_smoke_output(*, opportunity_output: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    output = opportunity_output.merge(labels, on=["target_date", "code"], how="left", validate="one_to_one")
    output["year"] = output["target_date"].astype(str).str[:4].astype(int)
    output["buy_decision"] = output.apply(decide_buy, axis=1)
    output = output.rename(
        columns={
            "future_return_5d": "future_return_5bd",
            "future_return_10d": "future_return_10bd",
            "future_return_20d": "future_return_20bd",
            "future_max_return_20d": "future_max_return_20bd",
            "future_max_drawdown_20d": "future_min_return_20bd",
        }
    )
    for column in OUTPUT_COLUMNS:
        if column not in output.columns:
            output[column] = np.nan
    return output[list(OUTPUT_COLUMNS)].sort_values(["year", "buy_rank", "code"]).reset_index(drop=True)


def decide_buy(row: pd.Series) -> str:
    if pd.isna(row.get("expected_edge_score")) or pd.isna(row.get("downside_risk_score")):
        return "SKIP_MISSING_SIGNAL"
    if str(row.get("risk_guard_status", "")).lower() == "bad":
        return "SKIP_RISK_GUARD"
    return "BUY_CANDIDATE"


def build_summary(
    *,
    output: pd.DataFrame,
    candidate_subset: pd.DataFrame,
    selected_dates: dict[int, str],
    skipped_years: dict[int, str],
    model_payload: dict[str, Any],
    created_at: str,
    seed: int,
    candidate_path: Path,
    opportunity_dataset_path: Path,
    opportunity_model_path: Path,
    label_path: Path,
) -> dict[str, Any]:
    by_year = {}
    for year, target_date in selected_dates.items():
        year_output = output[output["year"] == year]
        year_candidates = candidate_subset[candidate_subset["target_date"].astype(str) == target_date]
        by_year[str(year)] = aggregate_block(year_output, candidate_count=len(year_candidates), target_date=target_date)
    overall = aggregate_block(output, candidate_count=len(candidate_subset), target_date="ALL")
    feature_columns = list(model_payload.get("feature_columns") or [])
    forbidden_columns = [column for column in feature_columns if is_forbidden_feature(column.replace("feature__", "", 1))]
    future_in_feature_columns = [column for column in feature_columns if "future" in column.lower()]
    audit_ok = not forbidden_columns and not future_in_feature_columns
    completion_status = (
        PHASE6J_E2E_SMOKE_TEST_PASSED
        if audit_ok and output["target_date"].nunique() == len(TARGET_YEARS) and not skipped_years
        else PHASE6J_E2E_SMOKE_TEST_PASSED_WITH_LIMITATIONS
        if audit_ok and not output.empty
        else PHASE6J_E2E_SMOKE_TEST_FAILED
    )
    return {
        "phase": PHASE,
        "created_at": created_at,
        "completion_status": completion_status,
        "seed": seed,
        "target_years": list(TARGET_YEARS),
        "selected_target_dates": {str(year): date for year, date in selected_dates.items()},
        "skipped_years": {str(year): reason for year, reason in skipped_years.items()},
        "candidate_source": "precomputed Phase4 historical Candidate Top50 artifact",
        "opportunity_source": "Phase5 formal Opportunity model re-scoring",
        "future_outcome_source": "Phase4 long-history label artifact; evaluation only",
        "candidate_path": str(candidate_path),
        "opportunity_dataset_path": str(opportunity_dataset_path),
        "opportunity_model_path": str(opportunity_model_path),
        "label_path": str(label_path),
        "yearly_summary": by_year,
        "overall_summary": overall,
        "audit": {
            "forbidden_feature_audit_status": "OK" if not forbidden_columns else "ERROR",
            "forbidden_feature_columns": forbidden_columns,
            "forbidden_feature_column_count": len(forbidden_columns),
            "future_columns_not_used_for_inference": not future_in_feature_columns,
            "future_feature_columns": future_in_feature_columns,
            "leakage_audit_status": "OK" if audit_ok else "ERROR",
            "broker_api_executed": False,
            "order_executed": False,
            "paper_trading_executed": False,
            "capital_allocation_executed": False,
            "live_order_executed": False,
            "real_account_updated": False,
            "full_backtest_executed": False,
        },
    }


def aggregate_block(frame: pd.DataFrame, *, candidate_count: int, target_date: str) -> dict[str, Any]:
    if frame.empty:
        return {
            "target_date": target_date,
            "candidate_count": int(candidate_count),
            "opportunity_top5_count": 0,
            "buy_candidate_count": 0,
            "skip_count": 0,
            "mean_future_return_5bd": 0.0,
            "mean_future_return_10bd": 0.0,
            "mean_future_return_20bd": 0.0,
            "mean_future_max_return_20bd": 0.0,
            "mean_future_min_return_20bd": 0.0,
            "positive_return_20bd_count": 0,
        }
    return {
        "target_date": target_date,
        "candidate_count": int(candidate_count),
        "opportunity_top5_count": int(len(frame)),
        "buy_candidate_count": int((frame["buy_decision"] == "BUY_CANDIDATE").sum()),
        "skip_count": int((frame["buy_decision"] != "BUY_CANDIDATE").sum()),
        "mean_future_return_5bd": round_float(frame["future_return_5bd"].mean()),
        "mean_future_return_10bd": round_float(frame["future_return_10bd"].mean()),
        "mean_future_return_20bd": round_float(frame["future_return_20bd"].mean()),
        "mean_future_max_return_20bd": round_float(frame["future_max_return_20bd"].mean()),
        "mean_future_min_return_20bd": round_float(frame["future_min_return_20bd"].mean()),
        "positive_return_20bd_count": int((frame["future_return_20bd"] > 0).sum()),
    }


def is_forbidden_feature(name: str) -> bool:
    if name.startswith(FORBIDDEN_FEATURE_PREFIXES):
        return True
    return any(term in name for term in FORBIDDEN_FEATURE_TERMS)


def round_float(value: Any) -> float:
    if pd.isna(value) or not np.isfinite(float(value)):
        return 0.0
    return round(float(value), 6)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
