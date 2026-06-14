from __future__ import annotations

import json
import math
import pickle
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.opportunity_ai.training import to_jsonable, transform_features

PHASE = "Phase5-O"
DEFAULT_CANDIDATE_PATH = Path("reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet")
DEFAULT_DATASET_PATH = Path("reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet")
DEFAULT_LABEL_PATH = Path(".runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet")
DEFAULT_MODEL_PATH = Path("reports/opportunity_ai/phase5i/models/opportunity_model.pkl")
DEFAULT_OUTPUT_DIR = Path("reports/opportunity_ai/phase5o")

JSON_FILENAME = "random_date_outcome_check.json"
BY_DATE_FILENAME = "random_date_outcome_by_date.csv"
BY_STOCK_FILENAME = "random_date_outcome_by_stock.csv"
DEFAULT_DOC_PATH = Path("docs/phase_reports/phase5o_random_date_opportunity_outcome_check.md")

DEFAULT_YEARS = (2021, 2022, 2023, 2024, 2025)
OUTCOME_COLUMNS = (
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_max_return_20d",
    "future_max_drawdown_20d",
)
FORBIDDEN_FEATURE_TERMS = (
    "future_return_",
    "future_max_return_",
    "future_max_drawdown_",
    "downside_bad_",
    "top_decile_",
    "trade_result",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
)


@dataclass(frozen=True)
class RandomDateOutcomeResult:
    summary: dict[str, Any]
    by_date: pd.DataFrame
    by_stock: pd.DataFrame


def run_random_date_outcome_check(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    label_path: Path = DEFAULT_LABEL_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    doc_path: Path = DEFAULT_DOC_PATH,
    years: list[int] | tuple[int, ...] = DEFAULT_YEARS,
    samples_per_year: int = 1,
    top_n: int = 5,
    seed: int = 42,
    created_at: str | None = None,
) -> RandomDateOutcomeResult:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / JSON_FILENAME
    by_date_path = output_dir / BY_DATE_FILENAME
    by_stock_path = output_dir / BY_STOCK_FILENAME

    candidate = pd.read_parquet(candidate_path)
    dataset = pd.read_parquet(dataset_path)
    labels = pd.read_parquet(label_path)
    model_payload = load_model_payload(model_path)
    feature_columns = list(model_payload.get("feature_columns") or sorted(c for c in dataset.columns if str(c).startswith("feature__")))
    audit = leakage_audit(feature_columns)

    eligible_dates = eligible_target_dates(candidate, labels, years=years)
    sampled_dates = sample_target_dates(eligible_dates, years=years, samples_per_year=samples_per_year, seed=seed)
    scored = score_dataset_for_dates(dataset, model_payload, feature_columns, sampled_dates)
    outcome_frame = attach_outcomes(scored, labels)
    by_stock = build_by_stock(outcome_frame, top_n=top_n)
    by_date = build_by_date(by_stock, top_n=top_n)
    comparisons = build_comparisons(by_date)
    summary = build_summary(
        created_at=created_at,
        seed=seed,
        years=list(years),
        samples_per_year=samples_per_year,
        top_n=top_n,
        sampled_dates=sampled_dates,
        eligible_dates=eligible_dates,
        json_path=json_path,
        by_date_path=by_date_path,
        by_stock_path=by_stock_path,
        doc_path=doc_path,
        feature_columns=feature_columns,
        audit=audit,
        by_date=by_date,
        by_stock=by_stock,
        comparisons=comparisons,
    )
    write_json(json_path, summary)
    by_date.to_csv(by_date_path, index=False)
    by_stock.to_csv(by_stock_path, index=False)
    write_markdown_report(doc_path, summary, by_date, by_stock)
    return RandomDateOutcomeResult(summary=summary, by_date=by_date, by_stock=by_stock)


def eligible_target_dates(candidate: pd.DataFrame, labels: pd.DataFrame, *, years: list[int] | tuple[int, ...]) -> dict[int, list[str]]:
    candidate_dates = set(candidate["target_date"].astype(str).unique())
    label_ok = labels.dropna(subset=list(OUTCOME_COLUMNS)).copy()
    label_dates = set(label_ok["target_date"].astype(str).unique())
    available = sorted(candidate_dates & label_dates)
    result: dict[int, list[str]] = {}
    for year in years:
        result[int(year)] = [date for date in available if str(date).startswith(f"{int(year)}-")]
    return result


def sample_target_dates(
    eligible_dates: dict[int, list[str]],
    *,
    years: list[int] | tuple[int, ...],
    samples_per_year: int,
    seed: int,
) -> list[str]:
    rng = random.Random(seed)
    sampled: list[str] = []
    for year in years:
        dates = sorted(eligible_dates.get(int(year), []))
        if len(dates) < samples_per_year:
            raise ValueError(f"Not enough eligible target dates for {year}: required={samples_per_year}, available={len(dates)}")
        sampled.extend(sorted(rng.sample(dates, samples_per_year)))
    return sampled


