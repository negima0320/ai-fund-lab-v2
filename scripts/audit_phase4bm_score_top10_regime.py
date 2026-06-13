#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
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

from scripts.audit_phase4bi_random_date_candidate_winrate import _read_json, _read_pickle, _write_csv, _write_json, selection_frame_has_leakage  # noqa: E402
from scripts.audit_phase4bj_candidate_robustness import (  # noqa: E402
    DEFAULT_YEARS,
    read_feature_table,
    read_label_table,
    sample_target_dates,
    score_candidates_for_date,
)

PHASE = "Phase4-BM"
OUTPUT_DIR = Path("reports/candidate_ai/final_check")
SUMMARY_PATH = OUTPUT_DIR / "phase4bm_score_top10_regime_summary.json"
TOPN_QUALITY_PATH = OUTPUT_DIR / "phase4bm_score_topn_quality.csv"
FUTURE_TOP10_CAPTURE_PATH = OUTPUT_DIR / "phase4bm_future_top10_capture.csv"
REGIME_PROXY_QUALITY_PATH = OUTPUT_DIR / "phase4bm_regime_proxy_quality.csv"
MANIFEST_PATH = OUTPUT_DIR / "phase4bm_manifest.json"
DOC_PATH = Path("docs/phase_reports/phase4bm_score_top10_regime_audit.md")

BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")
BE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")
BJ_SUMMARY_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_summary.json"

READY = "PHASE4_SCORE_TOP10_REGIME_AUDIT_COMPLETE"
READY_WEAK = "PHASE4_SCORE_TOP10_REGIME_AUDIT_COMPLETE_WITH_WEAKNESSES"
BLOCKED_SELECTION_LEAKAGE = "BLOCKED_BY_SELECTION_LEAKAGE"
BLOCKED_INPUT = "BLOCKED_BY_MISSING_INPUT"
BLOCKED_AUDIT = "BLOCKED_BY_AUDIT_FAILURE"

