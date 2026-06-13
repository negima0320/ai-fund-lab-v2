#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import pickle
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.audit_phase4bi_random_date_candidate_winrate import (  # noqa: E402
    FIRST_TRAINABLE_TARGET_DATE,
    _is_nan,
    _mean_bool,
    _mean_float,
    _predict_scores,
    _read_json,
    _read_pickle,
    _write_csv,
    _write_json,
    selection_frame_has_leakage,
)

PHASE = "Phase4-BJ"
OUTPUT_DIR = Path("reports/candidate_ai/final_check")
SUMMARY_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_summary.json"
BY_YEAR_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_by_year.csv"
BY_DATE_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_by_date.csv"
BY_TOPN_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_by_topn.csv"
CANDIDATES_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_candidates.csv"
SCORE_DECILE_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_score_decile.csv"
MARKET_REGIME_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_market_regime.csv"
SECTOR_CSV_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_sector.csv"
MANIFEST_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_manifest.json"
DOC_PATH = Path("docs/phase_reports/phase4bj_candidate_robustness_audit.md")
BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
BE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")

READY = "PHASE4_ROBUSTNESS_TEST_COMPLETE"
READY_WEAK = "PHASE4_ROBUSTNESS_TEST_COMPLETE_WITH_WEAKNESSES"
BLOCKED_SELECTION_LEAKAGE = "BLOCKED_BY_SELECTION_LEAKAGE"
BLOCKED_MODEL = "BLOCKED_BY_MISSING_MODEL"
BLOCKED_FEATURE = "BLOCKED_BY_MISSING_FEATURE_TABLE"
BLOCKED_LABEL = "BLOCKED_BY_MISSING_LABEL_TABLE"
BLOCKED_DATES = "BLOCKED_BY_NO_ELIGIBLE_TARGET_DATES"
BLOCKED_AUDIT = "BLOCKED_BY_AUDIT_FAILURE"

