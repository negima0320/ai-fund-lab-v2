#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.audit_phase4bi_random_date_candidate_winrate import selection_frame_has_leakage  # noqa: E402

PHASE = "Phase4-BK"
OUTPUT_DIR = Path("reports/candidate_ai/final_check")
CANDIDATE_PATH = OUTPUT_DIR / "phase4bj_candidate_robustness_candidates.csv"
BE_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json")
BF_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json")

SUMMARY_PATH = OUTPUT_DIR / "phase4bk_winner_loser_cases_summary.json"
BEST_PATH = OUTPUT_DIR / "phase4bk_winner_loser_best.csv"
WORST_PATH = OUTPUT_DIR / "phase4bk_winner_loser_worst.csv"
FEATURE_COMPARE_PATH = OUTPUT_DIR / "phase4bk_winner_loser_feature_compare.csv"
DOC_PATH = Path("docs/phase_reports/phase4bk_winner_loser_case_study.md")

READY = "PHASE4_WINNER_LOSER_CASE_STUDY_COMPLETE"
BLOCKED_CANDIDATE = "BLOCKED_BY_MISSING_CANDIDATE_FILE"
BLOCKED_FEATURE = "BLOCKED_BY_MISSING_FEATURE_TABLE"
BLOCKED_LEAKAGE = "BLOCKED_BY_SELECTION_LEAKAGE"
BLOCKED_AUDIT = "BLOCKED_BY_AUDIT_FAILURE"

