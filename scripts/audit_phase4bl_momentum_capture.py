#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
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

from scripts.audit_phase4bi_random_date_candidate_winrate import _read_json, _read_pickle, _write_csv, _write_json, selection_frame_has_leakage  # noqa: E402
from scripts.audit_phase4bj_candidate_robustness import (  # noqa: E402
    DEFAULT_YEARS,
    read_feature_table,
    read_label_table,
    sample_target_dates,
    score_candidates_for_date,
)

PHASE = "Phase4-BL"
OUTPUT_DIR = Path("reports/candidate_ai/final_check")
SUMMARY_PATH = OUTPUT_DIR / "phase4bl_momentum_capture_summary.json"
BY_DATE_PATH = OUTPUT_DIR / "phase4bl_momentum_capture_by_date.csv"
BY_YEAR_PATH = OUTPUT_DIR / "phase4bl_momentum_capture_by_year.csv"
BY_TOPN_TOPK_PATH = OUTPUT_DIR / "phase4bl_momentum_capture_by_topn_topk.csv"
INTERSECTIONS_PATH = OUTPUT_DIR / "phase4bl_momentum_capture_intersections.csv"
MANIFEST_PATH = OUTPUT_DIR / "phase4bl_momentum_capture_manifest.json"
DOC_PATH = Path("docs/phase_reports/phase4bl_momentum_capture_audit.md")

BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
BE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")
BJ_SUMMARY_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_summary.json"

READY = "PHASE4_MOMENTUM_CAPTURE_AUDIT_COMPLETE"
READY_WEAK = "PHASE4_MOMENTUM_CAPTURE_AUDIT_COMPLETE_WITH_WEAKNESSES"
BLOCKED_SELECTION_LEAKAGE = "BLOCKED_BY_SELECTION_LEAKAGE"
BLOCKED_MODEL = "BLOCKED_BY_MISSING_MODEL"
BLOCKED_FEATURE = "BLOCKED_BY_MISSING_FEATURE_TABLE"
BLOCKED_LABEL = "BLOCKED_BY_MISSING_LABEL_TABLE"
BLOCKED_DATES = "BLOCKED_BY_NO_ELIGIBLE_TARGET_DATES"
BLOCKED_AUDIT = "BLOCKED_BY_AUDIT_FAILURE"