DEFAULT_TOP_N_LIST = (10, 20, 30, 50)
FUTURE_TOP_K_LIST = (10, 20, 50, 100)
FUTURE_BASIS_COLUMNS = {
    "future_return_20d": "label__future_return_20d",
    "future_max_return_20d": "label__future_max_return_20d",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-BM score, Top10 capture, and regime proxy audit.")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--dates-per-year", type=int, default=10)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--top-n-list", nargs="+", type=int, default=list(DEFAULT_TOP_N_LIST))
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    summary = run_phase4bm_score_top10_regime(
        random_seed=args.random_seed,
        dates_per_year=args.dates_per_year,
        years=args.years,
        top_n_list=args.top_n_list,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4bm_score_top10_regime(
    *,
    random_seed: int = 42,
    dates_per_year: int = 10,
    years: list[int] | tuple[int, ...] = DEFAULT_YEARS,
    top_n_list: list[int] | tuple[int, ...] = DEFAULT_TOP_N_LIST,
    run_id: str | None = None,
    bf_summary_path: Path = BF_SUMMARY_PATH,
    be_summary_path: Path = BE_SUMMARY_PATH,
    bj_summary_path: Path = BJ_SUMMARY_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    try:
        top_n_list = sorted({int(value) for value in top_n_list})
        bf_summary = _read_json(bf_summary_path)
        be_summary = _read_json(be_summary_path)
        model_path = Path(str(bf_summary.get("model_artifact_path") or ""))
        feature_table_path = Path(str(be_summary.get("feature_table_path") or ""))
        dataset_path = Path(str(be_summary.get("dataset_output_path") or ""))
        if not model_path.is_file() or not feature_table_path.is_file() or not dataset_path.is_file():
            return write_blocked(output_dir, BLOCKED_INPUT, "Required model, feature table, or label table is missing.")

        model_payload = _read_pickle(model_path)
        model = model_payload.get("model")
        feature_columns = [str(column) for column in model_payload.get("feature_columns", [])]
        if model is None or not feature_columns:
            return write_blocked(output_dir, BLOCKED_INPUT, "Model payload is missing model or feature columns.")

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
                top_n=max(top_n_list),
            )
        if len(sampled_dates) != len(years) * dates_per_year:
            return write_blocked(output_dir, BLOCKED_INPUT, "Could not prepare all sampled target dates.")

        rng = random.Random(random_seed)
        topn_quality_rows: list[dict[str, Any]] = []
        top10_capture_rows: list[dict[str, Any]] = []
        regime_rows_by_date: list[dict[str, Any]] = []
        correlation_rows = []

        for sampled in sampled_dates:
            target_date = str(sampled["target_date"])
            sampled_year = int(sampled["sampled_year"])
            features_for_date = feature_frame[feature_frame["target_date"] == target_date].copy()
            labels_for_date = label_frame[label_frame["target_date"] == target_date].copy()
            scored = score_candidates_for_date(feature_frame_only=features_for_date, model=model, feature_columns=feature_columns)
            market = scored.merge(labels_for_date, on=["target_date", "code"], how="inner", validate="one_to_one")
            regime = classify_regime(market)
            correlation_rows.append(market[["candidate_score", *FUTURE_BASIS_COLUMNS.values(), "label__downside_bad_20d"]])

            future_top_sets = {
                basis: {
                    top_k: set(
                        market.sort_values([column, "code"], ascending=[False, True]).head(top_k)["code"].astype(str)
                    )
                    for top_k in FUTURE_TOP_K_LIST
                }
                for basis, column in FUTURE_BASIS_COLUMNS.items()
            }
            for top_n in top_n_list:
                selected = scored.head(top_n).merge(labels_for_date, on=["target_date", "code"], how="left", validate="one_to_one")
                selected_codes = set(selected["code"].astype(str))
                topn_quality_rows.append(
                    {
                        "sampled_year": sampled_year,
                        "target_date": target_date,
                        "top_n": top_n,
                        "regime_proxy": regime,
                        **quality_metrics(selected),
                        **capture_metrics_for_selected(selected_codes, future_top_sets),
                    }
                )
                for basis in FUTURE_BASIS_COLUMNS:
                    future_top10 = future_top_sets[basis][10]
                    random_codes = set(rng.sample(list(market["code"].astype(str)), k=min(top_n, len(market))))
                    capture_count = len(selected_codes & future_top10)
                    random_capture_count = len(random_codes & future_top10)
                    top10_capture_rows.append(
                        {
                            "sampled_year": sampled_year,
                            "target_date": target_date,
                            "future_topk_basis": basis,
                            "candidate_top_n": top_n,
                            "future_top_k": 10,
                            "eligible_universe_count": int(len(market)),
                            "capture_count": capture_count,
                            "capture_rate": safe_rate(capture_count, 10),
                            "precision_to_future_top10": safe_rate(capture_count, top_n),
                            "random_capture_count": random_capture_count,
                            "random_capture_rate": safe_rate(random_capture_count, 10),
                            "market_expected_capture_rate": safe_rate(top_n, len(market)),
                            "enrichment_vs_random": safe_ratio(safe_rate(capture_count, 10), safe_rate(random_capture_count, 10)),
                        }
                    )

            top50 = scored.head(50).merge(labels_for_date, on=["target_date", "code"], how="left", validate="one_to_one")
            top50_codes = set(top50["code"].astype(str))
            market_metrics = quality_metrics(market)
            random_codes = set(rng.sample(list(market["code"].astype(str)), k=min(50, len(market))))
            random_frame = market[market["code"].astype(str).isin(random_codes)]
            regime_rows_by_date.append(
                {
                    "sampled_year": sampled_year,
                    "target_date": target_date,
                    "regime_proxy": regime,
                    "market_avg_future_return_20d": round_float(market["label__future_return_20d"].mean()),
                    **prefixed("candidate", quality_metrics(top50)),
                    **prefixed("market", market_metrics),
                    **prefixed("random", quality_metrics(random_frame)),
                    **capture_metrics_for_selected(top50_codes, {"future_return_20d": {50: future_top_sets["future_return_20d"][50]}}),
                }
            )

        topn_quality_summary = aggregate_rows(topn_quality_rows, ["top_n"])
        future_top10_capture_summary = aggregate_rows(top10_capture_rows, ["future_topk_basis", "candidate_top_n", "future_top_k"])
        regime_summary = aggregate_rows(regime_rows_by_date, ["regime_proxy"])
        score_correlations = build_score_correlations(correlation_rows)
        monotonicity = score_rank_monotonicity(topn_quality_summary)
        summary = build_summary(
            sampled_dates=sampled_dates,
            years=years,
            topn_quality_summary=topn_quality_summary,
            future_top10_capture_summary=future_top10_capture_summary,
            regime_summary=regime_summary,
            score_correlations=score_correlations,
            score_rank_monotonicity_status=monotonicity,
            output_dir=output_dir,
            run_id=run_id,
        )
        paths = output_paths(output_dir, run_id)
        _write_json(paths["summary"], summary)
        _write_csv(paths["topn_quality"], topn_quality_rows)
        _write_csv(paths["future_top10"], top10_capture_rows)
        _write_csv(paths["regime"], regime_rows_by_date)
        _write_json(
            paths["manifest"],
            {
                "phase": PHASE,
                "sampled_dates": sampled_dates,
                "future_data_used_for_selection": False,
                "label_data_used_for_selection": False,
                "regime_proxy_used_for_selection": False,
                "feature_table_path": str(feature_table_path),
                "dataset_path": str(dataset_path),
                "model_path": str(model_path),
            },
        )
        if output_dir == OUTPUT_DIR and run_id is None:
            write_markdown(DOC_PATH, summary)
        return summary
    except Exception as exc:  # pragma: no cover
        return write_blocked(output_dir, BLOCKED_AUDIT, f"Score/Top10/regime audit failed: {type(exc).__name__}")


def load_bj_sampled_dates(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = _read_json(path)
    return [{"sampled_year": int(row["sampled_year"]), "target_date": str(row["target_date"])} for row in payload.get("sampled_dates", [])]


def classify_regime(market: Any) -> str:
    value = float(market["label__future_return_20d"].mean())
    if value > 0.02:
        return "up"
    if value < -0.02:
        return "down"
    return "flat"


def quality_metrics(frame: Any) -> dict[str, Any]:
    return {
        "candidate_count": int(len(frame)),
        "win_rate_5d": mean_bool(frame["label__future_return_5d"] > 0),
        "win_rate_10d": mean_bool(frame["label__future_return_10d"] > 0),
        "win_rate_20d": mean_bool(frame["label__future_return_20d"] > 0),
        "avg_return_20d": round_float(frame["label__future_return_20d"].mean()),
        "avg_future_max_return_20d": round_float(frame["label__future_max_return_20d"].mean()),
        "downside_bad_rate_20d": mean_bool(frame["label__downside_bad_20d"]),
        "top_decile_rate_20d": mean_bool(frame["label__top_decile_20d"]),
    }


def capture_metrics_for_selected(selected_codes: set[str], future_top_sets: dict[str, dict[int, set[str]]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for basis, topk_map in future_top_sets.items():
        for top_k, future_codes in topk_map.items():
            capture_count = len(selected_codes & future_codes)
            metrics[f"{basis}_top{top_k}_capture_count"] = int(capture_count)
            metrics[f"{basis}_top{top_k}_capture_rate"] = safe_rate(capture_count, top_k)
    return metrics


def build_score_correlations(frames: list[Any]) -> dict[str, float]:
    import pandas as pd

    frame = pd.concat(frames, ignore_index=True)
    return {
        "score_future_return_correlation": corr(frame, "candidate_score", "label__future_return_20d"),
        "score_future_max_return_correlation": corr(frame, "candidate_score", "label__future_max_return_20d"),
        "score_downside_bad_correlation": corr(frame.assign(label__downside_bad_20d=frame["label__downside_bad_20d"].astype(bool).astype(int)), "candidate_score", "label__downside_bad_20d"),
    }


def corr(frame: Any, left: str, right: str) -> float:
    value = frame[left].astype(float).corr(frame[right].astype(float), method="spearman")
    if value != value:
        return 0.0
    return round_float(value)


def score_rank_monotonicity(topn_rows: list[dict[str, Any]]) -> str:
    ordered = sorted(topn_rows, key=lambda row: int(row["top_n"]))
    max_returns = [float(row["avg_future_max_return_20d"]) for row in ordered]
    top_deciles = [float(row["top_decile_rate_20d"]) for row in ordered]
    downside = [float(row["downside_bad_rate_20d"]) for row in ordered]
    positive = max_returns[0] >= max_returns[-1] and top_deciles[0] >= top_deciles[-1]
    risk = downside[0] <= downside[-1]
    if positive and risk:
        return "OK"
    if positive:
        return "PARTIAL"
    return "WEAK"


def build_summary(
    *,
    sampled_dates: list[dict[str, Any]],
    years: list[int] | tuple[int, ...],
    topn_quality_summary: list[dict[str, Any]],
    future_top10_capture_summary: list[dict[str, Any]],
    regime_summary: list[dict[str, Any]],
    score_correlations: dict[str, float],
    score_rank_monotonicity_status: str,
    output_dir: Path,
    run_id: str | None,
) -> dict[str, Any]:
    return_top10 = lookup_capture(future_top10_capture_summary, "future_return_20d", 50)
    max_top10 = lookup_capture(future_top10_capture_summary, "future_max_return_20d", 50)
    pass_flag = return_top10["enrichment_vs_random"] > 1.2 or max_top10["enrichment_vs_random"] > 1.2
    readiness = READY if pass_flag and score_rank_monotonicity_status != "WEAK" else READY_WEAK
    paths = output_paths(output_dir, run_id)
    return {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": readiness,
        "audit_executed": True,
        "sampled_dates": sampled_dates,
        "years": list(years),
        "score_rank_monotonicity_status": score_rank_monotonicity_status,
        "topn_quality_summary": topn_quality_summary,
        "candidate_top50_future_return_top10_capture_count": int(return_top10["capture_count"] * len(sampled_dates)),
        "candidate_top50_future_return_top10_capture_rate": return_top10["capture_rate"],
        "candidate_top50_future_max_top10_capture_count": int(max_top10["capture_count"] * len(sampled_dates)),
        "candidate_top50_future_max_top10_capture_rate": max_top10["capture_rate"],
        "random_future_return_top10_capture_rate": return_top10["random_capture_rate"],
        "random_future_max_top10_capture_rate": max_top10["random_capture_rate"],
        "enrichment_vs_random_future_return_top10": return_top10["enrichment_vs_random"],
        "enrichment_vs_random_future_max_top10": max_top10["enrichment_vs_random"],
        "regime_proxy_status": "OK",
        "regime_summary": regime_summary,
        **score_correlations,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "future_data_used_for_evaluation": True,
        "regime_proxy_used_for_selection": False,
        "leakage_audit_status": "OK",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "key_findings": key_findings(score_rank_monotonicity_status, return_top10, max_top10, score_correlations),
        "phase5_implications": phase5_implications(score_rank_monotonicity_status, return_top10, max_top10),
        "recommended_next_action": "Use score-rank and regime proxy findings to design Phase5 Opportunity AI filters.",
        "summary_path": str(paths["summary"]),
    }


def lookup_capture(rows: list[dict[str, Any]], basis: str, top_n: int) -> dict[str, Any]:
    for row in rows:
        if row["future_topk_basis"] == basis and int(row["candidate_top_n"]) == top_n and int(row["future_top_k"]) == 10:
            return row
    return {"capture_count": 0, "capture_rate": 0.0, "random_capture_rate": 0.0, "enrichment_vs_random": 0.0}


def key_findings(monotonicity: str, return_top10: dict[str, Any], max_top10: dict[str, Any], correlations: dict[str, float]) -> list[str]:
    findings = [f"score_rank_monotonicity_{monotonicity.lower()}"]
    if return_top10["enrichment_vs_random"] > 1:
        findings.append("candidate_top50_captures_future_return_top10_above_random")
    if max_top10["enrichment_vs_random"] > 1:
        findings.append("candidate_top50_captures_future_max_top10_above_random")
    if max_top10["capture_rate"] > return_top10["capture_rate"]:
        findings.append("future_max_top10_capture_stronger_than_future_return_top10_capture")
    if correlations["score_downside_bad_correlation"] > 0:
        findings.append("higher_score_has_positive_downside_bad_correlation")
    return findings


def phase5_implications(monotonicity: str, return_top10: dict[str, Any], max_top10: dict[str, Any]) -> list[str]:
    implications = []
    if monotonicity != "OK":
        implications.append("Phase5 should not rely on Candidate score rank alone; add confirmation and risk filters.")
    if max_top10["capture_rate"] > return_top10["capture_rate"]:
        implications.append("Phase5 should separate temporary spike potential from sustained 20d return quality.")
    implications.append("Regime proxy is post-selection evaluation only and must not become a selection feature.")
    return implications


def aggregate_rows(rows: list[dict[str, Any]], group_keys: list[str]) -> list[dict[str, Any]]:
    import pandas as pd

    df = pd.DataFrame(rows)
    metric_columns = [column for column in df.columns if column not in set(group_keys + ["target_date", "sampled_year", "regime_proxy"])]
    grouped = df.groupby(group_keys, sort=True)[metric_columns].mean(numeric_only=True).reset_index()
    output = [{key: normalize(value) for key, value in row.items()} for row in grouped.to_dict("records")]
    for row in output:
        if "capture_rate" in row and "random_capture_rate" in row:
            row["enrichment_vs_random"] = safe_ratio(row["capture_rate"], row["random_capture_rate"])
    return output


def prefixed(prefix: str, values: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in values.items()}


def mean_bool(values: Any) -> float:
    clean = [bool(value) for value in list(values)]
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
        "topn_quality": output_dir / name_with_run_id(TOPN_QUALITY_PATH.name, run_id),
        "future_top10": output_dir / name_with_run_id(FUTURE_TOP10_CAPTURE_PATH.name, run_id),
        "regime": output_dir / name_with_run_id(REGIME_PROXY_QUALITY_PATH.name, run_id),
        "manifest": output_dir / name_with_run_id(MANIFEST_PATH.name, run_id),
    }


def name_with_run_id(name: str, run_id: str | None) -> str:
    if not run_id:
        return name
    stem, suffix = name.rsplit(".", 1)
    return f"{stem}_{run_id}.{suffix}"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BM Candidate Score / Top10 Capture / Regime Proxy Audit",
        "",
        f"- status: `{summary['status']}`",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- score_rank_monotonicity_status: `{summary['score_rank_monotonicity_status']}`",
        f"- candidate_top50_future_return_top10_capture_rate: `{summary['candidate_top50_future_return_top10_capture_rate']}`",
        f"- candidate_top50_future_max_top10_capture_rate: `{summary['candidate_top50_future_max_top10_capture_rate']}`",
        f"- regime_proxy_status: `{summary['regime_proxy_status']}`",
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
        "- Future/label/regime proxy data was used only after candidate lists were created for evaluation.",
        "- This is not backtest, trading, Paper Trading, broker API, order execution, final assets, or annual return.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked(output_dir: Path, readiness: str, reason: str) -> dict[str, Any]:
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness,
        "audit_executed": False,
        "block_reason": reason,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "leakage_audit_status": "SKIPPED",
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "order_executed": False,
        "recommended_next_action": "Fix the Phase4-BM blocker and rerun.",
    }
    _write_json(output_dir / SUMMARY_PATH.name, summary)
    return summary


if __name__ == "__main__":
    raise SystemExit(main())