DEFAULT_YEARS = (2021, 2022, 2023, 2024, 2025)
DEFAULT_TOP_N_LIST = (10, 20, 30, 50)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-BJ Candidate AI robustness test.")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--dates-per-year", type=int, default=10)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--top-n-list", nargs="+", type=int, default=list(DEFAULT_TOP_N_LIST))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = run_phase4bj_candidate_robustness(
        random_seed=args.random_seed,
        dates_per_year=args.dates_per_year,
        years=args.years,
        top_n_list=args.top_n_list,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4bj_candidate_robustness(
    *,
    random_seed: int = 42,
    dates_per_year: int = 10,
    years: list[int] | tuple[int, ...] = DEFAULT_YEARS,
    top_n_list: list[int] | tuple[int, ...] = DEFAULT_TOP_N_LIST,
    run_id: str | None = None,
    bf_summary_path: Path = BF_SUMMARY_PATH,
    be_summary_path: Path = BE_SUMMARY_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    try:
        top_n_list = sorted({int(value) for value in top_n_list})
        max_top_n = max(top_n_list)
        bf_summary = _read_json(bf_summary_path)
        be_summary = _read_json(be_summary_path)
        model_path = Path(str(bf_summary.get("model_artifact_path") or ""))
        feature_table_path = Path(str(be_summary.get("feature_table_path") or ""))
        dataset_path = Path(str(be_summary.get("dataset_output_path") or ""))
        if not model_path.is_file():
            return _write_blocked(output_dir, BLOCKED_MODEL, "Phase4-BF model artifact is missing.")
        if not feature_table_path.is_file():
            return _write_blocked(output_dir, BLOCKED_FEATURE, "Long-history feature table is missing.")
        if not dataset_path.is_file():
            return _write_blocked(output_dir, BLOCKED_LABEL, "Long-history dataset with labels is missing.")

        model_payload = _read_pickle(model_path)
        model = model_payload.get("model")
        feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
        if model is None or not feature_columns:
            return _write_blocked(output_dir, BLOCKED_MODEL, "Model payload is missing model or feature columns.")

        feature_frame = read_feature_table(feature_table_path, feature_columns)
        label_frame = read_label_table(dataset_path)
        if selection_frame_has_leakage(feature_frame):
            return _write_blocked(output_dir, BLOCKED_SELECTION_LEAKAGE, "Selection frame contains label or future columns.")

        sampled_dates = sample_target_dates(
            feature_frame=feature_frame,
            label_frame=label_frame,
            years=years,
            dates_per_year=dates_per_year,
            random_seed=random_seed,
            top_n=max_top_n,
        )
        if len(sampled_dates) != len(years) * dates_per_year:
            return _write_blocked(output_dir, BLOCKED_DATES, "Could not sample all requested target dates.")

        by_date_rows: list[dict[str, Any]] = []
        candidate_rows: list[dict[str, Any]] = []
        score_decile_rows: list[dict[str, Any]] = []
        rng = random.Random(random_seed)
        for sampled in sampled_dates:
            target_date = sampled["target_date"]
            features_for_date = feature_frame[feature_frame["target_date"] == target_date].copy()
            labels_for_date = label_frame[label_frame["target_date"] == target_date].copy()
            scored = score_candidates_for_date(
                feature_frame_only=features_for_date,
                model=model,
                feature_columns=feature_columns,
            )
            market = scored[["target_date", "code", "candidate_score"]].merge(
                labels_for_date, on=["target_date", "code"], how="inner"
            )
            score_decile_rows.extend(score_decile_metrics(sampled["sampled_year"], target_date, market))
            for top_n in top_n_list:
                selected = scored.head(top_n).copy()
                evaluated = selected.merge(labels_for_date, on=["target_date", "code"], how="left", validate="one_to_one")
                random_codes = rng.sample(list(market["code"].astype(str)), k=min(top_n, len(market)))
                random_baseline = market[market["code"].astype(str).isin(random_codes)]
                row = {
                    "sampled_year": sampled["sampled_year"],
                    "target_date": target_date,
                    "top_n": top_n,
                    "candidate_count": int(len(evaluated)),
                    **prefixed("candidate", quality_metrics(evaluated)),
                    **prefixed("market", quality_metrics(market)),
                    **prefixed("random", quality_metrics(random_baseline)),
                }
                by_date_rows.append(row)
                for _, candidate in evaluated.iterrows():
                    candidate_rows.append(candidate_output_row(sampled["sampled_year"], top_n, candidate))

        by_year_rows = aggregate_rows(by_date_rows, ["sampled_year", "top_n"])
        by_topn_rows = aggregate_rows(by_date_rows, ["top_n"])
        top50_rows = [row for row in by_date_rows if row["top_n"] == max_top_n]
        readiness, findings, implications = judge_robustness(top50_rows)
        summary = build_summary(
            random_seed=random_seed,
            dates_per_year=dates_per_year,
            years=years,
            top_n_list=top_n_list,
            sampled_dates=sampled_dates,
            top50_rows=top50_rows,
            by_year_rows=by_year_rows,
            by_topn_rows=by_topn_rows,
            score_decile_rows=score_decile_rows,
            readiness_status=readiness,
            key_findings=findings,
            phase5_implications=implications,
            run_id=run_id,
            output_dir=output_dir,
        )
        paths = output_paths(output_dir, run_id)
        _write_json(paths["summary"], summary)
        _write_csv(paths["by_year"], by_year_rows)
        _write_csv(paths["by_date"], by_date_rows)
        _write_csv(paths["by_topn"], by_topn_rows)
        _write_csv(paths["candidates"], candidate_rows)
        _write_csv(paths["score_decile"], score_decile_rows)
        _write_csv(paths["market_regime"], [{"status": "SKIPPED", "reason": "local TOPIX or market regime feature is not available"}])
        _write_csv(paths["sector"], [{"status": "SKIPPED", "reason": "local sector master is not available"}])
        _write_json(
            paths["manifest"],
            {
                "phase": PHASE,
                "created_at": now(),
                "random_seed": random_seed,
                "dates_per_year": dates_per_year,
                "years": list(years),
                "top_n_list": list(top_n_list),
                "run_id": run_id,
                "sampled_dates": sampled_dates,
                "feature_table_path": str(feature_table_path),
                "dataset_path": str(dataset_path),
                "model_path": str(model_path),
                "future_data_used_for_selection": False,
                "label_data_used_for_selection": False,
            },
        )
        if output_dir == OUTPUT_DIR and run_id is None:
            write_markdown(DOC_PATH, summary)
        return summary
    except Exception as exc:  # pragma: no cover
        return _write_blocked(output_dir, BLOCKED_AUDIT, f"Robustness audit failed: {type(exc).__name__}")


def sample_target_dates(
    *,
    feature_frame: Any,
    label_frame: Any,
    years: list[int] | tuple[int, ...],
    dates_per_year: int,
    random_seed: int,
    top_n: int,
) -> list[dict[str, Any]]:
    rng = random.Random(random_seed)
    eligible_counts = feature_frame.groupby("target_date", sort=False).size().to_dict()
    label_counts = label_frame.groupby("target_date", sort=False).size().to_dict()
    feature_dates = set(str(date) for date in eligible_counts)
    label_dates = set(str(date) for date in label_counts)
    sampled: list[dict[str, Any]] = []
    for year in years:
        candidates = sorted(date for date in feature_dates & label_dates if date.startswith(f"{year}-"))
        if year == 2021:
            candidates = [date for date in candidates if date >= FIRST_TRAINABLE_TARGET_DATE]
        candidates = [
            date
            for date in candidates
            if int(eligible_counts.get(date, 0)) >= top_n and int(label_counts.get(date, 0)) >= top_n
        ]
        if len(candidates) < dates_per_year:
            continue
        sampled.extend({"sampled_year": year, "target_date": date} for date in sorted(rng.sample(candidates, dates_per_year)))
    return sampled


def score_candidates_for_date(*, feature_frame_only: Any, model: Any, feature_columns: list[str]) -> Any:
    if selection_frame_has_leakage(feature_frame_only):
        raise ValueError("selection frame contains label/future columns")
    stripped = [column.replace("feature__", "", 1) for column in feature_columns]
    eligible = feature_frame_only[
        feature_frame_only["universe_eligible"].astype(bool)
        & feature_frame_only["excluded_reason"].fillna("").astype(str).eq("")
    ].copy()
    eligible["candidate_score"] = _predict_scores(model, eligible[stripped].astype(float).to_numpy())
    return eligible.sort_values(["candidate_score", "code"], ascending=[False, True]).assign(
        candidate_rank=lambda df: range(1, len(df) + 1)
    )[["target_date", "code", "candidate_score", "candidate_rank"]]


def quality_metrics(frame: Any) -> dict[str, Any]:
    return {
        "win_rate_5d": mean_bool(frame["label__future_return_5d"] > 0),
        "win_rate_10d": mean_bool(frame["label__future_return_10d"] > 0),
        "win_rate_20d": mean_bool(frame["label__future_return_20d"] > 0),
        "avg_return_5d": mean_float(frame["label__future_return_5d"]),
        "avg_return_10d": mean_float(frame["label__future_return_10d"]),
        "avg_return_20d": mean_float(frame["label__future_return_20d"]),
        "avg_future_max_return_20d": mean_float(frame["label__future_max_return_20d"]),
        "avg_future_max_drawdown_20d": mean_float(frame["label__future_max_drawdown_20d"]),
        "downside_bad_rate_20d": mean_bool(frame["label__downside_bad_20d"]),
        "top_decile_rate_20d": mean_bool(frame["label__top_decile_20d"]),
        "candidate_count": int(len(frame)),
    }


def score_decile_metrics(sampled_year: int, target_date: str, market: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scored = market.copy()
    scored["score_decile"] = np.floor(scored["candidate_score"].rank(method="first", pct=True) * 10).clip(0, 9).astype(int) + 1
    for decile, group in scored.groupby("score_decile", sort=True):
        rows.append({"sampled_year": sampled_year, "target_date": target_date, "score_decile": int(decile), **quality_metrics(group)})
    return rows


def aggregate_rows(rows: list[dict[str, Any]], group_keys: list[str]) -> list[dict[str, Any]]:
    import pandas as pd

    df = pd.DataFrame(rows)
    metric_columns = [column for column in df.columns if column not in set(group_keys + ["target_date"])]
    grouped = df.groupby(group_keys, sort=True)[metric_columns].mean(numeric_only=True).reset_index()
    return [{key: normalize_value(value) for key, value in row.items()} for row in grouped.to_dict("records")]


def build_summary(
    *,
    random_seed: int,
    dates_per_year: int,
    years: list[int] | tuple[int, ...],
    top_n_list: list[int] | tuple[int, ...],
    sampled_dates: list[dict[str, Any]],
    top50_rows: list[dict[str, Any]],
    by_year_rows: list[dict[str, Any]],
    by_topn_rows: list[dict[str, Any]],
    score_decile_rows: list[dict[str, Any]],
    readiness_status: str,
    key_findings: list[str],
    phase5_implications: list[str],
    run_id: str | None,
    output_dir: Path,
) -> dict[str, Any]:
    total = average_dicts(top50_rows)
    paths = output_paths(output_dir, run_id)
    return {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness_status,
        "robustness_test_executed": True,
        "random_seed": random_seed,
        "dates_per_year": dates_per_year,
        "years": list(years),
        "sampled_dates": sampled_dates,
        "top_n_list": list(top_n_list),
        "total_sampled_date_count": len(sampled_dates),
        "total_candidate_count_top50": int(sum(row["candidate_count"] for row in top50_rows)),
        "by_year_summary": by_year_rows,
        "by_topn_summary": by_topn_rows,
        "total_win_rate_5d_top50": total["candidate_win_rate_5d"],
        "total_win_rate_10d_top50": total["candidate_win_rate_10d"],
        "total_win_rate_20d_top50": total["candidate_win_rate_20d"],
        "total_avg_return_5d_top50": total["candidate_avg_return_5d"],
        "total_avg_return_10d_top50": total["candidate_avg_return_10d"],
        "total_avg_return_20d_top50": total["candidate_avg_return_20d"],
        "total_avg_future_max_return_20d_top50": total["candidate_avg_future_max_return_20d"],
        "total_downside_bad_rate_20d_top50": total["candidate_downside_bad_rate_20d"],
        "total_top_decile_rate_20d_top50": total["candidate_top_decile_rate_20d"],
        "total_market_win_rate_5d": total["market_win_rate_5d"],
        "total_market_win_rate_10d": total["market_win_rate_10d"],
        "total_market_win_rate_20d": total["market_win_rate_20d"],
        "total_random_win_rate_5d_top50": total["random_win_rate_5d"],
        "total_random_win_rate_10d_top50": total["random_win_rate_10d"],
        "total_random_win_rate_20d_top50": total["random_win_rate_20d"],
        "candidate_vs_market_win_rate_diff_5d_top50": diff(total["candidate_win_rate_5d"], total["market_win_rate_5d"]),
        "candidate_vs_market_win_rate_diff_10d_top50": diff(total["candidate_win_rate_10d"], total["market_win_rate_10d"]),
        "candidate_vs_market_win_rate_diff_20d_top50": diff(total["candidate_win_rate_20d"], total["market_win_rate_20d"]),
        "candidate_vs_random_win_rate_diff_5d_top50": diff(total["candidate_win_rate_5d"], total["random_win_rate_5d"]),
        "candidate_vs_random_win_rate_diff_10d_top50": diff(total["candidate_win_rate_10d"], total["random_win_rate_10d"]),
        "candidate_vs_random_win_rate_diff_20d_top50": diff(total["candidate_win_rate_20d"], total["random_win_rate_20d"]),
        "score_decile_analysis_status": "OK",
        "score_monotonicity_status": score_monotonicity_status(score_decile_rows),
        "market_regime_analysis_status": "SKIPPED",
        "sector_analysis_status": "SKIPPED",
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "leakage_audit_status": "OK",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "summary_path": str(paths["summary"]),
        "key_findings": key_findings,
        "recommended_phase5_implications": phase5_implications,
        "recommended_next_action": "Use robustness findings as Phase5 Opportunity AI input; do not promote directly to trading.",
    }


def judge_robustness(top50_rows: list[dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    total = average_dicts(top50_rows)
    findings: list[str] = []
    implications: list[str] = []
    weak = False
    if total["candidate_avg_future_max_return_20d"] > total["market_avg_future_max_return_20d"]:
        findings.append("top50_future_max_return_beats_market_on_sampled_dates")
    else:
        findings.append("top50_future_max_return_does_not_beat_market")
        weak = True
    if total["candidate_win_rate_20d"] < total["market_win_rate_20d"]:
        findings.append("top50_20d_win_rate_lags_market")
        implications.append("Phase5 should add downside and confirmation filters before any opportunity ranking.")
        weak = True
    if total["candidate_downside_bad_rate_20d"] > total["market_downside_bad_rate_20d"]:
        findings.append("top50_downside_bad_rate_is_above_market")
        implications.append("Phase5 should penalize downside_bad and drawdown-prone candidates.")
        weak = True
    if total["candidate_top_decile_rate_20d"] > total["market_top_decile_rate_20d"]:
        findings.append("top50_top_decile_rate_beats_market")
    else:
        findings.append("top50_top_decile_rate_is_weak")
        weak = True
    if not implications:
        implications.append("Phase5 can focus on opportunity ranking and risk refinement.")
    return (READY_WEAK if weak else READY), findings, implications


def score_monotonicity_status(score_decile_rows: list[dict[str, Any]]) -> str:
    if not score_decile_rows:
        return "PENDING"
    import pandas as pd

    df = pd.DataFrame(score_decile_rows)
    grouped = df.groupby("score_decile")["top_decile_rate_20d"].mean()
    return "OK" if grouped.iloc[-1] > grouped.iloc[0] else "WEAK"


def read_feature_table(path: Path, feature_columns: list[str]) -> Any:
    import pandas as pd

    columns = ["target_date", "code", "universe_eligible", "excluded_reason", *[column.replace("feature__", "", 1) for column in feature_columns]]
    df = pd.read_parquet(path, columns=columns)
    df = df.assign(target_date=lambda frame: frame["target_date"].astype(str), code=lambda frame: frame["code"].astype(str))
    df = df[df["universe_eligible"].astype(bool) & df["excluded_reason"].fillna("").astype(str).eq("")]
    return df


def read_label_table(path: Path) -> Any:
    import pandas as pd

    columns = [
        "target_date",
        "code",
        "label__future_return_5d",
        "label__future_return_10d",
        "label__future_return_20d",
        "label__future_max_return_20d",
        "label__future_max_drawdown_20d",
        "label__top_decile_20d",
        "label__downside_bad_20d",
    ]
    return pd.read_parquet(path, columns=columns).assign(target_date=lambda df: df["target_date"].astype(str), code=lambda df: df["code"].astype(str))


def candidate_output_row(sampled_year: int, top_n: int, row: Any) -> dict[str, Any]:
    return {
        "sampled_year": sampled_year,
        "target_date": row["target_date"],
        "top_n": top_n,
        "candidate_rank": int(row["candidate_rank"]),
        "code": str(row["code"]),
        "candidate_score": round(float(row["candidate_score"]), 8),
        "future_return_5d": round_float(row["label__future_return_5d"]),
        "future_return_10d": round_float(row["label__future_return_10d"]),
        "future_return_20d": round_float(row["label__future_return_20d"]),
        "future_max_return_20d": round_float(row["label__future_max_return_20d"]),
        "future_max_drawdown_20d": round_float(row["label__future_max_drawdown_20d"]),
        "top_decile_20d": False if _is_nan(row["label__top_decile_20d"]) else bool(row["label__top_decile_20d"]),
        "downside_bad_20d": False if _is_nan(row["label__downside_bad_20d"]) else bool(row["label__downside_bad_20d"]),
    }


def prefixed(prefix: str, values: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in values.items()}


def average_dicts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [key for key in rows[0] if isinstance(rows[0][key], (int, float)) and key not in {"sampled_year", "top_n"}]
    return {key: mean_float(row[key] for row in rows) for key in keys}


def mean_bool(values: Any) -> float:
    return _mean_bool([value for value in list(values) if not _is_nan(value)])


def mean_float(values: Any) -> float:
    return _mean_float([value for value in list(values) if not _is_nan(value)])


def round_float(value: Any) -> float:
    return round(float(value), 6)


def diff(left: float, right: float) -> float:
    return round(float(left - right), 6)


def normalize_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return round(float(value), 6)
    if isinstance(value, float):
        return round(value, 6)
    return value


def output_paths(output_dir: Path, run_id: str | None) -> dict[str, Path]:
    return {
        "summary": output_dir / name_with_run_id(SUMMARY_PATH.name, run_id),
        "by_year": output_dir / name_with_run_id(BY_YEAR_CSV_PATH.name, run_id),
        "by_date": output_dir / name_with_run_id(BY_DATE_CSV_PATH.name, run_id),
        "by_topn": output_dir / name_with_run_id(BY_TOPN_CSV_PATH.name, run_id),
        "candidates": output_dir / name_with_run_id(CANDIDATES_CSV_PATH.name, run_id),
        "score_decile": output_dir / name_with_run_id(SCORE_DECILE_CSV_PATH.name, run_id),
        "market_regime": output_dir / name_with_run_id(MARKET_REGIME_CSV_PATH.name, run_id),
        "sector": output_dir / name_with_run_id(SECTOR_CSV_PATH.name, run_id),
        "manifest": output_dir / name_with_run_id(MANIFEST_PATH.name, run_id),
    }


def name_with_run_id(name: str, run_id: str | None) -> str:
    if not run_id:
        return name
    stem, suffix = name.rsplit(".", 1)
    return f"{stem}_{run_id}.{suffix}"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BJ Candidate AI Robustness Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- sampled_date_count: `{summary['total_sampled_date_count']}`",
        f"- total_candidate_count_top50: `{summary['total_candidate_count_top50']}`",
        "",
        "## Top50 Totals",
        "",
        f"- win_rate_5d/10d/20d: `{summary['total_win_rate_5d_top50']}` / `{summary['total_win_rate_10d_top50']}` / `{summary['total_win_rate_20d_top50']}`",
        f"- avg_return_20d: `{summary['total_avg_return_20d_top50']}`",
        f"- avg_future_max_return_20d: `{summary['total_avg_future_max_return_20d_top50']}`",
        f"- downside_bad_rate_20d: `{summary['total_downside_bad_rate_20d_top50']}`",
        f"- top_decile_rate_20d: `{summary['total_top_decile_rate_20d_top50']}`",
        "",
        "## Analysis Status",
        "",
        f"- score_decile_analysis_status: `{summary['score_decile_analysis_status']}`",
        f"- score_monotonicity_status: `{summary['score_monotonicity_status']}`",
        f"- market_regime_analysis_status: `{summary['market_regime_analysis_status']}`",
        f"- sector_analysis_status: `{summary['sector_analysis_status']}`",
        "",
        "## Leakage Guard",
        "",
        "- Candidate selection used feature table columns only.",
        "- Label/future data was joined only after candidate lists were created for evaluation.",
        "- This is not backtest, trading, Paper Trading, broker API, order execution, portfolio simulation, annual return, or final assets.",
        "",
        "## Key Findings",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["key_findings"])
    lines.extend(["", "## Phase5 Implications", ""])
    lines.extend(f"- {item}" for item in summary["recommended_phase5_implications"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_blocked(output_dir: Path, readiness: str, reason: str) -> dict[str, Any]:
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness,
        "robustness_test_executed": False,
        "block_reason": reason,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "leakage_audit_status": "SKIPPED",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "recommended_next_action": "Fix the Phase4-BJ robustness blocker and rerun.",
    }
    _write_json(output_dir / SUMMARY_PATH.name, summary)
    return summary


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