DEFAULT_TOP_N_LIST = (10, 20, 30, 50)
DEFAULT_FUTURE_TOP_K_LIST = (10, 20, 50, 100)
FUTURE_BASIS_COLUMNS = {
    "future_return_20d": "label__future_return_20d",
    "future_max_return_20d": "label__future_max_return_20d",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-BL momentum capture audit.")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--dates-per-year", type=int, default=10)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--candidate-topn-list", nargs="+", type=int, default=list(DEFAULT_TOP_N_LIST))
    parser.add_argument("--future-topk-list", nargs="+", type=int, default=list(DEFAULT_FUTURE_TOP_K_LIST))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = run_phase4bl_momentum_capture(
        random_seed=args.random_seed,
        dates_per_year=args.dates_per_year,
        years=args.years,
        candidate_topn_list=args.candidate_topn_list,
        future_topk_list=args.future_topk_list,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4bl_momentum_capture(
    *,
    random_seed: int = 42,
    dates_per_year: int = 10,
    years: list[int] | tuple[int, ...] = DEFAULT_YEARS,
    candidate_topn_list: list[int] | tuple[int, ...] = DEFAULT_TOP_N_LIST,
    future_topk_list: list[int] | tuple[int, ...] = DEFAULT_FUTURE_TOP_K_LIST,
    run_id: str | None = None,
    bf_summary_path: Path = BF_SUMMARY_PATH,
    be_summary_path: Path = BE_SUMMARY_PATH,
    bj_summary_path: Path = BJ_SUMMARY_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    try:
        candidate_topn_list = sorted({int(value) for value in candidate_topn_list})
        future_topk_list = sorted({int(value) for value in future_topk_list})
        bf_summary = _read_json(bf_summary_path)
        be_summary = _read_json(be_summary_path)
        model_path = Path(str(bf_summary.get("model_artifact_path") or ""))
        feature_table_path = Path(str(be_summary.get("feature_table_path") or ""))
        dataset_path = Path(str(be_summary.get("dataset_output_path") or ""))
        if not model_path.is_file():
            return write_blocked(output_dir, BLOCKED_MODEL, "Phase4-BF model artifact is missing.")
        if not feature_table_path.is_file():
            return write_blocked(output_dir, BLOCKED_FEATURE, "Long-history feature table is missing.")
        if not dataset_path.is_file():
            return write_blocked(output_dir, BLOCKED_LABEL, "Long-history label/dataset table is missing.")

        model_payload = _read_pickle(model_path)
        model = model_payload.get("model")
        feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
        if model is None or not feature_columns:
            return write_blocked(output_dir, BLOCKED_MODEL, "Model payload is missing model or feature columns.")

        feature_frame = read_feature_table(feature_table_path, feature_columns)
        label_frame = read_label_table(dataset_path)
        if selection_frame_has_leakage(feature_frame):
            return write_blocked(output_dir, BLOCKED_SELECTION_LEAKAGE, "Selection frame contains label/future columns.")

        sampled_dates = load_bj_sampled_dates(bj_summary_path)
        if not sampled_dates:
            sampled_dates = sample_target_dates(
                feature_frame=feature_frame,
                label_frame=label_frame,
                years=years,
                dates_per_year=dates_per_year,
                random_seed=random_seed,
                top_n=max(candidate_topn_list),
            )
        if len(sampled_dates) != len(years) * dates_per_year:
            return write_blocked(output_dir, BLOCKED_DATES, "Could not prepare all requested sampled dates.")

        by_date_rows: list[dict[str, Any]] = []
        intersection_rows: list[dict[str, Any]] = []
        rng = random.Random(random_seed)
        for sampled in sampled_dates:
            target_date = str(sampled["target_date"])
            features_for_date = feature_frame[feature_frame["target_date"] == target_date].copy()
            labels_for_date = label_frame[label_frame["target_date"] == target_date].copy()
            scored = score_candidates_for_date(
                feature_frame_only=features_for_date,
                model=model,
                feature_columns=feature_columns,
            )
            market = scored.merge(labels_for_date, on=["target_date", "code"], how="inner", validate="one_to_one")
            for basis_name, basis_column in FUTURE_BASIS_COLUMNS.items():
                ranked_future = market.sort_values([basis_column, "code"], ascending=[False, True]).copy()
                ranked_future["future_rank"] = range(1, len(ranked_future) + 1)
                future_rank_map = dict(zip(ranked_future["code"].astype(str), ranked_future["future_rank"]))
                for top_n in candidate_topn_list:
                    candidate_top = scored.head(top_n).copy()
                    candidate_codes = set(candidate_top["code"].astype(str))
                    random_codes = set(rng.sample(list(market["code"].astype(str)), k=min(top_n, len(market))))
                    for top_k in future_topk_list:
                        future_top = ranked_future.head(top_k).copy()
                        future_codes = set(future_top["code"].astype(str))
                        captured = sorted(candidate_codes & future_codes)
                        random_captured = random_codes & future_codes
                        eligible_count = int(len(market))
                        capture_count = len(captured)
                        random_capture_count = len(random_captured)
                        capture_rate = safe_rate(capture_count, top_k)
                        random_capture_rate = safe_rate(random_capture_count, top_k)
                        market_expected_capture_rate = safe_rate(top_n, eligible_count)
                        row = {
                            "sampled_year": int(sampled["sampled_year"]),
                            "target_date": target_date,
                            "future_topk_basis": basis_name,
                            "candidate_top_n": top_n,
                            "future_top_k": top_k,
                            "eligible_universe_count": eligible_count,
                            "capture_count": capture_count,
                            "capture_rate": capture_rate,
                            "precision_to_future_topk": safe_rate(capture_count, top_n),
                            "random_capture_count": random_capture_count,
                            "random_capture_rate": random_capture_rate,
                            "market_expected_capture_rate": market_expected_capture_rate,
                            "enrichment_vs_random": safe_ratio(capture_rate, random_capture_rate),
                            "enrichment_vs_market_expected": safe_ratio(capture_rate, market_expected_capture_rate),
                        }
                        by_date_rows.append(row)
                        if top_n == max(candidate_topn_list) and top_k in {50, 100}:
                            candidate_lookup = candidate_top.set_index("code")
                            future_lookup = ranked_future.set_index("code")
                            for code in captured:
                                candidate_row = candidate_lookup.loc[code]
                                future_row = future_lookup.loc[code]
                                intersection_rows.append(
                                    {
                                        "sampled_year": int(sampled["sampled_year"]),
                                        "target_date": target_date,
                                        "future_topk_basis": basis_name,
                                        "candidate_top_n": top_n,
                                        "future_top_k": top_k,
                                        "code": str(code),
                                        "candidate_rank": int(candidate_row["candidate_rank"]),
                                        "candidate_score": round_float(candidate_row["candidate_score"]),
                                        "future_rank": int(future_rank_map[str(code)]),
                                        "future_return_20d": round_float(future_row["label__future_return_20d"]),
                                        "future_max_return_20d": round_float(future_row["label__future_max_return_20d"]),
                                        "future_max_drawdown_20d": round_float(future_row["label__future_max_drawdown_20d"]),
                                    }
                                )

        by_year_rows = aggregate_rows(by_date_rows, ["sampled_year", "future_topk_basis", "candidate_top_n", "future_top_k"])
        by_topn_topk_rows = aggregate_rows(by_date_rows, ["future_topk_basis", "candidate_top_n", "future_top_k"])
        summary = build_summary(
            sampled_dates=sampled_dates,
            years=years,
            candidate_topn_list=candidate_topn_list,
            future_topk_list=future_topk_list,
            by_date_rows=by_date_rows,
            by_year_rows=by_year_rows,
            by_topn_topk_rows=by_topn_topk_rows,
            random_seed=random_seed,
            dates_per_year=dates_per_year,
            run_id=run_id,
            output_dir=output_dir,
        )
        paths = output_paths(output_dir, run_id)
        _write_json(paths["summary"], summary)
        _write_csv(paths["by_date"], by_date_rows)
        _write_csv(paths["by_year"], by_year_rows)
        _write_csv(paths["by_topn_topk"], by_topn_topk_rows)
        _write_csv(paths["intersections"], intersection_rows)
        _write_json(
            paths["manifest"],
            {
                "phase": PHASE,
                "created_at": now(),
                "random_seed": random_seed,
                "dates_per_year": dates_per_year,
                "years": list(years),
                "candidate_topn_list": list(candidate_topn_list),
                "future_topk_list": list(future_topk_list),
                "future_topk_basis_list": list(FUTURE_BASIS_COLUMNS),
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
        return write_blocked(output_dir, BLOCKED_AUDIT, f"Momentum capture audit failed: {type(exc).__name__}")


def load_bj_sampled_dates(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = _read_json(path)
    sampled = payload.get("sampled_dates") or []
    return [{"sampled_year": int(row["sampled_year"]), "target_date": str(row["target_date"])} for row in sampled]


def build_summary(
    *,
    sampled_dates: list[dict[str, Any]],
    years: list[int] | tuple[int, ...],
    candidate_topn_list: list[int],
    future_topk_list: list[int],
    by_date_rows: list[dict[str, Any]],
    by_year_rows: list[dict[str, Any]],
    by_topn_topk_rows: list[dict[str, Any]],
    random_seed: int,
    dates_per_year: int,
    run_id: str | None,
    output_dir: Path,
) -> dict[str, Any]:
    top50_return_top50 = total_capture(by_date_rows, "future_return_20d", 50, 50)
    top50_return_top100 = total_capture(by_date_rows, "future_return_20d", 50, 100)
    top50_max_top50 = total_capture(by_date_rows, "future_max_return_20d", 50, 50)
    top50_max_top100 = total_capture(by_date_rows, "future_max_return_20d", 50, 100)
    pass_flag = (
        top50_return_top50["enrichment_vs_random"] > 1.2
        or top50_return_top100["enrichment_vs_random"] > 1.15
        or top50_max_top50["enrichment_vs_random"] > 1.2
        or top50_max_top100["enrichment_vs_random"] > 1.15
    )
    key_findings, phase5_implications = findings_and_implications(top50_return_top50, top50_return_top100, top50_max_top50, top50_max_top100)
    paths = output_paths(output_dir, run_id)
    return {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": READY if pass_flag else READY_WEAK,
        "momentum_capture_audit_executed": True,
        "random_seed": random_seed,
        "dates_per_year": dates_per_year,
        "years": list(years),
        "sampled_dates": sampled_dates,
        "total_sampled_date_count": len(sampled_dates),
        "candidate_topn_list": list(candidate_topn_list),
        "future_topk_list": list(future_topk_list),
        "future_topk_basis_list": list(FUTURE_BASIS_COLUMNS),
        "total_candidate_top50_future_return_top50_capture_count": top50_return_top50["capture_count"],
        "total_candidate_top50_future_return_top50_capture_rate": top50_return_top50["capture_rate"],
        "total_candidate_top50_future_return_top100_capture_count": top50_return_top100["capture_count"],
        "total_candidate_top50_future_return_top100_capture_rate": top50_return_top100["capture_rate"],
        "total_candidate_top50_future_max_top50_capture_count": top50_max_top50["capture_count"],
        "total_candidate_top50_future_max_top50_capture_rate": top50_max_top50["capture_rate"],
        "total_candidate_top50_future_max_top100_capture_count": top50_max_top100["capture_count"],
        "total_candidate_top50_future_max_top100_capture_rate": top50_max_top100["capture_rate"],
        "random_capture_rate_top50_future_return_top50": top50_return_top50["random_capture_rate"],
        "random_capture_rate_top50_future_max_top50": top50_max_top50["random_capture_rate"],
        "enrichment_vs_random_future_return_top50": top50_return_top50["enrichment_vs_random"],
        "enrichment_vs_random_future_max_top50": top50_max_top50["enrichment_vs_random"],
        "market_expected_capture_rate_top50": top50_return_top50["market_expected_capture_rate"],
        "by_year_capture_summary": by_year_rows,
        "by_topn_topk_summary": by_topn_topk_rows,
        "best_capture_dates": best_worst_dates(by_date_rows, best=True),
        "worst_capture_dates": best_worst_dates(by_date_rows, best=False),
        "future_return_vs_future_max_capture_gap": round_float(top50_max_top50["capture_rate"] - top50_return_top50["capture_rate"]),
        "momentum_capture_pass": pass_flag,
        "key_findings": key_findings,
        "phase5_implications": phase5_implications,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "future_data_used_for_capture_evaluation": True,
        "leakage_audit_status": "OK",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "summary_path": str(paths["summary"]),
        "recommended_next_action": "Use capture gaps to design Phase5 Opportunity AI confirmation and risk filters.",
    }


def total_capture(rows: list[dict[str, Any]], basis: str, top_n: int, top_k: int) -> dict[str, Any]:
    filtered = [row for row in rows if row["future_topk_basis"] == basis and row["candidate_top_n"] == top_n and row["future_top_k"] == top_k]
    capture_count = sum(int(row["capture_count"]) for row in filtered)
    random_capture_count = sum(int(row["random_capture_count"]) for row in filtered)
    denominator = len(filtered) * top_k
    capture_rate = safe_rate(capture_count, denominator)
    random_capture_rate = safe_rate(random_capture_count, denominator)
    market_expected_capture_rate = mean(row["market_expected_capture_rate"] for row in filtered)
    return {
        "capture_count": int(capture_count),
        "capture_rate": capture_rate,
        "random_capture_count": int(random_capture_count),
        "random_capture_rate": random_capture_rate,
        "market_expected_capture_rate": market_expected_capture_rate,
        "enrichment_vs_random": safe_ratio(capture_rate, random_capture_rate),
        "enrichment_vs_market_expected": safe_ratio(capture_rate, market_expected_capture_rate),
    }


def findings_and_implications(*captures: dict[str, Any]) -> tuple[list[str], list[str]]:
    return_top50, return_top100, max_top50, max_top100 = captures
    findings: list[str] = []
    implications: list[str] = []
    if max_top50["enrichment_vs_random"] > return_top50["enrichment_vs_random"]:
        findings.append("future_max_return_capture_is_stronger_than_future_return_capture")
        implications.append("Phase5 should distinguish temporary price spikes from sustained 20d returns.")
    if return_top50["enrichment_vs_random"] > 1:
        findings.append("candidate_top50_captures_future_return_top50_above_random")
    else:
        findings.append("candidate_top50_future_return_top50_capture_is_weak")
        implications.append("Phase5 should add confirmation filters for sustained return candidates.")
    if max_top50["enrichment_vs_random"] > 1:
        findings.append("candidate_top50_captures_future_max_top50_above_random")
    else:
        findings.append("candidate_top50_future_max_top50_capture_is_weak")
    if return_top100["enrichment_vs_random"] > 1 or max_top100["enrichment_vs_random"] > 1:
        findings.append("candidate_top50_has_some_future_top100_enrichment")
    if not implications:
        implications.append("Phase5 can build on Candidate scores, but should still manage downside risk.")
    implications.append("This audit is not backtest/trading; use only as Opportunity AI design evidence.")
    return findings, implications


def best_worst_dates(rows: list[dict[str, Any]], *, best: bool) -> list[dict[str, Any]]:
    target = [row for row in rows if row["candidate_top_n"] == 50 and row["future_top_k"] == 50]
    target = sorted(target, key=lambda row: (row["capture_rate"], row["capture_count"]), reverse=best)
    return [
        {
            "target_date": row["target_date"],
            "sampled_year": row["sampled_year"],
            "future_topk_basis": row["future_topk_basis"],
            "capture_count": row["capture_count"],
            "capture_rate": row["capture_rate"],
        }
        for row in target[:10]
    ]


def aggregate_rows(rows: list[dict[str, Any]], group_keys: list[str]) -> list[dict[str, Any]]:
    import pandas as pd

    df = pd.DataFrame(rows)
    metric_columns = [column for column in df.columns if column not in set(group_keys + ["target_date", "sampled_year"])]
    grouped = df.groupby(group_keys, sort=True)[metric_columns].mean(numeric_only=True).reset_index()
    rows = [{key: normalize(value) for key, value in row.items()} for row in grouped.to_dict("records")]
    for row in rows:
        row["enrichment_vs_random"] = safe_ratio(float(row.get("capture_rate", 0.0)), float(row.get("random_capture_rate", 0.0)))
        row["enrichment_vs_market_expected"] = safe_ratio(
            float(row.get("capture_rate", 0.0)), float(row.get("market_expected_capture_rate", 0.0))
        )
    return rows


def mean(values: Any) -> float:
    clean = [float(value) for value in list(values)]
    if not clean:
        return 0.0
    return round_float(sum(clean) / len(clean))


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round_float(float(numerator) / float(denominator))


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round_float(float(numerator) / float(denominator))


def round_float(value: Any) -> float:
    return round(float(value), 6)


def normalize(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round_float(value)
    return value


def output_paths(output_dir: Path, run_id: str | None) -> dict[str, Path]:
    return {
        "summary": output_dir / name_with_run_id(SUMMARY_PATH.name, run_id),
        "by_date": output_dir / name_with_run_id(BY_DATE_PATH.name, run_id),
        "by_year": output_dir / name_with_run_id(BY_YEAR_PATH.name, run_id),
        "by_topn_topk": output_dir / name_with_run_id(BY_TOPN_TOPK_PATH.name, run_id),
        "intersections": output_dir / name_with_run_id(INTERSECTIONS_PATH.name, run_id),
        "manifest": output_dir / name_with_run_id(MANIFEST_PATH.name, run_id),
    }


def name_with_run_id(name: str, run_id: str | None) -> str:
    if not run_id:
        return name
    stem, suffix = name.rsplit(".", 1)
    return f"{stem}_{run_id}.{suffix}"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BL Momentum Capture Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- momentum_capture_pass: `{summary['momentum_capture_pass']}`",
        f"- sampled_date_count: `{summary['total_sampled_date_count']}`",
        "",
        "## Core Capture",
        "",
        f"- Top50 vs FutureReturnTop50 capture: `{summary['total_candidate_top50_future_return_top50_capture_count']}` / rate `{summary['total_candidate_top50_future_return_top50_capture_rate']}`",
        f"- Top50 vs FutureReturnTop100 capture: `{summary['total_candidate_top50_future_return_top100_capture_count']}` / rate `{summary['total_candidate_top50_future_return_top100_capture_rate']}`",
        f"- Top50 vs FutureMaxTop50 capture: `{summary['total_candidate_top50_future_max_top50_capture_count']}` / rate `{summary['total_candidate_top50_future_max_top50_capture_rate']}`",
        f"- Top50 vs FutureMaxTop100 capture: `{summary['total_candidate_top50_future_max_top100_capture_count']}` / rate `{summary['total_candidate_top50_future_max_top100_capture_rate']}`",
        f"- random_capture_rate_top50_future_return_top50: `{summary['random_capture_rate_top50_future_return_top50']}`",
        f"- random_capture_rate_top50_future_max_top50: `{summary['random_capture_rate_top50_future_max_top50']}`",
        f"- market_expected_capture_rate_top50: `{summary['market_expected_capture_rate_top50']}`",
        "",
        "## Key Findings",
        "",
        *[f"- {item}" for item in summary["key_findings"]],
        "",
        "## Phase5 Implications",
        "",
        *[f"- {item}" for item in summary["phase5_implications"]],
        "",
        "## Guardrails",
        "",
        "- Candidate selection used feature-only inputs.",
        "- Future/label data was used only after candidate lists were created for capture evaluation.",
        "- This is not backtest, trading, Paper Trading, broker API, order execution, portfolio simulation, annual return, or final assets.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked(output_dir: Path, readiness: str, reason: str) -> dict[str, Any]:
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness,
        "momentum_capture_audit_executed": False,
        "block_reason": reason,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "leakage_audit_status": "SKIPPED",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "recommended_next_action": "Fix the Phase4-BL blocker and rerun.",
    }
    _write_json(output_dir / SUMMARY_PATH.name, summary)
    return summary


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