def score_dataset_for_dates(
    dataset: pd.DataFrame,
    model_payload: dict[str, Any],
    feature_columns: list[str],
    target_dates: list[str],
) -> pd.DataFrame:
    frame = dataset[dataset["target_date"].astype(str).isin(set(target_dates))].copy()
    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = np.nan
    matrix = transform_features(frame, feature_columns, model_payload.get("preprocessing", {}))
    frame["expected_edge_score"] = np.asarray(model_payload["model"].predict(matrix), dtype=float)
    frame["candidate_score"] = pd.to_numeric(frame.get("feature__candidate_score", 0.0), errors="coerce").fillna(0.0)
    frame["candidate_rank"] = pd.to_numeric(frame.get("feature__candidate_rank", 999999), errors="coerce").fillna(999999).astype(int)
    frame["buy_rank"] = (
        frame.sort_values(["target_date", "expected_edge_score", "code"], ascending=[True, False, True])
        .groupby("target_date")
        .cumcount()
        + 1
    )
    frame["candidate_score_rank"] = (
        frame.sort_values(["target_date", "candidate_score", "code"], ascending=[True, False, True])
        .groupby("target_date")
        .cumcount()
        + 1
    )
    return frame


def attach_outcomes(scored: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    label_columns = ["target_date", "code", *OUTCOME_COLUMNS]
    merged = scored.merge(labels[label_columns], on=["target_date", "code"], how="inner", validate="one_to_one")
    merged["return_5bd"] = pd.to_numeric(merged["future_return_5d"], errors="coerce")
    merged["return_10bd"] = pd.to_numeric(merged["future_return_10d"], errors="coerce")
    merged["return_20bd"] = pd.to_numeric(merged["future_return_20d"], errors="coerce")
    merged["positive_5bd"] = merged["return_5bd"] > 0
    merged["positive_10bd"] = merged["return_10bd"] > 0
    merged["positive_20bd"] = merged["return_20bd"] > 0
    merged["max_return_20bd"] = pd.to_numeric(merged["future_max_return_20d"], errors="coerce")
    merged["max_drawdown_20bd"] = pd.to_numeric(merged["future_max_drawdown_20d"], errors="coerce")
    return merged


def build_by_stock(outcome_frame: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    groups: list[pd.DataFrame] = []
    candidate = outcome_frame.copy()
    candidate["selection_group"] = "CandidateTop50"
    groups.append(candidate)
    candidate_score = outcome_frame[outcome_frame["candidate_score_rank"] <= top_n].copy()
    candidate_score["selection_group"] = "CandidateScoreTop5"
    groups.append(candidate_score)
    opportunity = outcome_frame[outcome_frame["buy_rank"] <= top_n].copy()
    opportunity["selection_group"] = "OpportunityTop5"
    groups.append(opportunity)
    combined = pd.concat(groups, ignore_index=True)
    columns = [
        "target_date",
        "selection_group",
        "code",
        "buy_rank",
        "candidate_rank",
        "expected_edge_score",
        "candidate_score",
        "return_5bd",
        "return_10bd",
        "return_20bd",
        "positive_5bd",
        "positive_10bd",
        "positive_20bd",
        "max_return_20bd",
        "max_drawdown_20bd",
    ]
    return combined[columns].sort_values(["target_date", "selection_group", "buy_rank", "candidate_rank", "code"]).reset_index(drop=True)


def build_by_date(by_stock: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (target_date, group), frame in by_stock.groupby(["target_date", "selection_group"], sort=True):
        rows.append(
            {
                "target_date": str(target_date),
                "selection_group": str(group),
                "selected_count": int(len(frame)),
                "mean_return_5bd": round_float(frame["return_5bd"].mean()),
                "mean_return_10bd": round_float(frame["return_10bd"].mean()),
                "mean_return_20bd": round_float(frame["return_20bd"].mean()),
                "win_rate_5bd": round_float(frame["positive_5bd"].mean()),
                "win_rate_10bd": round_float(frame["positive_10bd"].mean()),
                "win_rate_20bd": round_float(frame["positive_20bd"].mean()),
                "positive_count_5bd": int(frame["positive_5bd"].sum()),
                "positive_count_10bd": int(frame["positive_10bd"].sum()),
                "positive_count_20bd": int(frame["positive_20bd"].sum()),
                "avg_max_return_20bd": round_float(frame["max_return_20bd"].mean()),
                "avg_max_drawdown_20bd": round_float(frame["max_drawdown_20bd"].mean()),
                "top_n": int(top_n),
            }
        )
    return pd.DataFrame(rows)


def build_comparisons(by_date: pd.DataFrame) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    for target_date, frame in by_date.groupby("target_date"):
        lookup = {row["selection_group"]: row for row in frame.to_dict("records")}
        opp = lookup.get("OpportunityTop5", {})
        candidate = lookup.get("CandidateTop50", {})
        score = lookup.get("CandidateScoreTop5", {})
        comparisons[str(target_date)] = {
            "opportunity_beats_candidate_top50": horizon_win_block(opp, candidate),
            "opportunity_beats_candidate_score_top5": horizon_win_block(opp, score),
        }
    return comparisons


def horizon_win_block(left: dict[str, Any], right: dict[str, Any]) -> dict[str, bool]:
    return {
        "5bd": float(left.get("mean_return_5bd", 0.0)) > float(right.get("mean_return_5bd", 0.0)),
        "10bd": float(left.get("mean_return_10bd", 0.0)) > float(right.get("mean_return_10bd", 0.0)),
        "20bd": float(left.get("mean_return_20bd", 0.0)) > float(right.get("mean_return_20bd", 0.0)),
    }


def build_summary(
    *,
    created_at: str,
    seed: int,
    years: list[int],
    samples_per_year: int,
    top_n: int,
    sampled_dates: list[str],
    eligible_dates: dict[int, list[str]],
    json_path: Path,
    by_date_path: Path,
    by_stock_path: Path,
    doc_path: Path,
    feature_columns: list[str],
    audit: dict[str, Any],
    by_date: pd.DataFrame,
    by_stock: pd.DataFrame,
    comparisons: dict[str, Any],
) -> dict[str, Any]:
    opportunity_top5 = by_stock[by_stock["selection_group"] == "OpportunityTop5"].copy()
    contribution_summary = build_contribution_summary(opportunity_top5)
    effective_dates = []
    ineffective_dates = []
    for target_date, block in comparisons.items():
        wins = block["opportunity_beats_candidate_top50"]
        if wins["20bd"]:
            effective_dates.append(target_date)
        else:
            ineffective_dates.append(target_date)
    return {
        "phase": PHASE,
        "status": "OK",
        "created_at": created_at,
        "random_seed": int(seed),
        "years": years,
        "samples_per_year": int(samples_per_year),
        "top_n": int(top_n),
        "sampled_target_dates": sampled_dates,
        "eligible_target_date_count_by_year": {str(year): len(dates) for year, dates in eligible_dates.items()},
        "artifact_paths": {
            "json": str(json_path),
            "by_date_csv": str(by_date_path),
            "by_stock_csv": str(by_stock_path),
            "markdown_report": str(doc_path),
        },
        "feature_audit": audit,
        "future_outcome_used_for_evaluation_only": True,
        "label_table_used_for_inference_features": False,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "capital_allocation_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "feature_column_count": len(feature_columns),
        "feature_columns": feature_columns,
        "by_date_records": by_date.to_dict("records"),
        "opportunity_top5_by_date": {
            str(target_date): frame[["code", "buy_rank", "expected_edge_score", "return_5bd", "return_10bd", "return_20bd"]].to_dict("records")
            for target_date, frame in opportunity_top5.groupby("target_date")
        },
        "opportunity_contribution_by_date": contribution_summary,
        "comparisons": comparisons,
        "opportunity_effective_dates_20bd_vs_candidate_top50": effective_dates,
        "opportunity_ineffective_dates_20bd_vs_candidate_top50": ineffective_dates,
        "initial_conclusion": build_initial_conclusion(effective_dates, ineffective_dates, len(sampled_dates)),
        "caveats": [
            "Sample size is small.",
            "Phase5 primary horizon is 20 business days.",
            "5bd and 10bd outcomes are auxiliary observations.",
            "This is offline outcome checking, not live trading or Paper Trading.",
            "Future outcomes are used only for evaluation.",
        ],
    }


def build_contribution_summary(opportunity_top5: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for target_date, frame in opportunity_top5.groupby("target_date"):
        sorted_frame = frame.sort_values(["return_20bd", "code"], ascending=[False, True])
        top = sorted_frame.iloc[0]
        drag = sorted_frame.iloc[-1]
        summary[str(target_date)] = {
            "top_contributor_20bd": {
                "code": str(top["code"]),
                "buy_rank": int(top["buy_rank"]),
                "return_20bd": round_float(top["return_20bd"]),
                "return_10bd": round_float(top["return_10bd"]),
                "return_5bd": round_float(top["return_5bd"]),
            },
            "largest_drag_20bd": {
                "code": str(drag["code"]),
                "buy_rank": int(drag["buy_rank"]),
                "return_20bd": round_float(drag["return_20bd"]),
                "return_10bd": round_float(drag["return_10bd"]),
                "return_5bd": round_float(drag["return_5bd"]),
            },
            "positive_20bd_codes": [str(code) for code in frame.loc[frame["positive_20bd"], "code"].tolist()],
            "negative_20bd_codes": [str(code) for code in frame.loc[~frame["positive_20bd"], "code"].tolist()],
        }
    return summary


def build_initial_conclusion(effective_dates: list[str], ineffective_dates: list[str], total_dates: int) -> str:
    if not total_dates:
        return "No sampled dates were evaluated."
    if len(effective_dates) > len(ineffective_dates):
        return "OpportunityTop5 beat CandidateTop50 on 20bd mean return for a majority of sampled dates."
    if len(effective_dates) == len(ineffective_dates):
        return "OpportunityTop5 was mixed versus CandidateTop50 on 20bd mean return for sampled dates."
    return "OpportunityTop5 did not beat CandidateTop50 on 20bd mean return for a majority of sampled dates."


def leakage_audit(feature_columns: list[str]) -> dict[str, Any]:
    forbidden = [column for column in feature_columns if any(term in column.lower() for term in FORBIDDEN_FEATURE_TERMS)]
    future = [column for column in forbidden if "future_" in column.lower() or "downside_bad_" in column.lower() or "top_decile_" in column.lower()]
    return {
        "forbidden_feature_column_count": len(forbidden),
        "forbidden_feature_columns": forbidden,
        "future_feature_column_count": len(future),
        "leakage_status": "OK" if not forbidden else "ERROR",
    }


def write_markdown_report(path: Path, summary: dict[str, Any], by_date: pd.DataFrame, by_stock: pd.DataFrame) -> None:
    lines = [
        "# Phase5-O Random Date Opportunity Outcome Check",
        "",
        "## 1. Purpose",
        "",
        "This report checks, on randomly sampled historical target dates, whether OpportunityTop5 improved 5bd / 10bd / 20bd outcomes versus CandidateTop50 and CandidateScoreTop5.",
        "",
        "This is an offline outcome check. It is not live trading, Paper Trading, Broker API use, order placement, promotion, or capital allocation.",
        "",
        "## 2. Sampling",
        "",
        f"- random seed: `{summary['random_seed']}`",
        f"- years: `{summary['years']}`",
        f"- samples per year: `{summary['samples_per_year']}`",
        f"- sampled target dates: `{summary['sampled_target_dates']}`",
        "",
        "## 3. By-Date Metrics",
        "",
        markdown_table(by_date),
        "",
        "## 4. OpportunityTop5 By Date",
        "",
    ]
    opportunity = by_stock[by_stock["selection_group"] == "OpportunityTop5"].copy()
    for target_date, frame in opportunity.groupby("target_date"):
        lines.extend(
            [
                f"### {target_date}",
                "",
                markdown_table(frame[["code", "buy_rank", "expected_edge_score", "return_5bd", "return_10bd", "return_20bd", "max_return_20bd", "max_drawdown_20bd"]]),
                "",
            ]
        )
    lines.extend(
        [
            "## 5. Comparison Summary",
            "",
            f"- Opportunity effective dates on 20bd mean return vs CandidateTop50: `{summary['opportunity_effective_dates_20bd_vs_candidate_top50']}`",
            f"- Opportunity ineffective dates on 20bd mean return vs CandidateTop50: `{summary['opportunity_ineffective_dates_20bd_vs_candidate_top50']}`",
            f"- initial conclusion: {summary['initial_conclusion']}",
            "",
            "## 6. Contributors And Draggers",
            "",
        ]
    )
    for target_date, block in summary["opportunity_contribution_by_date"].items():
        top = block["top_contributor_20bd"]
        drag = block["largest_drag_20bd"]
        lines.extend(
            [
                f"- `{target_date}`: top contributor `{top['code']}` return_20bd={top['return_20bd']}; largest drag `{drag['code']}` return_20bd={drag['return_20bd']}",
            ]
        )
    lines.extend(
        [
            "",
            "## 7. Caveats",
            "",
            "- sample size is small",
            "- Phase5 primary horizon is 20 business days",
            "- 5bd / 10bd are auxiliary observations",
            "- future outcome is evaluation-only",
            "- this is not real trading, Paper Trading, Broker API, order placement, capital allocation, promotion, or reader switch",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_model_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict) or "model" not in payload:
        raise ValueError("Opportunity model payload is invalid")
    return payload


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.to_dict("records"):
        values = [format_markdown_value(row.get(column)) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def format_markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return str(round_float(value))
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def round_float(value: Any, digits: int = 6) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return round(numeric, digits)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