YEARS = (2021, 2022, 2023, 2024, 2025)
CASE_COUNT_PER_YEAR = 10
FEATURE_COLUMNS = [
    "liquidity_avg_volume_20d",
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "price_momentum_return_60d",
    "volatility_return_std_20d",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "trend_ma_20_60_ratio",
    "volume_momentum_ratio_5d",
    "volume_momentum_ratio_1d_20d",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase4-BK winner/loser case study.")
    parser.add_argument("--candidate-path", type=Path, default=CANDIDATE_PATH)
    parser.add_argument("--be-summary-path", type=Path, default=BE_SUMMARY_PATH)
    parser.add_argument("--bf-summary-path", type=Path, default=BF_SUMMARY_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    summary = run_phase4bk_winner_loser_case_study(
        candidate_path=args.candidate_path,
        be_summary_path=args.be_summary_path,
        bf_summary_path=args.bf_summary_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def run_phase4bk_winner_loser_case_study(
    *,
    candidate_path: Path = CANDIDATE_PATH,
    be_summary_path: Path = BE_SUMMARY_PATH,
    bf_summary_path: Path = BF_SUMMARY_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    try:
        if not candidate_path.is_file():
            return write_blocked(output_dir, BLOCKED_CANDIDATE, "Phase4-BJ candidate file is missing.")
        be_summary = read_json(be_summary_path)
        feature_table_path = Path(str(be_summary.get("feature_table_path") or ""))
        if not feature_table_path.is_file():
            return write_blocked(output_dir, BLOCKED_FEATURE, "Long history feature table is missing.")

        candidates = read_candidates(candidate_path)
        top50_candidates = candidates[candidates["top_n"].astype(int) == 50].copy()
        if top50_candidates.empty:
            return write_blocked(output_dir, BLOCKED_CANDIDATE, "Phase4-BJ Top50 candidates are missing.")
        if candidate_selection_frame_has_leakage(top50_candidates):
            return write_blocked(output_dir, BLOCKED_LEAKAGE, "Candidate selection frame contains forbidden columns.")

        best = pick_best_cases(top50_candidates)
        worst = pick_worst_cases(top50_candidates)
        features = read_features_for_cases(feature_table_path, best, worst)
        best = attach_features(best, features)
        worst = attach_features(worst, features)
        feature_compare = build_feature_compare(best, worst)

        summary = build_summary(best=best, worst=worst, feature_compare=feature_compare, bf_summary_path=bf_summary_path)
        paths = output_paths(output_dir)
        write_json(paths["summary"], summary)
        write_csv(paths["best"], rows_from_frame(best))
        write_csv(paths["worst"], rows_from_frame(worst))
        write_csv(paths["feature_compare"], feature_compare)
        if output_dir == OUTPUT_DIR:
            write_markdown(DOC_PATH, summary, best, worst, feature_compare)
        return summary
    except Exception as exc:  # pragma: no cover
        return write_blocked(output_dir, BLOCKED_AUDIT, f"Case study audit failed: {type(exc).__name__}")


def read_candidates(path: Path) -> Any:
    import pandas as pd

    df = pd.read_csv(path, dtype={"code": str})
    df["target_date"] = df["target_date"].astype(str)
    df["sampled_year"] = df["sampled_year"].astype(int)
    return df


def candidate_selection_frame_has_leakage(candidates: Any) -> bool:
    selection_columns = ["sampled_year", "target_date", "top_n", "candidate_rank", "code", "candidate_score"]
    return selection_frame_has_leakage(candidates[selection_columns])


def pick_best_cases(candidates: Any) -> Any:
    sort_columns = ["future_max_return_20d", "future_return_20d", "candidate_score"]
    return pick_by_year(candidates, sort_columns, ascending=[False, False, False])


def pick_worst_cases(candidates: Any) -> Any:
    frame = candidates.copy()
    frame["downside_priority"] = frame["downside_bad_20d"].astype(bool).astype(int)
    sort_columns = ["downside_priority", "future_max_drawdown_20d", "future_return_20d", "candidate_score"]
    return pick_by_year(frame, sort_columns, ascending=[False, True, True, False]).drop(columns=["downside_priority"])


def pick_by_year(candidates: Any, sort_columns: list[str], ascending: list[bool]) -> Any:
    import pandas as pd

    rows = []
    for year in YEARS:
        group = candidates[candidates["sampled_year"].astype(int) == year].copy()
        if group.empty:
            continue
        rows.append(group.sort_values(sort_columns, ascending=ascending).head(CASE_COUNT_PER_YEAR))
    if not rows:
        return pd.DataFrame(columns=candidates.columns)
    return pd.concat(rows, ignore_index=True)


def read_features_for_cases(feature_table_path: Path, best: Any, worst: Any) -> Any:
    import pandas as pd

    keys = pd.concat([best[["target_date", "code"]], worst[["target_date", "code"]]], ignore_index=True).drop_duplicates()
    columns = ["target_date", "code", *FEATURE_COLUMNS]
    features = pd.read_parquet(feature_table_path, columns=columns)
    features["target_date"] = features["target_date"].astype(str)
    features["code"] = features["code"].astype(str)
    return keys.merge(features, on=["target_date", "code"], how="left", validate="one_to_one")


def attach_features(cases: Any, features: Any) -> Any:
    merged = cases.merge(features, on=["target_date", "code"], how="left", validate="one_to_one")
    if "company_name" not in merged.columns:
        merged.insert(3, "company_name", "")
    return merged


def build_feature_compare(best: Any, worst: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in FEATURE_COLUMNS:
        best_mean = safe_mean(best[feature])
        worst_mean = safe_mean(worst[feature])
        rows.append(
            {
                "feature_name": feature,
                "best_mean": best_mean,
                "worst_mean": worst_mean,
                "best_minus_worst": round_float(best_mean - worst_mean),
                "phase5_hint": phase5_hint(feature, best_mean, worst_mean),
            }
        )
    rows.append(
        {
            "feature_name": "candidate_score",
            "best_mean": safe_mean(best["candidate_score"]),
            "worst_mean": safe_mean(worst["candidate_score"]),
            "best_minus_worst": round_float(safe_mean(best["candidate_score"]) - safe_mean(worst["candidate_score"])),
            "phase5_hint": "Use only as candidate prior; Phase5 should add risk/confirmation filters.",
        }
    )
    return rows


def phase5_hint(feature: str, best_mean: float, worst_mean: float) -> str:
    diff = best_mean - worst_mean
    if math.isnan(diff):
        return "No stable hypothesis; missing values need review."
    if abs(diff) < 1e-9:
        return "No material Best/Worst separation in this case sample."
    direction = "higher" if diff > 0 else "lower"
    return f"Best cases show {direction} {feature}; consider as Phase5 scoring/filter hypothesis."


def build_summary(*, best: Any, worst: Any, feature_compare: list[dict[str, Any]], bf_summary_path: Path) -> dict[str, Any]:
    best_score = safe_mean(best["candidate_score"])
    worst_score = safe_mean(worst["candidate_score"])
    best_common = common_feature_hypotheses(feature_compare, positive=True)
    worst_common = common_feature_hypotheses(feature_compare, positive=False)
    rank_return_corr = correlation(best, worst, "candidate_rank", "future_return_20d")
    rank_downside_corr = correlation(best, worst, "candidate_rank", "downside_bad_20d")
    return {
        "phase": PHASE,
        "status": "OK",
        "readiness_status": READY,
        "best_case_count": int(len(best)),
        "worst_case_count": int(len(worst)),
        "years": list(YEARS),
        "best_avg_candidate_score": best_score,
        "worst_avg_candidate_score": worst_score,
        "candidate_score_gap_best_minus_worst": round_float(best_score - worst_score),
        "best_avg_return_20d": safe_mean(best["future_return_20d"]),
        "worst_avg_return_20d": safe_mean(worst["future_return_20d"]),
        "best_avg_future_max_return_20d": safe_mean(best["future_max_return_20d"]),
        "worst_avg_future_max_return_20d": safe_mean(worst["future_max_return_20d"]),
        "best_avg_future_max_drawdown_20d": safe_mean(best["future_max_drawdown_20d"]),
        "worst_avg_future_max_drawdown_20d": safe_mean(worst["future_max_drawdown_20d"]),
        "best_common_features": best_common,
        "worst_common_features": worst_common,
        "rank_future_return_20d_correlation": rank_return_corr,
        "rank_downside_bad_20d_correlation": rank_downside_corr,
        "phase5_filter_hypotheses": phase5_hypotheses(feature_compare, best_score, worst_score),
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "future_data_used_for_case_analysis": True,
        "leakage_audit_status": "OK",
        "backtest_executed": False,
        "trading_executed": False,
        "order_executed": False,
        "paper_trading_executed": False,
        "broker_api_called": False,
        "model_manifest_path": str(read_json(bf_summary_path).get("model_manifest_path", "")) if bf_summary_path.is_file() else "",
        "summary_path": str(SUMMARY_PATH),
        "recommended_next_action": "Use Best/Worst feature gaps as Phase5 Opportunity AI filter and scoring hypotheses.",
    }


def common_feature_hypotheses(feature_compare: list[dict[str, Any]], *, positive: bool) -> list[str]:
    sorted_rows = sorted(feature_compare, key=lambda row: abs(float(row["best_minus_worst"])), reverse=True)
    selected = []
    for row in sorted_rows:
        if row["feature_name"] == "candidate_score":
            continue
        diff = float(row["best_minus_worst"])
        if (positive and diff > 0) or (not positive and diff < 0):
            selected.append(f"{row['feature_name']} ({'higher' if diff > 0 else 'lower'} in Best)")
        if len(selected) >= 5:
            break
    return selected


def phase5_hypotheses(feature_compare: list[dict[str, Any]], best_score: float, worst_score: float) -> list[str]:
    hypotheses = [
        "Treat Candidate score as an upstream prior, not a buy decision.",
        "Add downside and drawdown filters before opportunity ranking.",
    ]
    if best_score <= worst_score:
        hypotheses.append("Candidate score alone does not separate winners from losers in this sample; add confirmation features.")
    for row in sorted(feature_compare, key=lambda item: abs(float(item["best_minus_worst"])), reverse=True)[:5]:
        if row["feature_name"] != "candidate_score":
            hypotheses.append(str(row["phase5_hint"]))
    return hypotheses


def correlation(best: Any, worst: Any, left: str, right: str) -> float:
    import pandas as pd

    frame = pd.concat([best[[left, right]], worst[[left, right]]], ignore_index=True)
    if right == "downside_bad_20d":
        frame[right] = frame[right].astype(bool).astype(int)
    value = frame[left].astype(float).corr(frame[right].astype(float), method="spearman")
    return round_float(value) if not math.isnan(float(value)) else 0.0


def safe_mean(values: Any) -> float:
    clean = [float(value) for value in list(values) if value == value]
    if not clean:
        return float("nan")
    return round_float(sum(clean) / len(clean))


def round_float(value: Any) -> float:
    if value is None:
        return float("nan")
    return round(float(value), 6)


def rows_from_frame(frame: Any) -> list[dict[str, Any]]:
    wanted = [
        "sampled_year",
        "target_date",
        "code",
        "company_name",
        "candidate_rank",
        "candidate_score",
        "future_return_5d",
        "future_return_10d",
        "future_return_20d",
        "future_max_return_20d",
        "future_max_drawdown_20d",
        "top_decile_20d",
        "downside_bad_20d",
        *FEATURE_COLUMNS,
    ]
    rows: list[dict[str, Any]] = []
    for row in frame[wanted].to_dict("records"):
        rows.append({key: normalize(value) for key, value in row.items()})
    return rows


def normalize(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return round(value, 6)
    return value


def output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "summary": output_dir / SUMMARY_PATH.name,
        "best": output_dir / BEST_PATH.name,
        "worst": output_dir / WORST_PATH.name,
        "feature_compare": output_dir / FEATURE_COMPARE_PATH.name,
    }


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: dict[str, Any], best: Any, worst: Any, feature_compare: list[dict[str, Any]]) -> None:
    best_preview = rows_from_frame(best.head(10))
    worst_preview = rows_from_frame(worst.head(10))
    lines = [
        "# Phase4-BK Winner / Loser Case Study",
        "",
        f"- status: `{summary['status']}`",
        f"- readiness_status: `{summary['readiness_status']}`",
        f"- best_case_count: `{summary['best_case_count']}`",
        f"- worst_case_count: `{summary['worst_case_count']}`",
        f"- leakage_audit_status: `{summary['leakage_audit_status']}`",
        "",
        "## Score / Return Summary",
        "",
        f"- best_avg_candidate_score: `{summary['best_avg_candidate_score']}`",
        f"- worst_avg_candidate_score: `{summary['worst_avg_candidate_score']}`",
        f"- best_avg_return_20d: `{summary['best_avg_return_20d']}`",
        f"- worst_avg_return_20d: `{summary['worst_avg_return_20d']}`",
        f"- best_avg_future_max_return_20d: `{summary['best_avg_future_max_return_20d']}`",
        f"- worst_avg_future_max_return_20d: `{summary['worst_avg_future_max_return_20d']}`",
        f"- best_avg_future_max_drawdown_20d: `{summary['best_avg_future_max_drawdown_20d']}`",
        f"- worst_avg_future_max_drawdown_20d: `{summary['worst_avg_future_max_drawdown_20d']}`",
        "",
        "## Best Preview",
        "",
        *[f"- {row['sampled_year']} {row['target_date']} {row['code']} rank={row['candidate_rank']} score={row['candidate_score']} return20d={row['future_return_20d']}" for row in best_preview],
        "",
        "## Worst Preview",
        "",
        *[f"- {row['sampled_year']} {row['target_date']} {row['code']} rank={row['candidate_rank']} score={row['candidate_score']} return20d={row['future_return_20d']} drawdown20d={row['future_max_drawdown_20d']}" for row in worst_preview],
        "",
        "## Feature Compare",
        "",
        *[f"- {row['feature_name']}: best_mean={row['best_mean']} worst_mean={row['worst_mean']} diff={row['best_minus_worst']}" for row in feature_compare],
        "",
        "## Phase5 Hypotheses",
        "",
        *[f"- {item}" for item in summary["phase5_filter_hypotheses"]],
        "",
        "## Guardrails",
        "",
        "- Candidate selection was already completed in Phase4-BJ using feature-only inputs.",
        "- Future/label columns are used here only for post-selection case analysis.",
        "- No backtest, trading, Paper Trading, broker API, order, promotion, or reader switch is executed.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked(output_dir: Path, readiness: str, reason: str) -> dict[str, Any]:
    summary = {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness,
        "block_reason": reason,
        "future_data_used_for_selection": False,
        "label_data_used_for_selection": False,
        "leakage_audit_status": "SKIPPED",
        "backtest_executed": False,
        "trading_executed": False,
        "order_executed": False,
        "recommended_next_action": "Fix the Phase4-BK blocker and rerun.",
    }
    write_json(output_dir / SUMMARY_PATH.name, summary)
    return summary


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
